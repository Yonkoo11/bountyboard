import unittest

from scripts.data_quality_gate import evaluate


class DataQualityGateTests(unittest.TestCase):
    def healthy_manifest(self):
        return {
            "source_counts": {
                "ethglobal": 20,
                "devpost": 50,
                "hacklist": 30,
                "dorahacks": 10,
                "gitcoin": 0,
                "solana": 8,
                "twitter": 0,
                "exa": 0,
            }
        }

    def test_healthy_core_sources_pass_with_optional_warnings(self):
        failures, warnings = evaluate(self.healthy_manifest(), {})
        self.assertEqual(failures, [])
        self.assertIn("optional source exa returned zero results", warnings)

    def test_zero_expected_source_blocks_green_run(self):
        manifest = self.healthy_manifest()
        manifest["source_counts"]["dorahacks"] = 0
        failures, _ = evaluate(manifest, {})
        self.assertIn("expected source dorahacks returned zero results", failures)

    def test_zero_hacklist_crosscheck_blocks_green_run(self):
        manifest = self.healthy_manifest()
        manifest["source_counts"]["hacklist"] = 0
        failures, _ = evaluate(manifest, {})
        self.assertIn("expected source hacklist returned zero results", failures)

    def test_historical_source_collapse_blocks_green_run(self):
        manifest = self.healthy_manifest()
        manifest["source_counts"]["devpost"] = 2
        health = {"devpost": {"history": [50, 52, 48, 2]}}
        failures, _ = evaluate(manifest, health)
        self.assertTrue(any("devpost collapsed" in failure for failure in failures))

    def test_missing_source_is_not_silently_ignored(self):
        manifest = self.healthy_manifest()
        del manifest["source_counts"]["ethglobal"]
        failures, _ = evaluate(manifest, {})
        self.assertTrue(any("did not report" in failure for failure in failures))

    def test_partial_source_error_blocks_green_run(self):
        manifest = self.healthy_manifest()
        manifest["source_errors"] = ["devpost: 1 request failure(s)"]
        failures, _ = evaluate(manifest, {})
        self.assertIn("source error: devpost: 1 request failure(s)", failures)

    def test_optional_source_error_is_a_warning(self):
        manifest = self.healthy_manifest()
        manifest["source_errors"] = ["gitcoin: 4 request failure(s)"]
        failures, warnings = evaluate(manifest, {})
        self.assertEqual(failures, [])
        self.assertIn("source error: gitcoin: 4 request failure(s)", warnings)


if __name__ == "__main__":
    unittest.main()
