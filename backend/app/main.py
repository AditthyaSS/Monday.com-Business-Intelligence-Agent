"""FastAPI application: health, data-status, chat endpoints.

Implements the frozen API contract exactly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.config import get_settings
from app.sources.monday_api import MondayAPI, MondayAuthError, MondayUnavailable
from app.normalize.deals import normalise_deals, QualityReport
from app.normalize.workorders import normalise_workorders, WOQualityReport
from app.agent.loop import AgentResult, ToolExecutor, run_agent
from app.llm.gemini import GeminiProvider
from app.llm.base import LLMUnavailable

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="Skylark BI Agent",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory state (per process / per Vercel instance)
# ---------------------------------------------------------------------------

_monday = MondayAPI(settings)

# Normalised DataFrames cache
_deals_df: pd.DataFrame | None = None
_wo_df: pd.DataFrame | None = None
_deals_report: QualityReport | None = None
_wo_report: WOQualityReport | None = None
_loaded_at: float = 0.0
_deals_snap_warnings: list[str] = []
_wo_snap_warnings: list[str] = []
_from_cache: bool = False

# LLM call counter (daily budget)
_llm_calls_today: int = 0
_llm_call_date: date | None = None

# Per-IP rate limiting: sliding window per minute
_ip_windows: dict[str, deque] = defaultdict(lambda: deque())

# Answer cache: {hash -> (answer, timestamp)}
_answer_cache: dict[str, tuple[dict, float]] = {}


def _today() -> date:
    if settings.today_override:
        return date.fromisoformat(settings.today_override)
    return datetime.now(timezone.utc).date()


def _reset_daily_counter() -> None:
    global _llm_calls_today, _llm_call_date
    today = _today()
    if _llm_call_date != today:
        _llm_calls_today = 0
        _llm_call_date = today


def _inc_llm_calls(n: int) -> None:
    global _llm_calls_today
    _llm_calls_today += n


def _budget_ok() -> bool:
    _reset_daily_counter()
    return _llm_calls_today < settings.global_llm_calls_per_day


def _llm_disabled() -> bool:
    return os.environ.get("LLM_DISABLED", "0") == "1"


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str) -> None:
    """Sliding-window per-minute limiter (6 req/min)."""
    now = time.monotonic()
    window = _ip_windows[ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= 6:
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "rate_limited", "message": "Too many requests. Please wait a minute."},
                    "retry_after_seconds": 60},
        )
    window.append(now)


def _load_data(force: bool = False) -> None:
    """Load and normalise both boards into module-level DataFrames."""
    global _deals_df, _wo_df, _deals_report, _wo_report
    global _loaded_at, _deals_snap_warnings, _wo_snap_warnings, _from_cache

    now = time.monotonic()
    if not force and _deals_df is not None and (now - _loaded_at) < settings.cache_ttl_seconds:
        return

    today = _today()
    try:
        deals_snap = _monday.get_board("deals")
        _deals_snap_warnings = deals_snap.warnings
        _from_cache = deals_snap.from_cache
        _deals_df, _deals_report = normalise_deals(deals_snap.df, today=today, warnings_in=deals_snap.warnings)
    except Exception as exc:
        logger.error("Failed to load deals: %s", exc)
        if _deals_df is None:
            raise

    try:
        wo_snap = _monday.get_board("work_orders")
        _wo_snap_warnings = wo_snap.warnings
        _wo_df, _wo_report = normalise_workorders(wo_snap.df, today=today, warnings_in=wo_snap.warnings)
    except Exception as exc:
        logger.error("Failed to load work_orders: %s", exc)
        if _wo_df is None:
            raise

    _loaded_at = time.monotonic()


def _data_as_of() -> str | None:
    """Return the latest date seen across both boards."""
    candidates = []
    if _deals_df is not None:
        for col in ["tentative_close", "actual_close", "created"]:
            if col in _deals_df.columns:
                vals = _deals_df[col].dropna()
                if len(vals):
                    candidates.append(max(v for v in vals if isinstance(v, date)))
    if _wo_df is not None:
        for col in ["po_date", "last_invoice_date"]:
            if col in _wo_df.columns:
                vals = _wo_df[col].dropna()
                if len(vals):
                    candidates.append(max(v for v in vals if isinstance(v, date)))
    if candidates:
        return str(max(candidates))
    return None


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str = Field(max_length=1000)

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=12)


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _error_response(code: str, message: str, status: int, extra: dict | None = None) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status, content=body)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/data-status")
@app.get("/data-status")
def data_status() -> dict:
    _reset_daily_counter()
    try:
        _load_data()
    except Exception as exc:
        return {
            "deals_rows": 0,
            "work_orders_rows": 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data_as_of": None,
            "quality_lines": [str(exc)],
            "warnings": [str(exc)],
            "llm_calls_today": _llm_calls_today,
            "llm_daily_budget": settings.global_llm_calls_per_day,
            "degraded": True,
            "stale_cache": True,
        }

    dlines = _deals_report.summarise() if _deals_report else []
    wlines = _wo_report.summarise() if _wo_report else []
    quality_lines = dlines + wlines
    warnings = list(set(_deals_snap_warnings + _wo_snap_warnings))

    today = _today()
    dao = _data_as_of()
    stale = False
    if dao:
        try:
            d = date.fromisoformat(dao)
            stale = (today - d).days > 45
        except Exception:
            pass

    return {
        "deals_rows": len(_deals_df) if _deals_df is not None else 0,
        "work_orders_rows": len(_wo_df) if _wo_df is not None else 0,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data_as_of": dao,
        "quality_lines": quality_lines,
        "warnings": warnings,
        "llm_calls_today": _llm_calls_today,
        "llm_daily_budget": settings.global_llm_calls_per_day,
        "degraded": _llm_disabled() or not _budget_ok(),
        "stale_cache": _from_cache or stale,
    }


@app.post("/api/chat")
@app.post("/chat")
def chat(request: Request, body: ChatRequest) -> dict:
    ip = _get_client_ip(request)
    try:
        _check_rate_limit(ip)
    except HTTPException:
        raise

    try:
        _load_data()
    except MondayAuthError:
        return _error_response("monday_auth_error", "Can't read monday.com (credentials problem)", 502)
    except MondayUnavailable:
        return _error_response("monday_unavailable", "monday.com is unreachable and no cached data is available.", 503)
    except Exception as exc:
        logger.error("Data load error: %s", exc)
        return _error_response("data_load_error", "Could not load board data.", 503)

    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    question = messages[-1]["content"]
    history = messages[:-1]

    # Answer cache
    cache_key = hashlib.md5(json.dumps({"q": question, "dao": _data_as_of()}).encode()).hexdigest()
    if cache_key in _answer_cache:
        cached_answer, cached_at = _answer_cache[cache_key]
        if time.monotonic() - cached_at < settings.answer_cache_ttl_seconds:
            return cached_answer

    # Budget check
    _reset_daily_counter()
    use_degraded = _llm_disabled() or not _budget_ok()
    llm: GeminiProvider | None = None
    if not use_degraded:
        try:
            llm = GeminiProvider(settings)
        except Exception:
            use_degraded = True

    executor = ToolExecutor(
        deals_df=_deals_df,
        wo_df=_wo_df,
        deals_report=_deals_report,
        wo_report=_wo_report,
        today=_today(),
        fy_start_month=settings.fiscal_year_start_month,
    )

    try:
        result: AgentResult = run_agent(
            question=question,
            history=history,
            executor=executor,
            llm=llm,
            today=_today(),
            data_as_of=_data_as_of(),
            max_llm_calls=settings.max_llm_calls_per_question,
            llm_disabled=use_degraded,
        )
    except LLMUnavailable as exc:
        return _error_response("llm_unavailable", f"AI model is unavailable: {exc}", 503)
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        return _error_response("agent_error", "An error occurred processing your request.", 500)

    _inc_llm_calls(result.llm_calls)

    trace_out = [
        {
            "tool": t.tool,
            "params": t.params,
            "coverage": t.coverage,
            "caveats": t.caveats,
            "assumptions": t.assumptions,
        }
        for t in result.trace
    ]

    response_body = {
        "answer": result.answer,
        "trace": trace_out,
        "llm_calls": result.llm_calls,
        "model_used": result.model_used,
        "degraded": result.degraded,
    }

    # Cache answer
    _answer_cache[cache_key] = (response_body, time.monotonic())
    return response_body


# ---------------------------------------------------------------------------
# Serve frontend (if built)
# ---------------------------------------------------------------------------

_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
_dist = os.path.normpath(_dist)
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root() -> dict:
        return {"message": "Skylark BI Agent API. Frontend not built. Run: cd frontend && npm run build"}
