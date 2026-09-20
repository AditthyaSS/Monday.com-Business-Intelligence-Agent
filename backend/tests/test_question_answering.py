"""Focused tests for the question-answering system, analytics tools, and agent loop.

Covers:
- Pipeline summary (counts, values, averages, median, overdue close dates, rankings)
- Work order summary (order value, billed, collected, to-bill, anomalies, sector breakdown)
- Sector overview (win rate = Won/(Won+Dead), zero-denominator protection, rankings, ties)
- Data quality report
- Cross-board sector matching
- Degraded mode responses (ensuring specific founder questions get concrete answers)
- Structured data reaching the LLM context
"""

import json
from datetime import date
import pandas as pd
import pytest

from app.agent.loop import ToolExecutor, run_agent
from app.analytics.tools import (
    data_quality_report,
    leadership_brief,
    pipeline_summary,
    sector_overview,
    work_order_summary,
)
from app.llm.base import LLMMessage, LLMResponse, ToolCall
from app.normalize.deals import QualityReport
from app.normalize.workorders import WOQualityReport


def _create_sample_deals_df() -> pd.DataFrame:
    """Create a realistic sample deals dataframe covering various sectors and statuses."""
    rows = [
        # Mining: 3 Won, 1 Dead, 2 Open (1 missing value)
        {"deal_name": "Mine-1", "owner": "O1", "client_code": "C1", "client_id": 1,
         "status": "Won", "stage_code": "G", "stage_name": "G. Project Won",
         "probability": None, "value_inr": 10_000_000.0, "tentative_close": None,
         "actual_close": date(2025, 5, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "Mine-2", "owner": "O1", "client_code": "C1", "client_id": 1,
         "status": "Won", "stage_code": "G", "stage_name": "G. Project Won",
         "probability": None, "value_inr": 20_000_000.0, "tentative_close": None,
         "actual_close": date(2025, 6, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "Mine-3", "owner": "O1", "client_code": "C1", "client_id": 1,
         "status": "Won", "stage_code": "G", "stage_name": "G. Project Won",
         "probability": None, "value_inr": 30_000_000.0, "tentative_close": None,
         "actual_close": date(2025, 7, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "Mine-4", "owner": "O1", "client_code": "C1", "client_id": 1,
         "status": "Dead", "stage_code": "H", "stage_name": "H. Project Cancelled",
         "probability": None, "value_inr": 15_000_000.0, "tentative_close": None,
         "actual_close": date(2025, 8, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "Mine-Open-1", "owner": "O1", "client_code": "C1", "client_id": 1,
         "status": "Open", "stage_code": "C", "stage_name": "C. Proposal Submitted",
         "probability": None, "value_inr": 25_000_000.0, "tentative_close": date(2025, 12, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": ["open_close_date_past"]},
        {"deal_name": "Mine-Open-2", "owner": "O1", "client_code": "C1", "client_id": 1,
         "status": "Open", "stage_code": "D", "stage_name": "D. Commercial Negotiation",
         "probability": None, "value_inr": None, "tentative_close": date(2026, 11, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Mining", "sector_is_real": True, "quality_flags": []},

        # Renewables: 1 Won, 1 Dead (50% win rate), 1 Open
        {"deal_name": "Renew-1", "owner": "O2", "client_code": "C2", "client_id": 2,
         "status": "Won", "stage_code": "G", "stage_name": "G. Project Won",
         "probability": None, "value_inr": 40_000_000.0, "tentative_close": None,
         "actual_close": date(2025, 5, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Renewables", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "Renew-2", "owner": "O2", "client_code": "C2", "client_id": 2,
         "status": "Dead", "stage_code": "H", "stage_name": "H. Project Cancelled",
         "probability": None, "value_inr": 10_000_000.0, "tentative_close": None,
         "actual_close": date(2025, 5, 1), "created": date(2025, 1, 1), "product": None,
         "sector": "Renewables", "sector_is_real": True, "quality_flags": []},
        {"deal_name": "Renew-Open", "owner": "O2", "client_code": "C2", "client_id": 2,
         "status": "Open", "stage_code": "C", "stage_name": "C. Proposal Submitted",
         "probability": None, "value_inr": 50_000_000.0, "tentative_close": date(2026, 12, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Renewables", "sector_is_real": True, "quality_flags": []},

        # Aviation: 0 Won, 0 Dead, 1 Open (Closed deals = 0 -> Win Rate must be None)
        {"deal_name": "Av-Open", "owner": "O3", "client_code": "C3", "client_id": 3,
         "status": "Open", "stage_code": "B", "stage_name": "B. Technical Qualification",
         "probability": None, "value_inr": 5_000_000.0, "tentative_close": date(2026, 10, 1),
         "actual_close": None, "created": date(2025, 1, 1), "product": None,
         "sector": "Aviation", "sector_is_real": True, "quality_flags": []},
    ]
    return pd.DataFrame(rows)


def _create_sample_wo_df() -> pd.DataFrame:
    """Create a realistic sample work orders dataframe."""
    rows = [
        {"wo_id": "WO-001", "deal_name": "Mine-1", "client_code": "C1", "client_id": 1,
         "nature": "Survey", "execution_status": "Completed", "po_date": date(2025, 6, 1),
         "start": date(2025, 6, 1), "end": date(2025, 7, 1), "owner": "O1",
         "sector": "Mining", "work_types": ["Survey"], "software_platform": None,
         "amount_excl": 10_000_000.0, "amount_incl": 11_800_000.0,
         "billed_excl": 6_000_000.0, "billed_incl": 7_080_000.0,
         "collected_incl": 5_900_000.0, "receivable": 1_180_000.0, "to_bill_excl": 4_000_000.0,
         "ar_priority": False, "invoice_status": "Partially Billed",
         "billing_status": "Billed", "wo_status": "Active", "last_invoice_date": date(2026, 1, 1),
         "quality_flags": []},
        {"wo_id": "WO-002", "deal_name": "Mine-2", "client_code": "C1", "client_id": 1,
         "nature": "Processing", "execution_status": "In Progress", "po_date": date(2025, 7, 1),
         "start": date(2025, 7, 1), "end": date(2025, 8, 1), "owner": "O1",
         "sector": "Mining", "work_types": ["Processing"], "software_platform": None,
         "amount_excl": 5_000_000.0, "amount_incl": 5_900_000.0,
         "billed_excl": 6_000_000.0, "billed_incl": 7_080_000.0,
         "collected_incl": 7_080_000.0, "receivable": 0.0, "to_bill_excl": -1_000_000.0,
         "ar_priority": False, "invoice_status": "Over Billed",
         "billing_status": "Billed", "wo_status": "Active", "last_invoice_date": date(2026, 1, 1),
         "quality_flags": ["over_billed", "negative_to_bill"]},
        {"wo_id": "WO-003", "deal_name": "Renew-1", "client_code": "C2", "client_id": 2,
         "nature": "Inspection", "execution_status": "Completed", "po_date": date(2025, 8, 1),
         "start": date(2025, 8, 1), "end": date(2025, 9, 1), "owner": "O2",
         "sector": "Renewables", "work_types": ["Inspection"], "software_platform": None,
         "amount_excl": 15_000_000.0, "amount_incl": 17_700_000.0,
         "billed_excl": 15_000_000.0, "billed_incl": 17_700_000.0,
         "collected_incl": 17_700_000.0, "receivable": 0.0, "to_bill_excl": 0.0,
         "ar_priority": False, "invoice_status": "Fully Billed",
         "billing_status": "Billed", "wo_status": "Closed", "last_invoice_date": date(2026, 1, 1),
         "quality_flags": []},
    ]
    return pd.DataFrame(rows)


def _make_test_executor():
    deals_df = _create_sample_deals_df()
    wo_df = _create_sample_wo_df()
    dr = QualityReport(board="deals", rows_in=len(deals_df), rows_used=len(deals_df))
    wr = WOQualityReport(rows_in=len(wo_df), rows_used=len(wo_df))
    return ToolExecutor(deals_df, wo_df, dr, wr, today=date(2026, 9, 19))


# ---------------------------------------------------------------------------
# 1. Pipeline Summary Tests
# ---------------------------------------------------------------------------

def test_pipeline_summary_averages_and_rankings():
    df = _create_sample_deals_df()
    result = pipeline_summary(df, today=date(2026, 9, 19))
    data = result["data"]

    # 4 open deals total: Mine-Open-1 (25M), Mine-Open-2 (None), Renew-Open (50M), Av-Open (5M)
    assert data["total_count"] == 4
    assert data["value_count"] == 3
    assert data["missing_value_count"] == 1
    assert data["total_value"] == 80_000_000.0

    # Mean: 80M / 3 ≈ 26.67M
    assert data["mean_deal_value"] == pytest.approx(26_666_666.67, rel=1e-2)
    # Median of [5M, 25M, 50M] is 25M
    assert data["median_deal_value"] == 25_000_000.0

    # Stale close count: 1 deal (Mine-Open-1 has tentative close in 2025)
    assert data["stale_close_count"] == 1
    assert data["stale_close_pct"] == 25

    # Top sector by value: Renewables (50M)
    assert data["top_sector_by_value"]["sector"] == "Renewables"
    assert data["top_sector_by_value"]["value"] == 50_000_000.0

    # Top sector by count: Mining (2 open deals)
    assert data["top_sector_by_count"]["sector"] == "Mining"
    assert data["top_sector_by_count"]["count"] == 2


# ---------------------------------------------------------------------------
# 2. Work Order Summary Tests
# ---------------------------------------------------------------------------

def test_work_order_summary_metrics_and_anomalies():
    df = _create_sample_wo_df()
    result = work_order_summary(df, today=date(2026, 9, 19), gst_basis="excl")
    data = result["data"]

    assert data["count"] == 3
    assert data["order_value"] == 30_000_000.0
    assert data["billed"] == 27_000_000.0
    assert data["to_bill"] == 3_000_000.0

    # Anomalies
    assert data["over_billed_count"] == 1
    assert data["negative_to_bill_count"] == 1
    assert any("WO-002" in a for a in data["anomalies"])

    # Sector aggregation
    assert len(data["by_sector"]) == 2
    # Renewables has order_value 15M, Mining has 15M
    assert data["top_sector_by_order_value"] is not None


# ---------------------------------------------------------------------------
# 3. Sector Overview Win Rate & Zero Denominator Tests
# ---------------------------------------------------------------------------

def test_sector_overview_win_rate_and_zero_denominator():
    deals_df = _create_sample_deals_df()
    wo_df = _create_sample_wo_df()
    result = sector_overview(deals_df, wo_df, today=date(2026, 9, 19))
    data = result["data"]

    row_map = {r["sector"]: r for r in data["rows"]}

    # Mining: 3 Won, 1 Dead -> Win Rate = 3 / 4 = 75.0%
    assert row_map["Mining"]["won"] == 3
    assert row_map["Mining"]["dead"] == 1
    assert row_map["Mining"]["closed_deals"] == 4
    assert row_map["Mining"]["win_rate_pct"] == 75.0

    # Renewables: 1 Won, 1 Dead -> Win Rate = 1 / 2 = 50.0%
    assert row_map["Renewables"]["won"] == 1
    assert row_map["Renewables"]["dead"] == 1
    assert row_map["Renewables"]["closed_deals"] == 2
    assert row_map["Renewables"]["win_rate_pct"] == 50.0

    # Aviation: 0 Won, 0 Dead -> Win Rate MUST BE None (not 0.0%)
    assert row_map["Aviation"]["won"] == 0
    assert row_map["Aviation"]["dead"] == 0
    assert row_map["Aviation"]["closed_deals"] == 0
    assert row_map["Aviation"]["win_rate_pct"] is None

    # Highest win rate sector: Mining (75.0%)
    top_wr = data["rankings"]["top_win_rate_overall"]
    assert len(top_wr) == 1
    assert top_wr[0]["sector"] == "Mining"
    assert top_wr[0]["win_rate_pct"] == 75.0
    assert top_wr[0]["won"] == 3
    assert top_wr[0]["dead"] == 1


def test_sector_overview_tied_win_rate():
    # Test tie handling
    rows = [
        {"deal_name": "D1", "sector": "S1", "status": "Won", "value_inr": 100.0, "stage_name": "G", "quality_flags": []},
        {"deal_name": "D2", "sector": "S1", "status": "Dead", "value_inr": 100.0, "stage_name": "H", "quality_flags": []},
        {"deal_name": "D3", "sector": "S2", "status": "Won", "value_inr": 100.0, "stage_name": "G", "quality_flags": []},
        {"deal_name": "D4", "sector": "S2", "status": "Dead", "value_inr": 100.0, "stage_name": "H", "quality_flags": []},
    ]
    deals_df = pd.DataFrame(rows)
    wo_df = pd.DataFrame([])
    result = sector_overview(deals_df, wo_df, today=date(2026, 9, 19))
    top_wr = result["data"]["rankings"]["top_win_rate_overall"]
    assert len(top_wr) == 2
    assert {s["sector"] for s in top_wr} == {"S1", "S2"}
    assert top_wr[0]["win_rate_pct"] == 50.0


# ---------------------------------------------------------------------------
# 4. Degraded Mode Direct Answers
# ---------------------------------------------------------------------------

def test_degraded_mode_highest_win_rate_question():
    """Verify that asking for highest win rate in degraded mode returns sector, %, won, and dead counts."""
    executor = _make_test_executor()
    result = run_agent(
        question="Which sector has the highest win rate, and how many won and dead deals are behind that percentage?",
        history=[],
        executor=executor,
        llm=None,
        today=date(2026, 9, 19),
        data_as_of=None,
        max_llm_calls=3,
        llm_disabled=True,
    )
    assert result.degraded is True
    answer = result.answer

    # Must contain Mining, 75.0%, 3 Won, 1 Dead
    assert "Mining" in answer
    assert "75" in answer
    assert "3" in answer
    assert "1" in answer


def test_degraded_mode_open_pipeline_question():
    executor = _make_test_executor()
    result = run_agent(
        question="How is our open pipeline looking overall?",
        history=[],
        executor=executor,
        llm=None,
        today=date(2026, 9, 19),
        data_as_of=None,
        max_llm_calls=3,
        llm_disabled=True,
    )
    assert result.degraded is True
    answer = result.answer
    assert "Open pipeline" in answer or "pipeline" in answer.lower()
    assert "8.0 Cr" in answer or "80" in answer


# ---------------------------------------------------------------------------
# 5. Tool Result Structured Data Reaching LLM Context
# ---------------------------------------------------------------------------

class MessageCapturingFakeProvider:
    """Fake LLM that records the message history passed to it."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.captured_messages: list[list[LLMMessage]] = []

    def generate(self, system, messages, tools) -> LLMResponse:
        self.captured_messages.append(list(messages))
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(text="Final answer.", tool_calls=[])


def test_structured_data_passed_to_llm():
    """Verify that Structured Data (JSON) is included in the tool result messages passed to the LLM."""
    tc = ToolCall(id="c1", name="sector_overview", args={})
    fake = MessageCapturingFakeProvider([
        LLMResponse(text=None, tool_calls=[tc], model_used="fake"),
        LLMResponse(text="Mining has the highest win rate.", tool_calls=[], model_used="fake"),
    ])
    executor = _make_test_executor()
    result = run_agent(
        question="Which sector has the highest win rate?",
        history=[],
        executor=executor,
        llm=fake,
        today=date(2026, 9, 19),
        data_as_of=None,
        max_llm_calls=3,
        llm_disabled=False,
    )
    assert result.llm_calls == 2
    assert len(fake.captured_messages) == 2

    # Second LLM call must receive the tool result with Structured Data (JSON)
    second_call_msgs = fake.captured_messages[1]
    tool_msg = next(m for m in second_call_msgs if "[called tools]" in m.content)
    assert "Structured Data (JSON):" in tool_msg.content
    assert "win_rate_pct" in tool_msg.content
    assert "Mining" in tool_msg.content
    assert "Renewables" in tool_msg.content
