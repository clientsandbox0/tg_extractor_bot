"""
bot.py

Responsibility:
  Telegram Bot admin interface.
  Commands available to ADMIN_USER_ID only:

    /start   — trigger the migration pipeline
    /status  — live migration progress (total / notified / joined)
    /report  — full member table with join status
    /help    — list all commands
"""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Update  # pyrefly: ignore [missing-import]
from telegram.ext import (  # pyrefly: ignore [missing-import]
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from . import database
from .services import migration_service

load_dotenv()

BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))


# ── Auth guard ────────────────────────────────────────────────────────────────

def admin_only(func):
    """Decorator — silently ignores commands from non-admins."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("⛔ Unauthorized.")
            return
        return await func(update, context)
    return wrapper


# ── Command Handlers ──────────────────────────────────────────────────────────

@admin_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *Migration Bot — Commands*\n\n"
        "/status  — migration progress\n"
        "/report  — full member list\n"
        "/start\\_migration  — begin migration pipeline\n"
        "/help    — this message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@admin_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live migration stats."""
    try:
        stats = await database.get_migration_stats()
        total    = stats["total"]
        notified = stats["notified"]
        joined   = stats["joined"]
        pending  = total - joined

        pct = f"{(joined / total * 100):.1f}%" if total > 0 else "0%"

        text = (
            f"📊 *Migration Status*\n\n"
            f"👥 Total members:   `{total}`\n"
            f"📨 Notified:        `{notified}`\n"
            f"✅ Joined new group: `{joined}`\n"
            f"⏳ Pending:          `{pending}`\n"
            f"📈 Progress:         `{pct}`"
        )
    except Exception as e:
        text = f"❌ Error fetching stats: {e}"

    await update.message.reply_text(text, parse_mode="Markdown")


@admin_only
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Print all members with their join status."""
    try:
        members = await database.get_all_members()

        if not members:
            await update.message.reply_text("No members in database yet.")
            return

        lines = ["📋 *Full Member Report*\n"]
        for m in members:
            joined_mark = "✅" if m["joined_at"] else "⏳"
            name = f"{m['first_name'] or ''} {m['last_name'] or ''}".strip()
            username = f"@{m['username']}" if m["username"] else "no username"
            lines.append(f"{joined_mark} {name} ({username}) — `{m['user_id']}`")

        # Telegram message limit: 4096 chars — split if needed
        message = "\n".join(lines)
        if len(message) > 4000:
            message = message[:4000] + "\n\n_(truncated — too many members)_"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


@admin_only
async def cmd_start_migration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick off the full migration pipeline."""
    await update.message.reply_text(
        "🚀 Starting migration pipeline...\n"
        "Check your terminal for live progress."
    )
    # Run migration in background — don't block the bot
    asyncio.create_task(migration_service.run_migration())


# ── Bot Runner ────────────────────────────────────────────────────────────────

def run_bot():
    """Build and start the bot (blocking — runs until Ctrl+C)."""
    print("[Bot] Starting admin bot...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("help",              cmd_help))
    app.add_handler(CommandHandler("status",            cmd_status))
    app.add_handler(CommandHandler("report",            cmd_report))
    app.add_handler(CommandHandler("start_migration",   cmd_start_migration))

    print("[Bot] Bot running. Send /help to your bot on Telegram.")
    app.run_polling()
