from io import BytesIO
from typing import List, Tuple
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplcyberpunk  # type: ignore
from matplotlib.dates import DateFormatter


def plot_balance_chart(points: List[Tuple[str, float]]) -> BytesIO:
    dates = [datetime.strptime(d, "%Y-%m-%d").date() for d, _ in points]
    balances = [b for _, b in points]

    plt.style.use("cyberpunk")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, balances, marker="o", linewidth=2)
    mplcyberpunk.add_gradient_fill(ax, dates, balances, alpha_fill=0.3)
    mplcyberpunk.add_glow_effects()
    ax.set_xlabel("Дата")
    ax.set_ylabel("Баланс, ₽")
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
