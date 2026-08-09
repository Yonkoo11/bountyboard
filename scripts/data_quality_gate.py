"""Fail loudly when a discovery run completed with materially degraded coverage.

The gate does not decide which opportunities are good. It checks whether the
radar had enough functioning inputs for a green run to be meaningful.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median
from typing import Any

REPO_DIR = Path(__file__).parent.parent
LAST_RUN_FILE = REPO_DIR / "data" / "last_run.json"
SOURCE_HEALTH_FILE = REPO_DIR / "data" / "source_health.json"

CORE_SOURCES = {"ethglobal", "devpost"}
EXPECTED_SOURCES = {"dorahacks", "solana"}
OPTIONAL_SOURCES = {"gitcoin", "twitter", "exa"}
MINIMUM_TOTAL_RESULTS = 10


def evaluate(manifest: dict[str, Any], health: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return blocking failures and non-blocking warnings for one scan."""
    failures: list[str] = []
    warnings: list[str] = []
    counts = manifest.get("source_counts") or {}

    for error in manifest.get("source_errors") or []:
        source = str(error).split(":", 1)[0]
        message = f"source error: {error}"
        if source in OPTIONAL_SOURCES:
            warnings.append(message)
        else:
            failures.append(message)

    missing = sorted((CORE_SOURCES | EXPECTED_SOURCES | OPTIONAL_SOURCES) - counts.keys())
    if missing:
        failures.append(f"sources did not report a result: {', '.join(missing)}")

    for source in sorted(CORE_SOURCES):
        if int(counts.get(source, 0)) <= 0:
            failures.append(f"core source {source} returned zero results")

    for source in sorted(EXPECTED_SOURCES):
        if int(counts.get(source, 0)) <= 0:
            failures.append(f"expected source {source} returned zero results")

    for source in sorted(OPTIONAL_SOURCES):
        if int(counts.get(source, 0)) <= 0:
            warnings.append(f"optional source {source} returned zero results")

    total = sum(max(0, int(value or 0)) for value in counts.values())
    if total < MINIMUM_TOTAL_RESULTS:
        failures.append(f"only {total} raw results were collected (minimum {MINIMUM_TOTAL_RESULTS})")

    for source, current in counts.items():
        history = (health.get(source) or {}).get("history") or []
        previous = [int(value) for value in history[:-1] if int(value) > 0]
        if len(previous) < 3:
            continue
        baseline = median(previous)
        if baseline >= 5 and int(current or 0) < baseline * 0.25:
            failures.append(
                f"source {source} collapsed to {current} results from a median of {baseline:g}"
            )

    return failures, warnings


def main() -> int:
    if not LAST_RUN_FILE.exists():
        print(f"QUALITY GATE FAILED: missing {LAST_RUN_FILE.relative_to(REPO_DIR)}")
        return 1
    if not SOURCE_HEALTH_FILE.exists():
        print(f"QUALITY GATE FAILED: missing {SOURCE_HEALTH_FILE.relative_to(REPO_DIR)}")
        return 1

    try:
        manifest = json.loads(LAST_RUN_FILE.read_text())
        health = json.loads(SOURCE_HEALTH_FILE.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"QUALITY GATE FAILED: operational state is unreadable: {error}")
        return 1

    failures, warnings = evaluate(manifest, health)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    counts = manifest.get("source_counts") or {}
    print(f"QUALITY GATE PASSED: {sum(counts.values())} raw results across {len(counts)} sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
