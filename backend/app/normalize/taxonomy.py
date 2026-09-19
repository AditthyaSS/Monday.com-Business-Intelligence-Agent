"""Sector/status taxonomy and synonym maps.

Single source of truth — fully unit-tested.  This module only defines
canonical labels, synonym lookups and validation helpers.  It never does I/O.
"""

from __future__ import annotations

from typing import Literal

# ---------------------------------------------------------------------------
# Deal status
# ---------------------------------------------------------------------------

DealStatus = Literal["Won", "Dead", "Open", "On Hold", "Unknown"]

_STATUS_MAP: dict[str, DealStatus] = {
    "won": "Won",
    "closed won": "Won",
    "dead": "Dead",
    "closed lost": "Dead",
    "lost": "Dead",
    "open": "Open",
    "in progress": "Open",
    "on hold": "On Hold",
    "hold": "On Hold",
}


def canon_deal_status(raw: str | None) -> DealStatus:
    """Normalise a raw deal-status string to a canonical value."""
    if not raw:
        return "Unknown"
    return _STATUS_MAP.get(raw.strip().casefold(), "Unknown")


# ---------------------------------------------------------------------------
# Deal stage
# ---------------------------------------------------------------------------

# Stages have a letter prefix (A-N) except "Project Completed" -> code P
_STAGE_PREFIX = {
    "a": "A. Lead Generated",
    "b": "B. Initial Discussion",
    "c": "C. Proposal Sent",
    "d": "D. Negotiation",
    "e": "E. Commercial Negotiation",
    "f": "F. Submitted",
    "g": "G. Project Won",
    "h": "H. Work Order Received",
    "i": "I. Invoiced",
    "j": "J. Payment Received",
    "k": "K. Project Completed",
    "l": "L. Project On Hold",
    "m": "M. Projects On Hold",
    "n": "N. Dead Deals",
    "p": "Project Completed",  # special
}


def canon_deal_stage(raw: str | None) -> tuple[str | None, str | None]:
    """Return (stage_code, stage_name) from a raw stage string.

    stage_code is the leading letter prefix, or 'P' for 'Project Completed'.
    Returns (None, None) if the input is blank.
    """
    if not raw:
        return None, None
    text = raw.strip()
    if text.casefold().startswith("project completed"):
        return "P", "Project Completed"
    # Extract leading letter
    code = text[0].upper() if text else None
    return code, text


# ---------------------------------------------------------------------------
# Deal stage conflict detection
# ---------------------------------------------------------------------------

# Stage codes that imply "still working" vs "closed"
_OPEN_STAGE_CODES = {"A", "B", "C", "D", "E", "F", "H", "L", "M"}
_WON_STAGE_CODES = {"G", "I", "J", "K", "P"}
_DEAD_STAGE_CODES = {"N"}


def status_stage_conflict(status: str, stage_code: str | None) -> bool:
    """Return True if status and stage_code are contradictory.

    Examples: Won + stage A = conflict; Dead + stage G = conflict.
    """
    if stage_code is None or status == "Unknown":
        return False
    if status == "Won" and stage_code in _OPEN_STAGE_CODES:
        return True
    if status == "Dead" and stage_code in _WON_STAGE_CODES:
        return True
    if status == "Open" and stage_code in {"K", "P", "N"}:
        return True
    return False


# ---------------------------------------------------------------------------
# Sector taxonomy
# ---------------------------------------------------------------------------

# Canonical sector labels
SECTORS = [
    "Mining",
    "Renewables",
    "Railways",
    "Powerline",
    "Construction",
    "Manufacturing",
    "Aviation",
    "Security & Surveillance",
    "Others",
    "DSP",
    "Tender",
    "Unspecified",
]

# Sectors that are NOT real business sectors (deal-type labels or blank)
FAKE_SECTORS = {"DSP", "Tender", "Unspecified"}


def sector_is_real(sector: str | None) -> bool:
    """Return True if the sector is a legitimate business sector."""
    return bool(sector) and sector not in FAKE_SECTORS


