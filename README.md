# Telegram Group Migration & Member Extraction Bot

An automated, cloud-native Telegram migration tool built with [Telethon](https://docs.telethon.dev/) (MTProto), PostgreSQL ([Supabase](https://supabase.com/)), and GitHub Actions.

The application extracts members across multiple source Telegram groups, deduplicates them, persists them into a cloud database, and directly adds them to the target group in controlled, ban-protected batches—completely automated without needing a local server.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph GitHub_Actions["GitHub Actions Runner"]
        Trigger["Triggers: Cron Every 6h / Push / Manual Dispatch"]
        SessionRestore["Restore Telethon Session File"]
        PythonEnv["Set up Python 3.11 Environment"]
        Trigger --> SessionRestore --> PythonEnv
    end

    subgraph Telegram_Cloud["Telegram MTProto API"]
        OldGroup1["Source Group 1 (Python Language Proxy)"]
        OldGroup2["Source Group 2 (Training, Proxy and Job Support)"]
        TargetGroup["Target Group (Aws Azure Job Support)"]
    end

    subgraph Database_Layer["Supabase PostgreSQL"]
        UsersTable[("PostgreSQL: users table")]
    end

    subgraph Pipeline["Application Pipeline (run_fetch.py)"]
        MemberService["member_service.py: Extract and Deduplicate"]
        DBSave["database.py: Upsert Members"]
        AdderService["adder_service.py: Direct Add and Anti-Flood"]
    end

    PythonEnv --> Pipeline
    OldGroup1 -->|"iter_participants"| MemberService
    OldGroup2 -->|"iter_participants"| MemberService
    MemberService --> DBSave
    DBSave --> UsersTable
    UsersTable -->|"get_pending_add_members"| AdderService
    AdderService -->|"InviteToChannelRequest"| TargetGroup
    AdderService -->|"mark_add_result"| UsersTable
```

---

## 🔄 End-to-End Flow

```
+-------------------------------------------------------------------------------+
| 1. SCHEDULED / MANUAL TRIGGER                                                 |
|    - Runs on GitHub Actions runner every 6 hours (`0 */6 * * *`) or on demand |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| 2. SESSION RESTORATION                                                        |
|    - Restores the Telethon session from encrypted GitHub Secret               |
|    - Authenticates as the authorized Telegram account (no interactive OTP)    |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| 3. DATABASE INITIALIZATION                                                    |
|    - Connects to Supabase IPv4 Pooler (port 5432) with statement caching disabled|
|    - Verifies / creates the `users` table with migration columns              |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| 4. EXTRACT & DEDUPLICATE                                                      |
|    - Loops through all configured source groups in `OLD_GROUP_IDS`            |
|    - Filters out bots and non-user entities                                   |
|    - Deduplicates members by `user_id` across groups                          |
|    - Inserts new members into PostgreSQL (`ON CONFLICT (user_id) DO NOTHING`) |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| 5. DIRECT ADD TO TARGET GROUP                                                 |
|    - Fetches next batch of pending members from database                      |
|    - Calls `InviteToChannelRequest` for each member with safe delays (2.5s)   |
|    - Handles Telegram edge cases:                                             |
|        * Success                 -> marks `add_status = 'added'`              |
|        * Already in group        -> marks `add_status = 'already_participant'`|
|        * Privacy settings block  -> marks `add_status = 'privacy_restricted'` |
|        * Channel limit reached   -> marks `add_status = 'skipped'`            |
|        * PeerFloodError / Cooldown -> stops batch safely to protect account   |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
+-------------------------------------------------------------------------------+
| 6. NEXT AUTOMATED CYCLE                                                       |
|    - On the next 6-hour trigger, resumes from the next un-added member        |
+-------------------------------------------------------------------------------+
```

---

## 📁 Repository Structure

```
tg_extractor_bot/
├── .github/
│   └── workflows/
│       └── migration.yml         # GitHub Actions unified pipeline (Cron + Dispatch)
├── app/
│   ├── __init__.py
│   ├── telegram.py               # Shared Telethon client initialization
│   ├── database.py               # Supabase PostgreSQL asyncpg connection pool & queries
│   ├── bot.py                    # Optional admin bot notification / status UI
│   ├── main.py                   # Local execution entry point
│   ├── migration.py              # CLI migration runner
│   └── services/
│       ├── __init__.py
│       ├── member_service.py     # Multi-group extraction & deduplication logic
│       ├── adder_service.py      # Direct Telegram member addition & anti-flood guard
│       ├── notification_service.py # DM invite fallback
│       └── tracking_service.py   # Event listener for voluntary new group joins
├── scripts/
│   ├── export_session.py         # One-time interactive script to generate base64 session
│   ├── run_fetch.py              # Main execution script invoked by GitHub Actions
│   ├── run_check_joins.py        # Periodic sync for voluntary join events
│   └── run_report.py             # Periodic admin summary report
├── requirements.txt              # Python dependencies
├── .gitignore                    # Prevents secrets/sessions from Git tracking
└── README.md                     # Architecture and documentation
```

---

## 🛡️ Anti-Ban & Safeguard Mechanisms

Telegram enforces strict server-side rate limits on direct group additions to prevent spam. The application implements multiple layers of protection:

| Error / Scenario | Application Behavior | Account Impact |
|---|---|---|
| **`PeerFloodError`** | Stops the current batch immediately and exits with status `0`. Preserves database progress. Resumes on next scheduled cycle. | **Prevents Telegram account bans or restrictions.** |
| **`FloodWaitError`** | If wait is short (≤30s), pauses; if longer, cleanly halts batch until next run. | Protects account from escalation. |
| **`UserPrivacyRestrictedError`** | User has privacy setting: *"Who can add me to groups: Nobody / Contacts only"*. Marked as `privacy_restricted` in DB and skipped. | No impact. |
| **`UserAlreadyParticipantError`** | User is already in the new group. Marked as `already_participant` with `joined_at = NOW()`. | No impact. |
| **`UserChannelsTooMuchError`** | User has joined Telegram's maximum channel limit (500). Marked as `skipped`. | No impact. |
| **Batch Size & Delays** | 2.5-second pacing between additions, capped at batches of 50 per cycle. | Keeps request velocity below Telegram's automated heuristic threshold. |

---

## 🗄️ Database Schema (`users` table)

Data is persisted in Supabase PostgreSQL:

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id      BIGINT PRIMARY KEY,
    username     TEXT,
    first_name   TEXT,
    last_name    TEXT,
    fetched_at   TIMESTAMP DEFAULT NOW(),
    notified_at  TIMESTAMP,
    joined_at    TIMESTAMP,
    add_status   TEXT
);
```

### `add_status` Values:
* `NULL` — Pending addition
* `'added'` — Successfully added directly into target group
* `'already_participant'` — Member was already present in target group
* `'privacy_restricted'` — User privacy settings block stranger additions
* `'skipped: <Reason>'` — User reached 500 channels or is invalid

---

## 🔐 GitHub Secrets Configuration

The pipeline runs completely from GitHub Actions without needing any local `.env` file:

| Secret Name | Description | Example / Format |
|---|---|---|
| `TELEGRAM_API_ID` | Telegram API Application ID | `32777911` |
| `TELEGRAM_API_HASH` | Telegram API Hash | `7268252f...` |
| `TELEGRAM_BOT_TOKEN` | BotFather Token for notifications | `8629924302:AAE3...` |
| `TELEGRAM_SESSION` | Base64-encoded Telethon `.session` file | `U1FMaXRlIGZvcm...` |
| `OLD_GROUP_IDS` | Comma-separated list of source group IDs | `-1001330763900,-1001353108096` |
| `NEW_GROUP_ID` | Target supergroup ID | `-1004469902513` |
| `ADMIN_USER_ID` | Admin personal Telegram ID | `8800032074` |
| `DATABASE_URL` | Supabase IPv4 Pooler connection string | `postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:5432/postgres` |

---

## 🚀 Running & Monitoring

### Automatic Schedule
The workflow runs automatically every 6 hours via GitHub Actions (`.github/workflows/migration.yml`):
```yaml
schedule:
  - cron: '0 */6 * * *'
```

### Manual Trigger
1. Go to your repository on GitHub: **Actions** tab.
2. Select **Telegram Migration Pipeline**.
3. Click **Run workflow** → Select job: `all` or `fetch-and-notify`.

### Verifying Progress via SQL
Run this query in your Supabase SQL Editor to see live migration progress:
```sql
SELECT 
    COUNT(*) AS total_extracted,
    COUNT(CASE WHEN add_status = 'added' THEN 1 END) AS successfully_added,
    COUNT(CASE WHEN add_status = 'already_participant' THEN 1 END) AS already_in_group,
    COUNT(CASE WHEN add_status = 'privacy_restricted' THEN 1 END) AS privacy_blocked,
    COUNT(CASE WHEN joined_at IS NULL AND add_status IS NULL THEN 1 END) AS pending
FROM users;
```
