import unittest

from scripts.triage_candidates import triage


class CandidateTriageTests(unittest.TestCase):
    def test_remote_only_profile_rejects_confirmed_in_person(self):
        item = triage({"name": "Local", "format": "in-person"}, {"remote_only": True})
        self.assertEqual(item["profile_match"], "no")
        self.assertIn("in-person only", item["research_reasons"])

    def test_unknown_personal_attributes_never_become_eligible(self):
        item = triage({"name": "Mystery", "url": "https://example.com"}, {"remote_only": True})
        self.assertEqual(item["profile_match"], "conditional")
        self.assertIn("participation format", item["research_reasons"])

    def test_explicit_online_lead_can_match_but_keeps_missing_research(self):
        item = triage({"name": "Remote", "format": "online", "url": "https://example.com"}, {"remote_only": True})
        self.assertEqual(item["profile_match"], "yes")
        self.assertIn("deadline", item["research_reasons"])
        self.assertIn("eligibility", item["research_reasons"])

    def test_student_restriction_requires_known_profile_fact(self):
        item = triage(
            {"name": "Student AI", "format": "online", "eligibility": "University students", "url": "https://example.com"},
            {"remote_only": True, "student_status": "unknown"},
        )
        self.assertEqual(item["profile_match"], "conditional")
        self.assertIn("student status", item["research_reasons"])


if __name__ == "__main__":
    unittest.main()
