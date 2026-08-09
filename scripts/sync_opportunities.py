"""Export the canonical SQLite opportunity rows to versioned JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_DIR))
import db

OUTPUT = REPO_DIR / "data" / "opportunities.json"
FIELDS = [
    "id", "name", "category", "deadline", "start_date", "prize_usd", "prize_note",
    "theme_fit", "status", "tracks", "angle", "url", "resubmittable", "notes",
    "submission_url", "source", "verification_status", "verified_at",
    "last_checked_at", "application_status", "eligibility", "award_type",
    "max_award_usd", "win_probability", "format", "location",
]


def main() -> None:
    rows = db.get_all()
    exported = [{key: row[key] for key in FIELDS if key in row} for row in rows]
    OUTPUT.write_text(json.dumps(exported, indent=2, ensure_ascii=True) + "\n")
    print(f"Synced {len(exported)} opportunities to {OUTPUT.relative_to(REPO_DIR)}")


if __name__ == "__main__":
    main()
