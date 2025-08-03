from io import BytesIO
from typing import List, Tuple
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter


def plot_balance_chart(points: List[Tuple[str, float]]) -> BytesIO:
    dates = [datetime.strptime(d, "%Y-%m-%d").date() for d, _ in points]
    balances = [b for _, b in points]

    plt.style.use("seaborn-v0_8")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, balances, marker="o", color="#007bff", linewidth=2)
    ax.fill_between(dates, balances, color="#007bff", alpha=0.2)
    ax.set_xlabel("Дата")
    ax.set_ylabel("Баланс, ₽")
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.autofmt_xdate()
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
