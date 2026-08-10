"""Produce and optionally notify an urgency digest for personally relevant leads."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
CANDIDATES_FILE = REPO_DIR / "data" / "scout_candidates.json"
sys.path.insert(0, str(REPO_DIR))


def urgent_candidates(candidates: list[dict], *, today: date | None = None, days: int = 14) -> list[dict]:
    current = today or date.today()
    urgent: list[dict] = []
    for item in candidates:
        if item.get("profile_match") == "no" or item.get("review_status") in {"rejected", "snoozed"}:
            continue
        if item.get("application_status") in {"applied", "won", "lost", "withdrawn"}:
            continue
        raw = item.get("deadline")
        if not raw:
            continue
        try:
            deadline = datetime.strptime(str(raw), "%Y-%m-%d").date()
        except ValueError:
            continue
        remaining = (deadline - current).days
        if 0 <= remaining <= days:
            enriched = dict(item)
            enriched["days_remaining"] = remaining
            urgent.append(enriched)
    return sorted(urgent, key=lambda item: (
        int(item["days_remaining"]),
        0 if item.get("profile_match") == "yes" else 1,
        -int(item.get("theme_fit") or 0),
    ))


def render_digest(items: list[dict]) -> str:
    if not items:
        return "No personally relevant known deadlines in the alert window."
    lines = []
    for item in items:
        remaining = int(item["days_remaining"])
        timing = "today" if remaining == 0 else f"in {remaining} day{'s' if remaining != 1 else ''}"
        lines.append(
            f"- {item.get('name', 'Unnamed lead')} — {timing} — "
            f"{item.get('profile_match', 'conditional')} — {item.get('url', 'source missing')}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    candidates = json.loads(CANDIDATES_FILE.read_text())
    items = urgent_candidates(candidates, days=max(0, args.days))
    digest = render_digest(items)
    print(digest)
    if args.markdown_output:
        rendered = "# BountyBoard deadline priorities\n\n" + digest if items else digest
        args.markdown_output.write_text(rendered + "\n")
    if args.notify and items:
        from scripts.notify import send
        notification_items = items[:15]
        notification = render_digest(notification_items)
        if len(items) > len(notification_items):
            notification += f"\n- …and {len(items) - len(notification_items)} more on BountyBoard"
        send(f"BountyBoard: {len(items)} approaching deadlines", notification, level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
