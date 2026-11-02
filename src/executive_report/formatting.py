"""Brazilian number formatting (1.234,56), used in the Portuguese report."""

from __future__ import annotations


def _br(value: float, decimals: int) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def num(value: float | None, decimals: int = 0) -> str:
    return "n/d" if value is None else _br(value, decimals)


def brl(value: float | None) -> str:
    return "n/d" if value is None else f"R$ {_br(value, 2)}"


def pct(value: float | None, decimals: int = 1, signed: bool = False) -> str:
    if value is None:
        return "n/d"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{_br(value, decimals)}%"
