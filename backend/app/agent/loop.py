"""Agent loop: call LLM -> execute tools -> call LLM again with results.

Hard cap: MAX_LLM_CALLS_PER_QUESTION (default 3).
Degraded mode: when LLM is unavailable or disabled, keyword-routes to tools.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from app.analytics import tools as analytics
from app.analytics.periods import resolve_period
from app.llm.base import LLMMessage, LLMProvider, LLMUnavailable, ToolCall
from app.normalize.common import fmt_inr
from app.normalize.deals import QualityReport
from app.normalize.workorders import WOQualityReport
from app.normalize.taxonomy import resolve_sector_phrase
from app.agent.prompts import TOOL_DECLARATIONS, build_system_prompt

logger = logging.getLogger(__name__)


@dataclass
class TraceItem:
    tool: str
    params: dict[str, Any]
    result_summary: str
    coverage: list[dict[str, Any]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    answer: str
    trace: list[TraceItem]
    llm_calls: int
    model_used: str | None
    degraded: bool


# ---------------------------------------------------------------------------
# Tool execution (the agent loop calls these, never the LLM directly)
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Runs analytics tools against the current normalised data."""

    def __init__(
        self,
        deals_df: pd.DataFrame,
        wo_df: pd.DataFrame,
        deals_report: QualityReport,
        wo_report: WOQualityReport,
        today: date,
        fy_start_month: int = 4,
    ) -> None:
        self.deals_df = deals_df
        self.wo_df = wo_df
        self.deals_report = deals_report
        self.wo_report = wo_report
        self.today = today
        self.fy_start = fy_start_month

    def _resolve_sector(self, sector_phrase: str | None) -> list[str] | str | None:
        """Resolve a user sector phrase to canonical sector(s)."""
        if not sector_phrase:
            return None
        resolved = resolve_sector_phrase(sector_phrase)
        if resolved:
            return resolved  # list of canonical sectors
        return sector_phrase  # pass through as-is; tool will filter

    def run(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call by name and return a ToolResult."""
        sector_raw = args.get("sector")
        sector = self._resolve_sector(sector_raw)
        period = args.get("period", "all_time")
        gst = args.get("gst_basis", "excl")

        if name == "pipeline_summary":
            return analytics.pipeline_summary(
                self.deals_df, self.today,
                period_spec=period, sector=sector,
                owner=args.get("owner"),
                fy_start_month=self.fy_start,
            )
        if name == "work_order_summary":
            return analytics.work_order_summary(
                self.wo_df, self.today,
                period_spec=period, sector=sector,
                gst_basis=gst, fy_start_month=self.fy_start,
            )
        if name == "sector_overview":
            return analytics.sector_overview(
                self.deals_df, self.wo_df, self.today, gst_basis=gst
            )
        if name == "data_quality_report":
            return analytics.data_quality_report(
                self.deals_report.summarise(), self.wo_report.summarise()
            )
        if name == "leadership_brief":
            return analytics.leadership_brief(
                self.deals_df, self.wo_df, self.today,
                gst_basis=gst, fy_start_month=self.fy_start,
                deals_report_lines=self.deals_report.summarise(),
                wo_report_lines=self.wo_report.summarise(),
            )
        return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Degraded-mode keyword router
# ---------------------------------------------------------------------------

_KEYWORD_ROUTES: list[tuple[list[str], str, dict]] = [
    (["pipeline", "open deal", "opportunity", "opportunities"], "pipeline_summary", {}),
    (["win rate", "won", "dead", "lost", "close rate"], "pipeline_summary", {}),
    (["billed", "collected", "receivable", "billing", "invoice", "work order"], "work_order_summary", {}),
    (["sector", "sector overview", "cross board", "cross-board"], "sector_overview", {}),
    (["leadership", "update", "brief", "summary report"], "leadership_brief", {}),
    (["data quality", "quality", "reliability", "missing", "anomal"], "data_quality_report", {}),
]


def _keyword_route(question: str) -> tuple[str, dict] | None:
    """Return (tool_name, default_args) for a question if a keyword matches."""
    q = question.casefold()
    for keywords, tool, default_args in _KEYWORD_ROUTES:
        if any(kw in q for kw in keywords):
            # Try to detect sector phrase
            for phrase, _ in {
                "energy": None, "solar": None, "wind": None, "renewable": None,
                "mining": None, "rail": None, "railway": None, "power": None,
                "construction": None, "aviation": None,
            }.items():
                if phrase in q:
                    default_args = {**default_args, "sector": phrase}
                    break
            return tool, default_args
    return None


def _render_degraded(tool_name: str, result: dict[str, Any]) -> str:
    """Render a deterministic answer from a ToolResult in degraded mode."""
    prefix = "AI narration unavailable, showing computed results.\n\n"
    display = result.get("display", {})
    summary = display.get("summary", "")
    lines = [prefix + summary]
    if result.get("no_data_in_period"):
        avail = result.get("available_range", "unknown")
        lines.append(f"\nNo data found for the requested period. Data available: {avail}.")
    caveats = result.get("caveats", [])
    if caveats:
        lines.append("\n**Data notes:**")
        for c in caveats[:3]:
            lines.append(f"- {c}")
    assumptions = result.get("assumptions_used", [])
    if assumptions:
        lines.append("\n**Assumptions:**")
        for a in assumptions[:3]:
            lines.append(f"- {a}")
    data_as_of = result.get("data_as_of")
    if data_as_of:
        lines.append(f"\n_Data as of: {data_as_of}_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run_agent(
    question: str,
    history: list[dict[str, str]],  # [{role, content}]
    executor: ToolExecutor,
    llm: LLMProvider | None,
    today: date,
    data_as_of: str | None,
    max_llm_calls: int = 3,
    llm_disabled: bool = False,
) -> AgentResult:
    """Run the full agent loop for one user question.

    Returns an AgentResult with answer, trace, call count, model, and degraded flag.
    """
    trace: list[TraceItem] = []
    llm_calls = 0
    model_used: str | None = None

    # Build message history (last 8 messages, text only)
    history_msgs: list[LLMMessage] = []
    for m in history[-8:]:
        role = m.get("role", "user")
        content = m.get("content", "")
        history_msgs.append(LLMMessage(role=role, content=content))
    history_msgs.append(LLMMessage(role="user", content=question))

    system_prompt = build_system_prompt(today, data_as_of)

    # --- LLM disabled or unavailable: degrade immediately ---
    if llm_disabled or llm is None:
        return _degraded_answer(question, executor, trace, data_as_of)

    # --- LLM loop ---
    messages = list(history_msgs)
    collected_tool_results: list[str] = []

    for call_num in range(max_llm_calls):
        if llm_calls >= max_llm_calls:
            break
        try:
            response = llm.generate(system_prompt, messages, TOOL_DECLARATIONS)
            llm_calls += 1
            model_used = response.model_used
        except LLMUnavailable as exc:
            logger.warning("LLM unavailable: %s; falling back to degraded mode", exc)
            return _degraded_answer(question, executor, trace, data_as_of)

        if not response.tool_calls:
            # No tool calls → final answer
            answer = response.text or "I could not generate an answer."
            return AgentResult(
                answer=answer, trace=trace, llm_calls=llm_calls,
                model_used=model_used, degraded=False,
            )

        # Execute all tool calls
        tool_result_parts: list[str] = []
        for tc in response.tool_calls:
            try:
                result = executor.run(tc.name, tc.args)
            except Exception as exc:
                result = {"error": str(exc), "tool": tc.name}

            trace.append(TraceItem(
                tool=tc.name,
                params=tc.args,
                result_summary=result.get("display", {}).get("summary", "")[:200],
                coverage=result.get("coverage", []),
                caveats=result.get("caveats", []),
                assumptions=result.get("assumptions_used", []),
            ))
            # Serialize result for LLM context (display + key data)
            tool_result_parts.append(
                f"Tool: {tc.name}\n"
                f"Summary: {result.get('display', {}).get('summary', '')}\n"
                f"Caveats: {'; '.join(result.get('caveats', []))}\n"
                f"Assumptions: {'; '.join(result.get('assumptions_used', []))}\n"
                f"Data as of: {result.get('data_as_of', 'unknown')}\n"
                f"No data: {result.get('no_data_in_period', False)}\n"
                f"Available range: {result.get('available_range', '')}\n"
            )

        # Add tool results to message history for next LLM call
        combined = "\n---\n".join(tool_result_parts)
        messages.append(LLMMessage(role="assistant", content=f"[called tools]\n{combined}"))
        messages.append(LLMMessage(role="user", content="Please provide the final answer based on the tool results above."))

    # If we ran out of LLM calls, return last tool result in degraded style
    if trace:
        last_result = executor.run(trace[-1].tool, trace[-1].params)
        answer = _render_degraded(trace[-1].tool, last_result)
        return AgentResult(answer=answer, trace=trace, llm_calls=llm_calls, model_used=model_used, degraded=True)

    return AgentResult(
        answer="I ran out of calls to answer this question. Please try again.",
        trace=trace, llm_calls=llm_calls, model_used=model_used, degraded=True,
    )


def _degraded_answer(
    question: str,
    executor: ToolExecutor,
    trace: list[TraceItem],
    data_as_of: str | None,
) -> AgentResult:
    """Keyword-route and render a degraded (no-LLM) answer."""
    route = _keyword_route(question)
    if route is None:
        # No match: show the sample questions
        answer = (
            "AI narration unavailable, showing computed results.\n\n"
            "I can answer questions about:\n"
            "- Open pipeline (count, value, sector, owner)\n"
            "- Work orders (billed, collected, receivable)\n"
            "- Sector overview\n"
            "- Leadership brief\n"
            "- Data quality\n\n"
            "Try: 'How is our open pipeline looking?'"
        )
        return AgentResult(answer=answer, trace=[], llm_calls=0, model_used=None, degraded=True)

    tool_name, args = route
    result = executor.run(tool_name, args)
    trace.append(TraceItem(
        tool=tool_name,
        params=args,
        result_summary=result.get("display", {}).get("summary", "")[:200],
        coverage=result.get("coverage", []),
        caveats=result.get("caveats", []),
        assumptions=result.get("assumptions_used", []),
    ))
    answer = _render_degraded(tool_name, result)
    return AgentResult(answer=answer, trace=trace, llm_calls=0, model_used=None, degraded=True)
