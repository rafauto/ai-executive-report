"""Business rules that turn numbers into prioritized alerts.

Alerts are computed deterministically, before the LLM runs. The AI writes and
adds context, but it never decides on its own what counts as a problem.
Alert titles and details are in Brazilian Portuguese because they go straight
into the report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import AlertThresholds
from .formatting import num, pct

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Alert:
    code: str
    severity: str  # high | medium | low
    title: str
    detail: str
    value: float
    threshold: float

    def to_dict(self) -> dict:
        return asdict(self)


def _severity(value: float, limit: float, higher_is_worse: bool) -> str:
    """'high' when the deviation exceeds 50% of the threshold, else 'medium'."""
    if limit == 0:
        return "medium"
    if higher_is_worse:
        excess = (value - limit) / abs(limit)
    else:
        excess = (limit - value) / abs(limit)
    return "high" if excess >= 0.5 else "medium"


def evaluate_alerts(data: dict, t: AlertThresholds | None = None) -> list[Alert]:
    t = t or AlertThresholds()
    k = data["kpis"]
    change = data["mom_change_pct"]
    prev = data["previous_month"]
    alerts: list[Alert] = []

    revenue_change = change["revenue"]
    if revenue_change is not None and revenue_change <= t.revenue_drop_pct:
        severity = "high" if revenue_change <= 2 * t.revenue_drop_pct else "medium"
        alerts.append(
            Alert(
                "REVENUE_DROP",
                severity,
                "Queda de receita",
                f"Receita caiu {pct(abs(revenue_change))} em relação a {prev}.",
                revenue_change,
                t.revenue_drop_pct,
            )
        )

    orders_change = change["orders"]
    if orders_change is not None and orders_change <= t.orders_drop_pct:
        alerts.append(
            Alert(
                "ORDERS_DROP",
                "medium",
                "Queda no volume de pedidos",
                f"Pedidos caíram {pct(abs(orders_change))} em relação a {prev}.",
                orders_change,
                t.orders_drop_pct,
            )
        )

    if k["late_delivery_pct"] >= t.late_delivery_pct:
        alerts.append(
            Alert(
                "LATE_DELIVERIES",
                _severity(k["late_delivery_pct"], t.late_delivery_pct, True),
                "Atrasos de entrega acima do limite",
                f"{pct(k['late_delivery_pct'])} das entregas chegaram depois da data prometida.",
                k["late_delivery_pct"],
                t.late_delivery_pct,
            )
        )

    if k["cancel_rate_pct"] >= t.cancel_rate_pct:
        alerts.append(
            Alert(
                "HIGH_CANCELLATIONS",
                _severity(k["cancel_rate_pct"], t.cancel_rate_pct, True),
                "Cancelamentos acima do limite",
                f"{pct(k['cancel_rate_pct'])} dos pedidos foram cancelados "
                "ou ficaram indisponíveis.",
                k["cancel_rate_pct"],
                t.cancel_rate_pct,
            )
        )

    score = k["avg_review_score"]
    if score is not None and score < t.min_review_score:
        alerts.append(
            Alert(
                "LOW_REVIEW_SCORE",
                _severity(score, t.min_review_score, False),
                "Satisfação abaixo da meta",
                f"Nota média de {num(score, 2)} (meta mínima {num(t.min_review_score, 1)}).",
                score,
                t.min_review_score,
            )
        )

    if k["negative_review_pct"] >= t.negative_review_pct:
        alerts.append(
            Alert(
                "NEGATIVE_REVIEWS",
                "medium",
                "Muitas avaliações negativas",
                f"{pct(k['negative_review_pct'])} das avaliações tiveram nota 1 ou 2.",
                k["negative_review_pct"],
                t.negative_review_pct,
            )
        )

    for cat in data["top_categories"][:5]:
        v = cat["change_pct"]
        if v is not None and v <= t.category_drop_pct:
            alerts.append(
                Alert(
                    "CATEGORY_DROP",
                    "medium",
                    f"Queda forte em '{cat['name']}'",
                    f"Categoria top 5 com receita {pct(abs(v))} menor que no mês anterior.",
                    v,
                    t.category_drop_pct,
                )
            )

    for st in data["delivery_by_state"]:
        if st["late_pct"] >= t.state_late_pct:
            alerts.append(
                Alert(
                    "STATE_LATE_DELIVERIES",
                    _severity(st["late_pct"], t.state_late_pct, True),
                    f"Atraso concentrado em {st['state']}",
                    f"{pct(st['late_pct'])} de atraso em "
                    f"{st['delivered_orders']} entregas no estado.",
                    st["late_pct"],
                    t.state_late_pct,
                )
            )

    return sorted(alerts, key=lambda a: SEVERITY_ORDER[a.severity])
