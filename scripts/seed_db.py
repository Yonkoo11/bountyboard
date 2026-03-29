"""Seed roster.db from opportunities.json (for CI or fresh clones)."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import db

data_file = REPO / "data" / "opportunities.json"
if not data_file.exists():
    print("No opportunities.json found")
    sys.exit(1)

with open(data_file) as f:
    opps = json.load(f)

for o in opps:
    if o.get("category") == "contest":
        o["category"] = "hackathon"
    try:
        db.upsert(o)
    except Exception as e:
        print(f"SKIP {o.get('id', '?')}: {e}")

count = db.count()
print(f"Seeded {sum(count.values())} entries: {count}")
