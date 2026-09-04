import os

from dotenv import load_dotenv  # pyrefly: ignore [missing-import]
from telethon.tl.types import User  # pyrefly: ignore [missing-import]

from .telegram import client

load_dotenv()

OLD_GROUP_ID = int(os.getenv("OLD_GROUP_ID"))


async def get_old_group_members() -> list[dict]:
    """
    Connects to Telegram, reads all accessible participants
    from OLD_GROUP_ID, and returns them as a list of dicts.

    Returns:
        List of member dicts:
        [
            {
                "user_id": int,
                "username": str | None,
                "first_name": str | None,
                "last_name": str | None,
            },
            ...
        ]
    """

    print("Connecting to Telegram...")
    await client.start()
    print("Connected.\n")

    print(f"Reading members from group: {OLD_GROUP_ID}")

    members = []

    async for user in client.iter_participants(OLD_GROUP_ID):
        # Skip bots and non-user entities
        if not isinstance(user, User):
            continue

        members.append({
            "user_id":    user.id,
            "username":   user.username,
            "first_name": user.first_name,
            "last_name":  user.last_name,
        })

    print(f"Members found: {len(members)}")

    return members
