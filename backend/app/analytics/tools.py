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
    missing_value_count = total_count - value_count
    total_value = float(df.loc[with_value, "value_inr"].sum()) if value_count > 0 else 0.0
    mean_val = float(round(total_value / value_count, 2)) if value_count > 0 else 0.0
    median_val = float(df.loc[with_value, "value_inr"].median()) if value_count > 0 else 0.0

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
    sector_agg_records = sector_agg.to_dict("records")
    top_sector_by_value = sector_agg_records[0] if sector_agg_records else None

    sector_by_count = sector_agg.sort_values("count", ascending=False)
    sector_by_count_records = sector_by_count.to_dict("records")
    top_sector_by_count = sector_by_count_records[0] if sector_by_count_records else None

    # Top 5 deals (by value)
    top5 = (
        df[with_value]
        .nlargest(5, "value_inr")[["deal_name", "sector", "stage_name", "value_inr", "tentative_close"]]
        .copy()
    )
    top5["value_fmt"] = top5["value_inr"].apply(fmt_inr)
    top5_list = top5.to_dict("records")

    # Stale deals sample
    stale_sample = []
    if stale_count:
        stale_df = df[stale].sort_values("value_inr", ascending=False)
        for _, r in stale_df.head(5).iterrows():
            stale_sample.append({
                "deal_name": r.get("deal_name"),
                "sector": r.get("sector"),
                "value_fmt": fmt_inr(float(r["value_inr"])) if pd.notna(r.get("value_inr")) else "Missing",
                "tentative_close": str(r.get("tentative_close")) if r.get("tentative_close") else None,
            })

    # Concentration
    conc = _concentration(df.loc[with_value, "value_inr"])

    if stale_count:
        caveats.append(f"{stale_count} of {total_count} open deals ({stale_pct}%) have a Tentative Close Date in the past.")
    if value_count < total_count:
        caveats.append(f"Deal value present for {value_count} of {total_count} open deals; {missing_value_count} missing excluded from totals.")
    if conc.get("top3_share") and conc["top3_share"] > 60:
        caveats.append(f"Top-3 deals represent {conc['top3_share']}% of open pipeline value — high concentration.")

    summary_lines = [
        f"**Open pipeline:** {total_count} deals totaling {fmt_inr(total_value)} "
        f"(value present for {value_count} of {total_count}; {missing_value_count} missing value).",
        f"**Deal sizes:** Average: {fmt_inr(mean_val)}, Median: {fmt_inr(median_val)}.",
    ]
    if top_sector_by_value:
        summary_lines.append(
            f"**Largest sector by value:** {top_sector_by_value['sector']} "
            f"({top_sector_by_value['value_fmt']}, {top_sector_by_value['count']} deals)."
        )
    if top_sector_by_count:
        summary_lines.append(
            f"**Most open deals:** {top_sector_by_count['sector']} "
            f"({top_sector_by_count['count']} deals, {top_sector_by_count['value_fmt']})."
        )
    if stale_count:
        summary_lines.append(
            f"**Overdue close dates:** {stale_count} of {total_count} open deals ({stale_pct}%) "
            f"have tentative close dates in the past."
        )

    return {
        "tool": "pipeline_summary",
        "no_data_in_period": False,
        "period": {"label": period.label, "start": str(period.start), "end": str(period.end)},
        "data": {
            "total_count": total_count,
            "value_count": value_count,
            "missing_value_count": missing_value_count,
            "total_value": total_value,
            "total_value_fmt": fmt_inr(total_value),
            "mean_deal_value": mean_val,
            "mean_deal_value_fmt": fmt_inr(mean_val),
            "median_deal_value": median_val,
            "median_deal_value_fmt": fmt_inr(median_val),
            "stale_close_count": stale_count,
            "stale_close_pct": stale_pct,
            "stale_deals_sample": stale_sample,
            "concentration": conc,
            "by_stage": stage_agg.to_dict("records"),
            "by_sector": sector_agg_records,
            "by_sector_by_count": sector_by_count_records,
            "top_sector_by_value": top_sector_by_value,
            "top_sector_by_count": top_sector_by_count,
            "top_5_deals": top5_list,
        },
        "display": {
            "total_value_fmt": fmt_inr(total_value),
            "summary": "\n".join(summary_lines),
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
    anomaly_details = []
    over_billed_count = 0
    negative_to_bill_count = 0
    for _, row in df.iterrows():
        flags = row.get("quality_flags", [])
        if "over_billed" in flags:
            over_billed_count += 1
            wo_id = row.get("wo_id", "?")
            deal_name = row.get("deal_name", "?")
            sec = row.get("sector", "Unspecified")
            anomalies.append(f"Over-billed: {wo_id} (deal: {deal_name})")
            anomaly_details.append({
                "wo_id": wo_id,
                "deal_name": deal_name,
                "sector": sec,
                "issue": "Over-billed",
            })
        if "negative_to_bill" in flags:
            negative_to_bill_count += 1
            wo_id = row.get("wo_id", "?")
            deal_name = row.get("deal_name", "?")
            sec = row.get("sector", "Unspecified")
            anomalies.append(f"Negative to-bill: {wo_id}")
            anomaly_details.append({
                "wo_id": wo_id,
                "deal_name": deal_name,
                "sector": sec,
                "issue": "Negative to-bill",
            })

    # By sector aggregation with order_value and billed_value
    df["_sec_order"] = order_col
    df["_sec_billed"] = billed_col
    sector_agg = (
        df.groupby("sector", dropna=False)
        .agg(
            wo_count=("wo_id", "count"),
            order_value=("_sec_order", "sum"),
            billed_value=("_sec_billed", "sum"),
        )
        .reset_index()
        .sort_values("order_value", ascending=False)
    )
    sector_agg["order_value_fmt"] = sector_agg["order_value"].apply(fmt_inr)
    sector_agg["billed_value_fmt"] = sector_agg["billed_value"].apply(fmt_inr)
    sector_agg_records = sector_agg.to_dict("records")
    top_wo_sector = sector_agg_records[0] if sector_agg_records else None

    if order_val < billed_val:
        caveats.append("Total billed exceeds total order value (anomalies present).")
    if anomalies:
        caveats.append(f"{len(anomalies)} billing anomaly(s) detected ({over_billed_count} over-billed, {negative_to_bill_count} negative to-bill).")

    summary_lines = [
        f"**Work orders:** {len(df)} total. Order value: {fmt_inr(order_val)}, "
        f"Billed: {fmt_inr(billed_val)} ({billing_pct}%), "
        f"Collected: {fmt_inr(collected_val)} ({collection_pct}% of billed), "
        f"Receivable: {fmt_inr(receivable_val)}, "
        f"Still to bill: {fmt_inr(to_bill_val)}.",
    ]
    if top_wo_sector:
        summary_lines.append(
            f"**Highest order value sector:** {top_wo_sector['sector']} "
            f"({top_wo_sector['order_value_fmt']}, {top_wo_sector['wo_count']} work orders, {top_wo_sector['billed_value_fmt']} billed)."
        )
    if anomalies:
        summary_lines.append(
            f"**Billing anomalies:** {len(anomalies)} detected ({over_billed_count} over-billed, {negative_to_bill_count} negative to-bill)."
        )

    return {
        "tool": "work_order_summary",
        "no_data_in_period": False,
        "period": {"label": period.label},
        "data": {
            "count": len(df),
            "order_value": order_val,
            "order_value_fmt": fmt_inr(order_val),
            "billed": billed_val,
            "billed_fmt": fmt_inr(billed_val),
            "to_bill": to_bill_val,
            "to_bill_fmt": fmt_inr(to_bill_val),
            "collected": collected_val,
            "collected_fmt": fmt_inr(collected_val),
            "receivable": receivable_val,
            "receivable_fmt": fmt_inr(receivable_val),
            "billing_pct": billing_pct,
            "collection_pct": collection_pct,
            "exec_status_mix": exec_counts,
            "anomalies": anomalies[:10],
            "anomaly_details": anomaly_details[:10],
            "over_billed_count": over_billed_count,
            "negative_to_bill_count": negative_to_bill_count,
            "by_sector": sector_agg_records,
            "top_sector_by_order_value": top_wo_sector,
        },
        "display": {
            "summary": "\n".join(summary_lines),
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
    )
    for col in ["open_count", "open_value", "won", "dead"]:
        if col in deal_sector.columns:
            deal_sector[col] = pd.to_numeric(deal_sector[col], errors="coerce").fillna(0)

    # WO side
    wo = wo_df.copy()
    if len(wo) > 0 and "sector" in wo.columns:
        if gst_basis == "excl":
            wo["_order"] = wo["amount_excl"] if "amount_excl" in wo.columns else 0.0
            wo["_billed"] = wo["billed_excl"] if "billed_excl" in wo.columns else 0.0
            rec_series = wo["receivable"] if "receivable" in wo.columns else pd.Series([None] * len(wo))
            wo["_receivable"] = rec_series.apply(
                lambda x: x / GST_RATE if x is not None and not math.isnan(float(x if x else 0)) else None
            )
        else:
            wo["_order"] = wo["amount_incl"] if "amount_incl" in wo.columns else 0.0
            wo["_billed"] = wo["billed_incl"] if "billed_incl" in wo.columns else 0.0
            wo["_receivable"] = wo["receivable"] if "receivable" in wo.columns else pd.Series([None] * len(wo))

        wo_id_col = "wo_id" if "wo_id" in wo.columns else "sector"
        wo_by_sector = (
            wo.groupby("sector")
            .agg(wo_count=(wo_id_col, "count"), wo_value=("_order", "sum"), wo_billed=("_billed", "sum"), wo_receivable=("_receivable", "sum"))
            .reset_index()
        )
    else:
        wo_by_sector = pd.DataFrame(columns=["sector", "wo_count", "wo_value", "wo_billed", "wo_receivable"])

    merged = deal_sector.merge(wo_by_sector, on="sector", how="outer")
    num_cols = ["open_count", "open_value", "won", "dead", "wo_count", "wo_value", "wo_billed", "wo_receivable"]
    for col in num_cols:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    merged = merged[merged["sector"] != ""]
    merged = merged[merged["sector"].notna()]

    # Win rate = Won / (Won + Dead) strictly. None when Won + Dead == 0.
    merged["win_rate"] = merged.apply(
        lambda r: round(r["won"] / (r["won"] + r["dead"]) * 100, 1)
        if (r["won"] + r["dead"]) > 0 else None,
        axis=1,
    )

    rows = []
    for _, r in merged.iterrows():
        won_cnt = int(r.get("won", 0))
        dead_cnt = int(r.get("dead", 0))
        closed_cnt = won_cnt + dead_cnt
        wr = r.get("win_rate")
        wr_pct = float(wr) if wr is not None and not pd.isna(wr) else None

        rows.append({
            "sector": r["sector"],
            "open_count": int(r.get("open_count", 0)),
            "open_value": float(r.get("open_value", 0)),
            "open_value_fmt": fmt_inr(float(r.get("open_value", 0))),
            "won": won_cnt,
            "dead": dead_cnt,
            "closed_deals": closed_cnt,
            "win_rate_pct": wr_pct,
            "wo_count": int(r.get("wo_count", 0)),
            "wo_value": float(r.get("wo_value", 0)),
            "wo_value_fmt": fmt_inr(float(r.get("wo_value", 0))),
            "wo_billed": float(r.get("wo_billed", 0)),
            "wo_billed_fmt": fmt_inr(float(r.get("wo_billed", 0))),
            "wo_receivable": float(r.get("wo_receivable", 0)),
            "wo_receivable_fmt": fmt_inr(float(r.get("wo_receivable", 0))),
        })

    # Rankings
    # 1. By win rate (only sectors where closed_deals > 0)
    with_closed = [r for r in rows if r["closed_deals"] > 0]
    by_win_rate = sorted(with_closed, key=lambda x: (x["win_rate_pct"] or 0, x["won"]), reverse=True)

    top_win_rate_overall = []
    if by_win_rate:
        max_rate = by_win_rate[0]["win_rate_pct"]
        top_win_rate_overall = [r for r in by_win_rate if r["win_rate_pct"] == max_rate]

    # Substantial volume sectors (closed_deals >= 5)
    volume_sectors = [r for r in with_closed if r["closed_deals"] >= 5]
    by_win_rate_volume = sorted(volume_sectors, key=lambda x: (x["win_rate_pct"] or 0, x["won"]), reverse=True)
    top_win_rate_established = by_win_rate_volume[0] if by_win_rate_volume else None

    # 2. By open pipeline value
    by_open_pipeline = sorted(rows, key=lambda x: x["open_value"], reverse=True)
    top_pipeline_sector = by_open_pipeline[0] if by_open_pipeline and by_open_pipeline[0]["open_value"] > 0 else None

    # 3. By open deal count
    by_open_deals = sorted(rows, key=lambda x: x["open_count"], reverse=True)
    top_open_deals_sector = by_open_deals[0] if by_open_deals and by_open_deals[0]["open_count"] > 0 else None

    # 4. By work order value
    by_wo_value = sorted(rows, key=lambda x: x["wo_value"], reverse=True)
    top_wo_sector = by_wo_value[0] if by_wo_value and by_wo_value[0]["wo_value"] > 0 else None

    # Dynamic summary
    summary_lines = []
    if top_win_rate_overall:
        if len(top_win_rate_overall) == 1:
            top = top_win_rate_overall[0]
            summary_lines.append(
                f"**Highest win rate:** {top['sector']} at {top['win_rate_pct']}%. "
                f"That is based on {top['won']} Won deals and {top['dead']} Dead deals "
                f"({top['closed_deals']} closed deals)."
            )
        else:
            tied_details = ", ".join(
                f"**{s['sector']}** at {s['win_rate_pct']}% ({s['won']} Won, {s['dead']} Dead)"
                for s in top_win_rate_overall
            )
            summary_lines.append(f"**Highest win rate (tied):** {tied_details}.")

        if top_win_rate_established and top_win_rate_established not in top_win_rate_overall:
            est = top_win_rate_established
            summary_lines.append(
                f"Among established sectors with significant deal volume (≥5 closed deals), "
                f"**{est['sector']}** has the highest win rate at {est['win_rate_pct']}%, "
                f"based on {est['won']} Won deals and {est['dead']} Dead deals ({est['closed_deals']} closed deals)."
            )

    if top_pipeline_sector:
        summary_lines.append(
            f"**Largest open pipeline:** {top_pipeline_sector['sector']} with {top_pipeline_sector['open_value_fmt']} "
            f"across {top_pipeline_sector['open_count']} open deals."
        )

    if top_wo_sector:
        summary_lines.append(
            f"**Largest work order value:** {top_wo_sector['sector']} with {top_wo_sector['wo_value_fmt']} "
            f"across {top_wo_sector['wo_count']} work orders ({top_wo_sector['wo_billed_fmt']} billed)."
        )

    summary_lines.append("\n**Sector Breakdown:**")
    for r in sorted(rows, key=lambda x: (x["open_value"], x["wo_value"]), reverse=True):
        if r["win_rate_pct"] is not None:
            wr_str = f"{r['win_rate_pct']}% ({r['won']} Won / {r['dead']} Dead)"
        else:
            wr_str = "N/A (0 closed deals)"
        summary_lines.append(
            f"- **{r['sector']}**: Win rate {wr_str} | Open: {r['open_count']} deals ({r['open_value_fmt']}) | WOs: {r['wo_count']} orders ({r['wo_value_fmt']})"
        )

    data_as_of_d = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])
    data_as_of_w = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    data_as_of = max(filter(None, [data_as_of_d, data_as_of_w]), default=None)

    return {
        "tool": "sector_overview",
        "no_data_in_period": False,
        "data": {
            "rows": rows,
            "rankings": {
                "by_win_rate": by_win_rate,
                "top_win_rate_overall": top_win_rate_overall,
                "top_win_rate_established": top_win_rate_established,
                "by_open_pipeline": by_open_pipeline,
                "top_pipeline_sector": top_pipeline_sector,
                "by_open_deals": by_open_deals,
                "top_open_deals_sector": top_open_deals_sector,
                "by_wo_value": by_wo_value,
                "top_wo_sector": top_wo_sector,
            },
        },
        "display": {
            "summary": "\n".join(summary_lines),
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
        f"**Win Rate:** {win_rate}% (won {won} of {won + dead} closed deals)" if win_rate is not None else "**Win Rate:** N/A (0 closed deals)",
        "",
        "### Pipeline Status",
        pipe['display'].get('summary', ''),
        "",
        "### Work Orders & Billing",
        wo['display'].get('summary', ''),
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
