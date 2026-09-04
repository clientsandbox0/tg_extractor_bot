"""
scripts/run_check_joins.py

Called by: .github/workflows/check_joins.yml  (every 30 min)

Steps:
  1. Connect Telethon
  2. Fetch current participant list of the NEW group
  3. For each participant, check if they exist in our DB (old group member)
  4. Mark joined_at = NOW() for any that haven't been recorded yet
  5. Disconnect and exit

This is a polling replacement for the real-time tracking_service.py
event listener (which requires a persistent process).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.telegram import client
from app import database
from telethon.tl.types import User  # pyrefly: ignore [missing-import]

NEW_GROUP_ID = int(os.getenv("NEW_GROUP_ID"))


async def main():
    print("=== [run_check_joins.py] Polling new group for joins ===\n")

    await client.start()
    print("Connected.\n")

    await database.init_db()

    new_joins = 0
    total_checked = 0

    print(f"Scanning participants of new group {NEW_GROUP_ID}...")

    async for user in client.iter_participants(NEW_GROUP_ID):
        if not isinstance(user, User):
            continue

        total_checked += 1
        updated = await database.mark_joined(user.id)

        if updated:
            new_joins += 1
            print(f"  ✓ Marked joined: {user.id} (@{user.username})")

    print(f"\nScanned: {total_checked} | Newly recorded joins: {new_joins}")

    await client.disconnect()
    await database.close_pool()
    print("\n[run_check_joins.py] Complete.")


if __name__ == "__main__":
    asyncio.run(main())
