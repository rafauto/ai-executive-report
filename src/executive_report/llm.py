"""Narrative generation with an LLM, plus a guardrail against invented numbers.

Supported providers (LLM_PROVIDER):
- anthropic : Claude, via ANTHROPIC_API_KEY
- openai    : any OpenAI-compatible API (OpenAI, Groq, Gemini, Ollama...)
              via OPENAI_API_KEY and, optionally, OPENAI_BASE_URL
- offline   : rule-based text, no AI (for tests, CI and key-less demos)

The report is written for a Brazilian board, so the system prompt and the
generated text are in Brazilian Portuguese.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from .config import LLMSettings
from .formatting import brl, num, pct

SYSTEM_PROMPT = """\
Você é um analista sênior de BI de um e-commerce brasileiro e escreve para a diretoria.
Regras obrigatórias:
1. Use APENAS os números fornecidos no JSON. Não invente, não estime e não calcule novos valores.
2. Escreva em português do Brasil, com números no formato brasileiro (1.234,56 e 12,3%).
3. Seja direto: frases curtas, sem jargão técnico, foco em impacto no negócio.
4. Trate os alertas na ordem de severidade recebida; não crie alertas novos.
5. Se um dado estiver ausente (null), diga que não está disponível.
6. Responda somente em Markdown com exatamente estas seções, nesta ordem:
## Resumo executivo
(3 a 5 frases com a visão geral do mês)
## Análise dos alertas
(um parágrafo curto por alerta, com provável causa e impacto; se não houver alertas, diga isso)
## Destaques positivos
(2 a 4 tópicos)
## Recomendações
(3 a 5 ações numeradas, específicas e acionáveis, ligadas aos dados)
"""

REQUIRED_SECTIONS = [
    "## Resumo executivo",
    "## Análise dos alertas",
    "## Destaques positivos",
    "## Recomendações",
]

SEVERITY_PT = {"high": "alta", "medium": "média", "low": "baixa"}


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


def build_user_prompt(data: dict, alerts: list[dict]) -> str:
    payload = {k: v for k, v in data.items() if k != "monthly_series"}
    payload["monthly_series_last_6"] = data["monthly_series"][-6:]
    payload["alerts"] = alerts
    return (
        f"Escreva o relatório executivo de {data['reference_month']} "
        f"(comparação com {data['previous_month']}).\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
    )


def _call_anthropic(settings: LLMSettings, user_prompt: str) -> LLMResult:
    import anthropic  # lazy import: only required when this provider is used

    client = anthropic.Anthropic(api_key=settings.api_key)  # None -> ANTHROPIC_API_KEY
    response = client.messages.create(
        model=settings.resolved_model,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return LLMResult(
        text,
        "anthropic",
        settings.resolved_model,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )


def _call_openai(settings: LLMSettings, user_prompt: str) -> LLMResult:
    from openai import OpenAI

    client = OpenAI(api_key=settings.api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
    response = client.chat.completions.create(
        model=settings.resolved_model,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    usage = response.usage
    return LLMResult(
        response.choices[0].message.content or "",
        "openai",
        settings.resolved_model,
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
    )


def offline_narrative(data: dict, alerts: list[dict]) -> str:
    """Rule-based narrative used without an API key. Same format as the LLM."""
    k, change = data["kpis"], data["mom_change_pct"]
    trend = "cresceu" if (change["revenue"] or 0) >= 0 else "recuou"
    lines = [
        "## Resumo executivo",
        f"Em {data['reference_month']} a receita {trend} {pct(abs(change['revenue'] or 0))} "
        f"contra {data['previous_month']}, somando {brl(k['revenue'])} em {num(k['orders'])} "
        f"pedidos (ticket médio de {brl(k['avg_ticket'])}). A nota média de avaliação foi "
        f"{num(k['avg_review_score'], 2)} e {pct(k['late_delivery_pct'])} das entregas atrasaram. "
        f"Foram identificados {len(alerts)} alerta(s) para acompanhamento.",
        "",
        "## Análise dos alertas",
    ]
    lines += [
        f"- **{a['title']}** ({SEVERITY_PT[a['severity']]}): {a['detail']}" for a in alerts
    ] or ["Nenhum indicador ultrapassou os limites definidos neste mês."]

    top = data["top_categories"]
    growing = [c for c in top if (c["change_pct"] or 0) > 0]
    lines += ["", "## Destaques positivos"]
    if growing:
        best = max(growing, key=lambda c: c["change_pct"])
        lines.append(f"- Categoria **{best['name']}** cresceu {pct(best['change_pct'])} no mês.")
    if top:
        lines.append(f"- **{top[0]['name']}** lidera a receita com {brl(top[0]['revenue'])}.")
    if (change["avg_ticket"] or 0) > 0:
        lines.append(f"- Ticket médio subiu {pct(change['avg_ticket'])}.")
    lines += [
        "",
        "## Recomendações",
        "1. Revisar com a operação logística os estados e transportadoras com maior atraso.",
        "2. Investigar as categorias em queda (estoque, preço e campanhas).",
        "3. Acompanhar semanalmente os indicadores com alerta até voltarem ao limite.",
        "",
        "_Narrativa gerada em modo offline (sem LLM)._",
    ]
    return "\n".join(lines)


def generate_narrative(
    data: dict, alerts: list[dict], settings: LLMSettings | None = None
) -> LLMResult:
    settings = settings or LLMSettings()
    if settings.provider == "offline":
        return LLMResult(offline_narrative(data, alerts), "offline", "rules")

    user_prompt = build_user_prompt(data, alerts)
    if settings.provider == "anthropic":
        result = _call_anthropic(settings, user_prompt)
    elif settings.provider == "openai":
        result = _call_openai(settings, user_prompt)
    else:
        raise ValueError(
            f"Invalid LLM_PROVIDER: {settings.provider!r}. Use anthropic, openai or offline."
        )

    missing = [s for s in REQUIRED_SECTIONS if s not in result.text]
    if missing:
        raise ValueError(f"LLM answer is not in the expected format; missing sections: {missing}")
    return result


# ---------------------------------------------------------------------------
# Guardrail: check that every number the LLM quotes exists in the data
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"(?:R\$\s*)?-?\d{1,3}(?:\.\d{3})*(?:,\d+)?%?|(?:R\$\s*)?-?\d+(?:,\d+)?%?")


def _parse_br_number(token: str) -> float | None:
    clean = token.replace("R$", "").replace("%", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


def _collect_numbers(obj, out: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.update({round(abs(obj), 2), round(abs(obj), 1), round(abs(obj), 0)})
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_numbers(v, out)
    elif isinstance(obj, str):
        for token in re.findall(r"\d+(?:\.\d+)?", obj):  # e.g. '2018-08'
            out.add(float(token))


def unverified_numbers(text: str, data: dict, alerts: list[dict]) -> list[str]:
    """Currency and percentage values in the text that are not found in the data."""
    known: set[float] = set()
    _collect_numbers(data, known)
    _collect_numbers(alerts, known)
    suspicious = []
    for token in _NUMBER_RE.findall(text):
        if "%" not in token and "R$" not in token:
            continue  # only numbers with a unit matter to the reader
        value = _parse_br_number(token)
        if value is None:
            continue
        candidates = {round(abs(value), 2), round(abs(value), 1), round(abs(value), 0)}
        if not candidates & known:
            suspicious.append(token.strip())
    return sorted(set(suspicious))
