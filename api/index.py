"""Vercel serverless entry point — with startup diagnostics."""
from __future__ import annotations

import sys
import os
import traceback

# Add backend/ to Python path
_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.normpath(os.path.join(_here, "..", "backend"))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

try:
    from app.main import app  # noqa: F401
except Exception as _exc:
    # Surface the import error as a working FastAPI app so we can read it
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def _import_error(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Import failed",
                "detail": str(_exc),
                "traceback": traceback.format_exc(),
                "sys_path": sys.path[:5],
                "python": sys.version,
            },
        )
