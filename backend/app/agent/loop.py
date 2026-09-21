"""Agent loop: call LLM -> execute tools -> call LLM again with results.

Hard cap: MAX_LLM_CALLS_PER_QUESTION (default 3).
Degraded mode: when LLM is unavailable or disabled, routes queries deterministically.
Handles unsupported questions with immediate clear data limitation explanations.
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
from app.llm.base import (
    LLMAuthError,
    LLMMessage,
    LLMProvider,
    LLMQuotaExceeded,
    LLMTimeoutError,
    LLMUnavailable,
    ToolCall,
)
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
# Unsupported domains guardrail
# ---------------------------------------------------------------------------

_UNSUPPORTED_DOMAINS: list[tuple[list[str], str]] = [
    (
        [
            "employee", "attrition", "headcount", "hr data", "salary", "salaries",
            "hiring", "turnover", "staff satisfaction", "employee satisfaction", "employee morale"
        ],
        "I can't answer that reliably from the connected Monday.com Deals and Work Orders boards because they don't contain employee or HR data.",
    ),
    (
        [
            "profit margin", "ebitda", "net income", "cost data", "cogs", "expenses",
            "expense", "burn rate", "gross margin", "net profit", "operating margin"
        ],
        "I can't calculate profit margin reliably because the connected boards do not contain the required cost/profit data.",
    ),
    (
        [
            "customer satisfaction", "csat", "nps", "client satisfaction", "customer feedback score"
        ],
        "I can't determine customer satisfaction from the connected boards because no customer satisfaction metric is available.",
    ),
    (
        [
            "marketing campaign", "website traffic", "cac", "google ads", "ad spend",
            "social media reach", "seo traffic"
        ],
        "I can't answer that reliably from the connected boards because they don't contain marketing or website analytics.",
    ),
]


def check_unsupported_question(question: str) -> str | None:
    """Return an explanation if the user is asking about an unsupported domain."""
    q = question.casefold()
    for triggers, message in _UNSUPPORTED_DOMAINS:
        if any(tr in q for tr in triggers):
            return message
    return None


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
                owner=args.get("owner"),
                gst_basis=gst, fy_start_month=self.fy_start,
            )
        if name == "sector_overview":
            sectors = args.get("sectors")
            if not sectors and sector:
                sectors = sector if isinstance(sector, list) else [sector]
            return analytics.sector_overview(
                self.deals_df, self.wo_df, self.today,
                gst_basis=gst, sectors=sectors,
            )
        if name == "owner_summary":
            return analytics.owner_summary(
                self.deals_df, self.wo_df, self.today,
                owner=args.get("owner"),
                period_spec=period,
                gst_basis=gst,
                fy_start_month=self.fy_start,
            )
        if name == "trend_analysis":
            return analytics.trend_analysis(
                self.deals_df, self.wo_df, self.today,
                metric=args.get("metric", "all"),
                period_spec=args.get("period_spec", "this_quarter"),
                compare_to=args.get("compare_to", "last_quarter"),
                fy_start_month=self.fy_start,
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
# Degraded-mode deterministic router
# ---------------------------------------------------------------------------

_KEYWORD_ROUTES: list[tuple[list[str], str, dict]] = [
    # 1. Owner questions
    (
        [
            "who owns", "which owner", "by owner", "owners by pipeline", "largest pipeline by owner",
            "top 5 owners", "top owners", "most valuable open deals", "most open deals",
            "most overdue opportunities", "overdue deals by owner", "largest book of opportunities",
            "sales owner", "sales rep", "rep with the largest"
        ],
        "owner_summary",
        {},
    ),
    # 2. Trend & period comparison questions
    (
        [
            "what changed", "changed recently", "changed this quarter", "recent changes",
            "growth", "trend", "increased", "decreased", "this quarter compared",
            "compared to last quarter", "how has our pipeline grown", "change in business"
        ],
        "trend_analysis",
        {},
    ),
    # 3. Specific sector comparison (Mining vs Renewables, etc.)
    (
        [
            "compare mining and renewables", "mining and renewables", "renewables and mining",
            "compare renewables and mining"
        ],
        "sector_overview",
        {"sectors": ["Mining", "Renewables"]},
    ),
    # 4. Cross-board & Sector overview
    (
        [
            "cross board", "cross-board", "pipeline and operational", "pipeline and work order",
            "pipeline and operation", "pipeline and billing", "deals and work orders",
            "overlap with execution", "which sectors have both", "highest win rate",
            "best win rate", "win rate", "win-rate", "winrate", "convert best",
            "conversion rate", "won deals", "dead deals", "sector overview", "which industries",
            "sectoral performance", "investigate based on both boards", "compare sectors"
        ],
        "sector_overview",
        {},
    ),
    # 5. Work order, Receivables, Collections, Operations
    (
        [
            "receivable", "outstanding", "money is still due", "still due", "remains to be collected",
            "money stuck", "money getting stuck", "where is our money", "billed versus collected",
            "billed vs collected", "billed against collected", "how much have we billed",
            "how much have we collected", "how much is still to be billed", "still to bill", "to-bill",
            "how are our work orders doing", "how is execution going", "what's happening operationally",
            "what's happening with our operations", "happening with our operations", "happening with operations",
            "operational overview", "operational snapshot", "operations doing", "how are operations", "operations",
            "operational delivery", "delivery problems", "delivery problem", "delivery issues", "delivery issue",
            "operational problems", "operational issues", "operational risk", "execution problems", "execution issues",
            "billing problems", "billing gap", "delayed orders", "overdue work orders", "work order",
            "work orders", "invoice", "invoiced", "billed", "collected"
        ],
        "work_order_summary",
        {},
    ),
    # 6. Data quality & trust
    (
        [
            "data quality", "can i trust", "trust this dataset", "trust the current data",
            "what data is missing", "duplicates", "anomal", "fields are incomplete", "data reliability",
            "excluded", "exclusions"
        ],
        "data_quality_report",
        {},
    ),
    # 7. Leadership brief
    (
        [
            "leadership", "executive snapshot", "executive update", "brief", "summary report",
            "biggest risks", "what should leadership know", "prepare a leadership update",
            "update for leadership", "where should leadership pay attention"
        ],
        "leadership_brief",
        {},
    ),
    # 8. Deals & Pipeline
    (
        [
            "pipeline", "open deal", "open deals", "potential revenue", "business is still open",
            "opportunity", "opportunities", "largest pipeline", "biggest pipeline", "deal value",
            "overdue", "stale close", "average deal", "median deal", "pipeline concentration",
            "concentrated is our pipeline", "how are sales doing"
        ],
        "pipeline_summary",
        {},
    ),
]


def _keyword_route(question: str) -> tuple[str, dict] | None:
    """Return (tool_name, default_args) for a question by analyzing business intent."""
    q = question.casefold()

    # Detect sector phrase in question
    extracted_sector = None
    for phrase in [
        "clean energy", "green energy", "solar energy", "wind energy",
        "energy", "solar", "wind", "renewable", "renewables",
        "mining", "railways", "railway", "rail", "train", "powerline", "power",
        "construction", "infra", "manufacturing", "aviation", "security", "others",
    ]:
        if phrase in q:
            extracted_sector = phrase
            break

    # 1. Specific two-sector direct comparison (e.g. "compare mining and renewables")
    if ("mining" in q and "renewable" in q) or ("renewables" in q and "mining" in q):
        return "sector_overview", {"sectors": ["Mining", "Renewables"]}

    # 2. Semantic Cross-Board & Sector Risk Intent:
    # A question has cross-board intent if it bridges:
    # (A) Sales/Deals/Pipeline signal AND (B) Operations/Delivery/Execution signal,
    # OR explicitly mentions cross-board / both boards / sales & operations overlap.
    sales_pipeline_signals = [
        "pipeline", "sales", "deal", "deals", "opportunity", "opportunities",
        "open business", "commercial exposure", "potential revenue", "pipeline concentration",
    ]
    ops_delivery_signals = [
        "operational", "operation", "operations", "delivery", "execution",
        "work order", "work orders", "delivery risk", "delivery problem", "delivery problems",
        "delivery issue", "delivery issues", "billing", "receivable", "receivables",
        "fulfillment", "slippage", "execution risk", "execution risks",
    ]
    cross_board_terms = [
        "cross board", "cross-board", "both boards", "two boards",
        "sales and execution", "sales and operations", "pipeline and delivery",
        "pipeline and operational", "pipeline and execution", "pipeline and work order",
        "deals and work orders", "deals and operations", "sales and delivery",
        "sales exposure and execution", "sales and execution risks",
    ]
    intersection_signals = [
        "both", "overlap", "overlapping", "together", "joint", "combined",
        "intersect", "simultaneous", "at the same time", "consider sales and operations",
        "sales and operations together",
    ]

    has_sales_signal = any(s in q for s in sales_pipeline_signals)
    has_ops_signal = any(s in q for s in ops_delivery_signals)
    has_cross_board_phrase = any(cb in q for cb in cross_board_terms)
    has_intersection = any(it in q for it in intersection_signals)

    # Route to sector_overview if question combines sales + operations OR asks for cross-board intersection
    if has_cross_board_phrase or (has_sales_signal and has_ops_signal) or (has_intersection and (has_sales_signal or has_ops_signal)):
        args: dict[str, Any] = {}
        if extracted_sector:
            args["sector"] = extracted_sector
        return "sector_overview", args

    # 3. Fall back to category-based intent routes
    for keywords, tool, default_args in _KEYWORD_ROUTES:
        if any(kw in q for kw in keywords):
            if extracted_sector and "sectors" not in default_args:
                default_args = {**default_args, "sector": extracted_sector}
            return tool, default_args

    return None


def _render_degraded(tool_name: str, result: dict[str, Any], prefix: str | None = None) -> str:
    """Render a deterministic answer from a ToolResult in degraded mode."""
    p = (prefix or "AI narration unavailable, showing computed results.").rstrip() + "\n\n"
    summary = result.get("summary") or result.get("display", {}).get("summary", "")
    lines = [p + summary]
    if result.get("no_data_in_period"):
        avail = result.get("available_range", "unknown")
        lines.append(f"\nNo data found for the requested period. Data available: {avail}.")
    caveats = result.get("caveats", [])
    if caveats:
        lines.append("\n**Data notes:**")
        for c in caveats[:3]:
            lines.append(f"- {c}")
    assumptions = result.get("assumptions") or result.get("assumptions_used", [])
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
    fallback_prefix: str | None = None,
) -> AgentResult:
    """Run the full agent loop for one user question.

    Returns an AgentResult with answer, trace, call count, model, and degraded flag.
    """
    trace: list[TraceItem] = []
    llm_calls = 0
    model_used: str | None = None

    # Check for unsupported questions (HR, profit margins, customer satisfaction, marketing)
    unsupported_msg = check_unsupported_question(question)
    if unsupported_msg:
        return AgentResult(
            answer=unsupported_msg,
            trace=[],
            llm_calls=0,
            model_used=None,
            degraded=False,
        )

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
        return _degraded_answer(question, executor, trace, data_as_of, prefix=fallback_prefix)

    # --- LLM loop ---
    messages = list(history_msgs)

    for call_num in range(max_llm_calls):
        if llm_calls >= max_llm_calls:
            break
        try:
            available_tools = [] if trace else TOOL_DECLARATIONS
            response = llm.generate(system_prompt, messages, available_tools)
            llm_calls += 1
            model_used = response.model_used
        except LLMQuotaExceeded as exc:
            logger.warning("LLM quota exceeded: %s; falling back to degraded mode", exc)
            fallback_msg = (
                "⚠️ AI narration is temporarily unavailable because the AI service has reached its current usage limit. "
                "I'm showing the computed result directly from the Monday.com data."
            )
            if trace:
                last_result = executor.run(trace[-1].tool, trace[-1].params)
                answer = _render_degraded(trace[-1].tool, last_result, prefix=fallback_msg)
                return AgentResult(answer=answer, trace=trace, llm_calls=llm_calls, model_used=model_used, degraded=True)
            return _degraded_answer(question, executor, trace, data_as_of, prefix=fallback_msg)
        except LLMAuthError as exc:
            logger.warning("LLM auth error: %s; falling back to degraded mode", exc)
            fallback_msg = (
                "⚠️ AI narration is unavailable because the AI service connection needs attention. "
                "I'm showing the computed result directly from the Monday.com data."
            )
            if trace:
                last_result = executor.run(trace[-1].tool, trace[-1].params)
                answer = _render_degraded(trace[-1].tool, last_result, prefix=fallback_msg)
                return AgentResult(answer=answer, trace=trace, llm_calls=llm_calls, model_used=model_used, degraded=True)
            return _degraded_answer(question, executor, trace, data_as_of, prefix=fallback_msg)
        except (LLMTimeoutError, LLMUnavailable) as exc:
            logger.warning("LLM unavailable (%s): %s; falling back to degraded mode", type(exc).__name__, exc)
            fallback_msg = (
                "⚠️ AI narration is temporarily unavailable. "
                "I'm showing the computed result directly from the Monday.com data."
            )
            if trace:
                last_result = executor.run(trace[-1].tool, trace[-1].params)
                answer = _render_degraded(trace[-1].tool, last_result, prefix=fallback_msg)
                return AgentResult(answer=answer, trace=trace, llm_calls=llm_calls, model_used=model_used, degraded=True)
            return _degraded_answer(question, executor, trace, data_as_of, prefix=fallback_msg)

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
                result_summary=(result.get("summary") or result.get("display", {}).get("summary", ""))[:200],
                coverage=result.get("coverage", []),
                caveats=result.get("caveats", []),
                assumptions=result.get("assumptions") or result.get("assumptions_used", []),
            ))
            # Serialize result for LLM context (display + structured data)
            data_str = json.dumps(result.get("data", {}), default=str)
            summary_part = result.get("summary") or result.get("display", {}).get("summary", "")
            tool_result_parts.append(
                f"Tool: {tc.name}\n"
                f"Summary:\n{summary_part}\n\n"
                f"Structured Data (JSON):\n{data_str}\n\n"
                f"Caveats: {'; '.join(result.get('caveats', []))}\n"
                f"Assumptions: {'; '.join(result.get('assumptions', []) or result.get('assumptions_used', []))}\n"
                f"Data as of: {result.get('data_as_of', 'unknown')}\n"
                f"No data: {result.get('no_data_in_period', False)}\n"
                f"Available range: {result.get('available_range', '')}\n"
            )

        # Add tool results to message history for next LLM call
        combined = "\n---\n".join(tool_result_parts)
        messages.append(LLMMessage(role="assistant", content=f"[called tools]\n{combined}"))
        messages.append(LLMMessage(role="user", content="Please provide the final answer based on the tool results above, directly answering the question with supporting numbers, counts, and caveats."))

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
    prefix: str | None = None,
) -> AgentResult:
    """Keyword-route and render a degraded (no-LLM) answer."""
    unsupported = check_unsupported_question(question)
    if unsupported:
        return AgentResult(answer=unsupported, trace=[], llm_calls=0, model_used=None, degraded=True)

    route = _keyword_route(question)
    if route is None:
        lead = (prefix or "AI narration unavailable, showing computed results.").rstrip()
        answer = (
            f"{lead}\n\n"
            "Could you clarify what you'd like to analyze? For example, you can ask about:\n"
            "- Open pipeline (count, value, sector, owner)\n"
            "- Work orders (billed, collected, receivable)\n"
            "- Sales owner performance & rankings\n"
            "- Sector overview & comparisons\n"
            "- Leadership brief\n"
            "- Data quality"
        )
        return AgentResult(answer=answer, trace=[], llm_calls=0, model_used=None, degraded=True)

    tool_name, args = route
    result = executor.run(tool_name, args)
    trace.append(TraceItem(
        tool=tool_name,
        params=args,
        result_summary=(result.get("summary") or result.get("display", {}).get("summary", ""))[:200],
        coverage=result.get("coverage", []),
        caveats=result.get("caveats", []),
        assumptions=result.get("assumptions") or result.get("assumptions_used", []),
    ))
    answer = _render_degraded(tool_name, result, prefix=prefix)
    return AgentResult(answer=answer, trace=trace, llm_calls=0, model_used=None, degraded=True)
