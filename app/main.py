"""
main.py — Entry Point

Two run modes:

  python -m app.main            → run full migration pipeline
  python -m app.main --bot      → run the admin bot only (for /status checks)

The migration pipeline:
  connect → fetch members → save to DB → generate invite → send DMs → track joins
"""

import asyncio
import sys

from . import database
from .telegram import client
from .services import migration_service
from .bot import run_bot


async def main():
    """Full migration pipeline entry point."""

    print("╔══════════════════════════════════════╗")
    print("║   Telegram Group Migration Tool      ║")
    print("╚══════════════════════════════════════╝\n")

    try:
        await client.start()
        await database.init_db()
        await migration_service.run_migration()

    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user.")

    finally:
        await database.close_pool()
        if client.is_connected():
            await client.disconnect()
        print("[Main] Shutdown complete.")


if __name__ == "__main__":
    # --bot flag: run admin bot only (no migration pipeline)
    if "--bot" in sys.argv:
        run_bot()
    else:
        asyncio.run(main())
