"""Vercel serverless entry point."""

import sys
import os

# Vercel runs functions from the repo root. Add backend/ to path.
_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_here, "..", "backend")
_backend = os.path.normpath(_backend)

if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.main import app  # noqa: F401
