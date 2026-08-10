"""Decision-quality rules shared by the CLI, scout, tests, and website.

BountyBoard is intentionally broad: incomplete leads stay visible. These helpers
make uncertainty explicit so a lead is never mistaken for a verified opportunity.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

VERIFICATION_STATES = ("verified", "partially_verified", "unverified", "stale")
APPLICATION_STATES = ("open", "rolling", "upcoming", "unknown", "closed")
AWARD_TYPES = ("cash_prize", "grant", "investment", "bounty", "credits", "mentorship", "unknown")


def is_safe_url(value: Any) -> bool:
    """Return true only for absolute HTTP(S) URLs."""
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def days_until(value: str | None, *, today: date | None = None) -> int | None:
    """Return days to a known deadline; unknown and invalid dates return None."""
    parsed = parse_date(value)
    if parsed is None:
        return None
    return (parsed - (today or date.today())).days


def verification_age_days(opportunity: dict[str, Any], *, today: date | None = None) -> int | None:
    state = opportunity.get("verification_status") or "unverified"
    if state == "verified":
        checked = parse_date(opportunity.get("verified_at"))
    else:
        checked = parse_date(opportunity.get("last_checked_at") or opportunity.get("verified_at"))
    if checked is None:
        return None
    return ((today or date.today()) - checked).days


def effective_verification(opportunity: dict[str, Any], *, today: date | None = None) -> str:
    """Return verification state, automatically aging old evidence to stale."""
    configured = opportunity.get("verification_status") or "unverified"
    age = verification_age_days(opportunity, today=today)
    if configured in ("verified", "partially_verified") and (age is None or age > 30):
        return "stale"
    return configured if configured in VERIFICATION_STATES else "unverified"


def application_state(opportunity: dict[str, Any], *, today: date | None = None) -> str:
    configured = opportunity.get("application_status") or "unknown"
    days = days_until(opportunity.get("deadline"), today=today)
    if days is not None and days < 0:
        return "closed"
    if configured == "closed":
        return "closed"
    if days is not None and configured == "unknown":
        return "open"
    return configured if configured in APPLICATION_STATES else "unknown"


def completeness(opportunity: dict[str, Any]) -> int:
    """Percentage of decision-critical fields present."""
    checks = (
        bool(opportunity.get("name")),
        is_safe_url(opportunity.get("url")),
        bool(opportunity.get("deadline")) or opportunity.get("application_status") == "rolling",
        bool(opportunity.get("prize_usd") or opportunity.get("prize_note")),
        bool(opportunity.get("tracks")),
        bool(opportunity.get("eligibility")),
        bool(opportunity.get("source")),
        bool(opportunity.get("last_checked_at") or opportunity.get("verified_at")),
    )
    return round(sum(checks) / len(checks) * 100)


def actionability_score(opportunity: dict[str, Any], *, today: date | None = None) -> int:
    """Score 0-100 for what deserves attention next, without hiding broad leads."""
    state = application_state(opportunity, today=today)
    if state == "closed" or opportunity.get("status") in ("closed", "rejected"):
        return 0

    score = 0
    days = days_until(opportunity.get("deadline"), today=today)
    if days is not None:
        if days <= 3:
            score += 30
        elif days <= 7:
            score += 26
        elif days <= 14:
            score += 21
        elif days <= 30:
            score += 15
        elif days <= 60:
            score += 9
        else:
            score += 4
    elif state == "rolling":
        score += 8

    prize = opportunity.get("max_award_usd") or opportunity.get("prize_usd") or 0
    if prize >= 100_000:
        score += 18
    elif prize >= 50_000:
        score += 15
    elif prize >= 20_000:
        score += 11
    elif prize >= 5_000:
        score += 7
    elif prize > 0:
        score += 3

    score += min(int((opportunity.get("theme_fit") or 0) * 2), 20)
    score += {
        "verified": 15,
        "partially_verified": 9,
        "unverified": 2,
        "stale": 0,
    }[effective_verification(opportunity, today=today)]
    score += round(completeness(opportunity) * 0.12)

    if not is_safe_url(opportunity.get("url")):
        score -= 12
    if state == "unknown":
        score -= 6
    return max(0, min(score, 100))


def expected_value(opportunity: dict[str, Any]) -> int | None:
    """Expected cash value when an individual award and win estimate are known."""
    award = opportunity.get("max_award_usd")
    probability = opportunity.get("win_probability")
    if award is None or probability is None:
        return None
    try:
        return round(float(award) * float(probability))
    except (TypeError, ValueError):
        return None


def missing_details(opportunity: dict[str, Any]) -> list[str]:
    missing = []
    if not is_safe_url(opportunity.get("url")):
        missing.append("source link")
    if not opportunity.get("deadline") and opportunity.get("application_status") != "rolling":
        missing.append("deadline")
    if not opportunity.get("eligibility"):
        missing.append("eligibility")
    if not opportunity.get("last_checked_at") and not opportunity.get("verified_at"):
        missing.append("freshness check")
    return missing
