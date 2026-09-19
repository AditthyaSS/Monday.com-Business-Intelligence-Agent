"""Normalise the raw Work Orders board snapshot into a clean DataFrame.

Input:  BoardSnapshot.df  (raw strings, header on row 0 after monday strips the blank first row)
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
    canon_billing_status,
    canon_execution_status,
    canon_invoice_status,
    canon_sector,
)

_WS = re.compile(r"\s+")


def _key(s: str) -> str:
    return _WS.sub(" ", s.strip()).casefold().rstrip(".,;:")


GST_RATE = 1.18  # verified: amount_incl == amount_excl * 1.18 on every row


_EXPECTED_COLS = {
    "wo_id":            ["serial #", "serial no", "sl no"],
    "deal_name":        ["name", "deal name masked", "deal name"],
    "client_code":      ["customer name code", "client code"],
    "nature":           ["nature of work", "nature"],
    "execution_status": ["execution status"],
    "po_date":          ["date of po/loi", "po date", "purchase order date"],
    "start":            ["probable start date", "start date", "start"],
    "end":              ["probable end date", "end date", "end"],
    "owner":            ["bd/kam personnel code", "owner code", "owner"],
    "sector":           ["sector"],
    "work_types":       ["type of work"],
    "software_platform":["is any skylark software platform part of the client deliverables in this deal?", "software platform"],
    "amount_excl":      ["amount in rupees (excl of gst) (masked)", "amount excl gst", "amount (excl gst)"],
    "amount_incl":      ["amount in rupees (incl of gst) (masked)", "amount incl gst", "amount (incl gst)"],
    "billed_excl":      ["billed value in rupees (excl of gst.) (masked)", "billed excl gst", "billed (excl gst)"],
    "billed_incl":      ["billed value in rupees (incl of gst.) (masked)", "billed incl gst", "billed (incl gst)"],
    "collected_incl":   ["collected amount in rupees (incl of gst.) (masked)", "collected (incl gst)", "collected incl gst"],
    "receivable":       ["amount receivable (masked)", "receivable", "ar"],
    "ar_priority":      ["ar priority account", "ar priority", "priority"],
    "invoice_status":   ["invoice status"],
    "billing_status":   ["billing status"],
    "wo_status":        ["wo status (billed)", "wo status"],
    "last_invoice_date":["last invoice date", "invoice date"],
}


def _match_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    raw_keys = {_key(c): c for c in df.columns}
    for candidate in candidates:
        if _key(candidate) in raw_keys:
            return raw_keys[_key(candidate)]
    return None


@dataclass
class WOQualityReport:
    board: str = "work_orders"
    rows_in: int = 0
    rows_used: int = 0
    billed_blank_as_zero: int = 0
    over_billed: int = 0
    negative_to_bill: int = 0
    collected_gt_billed: int = 0
    amount_missing: int = 0
    owner_missing: int = 0
    fully_empty_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summarise(self) -> list[str]:
        lines = [
            f"Board: {self.board} — {self.rows_in} rows in, {self.rows_used} used.",
        ]
        if self.billed_blank_as_zero:
            lines.append(f"{self.billed_blank_as_zero} rows have blank billed value — treated as 'not yet billed' (₹0).")
        if self.over_billed:
            lines.append(f"{self.over_billed} row(s) have billed > order amount (over-billing anomaly).")
        if self.negative_to_bill:
            lines.append(f"{self.negative_to_bill} row(s) have a negative still-to-bill (material anomaly).")
        if self.collected_gt_billed:
            lines.append(f"{self.collected_gt_billed} row(s) have collected > billed.")
        if self.amount_missing:
            lines.append(f"Order amount missing for {self.amount_missing} row(s).")
        if self.owner_missing:
            lines.append(f"Owner missing for {self.owner_missing} row(s).")
        if self.fully_empty_columns:
            lines.append(f"Fully empty columns (excluded): {', '.join(self.fully_empty_columns)}.")
        for w in self.warnings:
            lines.append(f"⚠ {w}")
        return lines


def gst_basis_values(
    amount_excl: float | None,
    amount_incl: float | None,
    billed_excl: float | None,
    billed_incl: float | None,
    collected_incl: float | None,
    receivable: float | None,
    basis: str = "excl",
) -> dict[str, float | None]:
    """Return money values normalised to a consistent GST basis.

    'excl': all amounts excl GST; collected/receivable (incl-only) divided by 1.18.
    'incl': all amounts incl GST; excl values multiplied by 1.18.
    """
    if basis == "excl":
        col = collected_incl / GST_RATE if collected_incl is not None else None
        rec = receivable / GST_RATE if receivable is not None else None
        return {
            "order_value": amount_excl,
            "billed": billed_excl,
            "collected": col,
            "receivable": rec,
            "to_bill": (
                (amount_excl - (billed_excl or 0.0))
                if amount_excl is not None
                else None
            ),
        }
    else:  # incl
        amt = amount_incl or (amount_excl * GST_RATE if amount_excl else None)
        bil = billed_incl or (billed_excl * GST_RATE if billed_excl else None)
        return {
            "order_value": amt,
            "billed": bil,
            "collected": collected_incl,
            "receivable": receivable,
            "to_bill": (
                (amt - (bil or 0.0)) if amt is not None else None
            ),
        }


def normalise_workorders(
    raw_df: pd.DataFrame,
    today: date | None = None,
    warnings_in: list[str] | None = None,
) -> tuple[pd.DataFrame, WOQualityReport]:
    """Normalise raw Work Orders snapshot to a clean DataFrame."""
    today = today or date.today()
    report = WOQualityReport(rows_in=len(raw_df))
    warnings: list[str] = list(warnings_in or [])

    # Detect fully-empty columns
    empty_cols = [c for c in raw_df.columns if raw_df[c].isna().all() or (raw_df[c].astype(str).str.strip() == "").all()]
    report.fully_empty_columns = empty_cols

    col_map: dict[str, str | None] = {}
    for target, candidates in _EXPECTED_COLS.items():
        found = _match_col(raw_df, candidates)
        col_map[target] = found
        if found is None:
            warnings.append(f"WO: expected column '{candidates[0]}' not found — treating as null.")

    def _get(row: Any, key: str) -> str | None:
        col = col_map.get(key)
        if col is None:
            return None
        val = row[col] if col in row.index else None
        return norm_text(val)

    rows: list[dict] = []
    for _, raw_row in raw_df.iterrows():
        billed_raw = _get(raw_row, "billed_excl")
        billed_incl_raw = _get(raw_row, "billed_incl")
        billed_excl = parse_number(billed_raw)
        billed_incl = parse_number(billed_incl_raw)
        amount_excl = parse_number(_get(raw_row, "amount_excl"))
        amount_incl = parse_number(_get(raw_row, "amount_incl"))
        collected_incl = parse_number(_get(raw_row, "collected_incl"))
        receivable = parse_number(_get(raw_row, "receivable"))

        flags: list[str] = []

        # Blank billed = not billed yet = 0 (A12)
        if billed_excl is None and billed_incl is None:
            billed_excl = 0.0
            billed_incl = 0.0
            flags.append("billed_blank_as_zero")

        # Over-billed
        if amount_excl is not None and billed_excl is not None and billed_excl > amount_excl + 1.0:
            flags.append("over_billed")

        # Negative to-bill (material)
        to_bill = (amount_excl - (billed_excl or 0)) if amount_excl is not None else None
        if to_bill is not None and to_bill < -1.0:
            flags.append("negative_to_bill")

        # Collected > billed
        if billed_incl is not None and collected_incl is not None and collected_incl > billed_incl + 1.0:
            flags.append("collected_gt_billed")

        if amount_excl is None:
            flags.append("amount_missing")

        owner = norm_text(_get(raw_row, "owner"))
        if not owner:
            flags.append("owner_missing")

        sector_raw = _get(raw_row, "sector")
        sector = canon_sector(sector_raw)

        po_date = parse_date(_get(raw_row, "po_date"))
        start = parse_date(_get(raw_row, "start"))
        end = parse_date(_get(raw_row, "end"))
        if start and end and end < start:
            flags.append("dates_inconsistent")

        work_types_raw = _get(raw_row, "work_types")
        work_types: list[str] = []
        if work_types_raw:
            work_types = sorted(set(p.strip() for p in work_types_raw.split(",") if p.strip()))

        ar_raw = _get(raw_row, "ar_priority")
        ar_priority = bool(ar_raw and ar_raw.strip().casefold() not in {"", "no", "false", "0", "nan"})

        client_code_raw = _get(raw_row, "client_code")

        rows.append({
            "wo_id": _get(raw_row, "wo_id"),
            "deal_name": _get(raw_row, "deal_name"),
            "client_code": client_code_raw,
            "client_id": extract_client_id(client_code_raw),
            "nature": _get(raw_row, "nature"),
            "execution_status": canon_execution_status(_get(raw_row, "execution_status")),
            "po_date": po_date,
            "start": start,
            "end": end,
            "owner": owner,
            "sector": sector,
            "work_types": work_types,
            "software_platform": _get(raw_row, "software_platform"),
            "amount_excl": amount_excl,
            "amount_incl": amount_incl,
            "billed_excl": billed_excl,
            "billed_incl": billed_incl,
            "collected_incl": collected_incl,
            "receivable": receivable,
            "to_bill_excl": to_bill,
            "ar_priority": ar_priority,
            "invoice_status": canon_invoice_status(_get(raw_row, "invoice_status")),
            "billing_status": canon_billing_status(_get(raw_row, "billing_status")),
            "wo_status": _get(raw_row, "wo_status"),
            "last_invoice_date": parse_date(_get(raw_row, "last_invoice_date")),
            "quality_flags": flags,
        })

    df = pd.DataFrame(rows)
    report.rows_used = len(df)
    report.billed_blank_as_zero = int(df["quality_flags"].apply(lambda f: "billed_blank_as_zero" in f).sum())
    report.over_billed = int(df["quality_flags"].apply(lambda f: "over_billed" in f).sum())
    report.negative_to_bill = int(df["quality_flags"].apply(lambda f: "negative_to_bill" in f).sum())
    report.collected_gt_billed = int(df["quality_flags"].apply(lambda f: "collected_gt_billed" in f).sum())
    report.amount_missing = int(df["quality_flags"].apply(lambda f: "amount_missing" in f).sum())
    report.owner_missing = int(df["quality_flags"].apply(lambda f: "owner_missing" in f).sum())
    report.warnings = warnings
    return df, report
