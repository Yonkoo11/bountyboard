"""Annotate scout leads with deterministic availability and research reasons."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_DIR))

from scripts.generate_site import availability_state, candidate_deadline

CANDIDATES_FILE = REPO_DIR / "data" / "scout_candidates.json"
PROFILE_FILE = REPO_DIR / "data" / "user_profile.json"


def triage(item: dict, profile: dict) -> dict:
    normalized = dict(item)
    opportunity = {
        "name": item.get("name") or item.get("title"),
        "angle": item.get("description") or item.get("summary") or "",
        "eligibility": item.get("eligibility") or "",
        "format": item.get("format") or "",
        "location": item.get("location") or "",
    }
    availability = availability_state(opportunity)
    reasons: list[str] = []
    if not candidate_deadline(item):
        reasons.append("deadline")
    if not item.get("eligibility"):
        reasons.append("eligibility")
    if availability == "unknown":
        reasons.append("participation format")
    if not item.get("url"):
        reasons.append("source link")
    if profile.get("remote_only") and availability == "unavailable":
        reasons.append("in-person only")
    normalized["availability_state"] = availability
    normalized["research_reasons"] = reasons
    normalized.setdefault("review_status", "pending")
    normalized.setdefault("reviewed_at", None)
    normalized["profile_match"] = (
        "no" if "in-person only" in reasons
        else "conditional" if availability in ("conditional", "unknown")
        else "yes"
    )
    return normalized


def main() -> None:
    candidates = json.loads(CANDIDATES_FILE.read_text())
    profile = json.loads(PROFILE_FILE.read_text())
    triaged = [triage(item, profile) for item in candidates]
    CANDIDATES_FILE.write_text(json.dumps(triaged, indent=2, ensure_ascii=True) + "\n")
    counts: dict[str, int] = {}
    for item in triaged:
        key = item["profile_match"]
        counts[key] = counts.get(key, 0) + 1
    print(f"Triaged {len(triaged)} candidates: {counts}")


if __name__ == "__main__":
    main()
