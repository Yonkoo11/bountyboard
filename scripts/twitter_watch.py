"""
twitter_watch.py — Twitter/X intelligence for the ideas bank.

Three modes:
  1. Competitor watch: track what key voices say about Tier 1 competitive spaces
  2. Pain point discovery: find real user complaints in target markets
  3. Signal detection: catch funding announcements, product launches, shutdowns

Uses twit.sh via agentcash (x402 micropayments on Base).
Cost: $0.01 per search query. Budget-gated via cost_monitor.

Usage:
    python scripts/twitter_watch.py                    # run all modes
    python scripts/twitter_watch.py --mode competitors # competitors only
    python scripts/twitter_watch.py --mode pain        # pain points only
    python scripts/twitter_watch.py --mode signals     # signals only
    python scripts/twitter_watch.py --mode voices      # key voices only
    python scripts/twitter_watch.py --dry-run          # preview queries, no API calls
"""

import fcntl
import json
import logging
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

REPO_DIR = Path(__file__).parent.parent
LOGS_DIR = REPO_DIR / "logs"
DATA_DIR = REPO_DIR / "data"
TWITTER_LOG = DATA_DIR / "twitter_watch.jsonl"
TODAY_ISO = date.today().isoformat()

sys.path.insert(0, str(REPO_DIR))

from config import AGENTCASH_BIN
from scripts.cost_monitor import _append_spend_log, check_budget

# ── Logging ──────────────────────────────────────────────────────────────────

LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / f"twitter_watch_{TODAY_ISO}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("twitter_watch")

TWIT_BASE = "https://twit.sh"
TWIT_COST_PER_QUERY = 0.01

# Noise filter: exclude these from ALL queries to cut bots, conspiracy, promo
GLOBAL_EXCLUDE = "airdrop giveaway whitelist presale moon 100x shill memecoin maga conspiracy qanon"

# ── Query Definitions ────────────────────────────────────────────────────────

# Mode 1: Competitor tracking (specific product/tool names in Tier 1 spaces)
COMPETITOR_QUERIES = [
    {
        "idea_id": 1,
        "name": "Rental scam verification",
        "params": {"anyWords": "landlord verification property records scam check", "words": "rental", "noneWords": GLOBAL_EXCLUDE, "minLikes": "3", "max_results": "10"},
    },
    {
        "idea_id": 2,
        "name": "Stateful fuzz coach",
        "params": {"anyWords": "Echidna Medusa Foundry fuzzing", "words": "smart contract stateful", "noneWords": GLOBAL_EXCLUDE, "minLikes": "3", "max_results": "10"},
    },
    {
        "idea_id": 3,
        "name": "LP tax / crypto tax tools",
        "params": {"anyWords": "CoinTracker Koinly TaxBit TokenTax", "words": "crypto tax", "noneWords": GLOBAL_EXCLUDE, "minLikes": "5", "max_results": "10"},
    },
    {
        "idea_id": 4,
        "name": "x402 / agent payments",
        "params": {"words": "x402 agent payments", "noneWords": GLOBAL_EXCLUDE, "minLikes": "2", "max_results": "10"},
    },
    {
        "idea_id": 5,
        "name": "DeFi parameter simulation",
        "params": {"anyWords": "Gauntlet Chaos Labs risk parameter", "words": "DeFi simulation", "noneWords": GLOBAL_EXCLUDE, "minLikes": "3", "max_results": "10"},
    },
    {
        "idea_id": 6,
        "name": "Smart account security",
        "params": {"anyWords": "ERC-4337 EIP-7702 account abstraction", "words": "security vulnerability", "noneWords": GLOBAL_EXCLUDE, "minLikes": "3", "max_results": "10"},
    },
    {
        "idea_id": 7,
        "name": "AI agent dev tools",
        "params": {"anyWords": "Cursor Copilot Devin Claude agent", "words": "test execution slow", "noneWords": GLOBAL_EXCLUDE, "minLikes": "5", "max_results": "10"},
    },
]

