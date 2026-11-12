import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.analysis.consolidate_canonical_themes import (
    canonical_theme_id,
    consolidate,
    flatten_themes,
    load_taxonomy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = PROJECT_ROOT / "configs" / "canonical_themes.v1.json"


def theme_record(
    *,
    source_theme_id: str,
    batch_id: str,
    bucket: str,
    theme_id: str,
    area: str,
    evidence: list[dict] | None = None,
) -> dict:
    return {
        "source_file": "fixture.json",
        "source_theme_id": source_theme_id,
        "batch_id": batch_id,
        "sentiment_bucket": bucket,
        "theme_id": theme_id,
        "theme_name_zh": "測試主題",
        "summary_zh": "測試摘要",
        "affected_area": area,
        "severity": "high",
        "evidence": evidence or [],
    }


class CanonicalThemeRuleTests(unittest.TestCase):
    def test_routes_pain_themes_with_specific_overrides(self):
        cases = [
            ("mobile_page_visibility_blank_screen", "mobile_app", "content_rendering_access"),
            ("mobile_typing_editing_input_bugs", "editing", "editing_input_controls"),
            ("feature_gaps_for_mobile_workflows", "editing", "mobile_ux_feature_parity"),
            ("missing_customization_and_display_options", "editing", "customization_feature_gaps"),
            ("bugs_and_data_loss", "other", "sync_offline_data_integrity"),
            ("account_gate_onboarding_block", "onboarding", "account_access_auth"),
        ]
        for theme_id, area, expected in cases:
            with self.subTest(theme_id=theme_id):
                record = theme_record(
                    source_theme_id=f"negative_001::{theme_id}",
                    batch_id="negative_001",
                    bucket="negative",
                    theme_id=theme_id,
                    area=area,
                )
                self.assertEqual(canonical_theme_id(record), expected)

    def test_routes_positive_themes_separately(self):
        record = theme_record(
            source_theme_id="positive_001::cross_device_sync_and_access",
            batch_id="positive_001",
            bucket="positive",
            theme_id="cross_device_sync_and_access",
            area="sync",
        )
        self.assertEqual(canonical_theme_id(record), "cross_device_mobile_value")


class FlattenThemesTests(unittest.TestCase):
    def test_flattens_batch_themes_with_stable_source_ids(self):
        with TemporaryDirectory() as temporary_directory:
            input_dir = Path(temporary_directory)
            payload = {
                "batch_id": "negative_001",
                "sentiment_bucket": "negative",
                "themes": [
                    {
                        "theme_id": "performance_and_lag",
                        "theme_name_zh": "效能問題",
                        "summary_zh": "App 很慢",
                        "affected_area": "performance",
                        "severity": "high",
                        "evidence": [{"review_id": "review-1", "quote": "slow"}],
                    }
                ],
            }
            (input_dir / "negative_001_output.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )

            records = flatten_themes(input_dir)

            self.assertEqual(len(records), 1)
            self.assertEqual(
                records[0]["source_theme_id"],
                "negative_001::performance_and_lag",
            )
            self.assertEqual(records[0]["evidence"][0]["review_id"], "review-1")


class ConsolidateThemesTests(unittest.TestCase):
    def test_aggregates_source_batch_evidence_and_unique_review_counts(self):
        taxonomy = load_taxonomy(TAXONOMY_PATH)
        shared_evidence = {
            "review_id": "review-1",
            "review_created_at": "2026-06-01T00:00:00+00:00",
            "app_version": "0.6.1",
            "thumbs_up_count": "2",
            "score": "1",
            "quote": "very slow",
            "reason_zh": "效能問題",
        }
        records = [
            theme_record(
                source_theme_id="negative_001::performance_and_lag",
                batch_id="negative_001",
                bucket="negative",
                theme_id="performance_and_lag",
                area="performance",
                evidence=[shared_evidence],
            ),
            theme_record(
                source_theme_id="mixed_or_uncertain_001::mobile_performance_and_lag",
                batch_id="mixed_or_uncertain_001",
                bucket="mixed_or_uncertain",
                theme_id="mobile_performance_and_lag",
                area="performance",
                evidence=[shared_evidence],
            ),
        ]

        result = consolidate(records, taxonomy)

        self.assertEqual(len(result["mappings"]), 2)
        self.assertEqual(len(result["evidence"]), 2)
        self.assertEqual(len(result["themes"]), 1)
        summary = result["themes"][0]
        self.assertEqual(summary["canonical_theme_id"], "performance_stability")
        self.assertEqual(summary["source_theme_count"], 2)
        self.assertEqual(summary["batch_count"], 2)
        self.assertEqual(summary["evidence_count"], 2)
        self.assertEqual(summary["unique_review_count"], 1)
        self.assertIn("not full-corpus prevalence", summary["counting_boundary"])


if __name__ == "__main__":
    unittest.main()
