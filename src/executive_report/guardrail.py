"""Guardrail: check that every number the LLM quotes exists in the computed data."""

from __future__ import annotations

import re

_NUMBER_RE = re.compile(r"(?:R\$\s*)?-?\d{1,3}(?:\.\d{3})*(?:,\d+)?%?|(?:R\$\s*)?-?\d+(?:,\d+)?%?")


def _parse_br_number(token: str) -> float | None:
    clean = token.replace("R$", "").replace("%", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


def _rounded_variants(value: float) -> set[float]:
    return {round(abs(value), 2), round(abs(value), 1), round(abs(value), 0)}


def _collect_numbers(obj, out: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.update(_rounded_variants(obj))
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
        if value is not None and not _rounded_variants(value) & known:
            suspicious.append(token.strip())
    return sorted(set(suspicious))
