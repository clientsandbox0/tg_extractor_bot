"""
database.py

Responsibility:
  PostgreSQL connection and all DB operations for the migration tool.
  Uses asyncpg for async query execution.

  Schema:
    users (
        user_id      BIGINT PRIMARY KEY,
        username     TEXT,
        first_name   TEXT,
        last_name    TEXT,
        fetched_at   TIMESTAMP,
        notified_at  TIMESTAMP,
        joined_at    TIMESTAMP
    )
"""

import os

import asyncpg  # pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Module-level connection pool — initialized once on startup
_pool: asyncpg.Pool | None = None


# ── Connection Pool ───────────────────────────────────────────────────────────

async def get_pool() -> asyncpg.Pool:
    """Return the shared connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def close_pool():
    """Gracefully close the connection pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ── Schema ────────────────────────────────────────────────────────────────────

async def init_db():
    """
    Create the `users` table if it does not already exist.
    Safe to call on every startup.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      BIGINT PRIMARY KEY,
                username     TEXT,
                first_name   TEXT,
                last_name    TEXT,
                fetched_at   TIMESTAMP DEFAULT NOW(),
                notified_at  TIMESTAMP,
                joined_at    TIMESTAMP
            );
        """)
    print("[Database] Schema ready.")


# ── Write Operations ──────────────────────────────────────────────────────────

async def save_members(members: list[dict]):
    """
    Bulk-insert members. Uses ON CONFLICT DO NOTHING so re-runs
    don't overwrite existing rows or raise duplicate key errors.
    """
    if not members:
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO NOTHING;
            """,
            [
                (m["user_id"], m["username"], m["first_name"], m["last_name"])
                for m in members
            ],
        )
    print(f"[Database] {len(members)} members saved (duplicates skipped).")


async def mark_notified(user_id: int):
    """Set notified_at = NOW() for the given user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET notified_at = NOW() WHERE user_id = $1;",
            user_id,
        )


async def mark_joined(user_id: int) -> bool:
    """
    Set joined_at = NOW() for a user — only if they are in our migration list.

    Returns:
        True  — row updated (user was in old group)
        False — user_id not found in DB
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE users SET joined_at = NOW() WHERE user_id = $1;",
            user_id,
        )
    # asyncpg returns "UPDATE N" — check N > 0
    return result == "UPDATE 1"


# ── Read Operations ───────────────────────────────────────────────────────────

async def get_unnotified_members() -> list[dict]:
    """Return all members who have not yet been sent an invite DM."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, username, first_name FROM users WHERE notified_at IS NULL;"
        )
    return [dict(row) for row in rows]


async def get_migration_stats() -> dict:
    """
    Return a summary of migration progress.

    Returns:
        {
            "total":     int,   # all fetched members
            "notified":  int,   # members sent an invite
            "joined":    int,   # members who joined the new group
        }
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*)                                    AS total,
                COUNT(*) FILTER (WHERE notified_at IS NOT NULL) AS notified,
                COUNT(*) FILTER (WHERE joined_at IS NOT NULL)   AS joined
            FROM users;
        """)
    return {
        "total":    row["total"],
        "notified": row["notified"],
        "joined":   row["joined"],
    }


async def get_all_members() -> list[dict]:
    """Return every member row with their full migration status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, username, first_name, last_name, "
            "fetched_at, notified_at, joined_at FROM users ORDER BY user_id;"
        )
    return [dict(row) for row in rows]
