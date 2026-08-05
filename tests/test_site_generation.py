import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_site


class SiteGenerationTests(unittest.TestCase):
    def test_candidate_leads_are_loaded_without_being_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate_file = Path(directory) / "candidates.json"
            candidate_file.write_text(
                '[{"name":"Unknown opportunity","url":"https://example.com","source":"scout"}]'
            )
            with patch.object(generate_site, "CANDIDATES_FILE", candidate_file):
                leads = generate_site.load_candidates()
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "radar")
        self.assertEqual(leads[0]["verification_status"], "unverified")

    def test_reviewed_candidate_keeps_evidence_state(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate_file = Path(directory) / "candidates.json"
            candidate_file.write_text(
                '[{"name":"Reviewed event","url":"https://example.com",'
                '"verification_status":"partially_verified","application_status":"open",'
                '"last_checked_at":"2026-08-06","eligibility":"Application required"}]'
            )
            with patch.object(generate_site, "CANDIDATES_FILE", candidate_file):
                leads = generate_site.load_candidates()
        self.assertEqual(leads[0]["verification_status"], "partially_verified")
        self.assertEqual(leads[0]["application_status"], "open")
        self.assertEqual(leads[0]["last_checked_at"], "2026-08-06")
        self.assertEqual(leads[0]["eligibility"], "Application required")

    def test_unknown_deadline_uses_human_label(self):
        self.assertEqual(
            generate_site.deadline_label({"application_status": "unknown"}),
            "Deadline unknown",
        )
        self.assertNotIn("9999", generate_site.deadline_label({}))

    def test_labeled_candidate_deadline_is_recovered(self):
        item = {"description": "**Deadline Date:** February 12, 2026 **Prize:** $100K"}
        self.assertEqual(generate_site.candidate_deadline(item), "2026-02-12")

    def test_duplicate_source_urls_are_collapsed(self):
        items = [
            {"name": "First", "url": "https://example.com/"},
            {"name": "Duplicate title", "url": "https://example.com"},
        ]
        self.assertEqual(len(generate_site.deduplicate(items)), 1)

    def test_generated_row_escapes_untrusted_content(self):
        row = generate_site.opportunity_row(
            {
                "name": "<script>alert(1)</script>",
                "category": "hackathon",
                "status": "radar",
                "application_status": "unknown",
                "verification_status": "unverified",
                "theme_fit": 1,
            },
            1,
        )
        self.assertNotIn("<script>", row)
        self.assertIn("&lt;script&gt;", row)

    def test_generated_row_rejects_unsafe_link_protocols(self):
        row = generate_site.opportunity_row(
            {
                "name": "Unsafe lead",
                "url": "javascript:alert(1)",
                "submission_url": "data:text/html,<script>alert(1)</script>",
                "category": "bounty",
                "status": "radar",
                "application_status": "unknown",
                "verification_status": "unverified",
            },
            1,
        )
        self.assertNotIn("javascript:", row)
        self.assertNotIn("data:text", row)
        self.assertIn("Source needed", row)

    def test_safe_url_accepts_only_absolute_http_urls(self):
        self.assertEqual(generate_site.safe_url("https://example.com/path"), "https://example.com/path")
        self.assertEqual(generate_site.safe_url("http://example.com"), "http://example.com")
        self.assertEqual(generate_site.safe_url("//example.com"), "")
        self.assertEqual(generate_site.safe_url("javascript:alert(1)"), "")

    def test_generated_page_exposes_refresh_age_without_claiming_source_verification(self):
        with patch.object(generate_site.db, "get_all", return_value=[]), patch.object(
            generate_site, "load_candidates", return_value=[]
        ):
            page = generate_site.generate()
        self.assertIn('id="freshnessStatus"', page)
        self.assertIn('data-generated-at="', page)
        self.assertIn("Last successful refresh", page)
        self.assertIn("Recently generated is not the same as verified", page)
        self.assertIn('styles.css?v=', page)
        self.assertIn('app.js?v=', page)
        self.assertNotIn("See the opportunity<br>before it passes", page)


if __name__ == "__main__":
    unittest.main()
