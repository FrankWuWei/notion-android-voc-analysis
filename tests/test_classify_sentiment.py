import unittest

from src.analysis.classify_sentiment import (
    apply_sentiment_results,
    assign_sentiment_bucket,
)


class AssignSentimentBucketTests(unittest.TestCase):
    def test_assigns_positive_for_high_confidence_positive_non_conflicting_review(self):
        result = assign_sentiment_bucket("POSITIVE", 0.95, "5")

        self.assertEqual(result, "positive")

    def test_assigns_negative_for_high_confidence_negative_non_conflicting_review(self):
        result = assign_sentiment_bucket("NEGATIVE", 0.91, "1")

        self.assertEqual(result, "negative")

    def test_assigns_mixed_or_uncertain_for_low_confidence_prediction(self):
        result = assign_sentiment_bucket("POSITIVE", 0.79, "5")

        self.assertEqual(result, "mixed_or_uncertain")

    def test_assigns_mixed_or_uncertain_for_three_star_review(self):
        result = assign_sentiment_bucket("NEGATIVE", 0.99, "3")

        self.assertEqual(result, "mixed_or_uncertain")

    def test_assigns_mixed_or_uncertain_for_label_and_rating_conflict(self):
        result = assign_sentiment_bucket("NEGATIVE", 0.99, "5")

        self.assertEqual(result, "mixed_or_uncertain")


class ApplySentimentResultsTests(unittest.TestCase):
    def test_adds_sentiment_columns_to_rows(self):
        rows = [
            {"review_id": "r1", "score": "5", "review_text_for_model": "Great app"},
            {"review_id": "r2", "score": "1", "review_text_for_model": "Too slow"},
        ]
        results = [
            {"label": "POSITIVE", "score": 0.98},
            {"label": "NEGATIVE", "score": 0.97},
        ]

        enriched = apply_sentiment_results(rows, results, confidence_threshold=0.8)

        self.assertEqual(enriched[0]["sentiment_label"], "POSITIVE")
        self.assertEqual(enriched[0]["sentiment_score"], "0.980000")
        self.assertEqual(enriched[0]["sentiment_bucket"], "positive")
        self.assertEqual(enriched[1]["sentiment_label"], "NEGATIVE")
        self.assertEqual(enriched[1]["sentiment_bucket"], "negative")


if __name__ == "__main__":
    unittest.main()
