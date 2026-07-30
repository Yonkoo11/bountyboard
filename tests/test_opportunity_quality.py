from datetime import date
import unittest

from opportunity_quality import (
    actionability_score,
    application_state,
    completeness,
    days_until,
    effective_verification,
    expected_value,
    is_safe_url,
    missing_details,
)


TODAY = date(2026, 7, 30)


class OpportunityQualityTests(unittest.TestCase):
    def test_unknown_deadline_is_unknown_not_magic_number(self):
        self.assertIsNone(days_until(None, today=TODAY))
        self.assertIsNone(days_until("not-a-date", today=TODAY))

    def test_deadline_state_closes_expired_opportunity(self):
        opportunity = {"deadline": "2026-07-29", "application_status": "open"}
        self.assertEqual(application_state(opportunity, today=TODAY), "closed")

    def test_old_verification_becomes_stale(self):
        opportunity = {
            "verification_status": "verified",
            "last_checked_at": "2026-06-01",
        }
        self.assertEqual(effective_verification(opportunity, today=TODAY), "stale")

    def test_recent_verification_remains_verified(self):
        opportunity = {
            "verification_status": "verified",
            "verified_at": "2026-07-25",
            "last_checked_at": "2026-07-29",
        }
        self.assertEqual(effective_verification(opportunity, today=TODAY), "verified")

    def test_unlinked_unknown_lead_remains_scorable_but_is_penalized(self):
        lead = {
            "name": "Possible bounty",
            "theme_fit": 9,
            "prize_usd": 100_000,
            "verification_status": "unverified",
            "application_status": "unknown",
        }
        sourced = {**lead, "url": "https://example.com", "application_status": "rolling"}
        self.assertGreater(actionability_score(sourced, today=TODAY), actionability_score(lead, today=TODAY))
        self.assertGreaterEqual(actionability_score(lead, today=TODAY), 0)

    def test_complete_verified_deadline_ranks_above_incomplete_lead(self):
        verified = {
            "name": "Verified event",
            "url": "https://example.com",
            "deadline": "2026-08-05",
            "prize_usd": 20_000,
            "theme_fit": 8,
            "tracks": ["AI"],
            "eligibility": "Open worldwide",
            "source": "official",
            "last_checked_at": "2026-07-29",
            "verification_status": "verified",
            "application_status": "open",
        }
        lead = {"name": "Lead", "theme_fit": 10, "prize_usd": 100_000}
        self.assertGreater(actionability_score(verified, today=TODAY), actionability_score(lead, today=TODAY))
        self.assertEqual(completeness(verified), 100)

    def test_expected_value_requires_individual_award_and_probability(self):
        self.assertIsNone(expected_value({"prize_usd": 100_000}))
        self.assertEqual(expected_value({"max_award_usd": 10_000, "win_probability": 0.2}), 2_000)

    def test_missing_details_are_explicit(self):
        self.assertEqual(
            missing_details({"name": "Lead"}),
            ["source link", "deadline", "eligibility", "freshness check"],
        )

    def test_source_urls_require_absolute_http_protocol(self):
        self.assertTrue(is_safe_url("https://example.com"))
        self.assertFalse(is_safe_url("javascript:alert(1)"))
        self.assertFalse(is_safe_url("//example.com"))


if __name__ == "__main__":
    unittest.main()
