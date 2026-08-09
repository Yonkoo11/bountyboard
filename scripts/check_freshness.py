"""Fail when BountyBoard's last successful full refresh is too old."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
LAST_RUN_FILE = REPO_DIR / "data" / "last_run.json"


def evaluate_freshness(
    manifest: dict, *, now: datetime | None = None, max_age_hours: float = 8
) -> tuple[bool, str]:
    raw = manifest.get("completed_at")
    if not isinstance(raw, str) or not raw.strip():
        return False, "last run has no completed_at timestamp"
    try:
        completed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False, f"last run has invalid completed_at timestamp: {raw!r}"
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age_hours = (current.astimezone(timezone.utc) - completed.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours < -0.25:
        return False, f"last run timestamp is {-age_hours:.1f}h in the future"
    if age_hours > max_age_hours:
        return False, f"last successful refresh is {age_hours:.1f}h old (limit {max_age_hours:g}h)"
    return True, f"last successful refresh is {max(0, age_hours):.1f}h old"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-age-hours", type=float, default=8)
    args = parser.parse_args()
    try:
        manifest = json.loads(LAST_RUN_FILE.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"FRESHNESS CHECK FAILED: {error}")
        return 1
    healthy, message = evaluate_freshness(manifest, max_age_hours=args.max_age_hours)
    print(f"FRESHNESS CHECK {'PASSED' if healthy else 'FAILED'}: {message}")
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
