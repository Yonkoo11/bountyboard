"""
weekly_digest.py — Aggregate twitter_watch + exa_competitor_watch into a weekly briefing.

Reads JSONL logs from the past 7 days, ranks by relevance, and sends
a single Telegram digest. Designed to run after scout_pipeline.sh completes.

Usage:
    python scripts/weekly_digest.py            # send digest
    python scripts/weekly_digest.py --dry-run  # print to stdout only
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
DATA_DIR = REPO_DIR / "data"
TWITTER_LOG = DATA_DIR / "twitter_watch.jsonl"
COMPETITOR_LOG = DATA_DIR / "competitor_watch.jsonl"

sys.path.insert(0, str(REPO_DIR))

LOOKBACK_DAYS = 7


def _read_jsonl(path: Path, since: str) -> list[dict]:
    """Read JSONL entries from the past N days."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("date", "") >= since:
                entries.append(entry)
        except json.JSONDecodeError:
            continue
    return entries


def build_digest(dry_run: bool = False) -> str:
    """Build and optionally send weekly digest."""
    since = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

    tweets = _read_jsonl(TWITTER_LOG, since)
    findings = _read_jsonl(COMPETITOR_LOG, since)

    if not tweets and not findings:
        return "No intelligence gathered this week."

    sections = []

    # Twitter: group by mode, rank by engagement
    if tweets:
        by_mode: dict[str, list[dict]] = {}
        for t in tweets:
            mode = t.get("mode", "unknown")
            by_mode.setdefault(mode, []).append(t)

        sections.append(f"TWITTER ({len(tweets)} tweets)")
        for mode, mode_tweets in by_mode.items():
            ranked = sorted(mode_tweets, key=lambda t: t.get("likes", 0), reverse=True)
            sections.append(f"\n  {mode} ({len(mode_tweets)}):")
            for t in ranked[:3]:
                sections.append(
                    f"    @{t.get('author', '?')} ({t.get('likes', 0)}L): "
                    f"{t.get('text', '')[:80]}"
                )

    # Exa competitor findings
    if findings:
        sections.append(f"\nEXA COMPETITOR ({len(findings)} findings)")
        by_idea: dict[int, list[dict]] = {}
        for f in findings:
            by_idea.setdefault(f.get("idea_id", 0), []).append(f)

        for idea_id, idea_findings in sorted(by_idea.items()):
            name = idea_findings[0].get("idea_name", "?")
            sections.append(f"\n  #{idea_id} {name}:")
            for f in idea_findings[:3]:
                sections.append(f"    {f.get('title', '?')[:70]}")

    digest = "\n".join(sections)

    if dry_run:
        print(digest)
        return digest

    from scripts.notify import send as notify
    notify(
        f"Weekly Intel: {len(tweets)}T + {len(findings)}E",
        digest,
        level="info",
    )

    return digest


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    digest = build_digest(dry_run=dry_run)
    if not dry_run:
        print(f"Digest sent ({len(digest)} chars).")
