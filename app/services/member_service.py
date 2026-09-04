"""
member_service.py

Responsibility:
  1. Fetch all accessible participants from all old Telegram groups
  2. Deduplicate across groups by user_id
  3. Persist them into the PostgreSQL `users` table via database.py
"""

import os

from dotenv import load_dotenv
from telethon.tl.types import User  # pyrefly: ignore [missing-import]

from ..telegram import client
from .. import database

load_dotenv()

# Supports multiple old groups as comma-separated list in OLD_GROUP_IDS
_raw = os.getenv("OLD_GROUP_IDS", os.getenv("OLD_GROUP_ID", ""))
OLD_GROUP_IDS = [int(gid.strip()) for gid in _raw.split(",") if gid.strip()]


async def fetch_members() -> list[dict]:
    """
    Read all participants from ALL old groups via Telethon.
    Deduplicates by user_id across groups.
    Skips bots and non-User entities.

    Returns:
        List of unique member dicts with keys:
        user_id, username, first_name, last_name
    """
    seen_ids: set[int] = set()
    members: list[dict] = []

    for group_id in OLD_GROUP_IDS:
        print(f"[MemberService] Fetching from group {group_id}...")
        count = 0

        try:
            async for user in client.iter_participants(group_id):
                if not isinstance(user, User):
                    continue
                if user.id in seen_ids:
                    continue  # already fetched from another group

                seen_ids.add(user.id)
                count += 1
                members.append({
                    "user_id":    user.id,
                    "username":   user.username,
                    "first_name": user.first_name,
                    "last_name":  user.last_name,
                })

            print(f"[MemberService]   → {count} new unique members from group {group_id}")
        except Exception as e:
            print(f"[MemberService]   ⚠️ Could not fetch from group {group_id}: {e}")

    print(f"[MemberService] Total unique members: {len(members)}")
    return members


async def fetch_and_save() -> list[dict]:
    """
    Fetch members from Telegram and immediately persist them to the DB.
    Returns the full member list.
    """
    members = await fetch_members()
    await database.save_members(members)
    print("[MemberService] Members saved to database.")
    return members
