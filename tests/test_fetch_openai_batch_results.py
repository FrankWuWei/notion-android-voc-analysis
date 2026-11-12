import json
import tempfile
import unittest
from pathlib import Path

from src.analysis.fetch_openai_batch_results import (
    describe_missing_batch_output,
    extract_response_text,
    parse_batch_result_line,
    write_result_outputs,
)


class FetchOpenAIBatchResultsTests(unittest.TestCase):
    def test_describe_missing_batch_output_includes_error_file_id(self):
        batch = {
            "id": "batch_123",
            "status": "completed",
            "error_file_id": "file-error",
            "request_counts": {"total": 23, "completed": 0, "failed": 23},
        }

        message = describe_missing_batch_output(batch)

        self.assertIn("status=completed", message)
        self.assertIn("error_file_id=file-error", message)
        self.assertIn("failed=23", message)
    def test_parse_batch_result_line_reads_output_text_shortcut(self):
        llm_output = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "analysis_language": "zh-Hant",
            "themes": [],
            "excluded_reviews": [],
        }
        line = json.dumps(
            {
                "custom_id": "negative_001",
                "response": {
                    "status_code": 200,
                    "body": {"output_text": json.dumps(llm_output, ensure_ascii=False)},
                },
            }
        )

        custom_id, parsed = parse_batch_result_line(line)

        self.assertEqual(custom_id, "negative_001")
        self.assertEqual(parsed, llm_output)

    def test_extract_response_text_reads_message_content(self):
        body = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"batch_id":"negative_001"}',
                        }
                    ],
                }
            ]
        }

        self.assertEqual(extract_response_text(body), '{"batch_id":"negative_001"}')

    def test_write_result_outputs_writes_one_json_file_per_batch_result(self):
        result = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "analysis_language": "zh-Hant",
            "themes": [],
            "excluded_reviews": [],
        }
        line = json.dumps(
            {
                "custom_id": "negative_001",
                "response": {
                    "status_code": 200,
                    "body": {"output_text": json.dumps(result, ensure_ascii=False)},
                },
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "batch_output.jsonl"
            output_dir = Path(temp_dir) / "outputs"
            input_path.write_text(line + "\n", encoding="utf-8")

            written = write_result_outputs(input_path, output_dir)

            output_path = output_dir / "negative_001_output.json"
            parsed = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(written, [output_path])
        self.assertEqual(parsed["batch_id"], "negative_001")


if __name__ == "__main__":
    unittest.main()

