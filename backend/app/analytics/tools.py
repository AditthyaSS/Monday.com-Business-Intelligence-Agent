"""Analytics tools: pipeline_summary, work_order_summary, sector_overview,
owner_summary, trend_analysis, data_quality_report, leadership_brief.

Every function takes validated params and returns a standardized ToolResult dict.
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

_PERIOD_SPECS = Literal["all_time", "this_quarter", "last_quarter", "this_fy", "last_fy", "previous_fy", "this_month", "last_month", "recent", "ytd"]
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
        return {"top1_share": None, "top3_share": None, "total_excl_top3": None, "total_excl_top3_fmt": None}
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
    sector: str | list[str] | None = None,
    owner: str | None = None,
    fy_start_month: int = 4,
) -> ToolResult:
    """Summarise open pipeline: count, value, coverage, by stage, sector, owner, top deals, overdue."""
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
        summary_text = f"No open deals found for {period.label}. Data available: {avail}."
        return {
            "tool": "pipeline_summary",
            "no_data_in_period": True,
            "period": {"label": period.label, "start": str(period.start), "end": str(period.end)},
            "available_range": avail,
            "data": {},
            "summary": summary_text,
            "display": {"summary": summary_text},
            "coverage": [],
            "caveats": caveats + ["No records match the selected period/filters."],
            "assumptions": assumptions,
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

    # By owner
    df_with_owner = df[df["owner"].notna() & (df["owner"] != "")].copy()
    missing_owner_open_deals = int((df["owner"].isna() | (df["owner"] == "")).sum())
    missing_owner_val = float(df[df["owner"].isna() | (df["owner"] == "")]["value_inr"].dropna().sum())

    owner_agg_records = []
    top_owner_by_value = None
    top_owner_by_count = None
    top_owner_by_overdue = None

    if len(df_with_owner) > 0:
        df_with_owner["_is_overdue"] = df_with_owner["quality_flags"].apply(lambda f: "open_close_date_past" in f)
        df_with_owner["_val_missing"] = df_with_owner["value_inr"].isna()

        owner_agg = (
            df_with_owner.groupby("owner", dropna=False)
            .agg(
                open_deals=("deal_name", "count"),
                open_value=("value_inr", "sum"),
                missing_value_count=("_val_missing", "sum"),
                overdue_deals=("_is_overdue", "sum"),
            )
            .reset_index()
        )
        owner_agg["open_value"] = owner_agg["open_value"].fillna(0.0)
        owner_agg["open_value_fmt"] = owner_agg["open_value"].apply(fmt_inr)
        owner_agg_records = owner_agg.sort_values("open_value", ascending=False).to_dict("records")
        top_owner_by_value = owner_agg_records[0] if owner_agg_records else None

        by_count_owners = owner_agg.sort_values("open_deals", ascending=False).to_dict("records")
        top_owner_by_count = by_count_owners[0] if by_count_owners else None

        by_overdue_owners = owner_agg.sort_values("overdue_deals", ascending=False).to_dict("records")
        top_owner_by_overdue = by_overdue_owners[0] if by_overdue_owners and by_overdue_owners[0]["overdue_deals"] > 0 else None

    # Top 5 deals (by value)
    top5 = (
        df[with_value]
        .nlargest(5, "value_inr")[["deal_name", "sector", "stage_name", "value_inr", "tentative_close", "owner"]]
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
                "owner": r.get("owner"),
                "value_fmt": fmt_inr(float(r["value_inr"])) if pd.notna(r.get("value_inr")) else "Missing",
                "tentative_close": str(r.get("tentative_close")) if r.get("tentative_close") else None,
            })

    # Concentration
    conc = _concentration(df.loc[with_value, "value_inr"])

    # Overall closed win rate stats across the deals board
    won_cnt = int((deals_df["status"] == "Won").sum())
    dead_cnt = int((deals_df["status"] == "Dead").sum())
    closed_cnt = won_cnt + dead_cnt
    win_rate = round(won_cnt / closed_cnt * 100, 1) if closed_cnt > 0 else None

    if stale_count:
        caveats.append(f"{stale_count} of {total_count} open deals ({stale_pct}%) have a Tentative Close Date in the past.")
    if value_count < total_count:
        caveats.append(f"Deal value present for {value_count} of {total_count} open deals; {missing_value_count} missing excluded from totals.")
    if conc.get("top3_share") and conc["top3_share"] > 60:
        caveats.append(f"Top-3 deals represent {conc['top3_share']}% of open pipeline value — high concentration.")
    if missing_owner_open_deals:
        caveats.append(f"{missing_owner_open_deals} open deal(s) have missing owner information.")

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
    if top_owner_by_value:
        summary_lines.append(
            f"**Top sales owner by pipeline:** {top_owner_by_value['owner']} "
            f"({top_owner_by_value['open_value_fmt']} across {top_owner_by_value['open_deals']} open deals)."
        )
    if stale_count:
        summary_lines.append(
            f"**Overdue close dates:** {stale_count} of {total_count} open deals ({stale_pct}%) "
            f"have tentative close dates in the past."
        )

    summary_str = "\n".join(summary_lines)

    return {
        "tool": "pipeline_summary",
        "no_data_in_period": False,
        "period": {"label": period.label, "start": str(period.start), "end": str(period.end)},
        "summary": summary_str,
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
            "by_owner": owner_agg_records,
            "top_owner_by_value": top_owner_by_value,
            "top_owner_by_count": top_owner_by_count,
            "top_owner_by_overdue": top_owner_by_overdue,
            "missing_owner_open_deals": missing_owner_open_deals,
            "missing_owner_pipeline_value": missing_owner_val,
            "top_5_deals": top5_list,
            "overall_won_deals": won_cnt,
            "overall_dead_deals": dead_cnt,
            "overall_closed_deals": closed_cnt,
            "overall_win_rate_pct": win_rate,
        },
        "display": {
            "total_value_fmt": fmt_inr(total_value),
            "summary": summary_str,
            "concentration": (
                f"Top-3 deals: {conc.get('top3_share', 'n/a')}% of total. "
                f"Excluding top 3: {conc.get('total_excl_top3_fmt', 'n/a')}."
            ),
            "stale_close": f"{stale_count}/{total_count} open deals have past tentative close date.",
        },
        "coverage": [
            {"metric": "open_deal_value", "used": value_count, "total": total_count, "note": "Deals with a monetary value"},
            {"metric": "owner_assigned", "used": total_count - missing_owner_open_deals, "total": total_count, "note": "Open deals with assigned owner"}
        ],
        "caveats": caveats,
        "assumptions": assumptions,
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
    sector: str | list[str] | None = None,
    owner: str | None = None,
    gst_basis: str = "excl",
    fy_start_month: int = 4,
) -> ToolResult:
    """Summarise work orders: value, billed, to-bill, collected, receivable, anomalies, sectors, owners."""
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
        assumptions.append(f"Owner filter: {owner}.")

    data_as_of = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    if data_as_of and (today - data_as_of).days > 45:
        caveats.append(f"Data ends around {data_as_of}; today is {today}. Results may be stale.")

    no_data = len(df) == 0
    if no_data:
        avail = _available_range(wo_df, "po_date")
        summary_text = f"No work orders found for {period.label}. Data available: {avail}."
        return {
            "tool": "work_order_summary",
            "no_data_in_period": True,
            "period": {"label": period.label},
            "available_range": avail,
            "data": {},
            "summary": summary_text,
            "display": {"summary": summary_text},
            "coverage": [],
            "caveats": caveats + ["No records match the selected period/filters."],
            "assumptions": assumptions,
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

    # Delayed / overdue work orders: end date in past and execution status != Completed
    df["_delayed"] = df.apply(
        lambda r: bool(r.get("end") and r["end"] < today and r.get("execution_status") != "Completed"),
        axis=1,
    )
    delayed_count = int(df["_delayed"].sum())
    delayed_sample = []
    if delayed_count > 0:
        for _, r in df[df["_delayed"]].head(5).iterrows():
            delayed_sample.append({
                "wo_id": r.get("wo_id"),
                "deal_name": r.get("deal_name"),
                "sector": r.get("sector"),
                "owner": r.get("owner"),
                "end_date": str(r.get("end")),
                "execution_status": r.get("execution_status"),
            })

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

    # Comprehensive Sector Aggregation
    df["_sec_order"] = order_col
    df["_sec_billed"] = billed_col
    df["_sec_collected"] = collected_col
    df["_sec_receivable"] = receivable_col
    df["_has_anomaly"] = df["quality_flags"].apply(lambda f: ("over_billed" in f) or ("negative_to_bill" in f))

    sector_agg = (
        df.groupby("sector", dropna=False)
        .agg(
            wo_count=("wo_id", "count"),
            order_value=("_sec_order", "sum"),
            billed_value=("_sec_billed", "sum"),
            collected_value=("_sec_collected", "sum"),
            receivable_value=("_sec_receivable", "sum"),
            anomalies_count=("_has_anomaly", "sum"),
        )
        .reset_index()
    )
    sector_agg["to_bill_value"] = sector_agg["order_value"] - sector_agg["billed_value"]
    sector_agg["billing_pct"] = sector_agg.apply(
        lambda r: round(r["billed_value"] / r["order_value"] * 100, 1) if r["order_value"] > 0 else None,
        axis=1,
    )
    sector_agg["collection_pct"] = sector_agg.apply(
        lambda r: round(r["collected_value"] / r["billed_value"] * 100, 1) if r["billed_value"] > 0 else None,
        axis=1,
    )
    sector_agg["order_value_fmt"] = sector_agg["order_value"].apply(fmt_inr)
    sector_agg["billed_value_fmt"] = sector_agg["billed_value"].apply(fmt_inr)
    sector_agg["collected_value_fmt"] = sector_agg["collected_value"].apply(fmt_inr)
    sector_agg["receivable_value_fmt"] = sector_agg["receivable_value"].apply(fmt_inr)
    sector_agg["to_bill_value_fmt"] = sector_agg["to_bill_value"].apply(fmt_inr)

    sector_agg_records = sector_agg.sort_values("order_value", ascending=False).to_dict("records")
    top_wo_sector = sector_agg_records[0] if sector_agg_records else None

    # Top sector by receivable
    by_receivable_sectors = sector_agg.sort_values("receivable_value", ascending=False).to_dict("records")
    top_sector_by_receivable = by_receivable_sectors[0] if by_receivable_sectors and by_receivable_sectors[0]["receivable_value"] > 0 else None

    # Top sector by to-bill gap
    by_to_bill_sectors = sector_agg.sort_values("to_bill_value", ascending=False).to_dict("records")
    top_sector_by_to_bill = by_to_bill_sectors[0] if by_to_bill_sectors and by_to_bill_sectors[0]["to_bill_value"] > 0 else None

    # Owner Aggregation for Work Orders
    owner_agg_records = []
    top_owner_by_wo_value = None
    top_owner_by_receivable = None

    df_with_owner = df[df["owner"].notna() & (df["owner"] != "")].copy()
    if len(df_with_owner) > 0:
        owner_wo_agg = (
            df_with_owner.groupby("owner", dropna=False)
            .agg(
                wo_count=("wo_id", "count"),
                order_value=("_sec_order", "sum"),
                billed_value=("_sec_billed", "sum"),
                collected_value=("_sec_collected", "sum"),
                receivable_value=("_sec_receivable", "sum"),
            )
            .reset_index()
        )
        owner_wo_agg["to_bill_value"] = owner_wo_agg["order_value"] - owner_wo_agg["billed_value"]
        owner_wo_agg["order_value_fmt"] = owner_wo_agg["order_value"].apply(fmt_inr)
        owner_wo_agg["billed_value_fmt"] = owner_wo_agg["billed_value"].apply(fmt_inr)
        owner_wo_agg["receivable_value_fmt"] = owner_wo_agg["receivable_value"].apply(fmt_inr)
        owner_wo_agg["to_bill_value_fmt"] = owner_wo_agg["to_bill_value"].apply(fmt_inr)
        owner_agg_records = owner_wo_agg.sort_values("order_value", ascending=False).to_dict("records")
        top_owner_by_wo_value = owner_agg_records[0] if owner_agg_records else None

        by_owner_rec = owner_wo_agg.sort_values("receivable_value", ascending=False).to_dict("records")
        top_owner_by_receivable = by_owner_rec[0] if by_owner_rec and by_owner_rec[0]["receivable_value"] > 0 else None

    if order_val < billed_val:
        caveats.append("Total billed exceeds total order value (anomalies present).")
    if anomalies:
        caveats.append(f"{len(anomalies)} billing anomaly(s) detected ({over_billed_count} over-billed, {negative_to_bill_count} negative to-bill).")
    if delayed_count > 0:
        caveats.append(f"{delayed_count} work order(s) have past scheduled end dates and remain incomplete.")

    summary_lines = [
        f"**Work Orders Overview ({period.label}):**",
        f"- **Order value:** {fmt_inr(order_val)} across {len(df)} work orders.",
        f"- **Billed:** {fmt_inr(billed_val)} ({billing_pct}% of order value).",
        f"- **Collected:** {fmt_inr(collected_val)} ({collection_pct}% of billed amount).",
        f"- **Receivables outstanding:** {fmt_inr(receivable_val)}.",
        f"- **Still to bill:** {fmt_inr(to_bill_val)}.",
    ]
    if top_sector_by_receivable:
        summary_lines.append(
            f"**Largest receivables sector:** {top_sector_by_receivable['sector']} "
            f"({top_sector_by_receivable['receivable_value_fmt']}, {top_sector_by_receivable['wo_count']} work orders)."
        )
    if top_sector_by_to_bill:
        summary_lines.append(
            f"**Biggest billing gap (still to bill):** {top_sector_by_to_bill['sector']} "
            f"({top_sector_by_to_bill['to_bill_value_fmt']} unbilled)."
        )
    if anomalies:
        summary_lines.append(
            f"**Billing anomalies:** {len(anomalies)} detected ({over_billed_count} over-billed, {negative_to_bill_count} negative to-bill)."
        )
    if delayed_count > 0:
        summary_lines.append(
            f"**Delayed / overdue work orders:** {delayed_count} orders past scheduled end date."
        )

    summary_str = "\n".join(summary_lines)

    return {
        "tool": "work_order_summary",
        "no_data_in_period": False,
        "period": {"label": period.label},
        "summary": summary_str,
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
            "delayed_orders_count": delayed_count,
            "delayed_orders_sample": delayed_sample,
            "anomalies": anomalies[:10],
            "anomaly_details": anomaly_details[:10],
            "over_billed_count": over_billed_count,
            "negative_to_bill_count": negative_to_bill_count,
            "by_sector": sector_agg_records,
            "top_sector_by_order_value": top_wo_sector,
            "top_sector_by_receivable": top_sector_by_receivable,
            "top_sector_by_to_bill": top_sector_by_to_bill,
            "by_owner": owner_agg_records,
            "top_owner_by_wo_value": top_owner_by_wo_value,
            "top_owner_by_receivable": top_owner_by_receivable,
        },
        "display": {
            "summary": summary_str,
        },
        "coverage": [
            {"metric": "order_value", "used": int(order_col.notna().sum()), "total": len(df), "note": "Rows with order amount"},
            {"metric": "billed", "used": int(billed_col.notna().sum()), "total": len(df), "note": "Rows with billed amount"},
            {"metric": "collected", "used": int(collected_col.notna().sum()), "total": len(df), "note": "Rows with collection data"}
        ],
        "caveats": caveats,
        "assumptions": assumptions,
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
    sectors: list[str] | str | None = None,
) -> ToolResult:
    """Cross-board sector view: open pipeline, win rate, work order delivery, billing, receivables."""
    caveats = [
        "Cross-board comparison is aggregated at sector level because the source data does not provide a reliable record-level relationship.",
        f"GST basis: {gst_basis}.",
    ]
    assumptions = [
        "All time; no period filter.",
        "Win rate = Won / (Won + Dead) strictly by count.",
        "Established sector benchmark requires >=5 closed deals.",
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
            col_series = wo["collected_incl"] if "collected_incl" in wo.columns else pd.Series([None] * len(wo))
            wo["_collected"] = col_series.apply(
                lambda x: x / GST_RATE if x is not None and not math.isnan(float(x if x else 0)) else None
            )
        else:
            wo["_order"] = wo["amount_incl"] if "amount_incl" in wo.columns else 0.0
            wo["_billed"] = wo["billed_incl"] if "billed_incl" in wo.columns else 0.0
            wo["_receivable"] = wo["receivable"] if "receivable" in wo.columns else pd.Series([None] * len(wo))
            wo["_collected"] = wo["collected_incl"] if "collected_incl" in wo.columns else pd.Series([None] * len(wo))

        wo["_has_anomaly"] = wo["quality_flags"].apply(lambda f: ("over_billed" in f) or ("negative_to_bill" in f))
        wo_id_col = "wo_id" if "wo_id" in wo.columns else "sector"
        wo_by_sector = (
            wo.groupby("sector")
            .agg(
                wo_count=(wo_id_col, "count"),
                wo_value=("_order", "sum"),
                wo_billed=("_billed", "sum"),
                wo_collected=("_collected", "sum"),
                wo_receivable=("_receivable", "sum"),
                wo_anomalies=("_has_anomaly", "sum"),
            )
            .reset_index()
        )
        wo_by_sector["wo_to_bill"] = wo_by_sector["wo_value"] - wo_by_sector["wo_billed"]
    else:
        wo_by_sector = pd.DataFrame(columns=["sector", "wo_count", "wo_value", "wo_billed", "wo_collected", "wo_receivable", "wo_to_bill", "wo_anomalies"])

    merged = deal_sector.merge(wo_by_sector, on="sector", how="outer")
    num_cols = ["open_count", "open_value", "won", "dead", "wo_count", "wo_value", "wo_billed", "wo_collected", "wo_receivable", "wo_to_bill", "wo_anomalies"]
    for col in num_cols:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    merged = merged[merged["sector"] != ""]
    merged = merged[merged["sector"].notna()]

    # Filter sectors if specified
    if sectors:
        sec_filter = [s.strip().casefold() for s in (sectors if isinstance(sectors, list) else [sectors])]
        merged = merged[merged["sector"].str.casefold().isin(sec_filter)]
        assumptions.append(f"Filtered for sector comparison: {', '.join(merged['sector'].tolist())}.")

    # Win rate = Won / (Won + Dead) strictly. None when Won + Dead == 0.
    merged["win_rate"] = merged.apply(
        lambda r: round(r["won"] / (r["won"] + r["dead"]) * 100, 1)
        if (r["won"] + r["dead"]) > 0 else None,
        axis=1,
    )

    rows = []
    cross_board_investigate = []
    for _, r in merged.iterrows():
        won_cnt = int(r.get("won", 0))
        dead_cnt = int(r.get("dead", 0))
        closed_cnt = won_cnt + dead_cnt
        wr = r.get("win_rate")
        wr_pct = float(wr) if wr is not None and not pd.isna(wr) else None
        open_val = float(r.get("open_value", 0))
        wo_val = float(r.get("wo_value", 0))
        wo_billed = float(r.get("wo_billed", 0))
        wo_rec = float(r.get("wo_receivable", 0))
        wo_to_bill = float(r.get("wo_to_bill", 0))
        anom_cnt = int(r.get("wo_anomalies", 0))

        flags = []
        if open_val > 50_000_000 and wo_rec > 10_000_000:
            flags.append("High pipeline + high receivables")
        if open_val > 50_000_000 and wo_to_bill > 20_000_000:
            flags.append("High pipeline + large unbilled execution gap")
        if anom_cnt > 0:
            flags.append(f"{anom_cnt} billing anomaly(s)")

        if flags:
            cross_board_investigate.append({
                "sector": r["sector"],
                "open_value_fmt": fmt_inr(open_val),
                "wo_receivable_fmt": fmt_inr(wo_rec),
                "wo_to_bill_fmt": fmt_inr(wo_to_bill),
                "issues": flags,
            })

        rows.append({
            "sector": r["sector"],
            "open_count": int(r.get("open_count", 0)),
            "open_value": open_val,
            "open_value_fmt": fmt_inr(open_val),
            "won": won_cnt,
            "dead": dead_cnt,
            "closed_deals": closed_cnt,
            "win_rate_pct": wr_pct,
            "wo_count": int(r.get("wo_count", 0)),
            "wo_value": wo_val,
            "wo_value_fmt": fmt_inr(wo_val),
            "wo_billed": wo_billed,
            "wo_billed_fmt": fmt_inr(wo_billed),
            "wo_collected": float(r.get("wo_collected", 0)),
            "wo_collected_fmt": fmt_inr(float(r.get("wo_collected", 0))),
            "wo_receivable": wo_rec,
            "wo_receivable_fmt": fmt_inr(wo_rec),
            "wo_to_bill": wo_to_bill,
            "wo_to_bill_fmt": fmt_inr(wo_to_bill),
            "cross_board_issues": flags,
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

    # 5. By receivable value
    by_receivable = sorted(rows, key=lambda x: x["wo_receivable"], reverse=True)
    top_receivable_sector = by_receivable[0] if by_receivable and by_receivable[0]["wo_receivable"] > 0 else None

    # 6. By still to bill
    by_to_bill = sorted(rows, key=lambda x: x["wo_to_bill"], reverse=True)
    top_to_bill_sector = by_to_bill[0] if by_to_bill and by_to_bill[0]["wo_to_bill"] > 0 else None

    # Dynamic summary
    summary_lines = [
        "**Cross-Board Sector Performance & Comparison:**",
        "_Note: Comparison aggregated at sector level; no record-level deal-to-work-order key exists._",
    ]

    if top_win_rate_overall:
        if len(top_win_rate_overall) == 1:
            top = top_win_rate_overall[0]
            summary_lines.append(
                f"- **Highest win rate:** {top['sector']} at {top['win_rate_pct']}% "
                f"({top['won']} Won, {top['dead']} Dead across {top['closed_deals']} closed deals)."
            )
        else:
            tied_details = ", ".join(
                f"**{s['sector']}** ({s['win_rate_pct']}%, {s['won']} Won / {s['dead']} Dead)"
                for s in top_win_rate_overall
            )
            summary_lines.append(f"- **Highest win rate (tied):** {tied_details}.")

        if top_win_rate_established and top_win_rate_established not in top_win_rate_overall:
            est = top_win_rate_established
            summary_lines.append(
                f"- **Highest win rate (established sectors with ≥5 closed deals):** "
                f"**{est['sector']}** at {est['win_rate_pct']}% "
                f"({est['won']} Won, {est['dead']} Dead across {est['closed_deals']} closed deals)."
            )

    if top_pipeline_sector:
        summary_lines.append(
            f"- **Largest open pipeline:** {top_pipeline_sector['sector']} with {top_pipeline_sector['open_value_fmt']} "
            f"across {top_pipeline_sector['open_count']} open deals."
        )

    if top_wo_sector:
        summary_lines.append(
            f"- **Largest work order execution:** {top_wo_sector['sector']} with {top_wo_sector['wo_value_fmt']} "
            f"across {top_wo_sector['wo_count']} work orders ({top_wo_sector['wo_billed_fmt']} billed)."
        )

    if top_receivable_sector:
        summary_lines.append(
            f"- **Largest receivables:** {top_receivable_sector['sector']} with {top_receivable_sector['wo_receivable_fmt']} outstanding."
        )

    if cross_board_investigate:
        investigate_notes = "; ".join(
            f"**{c['sector']}** ({', '.join(c['issues'])})"
            for c in cross_board_investigate
        )
        summary_lines.append(f"- **Cross-board operational risk sectors:** {investigate_notes}.")

    summary_lines.append("\n**Sector Breakdown:**")
    for r in sorted(rows, key=lambda x: (x["open_value"], x["wo_value"]), reverse=True):
        if r["win_rate_pct"] is not None:
            wr_str = f"{r['win_rate_pct']}% ({r['won']} Won / {r['dead']} Dead)"
        else:
            wr_str = "N/A (0 closed deals)"
        summary_lines.append(
            f"- **{r['sector']}**: Win rate {wr_str} | Open Pipeline: {r['open_count']} deals ({r['open_value_fmt']}) | WOs: {r['wo_count']} orders ({r['wo_value_fmt']}, Rec: {r['wo_receivable_fmt']})"
        )

    summary_str = "\n".join(summary_lines)

    data_as_of_d = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])
    data_as_of_w = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    data_as_of = max(filter(None, [data_as_of_d, data_as_of_w]), default=None)

    return {
        "tool": "sector_overview",
        "no_data_in_period": False,
        "summary": summary_str,
        "data": {
            "rows": rows,
            "cross_board_disclaimer": "Cross-board comparison is aggregated at sector level because the source data does not provide a reliable record-level relationship.",
            "cross_board_investigate_sectors": cross_board_investigate,
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
                "by_receivable": by_receivable,
                "top_receivable_sector": top_receivable_sector,
                "by_to_bill": by_to_bill,
                "top_to_bill_sector": top_to_bill_sector,
            },
        },
        "display": {
            "summary": summary_str,
        },
        "coverage": [],
        "caveats": caveats,
        "assumptions": assumptions,
        "assumptions_used": assumptions,
        "data_as_of": str(data_as_of) if data_as_of else None,
    }


# ---------------------------------------------------------------------------
# owner_summary
# ---------------------------------------------------------------------------

def owner_summary(
    deals_df: pd.DataFrame,
    wo_df: pd.DataFrame,
    today: date,
    owner: str | None = None,
    period_spec: str = "all_time",
    gst_basis: str = "excl",
    fy_start_month: int = 4,
) -> ToolResult:
    """Owner-level analytics across Deals and Work Orders: open pipeline, rankings, overdue, win rates."""
    period = resolve_period(period_spec, today, fy_start_month)
    caveats = []
    assumptions = [
        f"Period: {period.label}.",
        "Owner rankings based on records with non-empty owner codes.",
        "Overdue open deals based on Tentative Close Date < today.",
        f"GST basis: {gst_basis} for work orders.",
    ]

    # Deals side
    d = deals_df.copy()
    if period.start is not None:
        d = _filter_period(d, "tentative_close", period)

    open_mask = d["status"] == "Open"
    open_deals = d[open_mask].copy()

    # Missing owner counts in deals
    missing_owner_deals = int((d["owner"].isna() | (d["owner"] == "")).sum())
    missing_owner_open_deals = int((open_deals["owner"].isna() | (open_deals["owner"] == "")).sum())
    missing_owner_pipeline_val = float(open_deals[open_deals["owner"].isna() | (open_deals["owner"] == "")]["value_inr"].dropna().sum())

    if missing_owner_deals > 0:
        caveats.append(f"{missing_owner_deals} deals ({missing_owner_open_deals} open deals totaling {fmt_inr(missing_owner_pipeline_val)}) have no owner assigned and are excluded from owner rankings.")

    # Clean non-empty owner deals
    d_clean = d[d["owner"].notna() & (d["owner"] != "")].copy()

    # Calculate owner deal metrics
    d_clean["_is_open"] = d_clean["status"] == "Open"
    d_clean["_is_won"] = d_clean["status"] == "Won"
    d_clean["_is_dead"] = d_clean["status"] == "Dead"
    d_clean["_is_overdue"] = d_clean["quality_flags"].apply(lambda f: "open_close_date_past" in f)
    d_clean["_val_missing"] = d_clean["_is_open"] & d_clean["value_inr"].isna()
    d_clean["_open_val"] = d_clean.apply(lambda r: r["value_inr"] if r["_is_open"] and pd.notna(r["value_inr"]) else 0.0, axis=1)

    deal_owners = (
        d_clean.groupby("owner")
        .agg(
            total_deals=("deal_name", "count"),
            open_deals=("_is_open", "sum"),
            open_pipeline_value=("_open_val", "sum"),
            missing_value_count=("_val_missing", "sum"),
            overdue_open_deals=("_is_overdue", "sum"),
            won_deals=("_is_won", "sum"),
            dead_deals=("_is_dead", "sum"),
        )
        .reset_index()
    )
    deal_owners["closed_deals"] = deal_owners["won_deals"] + deal_owners["dead_deals"]
    deal_owners["win_rate_pct"] = deal_owners.apply(
        lambda r: round(r["won_deals"] / r["closed_deals"] * 100, 1) if r["closed_deals"] > 0 else None,
        axis=1,
    )
    deal_owners["open_pipeline_value_fmt"] = deal_owners["open_pipeline_value"].apply(fmt_inr)

    # Work orders side
    wo = wo_df.copy()
    if period.start is not None:
        wo = _filter_period(wo, "po_date", period)

    if gst_basis == "excl":
        wo["_order"] = wo["amount_excl"] if "amount_excl" in wo.columns else 0.0
        wo["_billed"] = wo["billed_excl"] if "billed_excl" in wo.columns else 0.0
        rec_series = wo["receivable"] if "receivable" in wo.columns else pd.Series([None] * len(wo))
        wo["_receivable"] = rec_series.apply(
            lambda x: x / GST_RATE if x is not None and not math.isnan(float(x if x else 0)) else 0.0
        )
    else:
        wo["_order"] = wo["amount_incl"] if "amount_incl" in wo.columns else 0.0
        wo["_billed"] = wo["billed_incl"] if "billed_incl" in wo.columns else 0.0
        wo["_receivable"] = wo["receivable"].fillna(0.0) if "receivable" in wo.columns else 0.0

    wo_clean = wo[wo["owner"].notna() & (wo["owner"] != "")].copy()
    if len(wo_clean) > 0:
        wo_owners = (
            wo_clean.groupby("owner")
            .agg(
                wo_count=("wo_id", "count"),
                wo_order_value=("_order", "sum"),
                wo_billed=("_billed", "sum"),
                wo_receivable=("_receivable", "sum"),
            )
            .reset_index()
        )
        wo_owners["wo_order_value_fmt"] = wo_owners["wo_order_value"].apply(fmt_inr)
        wo_owners["wo_billed_fmt"] = wo_owners["wo_billed"].apply(fmt_inr)
        wo_owners["wo_receivable_fmt"] = wo_owners["wo_receivable"].apply(fmt_inr)
    else:
        wo_owners = pd.DataFrame(columns=["owner", "wo_count", "wo_order_value", "wo_order_value_fmt", "wo_billed", "wo_billed_fmt", "wo_receivable", "wo_receivable_fmt"])

    # Merge deal and work order owner stats
    merged = deal_owners.merge(wo_owners, on="owner", how="outer")
    for col in ["total_deals", "open_deals", "open_pipeline_value", "missing_value_count", "overdue_open_deals", "won_deals", "dead_deals", "closed_deals", "wo_count", "wo_order_value", "wo_billed", "wo_receivable"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    merged["open_pipeline_value_fmt"] = merged["open_pipeline_value"].apply(fmt_inr)
    merged["wo_order_value_fmt"] = merged["wo_order_value"].apply(fmt_inr)

    # Optional filter for single owner
    if owner:
        merged = merged[merged["owner"].str.casefold() == owner.strip().casefold()]
        assumptions.append(f"Filtered for owner: {owner}.")

    rows = merged.to_dict("records")

    # Rankings
    by_pipeline = sorted([r for r in rows if r["open_deals"] > 0], key=lambda x: x["open_pipeline_value"], reverse=True)
    top_by_pipeline = by_pipeline[0] if by_pipeline else None

    by_open_deals = sorted([r for r in rows if r["open_deals"] > 0], key=lambda x: x["open_deals"], reverse=True)
    top_by_open_deals = by_open_deals[0] if by_open_deals else None

    by_overdue = sorted([r for r in rows if r["overdue_open_deals"] > 0], key=lambda x: x["overdue_open_deals"], reverse=True)
    top_by_overdue = by_overdue[0] if by_overdue else None

    by_win_rate = sorted([r for r in rows if r.get("win_rate_pct") is not None and r["closed_deals"] >= 3], key=lambda x: (x["win_rate_pct"], x["won_deals"]), reverse=True)
    top_by_win_rate = by_win_rate[0] if by_win_rate else None

    # Summary
    summary_lines = [
        f"**Sales Owner Performance & Pipeline Book ({period.label}):**",
    ]
    if top_by_pipeline:
        summary_lines.append(
            f"- **Largest open pipeline:** **{top_by_pipeline['owner']}** with {top_by_pipeline['open_pipeline_value_fmt']} "
            f"across {int(top_by_pipeline['open_deals'])} open deals."
        )
    if top_by_open_deals:
        summary_lines.append(
            f"- **Most open deals:** **{top_by_open_deals['owner']}** with {int(top_by_open_deals['open_deals'])} open opportunities "
            f"({top_by_open_deals['open_pipeline_value_fmt']})."
        )
    if top_by_overdue:
        summary_lines.append(
            f"- **Most overdue opportunities:** **{top_by_overdue['owner']}** with {int(top_by_overdue['overdue_open_deals'])} "
            f"deals having past tentative close dates."
        )
    if top_by_win_rate:
        summary_lines.append(
            f"- **Highest win rate (min 3 closed deals):** **{top_by_win_rate['owner']}** at {top_by_win_rate['win_rate_pct']}% "
            f"({int(top_by_win_rate['won_deals'])} Won, {int(top_by_win_rate['dead_deals'])} Dead)."
        )

    summary_lines.append("\n**Top 5 Owners by Open Pipeline Value:**")
    for r in by_pipeline[:5]:
        summary_lines.append(
            f"- **{r['owner']}**: {r['open_pipeline_value_fmt']} ({int(r['open_deals'])} open deals, {int(r['overdue_open_deals'])} overdue, {int(r.get('wo_count', 0))} work orders)"
        )

    summary_str = "\n".join(summary_lines)

    data_as_of_d = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])
    data_as_of_w = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    data_as_of = max(filter(None, [data_as_of_d, data_as_of_w]), default=None)

    return {
        "tool": "owner_summary",
        "no_data_in_period": len(rows) == 0,
        "summary": summary_str,
        "data": {
            "owners": rows,
            "top_by_pipeline": top_by_pipeline,
            "top_5_by_pipeline": by_pipeline[:5],
            "top_by_open_deals": top_by_open_deals,
            "top_by_overdue": top_by_overdue,
            "top_by_win_rate": top_by_win_rate,
            "missing_owner_deals": missing_owner_deals,
            "missing_owner_open_deals": missing_owner_open_deals,
            "missing_owner_pipeline_value": missing_owner_pipeline_val,
        },
        "display": {
            "summary": summary_str,
        },
        "coverage": [
            {"metric": "open_deals_with_owner", "used": len(open_deals) - missing_owner_open_deals, "total": len(open_deals), "note": "Open deals with assigned owner code"}
        ],
        "caveats": caveats,
        "assumptions": assumptions,
        "assumptions_used": assumptions,
        "data_as_of": str(data_as_of) if data_as_of else None,
    }


# ---------------------------------------------------------------------------
# trend_analysis
# ---------------------------------------------------------------------------

def trend_analysis(
    deals_df: pd.DataFrame,
    wo_df: pd.DataFrame,
    today: date,
    metric: str = "all",
    period_spec: str = "this_quarter",
    compare_to: str = "last_quarter",
    fy_start_month: int = 4,
) -> ToolResult:
    """Evaluate period-over-period trends and changes, reporting data limitations honestly."""
    p_curr = resolve_period(period_spec, today, fy_start_month)
    p_prev = resolve_period(compare_to, today, fy_start_month)

    data_as_of_d = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])
    data_as_of_w = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    data_as_of = max(filter(None, [data_as_of_d, data_as_of_w]), default=None)

    # Check if data exists for the requested periods
    deals_created_curr = _filter_period(deals_df, "created", p_curr)
    deals_created_prev = _filter_period(deals_df, "created", p_prev)
    wo_curr = _filter_period(wo_df, "po_date", p_curr)
    wo_prev = _filter_period(wo_df, "po_date", p_prev)

    has_curr_data = len(deals_created_curr) > 0 or len(wo_curr) > 0
    has_prev_data = len(deals_created_prev) > 0 or len(wo_prev) > 0

    # If the requested period is recent (e.g. today is Sep 2026 and period is Q2 FY26-27 or "recent"),
    # but board data ends around Jan/Apr 2026:
    if not has_curr_data or not has_prev_data:
        # Get current-state snapshot
        open_deals = deals_df[deals_df["status"] == "Open"]
        total_open_val = float(open_deals["value_inr"].dropna().sum())
        wo_val = float(wo_df["amount_excl"].dropna().sum())
        wo_billed = float(wo_df["billed_excl"].dropna().sum())
        wo_rec = float(wo_df["receivable"].dropna().sum()) / GST_RATE

        explanation = (
            f"I can summarize the current state, but I can't reliably determine what changed recently "
            f"because the connected data does not provide a comparable prior-period dataset. "
            f"The connected board records span up to {data_as_of or 'January 2026'}, while today is {today} "
            f"(no records found for {p_curr.label} or {p_prev.label})."
        )
        summary_lines = [
            f"**Trend / Recent Change Assessment:**",
            explanation,
            "",
            "**Current-State Snapshot (A reliable recent-change comparison is unavailable):**",
            f"- **Open Pipeline:** {len(open_deals)} deals totaling {fmt_inr(total_open_val)}.",
            f"- **Work Orders Execution:** {len(wo_df)} orders totaling {fmt_inr(wo_val)} ({fmt_inr(wo_billed)} billed).",
            f"- **Receivables Outstanding:** {fmt_inr(wo_rec)} (excl GST).",
        ]
        summary_str = "\n".join(summary_lines)

        return {
            "tool": "trend_analysis",
            "has_comparable_history": False,
            "period_compared": {"current": p_curr.label, "previous": p_prev.label},
            "summary": summary_str,
            "data": {
                "has_comparable_history": False,
                "reason": "Missing recent historical snapshots or out-of-range period",
                "data_as_of": str(data_as_of),
                "current_snapshot": {
                    "open_deals_count": len(open_deals),
                    "open_pipeline_value": total_open_val,
                    "open_pipeline_value_fmt": fmt_inr(total_open_val),
                    "work_orders_count": len(wo_df),
                    "work_orders_value": wo_val,
                    "work_orders_value_fmt": fmt_inr(wo_val),
                    "billed_value": wo_billed,
                    "billed_value_fmt": fmt_inr(wo_billed),
                    "receivable_value": wo_rec,
                    "receivable_value_fmt": fmt_inr(wo_rec),
                },
            },
            "display": {
                "summary": summary_str,
            },
            "coverage": [],
            "caveats": [
                "Deals board is a static point-in-time snapshot, not an event-sourced audit log of historical stage changes.",
                f"Data ends around {data_as_of}; requested comparison {p_curr.label} vs {p_prev.label} has insufficient data.",
            ],
            "assumptions": [
                "Current-state snapshot presented in place of unsupportable delta.",
            ],
            "assumptions_used": [
                "Current-state snapshot presented in place of unsupportable delta.",
            ],
            "data_as_of": str(data_as_of) if data_as_of else None,
        }

    # If data does exist in both periods (e.g. historical fiscal years or past quarters)
    d_curr_cnt = len(deals_created_curr)
    d_prev_cnt = len(deals_created_prev)
    d_curr_val = float(deals_created_curr["value_inr"].dropna().sum())
    d_prev_val = float(deals_created_prev["value_inr"].dropna().sum())

    wo_curr_cnt = len(wo_curr)
    wo_prev_cnt = len(wo_prev)
    wo_curr_val = float(wo_curr["amount_excl"].dropna().sum())
    wo_prev_val = float(wo_prev["amount_excl"].dropna().sum())

    delta_deals_cnt = d_curr_cnt - d_prev_cnt
    pct_change_deals_cnt = round(delta_deals_cnt / d_prev_cnt * 100, 1) if d_prev_cnt > 0 else None

    delta_deals_val = d_curr_val - d_prev_val
    pct_change_deals_val = round(delta_deals_val / d_prev_val * 100, 1) if d_prev_val > 0 else None

    summary_lines = [
        f"**Comparison between {p_curr.label} and {p_prev.label}:**",
        f"- **Deals Created:** {d_curr_cnt} (vs {d_prev_cnt} in prior period, change: {delta_deals_cnt:+d} or {pct_change_deals_cnt}%).",
        f"- **Deals Value Created:** {fmt_inr(d_curr_val)} (vs {fmt_inr(d_prev_val)} in prior period, change: {fmt_inr(delta_deals_val)}).",
        f"- **Work Orders POs:** {wo_curr_cnt} orders ({fmt_inr(wo_curr_val)}) vs {wo_prev_cnt} orders ({fmt_inr(wo_prev_val)}).",
    ]
    summary_str = "\n".join(summary_lines)

    return {
        "tool": "trend_analysis",
        "has_comparable_history": True,
        "period_compared": {"current": p_curr.label, "previous": p_prev.label},
        "summary": summary_str,
        "data": {
            "has_comparable_history": True,
            "deals_created": {
                "current_count": d_curr_cnt,
                "previous_count": d_prev_cnt,
                "delta_count": delta_deals_cnt,
                "pct_change_count": pct_change_deals_cnt,
                "current_value": d_curr_val,
                "previous_value": d_prev_val,
                "delta_value": delta_deals_val,
                "pct_change_value": pct_change_deals_val,
            },
            "work_orders": {
                "current_count": wo_curr_cnt,
                "previous_count": wo_prev_cnt,
                "current_value": wo_curr_val,
                "previous_value": wo_prev_val,
            },
        },
        "display": {
            "summary": summary_str,
        },
        "coverage": [],
        "caveats": [
            "Comparison uses deal creation date and PO date, not point-in-time open pipeline snapshots.",
        ],
        "assumptions": [
            f"Current: {p_curr.label}; Previous: {p_prev.label}.",
        ],
        "assumptions_used": [
            f"Current: {p_curr.label}; Previous: {p_prev.label}.",
        ],
        "data_as_of": str(data_as_of) if data_as_of else None,
    }


# ---------------------------------------------------------------------------
# data_quality_report
# ---------------------------------------------------------------------------

def data_quality_report(
    deals_report_lines: list[str],
    wo_report_lines: list[str],
) -> ToolResult:
    """Return data quality summary, exclusions, and anomalies from both boards."""
    all_lines = [
        "## Data Quality & Reliability Report",
        "",
        "### Deals Board Quality",
    ] + deals_report_lines + [
        "",
        "### Work Orders Board Quality",
    ] + wo_report_lines
    summary_text = "\n".join(all_lines)

    return {
        "tool": "data_quality_report",
        "no_data_in_period": False,
        "summary": summary_text,
        "data": {
            "deals_lines": deals_report_lines,
            "wo_lines": wo_report_lines,
            "trust_assessment": "The data is usable for aggregate counts and status distributions, but financial metrics have known coverage limitations and anomalies that must be disclosed.",
        },
        "display": {
            "summary": summary_text,
        },
        "coverage": [],
        "caveats": [
            "Deal value is missing for a significant portion of deals and must be excluded from monetary sums.",
            "Over-billing and negative to-bill anomalies exist in work orders and must be factored into execution analysis.",
        ],
        "assumptions": [
            "Excluded junk and duplicate rows are documented in quality lines.",
        ],
        "assumptions_used": [
            "Excluded junk and duplicate rows are documented in quality lines.",
        ],
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
    """Compose an executive leadership update combining pipeline, operations, win rate, risks, and caveats."""
    pipe = pipeline_summary(deals_df, today, "all_time", fy_start_month=fy_start_month)
    wo = work_order_summary(wo_df, today, "all_time", gst_basis=gst_basis, fy_start_month=fy_start_month)
    sec = sector_overview(deals_df, wo_df, today, gst_basis=gst_basis)
    own = owner_summary(deals_df, wo_df, today, gst_basis=gst_basis, fy_start_month=fy_start_month)

    # Win rate
    won = len(deals_df[deals_df["status"] == "Won"])
    dead = len(deals_df[deals_df["status"] == "Dead"])
    closed = won + dead
    win_rate = round(won / closed * 100, 1) if closed > 0 else None

    pipe_data = pipe.get("data", {})
    wo_data = wo.get("data", {})
    own_data = own.get("data", {})

    risks = []
    if pipe_data.get("concentration", {}).get("top3_share", 0) > 60:
        risks.append(f"Pipeline concentration: top-3 deals = {pipe_data['concentration']['top3_share']}% of open value.")
    stale = pipe_data.get("stale_close_count", 0)
    total_open = pipe_data.get("total_count", 0)
    if stale and total_open:
        risks.append(f"{stale}/{total_open} open deals have a stale Tentative Close Date in the past.")
    if wo_data.get("receivable", 0) and wo_data["receivable"] > 0:
        risks.append(f"Outstanding receivables: {fmt_inr(wo_data['receivable'])} (needs collection follow-up).")
    if wo_data.get("over_billed_count", 0) > 0:
        risks.append(f"Billing anomalies: {wo_data['over_billed_count']} work order(s) billed for more than the PO amount.")
    if not risks:
        risks.append("No major data-identified risks (verify manually).")

    opportunities = [
        f"Open pipeline: {fmt_inr(pipe_data.get('total_value', 0))} across {pipe_data.get('total_count', 0)} deals.",
        f"Execution backlog (still to bill): {fmt_inr(wo_data.get('to_bill', 0))} across {wo_data.get('count', 0)} work orders.",
    ]
    if win_rate is not None:
        opportunities.append(f"Historical win rate: {win_rate}% ({won} Won / {dead} Dead out of {closed} closed deals).")

    top_owner = own_data.get("top_by_pipeline")
    if top_owner:
        opportunities.append(f"Lead sales owner: {top_owner['owner']} ({top_owner['open_pipeline_value_fmt']} pipeline).")

    caveats = (pipe.get("caveats", []) + wo.get("caveats", []) +
               (deals_report_lines or [])[:2] + (wo_report_lines or [])[:2])

    display_lines = [
        "## Executive Leadership Brief",
        f"**Win Rate:** {win_rate}% ({won} won of {closed} closed deals)" if win_rate is not None else "**Win Rate:** N/A (0 closed deals)",
        "",
        "### Pipeline Status",
        pipe.get("summary", ""),
        "",
        "### Work Orders & Billing Execution",
        wo.get("summary", ""),
        "",
        "### Top Business Risks",
    ] + [f"- {r}" for r in risks[:4]] + [
        "",
        "### Key Opportunities",
    ] + [f"- {o}" for o in opportunities[:4]] + [
        "",
        "### Data Quality & Caveats",
    ] + [f"- {c}" for c in caveats[:4]]

    summary_str = "\n".join(display_lines)

    data_as_of_d = _data_as_of(deals_df, ["tentative_close", "actual_close", "created"])
    data_as_of_w = _data_as_of(wo_df, ["po_date", "last_invoice_date"])
    data_as_of = max(filter(None, [data_as_of_d, data_as_of_w]), default=None)

    return {
        "tool": "leadership_brief",
        "no_data_in_period": False,
        "summary": summary_str,
        "data": {
            "pipeline": pipe_data,
            "work_orders": wo_data,
            "sectors": sec.get("data", {}),
            "owners": own_data,
            "win_rate": win_rate,
            "won": won,
            "dead": dead,
            "closed": closed,
            "risks": risks,
            "opportunities": opportunities,
        },
        "display": {
            "summary": summary_str,
        },
        "coverage": pipe.get("coverage", []) + wo.get("coverage", []),
        "caveats": caveats[:6],
        "assumptions": pipe.get("assumptions", []) + wo.get("assumptions", []),
        "assumptions_used": pipe.get("assumptions_used", []) + wo.get("assumptions_used", []),
        "data_as_of": str(data_as_of) if data_as_of else None,
    }
