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
from fastapi.exceptions import RequestValidationError
from app.sources.monday_api import (
    MondayAPI,
    MondayAuthError,
    MondayRateLimitError,
    MondayServerError,
    MondayUnavailable,
)
from app.normalize.deals import normalise_deals, QualityReport
from app.normalize.workorders import normalise_workorders, WOQualityReport
from app.agent.loop import AgentResult, ToolExecutor, run_agent
from app.llm.gemini import GeminiProvider
from app.llm.base import (
    LLMAuthError,
    LLMQuotaExceeded,
    LLMTimeoutError,
    LLMUnavailable,
)

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
        retry_after = int(max(1, 60 - (now - window[0])))
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please wait a moment before trying again.",
                "user_message": "⚠️ You are sending requests too quickly. Please wait a moment before trying again.",
                "retry_after_seconds": retry_after,
            },
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
        _from_cache = True
        dao = _data_as_of() or "unknown"
        _deals_snap_warnings = [
            f"⚠️ Monday.com is temporarily unavailable. I couldn't refresh the latest board data. I'll use the most recent successfully cached data if available. Data last refreshed: {dao}."
        ]

    try:
        wo_snap = _monday.get_board("work_orders")
        _wo_snap_warnings = wo_snap.warnings
        if wo_snap.from_cache:
            _from_cache = True
        _wo_df, _wo_report = normalise_workorders(wo_snap.df, today=today, warnings_in=wo_snap.warnings)
    except Exception as exc:
        logger.error("Failed to load work_orders: %s", exc)
        if _wo_df is None:
            raise
        _from_cache = True
        dao = _data_as_of() or "unknown"
        _wo_snap_warnings = [
            f"⚠️ Monday.com is temporarily unavailable. I couldn't refresh the latest board data. I'll use the most recent successfully cached data if available. Data last refreshed: {dao}."
        ]

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
# Error helpers & Exception Handlers
# ---------------------------------------------------------------------------

