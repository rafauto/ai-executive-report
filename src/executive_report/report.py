"""Assemble the final report in Markdown (in Brazilian Portuguese).

Tables and numbers are rendered by Python (deterministic); the LLM only writes
the narrative. This keeps a wrong AI number from ever reaching the board.
"""

from __future__ import annotations

from datetime import datetime

from .formatting import brl, num, pct
from .llm import LLMResult

# (label shown in the report, KPI key, formatter, key in mom_change_pct or None)
KPI_ROWS = [
    ("Receita", "revenue", brl, "revenue"),
    ("Pedidos", "orders", num, "orders"),
    ("Ticket médio", "avg_ticket", brl, "avg_ticket"),
    ("Clientes únicos", "unique_customers", num, "unique_customers"),
    ("Taxa de cancelamento", "cancel_rate_pct", pct, None),
    ("Prazo médio de entrega (dias)", "avg_delivery_days", lambda v: num(v, 1), None),
    ("Entregas atrasadas", "late_delivery_pct", pct, None),
    ("Nota média de avaliação", "avg_review_score", lambda v: num(v, 2), None),
    ("Avaliações negativas (1-2)", "negative_review_pct", pct, None),
    ("Frete / receita", "freight_to_revenue_pct", pct, None),
]

SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "🟡"}


def _absolute_change(key: str, current: float, previous: float) -> str:
    diff = current - previous
    sign = "+" if diff > 0 else ""
    if key.endswith("_pct"):
        return f"{sign}{num(diff, 1)} p.p."
    return f"{sign}{num(diff, 1 if key.endswith('_days') else 2)}"


def kpi_table(data: dict) -> str:
    cur, prev, change = data["kpis"], data["previous_kpis"], data["mom_change_pct"]
    lines = [
        f"| Indicador | {data['reference_month']} | {data['previous_month']} | Variação |",
        "|---|---:|---:|---:|",
    ]
    for label, key, fmt, change_key in KPI_ROWS:
        if change_key:
            delta = pct(change[change_key], signed=True)
        elif cur[key] is not None and prev[key] is not None:
            delta = _absolute_change(key, cur[key], prev[key])
        else:
            delta = "n/d"
        lines.append(f"| {label} | {fmt(cur[key])} | {fmt(prev[key])} | {delta} |")
    return "\n".join(lines)


def alerts_table(alerts: list[dict]) -> str:
    if not alerts:
        return "✅ Nenhum alerta disparado neste mês."
    lines = ["| | Alerta | Detalhe |", "|---|---|---|"]
    lines += [f"| {SEVERITY_ICON[a['severity']]} | {a['title']} | {a['detail']} |" for a in alerts]
    return "\n".join(lines)


def categories_table(data: dict, top: int = 5) -> str:
    lines = ["| Categoria | Receita | Variação | Part. no top 10 |", "|---|---:|---:|---:|"]
    for c in data["top_categories"][:top]:
        lines.append(
            f"| {c['name']} | {brl(c['revenue'])} | {pct(c['change_pct'], signed=True)} "
            f"| {pct(c['top_share_pct'])} |"
        )
    return "\n".join(lines)


def render_report(
    data: dict,
    alerts: list[dict],
    llm: LLMResult,
    timings: dict[str, float],
    unverified: list[str],
    source_label: str,
) -> str:
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    parts = [
        f"# Relatório Executivo · {data['reference_month']}",
        f"_Gerado automaticamente em {generated_at} · Fonte: {source_label} · "
        f"Comparação com {data['previous_month']}_",
        "",
        "## Indicadores principais",
        kpi_table(data),
        "",
        "## Alertas",
        alerts_table(alerts),
        "",
        llm.text.strip(),
        "",
        "## Top 5 categorias por receita",
        categories_table(data),
        "",
        "---",
    ]
    if unverified:
        parts.append(
            "> ⚠️ **Verificação automática:** os valores a seguir aparecem no texto da IA mas não "
            f"foram encontrados nos dados calculados e devem ser conferidos: {', '.join(unverified)}"
        )
        parts.append("")
    tokens = ""
    if llm.input_tokens is not None:
        tokens = f" · tokens: {llm.input_tokens} entrada / {llm.output_tokens} saída"
    parts.append(
        f"<sub>Narrativa: {llm.provider} ({llm.model}){tokens} · "
        f"Tempo total de geração: {num(sum(timings.values()), 1)} s</sub>"
    )
    return "\n".join(parts) + "\n"
