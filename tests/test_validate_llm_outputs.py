import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.validate_llm_outputs import validate_output_dir


class ValidateLLMOutputsTests(unittest.TestCase):
    def test_validate_output_dir_accepts_matching_review_references(self):
        batch = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "review_count": 1,
            "reviews": [
                {
                    "review_id": "r1",
                    "score": "1",
                    "review_text_for_model": "The app is too slow to use.",
                }
            ],
        }
        output = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "analysis_language": "zh-Hant",
            "themes": [
                {
                    "theme_id": "slow_app",
                    "theme_name_zh": "速度慢",
                    "summary_zh": "使用者覺得 app 太慢。",
                    "affected_area": "performance",
                    "severity": "high",
                    "evidence": [
                        {
                            "review_id": "r1",
                            "score": "1",
                            "quote": "too slow",
                            "reason_zh": "指出速度問題。",
                        }
                    ],
                    "suggested_action_zh": "改善載入速度。",
                }
            ],
            "excluded_reviews": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = Path(temp_dir) / "batches"
            output_dir = Path(temp_dir) / "outputs"
            batch_dir.mkdir()
            output_dir.mkdir()
            (batch_dir / "negative_llm_batches.jsonl").write_text(
                json.dumps(batch) + "\n",
                encoding="utf-8",
            )
            (output_dir / "negative_001_output.json").write_text(
                json.dumps(output, ensure_ascii=False),
                encoding="utf-8",
            )

            result = validate_output_dir(batch_dir, output_dir, require_all=True)

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["total_evidence"], 1)
        self.assertEqual(result["total_themes"], 1)

    def test_validate_output_dir_reports_bad_quote(self):
        batch = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "review_count": 1,
            "reviews": [
                {
                    "review_id": "r1",
                    "score": "1",
                    "review_text_for_model": "The app is too slow to use.",
                }
            ],
        }
        output = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "analysis_language": "zh-Hant",
            "themes": [
                {
                    "theme_id": "slow_app",
                    "theme_name_zh": "速度慢",
                    "summary_zh": "使用者覺得 app 太慢。",
                    "affected_area": "performance",
                    "severity": "high",
                    "evidence": [
                        {
                            "review_id": "r1",
                            "score": "1",
                            "quote": "not in the source text",
                            "reason_zh": "指出速度問題。",
                        }
                    ],
                    "suggested_action_zh": "改善載入速度。",
                }
            ],
            "excluded_reviews": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = Path(temp_dir) / "batches"
            output_dir = Path(temp_dir) / "outputs"
            batch_dir.mkdir()
            output_dir.mkdir()
            (batch_dir / "negative_llm_batches.jsonl").write_text(
                json.dumps(batch) + "\n",
                encoding="utf-8",
            )
            (output_dir / "negative_001_output.json").write_text(
                json.dumps(output, ensure_ascii=False),
                encoding="utf-8",
            )

            result = validate_output_dir(batch_dir, output_dir, require_all=True)

        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("quote not found", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
