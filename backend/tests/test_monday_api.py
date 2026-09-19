"""Focused Phase 1 tests using httpx MockTransport; no real Monday calls."""

from datetime import datetime, timezone

import httpx
import pandas as pd
import pytest

from app.config import Settings
from app.sources.monday_api import MondayAPI, MondayAuthError, ReadOnlyViolation


def settings(**overrides: str) -> Settings:
    values = dict(monday_api_token="token", monday_api_version="2026-01", gemini_api_key="unused", gemini_model="unused", deals_board_id="1", work_orders_board_id="2", cache_ttl_seconds=300)
    values.update(overrides)
    return Settings(**values)


def response(data: dict) -> httpx.Response:
    return httpx.Response(200, json={"data": data})


def test_read_only_guard() -> None:
    api = MondayAPI(settings(), client=httpx.Client(transport=httpx.MockTransport(lambda _: response({}))))
    with pytest.raises(ReadOnlyViolation):
        api._post("mutation { delete_item(id: 1) { id } }", {})


def test_pagination_and_item_name_are_raw_text() -> None:
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        calls.append(__import__("json").loads(body))
        query = calls[-1]["query"]
        if "BoardMetadata" in query:
            return response({"boards": [{"id": "1", "name": "Deals", "columns": [{"id": "name", "title": "Deal Name", "type": "name"}, {"id": "status", "title": "Status", "type": "status"}]}]})
        cursor = calls[-1]["variables"].get("cursor")
        if cursor is None:
            return response({"boards": [{"items_page": {"cursor": "c1", "items": [{"id": "a", "name": "Alpha", "group": {"title": "Open"}, "column_values": [{"id": "name", "text": "Wrong", "value": "x", "type": "name"}, {"id": "status", "text": "Open", "value": None, "type": "status"}] }]}}]})
        return response({"next_items_page": {"cursor": None, "items": [{"id": "b", "name": "Beta", "group": None, "column_values": [{"id": "status", "text": "", "value": None, "type": "status"}]}]}})

    api = MondayAPI(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    snapshot = api.get_board("deals")
    assert snapshot.df.shape == (2, 5)
    assert snapshot.df.iloc[0]["Deal Name"] == "Alpha"
    assert pd.isna(snapshot.df.iloc[1]["Status"])
    assert len(calls) == 3


def test_retry_on_429() -> None:
    count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count < 3:
            return httpx.Response(429, json={"errors": [{"message": "rate limit"}]})
        return response({"boards": []})

    api = MondayAPI(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    if True:
        api._post("query { boards { id } }", {})
    assert count == 3


def test_auth_error_is_not_retried() -> None:
    count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(401)

    api = MondayAPI(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    with pytest.raises(MondayAuthError):
        api._post("query { boards { id } }", {})
    assert count == 1


def test_stale_cache_is_returned_on_failure() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls <= 2:
            if "BoardMetadata" in request.content.decode():
                return response({"boards": [{"id": "1", "name": "Deals", "columns": []}]})
            return response({"boards": [{"items_page": {"cursor": None, "items": []}}]})
        return httpx.Response(503)

    api = MondayAPI(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    first = api.get_board("deals")
    second = api.get_board("deals")
    assert not first.from_cache
    assert second.from_cache
    assert "monday.com unreachable" in second.warnings[-1]


def test_duplicate_titles_are_suffixed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "BoardMetadata" in request.content.decode():
            return response({"boards": [{"id": "1", "name": "Deals", "columns": [{"id": "a", "title": "X", "type": "text"}, {"id": "b", "title": "X", "type": "text"}]}]})
        return response({"boards": [{"items_page": {"cursor": None, "items": []}}]})

    snapshot = MondayAPI(settings(), client=httpx.Client(transport=httpx.MockTransport(handler))).get_board("deals")
    assert list(snapshot.df.columns) == ["X", "X__2", "_item_id", "_item_name", "_group"]
    assert snapshot.warnings

