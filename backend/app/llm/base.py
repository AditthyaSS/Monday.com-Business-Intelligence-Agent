"""LLM provider base types.

Neutral wrappers so the rest of the app never imports SDK types directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LLMMessage:
    """A single chat message sent to or received from the LLM."""
    role: str   # "user" | "assistant" | "system" | "tool"
    content: str


@dataclass
class ToolCall:
    """A request from the LLM to call a named tool with given args."""
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class LLMResponse:
    """What the LLM returned."""
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    model_used: str | None = None


class LLMUnavailable(Exception):
    """Base: LLM could not be reached. Always falls back to degraded mode."""


class LLMQuotaExceeded(LLMUnavailable):
    """Daily or per-minute quota exhausted (429 / RESOURCE_EXHAUSTED)."""


class LLMAuthError(LLMUnavailable):
    """API key invalid or project configuration problem."""


class LLMTimeoutError(LLMUnavailable):
    """Network timeout or server-side timeout from the LLM service."""


class LLMProvider(Protocol):
    """Read-only interface that the agent loop uses to call the model."""

    def generate(
        self,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """Call the model and return a response (may include tool calls)."""
