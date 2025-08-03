from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_balance_chart(points: List[Tuple[str, float]]) -> BytesIO:
    """Build a balance chart for given points.

    Each point is a tuple of ISO date string and balance value.
    Returns a file-like object containing PNG image data.
    """
    dates = [datetime.fromisoformat(d) for d, _ in points]
    balances = [b for _, b in points]

    fig, ax = plt.subplots()
    ax.plot(dates, balances, marker="o")
    ax.set_xlabel("Date")
    ax.set_ylabel("Balance")
    fig.autofmt_xdate()

    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf
