import os

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Single shared client instance — imported by all other modules
client = TelegramClient(
    "telegram_migration",  # session file name
    API_ID,
    API_HASH,
)
