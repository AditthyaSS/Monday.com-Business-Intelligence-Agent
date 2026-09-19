"""Vercel serverless entry point for /api/data-status."""
from __future__ import annotations
import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from index import app  # noqa: F401
