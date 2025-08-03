import asyncio
import sys
from models.db import Database


async def main(user_id: int):
    db = Database()
    await db.seed_history_if_empty(user_id)
    await db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/seed_history.py <user_id>")
        raise SystemExit(1)
    asyncio.run(main(int(sys.argv[1])))
