"""Annotate scout leads with deterministic availability and research reasons."""

from __future__ import annotations

import json
import hashlib
import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_DIR))

from scripts.generate_site import availability_state, candidate_deadline

CANDIDATES_FILE = REPO_DIR / "data" / "scout_candidates.json"
PROFILE_FILE = REPO_DIR / "data" / "user_profile.json"


def profile_unknowns(item: dict, profile: dict) -> list[str]:
    """Return personal facts needed before claiming this lead is eligible."""
    text = " ".join(str(item.get(field) or "") for field in
                    ("name", "title", "description", "summary", "eligibility", "format", "location")).lower()
    unknowns: list[str] = []
    student_restricted = bool(re.search(
        r"\b(?:students? only|university students?|college students?|high school|students? ages?|student hackathon)\b",
        text,
    )) or str(item.get("eligibility") or "").lower().startswith("students")
    if student_restricted \
            and profile.get("student_status") in (None, "", "unknown"):
        unknowns.append("student status")
    if any(term in text for term in ("resident", "residency", "citizen", "country", "countries", "region", "apac", "emea")) \
            and profile.get("country") in (None, "", "unknown"):
        unknowns.append("country/residency")
    if re.search(r"\b(?:age[sd]?|under|over|13\+|16\+|18\+)\b", text) \
            and profile.get("age_band") in (None, "", "unknown"):
        unknowns.append("age")
    if any(term in text for term in ("team of", "team size", "teams of", "individuals or teams")):
        unknowns.append("team requirements")
    return unknowns


def triage(item: dict, profile: dict) -> dict:
    normalized = dict(item)
    if item.get("source") == "lablab" and "##" in str(item.get("description") or ""):
        description = str(item["description"]).split("##", 1)[1].strip()
        title = str(item.get("name") or "")
        if description.startswith(title):
            description = description[len(title):].strip()
        normalized["description"] = re.sub(r"\s+", " ", description)
    identity = str(item.get("url") or item.get("name") or item.get("title") or "unknown")
    normalized.setdefault("candidate_id", f"lead-{hashlib.sha256(identity.encode()).hexdigest()[:12]}")
    opportunity = {
        "name": item.get("name") or item.get("title"),
        "angle": normalized.get("description") or item.get("summary") or "",
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
    reasons.extend(profile_unknowns(normalized, profile))
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
    normalized.setdefault("decision_note", "")
    normalized["profile_match"] = (
        "no" if "in-person only" in reasons
        else "conditional" if availability in ("conditional", "unknown") or profile_unknowns(normalized, profile)
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
