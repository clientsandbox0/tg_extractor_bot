"""
tracking_service.py

Responsibility:
  Listen for new member join events on the NEW group using Telethon.
  When a known member joins, update their `joined_at` timestamp in the DB.

  Uses Telethon's event system (ChatAction) — runs as a long-lived listener.
"""

import os

from dotenv import load_dotenv
from telethon import events  # pyrefly: ignore [missing-import]

from ..telegram import client
from .. import database

load_dotenv()

NEW_GROUP_ID = int(os.getenv("NEW_GROUP_ID"))


async def start_tracking():
    """
    Register a Telethon event handler that fires whenever a user
    joins the new group. Marks them as joined in the database.

    This is non-blocking — the handler runs in the background
    via Telethon's event loop.
    """
    print(f"[TrackingService] Watching new group {NEW_GROUP_ID} for joins...")

    @client.on(events.ChatAction(chats=NEW_GROUP_ID))
    async def on_user_joined(event):
        # Only handle join events (not leaves, title changes, etc.)
        if not event.user_joined and not event.user_added:
            return

        user = await event.get_user()

        if user is None:
            return

        print(f"[TrackingService] User joined: {user.id} (@{user.username})")

        # Mark in DB — only if this user was in our old group
        updated = await database.mark_joined(user.id)

        if updated:
            print(f"[TrackingService] ✓ Recorded join for user {user.id}")
        else:
            print(f"[TrackingService] User {user.id} not in migration list — skipped.")
