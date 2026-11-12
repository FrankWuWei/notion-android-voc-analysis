import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.build_openai_batch_requests import (
    LLM_OUTPUT_JSON_SCHEMA,
    build_batch_request,
    write_batch_requests,
)


class BuildOpenAIBatchRequestsTests(unittest.TestCase):
    def test_default_batch_request_omits_temperature(self):
        template = (
            "Batch: {{batch_id}}\n"
            "Bucket: {{sentiment_bucket}}\n"
            "Count: {{review_count}}\n"
            "Reviews:\n{{reviews_json}}\n"
            "Schema:\n{{output_schema_json}}\n"
        )
        batch = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "review_count": 1,
            "reviews": [{"review_id": "r1", "score": "1"}],
        }

        request = build_batch_request(
            batch=batch,
            template=template,
            model="gpt-5.4-mini",
        )

        self.assertNotIn("temperature", request["body"])
    def test_build_batch_request_uses_responses_endpoint_and_structured_output(self):
        template = (
            "Batch: {{batch_id}}\n"
            "Bucket: {{sentiment_bucket}}\n"
            "Count: {{review_count}}\n"
            "Reviews:\n{{reviews_json}}\n"
            "Schema:\n{{output_schema_json}}\n"
        )
        batch = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "review_count": 1,
            "reviews": [
                {
                    "review_id": "r1",
                    "score": "1",
                    "review_text_for_model": "The app is too slow.",
                }
            ],
        }

        request = build_batch_request(
            batch=batch,
            template=template,
            model="gpt-5.4-mini",
            temperature=0.2,
            reasoning_effort="low",
            max_output_tokens=12000,
        )

        self.assertEqual(request["custom_id"], "negative_001")
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["url"], "/v1/responses")
        self.assertEqual(request["body"]["model"], "gpt-5.4-mini")
        self.assertIn("negative_001", request["body"]["input"])
        self.assertIn('"review_id": "r1"', request["body"]["input"])
        self.assertEqual(request["body"]["reasoning"], {"effort": "low"})
        self.assertEqual(request["body"]["max_output_tokens"], 12000)
        self.assertEqual(request["body"]["text"]["format"]["type"], "json_schema")
        self.assertEqual(request["body"]["text"]["format"]["name"], "voc_theme_analysis")
        self.assertTrue(request["body"]["text"]["format"]["strict"])
        self.assertEqual(
            request["body"]["text"]["format"]["schema"],
            LLM_OUTPUT_JSON_SCHEMA,
        )

    def test_write_batch_requests_writes_one_request_per_source_batch(self):
        template = (
            "Batch: {{batch_id}}\n"
            "Bucket: {{sentiment_bucket}}\n"
            "Count: {{review_count}}\n"
            "Reviews:\n{{reviews_json}}\n"
            "Schema:\n{{output_schema_json}}\n"
        )
        batches = [
            {
                "batch_id": "negative_001",
                "sentiment_bucket": "negative",
                "review_count": 1,
                "reviews": [{"review_id": "r1", "score": "1"}],
            },
            {
                "batch_id": "negative_002",
                "sentiment_bucket": "negative",
                "review_count": 1,
                "reviews": [{"review_id": "r2", "score": "2"}],
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "negative_llm_batches.jsonl"
            output_path = Path(temp_dir) / "openai_batch_requests.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(batch) for batch in batches) + "\n",
                encoding="utf-8",
            )

            written = write_batch_requests(
                batch_paths=[input_path],
                template=template,
                output_path=output_path,
                model="gpt-5.4-mini",
                temperature=0.2,
                reasoning_effort=None,
                max_output_tokens=None,
            )

            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(written, 2)
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["custom_id"], "negative_001")
        self.assertEqual(json.loads(lines[1])["custom_id"], "negative_002")


if __name__ == "__main__":
    unittest.main()

