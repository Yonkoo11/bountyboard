"""
exa_competitor_watch.py — Monitor competitive landscape for Tier 1 ideas.

Runs 7 targeted Exa queries (one per Tier 1 idea) to catch:
- Competitor funding rounds
- New product launches in the same space
- API/regulation changes that affect viability
- Market shifts (acquisitions, shutdowns)

Cost: ~$0.07/run (7 queries x $0.01 each). Run weekly = $0.28/month.

Usage:
    python scripts/exa_competitor_watch.py            # normal run
    python scripts/exa_competitor_watch.py --dry-run  # preview, no alerts
"""

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
LOGS_DIR = REPO_DIR / "logs"
DATA_DIR = REPO_DIR / "data"
WATCH_LOG = DATA_DIR / "competitor_watch.jsonl"
TODAY_ISO = date.today().isoformat()

sys.path.insert(0, str(REPO_DIR))

from scripts.cost_monitor import BudgetExceeded, agentcash_fetch
from scripts.notify import send as notify

# ── Logging ──────────────────────────────────────────────────────────────────

LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / f"competitor_watch_{TODAY_ISO}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("competitor_watch")

# ── Tier 1 Ideas and their competitive queries ──────────────────────────────

TIER1_WATCHES = [
    {
        "id": 1,
        "name": "Rental scam verification",
        "query": "rental scam verification property ownership lookup landlord verification tool",
        "competitors": ["RentSafe", "Naborly", "Certn"],
    },
    {
        "id": 2,
        "name": "Stateful fuzz coach",
        "query": "smart contract fuzzing tool stateful testing Echidna Medusa new launch 2026",
        "competitors": ["Trail of Bits", "Certora", "Diligence Fuzzing"],
    },
    {
        "id": 3,
        "name": "LP tax calculator",
        "query": "LP tax cost basis Uniswap V3 concentrated liquidity tax reporting IRS crypto",
        "competitors": ["CoinTracker", "Koinly", "TaxBit", "TokenTax"],
    },
    {
        "id": 4,
        "name": "MCP/x402 reliability oracle",
        "query": "x402 protocol reliability monitoring MCP server uptime agent payments",
        "competitors": ["x402station", "MoonPay Agents", "Stripe Tempo MPP"],
    },
    {
        "id": 5,
        "name": "DeFi parameter simulation",
        "query": "DeFi risk parameter simulation lending protocol stress test Gauntlet Chaos Labs",
        "competitors": ["Gauntlet", "Chaos Labs", "Risk DAO"],
    },
    {
        "id": 6,
        "name": "Smart account security tooling",
        "query": "ERC-4337 EIP-7702 smart account security audit vulnerability tool",
        "competitors": ["Trail of Bits", "OpenZeppelin", "Alchemy"],
    },
    {
        "id": 7,
        "name": "Agent-speed test runner",
        "query": "AI agent test execution speed incremental testing API developer tools 2026",
        "competitors": ["Trunk", "Depot", "Namespace", "Nx"],
    },
]

EXA_URL = "https://stableenrich.dev/api/exa/search"

# Only search last 14 days to catch recent moves
LOOKBACK_DAYS = 14


def _log_finding(idea_id: int, idea_name: str, title: str, url: str, summary: str):
    """Append finding to JSONL log."""
    DATA_DIR.mkdir(exist_ok=True)
    entry = {
        "date": TODAY_ISO,
        "idea_id": idea_id,
        "idea_name": idea_name,
        "title": title,
        "url": url,
        "summary": summary[:500],
    }
    with open(WATCH_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


SIGNAL_WORDS = ["raised", "funding", "series", "launch", "acquired", "shut down", "sunset", "deprecated", "pivot", "shutdown"]


def _load_seen_urls() -> set[str]:
    """Load URLs from existing log for cross-run dedup."""
    seen = set()
    if WATCH_LOG.exists():
        for line in WATCH_LOG.read_text().splitlines():
            if line.strip():
                try:
                    entry = json.loads(line)
                    url = entry.get("url", "")
                    if url:
                        seen.add(url)
                except json.JSONDecodeError:
                    continue
    return seen


def run(dry_run: bool = False) -> int:
    """Run competitor watch. Returns count of relevant findings."""
    start_date = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    all_findings: list[dict] = []
    seen_urls = _load_seen_urls()
    log.info(f"Loaded {len(seen_urls)} previously seen URLs for dedup")

    for watch in TIER1_WATCHES:
        body = json.dumps({
            "query": watch["query"],
            "numResults": 5,
            "startPublishedDate": start_date,
            "contents": {
                "summary": {
                    "query": f"Is this about {watch['name']} or competitors: {', '.join(watch['competitors'])}? Extract: company name, what happened, funding amount if any, launch date"
                },
            },
        })

        try:
            data = agentcash_fetch(EXA_URL, body=body, estimated_cost=0.01)
        except BudgetExceeded as e:
            log.warning(f"Budget exceeded, stopping: {e}")
            break
        except Exception as e:
            log.warning(f"Query failed for #{watch['id']} {watch['name']}: {e}")
            continue

        items = data.get("data", {}).get("results", [])
        cost = data.get("data", {}).get("costDollars", {}).get("total", 0)
        log.info(f"#{watch['id']} {watch['name']}: {len(items)} results (${cost:.3f})")

        for item in items:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            summary = item.get("summary", "") or ""
            if not title or not url:
                continue

            # Cross-run dedup
            if url in seen_urls:
                continue
            seen_urls.add(url)

            text = (title + " " + summary).lower()
            relevant = any(c.lower() in text for c in watch["competitors"])
            has_signal = any(w in text for w in SIGNAL_WORDS)

            if relevant or has_signal:
                finding = {
                    "idea_id": watch["id"],
                    "idea_name": watch["name"],
                    "title": title,
                    "url": url,
                    "summary": summary[:300],
                }
                all_findings.append(finding)

                if not dry_run:
                    _log_finding(watch["id"], watch["name"], title, url, summary)

    log.info(f"Total relevant findings: {len(all_findings)}")

    if not all_findings:
        log.info("No competitive landscape changes detected.")
        return 0

    if dry_run:
        for f in all_findings:
            log.info(f"  [DRY] #{f['idea_id']} {f['idea_name']}: {f['title']}")
        return len(all_findings)

    # Telegram alert
    lines = []
    for f in all_findings[:8]:
        lines.append(f"  #{f['idea_id']} {f['idea_name']}: {f['title'][:60]}")
    body = "\n".join(lines)
    if len(all_findings) > 8:
        body += f"\n  ... and {len(all_findings) - 8} more"

    notify(
        f"Competitor Watch: {len(all_findings)} signals",
        body,
        level="info",
    )

    return len(all_findings)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    count = run(dry_run=dry_run)
    print(f"Done. {count} findings {'(dry run)' if dry_run else 'logged'}.")
