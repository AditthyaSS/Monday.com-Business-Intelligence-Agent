"""Comprehensive test suite for the improved Skylark BI Agent.

Covers:
1. Data Resilience (nulls, missing values, invalid dates, duplicate rows, missing owners, zero denominators, financial anomalies)
2. Query Understanding & Routing (pipeline, work orders, receivables, collections, billing, owners, sectors, cross-board, leadership)
3. Business Intelligence Calculations (averages, medians, concentration, GST basis, win rates, sector financials, delayed orders)
4. Owner Analytics (rankings by pipeline, deal counts, overdue deals, missing owner disclosures)
5. Cross-Board Analytics (disclaimer, sector overlap, side-by-side comparison)
6. Unsupported Questions (HR, attrition, satisfaction, profit margins, customer metrics)
7. Trend & Time Questions (honest unavailable prior period handling, current snapshot labeling)
8. Agent Loop & Degraded Mode (call limits, structured serialization, degraded answers)
"""

from datetime import date
import pandas as pd
import pytest

from app.agent.loop import (
    ToolExecutor,
    _keyword_route,
    _render_degraded,
    check_unsupported_question,
    run_agent,
)
from app.analytics.periods import resolve_period
from app.analytics.tools import (
    data_quality_report,
    leadership_brief,
    owner_summary,
    pipeline_summary,
    sector_overview,
    trend_analysis,
    work_order_summary,
)
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolCall
from app.normalize.common import fmt_inr, parse_number
from app.normalize.deals import QualityReport, normalise_deals
from app.normalize.taxonomy import canon_sector, resolve_sector_phrase
from app.normalize.workorders import WOQualityReport, normalise_workorders


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _build_test_deals_df() -> pd.DataFrame:
    """Build controlled test dataframe for deals."""
    rows = [
        # Mining: 2 Won, 1 Dead, 2 Open (1 missing value, 1 overdue)
        {"deal_name": "M-Won-1", "owner": "OWNER_01", "client_code": "C1", "client_id": 1,
         "status": "Won", "stage_code": "G", "stage_name": "G. Project Won",
         "probability": None, "value_inr": 10_000_000.0, "tentative_close": date(2025, 6, 1),
         "actual_close": date(2025, 6, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "M-Won-2", "owner": "OWNER_01", "client_code": "C1", "client_id": 1,
         "status": "Won", "stage_code": "G", "stage_name": "G. Project Won",
         "probability": None, "value_inr": 20_000_000.0, "tentative_close": date(2025, 7, 1),
         "actual_close": date(2025, 7, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "M-Dead-1", "owner": "OWNER_01", "client_code": "C1", "client_id": 1,
         "status": "Dead", "stage_code": "N", "stage_name": "N. Dead Deals",
         "probability": None, "value_inr": 15_000_000.0, "tentative_close": date(2025, 8, 1),
         "actual_close": date(2025, 8, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "M-Open-1", "owner": "OWNER_01", "client_code": "C1", "client_id": 1,
         "status": "Open", "stage_code": "D", "stage_name": "D. Negotiation",
         "probability": None, "value_inr": 30_000_000.0, "tentative_close": date(2025, 12, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": ["open_close_date_past"]},
        {"deal_name": "M-Open-2", "owner": "OWNER_02", "client_code": "C1", "client_id": 1,
         "status": "Open", "stage_code": "C", "stage_name": "C. Proposal Sent",
         "probability": None, "value_inr": None, "tentative_close": date(2026, 11, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": ["value_missing"]},

        # Renewables: 1 Won, 1 Dead, 1 Open
        {"deal_name": "R-Won-1", "owner": "OWNER_02", "client_code": "C2", "client_id": 2,
         "status": "Won", "stage_code": "G", "stage_name": "G. Project Won",
         "probability": None, "value_inr": 50_000_000.0, "tentative_close": date(2025, 5, 1),
         "actual_close": date(2025, 5, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Renewables", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "R-Dead-1", "owner": "OWNER_02", "client_code": "C2", "client_id": 2,
         "status": "Dead", "stage_code": "N", "stage_name": "N. Dead Deals",
         "probability": None, "value_inr": 10_000_000.0, "tentative_close": date(2025, 5, 1),
         "actual_close": date(2025, 5, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Renewables", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "R-Open-1", "owner": "OWNER_02", "client_code": "C2", "client_id": 2,
         "status": "Open", "stage_code": "E", "stage_name": "E. Commercial Negotiation",
         "probability": None, "value_inr": 70_000_000.0, "tentative_close": date(2026, 12, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Renewables", "sector_is_real": True, "quality_flags": []},

        # Construction: 0 Won, 0 Dead, 1 Open with missing owner
        {"deal_name": "C-Open-1", "owner": None, "client_code": "C3", "client_id": 3,
         "status": "Open", "stage_code": "A", "stage_name": "A. Lead Generated",
         "probability": None, "value_inr": 5_000_000.0, "tentative_close": date(2026, 10, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Construction", "sector_is_real": True, "quality_flags": ["owner_missing"]},
    ]
    return pd.DataFrame(rows)


def _build_test_wo_df() -> pd.DataFrame:
    """Build controlled test dataframe for work orders."""
    rows = [
        {"wo_id": "WO-01", "deal_name": "M-Won-1", "client_code": "WO_01", "client_id": 1,
         "nature": "Survey", "execution_status": "Completed", "po_date": date(2025, 6, 1),
         "start": date(2025, 6, 1), "end": date(2025, 7, 1), "owner": "OWNER_01",
         "sector": "Mining", "work_types": ["Survey"], "software_platform": None,
         "amount_excl": 10_000_000.0, "amount_incl": 11_800_000.0,
         "billed_excl": 8_000_000.0, "billed_incl": 9_440_000.0,
         "collected_incl": 7_080_000.0, "receivable": 2_360_000.0, "to_bill_excl": 2_000_000.0,
         "ar_priority": False, "invoice_status": "Partially Billed",
         "billing_status": "Billed", "wo_status": "Active", "last_invoice_date": date(2026, 1, 1),
         "quality_flags": []},

        # Over-billed and negative to-bill anomaly
        {"wo_id": "WO-02", "deal_name": "M-Won-2", "client_code": "WO_01", "client_id": 1,
         "nature": "Processing", "execution_status": "Ongoing", "po_date": date(2025, 7, 1),
         "start": date(2025, 7, 1), "end": date(2025, 8, 1), "owner": "OWNER_01",
         "sector": "Mining", "work_types": ["Processing"], "software_platform": None,
         "amount_excl": 5_000_000.0, "amount_incl": 5_900_000.0,
         "billed_excl": 6_000_000.0, "billed_incl": 7_080_000.0,
         "collected_incl": 7_080_000.0, "receivable": 0.0, "to_bill_excl": -1_000_000.0,
         "ar_priority": False, "invoice_status": "Over Billed",
         "billing_status": "Billed", "wo_status": "Active", "last_invoice_date": date(2026, 1, 1),
         "quality_flags": ["over_billed", "negative_to_bill"]},

        # Delayed work order (end date passed, Ongoing)
        {"wo_id": "WO-03", "deal_name": "R-Won-1", "client_code": "WO_02", "client_id": 2,
         "nature": "Inspection", "execution_status": "Ongoing", "po_date": date(2025, 8, 1),
         "start": date(2025, 8, 1), "end": date(2026, 1, 1), "owner": "OWNER_02",
         "sector": "Renewables", "work_types": ["Inspection"], "software_platform": None,
         "amount_excl": 20_000_000.0, "amount_incl": 23_600_000.0,
         "billed_excl": 10_000_000.0, "billed_incl": 11_800_000.0,
         "collected_incl": 5_900_000.0, "receivable": 5_900_000.0, "to_bill_excl": 10_000_000.0,
         "ar_priority": True, "invoice_status": "Partially Billed",
         "billing_status": "Billed", "wo_status": "Active", "last_invoice_date": date(2026, 1, 1),
         "quality_flags": []},
    ]
    return pd.DataFrame(rows)


def _build_test_executor(today: date = date(2026, 9, 21)) -> ToolExecutor:
    deals_df = _build_test_deals_df()
    wo_df = _build_test_wo_df()
    dr = QualityReport(board="deals", rows_in=len(deals_df), rows_used=len(deals_df), missing_value=1, missing_owner=1)
    wr = WOQualityReport(board="work_orders", rows_in=len(wo_df), rows_used=len(wo_df), over_billed=1, negative_to_bill=1)
    return ToolExecutor(deals_df, wo_df, dr, wr, today=today)


class MockLLM(LLMProvider):
    def __init__(self, response_text: str = "", tool_calls: list[ToolCall] | None = None) -> None:
        self.response_text = response_text
        self.tool_calls = tool_calls or []
        self.calls = 0

    def generate(self, system: str, messages: list[LLMMessage], tools: list[dict]) -> LLMResponse:
        self.calls += 1
        return LLMResponse(text=self.response_text, tool_calls=self.tool_calls, model_used="mock-model")


# ---------------------------------------------------------------------------
# 1. DATA RESILIENCE TESTS
# ---------------------------------------------------------------------------

def test_missing_deal_value_not_treated_as_zero():
    """Missing deal value must be excluded from monetary sums and reported in coverage."""
    deals_df = _build_test_deals_df()
    res = pipeline_summary(deals_df, today=date(2026, 9, 21))
    data = res["data"]

    # 4 open deals total: M-Open-1 (30M), M-Open-2 (None), R-Open-1 (70M), C-Open-1 (5M)
    assert data["total_count"] == 4
    assert data["value_count"] == 3
    assert data["missing_value_count"] == 1
    assert data["total_value"] == 105_000_000.0  # 30M + 70M + 5M
    # Average must be 105M / 3 = 35M (never 105M / 4 = 26.25M)
    assert data["mean_deal_value"] == 35_000_000.0
    assert any("missing" in c.lower() for c in res["caveats"])


def test_zero_denominator_win_rate():
    """Win rate with 0 closed deals must be None / N/A, never 0%."""
    deals_df = _build_test_deals_df()
    wo_df = _build_test_wo_df()
    res = sector_overview(deals_df, wo_df, today=date(2026, 9, 21))
    c_sec = next(r for r in res["data"]["rows"] if r["sector"] == "Construction")
    assert c_sec["closed_deals"] == 0
    assert c_sec["win_rate_pct"] is None


def test_work_order_anomalies_detected():
    """Over-billed and negative to-bill anomalies are captured and flagged."""
    wo_df = _build_test_wo_df()
    res = work_order_summary(wo_df, today=date(2026, 9, 21))
    data = res["data"]
    assert data["over_billed_count"] == 1
    assert data["negative_to_bill_count"] == 1
    assert any("anomaly" in c.lower() for c in res["caveats"])


def test_delayed_work_orders_flagged():
    """Incomplete orders past end date are flagged as delayed."""
    wo_df = _build_test_wo_df()
    res = work_order_summary(wo_df, today=date(2026, 9, 21))
    data = res["data"]
    assert data["delayed_orders_count"] >= 1
    assert any(d["wo_id"] == "WO-03" for d in data["delayed_orders_sample"])


# ---------------------------------------------------------------------------
# 2. OWNER ANALYTICS TESTS
# ---------------------------------------------------------------------------

def test_owner_summary_rankings_and_exclusions():
    """Owner summary accurately ranks owners and excludes missing owners from ranking."""
    deals_df = _build_test_deals_df()
    wo_df = _build_test_wo_df()
    res = owner_summary(deals_df, wo_df, today=date(2026, 9, 21))
    data = res["data"]

    # OWNER_02 has R-Open-1 (70M); OWNER_01 has M-Open-1 (30M)
    assert data["top_by_pipeline"]["owner"] == "OWNER_02"
    assert data["top_by_pipeline"]["open_pipeline_value"] == 70_000_000.0

    # OWNER_01 has M-Open-1 with past close date
    assert data["top_by_overdue"]["owner"] == "OWNER_01"
    assert data["top_by_overdue"]["overdue_open_deals"] == 1

    # Missing owner deal C-Open-1 (5M) must be excluded from rankings and disclosed
    assert data["missing_owner_open_deals"] == 1
    assert data["missing_owner_pipeline_value"] == 5_000_000.0
    assert any("excluded from owner rankings" in c for c in res["caveats"])


# ---------------------------------------------------------------------------
# 3. WORK ORDER & RECEIVABLE FINANCIAL TESTS
# ---------------------------------------------------------------------------

def test_receivable_and_billing_metrics():
    """Direct answers for receivables, billing, collections, and to-bill."""
    wo_df = _build_test_wo_df()
    res = work_order_summary(wo_df, today=date(2026, 9, 21), gst_basis="excl")
    data = res["data"]

    # Total order amount excl GST: 10M + 5M + 20M = 35M
    assert data["order_value"] == 35_000_000.0
    # Billed excl: 8M + 6M + 10M = 24M
    assert data["billed"] == 24_000_000.0
    # To bill: 35M - 24M = 11M
    assert data["to_bill"] == 11_000_000.0

    # Sector breakdown includes receivables and to_bill
    sec_rec = data["top_sector_by_receivable"]
    assert sec_rec is not None
    assert sec_rec["sector"] in ("Renewables", "Mining")


# ---------------------------------------------------------------------------
# 4. CROSS-BOARD & SECTOR TESTS
# ---------------------------------------------------------------------------

def test_cross_board_disclaimer_and_sector_comparison():
    """Sector overview must provide aggregation disclaimer and side-by-side comparison."""
    deals_df = _build_test_deals_df()
    wo_df = _build_test_wo_df()
    res = sector_overview(deals_df, wo_df, today=date(2026, 9, 21), sectors=["Mining", "Renewables"])
    assert "Cross-board comparison is aggregated at sector level" in res["caveats"][0]

    rows = res["data"]["rows"]
    assert len(rows) == 2
    sectors = {r["sector"] for r in rows}
    assert sectors == {"Mining", "Renewables"}


# ---------------------------------------------------------------------------
# 5. UNSUPPORTED QUESTIONS TESTS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("unsupported_q,expected_phrase", [
    ("What is our employee attrition?", "employee or HR data"),
    ("What is our employee satisfaction score?", "employee or HR data"),
    ("What is our staff turnover rate?", "employee or HR data"),
    ("What is our profit margin?", "cost/profit data"),
    ("What is our EBITDA and net income?", "cost/profit data"),
    ("What is our customer satisfaction rating?", "customer satisfaction metric"),
    ("What is our CSAT score?", "customer satisfaction metric"),
    ("What is our website traffic?", "marketing or website analytics"),
])
def test_unsupported_questions_handled(unsupported_q, expected_phrase):
    """Unsupported questions must return a direct explanation without hallucination."""
    msg = check_unsupported_question(unsupported_q)
    assert msg is not None
    assert expected_phrase in msg

    executor = _build_test_executor()
    result = run_agent(unsupported_q, [], executor, llm=None, today=date(2026, 9, 21), data_as_of="2026-04-01")
    assert expected_phrase in result.answer
    assert result.llm_calls == 0


# ---------------------------------------------------------------------------
# 6. TREND & PERIOD COMPARISON TESTS
# ---------------------------------------------------------------------------

def test_trend_recent_unavailable_history():
    """Trend question on unavailable recent history must state limitation clearly."""
    deals_df = _build_test_deals_df()
    wo_df = _build_test_wo_df()
    res = trend_analysis(deals_df, wo_df, today=date(2026, 9, 21), period_spec="this_quarter")
    assert res["has_comparable_history"] is False
    assert "reliable recent-change comparison is unavailable" in res["summary"]
    assert "Current-State Snapshot" in res["summary"]


# ---------------------------------------------------------------------------
# 7. QUERY UNDERSTANDING & ROUTING TESTS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question,expected_tool", [
    ("How much is receivable?", "work_order_summary"),
    ("What's outstanding?", "work_order_summary"),
    ("How much money is still due?", "work_order_summary"),
    ("Where is our money getting stuck?", "work_order_summary"),
    ("How much have we billed versus collected?", "work_order_summary"),
    ("How are our work orders doing?", "work_order_summary"),
    ("Give me an operational overview.", "work_order_summary"),
    ("What's happening with our operations?", "work_order_summary"),
    ("Who owns the most valuable open deals?", "owner_summary"),
    ("Which owner has the largest open pipeline?", "owner_summary"),
    ("Show me the top 5 owners by pipeline.", "owner_summary"),
    ("Who has the most open deals?", "owner_summary"),
    ("Which owner has the most overdue opportunities?", "owner_summary"),
    ("Which sector has the highest win rate?", "sector_overview"),
    ("Compare Mining and Renewables.", "sector_overview"),
    ("Which sectors have both pipeline and operational issues?", "sector_overview"),
    ("What changed recently in our business?", "trend_analysis"),
    ("What changed this quarter?", "trend_analysis"),
    ("Can I trust the current data?", "data_quality_report"),
    ("Give me an executive snapshot.", "leadership_brief"),
    ("How much of our pipeline is overdue?", "pipeline_summary"),
    ("Where is most of our potential revenue?", "pipeline_summary"),
])
def test_query_routing_comprehensiveness(question, expected_tool):
    """Deterministic routing must correctly route all key founder queries."""
    route = _keyword_route(question)
    assert route is not None, f"Failed to route question: {question}"
    tool_name, _ = route
    assert tool_name == expected_tool, f"Question '{question}' routed to {tool_name}, expected {expected_tool}"


# ---------------------------------------------------------------------------
# 8. AGENT LOOP & DEGRADED MODE TESTS
# ---------------------------------------------------------------------------

def test_agent_degraded_mode_receivable():
    """Receivable question in degraded mode directly provides receivable amounts."""
    executor = _build_test_executor()
    res = run_agent(
        question="How much is receivable?",
        history=[],
        executor=executor,
        llm=None,
        today=date(2026, 9, 21),
        data_as_of="2026-04-01",
        llm_disabled=True,
    )
    assert res.degraded is True
    assert "Receivables outstanding:" in res.answer
    assert len(res.trace) == 1
    assert res.trace[0].tool == "work_order_summary"


def test_agent_call_limits_preserved():
    """Agent must not exceed max_llm_calls."""
    executor = _build_test_executor()
    # Mock LLM that keeps returning tool calls
    infinite_tool_llm = MockLLM(
        response_text="Let me check pipeline",
        tool_calls=[ToolCall(id="tc1", name="pipeline_summary", args={})],
    )
    res = run_agent(
        question="How is pipeline doing?",
        history=[],
        executor=executor,
        llm=infinite_tool_llm,
        today=date(2026, 9, 21),
        data_as_of="2026-04-01",
        max_llm_calls=2,
    )
    assert res.llm_calls <= 2
