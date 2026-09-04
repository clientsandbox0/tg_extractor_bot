"""
adder_service.py

Responsibility:
  Directly adds extracted members into the new Telegram group using Telethon
  (the account with creator/admin permissions) without sending private DMs.

Handles:
  - UserAlreadyParticipantError (marks as joined)
  - UserPrivacyRestrictedError (user settings block adds)
  - UserChannelsTooMuchError / UserNotMutualContactError
  - FloodWaitError (pauses cleanly to protect account)
  - PeerFloodError (stops batch safely to prevent account ban)
"""

import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.errors import (
    UserPrivacyRestrictedError,
    UserAlreadyParticipantError,
    FloodWaitError,
    PeerFloodError,
    UserChannelsTooMuchError,
    UserNotMutualContactError,
    UserIdInvalidError,
    UserBannedInChannelError,
)
from .. import database

ADD_DELAY = 2.5  # Seconds between additions to keep within safe rate limits
DEFAULT_BATCH_SIZE = 50  # Process up to 50 members per run to safeguard account health


async def direct_add_members(client: TelegramClient, target_group_id: int, max_to_add: int = DEFAULT_BATCH_SIZE) -> dict:
    """
    Directly adds pending members from the database to the target group.
    """
    members = await database.get_pending_add_members(limit=max_to_add)
    total = len(members)
    print(f"\n[AdderService] Found {total} pending members to add (batch limit: {max_to_add})...")

    stats = {
        "added": 0,
        "already_participant": 0,
        "privacy_restricted": 0,
        "skipped": 0,
        "failed": 0,
    }

    if not members:
        print("[AdderService] No pending members to add.")
        return stats

    target_entity = await client.get_input_entity(target_group_id)

    for i, m in enumerate(members, 1):
        user_id = m["user_id"]
        username = m.get("username") or m.get("first_name") or str(user_id)

        try:
            user_entity = await client.get_input_entity(user_id)
            await client(InviteToChannelRequest(
                channel=target_entity,
                users=[user_entity],
            ))
            await database.mark_add_result(user_id, "added")
            stats["added"] += 1
            print(f"[AdderService] [{i}/{total}]  Added {username} ({user_id})")
            await asyncio.sleep(ADD_DELAY)

        except UserAlreadyParticipantError:
            await database.mark_add_result(user_id, "already_participant")
            stats["already_participant"] += 1
            print(f"[AdderService] [{i}/{total}]  Already in group: {username}")

        except UserPrivacyRestrictedError:
            await database.mark_add_result(user_id, "privacy_restricted")
            stats["privacy_restricted"] += 1
            print(f"[AdderService] [{i}/{total}] ⚠️ Privacy restricted (cannot be added directly): {username}")

        except (UserChannelsTooMuchError, UserNotMutualContactError, UserIdInvalidError, UserBannedInChannelError) as e:
            err_name = type(e).__name__
            await database.mark_add_result(user_id, f"skipped: {err_name}")
            stats["skipped"] += 1
            print(f"[AdderService] [{i}/{total}] ⚠️ Skipped {username} ({err_name})")

        except FloodWaitError as e:
            print(f"[AdderService] ⏳ FloodWait: Telegram requests waiting {e.seconds}s. Pausing...")
            if e.seconds <= 30:
                await asyncio.sleep(e.seconds)
            else:
                print(f"[AdderService] FloodWait duration is long ({e.seconds}s). Stopping batch to protect account.")
                break

        except PeerFloodError:
            print("[AdderService] ⚠️ PeerFloodError: Telegram is limiting add requests for today. Stopping batch.")
            break

        except Exception as e:
            err_msg = str(e)[:50]
            await database.mark_add_result(user_id, f"error: {err_msg}")
            stats["failed"] += 1
            print(f"[AdderService] [{i}/{total}] ⚠️ Error on {username}: {e}")
            await asyncio.sleep(ADD_DELAY)

    print(f"\n[AdderService] Batch complete: {stats}")
    return stats
