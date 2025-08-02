import asyncio
import sys
from models.db import Database
from models.seed_data import INITIAL_HISTORY, MOOD_MAP
from services.money import parse_money

async def main(user_id: int):
    db = Database()
    for d, balance_str, delta_text, note, mood_label in INITIAL_HISTORY:
        if balance_str is None:
            balance = None
        else:
            try:
                balance = float(parse_money(balance_str))
            except Exception:
                balance = None
        mood = MOOD_MAP.get(mood_label, "green")
        await db.add_history(user_id, d, balance, delta_text, note, mood)
    await db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/seed_history.py <user_id>")
        raise SystemExit(1)
    asyncio.run(main(int(sys.argv[1])))
