from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def parse_money(value: str) -> Decimal:
    cleaned = value.strip().replace('−', '-').replace(' ', '').replace(',', '.')
    if not cleaned:
        raise ValueError('empty')
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError('invalid number') from exc


def format_money(value: Decimal) -> str:
    q = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    parts = f"{q:,.2f}".replace(',', ' ')
    return parts + ' ₽'


def calc_intermediate(site: Decimal, unconfirmed: Decimal) -> Decimal:
    return (site + unconfirmed) * Decimal('0.97')


def calc_final(intermediate: Decimal, tbank: Decimal, ozone: Decimal) -> Decimal:
    return intermediate + tbank + ozone
