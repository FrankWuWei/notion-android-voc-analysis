import unittest

from src.analysis.repair_llm_outputs import (
    quote_review_key,
    repair_llm_output,
)


class RepairLLMOutputsTests(unittest.TestCase):
    def test_repair_llm_output_fixes_score_and_quote_from_source(self):
        llm_output = {
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
                            "score": "5",
                            "quote": "paraphrased quote",
                            "reason_zh": "指出速度問題。",
                        }
                    ],
                    "suggested_action_zh": "改善載入速度。",
                }
            ],
            "excluded_reviews": [],
        }
        source_reviews = {
            "r1": {
                "review_id": "r1",
                "score": "1",
                "review_text_for_model": "The app is too slow to use.",
            }
        }

        quote_reviews = {
            quote_review_key("negative_001", "slow_app", "r1"): {
                "action": "replace",
                "replacement_quote": "The app is too slow to use.",
            }
        }
        repaired, report = repair_llm_output(
            llm_output,
            source_reviews,
            quote_reviews,
        )

        evidence = repaired["themes"][0]["evidence"][0]
        self.assertEqual(evidence["score"], "1")
        self.assertEqual(evidence["quote"], "The app is too slow to use.")
        self.assertEqual(report["fixed_score"], 1)
        self.assertEqual(report["fixed_quote"], 1)
        self.assertEqual(report["reviewed_quote_replacement"], 1)

    def test_repair_llm_output_rejects_unreviewed_non_traceable_quote(self):
        llm_output = {
            "batch_id": "negative_001",
            "themes": [
                {
                    "theme_id": "slow_app",
                    "evidence": [
                        {"review_id": "r1", "score": "1", "quote": "paraphrase"}
                    ],
                }
            ],
            "excluded_reviews": [],
        }
        source_reviews = {
            "r1": {
                "review_id": "r1",
                "score": "1",
                "review_text_for_model": "The app is too slow to use.",
            }
        }

        with self.assertRaisesRegex(ValueError, "no semantic review decision"):
            repair_llm_output(llm_output, source_reviews)

    def test_repair_llm_output_drops_semantically_invalid_reviewed_quote(self):
        llm_output = {
            "batch_id": "negative_001",
            "themes": [
                {
                    "theme_id": "search_problem",
                    "evidence": [
                        {"review_id": "r1", "score": "1", "quote": "search is broken"}
                    ],
                }
            ],
            "excluded_reviews": [],
        }
        source_reviews = {
            "r1": {
                "review_id": "r1",
                "score": "1",
                "review_text_for_model": "The app is slow.",
            }
        }
        quote_reviews = {
            quote_review_key("negative_001", "search_problem", "r1"): {
                "action": "drop",
            }
        }

        repaired, report = repair_llm_output(
            llm_output,
            source_reviews,
            quote_reviews,
        )

        self.assertEqual(repaired["themes"], [])
        self.assertEqual(report["reviewed_quote_drop"], 1)
        self.assertEqual(report["dropped_evidence"], 1)
        self.assertEqual(report["dropped_themes"], 1)

    def test_repair_llm_output_drops_invalid_references_and_empty_themes(self):
        llm_output = {
            "batch_id": "negative_001",
            "sentiment_bucket": "negative",
            "analysis_language": "zh-Hant",
            "themes": [
                {
                    "theme_id": "invalid_theme",
                    "theme_name_zh": "無效",
                    "summary_zh": "無法追溯。",
                    "affected_area": "other",
                    "severity": "low",
                    "evidence": [{"review_id": "bad-id", "score": "1", "quote": "x"}],
                    "suggested_action_zh": "移除。",
                }
            ],
            "excluded_reviews": [{"review_id": "bad-id", "reason": "unrelated"}],
        }

        repaired, report = repair_llm_output(llm_output, {})

        self.assertEqual(repaired["themes"], [])
        self.assertEqual(repaired["excluded_reviews"], [])
        self.assertEqual(report["dropped_evidence"], 1)
        self.assertEqual(report["dropped_themes"], 1)
        self.assertEqual(report["dropped_excluded"], 1)


if __name__ == "__main__":
    unittest.main()
