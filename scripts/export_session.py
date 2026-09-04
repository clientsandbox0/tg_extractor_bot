"""
scripts/export_session.py

────────────────────────────────────────────────────────────────
RUN THIS ONCE ON YOUR LOCAL MACHINE before setting up GitHub Actions.

PURPOSE:
  Telethon needs an interactive login the first time (phone + OTP).
  GitHub Actions can't do interactive login.

  This script:
    1. Starts Telethon interactively (asks for phone + code)
    2. Saves the session file locally: telegram_migration.session
    3. Base64-encodes it and prints the string

  You then paste that string as a GitHub Secret named TELEGRAM_SESSION.

USAGE:
  cd telegram-migration
  source .venv/bin/activate
  python scripts/export_session.py

AFTER RUNNING:
  Copy the printed base64 string.
  Go to: GitHub repo → Settings → Secrets → Actions → New secret
  Name:  TELEGRAM_SESSION
  Value: (paste the base64 string)
────────────────────────────────────────────────────────────────
"""

import asyncio
import base64
import os

from dotenv import load_dotenv

load_dotenv()

API_ID   = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

SESSION_FILE = "telegram_migration.session"


async def main():
    # Import here so the script can run standalone
    from telethon import TelegramClient  # pyrefly: ignore [missing-import]

    print("Starting Telethon login...\n")
    print("You will be asked for your phone number and a Telegram OTP.\n")

    client = TelegramClient(SESSION_FILE.replace(".session", ""), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"\nLogged in as: {me.first_name} (@{me.username})\n")

    await client.disconnect()

    # Read and encode the session file
    with open(SESSION_FILE, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    print("=" * 60)
    print("TELEGRAM_SESSION (copy this entire string as a GitHub Secret):")
    print("=" * 60)
    print(encoded)
    print("=" * 60)
    print(
        "\nGo to: GitHub repo → Settings → Secrets and variables → Actions"
        "\nClick: New repository secret"
        "\nName:  TELEGRAM_SESSION"
        "\nValue: (paste the string above)"
    )


if __name__ == "__main__":
    asyncio.run(main())
