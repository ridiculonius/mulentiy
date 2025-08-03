from io import BytesIO
from typing import List, Tuple
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_balance_chart(points: List[Tuple[str, float]]) -> BytesIO:
    dates = [datetime.strptime(d, "%Y-%m-%d").date() for d, _ in points]
    balances = [b for _, b in points]
    fig, ax = plt.subplots()
    ax.plot(dates, balances, marker="o")
    ax.set_xlabel("Дата")
    ax.set_ylabel("Баланс, ₽")
    ax.grid(True)
    fig.autofmt_xdate()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
