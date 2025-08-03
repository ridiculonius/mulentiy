from __future__ import annotations
from io import BytesIO
from typing import Dict, List, Tuple
from datetime import datetime
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from services.money import parse_money


MOOD_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def plot_mood_pie(stats: Dict[str, int]) -> BytesIO:
    labels = [MOOD_EMOJI.get(m, m) for m in stats]
    sizes = [stats[m] for m in stats]
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(sizes, labels=labels, autopct="%1.0f%%")
    ax.set_title("Настроение")
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def plot_monthly_chart(points: List[Tuple[str, float]]) -> BytesIO:
    if not points:
        return BytesIO()
    dates = [datetime.strptime(m + "-01", "%Y-%m-%d") for m, _ in points]
    balances = [b for _, b in points]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, balances, marker="o", color="black")
    ax.set_xlabel("Месяц")
    ax.set_ylabel("Средний баланс, ₽")
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def sum_unconfirmed_rubles(text: str) -> float:
    pattern = re.compile(r"([\d\s]+(?:[.,]\d+)?)\s*₽")
    total = 0.0
    for m in pattern.findall(text):
        try:
            total += float(parse_money(m))
        except Exception:
            continue
    return total

