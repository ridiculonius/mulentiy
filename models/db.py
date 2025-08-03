import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from services.money import format_money

DB_PATH = Path('bot.db')


CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    last_site REAL,
    last_unconfirmed REAL,
    last_tbank REAL,
    last_ozone REAL
);
"""

CREATE_HISTORY = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    d TEXT,
    balance REAL,
    delta_text TEXT,
    note TEXT,
    mood TEXT CHECK(mood IN ('green','yellow','red')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_history_user_date ON history(user_id, d);
"""


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.path)
            await self._conn.execute("PRAGMA foreign_keys = ON")
            await self._conn.execute(CREATE_USERS)
            await self._conn.execute(CREATE_HISTORY)
            await self._conn.execute(CREATE_INDEX)
            await self._conn.commit()
        return self._conn

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def get_last_values(self, user_id: int) -> Dict[str, Optional[float]]:
        conn = await self.connect()
        async with conn.execute(
            "SELECT last_site, last_unconfirmed, last_tbank, last_ozone FROM users WHERE user_id=?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            return {
                "site": row[0],
                "unconfirmed": row[1],
                "tbank": row[2],
                "ozone": row[3],
            }
        await conn.execute("INSERT INTO users(user_id) VALUES(?)", (user_id,))
        await conn.commit()
        return {"site": None, "unconfirmed": None, "tbank": None, "ozone": None}

    async def update_last_values(self, user_id: int, **values: float):
        conn = await self.connect()
        fields = [
            f"last_{k}=?" for k in values
        ]
        params = list(values.values())
        params.append(user_id)
        await conn.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE user_id=?",
            params,
        )
        await conn.commit()

    async def get_last_balance(self, user_id: int) -> Optional[float]:
        conn = await self.connect()
        async with conn.execute(
            "SELECT balance FROM history WHERE user_id=? ORDER BY d DESC LIMIT 1",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def add_history(
        self,
        user_id: int,
        d: str,
        balance: float,
        delta_text: str,
        note: str,
        mood: str,
    ) -> int:
        conn = await self.connect()
        cursor = await conn.execute(
            "INSERT INTO history(user_id, d, balance, delta_text, note, mood) VALUES(?,?,?,?,?,?)",
            (user_id, d, balance, delta_text, note, mood),
        )
        await conn.commit()
        return cursor.lastrowid

    async def list_history(self, user_id: int, offset: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        conn = await self.connect()
        async with conn.execute(
            "SELECT id, d, balance, delta_text, note, mood FROM history WHERE user_id=? ORDER BY d DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "d": r[1],
                "balance": r[2],
                "delta_text": r[3],
                "note": r[4],
                "mood": r[5],
            }
            for r in rows
        ]

    async def count_history(self, user_id: int) -> int:
        conn = await self.connect()
        async with conn.execute(
            "SELECT COUNT(*) FROM history WHERE user_id=?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_balance_history(self, user_id: int, days: int) -> List[Tuple[str, float]]:
        """Return (date, balance) tuples for the last `days` records."""
        conn = await self.connect()
        async with conn.execute(
            "SELECT d, balance FROM history WHERE user_id=? AND balance IS NOT NULL ORDER BY d DESC LIMIT ?",
            (user_id, days),
        ) as cursor:
            rows = await cursor.fetchall()
        rows.reverse()
        return [(r[0], r[1]) for r in rows]

    async def get_history(self, user_id: int, record_id: int) -> Optional[Dict[str, Any]]:
        conn = await self.connect()
        async with conn.execute(
            "SELECT id, d, balance, delta_text, note, mood FROM history WHERE user_id=? AND id=?",
            (user_id, record_id),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "d": row[1],
                "balance": row[2],
                "delta_text": row[3],
                "note": row[4],
                "mood": row[5],
            }
        return None

    async def update_history(self, user_id: int, record_id: int, **fields: Any):
        if not fields:
            return
        conn = await self.connect()
        sets = ", ".join(f"{k}=?" for k in fields)
        params = list(fields.values()) + [user_id, record_id]
        await conn.execute(
            f"UPDATE history SET {sets} WHERE user_id=? AND id=?",
            params,
        )
        await conn.commit()

    async def delete_history(self, user_id: int, record_id: int):
        conn = await self.connect()
        await conn.execute(
            "DELETE FROM history WHERE user_id=? AND id=?",
            (user_id, record_id),
        )
        await conn.commit()


    async def recalc_deltas_from(self, user_id: int, start_date: str):
        conn = await self.connect()
        async with conn.execute(
            "SELECT balance FROM history WHERE user_id=? AND d < ? ORDER BY d DESC LIMIT 1",
            (user_id, start_date),
        ) as cursor:
            row = await cursor.fetchone()
        prev = Decimal(str(row[0])) if row and row[0] is not None else None
        async with conn.execute(
            "SELECT id, d, balance FROM history WHERE user_id=? AND d >= ? ORDER BY d",
            (user_id, start_date),
        ) as cursor:
            rows = await cursor.fetchall()
        for rid, d, balance in rows:
            if balance is None:
                delta_text = "-"
            elif prev is None:
                delta_text = "начало"
                prev = Decimal(str(balance))
            else:
                delta_text = format_money(Decimal(str(balance)) - prev)
                prev = Decimal(str(balance))
            await conn.execute(
                "UPDATE history SET delta_text=? WHERE id=?",
                (delta_text, rid),
            )
        await conn.commit()

    async def seed_history_if_empty(self, user_id: int):
        if await self.count_history(user_id) > 0:
            return
        from models.seed_data import INITIAL_HISTORY, MOOD_MAP
        from services.money import parse_money
        for d, balance_str, delta_text, note, mood_label in INITIAL_HISTORY:
            if balance_str is None:
                balance = None
            else:
                try:
                    balance = float(parse_money(balance_str))
                except Exception:
                    balance = None
            mood = MOOD_MAP.get(mood_label, "green")
            await self.add_history(user_id, d, balance, delta_text, note, mood)
