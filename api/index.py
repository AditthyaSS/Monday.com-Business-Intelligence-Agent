"""Vercel serverless entry point."""
from __future__ import annotations

import sys
import os

# Add backend/ to Python path so `import app.main` works
_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.normpath(os.path.join(_here, "..", "backend"))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.main import app  # noqa: F401  — Vercel picks up `app` by name
