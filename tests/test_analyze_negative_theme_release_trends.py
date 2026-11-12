import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.analysis.analyze_negative_theme_release_trends import (
    analyze_negative_theme_release_trends,
    build_trend_rows,
    classify_observation,
    review_matches_rule,
)


class AnalyzeNegativeThemeReleaseTrendsTests(unittest.TestCase):
    def make_review(self, review_id: str, created_at: str, text: str) -> dict:
        return {
            "review_id": review_id,
            "review_created_at": created_at,
            "review_text_clean": text,
            "sentiment_bucket": "negative",
            "app_version": "0.6.3000",
            "score": "1",
        }

    def make_candidate(self) -> dict:
        return {
            "candidate_id": "candidate-1",
            "theme_id": "login_problem",
            "theme_name_zh": "登入問題",
            "theme_affected_area": "account",
            "release_id": "release-1",
            "release_date": "2026-05-13",
            "release_title": "General release",
        }

    def make_rules(self) -> dict:
        return {
            "release_scope": "general_product_release",
            "window_days": 28,
            "minimum_eligible_reviews": 20,
            "rules": [
                {
                    "candidate_id": "candidate-1",
                    "theme_id": "login_problem",
                    "match_any_phrases": ["log in", "locked out"],
                }
            ],
        }

    def test_review_matches_rule_case_insensitively(self):
        matched, phrases = review_matches_rule(
            "I cannot LOG IN after the update.",
            ["log in", "locked out"],
        )

        self.assertTrue(matched)
        self.assertEqual(phrases, ["log in"])

    def test_classify_observation_prioritizes_incomplete_post_window(self):
        status = classify_observation(
            pre_eligible_count=50,
            post_eligible_count=50,
            post_match_count=5,
            pre_window_complete=True,
            post_window_complete=False,
        )

        self.assertEqual(status, "incomplete_post_window")

    def test_build_trend_rows_counts_window_matches_and_emits_evidence(self):
        reviews = [
            self.make_review("pre-match", "2026-04-15T00:00:00+00:00", "Cannot log in"),
            self.make_review("post-match", "2026-05-20T00:00:00+00:00", "Still locked out"),
        ]
        reviews.extend(
            self.make_review(
                f"pre-{index}",
                "2026-04-25T00:00:00+00:00",
                "The app is slow.",
            )
            for index in range(19)
        )
        reviews.extend(
            self.make_review(
                f"post-{index}",
                "2026-05-25T00:00:00+00:00",
                "The app is slow.",
            )
            for index in range(19)
        )
        reviews.append(
            self.make_review(
                "after-window",
                "2026-06-10T00:00:00+00:00",
                "The app is slow.",
            )
        )

        rows, evidence = build_trend_rows(
            reviews=reviews,
            candidates=[self.make_candidate()],
            rules=self.make_rules(),
        )

        self.assertEqual(rows[0]["pre_eligible_count"], 20)
        self.assertEqual(rows[0]["post_eligible_count"], 20)
        self.assertEqual(rows[0]["pre_match_count"], 1)
        self.assertEqual(rows[0]["post_match_count"], 1)
        self.assertEqual(rows[0]["observation_status"], "limited_post_evidence")
        self.assertEqual([item["period"] for item in evidence], ["pre", "post"])

    def test_analyze_writes_trend_evidence_and_summary_outputs(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            reviews_path = root / "reviews.csv"
            candidates_path = root / "candidates.csv"
            rules_path = root / "rules.json"
            output_path = root / "trends.csv"
            evidence_output_path = root / "evidence.csv"
            summary_output_path = root / "summary.json"
            review = self.make_review(
                "review-1",
                "2026-05-20T00:00:00+00:00",
                "I am locked out.",
            )
            with reviews_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=review.keys())
                writer.writeheader()
                writer.writerow(review)
            candidate = self.make_candidate()
            with candidates_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=candidate.keys())
                writer.writeheader()
                writer.writerow(candidate)
            rules_path.write_text(json.dumps(self.make_rules()), encoding="utf-8")

            summary = analyze_negative_theme_release_trends(
                reviews_path=reviews_path,
                candidates_path=candidates_path,
                rules_path=rules_path,
                output_path=output_path,
                evidence_output_path=evidence_output_path,
                summary_output_path=summary_output_path,
            )

            self.assertEqual(summary["trend_row_count"], 1)
            self.assertEqual(summary["evidence_row_count"], 1)
            self.assertTrue(output_path.exists())
            self.assertTrue(evidence_output_path.exists())
            self.assertEqual(
                json.loads(summary_output_path.read_text(encoding="utf-8")),
                summary,
            )


if __name__ == "__main__":
    unittest.main()
