import unittest

from scripts.validate_profile import validate


class ProfileValidationTests(unittest.TestCase):
    def test_valid_unknown_profile(self):
        self.assertEqual(validate({
            "remote_only": True,
            "country": "unknown",
            "student_status": "unknown",
            "age_band": "unknown",
            "travel_regions": [],
        }), [])

    def test_rejects_ambiguous_types_and_values(self):
        errors = validate({
            "remote_only": "yes",
            "country": "",
            "student_status": "maybe",
            "age_band": 18,
            "travel_regions": "global",
        })
        self.assertEqual(len(errors), 5)


if __name__ == "__main__":
    unittest.main()
