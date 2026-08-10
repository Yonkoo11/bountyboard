"""Review and track scout candidates without editing JSON by hand."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
CANDIDATES_FILE = REPO_DIR / "data" / "scout_candidates.json"
REVIEW_STATES = {"pending", "accepted", "rejected", "snoozed"}
APPLICATION_STATES = {"unknown", "open", "preparing", "applied", "finalist", "won", "lost", "withdrawn"}


def load_candidates(path: Path = CANDIDATES_FILE) -> list[dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError("candidate file must contain a JSON array")
    return data


def find_candidate(candidates: list[dict], identity: str) -> dict:
    matches = [item for item in candidates if identity in {
        str(item.get("candidate_id") or ""), str(item.get("url") or ""), str(item.get("name") or "")
    }]
    if not matches:
        raise ValueError(f"candidate not found: {identity}")
    if len(matches) > 1:
        raise ValueError(f"candidate identity is ambiguous: {identity}")
    return matches[0]


def update_candidate(item: dict, *, review_status: str | None = None,
                     application_status: str | None = None, note: str | None = None,
                     now: datetime | None = None) -> dict:
    updated = dict(item)
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    if review_status:
        if review_status not in REVIEW_STATES:
            raise ValueError(f"invalid review status: {review_status}")
        updated["review_status"] = review_status
        updated["reviewed_at"] = timestamp
    if application_status:
        if application_status not in APPLICATION_STATES:
            raise ValueError(f"invalid application status: {application_status}")
        if application_status not in {"unknown", "open"} and updated.get("review_status") != "accepted":
            raise ValueError("accept a candidate before advancing its application")
        updated["application_status"] = application_status
        updated["application_updated_at"] = timestamp
    if note is not None:
        updated["decision_note"] = note.strip()
    return updated


def queue_key(item: dict) -> tuple:
    deadline = str(item.get("deadline") or "9999-12-31")
    available = 0 if item.get("profile_match") == "yes" else 1
    fit = -int(item.get("theme_fit") or 0)
    prize = -int(item.get("prize_usd") or 0)
    return available, deadline, fit, prize, str(item.get("name") or "")


def save_candidates(candidates: list[dict], path: Path = CANDIDATES_FILE) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(candidates, indent=2, ensure_ascii=True) + "\n")
    temporary.replace(path)


def print_queue(candidates: list[dict], limit: int) -> None:
    pending = sorted((item for item in candidates if item.get("review_status", "pending") == "pending"), key=queue_key)
    for item in pending[:limit]:
        print("\t".join([
            str(item.get("candidate_id") or "missing-id"),
            str(item.get("profile_match") or "conditional"),
            str(item.get("deadline") or "deadline-unknown"),
            f"fit={int(item.get('theme_fit') or 0)}",
            str(item.get("name") or "Unnamed lead"),
        ]))
    print(f"Showing {min(limit, len(pending))} of {len(pending)} pending leads")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("queue")
    listing.add_argument("--limit", type=int, default=20)
    update = sub.add_parser("update")
    update.add_argument("identity", help="candidate ID, exact URL, or exact name")
    update.add_argument("--review", choices=sorted(REVIEW_STATES))
    update.add_argument("--application", choices=sorted(APPLICATION_STATES))
    update.add_argument("--note")
    args = parser.parse_args()

    candidates = load_candidates()
    if args.command == "queue":
        print_queue(candidates, max(1, args.limit))
        return 0
    if not any((args.review, args.application, args.note is not None)):
        parser.error("update requires --review, --application, or --note")
    try:
        candidate = find_candidate(candidates, args.identity)
        changed = update_candidate(candidate, review_status=args.review,
                                   application_status=args.application, note=args.note)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    candidates[candidates.index(candidate)] = changed
    save_candidates(candidates)
    print(f"Updated {changed.get('candidate_id')}: review={changed.get('review_status')} application={changed.get('application_status')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
