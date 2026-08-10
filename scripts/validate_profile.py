"""Validate the personal eligibility profile without guessing private facts."""

from __future__ import annotations

import json
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
PROFILE_FILE = REPO_DIR / "data" / "user_profile.json"
ALLOWED = {
    "country": {"unknown"},
    "student_status": {"unknown", "student", "not_student"},
    "age_band": {"unknown", "under_13", "13_17", "18_plus"},
}


def validate(profile: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(profile.get("remote_only"), bool):
        errors.append("remote_only must be true or false")
    for field, fixed_values in ALLOWED.items():
        value = profile.get(field)
        if field == "country":
            if not isinstance(value, str) or not value.strip():
                errors.append("country must be an ISO country code or 'unknown'")
        elif value not in fixed_values:
            errors.append(f"{field} must be one of: {', '.join(sorted(fixed_values))}")
    if not isinstance(profile.get("travel_regions"), list):
        errors.append("travel_regions must be a list")
    return errors


def main() -> int:
    profile = json.loads(PROFILE_FILE.read_text())
    errors = validate(profile)
    if errors:
        print("Profile invalid:")
        for error in errors:
            print(f"- {error}")
        return 1
    unknown = [field for field in ("country", "student_status", "age_band") if profile.get(field) == "unknown"]
    print(f"Profile valid. Unconfirmed fields: {', '.join(unknown) if unknown else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
