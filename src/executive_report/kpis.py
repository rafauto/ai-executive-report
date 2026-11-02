"""Executive KPIs for one month, compared with the previous month."""

from __future__ import annotations

import math

import pandas as pd


def _pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 2) if whole else 0.0


def _change(current: float, previous: float) -> float | None:
    if previous in (0, None) or (isinstance(previous, float) and math.isnan(previous)):
        return None
    return round(100 * (current - previous) / previous, 2)


def _safe_round(value: float, ndigits: int = 2) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), ndigits)


def period_kpis(view: pd.DataFrame, month: pd.Period) -> dict:
    """Headline indicators for a single month."""
    m = view[view["month"] == month]
    valid = m[~m["is_canceled"]]
    delivered = m[m["is_delivered"]]
    reviewed = m.dropna(subset=["review_score"])

    revenue = float(valid["order_value"].sum())
    n_orders = int(len(valid))
    return {
        "month": str(month),
        "revenue": round(revenue, 2),
        "orders": n_orders,
        "avg_ticket": round(revenue / n_orders, 2) if n_orders else 0.0,
        "unique_customers": int(valid["customer_unique_id"].nunique()),
        "cancel_rate_pct": _pct(int(m["is_canceled"].sum()), len(m)),
        "avg_delivery_days": _safe_round(delivered["delivery_days"].mean(), 1),
        "late_delivery_pct": _pct(int(delivered["is_late"].sum()), len(delivered)),
        "avg_review_score": _safe_round(reviewed["review_score"].mean(), 2),
        "negative_review_pct": _pct(int((reviewed["review_score"] <= 2).sum()), len(reviewed)),
        "freight_to_revenue_pct": _pct(float(valid["freight_value"].sum()), revenue),
    }


def _breakdown(
    view: pd.DataFrame, month: pd.Period, prev: pd.Period, by: str, top: int
) -> list[dict]:
    valid = view[~view["is_canceled"] & view["month"].isin([month, prev])]
    grouped = valid.groupby([by, "month"])["order_value"].sum().unstack(fill_value=0.0)
    for col in (month, prev):
        if col not in grouped.columns:
            grouped[col] = 0.0
    grouped = grouped.sort_values(month, ascending=False).head(top)
    total = float(grouped[month].sum()) or 1.0
    return [
        {
            "name": str(name),
            "revenue": round(float(row[month]), 2),
            "previous_revenue": round(float(row[prev]), 2),
            "change_pct": _change(float(row[month]), float(row[prev])),
            "top_share_pct": _pct(float(row[month]), total),
        }
        for name, row in grouped.iterrows()
    ]


def delivery_by_state(view: pd.DataFrame, month: pd.Period, min_orders: int) -> list[dict]:
    """Late-delivery rate and lead time per state, for states with enough volume."""
    d = view[(view["month"] == month) & view["is_delivered"]]
    g = d.groupby("customer_state").agg(
        delivered_orders=("order_id", "count"),
        late=("is_late", "sum"),
        avg_delivery_days=("delivery_days", "mean"),
    )
    g = g[g["delivered_orders"] >= min_orders]
    g["late_pct"] = (100 * g["late"] / g["delivered_orders"]).round(2)
    g = g.sort_values("late_pct", ascending=False)
    return [
        {
            "state": state,
            "delivered_orders": int(row["delivered_orders"]),
            "late_pct": float(row["late_pct"]),
            "avg_delivery_days": _safe_round(row["avg_delivery_days"], 1),
        }
        for state, row in g.iterrows()
    ]


def payment_mix(view: pd.DataFrame, month: pd.Period) -> list[dict]:
    valid = view[(view["month"] == month) & ~view["is_canceled"]]
    mix = valid.groupby("payment_type")["order_value"].sum().sort_values(ascending=False)
    total = float(mix.sum()) or 1.0
    return [{"method": str(k), "share_pct": _pct(float(v), total)} for k, v in mix.items()]


def monthly_series(view: pd.DataFrame, month: pd.Period, n_months: int = 12) -> list[dict]:
    valid = view[~view["is_canceled"] & (view["month"] <= month)]
    s = valid.groupby("month").agg(revenue=("order_value", "sum"), orders=("order_id", "count"))
    s = s.sort_index().tail(n_months)
    return [
        {"month": str(idx), "revenue": round(float(r["revenue"]), 2), "orders": int(r["orders"])}
        for idx, r in s.iterrows()
    ]


def build_report_data(view: pd.DataFrame, month: pd.Period, min_state_orders: int = 50) -> dict:
    """Full set of numbers that feeds the alerts and the LLM."""
    prev = month - 1
    current = period_kpis(view, month)
    previous = period_kpis(view, prev)
    changes = {
        key: _change(current[key], previous[key])
        for key in ("revenue", "orders", "avg_ticket", "unique_customers")
    }
    return {
        "reference_month": str(month),
        "previous_month": str(prev),
        "kpis": current,
        "previous_kpis": previous,
        "mom_change_pct": changes,
        "top_categories": _breakdown(view, month, prev, "category", top=10),
        "top_states_by_revenue": _breakdown(view, month, prev, "customer_state", top=5),
        "delivery_by_state": delivery_by_state(view, month, min_state_orders),
        "payment_mix": payment_mix(view, month),
        "monthly_series": monthly_series(view, month),
    }
