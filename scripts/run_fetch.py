"""
scripts/run_fetch.py

Called by: .github/workflows/fetch_and_notify.yml

Steps:
  1. Connect Telethon with pre-existing session file
  2. Initialize DB schema
  3. Fetch members from old group → save to PostgreSQL
  4. Generate invite link for new group
  5. Send invite DMs to all unnotified members (rate-limited)
"""

import asyncio
import os
import sys

# Allow imports from app/ package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.telegram import client
from app import database
from app.services.member_service import fetch_and_save
from app.services.adder_service import direct_add_members

NEW_GROUP_ID = int(os.getenv("NEW_GROUP_ID"))


async def main():
    print("=== [run_fetch.py] Fetch & Direct Add ===\n")

    # Connect — session file already restored by workflow
    await client.start()
    print("Connected to Telegram.\n")

    # Ensure DB schema exists
    await database.init_db()

    # Fetch members from old group → save to DB
    members = await fetch_and_save()
    if not members:
        print("No members found. Exiting.")
        await client.disconnect()
        await database.close_pool()
        return

    # Directly add members to the new group (batch of 50 per run)
    stats = await direct_add_members(client, NEW_GROUP_ID, max_to_add=50)
    print(f"\n[run_fetch.py] Direct add batch results: {stats}")

    await client.disconnect()
    await database.close_pool()
    print("\n[run_fetch.py] Complete.")


if __name__ == "__main__":
    asyncio.run(main())
