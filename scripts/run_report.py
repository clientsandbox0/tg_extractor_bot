"""
scripts/run_report.py

Called by: .github/workflows/daily_report.yml  (daily at 08:00 UTC)

Steps:
  1. Query migration stats from PostgreSQL
  2. Format a summary report
  3. Send it to ADMIN_USER_ID via Telegram Bot

No Telethon session needed — uses bot only.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import database
from telegram import Bot  # pyrefly: ignore [missing-import]

BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))


async def main():
    print("=== [run_report.py] Sending daily migration report ===\n")

    await database.init_db()

    stats = await database.get_migration_stats()

    total    = stats["total"]
    notified = stats["notified"]
    joined   = stats["joined"]
    pending  = total - joined
    pct      = f"{(joined / total * 100):.1f}%" if total > 0 else "0%"

    report = (
        f"📊 *Daily Migration Report*\n\n"
        f"👥 Total members fetched: `{total}`\n"
        f"📨 Invites sent:          `{notified}`\n"
        f"✅ Joined new group:      `{joined}`\n"
        f"⏳ Yet to join:           `{pending}`\n"
        f"📈 Migration progress:    `{pct}`\n\n"
        f"_Automated report — Telegram Migration Tool_"
    )

    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=ADMIN_USER_ID, text=report, parse_mode="Markdown")
    print("Report sent to admin.")

    await database.close_pool()
    print("\n[run_report.py] Complete.")


if __name__ == "__main__":
    asyncio.run(main())
