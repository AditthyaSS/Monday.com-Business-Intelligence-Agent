"""Common parsers: numbers, dates, text normalisation and INR formatting.

These are pure functions (no I/O) that convert messy raw strings to typed
Python values.  Each returns None on failure so the caller can count parse
errors without crashing.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

_MULTIPLIERS = {"cr": 1e7, "crore": 1e7, "l": 1e5, "lac": 1e5, "lakh": 1e5, "k": 1e3}
_STRIP_CURRENCY = re.compile(r"[₹\s]|rs\.?|inr", re.IGNORECASE)
_BRACKETS = re.compile(r"^\((.+)\)$")
_MISSING_WORDS = {"", "-", "n/a", "na", "nil", "none", "null", "nan"}


def parse_number(raw: Any, *, allow_suffix: bool = True) -> float | None:
    """Parse a messy number string to a float, or None if missing/invalid.

    Handles: commas, Rs/₹/INR prefix, (brackets) as negative, Cr/L/K suffixes.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if text.casefold() in _MISSING_WORDS:
        return None
    # Strip currency symbols
    text = _STRIP_CURRENCY.sub("", text).strip()
    if not text:
        return None
    # Handle (1,000) = negative
    m = _BRACKETS.match(text)
    negative = m is not None
    if m:
        text = m.group(1)
    # Detect multiplier suffix
    multiplier = 1.0
    if allow_suffix:
        for key, mult in sorted(_MULTIPLIERS.items(), key=lambda kv: -len(kv[0])):
            if text.casefold().endswith(key):
                multiplier = mult
                text = text[: -len(key)].strip()
                break
    # Remove commas (Indian or Western grouping)
    text = text.replace(",", "")
    try:
        value = float(text) * multiplier
    except ValueError:
        return None
    return -value if negative else value


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FMTS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d %b %Y",
    "%d %B %Y",
    "%b-%y",
    "%B-%y",
    "%b %Y",
    "%B %Y",
]

# Excel serial: days since 1900-01-00 (with Lotus 1-2-3 bug on 1900-02-29)
_EXCEL_ORIGIN_DAYS = 25569  # offset from 1900-01-00 to 1970-01-01
_EXCEL_VALID_RANGE = (20000, 60000)


def parse_date(raw: Any) -> date | None:
    """Parse a date string to a Python date, returning None if invalid.

    Tries ISO first, then day-first formats, then Excel serial numbers.
    Rejects impossible dates (e.g. month=13).
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if text.casefold() in _MISSING_WORDS:
        return None
    # ISO datetime or date (may include time part)
    if "T" in text or re.match(r"^\d{4}-\d{2}-\d{2}", text):
        try:
            return datetime.fromisoformat(text[:10]).date()
        except ValueError:
            pass
    # Named formats
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Excel serial number
    try:
        serial = float(text)
        if _EXCEL_VALID_RANGE[0] <= serial <= _EXCEL_VALID_RANGE[1]:
            import datetime as dt

            origin = dt.date(1970, 1, 1)
            delta_days = int(serial) - _EXCEL_ORIGIN_DAYS
            return origin + dt.timedelta(days=delta_days)
    except (ValueError, TypeError, OverflowError):
        pass
    return None


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

_WHITESPACE = re.compile(r"\s+")
_NULL_TEXTS = {"", "nan", "none", "null", "-", "n/a", "na", "nil"}


def norm_text(raw: Any) -> str | None:
    """Strip and collapse whitespace; treat blank/null-like strings as None."""
    if raw is None:
        return None
    text = _WHITESPACE.sub(" ", str(raw)).strip()
    if text.casefold() in _NULL_TEXTS:
        return None
    return text


def norm_key(raw: Any) -> str:
    """Casefold + strip + collapse whitespace for fuzzy matching."""
    if raw is None:
        return ""
    return _WHITESPACE.sub(" ", str(raw)).strip().casefold()


# ---------------------------------------------------------------------------
# Client ID extraction (for cross-board matching)
# ---------------------------------------------------------------------------

_DIGITS = re.compile(r"\d+")


def client_id(raw: Any) -> int | None:
    """Extract the numeric part of a client code for cross-board matching.

    'COMPANY089' and 'WOCOMPANY_002' both yield 89 and 2 respectively.
    Strips leading zeros so 089 == 89.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    matches = _DIGITS.findall(text)
    if not matches:
        return None
    try:
        return int(matches[-1])  # last numeric segment
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# INR formatting
# ---------------------------------------------------------------------------

def fmt_inr(x: float | None) -> str:
    """Format a rupee amount with Indian conventions.

    >= 1 Cr  => '₹12.4 Cr'
    >= 1 L   => '₹8.2 L'
    else     => '₹45,000' (Indian grouping: 2-2-3)
    Returns 'n/a' for None/NaN.
    """
    import math

    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if x >= 1e7:
        return f"₹{x / 1e7:.1f} Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:.1f} L"
    # Indian grouping: last 3 digits, then 2s
    sign = "-" if x < 0 else ""
    ix = int(abs(x))
    s = str(ix)
    if len(s) <= 3:
        return f"{sign}₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    formatted = ",".join(reversed(groups)) + "," + last3
    return f"{sign}₹{formatted}"
