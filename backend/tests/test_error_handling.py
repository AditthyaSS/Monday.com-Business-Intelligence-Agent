"""Unit tests verifying user-facing error handling across external API failures."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _error_response
from app.sources.monday_api import (
    MondayAuthError,
    MondayRateLimitError,
    MondayServerError,
    MondayUnavailable,
)
from app.llm.base import (
    LLMAuthError,
    LLMQuotaExceeded,
    LLMTimeoutError,
    LLMUnavailable,
    LLMResponse,
)
from app.agent.loop import AgentResult, ToolExecutor, run_agent


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    import app.main as main_mod
    main_mod._ip_windows.clear()
    yield
    main_mod._ip_windows.clear()


# ---------------------------------------------------------------------------
# Test Case 1: Monday API unavailable without cache -> 503
# ---------------------------------------------------------------------------
def test_monday_unavailable_no_cache():
    with patch("app.main._load_data", side_effect=MondayUnavailable("network down")):
        res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "How is pipeline?"}]})
        assert res.status_code == 503
        data = res.json()
        assert data["error"]["code"] == "MONDAY_UNAVAILABLE"
        assert "⚠️ Monday.com is currently unavailable, and no previously cached data is available." in data["error"]["user_message"]
        # Ensure no technical dump or raw exception is exposed
        assert "network down" not in data["error"]["user_message"]


# ---------------------------------------------------------------------------
# Test Case 2: Monday API auth failure (401/403) -> 502
# ---------------------------------------------------------------------------
def test_monday_auth_failure():
    with patch("app.main._load_data", side_effect=MondayAuthError("Invalid token xyz")):
        res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "How is pipeline?"}]})
        assert res.status_code == 502
        data = res.json()
        assert data["error"]["code"] == "MONDAY_AUTH_ERROR"
        assert "⚠️ I couldn't access the Monday.com data." in data["error"]["user_message"]
        # Token or credential details must NEVER leak
        assert "xyz" not in str(data)
        assert "token" not in data["error"]["user_message"].lower()


# ---------------------------------------------------------------------------
# Test Case 3: Monday API rate limit (429) -> 429 with retry_after
# ---------------------------------------------------------------------------
def test_monday_rate_limit():
    with patch("app.main._load_data", side_effect=MondayRateLimitError("Rate limit", retry_after=45)):
        res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "How is pipeline?"}]})
        assert res.status_code == 429
        data = res.json()
        assert data["error"]["code"] == "MONDAY_RATE_LIMITED"
        assert "⚠️ Monday.com is temporarily rate-limiting requests." in data["error"]["user_message"]
        assert data["error"]["retry_after_seconds"] == 45
        assert res.headers.get("retry-after") == "45"


# ---------------------------------------------------------------------------
# Test Case 4: Monday API server error (5xx) -> 502
# ---------------------------------------------------------------------------
def test_monday_server_error():
    with patch("app.main._load_data", side_effect=MondayServerError("502 Bad Gateway")):
        res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "How is pipeline?"}]})
        assert res.status_code == 502
        data = res.json()
        assert data["error"]["code"] == "MONDAY_SERVER_ERROR"
        assert "⚠️ Monday.com is experiencing a temporary service problem." in data["error"]["user_message"]


# ---------------------------------------------------------------------------
# Test Case 5: Gemini Quota Exceeded (429) -> Fall back to degraded calculation
# ---------------------------------------------------------------------------
def test_gemini_quota_exceeded_fallback():
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = LLMQuotaExceeded("Quota 429")

    executor = MagicMock(spec=ToolExecutor)
    executor.run.return_value = {
        "display": {"summary": "Total pipeline value: INR 10 Cr across 15 deals."},
        "caveats": ["2 deals missing value"],
        "assumptions_used": [],
        "data_as_of": "2026-09-15",
    }

    result = run_agent(
        question="How is our open pipeline looking?",
        history=[],
        executor=executor,
        llm=mock_llm,
        today=date(2026, 9, 19),
        data_as_of="2026-09-15",
    )

    assert result.degraded is True
    assert "⚠️ AI narration is temporarily unavailable because the AI service has reached its current usage limit." in result.answer
    assert "Total pipeline value: INR 10 Cr" in result.answer


# ---------------------------------------------------------------------------
# Test Case 6: Gemini Auth/Config Error -> Fall back to degraded calculation
# ---------------------------------------------------------------------------
def test_gemini_auth_error_fallback():
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = LLMAuthError("Invalid API key")

    executor = MagicMock(spec=ToolExecutor)
    executor.run.return_value = {
        "display": {"summary": "Work order billing: INR 5 Cr collected."},
        "caveats": [],
        "assumptions_used": [],
        "data_as_of": "2026-09-15",
    }

    result = run_agent(
        question="How much billed vs collected on work orders?",
        history=[],
        executor=executor,
        llm=mock_llm,
        today=date(2026, 9, 19),
        data_as_of="2026-09-15",
    )

    assert result.degraded is True
    assert "⚠️ AI narration is unavailable because the AI service connection needs attention." in result.answer
    assert "Work order billing: INR 5 Cr collected." in result.answer
    # No raw key error
    assert "Invalid API key" not in result.answer


# ---------------------------------------------------------------------------
# Test Case 7: Gemini Timeout / Unavailable -> Fall back to degraded calculation
# ---------------------------------------------------------------------------
def test_gemini_timeout_fallback():
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = LLMTimeoutError("Deadline exceeded")

    executor = MagicMock(spec=ToolExecutor)
    executor.run.return_value = {
        "display": {"summary": "Sector overview: Mining leads with 5 deals."},
        "caveats": [],
        "assumptions_used": [],
        "data_as_of": "2026-09-15",
    }

    result = run_agent(
        question="Give me a sector overview",
        history=[],
        executor=executor,
        llm=mock_llm,
        today=date(2026, 9, 19),
        data_as_of="2026-09-15",
    )

    assert result.degraded is True
    assert "⚠️ AI narration is temporarily unavailable." in result.answer
    assert "Sector overview: Mining leads with 5 deals." in result.answer


# ---------------------------------------------------------------------------
# Test Case 8: Invalid Request (Empty / Whitespace) -> 400
# ---------------------------------------------------------------------------
def test_invalid_empty_request():
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "   "}]})
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert "Please enter a question" in data["error"]["user_message"]


# ---------------------------------------------------------------------------
# Test Case 9: Unexpected Internal Error -> 500 without stack trace dump
# ---------------------------------------------------------------------------
def test_unexpected_internal_error():
    with patch("app.main.run_agent", side_effect=ZeroDivisionError("secret internal division bug")):
        with patch("app.main._load_data", return_value=None):
            res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Pipeline check"}]})
            assert res.status_code == 500
            data = res.json()
            assert data["error"]["code"] == "INTERNAL_ERROR"
            assert "⚠️ Something went wrong while processing this request. Please try again." in data["error"]["user_message"]
            # NEVER expose the internal stack trace or bug message
            assert "ZeroDivisionError" not in str(data)
            assert "secret internal division bug" not in str(data)


# ---------------------------------------------------------------------------
# Test Case 10: Stale cache fallback notice
# ---------------------------------------------------------------------------
def test_stale_cache_notice():
    import app.main as main_mod

    # Pretend Monday failed but cached DataFrames exist
    main_mod._from_cache = True
    fake_result = AgentResult(
        answer="Pipeline has 12 deals.",
        trace=[],
        llm_calls=0,
        model_used=None,
        degraded=True,
    )
    with patch("app.main.run_agent", return_value=fake_result):
        with patch("app.main._load_data", return_value=None):
            with patch("app.main._data_as_of", return_value="2026-08-01"):
                res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Pipeline?"}]})
                assert res.status_code == 200
                data = res.json()
                assert "⚠️ Note: Monday.com is currently unavailable. Using cached data (last refreshed: 2026-08-01)." in data["answer"]
    main_mod._from_cache = False
