# BountyBoard

BountyBoard is a broad opportunity radar for hackathons, grants, accelerators,
bounties, and ecosystem programs.

Its operating principle is simple:

> You cannot apply for an opportunity you never discover.

The system therefore keeps incomplete leads visible while making evidence quality
explicit. A missing deadline or source becomes a research task, not a reason to
silently discard the lead.

Live dashboard: https://yonkoo11.github.io/bountyboard/

## What the dashboard means

- **Verified:** source, current availability, and key facts were checked recently.
- **Partially verified:** at least one important fact still needs confirmation.
- **Unverified lead:** discovered by a scout but not yet confirmed.
- **Needs re-check:** prior evidence is more than 30 days old.
- **Actionability:** urgency, reported value, fit, completeness, and evidence—not
  a guarantee of earnings.
- **Reported pools:** advertised opportunity values. They are not expected income
  or necessarily the amount one participant can win.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/seed_db.py
python3 scripts/generate_site.py
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000`.

## Common commands

```bash
python3 scripts/scout.py --dry-run
python3 scripts/scout.py
python3 scripts/verify_data.py --dry-run --check-urls
python3 roster.py review
python3 -m unittest discover -s tests -v
```

## Architecture

- `scripts/scout.py` discovers opportunities from multiple sources.
- `data/scout_candidates.json` retains lower-confidence leads.
- `data/opportunities.json` is the portable committed dataset.
- `db.py` provides the local SQLite data layer.
- `opportunity_quality.py` owns verification, completeness, and ranking rules.
- `scripts/generate_site.py` renders the static GitHub Pages site.
- `docs/` contains the deployable frontend.

## Data policy

Broad coverage and truthful uncertainty are both required:

1. Keep plausible leads on the radar.
2. Never label inferred facts as verified.
3. Preserve the original source URL.
4. Re-check verified entries at least every 30 days.
5. Separate total prize pools, individual awards, grants, investments, credits,
   and mentorship.
6. Never interpret the sum of advertised pools as expected earnings.
