import unittest
from datetime import date

from scripts.deadline_digest import render_digest, urgent_candidates


class DeadlineDigestTests(unittest.TestCase):
    def test_digest_excludes_in_person_rejected_and_already_applied(self):
        base = {"deadline": "2026-08-12", "profile_match": "yes", "review_status": "pending", "application_status": "open"}
        rows = [
            {**base, "name": "Keep", "url": "https://example.com/keep", "theme_fit": 8},
            {**base, "name": "In person", "profile_match": "no"},
            {**base, "name": "Rejected", "review_status": "rejected"},
            {**base, "name": "Applied", "application_status": "applied"},
        ]
        urgent = urgent_candidates(rows, today=date(2026, 8, 9), days=7)
        self.assertEqual([item["name"] for item in urgent], ["Keep"])
        self.assertEqual(urgent[0]["days_remaining"], 3)

    def test_digest_orders_by_deadline_and_formats_human_timing(self):
        rows = [
            {"name": "Later", "deadline": "2026-08-11", "profile_match": "yes"},
            {"name": "Today", "deadline": "2026-08-09", "profile_match": "conditional"},
        ]
        urgent = urgent_candidates(rows, today=date(2026, 8, 9), days=3)
        digest = render_digest(urgent)
        self.assertLess(digest.index("Today"), digest.index("Later"))
        self.assertIn("— today —", digest)
