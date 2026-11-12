import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.enrich_llm_outputs import (
    DEFAULT_METADATA_FIELDS,
    enrich_llm_output,
    enrich_output_file,
    load_review_metadata,
)


class LoadReviewMetadataTests(unittest.TestCase):
    def test_load_review_metadata_indexes_reviews_by_review_id(self):
        batch = {
            "batch_id": "negative_001",
            "reviews": [
                {
                    "review_id": "r1",
                    "review_created_at": "2026-02-24T00:22:33+00:00",
                    "app_version": "0.6.1",
                    "thumbs_up_count": 7,
                    "sentiment_label": "NEGATIVE",
                    "sentiment_score": 0.98,
                    "sentiment_bucket": "negative",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            batch_path = Path(temp_dir) / "negative_llm_batches.jsonl"
            batch_path.write_text(json.dumps(batch) + "\n", encoding="utf-8")

            metadata = load_review_metadata([batch_path], DEFAULT_METADATA_FIELDS)

        self.assertEqual(
            metadata["r1"]["review_created_at"],
            "2026-02-24T00:22:33+00:00",
        )
        self.assertEqual(metadata["r1"]["app_version"], "0.6.1")
        self.assertEqual(metadata["r1"]["thumbs_up_count"], 7)


class EnrichLlmOutputTests(unittest.TestCase):
    def test_enrich_llm_output_adds_metadata_to_evidence_and_excluded_reviews(self):
        llm_output = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "analysis_language": "zh-Hant",
            "themes": [
                {
                    "theme_id": "slow_app",
                    "evidence": [
                        {
                            "review_id": "r1",
                            "score": "1",
                            "quote": "Very slow",
                            "reason_zh": "抱怨速度慢",
                        }
                    ],
                }
            ],
            "excluded_reviews": [{"review_id": "r2", "reason": "non_english"}],
        }
        metadata = {
            "r1": {
                "review_created_at": "2026-02-24T00:22:33+00:00",
                "app_version": "0.6.1",
                "thumbs_up_count": 7,
            },
            "r2": {
                "review_created_at": "2026-01-10T10:00:00+00:00",
                "app_version": "",
                "thumbs_up_count": 0,
            },
        }

        enriched = enrich_llm_output(llm_output, metadata, DEFAULT_METADATA_FIELDS)

        evidence = enriched["themes"][0]["evidence"][0]
        self.assertEqual(evidence["review_created_at"], "2026-02-24T00:22:33+00:00")
        self.assertEqual(evidence["app_version"], "0.6.1")
        self.assertEqual(evidence["thumbs_up_count"], 7)
        self.assertEqual(evidence["quote"], "Very slow")
        self.assertNotIn("review_created_at", llm_output["themes"][0]["evidence"][0])

        excluded = enriched["excluded_reviews"][0]
        self.assertEqual(excluded["review_created_at"], "2026-01-10T10:00:00+00:00")
        self.assertEqual(excluded["reason"], "non_english")

    def test_enrich_llm_output_raises_when_review_id_is_missing_from_metadata(self):
        llm_output = {
            "batch_id": "negative_001",
            "themes": [{"theme_id": "slow_app", "evidence": [{"review_id": "missing"}]}],
            "excluded_reviews": [],
        }

        with self.assertRaises(ValueError):
            enrich_llm_output(llm_output, {}, DEFAULT_METADATA_FIELDS)


class EnrichOutputFileTests(unittest.TestCase):
    def test_enrich_output_file_writes_new_json_without_changing_input_file(self):
        llm_output = {
            "batch_id": "negative_001",
            "themes": [{"theme_id": "slow_app", "evidence": [{"review_id": "r1"}]}],
            "excluded_reviews": [],
        }
        metadata = {
            "r1": {
                "review_created_at": "2026-02-24T00:22:33+00:00",
                "app_version": "0.6.1",
                "thumbs_up_count": 7,
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "negative_001_output.json"
            output_path = Path(temp_dir) / "negative_001_output.enriched.json"
            input_path.write_text(
                json.dumps(llm_output, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            original_text = input_path.read_text(encoding="utf-8")

            enrich_output_file(input_path, output_path, metadata, DEFAULT_METADATA_FIELDS)

            enriched = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(input_path.read_text(encoding="utf-8"), original_text)
            self.assertEqual(
                enriched["themes"][0]["evidence"][0]["review_created_at"],
                "2026-02-24T00:22:33+00:00",
            )


if __name__ == "__main__":
    unittest.main()
