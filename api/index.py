"""Vercel serverless entry point.

Adds backend/ to sys.path and exports the FastAPI app as `app`.
No startup work, no threads, no file writes outside /tmp.
"""

import sys
import os

# Make the backend package importable in Vercel's serverless environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: F401  (Vercel picks up `app` by name)
