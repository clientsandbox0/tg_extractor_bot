"""
notification_service.py

Responsibility:
  Send a direct message to each member via the Telegram Bot,
  containing the invite link to the new group.

  Rate-limited to avoid Telegram flood restrictions:
  ~1 message per second (safe default).
"""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot  # pyrefly: ignore [missing-import]
from telegram.error import TelegramError  # pyrefly: ignore [missing-import]

from .. import database

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Delay between DMs in seconds — keeps us under Telegram flood limits
RATE_LIMIT_DELAY = 1.2


async def send_invite(bot: Bot, user_id: int, invite_link: str) -> bool:
    """
    Send invite link DM to a single user.

    Returns:
        True  — message delivered
        False — user blocked the bot or has privacy settings preventing DMs
    """
    message = (
        "👋 Hi! Our group is moving to a new space.\n\n"
        "Click the link below to join the new group:\n"
        f"{invite_link}\n\n"
        "We hope to see you there! 🚀"
    )
    try:
        await bot.send_message(chat_id=user_id, text=message)
        return True
    except TelegramError as e:
        print(f"[NotificationService] Could not DM user {user_id}: {e}")
        return False


async def send_bulk_invites(invite_link: str) -> dict:
    """
    Send the invite link DM to all members stored in the DB
    that have not yet been notified.

    Returns:
        {
            "sent": int,
            "failed": int,
        }
    """
    bot = Bot(token=BOT_TOKEN)
    members = await database.get_unnotified_members()

    sent = 0
    failed = 0

    print(f"[NotificationService] Sending invites to {len(members)} members...")

    for member in members:
        user_id = member["user_id"]
        success = await send_invite(bot, user_id, invite_link)

        if success:
            await database.mark_notified(user_id)
            sent += 1
            print(f"[NotificationService] ✓ Sent to {user_id}")
        else:
            failed += 1

        # Rate-limit: pause between each DM
        await asyncio.sleep(RATE_LIMIT_DELAY)

    print(f"[NotificationService] Done. Sent: {sent} | Failed: {failed}")
    return {"sent": sent, "failed": failed}