# Mode 2: Pain point discovery (real user complaints -- tight queries)
PAIN_QUERIES = [
    {
        "category": "budgeting",
        "params": {"anyWords": "terrible broken hate sucks", "words": "budgeting app", "noneWords": GLOBAL_EXCLUDE + " bitcoin crypto", "minLikes": "5", "max_results": "10"},
    },
    {
        "category": "contractor_trust",
        "params": {"anyWords": "scammed ripped off terrible nightmare", "words": "contractor", "noneWords": GLOBAL_EXCLUDE + " military defense government", "minLikes": "5", "max_results": "10"},
    },
    {
        "category": "healthcare_nav",
        "params": {"anyWords": "impossible hours waiting months", "words": "find doctor appointment", "noneWords": GLOBAL_EXCLUDE + " political policy congress", "minLikes": "5", "max_results": "10"},
    },
    {
        "category": "caregiver",
        "params": {"anyWords": "overwhelmed exhausted burnout alone", "words": "caregiver parent care", "noneWords": GLOBAL_EXCLUDE + " political policy daycare childcare", "minLikes": "5", "max_results": "10"},
    },
    {
        "category": "pet_costs",
        "params": {"anyWords": "expensive insane ridiculous bill", "words": "vet pet", "noneWords": GLOBAL_EXCLUDE + " veteran military", "minLikes": "5", "max_results": "10"},
    },
    {
        "category": "food_waste_tool",
        "params": {"anyWords": "waste tracking inventory expired", "words": "restaurant food management", "noneWords": GLOBAL_EXCLUDE + " climate activism protest", "minLikes": "3", "max_results": "10"},
    },
    {
        "category": "crypto_tax_pain",
        "params": {"anyWords": "nightmare confusing wrong broken", "words": "crypto tax software", "noneWords": GLOBAL_EXCLUDE + " political congress regulation ban", "minLikes": "5", "max_results": "10"},
    },
    {
        "category": "ci_slow",
        "params": {"anyWords": "slow minutes waiting forever", "words": "CI tests pipeline", "noneWords": GLOBAL_EXCLUDE + " hiring interview leetcode", "minLikes": "10", "max_results": "10"},
    },
]

# Mode 3: Signal detection (Tier 1 competitor-specific, not generic)
SIGNAL_QUERIES = [
    {
        "signal": "security_tools_funding",
        "params": {"anyWords": "raised series seed funding acquired", "words": "Trail of Bits Certora OpenZeppelin security", "noneWords": GLOBAL_EXCLUDE, "minLikes": "10", "max_results": "10"},
    },
    {
        "signal": "tax_tools_moves",
        "params": {"anyWords": "raised launched acquired shutdown", "words": "CoinTracker Koinly TaxBit crypto tax", "noneWords": GLOBAL_EXCLUDE, "minLikes": "5", "max_results": "10"},
    },
    {
        "signal": "agent_infra_moves",
        "params": {"anyWords": "raised launched acquired shutdown", "words": "AI agent developer tools", "noneWords": GLOBAL_EXCLUDE, "minLikes": "10", "max_results": "10"},
    },
]

# Mode 4: Key voices (track specific influential accounts directly)
KEY_VOICES = [
    {"username": "samczsun", "relevance": "security (#2, #6)", "params": {"from": "samczsun", "max_results": "5"}},
    {"username": "TheCryptoCPA", "relevance": "crypto tax (#3)", "params": {"from": "TheCryptoCPA", "max_results": "5"}},
    {"username": "bertcmiller", "relevance": "MEV/infra (#5)", "params": {"from": "bertcmiller", "max_results": "5"}},
    {"username": "wilsoncusack", "relevance": "x402/Coinbase (#4)", "params": {"from": "wilsoncusack", "max_results": "5"}},
]

# ── Core Functions ───────────────────────────────────────────────────────────


def _load_seen_ids() -> set[str]:
    """Load tweet IDs from existing log for cross-run dedup."""
    seen = set()
    if TWITTER_LOG.exists():
        for line in TWITTER_LOG.read_text().splitlines():
            if line.strip():
                try:
                    entry = json.loads(line)
                    tid = entry.get("tweet_id", "")
                    if tid:
                        seen.add(tid)
                except json.JSONDecodeError:
                    continue
    return seen


