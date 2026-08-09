import unittest
from datetime import datetime, timezone

from scripts.check_freshness import evaluate_freshness


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)

    def test_recent_refresh_passes(self):
        ok, message = evaluate_freshness(
            {"completed_at": "2026-08-09T09:00:00+00:00"}, now=self.now
        )
        self.assertTrue(ok)
        self.assertIn("3.0h old", message)

    def test_stale_refresh_fails(self):
        ok, message = evaluate_freshness(
            {"completed_at": "2026-08-09T03:00:00Z"}, now=self.now
        )
        self.assertFalse(ok)
        self.assertIn("limit 8h", message)

    def test_missing_or_future_timestamp_fails(self):
        self.assertFalse(evaluate_freshness({}, now=self.now)[0])
        self.assertFalse(
            evaluate_freshness(
                {"completed_at": "2026-08-09T13:00:00+00:00"}, now=self.now
            )[0]
        )
