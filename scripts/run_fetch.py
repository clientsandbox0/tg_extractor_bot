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
from app.services.notification_service import send_bulk_invites
from telethon.tl.functions.messages import ExportChatInviteRequest  # pyrefly: ignore [missing-import]

NEW_GROUP_ID = int(os.getenv("NEW_GROUP_ID"))


async def main():
    print("=== [run_fetch.py] Fetch & Notify ===\n")

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

    # Generate invite link for new group
    print("Generating invite link...")
    result = await client(ExportChatInviteRequest(peer=NEW_GROUP_ID))
    invite_link = result.link
    print(f"Invite link: {invite_link}\n")

    # Send DMs to all unnotified members
    stats = await send_bulk_invites(invite_link)
    print(f"\nDone. Sent: {stats['sent']} | Failed: {stats['failed']}")

    await client.disconnect()
    await database.close_pool()
    print("\n[run_fetch.py] Complete.")


if __name__ == "__main__":
    asyncio.run(main())
