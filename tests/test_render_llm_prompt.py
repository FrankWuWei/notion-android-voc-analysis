import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.render_llm_prompt import (
    load_jsonl_batch,
    render_prompt,
)


class LoadJsonlBatchTests(unittest.TestCase):
    def test_load_jsonl_batch_selects_matching_batch_id(self):
        batches = [
            {"batch_id": "negative_001", "reviews": []},
            {"batch_id": "negative_002", "reviews": []},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            batch_path = Path(temp_dir) / "batches.jsonl"
            batch_path.write_text(
                "\n".join(json.dumps(batch) for batch in batches) + "\n",
                encoding="utf-8",
            )

            result = load_jsonl_batch(batch_path, "negative_002")

        self.assertEqual(result["batch_id"], "negative_002")

    def test_load_jsonl_batch_raises_when_batch_id_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_path = Path(temp_dir) / "batches.jsonl"
            batch_path.write_text('{"batch_id": "negative_001"}\n', encoding="utf-8")

            with self.assertRaises(ValueError):
                load_jsonl_batch(batch_path, "missing")


class RenderPromptTests(unittest.TestCase):
    def test_render_prompt_replaces_template_placeholders(self):
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
            "reviews": [{"review_id": "r1", "review_text_for_model": "Too slow"}],
        }
        output_schema = {"themes": [{"theme_id": "string"}]}

        rendered = render_prompt(template, batch, output_schema)

        self.assertIn("Batch: negative_001", rendered)
        self.assertIn('"review_id": "r1"', rendered)
        self.assertIn('"themes"', rendered)
        self.assertNotIn("{{", rendered)


if __name__ == "__main__":
    unittest.main()
