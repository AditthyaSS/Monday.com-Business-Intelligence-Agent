"""Vercel serverless entry point for /api/health with full diagnostic fallback."""
from __future__ import annotations

import sys
import os
import traceback

_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.normpath(os.path.join(_here, "..", "backend"))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

try:
    from app.main import app  # noqa: F401
except Exception as _exc:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def _diag(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend import failed",
                "detail": str(_exc),
                "traceback": traceback.format_exc(),
                "here": _here,
                "backend": _backend,
                "sys_path": sys.path[:6],
                "backend_exists": os.path.exists(_backend),
                "backend_contents": os.listdir(_backend) if os.path.isdir(_backend) else [],
            },
        )
