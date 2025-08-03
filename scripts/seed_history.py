import asyncio
import sys
from models.db import Database


async def main(user_id: int, username: str | None):
    db = Database()
    await db.seed_history_if_empty(user_id, username)
    await db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python scripts/seed_history.py <user_id> [username]")
        raise SystemExit(1)
    uid = int(sys.argv[1])
    uname = sys.argv[2] if len(sys.argv) == 3 else None
    asyncio.run(main(uid, uname))
