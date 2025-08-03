from __future__ import annotations
from decimal import Decimal
import re

from services.money import parse_money


RUBLE_RE = re.compile(r"([\d\s]+(?:[.,]\d+)?)\s*₽")


def sum_rubles_from_text(text: str) -> Decimal:
    total = Decimal("0")
    for match in RUBLE_RE.findall(text):
        try:
            total += parse_money(match)
        except Exception:
            continue
    return total
