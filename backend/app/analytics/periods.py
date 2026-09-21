"""Period resolution for Indian fiscal year (Apr-Mar).

`resolve_period` converts a period spec string to a (start, end, label) tuple.
Used by all analytics tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

PeriodSpec = Literal[
    "all_time", "this_quarter", "last_quarter", "this_fy", "last_fy", "previous_fy",
    "this_month", "last_month", "recent", "ytd"
]


@dataclass
class Period:
    spec: str
    start: date | None          # None means "no filter"
    end: date | None
    label: str


def _fy_quarter(today: date, fy_start: int = 4) -> tuple[int, int]:
    """Return (fiscal_year_end, quarter_number) for today.

    FY Apr-Mar: FY26-27 means Apr 2026 - Mar 2027.
    Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar.
    """
    month = today.month
    year = today.year
    # Shift month so April = 1
    shifted = (month - fy_start) % 12 + 1
    q = (shifted - 1) // 3 + 1  # 1-4
    # Fiscal year label: the ending calendar year
    if month >= fy_start:
        fy_end = year + 1
    else:
        fy_end = year
    return fy_end, q


def _quarter_bounds(fy_end: int, q: int, fy_start: int = 4) -> tuple[date, date]:
    """Return (first_day, last_day) for a given FY quarter."""
    # Q1 starts at fy_start month, FY begins at fy_end-1
    fy_begin_year = fy_end - 1
    start_month = fy_start + (q - 1) * 3
    start_year = fy_begin_year
    if start_month > 12:
        start_month -= 12
        start_year += 1
    start = date(start_year, start_month, 1)
    # End = day before start of next quarter
    end_month = start_month + 3
    end_year = start_year
    if end_month > 12:
        end_month -= 12
        end_year += 1
    end = date(end_year, end_month, 1) - timedelta(days=1)
    return start, end


def resolve_period(spec: str, today: date, fy_start_month: int = 4) -> Period:
    """Convert a period spec to a Period with concrete dates.

    spec options:
      all_time, this_quarter, last_quarter, this_fy, last_fy, previous_fy,
      this_month, last_month, recent, ytd
    """
    norm_spec = spec.strip().casefold().replace("-", "_").replace(" ", "_") if spec else "all_time"

    if norm_spec in ("all_time", "all", "overall", "total"):
        return Period(spec="all_time", start=None, end=None, label="All time")

    fy_end, q = _fy_quarter(today, fy_start_month)

    if norm_spec in ("this_quarter", "current_quarter"):
        start, end = _quarter_bounds(fy_end, q, fy_start_month)
        s_str = start.strftime("%d %b").lstrip("0")
        e_str = end.strftime("%d %b %Y").lstrip("0")
        label = f"Q{q} FY{fy_end-1}-{str(fy_end)[-2:]} ({s_str} to {e_str})"
        return Period(spec="this_quarter", start=start, end=end, label=label)

    if norm_spec in ("last_quarter", "previous_quarter", "prev_quarter"):
        prev_q = q - 1
        prev_fy = fy_end
        if prev_q == 0:
            prev_q = 4
            prev_fy -= 1
        start, end = _quarter_bounds(prev_fy, prev_q, fy_start_month)
        label = f"Q{prev_q} FY{prev_fy-1}-{str(prev_fy)[-2:]} ({start} to {end})"
        return Period(spec="last_quarter", start=start, end=end, label=label)

    if norm_spec in ("this_month", "current_month"):
        start = date(today.year, today.month, 1)
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        end = date(next_year, next_month, 1) - timedelta(days=1)
        label = f"{today.strftime('%B %Y')} ({start} to {end})"
        return Period(spec="this_month", start=start, end=end, label=label)

    if norm_spec in ("last_month", "previous_month", "prev_month"):
        prev_m = today.month - 1 if today.month > 1 else 12
        prev_y = today.year if today.month > 1 else today.year - 1
        start = date(prev_y, prev_m, 1)
        end = date(today.year, today.month, 1) - timedelta(days=1)
        label = f"{start.strftime('%B %Y')} ({start} to {end})"
        return Period(spec="last_month", start=start, end=end, label=label)

    if norm_spec in ("recent", "recently"):
        # Trailing 90 days
        start = today - timedelta(days=90)
        label = f"Recent ({start} to {today})"
        return Period(spec="recent", start=start, end=today, label=label)

    if norm_spec in ("this_fy", "current_fy", "this_fiscal_year", "current_fiscal_year"):
        fy_b = fy_end - 1
        start = date(fy_b, fy_start_month, 1)
        end = date(fy_end, fy_start_month, 1) - timedelta(days=1)
        return Period(spec="this_fy", start=start, end=end, label=f"FY{fy_b}-{str(fy_end)[-2:]}")

    if norm_spec in ("last_fy", "previous_fy", "prev_fy", "previous_fiscal_year", "last_fiscal_year"):
        fy_b = fy_end - 2
        start = date(fy_b, fy_start_month, 1)
        end = date(fy_end - 1, fy_start_month, 1) - timedelta(days=1)
        return Period(spec="last_fy", start=start, end=end, label=f"FY{fy_b}-{str(fy_end-1)[-2:]}")

    if norm_spec in ("ytd", "year_to_date"):
        fy_b = fy_end - 1
        start = date(fy_b, fy_start_month, 1)
        return Period(spec="ytd", start=start, end=today, label=f"FY{fy_b}-{str(fy_end)[-2:]} YTD")

    # Fallback to all_time with original spec recorded
    return Period(spec="all_time", start=None, end=None, label=f"All time (unrecognized period: {spec})")
