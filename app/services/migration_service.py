"""
migration_service.py

Responsibility:
  Orchestrate the full migration flow in sequence:

  1. Connect Telethon client
  2. Fetch members from old group → save to DB
  3. Generate invite link for new group
  4. Send invite DMs to all members (via notification_service)
  5. Start tracking joins on new group (via tracking_service)
"""

import os

from dotenv import load_dotenv

from ..telegram import client
from .. import database
from . import member_service, notification_service, tracking_service

load_dotenv()

NEW_GROUP_ID = int(os.getenv("NEW_GROUP_ID"))


async def generate_invite_link() -> str:
    """
    Create a new invite link for the new group via Telethon.
    Requires the user account to be an admin of the new group.
    """
    print("[MigrationService] Generating invite link for new group...")
    link = await client(
        # ExportChatInviteRequest creates a new single-use or unlimited link
        __import__(
            "telethon.tl.functions.messages",
            fromlist=["ExportChatInviteRequest"]
        ).ExportChatInviteRequest(peer=NEW_GROUP_ID)
    )
    invite_url = link.link
    print(f"[MigrationService] Invite link: {invite_url}")
    return invite_url


async def run_migration():
    """
    Full migration pipeline. Call this once to kick off the entire process.

    Flow:
        connect → fetch members → save to DB
        → generate invite link → send DMs
        → start join tracking (runs until disconnected)
    """

    # ── Step 1: Connect ──────────────────────────────────────────
    print("\n[MigrationService] === Starting Migration ===\n")
    print("[MigrationService] Connecting to Telegram...")
    await client.start()
    print("[MigrationService] Connected.\n")

    # ── Step 2: Initialize DB schema ────────────────────────────
    await database.init_db()

    # ── Step 3: Fetch members + save ────────────────────────────
    members = await member_service.fetch_and_save()

    if not members:
        print("[MigrationService] No members found. Aborting.")
        await client.disconnect()
        return

    # ── Step 4: Generate invite link ────────────────────────────
    invite_link = await generate_invite_link()

    # ── Step 5: Send invite DMs ─────────────────────────────────
    stats = await notification_service.send_bulk_invites(invite_link)
    print(f"\n[MigrationService] Notifications sent: {stats}")

    # ── Step 6: Start tracking joins ────────────────────────────
    await tracking_service.start_tracking()

    print("\n[MigrationService] Tracking active. Waiting for members to join...")
    print("[MigrationService] Press Ctrl+C to stop.\n")

    # Keep the Telethon event loop alive so the tracker keeps running
    await client.run_until_disconnected()
