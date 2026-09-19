"""Normalise the raw Deals board snapshot into a clean DataFrame + QualityReport.

Input:  BoardSnapshot.df  (columns = monday column titles, raw strings)
Output: (clean_df, QualityReport)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from app.normalize.common import (
    client_id as extract_client_id,
    norm_text,
    parse_date,
    parse_number,
)
from app.normalize.taxonomy import (
    canon_deal_stage,
    canon_deal_status,
    canon_sector,
    sector_is_real,
    status_stage_conflict,
)

# ---------------------------------------------------------------------------
# Column header matching (tolerant: casefold + strip + collapse whitespace)
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")


def _key(s: str) -> str:
    return _WS.sub(" ", s.strip()).casefold().rstrip(".,;:")


_EXPECTED_COLS = {
    "deal_name":       ["deal name", "deal name masked", "name"],
    "owner":           ["owner code", "owner"],
    "client_code":     ["client code"],
    "status":          ["deal status"],
    "actual_close":    ["close date (a)", "close date", "actual close date"],
    "probability":     ["closure probability"],
    "value_inr":       ["masked deal value", "deal value"],
    "tentative_close": ["tentative close date"],
    "stage":           ["deal stage"],
    "product":         ["product deal"],
    "sector":          ["sector/service", "sector"],
    "created":         ["created date", "created"],
}


def _match_col(df: pd.DataFrame, key: str, candidates: list[str]) -> str | None:
    """Return the first matching df column, or None."""
    raw_keys = {_key(c): c for c in df.columns}
    for candidate in candidates:
        if _key(candidate) in raw_keys:
            return raw_keys[_key(candidate)]
    return None


# ---------------------------------------------------------------------------
# QualityReport
# ---------------------------------------------------------------------------

@dataclass
class QualityReport:
    """Per-board quality metrics reported alongside every answer."""

    board: str
    rows_in: int = 0
    rows_used: int = 0
    junk_excluded: int = 0
    duplicate_excluded: int = 0
    null_status_excluded: int = 0
    missing_value: int = 0
    missing_owner: int = 0
    status_stage_conflicts: int = 0
    stale_close_dates: int = 0
    warnings: list[str] = field(default_factory=list)

    def summarise(self) -> list[str]:
        """Return 5-8 plain-English lines suitable for an analyst caveat block."""
        lines = [
            f"Board: {self.board} — {self.rows_in} rows in, {self.rows_used} used after exclusions.",
        ]
        if self.junk_excluded:
            lines.append(f"Excluded {self.junk_excluded} junk row(s) (header text pasted into data).")
        if self.duplicate_excluded:
            lines.append(f"Excluded {self.duplicate_excluded} exact-duplicate row(s).")
        if self.null_status_excluded:
            lines.append(f"Excluded {self.null_status_excluded} row(s) with no status, value, or owner.")
        if self.missing_value:
            lines.append(f"Deal value missing for {self.missing_value} of {self.rows_used} rows — excluded from totals.")
        if self.missing_owner:
            lines.append(f"Owner missing for {self.missing_owner} row(s).")
        if self.status_stage_conflicts:
            lines.append(f"{self.status_stage_conflicts} rows have a conflict between Deal Status and Deal Stage (status wins).")
        if self.stale_close_dates:
            lines.append(f"{self.stale_close_dates} open deal(s) have a Tentative Close Date in the past.")
        for w in self.warnings:
            lines.append(f"⚠ {w}")
        return lines


# ---------------------------------------------------------------------------
# Main normalisation function
# ---------------------------------------------------------------------------

def normalise_deals(
    raw_df: pd.DataFrame,
    today: date | None = None,
    warnings_in: list[str] | None = None,
) -> tuple[pd.DataFrame, QualityReport]:
    """Normalise the raw Deals snapshot into a clean DataFrame.

    Returns (clean_df, report).  Never raises on missing columns — those
    become all-null columns with a warning.
    """
    today = today or date.today()
    report = QualityReport(board="deals", rows_in=len(raw_df))
    warnings: list[str] = list(warnings_in or [])

    # Map expected columns
    col_map: dict[str, str | None] = {}
    for target, candidates in _EXPECTED_COLS.items():
        found = _match_col(raw_df, target, candidates)
        col_map[target] = found
        if found is None:
            warnings.append(f"Deals: expected column '{candidates[0]}' not found — treating as null.")

    def _get(row: Any, key: str) -> str | None:
        col = col_map.get(key)
        if col is None:
            return None
        val = row[col] if col in row.index else None
        return norm_text(val)

    rows: list[dict] = []
    for _, raw_row in raw_df.iterrows():
        deal_name = _get(raw_row, "deal_name")
        status_raw = _get(raw_row, "status")
        value_raw = _get(raw_row, "value_inr")
        owner_raw = _get(raw_row, "owner")

        # Junk row: cell text equals its column header
        is_junk = False
        for target, candidates in _EXPECTED_COLS.items():
            col = col_map.get(target)
            if col is None:
                continue
            cell_val = norm_text(raw_row[col]) if col in raw_row.index else None
            if cell_val and any(_key(cell_val) == _key(c) for c in candidates):
                is_junk = True
                break
        # Also junk if no status AND no value AND no owner
        if not is_junk and not status_raw and not value_raw and not owner_raw:
            is_junk = True

        flags: list[str] = []
        if is_junk:
            flags.append("junk_row")

        status = canon_deal_status(status_raw)
        if status == "Unknown" and not is_junk:
            flags.append("null_status")

        stage_raw = _get(raw_row, "stage")
        stage_code, stage_name = canon_deal_stage(stage_raw)

        if not is_junk and status_stage_conflict(status, stage_code):
            flags.append("status_stage_conflict")

        value = parse_number(value_raw)
        if value is None and not is_junk:
            flags.append("value_missing")

        owner = norm_text(owner_raw)
        if not owner and not is_junk:
            flags.append("owner_missing")

        tentative_raw = _get(raw_row, "tentative_close")
        tentative_close = parse_date(tentative_raw)
        if status == "Open" and tentative_close and tentative_close < today:
            flags.append("open_close_date_past")

        actual_close = parse_date(_get(raw_row, "actual_close"))
        created = parse_date(_get(raw_row, "created"))

        if created and actual_close and actual_close < created:
            flags.append("close_before_created")

        client_code_raw = _get(raw_row, "client_code")
        cid = extract_client_id(client_code_raw)
        sector_raw = _get(raw_row, "sector")
        sector = canon_sector(sector_raw)
        s_real = sector_is_real(sector)
        if not s_real and not is_junk:
            flags.append("sector_not_real")

        rows.append({
            "deal_name": deal_name,
            "owner": owner,
            "client_code": client_code_raw,
            "client_id": cid,
            "status": status,
            "stage_code": stage_code,
            "stage_name": stage_name,
            "probability": _get(raw_row, "probability"),
            "value_inr": value,
            "tentative_close": tentative_close,
            "actual_close": actual_close,
            "created": created,
            "product": _get(raw_row, "product"),
            "sector": sector,
            "sector_is_real": s_real,
            "quality_flags": flags,
        })

    df = pd.DataFrame(rows)

    # Mark exact duplicates (same values on all original key columns; keep first)
    key_cols = ["deal_name", "owner", "client_code", "status", "stage_name", "value_inr"]
    existing = [c for c in key_cols if c in df.columns]
    if existing:
        dup_mask = df.duplicated(subset=existing, keep="first")
        for idx in df[dup_mask].index:
            df.at[idx, "quality_flags"] = df.at[idx, "quality_flags"] + ["exact_duplicate"]

    # Compute stats
    junk_mask = df["quality_flags"].apply(lambda f: "junk_row" in f)
    dup_mask2 = df["quality_flags"].apply(lambda f: "exact_duplicate" in f)
    null_st_mask = df["quality_flags"].apply(lambda f: "null_status" in f)
    excluded_mask = junk_mask | dup_mask2

    report.junk_excluded = int(junk_mask.sum())
    report.duplicate_excluded = int(dup_mask2.sum())
    report.null_status_excluded = int(null_st_mask.sum())
    report.rows_used = int((~excluded_mask).sum())

    clean = df[~excluded_mask].copy()
    report.missing_value = int(clean["value_inr"].isna().sum())
    report.missing_owner = int((clean["owner"].isna()).sum())
    report.status_stage_conflicts = int(
        clean["quality_flags"].apply(lambda f: "status_stage_conflict" in f).sum()
    )
    report.stale_close_dates = int(
        clean["quality_flags"].apply(lambda f: "open_close_date_past" in f).sum()
    )
    report.warnings = warnings
    return clean, report
