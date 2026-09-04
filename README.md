# Telegram Group Migration Tool

A step-by-step Python tool to read members from an old Telegram group,
save them, notify them, and track voluntary joins to a new group.

Built with [Telethon](https://docs.telethon.dev/) and Python 3.11.

---

## Project Structure

```
telegram-migration/
│
├── .env                  
├── requirements.txt      
├── app/
│   ├── __init__.py       
│   ├── main.py           
│   ├── telegram.py       
│   ├── database.py       
│   └── migration.py      
│
└── data/                 
```

---

## File Purposes

### Root

| File | Purpose |
|------|---------|
| `.env` | Stores secret credentials — API ID, API Hash, and old group ID. Never commit this file to Git. |
| `requirements.txt` | Lists all Python packages needed to run the project (`Telethon`, `python-dotenv`). |
| `README.md` | This file. Documents the project structure, file purposes, and build plan. |

---

### `app/` — Application Package

| File | Purpose |
|------|---------|
| `__init__.py` | Marks the `app/` folder as a Python package so files inside can import from each other using relative imports (e.g., `from .telegram import client`). |
| `telegram.py` | Creates and exports the Telethon `TelegramClient` instance. Reads `API_ID` and `API_HASH` from `.env`. All other modules import the client from here. |
| `migration.py` | Contains the core logic — connects to Telegram, calls `iter_participants()` on the old group, and returns a list of accessible members. |
| `database.py` | Reserved for Step 2. Will contain PostgreSQL connection and functions to save members into a `users` table. Empty for now. |
| `main.py` | Entry point of the application. Calls `get_old_group_members()`, prints results, and cleanly disconnects the client. Run with `python -m app.main`. |

---

### `data/`

| Folder | Purpose |
|--------|---------|
| `data/` | Output directory. Will store exported member lists, reports, or migration logs as the project grows. Empty for now. |

---

## Environment Variables (`.env`)

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here

OLD_GROUP_ID=-1001234567890
```

Get your API ID and API Hash from: https://my.telegram.org

---

## Setup

```bash
# 1. Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your credentials to .env

# 4. Run
python -m app.main
```

> **First run:** Telethon will ask for your phone number and a login code
> sent to your Telegram account. After that, a `telegram_migration.session`
> file is created locally. Protect it — it holds your active session.

---

## Build Plan

| Step | Status | Description |
|------|--------|-------------|
| 1 | 🔨 In Progress | Telethon client + read old group members |
| 2 | ⏳ Pending | Save members to PostgreSQL (`users` table) |
| 3 | ⏳ Pending | Create new group invite link |
| 4 | ⏳ Pending | Send migration announcement to old group |
| 5 | ⏳ Pending | Track voluntary joins to the new group |
| 6 | ⏳ Pending | `/status` bot command |
| 7 | ⏳ Pending | Automatic migration report |

---

## Security Notes

- `.env` must be added to `.gitignore` — never push credentials to Git.
- `telegram_migration.session` must also be in `.gitignore` — it is an active authenticated session.
- Do not hardcode API keys or tokens anywhere in Python files.
