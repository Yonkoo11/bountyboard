import unittest
from datetime import datetime, timezone

from scripts.candidate_workflow import find_candidate, queue_key, update_candidate


class CandidateWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
        self.item = {
            "candidate_id": "lead-abc",
            "name": "Remote Agent Hack",
            "url": "https://example.com/hack",
            "review_status": "pending",
            "application_status": "open",
            "profile_match": "yes",
            "deadline": "2026-08-17",
        }

    def test_candidate_can_be_found_by_stable_id_url_or_exact_name(self):
        for identity in ("lead-abc", "https://example.com/hack", "Remote Agent Hack"):
            self.assertIs(find_candidate([self.item], identity), self.item)

    def test_application_cannot_advance_before_acceptance(self):
        with self.assertRaisesRegex(ValueError, "accept a candidate"):
            update_candidate(self.item, application_status="applied", now=self.now)

    def test_accepted_candidate_can_move_to_applied(self):
        accepted = update_candidate(self.item, review_status="accepted", now=self.now)
        applied = update_candidate(accepted, application_status="applied", note="Submitted", now=self.now)
        self.assertEqual(applied["review_status"], "accepted")
        self.assertEqual(applied["application_status"], "applied")
        self.assertEqual(applied["decision_note"], "Submitted")

    def test_queue_prioritizes_personally_available_then_deadline(self):
        conditional = {**self.item, "candidate_id": "lead-conditional", "profile_match": "conditional", "deadline": "2026-08-10"}
        later_available = {**self.item, "candidate_id": "lead-later", "deadline": "2026-08-20"}
        self.assertEqual(sorted([conditional, later_available], key=queue_key)[0]["candidate_id"], "lead-later")