def _twit_search(params: dict) -> list[dict]:
    """Execute a twit.sh search query. Returns list of tweet dicts.

    Budget-gated: checks daily/weekly caps before calling, logs cost after.
    """
    budget = check_budget()
    if budget["daily_remaining"] < TWIT_COST_PER_QUERY:
        log.warning(f"Daily budget exhausted: ${budget['daily_spent']:.3f}")
        return []
    if budget["weekly_remaining"] < TWIT_COST_PER_QUERY:
        log.warning(f"Weekly budget exhausted: ${budget['weekly_spent']:.3f}")
        return []

    qs = urlencode(params, quote_via=quote)
    url = f"{TWIT_BASE}/tweets/search?{qs}"

    cmd = [AGENTCASH_BIN, "fetch", url, "--format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        log.warning(f"twit.sh timeout: {url[:100]}")
        return []

    if proc.returncode != 0:
        log.warning(f"twit.sh call failed: {proc.stderr[:200]}")
        return []

    try:
        response = json.loads(proc.stdout)
    except json.JSONDecodeError:
        log.warning(f"Invalid JSON from twit.sh: {proc.stdout[:200]}")
        return []

    if not response.get("success"):
        error = response.get("error", {})
        status = error.get("statusCode", 0)
        if status == 402:
            log.warning("twit.sh: wallet empty (402). No cost incurred.")
        else:
            log.warning(f"twit.sh error: {error.get('message', 'unknown')}")
        return []

    # Only log cost AFTER confirmed success (payment went through)
    _append_spend_log({
        "ts": datetime.now(timezone.utc).isoformat(),
        "url": url[:200],
        "cost": TWIT_COST_PER_QUERY,
        "source": "twit.sh",
    })

    return response.get("data", {}).get("data", [])


def _twit_user_timeline(params: dict) -> list[dict]:
    """Fetch user timeline from twit.sh. Same budget/logging as search."""
    budget = check_budget()
    if budget["daily_remaining"] < TWIT_COST_PER_QUERY:
        return []

    username = params.get("from", "")
    max_results = params.get("max_results", "5")
    url = f"{TWIT_BASE}/tweets/user?username={quote(username)}&max_results={max_results}"

    cmd = [AGENTCASH_BIN, "fetch", url, "--format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        log.warning(f"twit.sh timeout for @{username}")
        return []

    if proc.returncode != 0:
        return []

    try:
        response = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    if not response.get("success"):
        error = response.get("error", {})
        if error.get("statusCode") == 402:
            log.warning(f"twit.sh: wallet empty for @{username}")
        return []

    _append_spend_log({
        "ts": datetime.now(timezone.utc).isoformat(),
        "url": url[:200],
        "cost": TWIT_COST_PER_QUERY,
        "source": "twit.sh",
    })

    return response.get("data", {}).get("data", [])


def _log_tweet(mode: str, label: str, tweet: dict):
    """Append tweet to JSONL log with file locking."""
    DATA_DIR.mkdir(exist_ok=True)
    author = tweet.get("author", {})
    metrics = tweet.get("public_metrics", {})
    entry = {
        "date": TODAY_ISO,
        "mode": mode,
        "label": label,
        "tweet_id": tweet.get("id"),
        "author": author.get("username", ""),
        "author_followers": author.get("public_metrics", {}).get("followers_count", 0),
        "text": tweet.get("text", "")[:500],
        "likes": metrics.get("like_count", 0),
        "retweets": metrics.get("retweet_count", 0),
        "replies": metrics.get("reply_count", 0),
        "created_at": tweet.get("created_at", ""),
    }
    with open(TWITTER_LOG, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(entry) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


def _dedup_tweets(tweets: list[dict], seen_ids: set[str]) -> list[dict]:
    """Remove duplicate tweets by ID (works across runs)."""
    result = []
    for t in tweets:
        tid = t.get("id", "")
        if tid and tid not in seen_ids:
            seen_ids.add(tid)
            result.append(t)
    return result


def _is_noise(tweet: dict) -> bool:
    """Filter obvious noise: bot farms, promotions, political takes."""
    text = (tweet.get("text", "") or "").lower()
    author = tweet.get("author", {})

    # Emoji spam (3+ rocket/fire/money emojis)
    emoji_count = sum(text.count(e) for e in ["🚀", "🔥", "💰", "💎", "🌙", "⚡"])
    if emoji_count > 2:
        return True

    # Bot patterns: low followers + high engagement = suspicious
    followers = author.get("public_metrics", {}).get("followers_count", 0)
    likes = tweet.get("public_metrics", {}).get("like_count", 0)
    if followers < 100 and likes > 50:
        return True

    # Promotional patterns
    promo_words = ["join our", "don't miss", "limited time", "click here", "sign up now", "free tokens"]
    if any(w in text for w in promo_words):
        return True

    return False


# ── Run Functions ────────────────────────────────────────────────────────────


def _run_query_list(queries: list[dict], mode: str, label_key: str, seen: set[str], dry_run: bool) -> list[dict]:
    """Generic runner for a list of queries. Handles budget, dedup, logging."""
    all_tweets = []

    for q in queries:
        label = q.get(label_key, q.get("name", q.get("signal", q.get("username", "?"))))

        if dry_run:
            log.info(f"  [DRY] {mode}/{label}: {q.get('params', {})}")
            continue

        budget = check_budget()
        if budget["daily_remaining"] < TWIT_COST_PER_QUERY:
            log.warning(f"Budget exceeded, stopping {mode}")
            break

        tweets = _twit_search(q["params"])
        tweets = _dedup_tweets(tweets, seen)
        tweets = [t for t in tweets if not _is_noise(t)]
        log.info(f"{mode}/{label}: {len(tweets)} tweets")

        for t in tweets:
            _log_tweet(mode, label, t)

        all_tweets.extend(tweets)

    return all_tweets


def run_competitors(seen: set[str], dry_run: bool = False) -> list[dict]:
    return _run_query_list(COMPETITOR_QUERIES, "competitor", "name", seen, dry_run)


def run_pain(seen: set[str], dry_run: bool = False) -> list[dict]:
    return _run_query_list(PAIN_QUERIES, "pain", "category", seen, dry_run)


def run_signals(seen: set[str], dry_run: bool = False) -> list[dict]:
    return _run_query_list(SIGNAL_QUERIES, "signal", "signal", seen, dry_run)


def run_voices(seen: set[str], dry_run: bool = False) -> list[dict]:
    """Track key voices by fetching their recent timelines."""
    all_tweets = []

    for voice in KEY_VOICES:
        if dry_run:
            log.info(f"  [DRY] voices/@{voice['username']} ({voice['relevance']})")
            continue

        budget = check_budget()
        if budget["daily_remaining"] < TWIT_COST_PER_QUERY:
            log.warning("Budget exceeded, stopping voices")
            break

        tweets = _twit_user_timeline(voice["params"])
        tweets = _dedup_tweets(tweets, seen)
        log.info(f"voices/@{voice['username']}: {len(tweets)} tweets")

        for t in tweets:
            _log_tweet("voice", f"@{voice['username']} ({voice['relevance']})", t)

        all_tweets.extend(tweets)

    return all_tweets


def _format_digest(tweets: list[dict], mode: str) -> str:
    """Format tweets into a readable Telegram digest."""
    if not tweets:
        return f"  {mode}: no results"

    ranked = sorted(
        tweets,
        key=lambda t: t.get("public_metrics", {}).get("like_count", 0)
        + t.get("public_metrics", {}).get("retweet_count", 0),
        reverse=True,
    )

    lines = [f"  {mode} ({len(tweets)} tweets):"]
    for t in ranked[:5]:
        author = t.get("author", {})
        metrics = t.get("public_metrics", {})
        text = t.get("text", "").replace("\n", " ")[:100]
        lines.append(
            f"    @{author.get('username', '?')} "
            f"({metrics.get('like_count', 0)}L) "
            f"{text}"
        )
    return "\n".join(lines)


def run(mode: str = "all", dry_run: bool = False) -> dict:
    """Run Twitter watch. Returns {mode_name: [tweets]}."""
    seen = _load_seen_ids()
    log.info(f"Loaded {len(seen)} previously seen tweet IDs for dedup")

    results = {}
    modes = {
        "competitors": run_competitors,
        "pain": run_pain,
        "signals": run_signals,
        "voices": run_voices,
    }

    for mode_name, runner in modes.items():
        if mode in ("all", mode_name):
            log.info(f"=== {mode_name} ===")
            results[mode_name] = runner(seen, dry_run)

    if dry_run:
        return results

    from scripts.notify import send as notify

    total = sum(len(v) for v in results.values())
    if total == 0:
        log.info("No new tweets found across all modes.")
        return results

    digest_parts = []
    for mode_name, tweets in results.items():
        digest_parts.append(_format_digest(tweets, mode_name))

    notify(
        f"Twitter Watch: {total} new tweets",
        "\n".join(digest_parts),
        level="info",
    )

    return results


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    mode = "all"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]

    results = run(mode=mode, dry_run=dry_run)
    total = sum(len(v) for v in results.values())
    suffix = "(dry run)" if dry_run else "logged"
    print(f"Done. {total} tweets {suffix}.")
