#!/bin/bash
# scout_pipeline.sh — Full scout pipeline: discover → verify → generate site → push
#
# Called by launchd (com.bountyboard.scout) every Sunday 9AM.

set -euo pipefail

REPO="/Users/yonko/bountyboard"
PYTHON="/opt/homebrew/bin/python3"
cd "$REPO"

echo "=== Scout Pipeline $(date) ==="

# Step 0a: Watch Tier 1 idea competitive landscape (Exa)
echo "--- Competitor watch (Exa) ---"
$PYTHON scripts/exa_competitor_watch.py 2>&1 || echo "Competitor watch had errors (continuing)"

# Step 0b: Twitter/X intelligence (twit.sh)
echo "--- Twitter watch ---"
$PYTHON scripts/twitter_watch.py 2>&1 || echo "Twitter watch had errors (continuing)"

# Step 1: Scout for new opportunities
echo "--- Running scout ---"
$PYTHON scripts/scout.py 2>&1 || echo "Scout had errors (continuing)"

# Step 1b: Apply the confirmed personal profile without guessing unknown traits.
echo "--- Triaging personal eligibility ---"
$PYTHON scripts/triage_candidates.py 2>&1

# Step 2: Verify data quality, close expired + cross-check Exa results
echo "--- Verifying data ---"
$PYTHON scripts/verify_data.py --verify-exa 2>&1

# Step 2b: Fail loudly when source coverage is degraded. The site is still
# regenerated below so working sources are never hidden by one broken adapter.
echo "--- Checking discovery coverage ---"
GATE_FAILED=0
$PYTHON scripts/data_quality_gate.py 2>&1 || GATE_FAILED=1

# Step 3: Regenerate website
echo "--- Generating site ---"
$PYTHON scripts/generate_site.py 2>&1

# Step 4: Auto-commit and push if public data or operational evidence changed
if test -z "$(git status --porcelain -- docs/ data/opportunities.json data/scout_candidates.json data/source_health.json data/last_run.json)"; then
    echo "--- No site changes ---"
else
    echo "--- Pushing site update ---"
    git add docs/ data/opportunities.json data/scout_candidates.json data/source_health.json data/last_run.json
    git commit -m "auto: update site $(date +%Y-%m-%d)"
    git push origin main 2>&1 || echo "Push failed (will retry next run)"
fi

# Step 5: Weekly intelligence digest (aggregates Twitter + Exa findings)
echo "--- Weekly digest ---"
$PYTHON scripts/weekly_digest.py 2>&1 || echo "Digest had errors (continuing)"

echo "=== Pipeline complete ==="

if [ "$GATE_FAILED" -ne 0 ]; then
    echo "Discovery coverage was degraded"
    exit 1
fi
