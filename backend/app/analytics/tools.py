"""Analytics tools: pipeline_summary, work_order_summary, sector_overview,
data_quality_report, leadership_brief.

Every function takes validated params and returns a ToolResult dict.
Numbers computed in pandas; the LLM only narrates.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Literal

import pandas as pd

from app.normalize.common import fmt_inr
from app.analytics.periods import Period, resolve_period

# Type alias for coverage entries
CoverageEntry = dict[str, Any]
ToolResult = dict[str, Any]

_PERIOD_SPECS = Literal["all_time", "this_quarter", "last_quarter", "this_fy", "last_fy", "ytd"]
GST_RATE = 1.18


def _data_as_of(df: pd.DataFrame, date_cols: list[str]) -> date | None:
    """Return the maximum date seen across specified columns."""
    latest: date | None = None
    for col in date_cols:
        if col not in df.columns:
            continue
        for val in df[col]:
            if isinstance(val, date):
                if latest is None or val > latest:
                    latest = val
    return latest


def _filter_period(df: pd.DataFrame, date_col: str, period: Period) -> pd.DataFrame:
    """Filter df rows to those whose date_col falls within period."""
    if period.start is None:
        return df
    if date_col not in df.columns:
        return df
    mask = pd.Series([True] * len(df), index=df.index)
    dates = df[date_col]
    if period.start:
        mask = mask & dates.apply(lambda d: d is not None and d >= period.start)
    if period.end:
        mask = mask & dates.apply(lambda d: d is not None and d <= period.end)
    return df[mask]


def _available_range(df: pd.DataFrame, date_col: str) -> str:
    """Return a human-readable date range string for the given column."""
    if date_col not in df.columns:
        return "unknown"
    dates = df[date_col].dropna()
    if len(dates) == 0:
        return "no dates available"
    mn = min(dates)
    mx = max(dates)
    return f"{mn} to {mx}"


def _concentration(values: pd.Series) -> dict[str, Any]:
    """Return top-1 and top-3 share of total."""
    total = values.sum()
    if total == 0 or len(values) == 0:
        return {"top1_share": None, "top3_share": None, "total_excl_top3": None}
    sorted_vals = values.sort_values(ascending=False)
    top1 = sorted_vals.iloc[0] if len(sorted_vals) >= 1 else 0
    top3 = sorted_vals.iloc[:3].sum()
    excl_top3 = sorted_vals.iloc[3:].sum()
    return {
        "top1_share": round(top1 / total * 100, 1),
        "top3_share": round(top3 / total * 100, 1),
        "total_excl_top3": float(excl_top3),
        "total_excl_top3_fmt": fmt_inr(excl_top3),
    }


# ---------------------------------------------------------------------------
# pipeline_summary
# ---------------------------------------------------------------------------

def pipeline_summary(
    deals_df: pd.DataFrame,
    today: date,
    period_spec: str = "all_time",
    sector: str | None = None,
    owner: str | None = None,
    fy_start_month: int = 4,
) -> ToolResult:
    """Summarise open pipeline: count, value, coverage, by stage, top 5 deals, concentration."""
    period = resolve_period(period_spec, today, fy_start_month)

    # Start from full clean df
    df = deals_df[deals_df["status"] == "Open"].copy()

    # Period filter: open pipeline uses tentative_close date
    if period.start is not None:
        df = _filter_period(df, "tentative_close", period)

    # Optional filters
    caveats: list[str] = []
    assumptions: list[str] = [f"Period: {period.label}", "Status = Open only."]

    if sector:
        # sector is already a list of canonical sectors (handled by the agent/tool caller)
        if isinstance(sector, list):
            df = df[df["sector"].isin(sector)]
            assumptions.append(f"Sector filter: {', '.join(sector)}.")
        else:
            df = df[df["sector"] == sector]
            assumptions.append(f"Sector filter: {sector}.")

    if owner:
        df = df[df["owner"] == owner]
        assumptions.append(f"Owner filter: {owner}.")

    data_as_of = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])

    if data_as_of and (today - data_as_of).days > 45:
        caveats.append(f"Data ends around {data_as_of}; today is {today}. Results may be stale.")

    no_data = len(df) == 0

    if no_data:
        avail = _available_range(deals_df[deals_df["status"] == "Open"], "tentative_close")
        return {
            "tool": "pipeline_summary",
            "no_data_in_period": True,
            "period": {"label": period.label, "start": str(period.start), "end": str(period.end)},
            "available_range": avail,
            "data": {},
            "display": {"summary": f"No open deals found for {period.label}. Data available: {avail}."},
            "coverage": [],
            "caveats": caveats + ["No records match the selected period/filters."],
            "assumptions_used": assumptions,
            "data_as_of": str(data_as_of) if data_as_of else None,
        }

    total_count = len(df)
    with_value = df["value_inr"].notna()
    value_count = int(with_value.sum())
    total_value = float(df.loc[with_value, "value_inr"].sum()) if value_count > 0 else 0.0

    # Stale close dates
    stale = df["quality_flags"].apply(lambda f: "open_close_date_past" in f)
    stale_count = int(stale.sum())
    stale_pct = round(stale_count / total_count * 100) if total_count > 0 else 0

    # By stage
    stage_agg = (
        df.groupby("stage_name", dropna=False)
        .agg(count=("deal_name", "count"), value=("value_inr", "sum"))
        .reset_index()
        .rename(columns={"stage_name": "stage"})
    )
    stage_agg["value_fmt"] = stage_agg["value"].apply(fmt_inr)

    # By sector
    sector_agg = (
        df.groupby("sector", dropna=False)
        .agg(count=("deal_name", "count"), value=("value_inr", "sum"))
        .reset_index()
        .sort_values("value", ascending=False)
    )
    sector_agg["value_fmt"] = sector_agg["value"].apply(fmt_inr)

    # Top 5 deals (by value)
    top5 = (
        df[with_value]
        .nlargest(5, "value_inr")[["deal_name", "sector", "stage_name", "value_inr", "tentative_close"]]
        .copy()
    )
    top5["value_fmt"] = top5["value_inr"].apply(fmt_inr)
    top5_list = top5.to_dict("records")

    # Concentration
    conc = _concentration(df.loc[with_value, "value_inr"])

    if stale_count:
        caveats.append(f"{stale_count} of {total_count} open deals ({stale_pct}%) have a Tentative Close Date in the past.")
    if value_count < total_count:
        caveats.append(f"Deal value present for {value_count} of {total_count} open deals; missing excluded from totals.")
    if conc.get("top3_share") and conc["top3_share"] > 60:
        caveats.append(f"Top-3 deals represent {conc['top3_share']}% of open pipeline value — high concentration.")

    return {
        "tool": "pipeline_summary",
        "no_data_in_period": False,
        "period": {"label": period.label, "start": str(period.start), "end": str(period.end)},
        "data": {
            "total_count": total_count,
            "value_count": value_count,
            "total_value": total_value,
            "stale_close_count": stale_count,
            "concentration": conc,
            "by_stage": stage_agg.to_dict("records"),
            "by_sector": sector_agg.to_dict("records"),
            "top_5_deals": top5_list,
        },
        "display": {
            "total_value_fmt": fmt_inr(total_value),
            "summary": (
                f"Open pipeline: {total_count} deals, {fmt_inr(total_value)} "
                f"(value present for {value_count} of {total_count})."
            ),
            "concentration": (
                f"Top-3 deals: {conc.get('top3_share', 'n/a')}% of total. "
                f"Excluding top 3: {conc.get('total_excl_top3_fmt', 'n/a')}."
            ),
            "stale_close": f"{stale_count}/{total_count} open deals have past tentative close date.",
        },
        "coverage": [
            {"metric": "open_deal_value", "used": value_count, "total": total_count, "note": "Deals with a monetary value"}
        ],
        "caveats": caveats,
        "assumptions_used": assumptions,
        "data_as_of": str(data_as_of) if data_as_of else None,
    }


# ---------------------------------------------------------------------------
# work_order_summary
# ---------------------------------------------------------------------------

def work_order_summary(
    wo_df: pd.DataFrame,
    today: date,
    period_spec: str = "all_time",
    sector: str | None = None,
    owner: str | None = None,
    gst_basis: str = "excl",
    fy_start_month: int = 4,
) -> ToolResult:
    """Summarise work orders: value, billed, to-bill, collected, receivable, anomalies."""
    period = resolve_period(period_spec, today, fy_start_month)
    df = wo_df.copy()

    caveats: list[str] = []
    assumptions: list[str] = [
        f"Period: {period.label} (using PO date).",
        f"GST basis: {gst_basis}.",
    ]
    if gst_basis == "excl":
        assumptions.append("Collected and receivable (incl-GST only in source) divided by 1.18 to get excl-GST estimate.")

    df = _filter_period(df, "po_date", period)

    if sector:
        if isinstance(sector, list):
            df = df[df["sector"].isin(sector)]
            assumptions.append(f"Sector filter: {', '.join(sector)}.")
        else:
            df = df[df["sector"] == sector]
            assumptions.append(f"Sector filter: {sector}.")

    if owner:
        df = df[df["owner"] == owner]

    data_as_of = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    if data_as_of and (today - data_as_of).days > 45:
        caveats.append(f"Data ends around {data_as_of}; today is {today}. Results may be stale.")

    no_data = len(df) == 0
    if no_data:
        avail = _available_range(wo_df, "po_date")
        return {
            "tool": "work_order_summary",
            "no_data_in_period": True,
            "period": {"label": period.label},
            "available_range": avail,
            "data": {},
            "display": {"summary": f"No work orders found for {period.label}. Data available: {avail}."},
            "coverage": [],
            "caveats": caveats + ["No records match the selected period/filters."],
            "assumptions_used": assumptions,
            "data_as_of": str(data_as_of) if data_as_of else None,
        }

    def _col(basis_col: str, fallback_col: str | None = None) -> pd.Series:
        if basis_col in df.columns:
            return df[basis_col]
        if fallback_col and fallback_col in df.columns:
            return df[fallback_col]
        return pd.Series([None] * len(df), index=df.index)

    if gst_basis == "excl":
        order_col = _col("amount_excl")
        billed_col = _col("billed_excl")
        collected_col = _col("collected_incl").apply(lambda x: x / GST_RATE if x is not None and not math.isnan(float(x if x else 0)) else None)
        receivable_col = _col("receivable").apply(lambda x: x / GST_RATE if x is not None and not math.isnan(float(x if x else 0)) else None)
    else:
        order_col = _col("amount_incl")
        billed_col = _col("billed_incl")
        collected_col = _col("collected_incl")
        receivable_col = _col("receivable")

    def _safe_sum(s: pd.Series) -> float:
        return float(s.dropna().sum())

    order_val = _safe_sum(order_col)
    billed_val = _safe_sum(billed_col)
    collected_val = _safe_sum(collected_col)
    receivable_val = _safe_sum(receivable_col)
    to_bill_val = order_val - billed_val if order_val else 0.0

    billing_pct = round(billed_val / order_val * 100, 1) if order_val > 0 else None
    collection_pct = round(collected_val / billed_val * 100, 1) if billed_val > 0 else None

    # Execution status mix
    exec_counts = df["execution_status"].value_counts(dropna=False).to_dict()

    # Anomalies
    anomalies = []
    for _, row in df.iterrows():
        flags = row.get("quality_flags", [])
        if "over_billed" in flags:
            anomalies.append(f"Over-billed: {row.get('wo_id', '?')} (deal: {row.get('deal_name', '?')})")
        if "negative_to_bill" in flags:
            anomalies.append(f"Negative to-bill: {row.get('wo_id', '?')}")

    # By sector
    sector_agg = (
        df.groupby("sector")
        .agg(count=("wo_id", "count"))
        .reset_index()
    )

    if order_val < billed_val:
        caveats.append("Total billed exceeds total order value (anomalies present).")
    if anomalies:
        caveats.append(f"{len(anomalies)} billing anomaly(s) detected.")

    return {
        "tool": "work_order_summary",
        "no_data_in_period": False,
        "period": {"label": period.label},
        "data": {
            "count": len(df),
            "order_value": order_val,
            "billed": billed_val,
            "to_bill": to_bill_val,
            "collected": collected_val,
            "receivable": receivable_val,
            "billing_pct": billing_pct,
            "collection_pct": collection_pct,
            "exec_status_mix": exec_counts,
            "anomalies": anomalies[:10],
            "by_sector": sector_agg.to_dict("records"),
        },
        "display": {
            "summary": (
                f"{len(df)} work orders. Order value: {fmt_inr(order_val)}, "
                f"Billed: {fmt_inr(billed_val)} ({billing_pct}%), "
                f"Collected: {fmt_inr(collected_val)} ({collection_pct}%), "
                f"Receivable: {fmt_inr(receivable_val)}, "
                f"Still to bill: {fmt_inr(to_bill_val)}."
            ),
        },
        "coverage": [
            {"metric": "order_value", "used": int(order_col.notna().sum()), "total": len(df), "note": "Rows with order amount"},
            {"metric": "billed", "used": int(billed_col.notna().sum()), "total": len(df), "note": "Rows with billed amount"},
        ],
        "caveats": caveats,
        "assumptions_used": assumptions,
        "data_as_of": str(data_as_of) if data_as_of else None,
    }


# ---------------------------------------------------------------------------
# sector_overview
# ---------------------------------------------------------------------------

def sector_overview(
    deals_df: pd.DataFrame,
    wo_df: pd.DataFrame,
    today: date,
    gst_basis: str = "excl",
) -> ToolResult:
    """Cross-board sector view: open pipeline, win rate, work order value."""
    caveats = [
        "Cross-board matching is at sector level only (no clean deal-level key).",
        f"GST basis: {gst_basis}.",
    ]
    assumptions = [
        "All time; no period filter.",
        "Win rate = Won / (Won + Dead) by count.",
        "Sectors with no deals AND no work orders are excluded.",
    ]

    # Deals side
    d = deals_df.copy()
    open_by_sector = (
        d[d["status"] == "Open"]
        .groupby("sector")
        .agg(open_count=("deal_name", "count"), open_value=("value_inr", "sum"))
        .reset_index()
    )
    won_by_sector = d[d["status"] == "Won"].groupby("sector").size().rename("won")
    dead_by_sector = d[d["status"] == "Dead"].groupby("sector").size().rename("dead")

    deal_sector = (
        open_by_sector
        .merge(won_by_sector, on="sector", how="outer")
        .merge(dead_by_sector, on="sector", how="outer")
        .fillna(0)
    )
    deal_sector["win_rate"] = deal_sector.apply(
        lambda r: round(r["won"] / (r["won"] + r["dead"]) * 100, 1)
        if (r["won"] + r["dead"]) > 0 else None,
        axis=1,
    )

    # WO side
    wo = wo_df.copy()
    if gst_basis == "excl":
        wo["_order"] = wo["amount_excl"]
        wo["_billed"] = wo["billed_excl"]
        wo["_receivable"] = wo["receivable"].apply(lambda x: x / GST_RATE if x is not None else None)
    else:
        wo["_order"] = wo["amount_incl"]
        wo["_billed"] = wo["billed_incl"]
        wo["_receivable"] = wo["receivable"]

    wo_by_sector = (
        wo.groupby("sector")
        .agg(wo_count=("wo_id", "count"), wo_value=("_order", "sum"), wo_billed=("_billed", "sum"), wo_receivable=("_receivable", "sum"))
        .reset_index()
    )

    merged = deal_sector.merge(wo_by_sector, on="sector", how="outer").fillna(0)
    merged = merged[merged["sector"] != ""]

    rows = []
    for _, r in merged.iterrows():
        rows.append({
            "sector": r["sector"],
            "open_count": int(r.get("open_count", 0)),
            "open_value": float(r.get("open_value", 0)),
            "open_value_fmt": fmt_inr(float(r.get("open_value", 0))),
            "won": int(r.get("won", 0)),
            "dead": int(r.get("dead", 0)),
            "win_rate_pct": r.get("win_rate"),
            "wo_count": int(r.get("wo_count", 0)),
            "wo_value": float(r.get("wo_value", 0)),
            "wo_value_fmt": fmt_inr(float(r.get("wo_value", 0))),
            "wo_billed_fmt": fmt_inr(float(r.get("wo_billed", 0))),
            "wo_receivable_fmt": fmt_inr(float(r.get("wo_receivable", 0))),
        })

    data_as_of_d = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])
    data_as_of_w = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    data_as_of = max(filter(None, [data_as_of_d, data_as_of_w]), default=None)

    return {
        "tool": "sector_overview",
        "no_data_in_period": False,
        "data": {"rows": rows},
        "display": {
            "summary": f"Sector overview across {len(deals_df)} deals and {len(wo_df)} work orders.",
        },
        "coverage": [],
        "caveats": caveats,
        "assumptions_used": assumptions,
        "data_as_of": str(data_as_of) if data_as_of else None,
    }


# ---------------------------------------------------------------------------
# data_quality_report
# ---------------------------------------------------------------------------

def data_quality_report(
    deals_report_lines: list[str],
    wo_report_lines: list[str],
) -> ToolResult:
    """Return quality summary from both boards."""
    all_lines = deals_report_lines + ["---"] + wo_report_lines
    return {
        "tool": "data_quality_report",
        "no_data_in_period": False,
        "data": {
            "deals_lines": deals_report_lines,
            "wo_lines": wo_report_lines,
        },
        "display": {
            "summary": "\n".join(all_lines),
        },
        "coverage": [],
        "caveats": [],
        "assumptions_used": [],
        "data_as_of": None,
    }


# ---------------------------------------------------------------------------
# leadership_brief
# ---------------------------------------------------------------------------

def leadership_brief(
    deals_df: pd.DataFrame,
    wo_df: pd.DataFrame,
    today: date,
    gst_basis: str = "excl",
    fy_start_month: int = 4,
    deals_report_lines: list[str] | None = None,
    wo_report_lines: list[str] | None = None,
) -> ToolResult:
    """Compose a paste-ready leadership update from pipeline + work orders."""
    pipe = pipeline_summary(deals_df, today, "all_time", fy_start_month=fy_start_month)
    wo = work_order_summary(wo_df, today, "all_time", gst_basis=gst_basis, fy_start_month=fy_start_month)

    # Win rate
    won = len(deals_df[deals_df["status"] == "Won"])
    dead = len(deals_df[deals_df["status"] == "Dead"])
    win_rate = round(won / (won + dead) * 100, 1) if (won + dead) > 0 else None

    pipe_data = pipe.get("data", {})
    wo_data = wo.get("data", {})

    risks = []
    if pipe_data.get("concentration", {}).get("top3_share", 0) > 60:
        risks.append(f"Pipeline concentration: top-3 deals = {pipe_data['concentration']['top3_share']}% of open value.")
    stale = pipe_data.get("stale_close_count", 0)
    total_open = pipe_data.get("total_count", 0)
    if stale and total_open:
        risks.append(f"{stale}/{total_open} open deals have a stale Tentative Close Date (past).")
    if wo_data.get("receivable", 0) and wo_data["receivable"] > 0:
        risks.append(f"Outstanding receivables: {fmt_inr(wo_data['receivable'])}.")
    if not risks:
        risks.append("No major data-identified risks (verify manually).")

    opportunities = [
        f"Open pipeline: {fmt_inr(pipe_data.get('total_value', 0))} across {pipe_data.get('total_count', 0)} deals.",
        f"Still to bill: {fmt_inr(wo_data.get('to_bill', 0))} — execution backlog with revenue potential.",
    ]
    if win_rate is not None:
        opportunities.append(f"Win rate: {win_rate}% (won {won}, lost {dead}) — benchmark against industry.")

    caveats = (pipe.get("caveats", []) + wo.get("caveats", []) +
               (deals_report_lines or [])[:3] + (wo_report_lines or [])[:3])

    display_lines = [
        "## Leadership Update",
        f"**Pipeline:** {pipe['display'].get('summary', '')}",
        f"**Work Orders:** {wo['display'].get('summary', '')}",
        f"**Win Rate:** {win_rate}% (won {won} of {won + dead} closed deals)",
        "",
        "### Top Risks",
    ] + [f"- {r}" for r in risks[:3]] + [
        "",
        "### Opportunities",
    ] + [f"- {o}" for o in opportunities[:3]] + [
        "",
        "### Data Caveats",
    ] + [f"- {c}" for c in caveats[:4]]

    data_as_of_d = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])
    data_as_of_w = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    data_as_of = max(filter(None, [data_as_of_d, data_as_of_w]), default=None)

    return {
        "tool": "leadership_brief",
        "no_data_in_period": False,
        "data": {
            "pipeline": pipe_data,
            "work_orders": wo_data,
            "win_rate": win_rate,
            "won": won,
            "dead": dead,
            "risks": risks,
            "opportunities": opportunities,
        },
        "display": {
            "summary": "\n".join(display_lines),
        },
        "coverage": pipe.get("coverage", []) + wo.get("coverage", []),
        "caveats": caveats[:6],
        "assumptions_used": pipe.get("assumptions_used", []) + wo.get("assumptions_used", []),
        "data_as_of": str(data_as_of) if data_as_of else None,
    }
