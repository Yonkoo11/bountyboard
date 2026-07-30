# BountyBoard — Opportunity Radar

A CLI and public dashboard for broadly discovering hackathons, grants,
accelerators, and bounties. Incomplete leads stay visible and are labeled by
verification state so discovery coverage is not confused with certainty.

---

## Requirements

- macOS (Calendar sync and notifications use osascript)
- Python 3.10+
- Apple Calendar app

---

## Install

```bash
git clone https://github.com/Yonkoo11/bountyboard.git
cd bountyboard

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## First Run

Seed the database (only needed once):

```bash
python scripts/migrate.py
```

Verify it worked:

```bash
python roster.py
```

---

## Telegram Setup (optional but recommended)

1. Open Telegram, search `@BotFather`, send `/newbot` — copy the token
2. Send your bot any message, then open:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   Find `"chat":{"id":...}` — that's your chat ID
3. Copy the env file and fill in your values:

```bash
cp .env.example .env
# edit .env with your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

4. Test it:

```bash
python scripts/notify.py info "hello"
```

---

## Automation

GitHub Actions discovers, checks, tests, generates, and publishes the radar
daily. The `launchd/` definitions provide optional local macOS automation for
calendar synchronization, daily briefings, and additional scouts.

---

## Commands

```
python roster.py                  Weekly focus report (default)
python roster.py today            Due this week
python roster.py list             All active opportunities
python roster.py list must        Must-Do tier only
python roster.py search <query>   Full-text search
python roster.py ideas            Winning ideas for Must-Do events
python roster.py sprint           Sprint plan + build order
python roster.py review           Triage auto-discovered items
python roster.py approve <id>     Approve a scouted item
python roster.py reject <id>      Reject a scouted item
python roster.py bulk-reject      Reject multiple at once
python roster.py add              Add opportunity manually
python roster.py add-url <url>    Add from URL (auto-scrapes title/deadline)
python roster.py edit <id>        Edit an existing entry
python roster.py done <id>        Mark as submitted
python roster.py outcome <id>     Record win/loss result
python roster.py stats            Win rate analytics by source
python roster.py export           Export all to data/export.csv
python roster.py undo             Undo last field change
python roster.py health           System health status
```

---

## Web Dashboard

```bash
python3 scripts/generate_site.py
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000`.

---

## Manual Scout

```bash
python scripts/scout.py              # all sources
python scripts/scout.py --dry-run    # preview, no writes
python scripts/scout.py --source devpost  # single source
```

Sources: ETHGlobal, Devpost, DoraHacks, Gitcoin, Solana Foundation, Twitter/X signals.

---

## Calendar Sync

```bash
python scripts/sync_calendar.py           # sync all unsynced deadlines
python scripts/sync_calendar.py --dry-run # preview only
python scripts/sync_calendar.py --force   # re-sync everything
```

Each event gets 3 reminders: 7 days, 3 days, and 1 day before deadline.

---

## Data

| Path | Contents |
|---|---|
| `data/roster.db` | SQLite database (source of truth) |
| `data/backups/YYYY-MM-DD.json` | Daily versioned backups |
| `data/audit.jsonl` | Audit log of every field change |
| `data/scout_candidates.json` | Low-score items pending review |
| `logs/` | Cron logs per run |

---

## Health Check

```bash
python roster.py health
```

Shows: last scout time, last calendar sync, DB counts by status, backup age, per-source result counts.
