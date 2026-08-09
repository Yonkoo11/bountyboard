"""Generate the public BountyBoard radar from the local opportunity database.

The radar is broad by design: verified opportunities, incomplete leads, and scout
candidates are all included. The interface distinguishes evidence quality instead
of hiding uncertain leads.
"""

from __future__ import annotations

import html
import hashlib
import json
import re
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

REPO_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_DIR))

import db
from opportunity_quality import (
    actionability_score,
    application_state,
    completeness,
    days_until,
    effective_verification,
    expected_value,
    is_safe_url,
    missing_details,
)

DOCS_DIR = REPO_DIR / "docs"
CANDIDATES_FILE = REPO_DIR / "data" / "scout_candidates.json"


def escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def compact_text(value: Any) -> str:
    """Collapse scraped Markdown/newlines into safe, readable plain text."""
    return " ".join(str(value or "").split())


def safe_url(value: Any) -> str:
    """Allow only absolute HTTP(S) links from discovered external data."""
    candidate = str(value or "").strip()
    return candidate if is_safe_url(candidate) else ""


def candidate_deadline(item: dict[str, Any]) -> str | None:
    """Use an explicit field first, then conservatively parse a labeled date."""
    if item.get("deadline"):
        return item["deadline"]
    text = compact_text(item.get("description") or item.get("summary"))
    match = re.search(
        r"(?:deadline(?: date)?|submissions? (?:close|end))\**\s*:\**\s*"
        r"([A-Z][a-z]+ \d{1,2},? \d{4})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(match.group(1), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def load_candidates() -> list[dict[str, Any]]:
    if not CANDIDATES_FILE.exists():
        return []
    try:
        raw = json.loads(CANDIDATES_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    candidates = []
    for index, item in enumerate(raw):
        name = item.get("name") or item.get("title")
        if not name:
            continue
        verification_status = item.get("verification_status") or "unverified"
        last_checked_at = item.get("last_checked_at") or item.get("scout_date")
        candidates.append({
            "id": f"radar-{index}-{name[:24]}",
            "name": name,
            "category": item.get("category") or "hackathon",
            "deadline": candidate_deadline(item),
            "prize_usd": item.get("prize_usd") or 0,
            "prize_note": item.get("prize_note") or "",
            "theme_fit": item.get("theme_fit") or item.get("score") or 0,
            "status": "radar",
            "tracks": item.get("tracks") or [],
            "angle": item.get("description") or item.get("summary") or "",
            "url": safe_url(item.get("url")),
            "source": item.get("source") or "scout",
            "verification_status": verification_status,
            "verified_at": item.get("verified_at") or (last_checked_at if verification_status == "verified" else None),
            "application_status": item.get("application_status") or "unknown",
            "review_status": item.get("review_status") or "pending",
            "last_checked_at": last_checked_at,
            "award_type": item.get("award_type") or "unknown",
            "eligibility": item.get("eligibility") or "",
            "format": item.get("format") or "",
            "availability_state": item.get("availability_state") or "",
            "research_reasons": item.get("research_reasons") or [],
            "profile_match": item.get("profile_match") or "conditional",
        })
    return candidates


def deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove exact source/name duplicates while retaining distinct rounds."""
    seen_urls: set[str] = set()
    seen_names: set[tuple[str, str | None]] = set()
    unique = []
    for item in items:
        url = safe_url(item.get("url")).lower().rstrip("/")
        name_key = (compact_text(item.get("name")).lower(), item.get("deadline"))
        if url and url in seen_urls:
            continue
        if name_key in seen_names:
            continue
        if url:
            seen_urls.add(url)
        seen_names.add(name_key)
        unique.append(item)
    return unique


def availability_state(opportunity: dict[str, Any]) -> str:
    stored = opportunity.get("availability_state")
    if stored in {"available", "conditional", "unavailable", "unknown"}:
        return str(stored)
    text = " ".join(compact_text(opportunity.get(field, "")) for field in
                    ("name", "angle", "notes", "description", "eligibility", "format", "location")).lower()
    online = any(term in text for term in ("online", "virtual", "remote", "worldwide"))
    in_person = any(term in text for term in ("in-person", "in person", "on-site", "onsite", "offline", "irl hackathon"))
    mandatory = any(term in text for term in ("shortlisted teams travel", "in-person final", "in person final", "live final in", "culminating in a live demo day", "finale at"))
    optional = any(term in text for term in ("may be invited", "invited to attend", "by invitation only", "optional in-person", "optional in person", "travel opportunity", "invitation to"))
    restricted = any(term in text for term in ("students only", "student hackathon", "university students", "high school", "ages 13", "ages 14", "ages 15", "ages 16", "ages 17", "ages 18", "apac-focused", "residents of", "must reside", "team of 2", "teams of 2"))
    if mandatory or optional or (in_person and online):
        return "conditional"
    if in_person:
        return "unavailable"
    if restricted:
        return "conditional"
    if online:
        return "available"
    return "unknown"


def availability_label(state: str) -> str:
    return {"available": "Remote-compatible", "conditional": "Check restrictions", "unavailable": "In-person only", "unknown": "Format unknown"}[state]


def deadline_label(opportunity: dict[str, Any]) -> str:
    state = application_state(opportunity)
    days = days_until(opportunity.get("deadline"))
    if state == "closed":
        return "Closed"
    if days is None:
        return "Rolling" if state == "rolling" else "Deadline unknown"
    if days == 0:
        return "Due today"
    if days == 1:
        return "1 day left"
    if 1 < days <= 30:
        return f"{days} days left"
    try:
        return datetime.strptime(opportunity["deadline"], "%Y-%m-%d").strftime("%b %d, %Y")
    except (KeyError, ValueError):
        return "Deadline unknown"


def money_label(opportunity: dict[str, Any]) -> str:
    amount = opportunity.get("max_award_usd") or opportunity.get("prize_usd") or 0
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    if amount:
        return f"${amount:,}"
    return opportunity.get("prize_note") or "Amount unknown"


def verification_label(value: str) -> str:
    return {
        "verified": "Verified",
        "partially_verified": "Partially verified",
        "unverified": "Unverified lead",
        "stale": "Needs re-check",
    }.get(value, "Unverified lead")


def opportunity_row(opportunity: dict[str, Any], rank: int) -> str:
    verification = effective_verification(opportunity)
    state = application_state(opportunity)
    score = actionability_score(opportunity)
    quality = completeness(opportunity)
    missing = list(dict.fromkeys([*missing_details(opportunity), *(opportunity.get("research_reasons") or [])]))
    expected = expected_value(opportunity)
    tracks = opportunity.get("tracks") or []
    if isinstance(tracks, str):
        try:
            tracks = json.loads(tracks)
        except (json.JSONDecodeError, TypeError):
            tracks = []

    search_text = " ".join([
        str(opportunity.get("name", "")),
        str(opportunity.get("category", "")),
        str(opportunity.get("source", "")),
        compact_text(opportunity.get("angle", "")),
        " ".join(str(track) for track in tracks),
    ]).lower()
    tags = "".join(f'<span class="tag">{escape(track)}</span>' for track in tracks[:4])
    missing_html = ""
    if missing:
        missing_html = (
            '<p class="missing"><strong>Needs research:</strong> '
            + ", ".join(escape(item) for item in missing)
            + "</p>"
        )
    angle = compact_text(
        opportunity.get("angle") or opportunity.get("notes") or "No summary captured yet."
    )
    source = opportunity.get("source") or "manual"
    checked = opportunity.get("last_checked_at") or opportunity.get("verified_at") or "never"
    eligibility = opportunity.get("eligibility") or "Not confirmed"
    availability = availability_state(opportunity)
    review_status = opportunity.get("review_status") or (
        "accepted" if opportunity.get("status") == "active" else "pending"
    )
    application_status = opportunity.get("application_status") or "unknown"
    ev_html = f'<span>EV estimate <strong>${expected:,}</strong></span>' if expected is not None else ""
    details_link = ""
    source_url = safe_url(opportunity.get("url"))
    submission_url = safe_url(opportunity.get("submission_url"))
    if source_url:
        details_link = (
            f'<a class="button secondary" href="{escape(source_url)}" '
            'target="_blank" rel="noopener noreferrer">Open source <span aria-hidden="true">↗</span></a>'
        )
    else:
        details_link = '<span class="button disabled" aria-disabled="true">Source needed</span>'
    submit_link = ""
    if submission_url and state != "closed":
        submit_link = (
            f'<a class="button primary" href="{escape(submission_url)}" '
            'target="_blank" rel="noopener noreferrer">Apply <span aria-hidden="true">↗</span></a>'
        )

    return f"""
<article class="opportunity" data-search="{escape(search_text)}"
  data-category="{escape(opportunity.get("category") or "other")}"
  data-verification="{verification}" data-state="{state}" data-availability="{availability}"
  data-review="{escape(review_status)}" data-application="{escape(application_status)}"
  data-score="{score}" data-prize="{opportunity.get("max_award_usd") or opportunity.get("prize_usd") or 0}"
  data-deadline="{escape(opportunity.get("deadline") or "9999-12-31")}">
  <div class="rank" aria-label="Actionability rank {rank}">{rank:02d}</div>
  <div class="opportunity-main">
    <div class="eyebrow-row">
      <span class="status {verification}"><span aria-hidden="true"></span>{verification_label(verification)}</span>
      <span class="category">{escape(opportunity.get("category") or "other")}</span>
      <span class="source">via {escape(source)}</span>
      <span class="availability {availability}">{availability_label(availability)}</span>
      <span class="source">{escape(str(review_status).replace("_", " "))} · {escape(str(application_status).replace("_", " "))}</span>
    </div>
    <h3>{escape(opportunity.get("name"))}</h3>
    <p class="summary">{escape(angle[:260])}</p>
    <div class="tags">{tags}</div>
    {missing_html}
  </div>
  <dl class="opportunity-facts">
    <div><dt>Deadline</dt><dd>{escape(deadline_label(opportunity))}</dd></div>
    <div><dt>Opportunity value</dt><dd>{escape(money_label(opportunity))}</dd></div>
    <div><dt>Eligibility</dt><dd>{escape(eligibility)}</dd></div>
    <div><dt>Evidence</dt><dd>{quality}% complete · checked {escape(checked)}</dd></div>
  </dl>
  <div class="opportunity-score">
    <span class="score">{score}</span>
    <span>actionability</span>
    {ev_html}
  </div>
  <div class="opportunity-actions">{details_link}{submit_link}</div>
</article>"""


def generate() -> str:
    today = date.today()
    # Day-level precision keeps committed output reproducible during CI rebuilds.
    # The deployed HTML still gives visitors an honest maximum age for this refresh.
    generated_at = datetime.combine(today, time.min, tzinfo=timezone.utc)
    generated_iso = generated_at.isoformat().replace("+00:00", "Z")
    asset_version = hashlib.sha256((DOCS_DIR / "styles.css").read_bytes() + (DOCS_DIR / "app.js").read_bytes()).hexdigest()[:10]
    database_items = db.get_all()
    candidates = load_candidates()
    all_items = deduplicate(database_items + candidates)

    visible = [
        item for item in all_items
        if item.get("status") not in ("closed", "rejected") and application_state(item) != "closed"
    ]
    closed = [
        item for item in database_items
        if item.get("status") in ("closed", "rejected") or application_state(item) == "closed"
    ]
    visible.sort(key=lambda item: (-actionability_score(item), item.get("deadline") or "9999"))
    verified_count = sum(effective_verification(item) == "verified" for item in visible)
    research_count = sum(effective_verification(item) != "verified" for item in visible)
    linked_count = sum(bool(item.get("url")) for item in visible)
    known_deadlines = sum(days_until(item.get("deadline")) is not None for item in visible)
    total_pool = sum(item.get("prize_usd") or 0 for item in visible)

    rows = "".join(opportunity_row(item, index) for index, item in enumerate(visible, 1))
    if not rows:
        rows = """
<div class="empty-state">
  <h3>No opportunities match this view</h3>
  <p>Clear the filters to return to the full radar.</p>
  <button class="button secondary" id="clearEmpty">Clear filters</button>
</div>"""

    updated = today.strftime("%B %d, %Y")
    return f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A broad radar for hackathons, grants, accelerators, bounties, and builder opportunities.">
  <meta name="theme-color" content="#f5f2ea">
  <meta property="og:title" content="BountyBoard — Opportunity Radar">
  <meta property="og:description" content="Discover broadly. Verify quickly. Never miss a serious builder opportunity.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://yonkoo11.github.io/bountyboard/">
  <link rel="canonical" href="https://yonkoo11.github.io/bountyboard/">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="styles.css?v={asset_version}">
  <title>BountyBoard — Opportunity Radar</title>
  <script>
    try {{
      const saved = localStorage.getItem("bb-theme");
      if (saved) document.documentElement.dataset.theme = saved;
    }} catch (_) {{}}
  </script>
</head>
<body>
  <a class="skip-link" href="#opportunities">Skip to opportunities</a>
  <header class="site-header">
    <a class="brand" href="./" aria-label="BountyBoard home"><strong>BOUNTYBOARD</strong></a>
    <div class="header-actions">
      <span class="updated">Last successful refresh <time id="refreshTime" datetime="{generated_iso}">{updated}</time></span>
      <button class="icon-button" id="themeToggle" type="button" aria-label="Switch to dark theme" aria-pressed="false">
        <span aria-hidden="true">◐</span>
      </button>
    </div>
  </header>

  <main>
    <section class="intro" aria-labelledby="hero-title">
      <div>
        <p class="kicker">Opportunity radar</p>
        <h1 id="hero-title">See the opportunity before it passes.</h1>
        <p>BountyBoard keeps every credible lead on the radar, then shows what is verified, what needs research, and what deserves action now.</p>
      </div>
      <div class="freshness current" id="freshnessStatus" role="status" data-generated-at="{generated_iso}">
        <span class="freshness-dot" aria-hidden="true"></span>
        <span><strong id="freshnessLabel">Updated today</strong><small id="freshnessDetail">Page generated {updated}; individual sources have their own check dates.</small></span>
      </div>
    </section>

    <section class="metrics" aria-label="Opportunity summary">
      <div><strong>{len(visible)}</strong><span>on radar</span></div>
      <div><strong>{verified_count}</strong><span>verified</span></div>
      <div><strong>{research_count}</strong><span>need research</span></div>
      <div><strong>{known_deadlines}</strong><span>known deadlines</span></div>
      <div><strong>${total_pool / 1000:.0f}K</strong><span>reported pools <em>not expected earnings</em></span></div>
      <div><strong>{len(closed)}</strong><span>archived</span></div>
    </section>

    <section class="workspace" id="opportunities" aria-labelledby="opportunities-title">
      <div class="section-heading">
        <div>
          <p class="kicker">Full radar</p>
          <h2 id="opportunities-title">All possible opportunities</h2>
          <p>{linked_count} have source links. Verification changes confidence and ranking, not inclusion.</p>
        </div>
        <div class="result-count" aria-live="polite"><strong id="visibleCount">{len(visible)}</strong> shown</div>
      </div>

      <div class="toolbar" aria-label="Opportunity controls">
        <label class="search">
          <span class="sr-only">Search opportunities</span>
          <span aria-hidden="true">⌕</span>
          <input id="search" type="search" placeholder="Search names, tracks, sources…" autocomplete="off">
        </label>
        <label class="select-control">
          <span>Availability</span>
          <select id="availabilityFilter">
            <option value="for_me">For me</option>
            <option value="all">All opportunities</option>
            <option value="available">Remote-compatible</option>
            <option value="conditional">Check restrictions</option>
            <option value="unknown">Format unknown</option>
            <option value="unavailable">In-person only</option>
          </select>
        </label>
        <label class="select-control">
          <span>Type</span>
          <select id="categoryFilter">
            <option value="all">All types</option>
            <option value="hackathon">Hackathons</option>
            <option value="grant">Grants</option>
            <option value="accelerator">Accelerators</option>
            <option value="bounty">Bounties</option>
          </select>
        </label>
        <label class="select-control">
          <span>Evidence</span>
          <select id="verificationFilter">
            <option value="all">Any evidence</option>
            <option value="verified">Verified</option>
            <option value="partially_verified">Partial</option>
            <option value="unverified">Unverified</option>
            <option value="stale">Needs re-check</option>
          </select>
        </label>
        <label class="select-control">
          <span>Workflow</span>
          <select id="workflowFilter">
            <option value="all">Any stage</option>
            <option value="pending">Pending review</option>
            <option value="accepted">Accepted</option>
            <option value="pursuing">Pursuing</option>
            <option value="applied">Applied</option>
          </select>
        </label>
        <label class="select-control">
          <span>Sort</span>
          <select id="sort">
            <option value="score">Actionability</option>
            <option value="deadline">Deadline</option>
            <option value="prize">Reported value</option>
          </select>
        </label>
        <button class="button reset" id="clearFilters" type="button">Reset</button>
      </div>

      <div class="legend" aria-label="Evidence legend">
        <span><i class="dot verified"></i>Verified recently</span>
        <span><i class="dot partially_verified"></i>Some facts confirmed</span>
        <span><i class="dot unverified"></i>Lead awaiting research</span>
        <span><i class="dot stale"></i>Evidence older than 30 days</span>
      </div>

      <div class="opportunity-list" id="opportunityList">
        {rows}
      </div>
      <div class="empty-state" id="filterEmpty" hidden>
        <h3>No opportunities match these filters</h3>
        <p>The leads are still here. Reset filters to return to the full radar.</p>
        <button class="button secondary" id="clearEmpty" type="button">Reset filters</button>
      </div>
    </section>

    <aside class="method" aria-label="Freshness note"><strong>Discovery is not verification.</strong> Check each card's evidence date before investing time in an application.</aside>
  </main>

  <footer>
    <strong>BountyBoard</strong>
    <span>Built to make missed opportunities less likely.</span>
  </footer>
  <script src="app.js?v={asset_version}" defer></script>
</body>
</html>"""


def main() -> None:
    page = "\n".join(line.rstrip() for line in generate().splitlines()) + "\n"
    if "--dry-run" in sys.argv:
        print(page)
        return
    DOCS_DIR.mkdir(exist_ok=True)
    output = DOCS_DIR / "index.html"
    output.write_text(page)
    print(f"Generated {output} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
