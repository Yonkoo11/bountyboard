<div align="center">

# BountyBoard

[![refresh](https://github.com/Yonkoo11/bountyboard/actions/workflows/daily-refresh.yml/badge.svg)](https://github.com/Yonkoo11/bountyboard/actions/workflows/daily-refresh.yml)
[![quality](https://github.com/Yonkoo11/bountyboard/actions/workflows/quality.yml/badge.svg)](https://github.com/Yonkoo11/bountyboard/actions/workflows/quality.yml)
[![live](https://img.shields.io/badge/live-yonkoo11.github.io%2Fbountyboard-3fb950)](https://yonkoo11.github.io/bountyboard/)

</div>

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
- **Actionability:** urgency, reported value, fit, completeness, and evidence, not
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

## Verify it yourself in 20 seconds

No API keys, no accounts. This rebuilds the public page from the committed data
and runs the test suite. Every expected output below was copied from a run on a
fresh clone on 2026-09-24; the seed counts change as the data changes.

```bash
git clone https://github.com/Yonkoo11/bountyboard && cd bountyboard
python3 -m venv .venv && . .venv/bin/activate
pip install -q -r requirements.txt
python3 -m unittest discover -s tests   # -> Ran 63 tests ... OK
python3 scripts/seed_db.py              # -> Seeded 53 entries: {'active': 3, 'closed': 41, 'needs_review': 6, 'rejected': 2, 'submitted': 1}
python3 scripts/validate_profile.py     # -> Profile valid. Unconfirmed fields: country, student_status, age_band
python3 scripts/generate_site.py        # -> Generated .../docs/index.html (291,060 bytes)
```

This proves the page builds from the data in the repo and that the ranking,
escaping, deadline and freshness rules behave as the tests describe. It does
not prove any listed opportunity is still open: that is what the evidence
labels on each card are for.

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

## What's real, and what we deliberately did not claim

| Capability | Status |
|---|---|
| **Broad discovery** | Real. The 2026-09-24 build lists 137 leads on the radar, 136 with a source link, 52 with a known deadline, 43 archived. |
| **Verification** | Measured negative. 0 of those 137 leads are currently marked verified; all 137 need research. Discovery is running, verification is not keeping up. |
| **Scheduled refresh** | Measured negative. Every scheduled refresh from at least 2026-09-13 to 2026-09-23 failed on two date-dependent tests, so the live page went about 22 days without updating. Fixed 2026-09-24; the refresh badge above is the live status. |
| **Reported pools** | Advertised totals only ($2317K in that build). Not expected earnings, not what one person can win. |
| **Freshness alarm** | Real. An hourly workflow fails when the last successful refresh is more than 8 hours old. It is how the outage above was noticed. |
| Eligibility for any specific person | Not claimed. The profile has unconfirmed fields (country, student status, age band). |

## Project layout

```
scripts/
  scout.py              # discovers leads from multiple sources
  seed_db.py            # loads committed JSON into the local SQLite DB
  generate_site.py      # renders docs/index.html
  verify_data.py        # checks stored entries and source URLs
  check_freshness.py    # fails when the last refresh is too old
  deadline_digest.py    # daily deadline alerts
opportunity_quality.py  # verification, completeness and ranking rules
db.py                   # SQLite data layer
data/
  opportunities.json    # curated, committed dataset
  scout_candidates.json # lower-confidence leads kept on the radar
docs/                   # the published site (GitHub Pages)
tests/                  # 63 unit tests, run on every refresh and push
.github/workflows/      # 4-hourly refresh, hourly freshness watch, deadline alerts, quality
```
