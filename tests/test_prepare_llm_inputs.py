import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.prepare_llm_inputs import (
    LLM_FIELDS,
    build_batches,
    prepare_records,
    select_rows_for_bucket,
    write_jsonl_batches,
)


class PrepareRecordsTests(unittest.TestCase):
    def test_prepare_records_keeps_only_llm_input_fields(self):
        rows = [
            {
                "review_id": "r1",
                "score": "5",
                "review_created_at": "2026-01-01T00:00:00+00:00",
                "app_version": "1.0",
                "thumbs_up_count": "7",
                "sentiment_label": "POSITIVE",
                "sentiment_score": "0.990000",
                "sentiment_bucket": "positive",
                "review_text_for_model": "Great app",
                "user_name": "not needed",
            }
        ]

        records = prepare_records(rows)

        self.assertEqual(set(records[0].keys()), set(LLM_FIELDS))
        self.assertNotIn("user_name", records[0])
        self.assertEqual(records[0]["review_id"], "r1")


class SelectRowsForBucketTests(unittest.TestCase):
    def test_select_rows_for_positive_uses_representative_limit(self):
        rows = [
            {
                "review_id": "low",
                "sentiment_bucket": "positive",
                "thumbs_up_count": "0",
                "review_text_char_count": "20",
                "review_created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "review_id": "high",
                "sentiment_bucket": "positive",
                "thumbs_up_count": "9",
                "review_text_char_count": "10",
                "review_created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "review_id": "medium",
                "sentiment_bucket": "positive",
                "thumbs_up_count": "3",
                "review_text_char_count": "100",
                "review_created_at": "2026-01-01T00:00:00+00:00",
            },
        ]

        selected, strategy = select_rows_for_bucket(
            rows,
            "positive",
            positive_limit=2,
        )

        self.assertEqual([row["review_id"] for row in selected], ["high", "medium"])
        self.assertEqual(strategy, "top_2_by_thumbs_up_then_text_length")

    def test_select_rows_for_negative_keeps_all_rows(self):
        rows = [
            {"review_id": "r1", "sentiment_bucket": "negative"},
            {"review_id": "r2", "sentiment_bucket": "negative"},
        ]

        selected, strategy = select_rows_for_bucket(rows, "negative")

        self.assertEqual(len(selected), 2)
        self.assertEqual(strategy, "all")


class BuildBatchesTests(unittest.TestCase):
    def test_build_batches_groups_records_with_metadata(self):
        rows = [
            {
                "review_id": "r1",
                "score": "1",
                "review_created_at": "2026-01-01T00:00:00+00:00",
                "app_version": "",
                "thumbs_up_count": "0",
                "sentiment_label": "NEGATIVE",
                "sentiment_score": "0.950000",
                "sentiment_bucket": "negative",
                "review_text_for_model": "Too slow",
            },
            {
                "review_id": "r2",
                "score": "1",
                "review_created_at": "2026-01-02T00:00:00+00:00",
                "app_version": "",
                "thumbs_up_count": "1",
                "sentiment_label": "NEGATIVE",
                "sentiment_score": "0.970000",
                "sentiment_bucket": "negative",
                "review_text_for_model": "Crashes",
            },
        ]

        batches = build_batches(
            rows,
            bucket="negative",
            batch_size=1,
            source_file="source.csv",
            selection_strategy="all",
        )

        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0]["batch_id"], "negative_001")
        self.assertEqual(batches[0]["review_count"], 1)
        self.assertEqual(batches[0]["reviews"][0]["review_id"], "r1")

    def test_write_jsonl_batches_writes_one_batch_per_line(self):
        batches = [
            {
                "batch_id": "negative_001",
                "sentiment_bucket": "negative",
                "review_count": 1,
                "reviews": [{"review_id": "r1"}],
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "negative.jsonl"
            write_jsonl_batches(batches, output_path)

            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["batch_id"], "negative_001")


if __name__ == "__main__":
    unittest.main()