def _error_response(
    code: str,
    message: str,
    user_message: str,
    status: int,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "user_message": user_message,
            "retry_after_seconds": retry_after_seconds,
        },
        "retry_after_seconds": retry_after_seconds,
    }
    headers: dict[str, str] = {}
    if retry_after_seconds is not None:
        headers["Retry-After"] = str(retry_after_seconds)
    return JSONResponse(status_code=status, content=content, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_response(
        code="INVALID_REQUEST",
        message="The request format was invalid.",
        user_message="Please enter a valid question (up to 1,000 characters).",
        status=400,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 429:
        retry_after = 60
        user_msg = "⚠️ You are sending requests too quickly. Please wait a moment before trying again."
        if isinstance(exc.detail, dict):
            retry_after = exc.detail.get("retry_after_seconds") or 60
            user_msg = exc.detail.get("user_message") or user_msg
        return _error_response(
            code="RATE_LIMITED",
            message="Rate limit reached.",
            user_message=user_msg,
            status=429,
            retry_after_seconds=retry_after,
        )
    detail_msg = exc.detail if isinstance(exc.detail, str) else "Request error."
    return _error_response(
        code="HTTP_ERROR",
        message=detail_msg,
        user_message=f"⚠️ {detail_msg}",
        status=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return _error_response(
        code="INTERNAL_ERROR",
        message="An unexpected server error occurred.",
        user_message="⚠️ Something went wrong while processing this request. Please try again.",
        status=500,
    )


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
def chat(request: Request, body: ChatRequest) -> Any:
    ip = _get_client_ip(request)
    try:
        _check_rate_limit(ip)
    except HTTPException:
        raise

    try:
        _load_data()
    except MondayAuthError:
        return _error_response(
            code="MONDAY_AUTH_ERROR",
            message="Monday.com credentials rejected.",
            user_message="⚠️ I couldn't access the Monday.com data. The connection or API credentials may need to be checked.",
            status=502,
        )
    except MondayRateLimitError as exc:
        return _error_response(
            code="MONDAY_RATE_LIMITED",
            message="Monday.com rate limit reached.",
            user_message="⚠️ Monday.com is temporarily rate-limiting requests. Please try again shortly.",
            status=429,
            retry_after_seconds=exc.retry_after or 60,
        )
    except MondayServerError:
        return _error_response(
            code="MONDAY_SERVER_ERROR",
            message="Monday.com service problem.",
            user_message="⚠️ Monday.com is experiencing a temporary service problem. Please try again shortly.",
            status=502,
        )
    except MondayUnavailable:
        return _error_response(
            code="MONDAY_UNAVAILABLE",
            message="Monday.com is currently unavailable.",
            user_message="⚠️ Monday.com is currently unavailable, and no previously cached data is available. Please try again later.",
            status=503,
        )
    except Exception as exc:
        logger.error("Data load error: %s", exc, exc_info=True)
        return _error_response(
            code="INTERNAL_ERROR",
            message="Could not load board data.",
            user_message="⚠️ Something went wrong while processing this request. Please try again.",
            status=500,
        )

    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    if not messages:
        return _error_response(
            code="INVALID_REQUEST",
            message="No messages provided.",
            user_message="Please enter a question to get started.",
            status=400,
        )

    question = messages[-1]["content"].strip()
    if not question:
        return _error_response(
            code="INVALID_REQUEST",
            message="Empty question.",
            user_message="Please enter a question or choose one of the suggested sample questions.",
            status=400,
        )

    history = messages[:-1]

    # Answer cache
    cache_key = hashlib.md5(json.dumps({"q": question, "dao": _data_as_of()}).encode()).hexdigest()
    if cache_key in _answer_cache:
        cached_answer, cached_at = _answer_cache[cache_key]
        if time.monotonic() - cached_at < settings.answer_cache_ttl_seconds:
            return cached_answer

    # Budget check & BYOK (Bring Your Own Key)
    _reset_daily_counter()
    custom_gemini_key = (request.headers.get("x-custom-gemini-key") or "").strip()
    has_byok = bool(custom_gemini_key)
    budget_ok = _budget_ok() or has_byok
    use_degraded = _llm_disabled() or not budget_ok
    llm: GeminiProvider | None = None
    fallback_prefix: str | None = None

    if _llm_disabled():
        use_degraded = True
    elif not budget_ok:
        use_degraded = True
        fallback_prefix = (
            "💤 My AI brain needs a short recharge. AI narration is unavailable for now, but I've still calculated the numbers for you."
        )
    else:
        try:
            llm = GeminiProvider(settings, api_key_override=custom_gemini_key if has_byok else None)
        except LLMAuthError:
            logger.warning("GeminiProvider init auth failure; falling back to degraded mode")
            use_degraded = True
            fallback_prefix = (
                "🔑 My AI connection needs a little attention. I'll keep working with the available data while the connection is fixed."
            )
        except Exception as exc:
            logger.warning("GeminiProvider init error: %s; falling back to degraded mode", exc)
            use_degraded = True
            fallback_prefix = (
                "🔌 My AI reasoning service is temporarily offline. I'm switching to computed results so the work can continue."
            )

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
            fallback_prefix=fallback_prefix,
        )
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        return _error_response(
            code="INTERNAL_ERROR",
            message="An error occurred processing your request.",
            user_message="⚠️ Something went wrong while processing this request. Please try again.",
            status=500,
        )

    if not has_byok:
        _inc_llm_calls(result.llm_calls)

    # If data came from cache, append notice and caveat
    dao = _data_as_of() or "unknown"
    if _from_cache:
        stale_notice = f"_⚠️ Note: Monday.com is currently unavailable. Using cached data (last refreshed: {dao})._"
        if "last refreshed" not in result.answer.lower() and "cached data" not in result.answer.lower():
            result.answer = f"{result.answer}\n\n{stale_notice}"

    trace_out = [
        {
            "tool": t.tool,
            "params": t.params,
            "coverage": t.coverage,
            "caveats": t.caveats + ([f"Using cached board data (data as of {dao})"] if _from_cache else []),
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
        "byok_active": has_byok,
        "llm_calls_today": _llm_calls_today,
        "llm_daily_budget": settings.global_llm_calls_per_day,
        "calls_remaining": max(0, settings.global_llm_calls_per_day - _llm_calls_today),
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
