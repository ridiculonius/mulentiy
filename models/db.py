from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

DB_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"


def get_balance_history(user_id: int, days: int) -> List[Tuple[str, float]]:
    """Return balance history for a user for the last ``days`` days.

    The function expects a table ``balance_history`` with columns
    ``user_id`` (INTEGER), ``date`` (TEXT, YYYY-MM-DD) and ``balance`` (REAL).
    Results are ordered by date ascending.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    start = date.today() - timedelta(days=days - 1)
    cur.execute(
        """
        SELECT date, balance
          FROM balance_history
         WHERE user_id = ? AND date >= ?
         ORDER BY date ASC
        """,
        (user_id, start.isoformat()),
    )
    rows = cur.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]
