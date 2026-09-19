"""Read-only Monday.com GraphQL board client."""

from __future__ import annotations

import copy
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import pandas as pd

from app.config import Settings, get_settings
from app.sources.base import BoardKind, BoardSnapshot

API_URL = "https://api.monday.com/v2"
_COLUMN_FIELDS = "id text value type"


class MondayError(RuntimeError):
    """Base error for Monday reads."""


class ReadOnlyViolation(MondayError):
    """Raised before a GraphQL mutation could be sent."""


class MondayAuthError(MondayError):
    """Credentials are invalid or unauthorized."""


class MondayComplexityError(MondayError):
    """The query must be retried with a smaller page size."""


class MondayUnavailable(MondayError):
    """Monday could not be read and no usable cache exists."""


@dataclass
class _CacheEntry:
    snapshot: BoardSnapshot
    stored_at: float


class MondayAPI:
    """Fetch board metadata and raw item text with retries and a stale cache."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
        sleep=time.sleep,
        random_fn=random.random,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client or httpx.Client(timeout=20.0)
        self._owns_client = client is None
        self._sleep = sleep
        self._random = random_fn
        self._cache: dict[str, _CacheEntry] = {}

    def close(self) -> None:
        """Close the HTTP client when this source owns it."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "MondayAPI":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_board(self, kind: BoardKind) -> BoardSnapshot:
        """Load one configured or uniquely named board, falling back to stale data."""

        board_id = self._configured_id(kind)
        try:
            if board_id is None:
                board_id = self._find_board_id(kind)
            metadata = self._board_metadata(board_id)
            snapshot = self._read_items(kind, board_id, metadata)
            self._cache[kind] = _CacheEntry(snapshot, time.monotonic())
            return snapshot
        except MondayAuthError:
            raise
        except Exception as exc:
            cached = self._cache.get(kind)
            if cached is not None:
                stale = copy.deepcopy(cached.snapshot)
                stale.from_cache = True
                stale.warnings.append(
                    f"monday.com unreachable, using data fetched at {stale.fetched_at.isoformat()}"
                )
                return stale
            if isinstance(exc, MondayUnavailable):
                raise
            raise MondayUnavailable(f"Unable to read the {kind} board: {exc}") from exc

    def _configured_id(self, kind: BoardKind) -> str | None:
        return self.settings.deals_board_id if kind == "deals" else self.settings.work_orders_board_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.settings.monday_api_token,
            "API-Version": self.settings.monday_api_version,
            "Content-Type": "application/json",
        }

    def _post(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """POST a query only, retrying transient failures without exposing credentials."""

        if re.search(r"\bmutation\b", query, re.IGNORECASE):
            raise ReadOnlyViolation("Mutation documents are forbidden by the board source")
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.post(API_URL, headers=self._headers(), json={"query": query, "variables": variables})
                if response.status_code in (401, 403):
                    raise MondayAuthError("Monday credentials were rejected")
                if response.status_code == 429 or response.status_code >= 500:
                    raise MondayError(f"transient HTTP status {response.status_code}")
                response.raise_for_status()
                payload = response.json()
                errors = payload.get("errors", [])
                if errors:
                    message = "; ".join(str(error.get("message", "GraphQL error")) for error in errors)
                    lowered = message.casefold()
                    if any(word in lowered for word in ("unauthorized", "authentication", "forbidden", "permission")):
                        raise MondayAuthError(message)
                    if any(word in lowered for word in ("complexity",)):
                        raise MondayComplexityError(message)
                    raise MondayError(message)
                return payload["data"]
            except (MondayAuthError, MondayComplexityError):
                raise
            except (httpx.HTTPError, MondayError, KeyError, ValueError) as exc:
                last_error = exc
                if attempt == 2:
                    break
                self._sleep((2**attempt) * 0.2 + self._random() * 0.1)
        raise MondayUnavailable(f"Monday request failed after retries: {last_error}") from last_error

    def _find_board_id(self, kind: BoardKind) -> str:
        data = self._post("query { boards { id name } }", {})
        needle = "deal" if kind == "deals" else "work order"
        matches = [board for board in data.get("boards", []) if needle in board["name"].casefold()]
        if len(matches) != 1:
            raise MondayError(f"Expected exactly one board containing '{needle}', found {len(matches)}")
        return str(matches[0]["id"])

    def _board_metadata(self, board_id: str) -> dict[str, Any]:
        data = self._post(
            "query BoardMetadata($ids: [ID!]) { boards(ids: $ids) { id name columns { id title type } } }",
            {"ids": [board_id]},
        )
        boards = data.get("boards", [])
        if len(boards) != 1:
            raise MondayError(f"Board {board_id} was not found")
        return boards[0]

    def _read_items(self, kind: BoardKind, board_id: str, metadata: dict[str, Any]) -> BoardSnapshot:
        columns = metadata.get("columns", [])
        titles: list[str] = []
        title_counts: dict[str, int] = {}
        warnings: list[str] = []
        column_keys: dict[str, str] = {}
        for column in columns:
            title = str(column.get("title") or column["id"])
            title_counts[title] = title_counts.get(title, 0) + 1
            key = title if title_counts[title] == 1 else f"{title}__{title_counts[title]}"
            if key != title:
                warnings.append(f"Duplicate Monday column title '{title}' renamed to '{key}'")
            titles.append(key)
            column_keys[str(column["id"])] = key

        items: list[dict[str, Any]] = []
        limit = 200
        cursor: str | None = None
        while True:
            try:
                page = self._items_page(board_id, limit, cursor)
            except MondayComplexityError:
                if limit > 25:
                    limit = max(25, limit // 2)
                    continue
                raise
            except MondayUnavailable as exc:
                if self._is_complexity_error(str(exc)) and limit > 25:
                    limit = max(25, limit // 2)
                    continue
                raise
            items.extend(page.get("items", []))
            cursor = page.get("cursor")
            if not cursor:
                break

        rows: list[dict[str, Any]] = []
        first_title = titles[0] if titles else None
        for item in items:
            row: dict[str, Any] = {title: None for title in titles}
            if first_title is not None:
                row[first_title] = item.get("name") or None
            for value in item.get("column_values", []):
                key = column_keys.get(str(value.get("id")))
                if key is None or key == first_title:
                    continue
                text = value.get("text")
                row[key] = text if text not in (None, "") else (value.get("value") or None)
            row.update(_item_id=str(item.get("id")), _item_name=item.get("name"), _group=(item.get("group") or {}).get("title"))
            rows.append(row)
        frame = pd.DataFrame(rows, columns=titles + ["_item_id", "_item_name", "_group"])
        return BoardSnapshot(frame, datetime.now(timezone.utc), str(metadata["id"]), str(metadata["name"]), warnings=warnings)

    def _items_page(self, board_id: str, limit: int, cursor: str | None) -> dict[str, Any]:
        if cursor:
            data = self._post(
                f"query NextItems($cursor: String!, $limit: Int!) {{ next_items_page(cursor: $cursor, limit: $limit) {{ cursor items {{ id name group {{ title }} column_values {{ {_COLUMN_FIELDS} }} }} }} }}",
                {"cursor": cursor, "limit": limit},
            )
            return data["next_items_page"]
        data = self._post(
            f"query Items($ids: [ID!], $limit: Int!) {{ boards(ids: $ids) {{ items_page(limit: $limit) {{ cursor items {{ id name group {{ title }} column_values {{ {_COLUMN_FIELDS} }} }} }} }} }}",
            {"ids": [board_id], "limit": limit},
        )
        return data["boards"][0]["items_page"]

    @staticmethod
    def _is_complexity_error(message: str) -> bool:
        lowered = message.casefold()
        return "complexity" in lowered or "limit" in lowered and "query" in lowered

