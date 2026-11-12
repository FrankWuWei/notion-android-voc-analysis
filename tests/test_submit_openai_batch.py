import io
import unittest
import urllib.error

from src.analysis.submit_openai_batch import format_http_error


class SubmitOpenAIBatchTests(unittest.TestCase):
    def test_format_http_error_includes_api_error_body(self):
        error = urllib.error.HTTPError(
            url="https://api.openai.com/v1/batches",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"error":{"message":"invalid batch endpoint"}}'),
        )

        message = format_http_error(error, "POST", "/batches")

        self.assertIn("OpenAI API HTTP 400 Bad Request", message)
        self.assertIn("POST /batches", message)
        self.assertIn("invalid batch endpoint", message)


if __name__ == "__main__":
    unittest.main()
