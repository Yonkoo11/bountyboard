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

    def test_verified_candidate_keeps_verification_date(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate_file = Path(directory) / "candidates.json"
            candidate_file.write_text(
                '[{"name":"Verified event","url":"https://example.com",'
                '"verification_status":"verified","last_checked_at":"2026-08-08"}]'
            )
            with patch.object(generate_site, "CANDIDATES_FILE", candidate_file):
                leads = generate_site.load_candidates()
        self.assertEqual(leads[0]["verified_at"], "2026-08-08")
        self.assertEqual(
            generate_site.effective_verification(leads[0]),
            "verified",
        )

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
        self.assertIn("Discovery is not verification", page)
        self.assertIn('styles.css?v=', page)
        self.assertIn('app.js?v=', page)
        self.assertNotIn('styles.css?v=20260809', page)
        self.assertNotIn("See the opportunity<br>before it passes", page)

    def test_generated_page_uses_restored_editorial_hero(self):
        item = {
            "id": "visible-hackathon",
            "name": "Visible Hackathon",
            "category": "hackathon",
            "status": "active",
            "deadline": "2026-09-16",
            "url": "https://example.com/hackathon",
            "verification_status": "partially_verified",
            "last_checked_at": "2026-08-09",
            "application_status": "open",
            "format": "online",
        }
        with patch.object(generate_site.db, "get_all", return_value=[item]), patch.object(
            generate_site, "load_candidates", return_value=[]
        ):
            page = generate_site.generate()
        self.assertIn("See the opportunity before it passes.", page)
        self.assertIn("Visible Hackathon", page)
        self.assertLess(page.index('id="hero-title"'), page.index('id="opportunities-title"'))

    def test_design_uses_one_full_radar_and_personal_availability_filter(self):
        items = [{
            "id": f"hackathon-{index}",
            "name": f"Hackathon {index}",
            "category": "hackathon",
            "status": "active",
            "deadline": f"2026-09-{index + 1:02d}",
            "url": f"https://example.com/{index}",
            "format": "online",
            "verification_status": "unverified",
            "application_status": "open",
        } for index in range(8)]
        with patch.object(generate_site.db, "get_all", return_value=items), patch.object(
            generate_site, "load_candidates", return_value=[]
        ):
            page = generate_site.generate()
        self.assertNotIn('class="hackathon-grid"', page)
        self.assertIn('id="availabilityFilter"', page)
        self.assertIn('value="for_me"', page)
        self.assertIn("All possible opportunities", page)

    def test_availability_classification_is_conservative(self):
        self.assertEqual(generate_site.availability_state({"format": "Online"}), "available")
        self.assertEqual(generate_site.availability_state({"format": "In-person"}), "unavailable")
        self.assertEqual(
            generate_site.availability_state({"name": "ETHGlobal Tokyo", "angle": "In-person in Tokyo"}),
            "unavailable",
        )
        self.assertEqual(
            generate_site.availability_state({"angle": "Online qualification with an in-person final"}),
            "conditional",
        )
        self.assertEqual(
            generate_site.availability_state({"angle": "Students only; virtual hackathon"}),
            "conditional",
        )
        self.assertEqual(generate_site.availability_state({"angle": "Details coming soon"}), "unknown")

    def test_optional_finalist_travel_is_not_hidden(self):
        state = generate_site.availability_state({
            "angle": "Finalists may be invited to an in-person tournament in Tokyo."
        })
        self.assertEqual(state, "conditional")

    def test_generated_row_exposes_availability_to_filter(self):
        row = generate_site.opportunity_row({
            "name": "Local-only event",
            "format": "In-person",
            "category": "hackathon",
            "status": "radar",
            "application_status": "open",
            "verification_status": "unverified",
        }, 1)
        self.assertIn('data-availability="unavailable"', row)
        self.assertIn("In-person only", row)


if __name__ == "__main__":
    unittest.main()
