"""Google Gemini implementation of LLMProvider.

Uses google-genai SDK with MANUAL function calling (automatic calling DISABLED).
Never sets temperature/top_p/top_k (deprecated on free tier).
"""

from __future__ import annotations

import random
import time
import logging
from typing import Any

import google.genai as genai
from google.genai import types as gtypes

from app.llm.base import (
    LLMAuthError, LLMMessage, LLMQuotaExceeded, LLMResponse,
    LLMTimeoutError, LLMUnavailable, ToolCall,
)
from app.config import Settings

logger = logging.getLogger(__name__)

# FunctionCallingMode enum value for manual control
_FC_NONE_AUTO = "ANY"  # any declared function may be called; we cap in the loop


def _build_tool(schema: dict[str, Any]) -> gtypes.Tool:
    """Convert our simple tool schema dict to a google-genai Tool object."""
    decls = []
    for fn in schema:
        decls.append(
            gtypes.FunctionDeclaration(
                name=fn["name"],
                description=fn.get("description", ""),
                parameters=fn.get("parameters", {}),
            )
        )
    return gtypes.Tool(function_declarations=decls)


def _to_sdk_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert our neutral messages to SDK-compatible content dicts."""
    result = []
    for m in messages:
        if m.role == "tool":
            # tool result goes as a function response part
            result.append({
                "role": "user",
                "parts": [{"function_response": {"name": "tool_result", "response": {"result": m.content}}}],
            })
        else:
            sdk_role = "model" if m.role == "assistant" else "user"
            result.append({"role": sdk_role, "parts": [{"text": m.content}]})
    return result


class GeminiProvider:
    """Wraps google-genai Client for use by the agent loop."""

    def __init__(self, settings: Settings, sleep=time.sleep, random_fn=random.random, api_key_override: str | None = None) -> None:
        self.settings = settings
        key = (api_key_override or "").strip() or settings.gemini_api_key
        self._client = genai.Client(api_key=key)
        self._sleep = sleep
        self._random = random_fn
        self._model = settings.gemini_model
        self._fallback = settings.gemini_fallback_model

    def generate(
        self,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """Call Gemini with manual function calling, retry on 429, fallback model."""
        sdk_messages = _to_sdk_messages(messages)
        sdk_tool = _build_tool(tools) if tools else None

        config_kwargs: dict[str, Any] = {
            "system_instruction": system,
            "tool_config": gtypes.ToolConfig(
                function_calling_config=gtypes.FunctionCallingConfig(mode="ANY")
            ) if sdk_tool else None,
            "automatic_function_calling": gtypes.AutomaticFunctionCallingConfig(disable=True),
        }
        if sdk_tool:
            config_kwargs["tools"] = [sdk_tool]

        last_quota_exc: Exception | None = None
        for model in [self._model] + ([self._fallback] if self._fallback else []):
            for attempt in range(2):  # 1 retry per model
                try:
                    response = self._client.models.generate_content(
                        model=model,
                        contents=sdk_messages,
                        config=gtypes.GenerateContentConfig(
                            **{k: v for k, v in config_kwargs.items() if v is not None}
                        ),
                    )
                    return self._parse_response(response, model)
                except Exception as exc:
                    err_lower = str(exc).lower()

                    # Auth / config errors — no point retrying
                    if any(w in err_lower for w in ("api_key", "api key", "invalid_argument",
                                                    "permission_denied", "unauthenticated")):
                        logger.error("Gemini auth error (model=%s): redacted", model)
                        raise LLMAuthError("Gemini authentication failed") from None

                    # Quota / rate limit — retry with back-off, then try fallback
                    if any(w in err_lower for w in ("429", "quota", "resource_exhausted",
                                                    "rate_limit", "rate limit")):
                        last_quota_exc = exc
                        if attempt == 0:
                            wait = 5.0 + self._random() * 5.0
                            logger.warning("Gemini 429 on %s; retrying in %.1fs", model, wait)
                            self._sleep(wait)
                            continue
                        logger.warning("Gemini 429 exhausted on %s; trying fallback", model)
                        break  # try next model

                    # Timeout
                    if any(w in err_lower for w in ("timeout", "deadline")):
                        logger.warning("Gemini timeout on %s (attempt %d)", model, attempt)
                        raise LLMTimeoutError("Gemini request timed out") from None

                    # Any other error — do not expose internal details
                    logger.error("Gemini unexpected error on %s: redacted", model)
                    raise LLMUnavailable("Gemini is temporarily unavailable") from None

        raise LLMQuotaExceeded("Gemini daily quota exhausted") from last_quota_exc

    @staticmethod
    def _parse_response(response: Any, model: str) -> LLMResponse:
        """Extract text and function calls from a Gemini response."""
        text = None
        tool_calls: list[ToolCall] = []

        candidate = response.candidates[0] if response.candidates else None
        if candidate is None:
            return LLMResponse(text="", tool_calls=[], model_used=model)

        for part in (candidate.content.parts or []):
            if hasattr(part, "text") and part.text:
                text = (text or "") + part.text
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                args = dict(fc.args) if fc.args else {}
                tool_calls.append(ToolCall(id=fc.name, name=fc.name, args=args))

        return LLMResponse(text=text, tool_calls=tool_calls, model_used=model)
