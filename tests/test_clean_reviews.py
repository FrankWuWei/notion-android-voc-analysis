import unittest

from src.preprocessing.clean_reviews import clean_rows, normalize_text


class NormalizeTextTests(unittest.TestCase):
    def test_normalize_text_unescapes_html_and_collapses_whitespace(self):
        text = "  Notion&nbsp;lags\n\n a   lot &amp; sync fails  "

        result = normalize_text(text)

        self.assertEqual(result, "Notion lags a lot & sync fails")

    def test_normalize_text_preserves_negation_and_punctuation(self):
        text = " can't sync!!! not good "

        result = normalize_text(text)

        self.assertEqual(result, "can't sync!!! not good")


class CleanRowsTests(unittest.TestCase):
    def test_clean_rows_drops_empty_too_short_and_duplicate_reviews(self):
        rows = [
            {
                "review_id": "r1",
                "score": "1",
                "review_text": "  Notion&nbsp;lags\nbadly  ",
            },
            {"review_id": "empty", "score": "5", "review_text": "   "},
            {"review_id": "short", "score": "5", "review_text": "ok"},
            {"review_id": "r1", "score": "2", "review_text": "duplicate"},
        ]

        cleaned, stats = clean_rows(rows, min_text_chars=3, max_model_chars=100)

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["review_id"], "r1")
        self.assertEqual(cleaned[0]["review_text_clean"], "Notion lags badly")
        self.assertEqual(stats["dropped_empty_text"], 1)
        self.assertEqual(stats["dropped_too_short_text"], 1)
        self.assertEqual(stats["dropped_duplicate_review_id"], 1)

    def test_clean_rows_keeps_auxiliary_columns_and_adds_model_text(self):
        rows = [
            {
                "review_id": "r1",
                "score": "3",
                "thumbs_up_count": "7",
                "review_created_at": "2026-01-01T00:00:00+00:00",
                "review_text": "Slow sync but useful",
                "app_version": "0.1",
            }
        ]

        cleaned, _ = clean_rows(rows, min_text_chars=3, max_model_chars=100)

        self.assertEqual(cleaned[0]["score"], "3")
        self.assertEqual(cleaned[0]["thumbs_up_count"], "7")
        self.assertEqual(cleaned[0]["review_created_at"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(cleaned[0]["app_version"], "0.1")
        self.assertEqual(cleaned[0]["review_text_for_model"], "Slow sync but useful")
        self.assertEqual(cleaned[0]["review_text_was_truncated"], "false")

    def test_clean_rows_truncates_only_model_text_when_review_is_long(self):
        rows = [{"review_id": "r1", "review_text": "abcdef"}]

        cleaned, stats = clean_rows(rows, min_text_chars=3, max_model_chars=4)

        self.assertEqual(cleaned[0]["review_text_clean"], "abcdef")
        self.assertEqual(cleaned[0]["review_text_for_model"], "abcd")
        self.assertEqual(cleaned[0]["review_text_was_truncated"], "true")
        self.assertEqual(stats["truncated_for_model"], 1)


if __name__ == "__main__":
    unittest.main()
