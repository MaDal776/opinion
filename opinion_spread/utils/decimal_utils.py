"""Decimal utilities for consistent numeric handling."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, getcontext
from typing import Any

getcontext().prec = 28


FOUR_DP = Decimal("0.0001")
TWO_DP = Decimal("0.01")


def to_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
        return Decimal(value)
    raise TypeError(f"Unsupported value type for Decimal conversion: {type(value)!r}")


def quantize_down(value: Decimal, step: Decimal = FOUR_DP) -> Decimal:
    return value.quantize(step, rounding=ROUND_DOWN)


def format_decimal(value: Decimal, step: Decimal = FOUR_DP) -> str:
    return str(quantize_down(value, step))


def safe_div(numerator: Decimal, denominator: Decimal, default: Decimal = Decimal("0")) -> Decimal:
    if denominator == 0:
        return default
    return numerator / denominator
