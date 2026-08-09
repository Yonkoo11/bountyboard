import unittest
from unittest.mock import patch

from scripts import scout


class FakeResponse:
    def __init__(self, payload=None, text=""):
        self.payload = payload
        self.text = text

    def json(self):
        return self.payload


def devpost_item(name, url, dates="Aug 1 - Aug 17, 2026"):
    return {
        "title": name,
        "url": url,
        "themes": ["Machine Learning/AI"],
        "prize_amount": 5000,
        "submission_period_dates": dates,
    }


class ScoutTests(unittest.TestCase):
    def test_devpost_fetches_open_and_upcoming_with_pagination(self):
        calls = []

        def fake_fetch(_url, **kwargs):
            params = kwargs["params"]
            calls.append(dict(params))
            status = params["status[]"]
            page = params["page"]
            if status == "open" and page == 1:
                return FakeResponse({
                    "hackathons": [devpost_item("Open One", "https://open-one.devpost.com")],
                    "meta": {"total_count": 2, "per_page": 1},
                })
            if status == "open" and page == 2:
                return FakeResponse({
                    "hackathons": [devpost_item("Open Two", "https://open-two.devpost.com")],
                    "meta": {"total_count": 2, "per_page": 1},
                })
            return FakeResponse({
                "hackathons": [devpost_item("Upcoming", "https://upcoming.devpost.com")],
                "meta": {"total_count": 1, "per_page": 9},
            })

        with patch.object(scout, "_fetch", side_effect=fake_fetch):
            rows = scout.fetch_devpost()

        self.assertEqual({row["name"] for row in rows}, {"Open One", "Open Two", "Upcoming"})
        self.assertIn({"challenge_type[]": "online", "status[]": "open", "page": 2}, calls)
        self.assertTrue(any(call["status[]"] == "upcoming" for call in calls))

    def test_devpost_deduplicates_same_event_across_states(self):
        payload = {
            "hackathons": [devpost_item("Same Event", "https://same.devpost.com")],
            "meta": {"total_count": 1, "per_page": 9},
        }
        with patch.object(scout, "_fetch", return_value=FakeResponse(payload)):
            rows = scout.fetch_devpost()
        self.assertEqual(len(rows), 1)

    def test_devpost_extracts_prize_from_markup_label(self):
        item = devpost_item("Markup Prize", "https://markup.devpost.com")
        item["prize_amount"] = "$$<span data-currency-value>685,000</span>"
        payload = {"hackathons": [item], "meta": {"total_count": 1, "per_page": 9}}
        with patch.object(scout, "_fetch", return_value=FakeResponse(payload)):
            rows = scout.fetch_devpost()
        self.assertEqual(rows[0]["prize_usd"], 685_000)
        self.assertEqual(rows[0]["prize_note"], "$685,000")

    def test_low_score_candidate_is_preserved_as_unverified(self):
        candidate = scout._candidate_from_item(
            {
                "source": "devpost",
                "url": "https://wellness.devpost.com",
                "name": "Wellness Hackathon",
                "deadline": "2026-08-16",
            },
            0,
            scout_date="2026-08-08",
        )
        self.assertEqual(candidate["theme_fit"], 0)
        self.assertEqual(candidate["verification_status"], "unverified")
        self.assertEqual(candidate["scout_date"], "2026-08-08")

    def test_candidate_url_can_join_database_dedup_state(self):
        existing_urls = {"https://database.example/event"}
        candidates = [{"url": "https://candidate.example/event"}]
        existing_urls.update(scout._candidate_urls(candidates))
        self.assertIn("https://candidate.example/event", existing_urls)

    def test_hacklist_uses_canonical_apply_links_as_unverified_leads(self):
        html = """
        <article aria-label="New Agent Hack, $12,500. View details.">
          <p>Organizer</p><h3>New Agent Hack</h3>
          <p>Build useful autonomous agents with real transactions.</p>
          <a href="https://organizer.example/hackathon">Apply</a>
        </article>
        """
        with patch.object(scout, "_fetch", return_value=FakeResponse(text=html)):
            rows = scout.fetch_hacklist()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "hacklist")
        self.assertEqual(rows[0]["url"], "https://organizer.example/hackathon")
        self.assertEqual(rows[0]["prize_usd"], 12500)
        self.assertEqual(rows[0]["prize_note"], "$12,500")
        self.assertEqual(rows[0]["_name_aliases"], ["Organizer New Agent Hack"])
        self.assertIsNone(rows[0]["deadline"])

    def test_hacklist_rejects_non_http_apply_links_and_deduplicates_urls(self):
        html = """
        <article><h3>Unsafe</h3><a href="javascript:alert(1)">Apply</a></article>
        <article><h3>First</h3><a href="https://example.com/event">Apply</a></article>
        <article><h3>Duplicate</h3><a href="https://example.com/event">Apply</a></article>
        """
        with patch.object(scout, "_fetch", return_value=FakeResponse(text=html)):
            rows = scout.fetch_hacklist()
        self.assertEqual([row["name"] for row in rows], ["First"])

    def test_usd_amount_handles_compact_and_non_cash_labels(self):
        self.assertEqual(scout._usd_amount("$2M total"), 2_000_000)
        self.assertEqual(scout._usd_amount("$8.75K"), 8_750)
        self.assertEqual(scout._usd_amount("Hardware prizes"), 0)

    def test_source_name_aliases_match_existing_platform_titles(self):
        item = {
            "name": "Shipaton 2026",
            "_name_aliases": ["RevenueCat Shipaton 2026"],
        }
        self.assertIn(
            scout._name_slug("RevenueCat Shipaton 2026"),
            scout._item_name_slugs(item),
        )

    def test_ethglobal_keeps_hackathons_cleans_titles_and_skips_conferences(self):
        html = """
        <div><a href="/events/ethonline2026">September 4—16 ETHOnline 2026 Async Hackathon Apply</a></div>
        <div><a href="/events/tokyo2026">September 25—27 ETHGlobal Tokyo 2026 IRL Hackathon Apply</a></div>
        <div><a href="/events/pragma-tokyo2026">September 26 Pragma Tokyo 2026 Conference Apply</a></div>
        """
        with patch.object(scout, "_fetch", return_value=FakeResponse(text=html)):
            rows = scout.fetch_ethglobal()
        self.assertEqual([row["name"] for row in rows], ["ETHOnline 2026", "ETHGlobal Tokyo 2026"])
        self.assertEqual([row["deadline"] for row in rows], ["2026-09-16", "2026-09-27"])
        self.assertFalse(any("Pragma" in row["name"] for row in rows))

    def test_solana_skips_winners_and_generic_links(self):
        html = """
        <div><a href="/news/old-hackathon-winners">2023 Hackathon Winners</a></div>
        <div><a href="/events">Events</a></div>
        <div><a href="/hackathon/new">New Solana Hackathon</a> December 12, 2099</div>
        """
        with patch.object(scout, "_fetch", return_value=FakeResponse(text=html)):
            rows = scout.fetch_solana()
        self.assertEqual(len(rows), 1)
        self.assertIn("New Solana Hackathon", rows[0]["name"])


if __name__ == "__main__":
    unittest.main()
