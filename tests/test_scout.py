import unittest
from unittest.mock import patch

from scripts import scout


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

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


if __name__ == "__main__":
    unittest.main()