# Mapping from raw monday text -> canonical sector
_SECTOR_CANON: dict[str, str] = {
    "mining": "Mining",
    "renewables": "Renewables",
    "renewable": "Renewables",
    "solar": "Renewables",
    "wind": "Renewables",
    "railways": "Railways",
    "railway": "Railways",
    "rail": "Railways",
    "powerline": "Powerline",
    "power line": "Powerline",
    "power": "Powerline",
    "transmission": "Powerline",
    "construction": "Construction",
    "manufacturing": "Manufacturing",
    "aviation": "Aviation",
    "security and surveillance": "Security & Surveillance",
    "security & surveillance": "Security & Surveillance",
    "surveillance": "Security & Surveillance",
    "others": "Others",
    "other": "Others",
    "dsp": "DSP",
    "tender": "Tender",
}


def canon_sector(raw: str | None) -> str:
    """Map a raw sector string to its canonical label."""
    if not raw or str(raw).strip().casefold() in {"", "nan", "none", "null", "-", "n/a"}:
        return "Unspecified"
    key = str(raw).strip().casefold()
    return _SECTOR_CANON.get(key, raw.strip())  # keep unknown as-is


# ---------------------------------------------------------------------------
# USER phrase -> list of canonical sectors (for query routing)
# ---------------------------------------------------------------------------

# Maps user-provided phrases (lowercased) to a list of canonical sector labels.
SECTOR_SYNONYMS: dict[str, list[str]] = {
    "energy": ["Renewables", "Powerline"],
    "solar": ["Renewables"],
    "wind": ["Renewables"],
    "renewable": ["Renewables"],
    "renewables": ["Renewables"],
    "power": ["Powerline"],
    "powerline": ["Powerline"],
    "power line": ["Powerline"],
    "transmission": ["Powerline"],
    "rail": ["Railways"],
    "railway": ["Railways"],
    "railways": ["Railways"],
    "mine": ["Mining"],
    "mines": ["Mining"],
    "mining": ["Mining"],
    "construction": ["Construction"],
    "manufacturing": ["Manufacturing"],
    "aviation": ["Aviation"],
    "others": ["Others"],
}


def resolve_sector_phrase(phrase: str) -> list[str] | None:
    """Return canonical sector list for a user phrase, or None if unknown."""
    key = phrase.strip().casefold()
    if key in SECTOR_SYNONYMS:
        return SECTOR_SYNONYMS[key]
    # Try partial match
    for k, v in SECTOR_SYNONYMS.items():
        if k in key or key in k:
            return v
    return None


# ---------------------------------------------------------------------------
# Work-order status canonicalisation
# ---------------------------------------------------------------------------

_INVOICE_STATUS_MAP: dict[str, str] = {
    "fully billed": "Fully Billed",
    "partially billed": "Partially Billed",
    "not billed yet": "Not Billed Yet",
    "billed- visit 7": "Billed",
    "billed- visit 3": "Billed",
    "billed-visit 7": "Billed",
    "billed-visit 3": "Billed",
    "stuck": "Stuck",
}


def canon_invoice_status(raw: str | None) -> str | None:
    """Normalise invoice status strings."""
    if not raw:
        return None
    key = raw.strip().casefold()
    return _INVOICE_STATUS_MAP.get(key, raw.strip())


_BILLING_STATUS_MAP: dict[str, str] = {
    "billed": "Billed",
    "billed ": "Billed",
    "billed-": "Billed",
    "update required": "Update Required",
    "not billable": "Not Billable",
    "stuck": "Stuck",
}


def canon_billing_status(raw: str | None) -> str | None:
    """Normalise billing status strings, fixing 'BIlled' typos."""
    if not raw:
        return None
    key = raw.strip().casefold().rstrip("-").strip()
    if "billed" in key:
        return "Billed"
    return _BILLING_STATUS_MAP.get(key, raw.strip())


_EXECUTION_STATUS_MAP: dict[str, str] = {
    "completed": "Completed",
    "ongoing": "Ongoing",
    "executed until current month": "Executed Until Current Month",
    "not started": "Not Started",
    "pause / struck": "Paused",
    "paused": "Paused",
    "partial completed": "Partial Completed",
    "details pending from client": "Pending Client Details",
}


def canon_execution_status(raw: str | None) -> str | None:
    """Normalise execution status strings."""
    if not raw:
        return None
    key = raw.strip().casefold()
    return _EXECUTION_STATUS_MAP.get(key, raw.strip())
