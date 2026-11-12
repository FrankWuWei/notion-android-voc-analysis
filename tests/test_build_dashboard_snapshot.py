import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.analysis.build_dashboard_snapshot import build_dashboard_snapshot


class BuildDashboardSnapshotTests(unittest.TestCase):
    def write_csv(self, path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_builds_traceable_frontend_snapshot_from_final_outputs(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            reviews = root / "reviews.csv"
            raw_reviews = root / "raw_reviews.csv"
            trends = root / "trends.csv"
            evidence = root / "evidence.csv"
            rules = root / "rules.json"
            output = root / "dashboardSnapshot.ts"
            llm_manifest = root / "manifest.json"
            llm_batch_dir = root / "llm_inputs"
            llm_output_dir = root / "llm_outputs"
            repair_report = root / "repair_report.json"

            self.write_csv(
                raw_reviews,
                [
                    {"review_id": "raw-review-1"},
                    {"review_id": "raw-review-2"},
                    {"review_id": "raw-review-3"},
                ],
            )
            self.write_csv(
                reviews,
                [
                    {"review_id": "raw-review-1", "review_created_at": "2026-05-17T00:00:00+00:00", "sentiment_bucket": "negative"},
                    {"review_id": "raw-review-2", "review_created_at": "2026-05-18T00:00:00+00:00", "sentiment_bucket": "positive"},
                ],
            )
            self.write_csv(
                trends,
                [
                    {
                        "candidate_id": "candidate-1",
                        "theme_id": "ai_controls",
                        "theme_name_zh": "AI 控制問題",
                        "theme_affected_area": "ai",
                        "release_date": "2026-05-07",
                        "release_title": "Plan Mode",
                        "release_scope": "general_product_release",
                        "window_days": "28",
                        "pre_eligible_count": "20",
                        "post_eligible_count": "21",
                        "pre_match_count": "2",
                        "post_match_count": "1",
                        "pre_match_rate": "0.1",
                        "post_match_rate": "0.047619",
                        "rate_change_percentage_points": "-5.2381",
                        "observation_status": "limited_post_evidence",
                    }
                ],
            )
            self.write_csv(
                evidence,
                [
                    {
                        "candidate_id": "candidate-1",
                        "theme_id": "ai_controls",
                        "period": "post",
                        "matched_phrases": "forced to use ai",
                        "review_id": "raw-review-1",
                        "review_created_at": "2026-05-17T00:00:00+00:00",
                        "app_version": "0.6.3870",
                        "score": "1",
                        "review_text_clean": "AI was forced on me.",
                    }
                ],
            )
            rules.write_text('{"rules": [{"candidate_id": "candidate-1", "match_any_phrases": ["forced to use ai"]}]}', encoding="utf-8")

            llm_batch_dir.mkdir()
            llm_output_dir.mkdir()
            llm_manifest.write_text(
                '{"buckets": {"positive": {"source_rows": 1, "selected_rows": 0, "batch_count": 0, "selection_strategy": "top_500_by_thumbs_up_then_text_length"}, "negative": {"source_rows": 1, "selected_rows": 1, "batch_count": 1, "selection_strategy": "all"}}}',
                encoding="utf-8",
            )
            (llm_batch_dir / "negative_llm_batches.jsonl").write_text(
                '{"batch_id":"negative_001","sentiment_bucket":"negative","reviews":[{"review_id":"raw-review-1","score":"1","review_text_for_model":"AI was forced on me."}]}\n',
                encoding="utf-8",
            )
            (llm_output_dir / "negative_001_output.json").write_text(
                '{"batch_id":"negative_001","sentiment_bucket":"negative","analysis_language":"zh-Hant","themes":[{"evidence":[{"review_id":"raw-review-1","score":"1","quote":"AI was forced on me."}]}],"excluded_reviews":[]}',
                encoding="utf-8",
            )
            repair_report.write_text(
                '{"batches":1,"fixed_score":1,"fixed_quote":2,"dropped_evidence":3,"dropped_excluded":0}',
                encoding="utf-8",
            )

            snapshot = build_dashboard_snapshot(
                reviews,
                trends,
                evidence,
                rules,
                output,
                llm_manifest_path=llm_manifest,
                llm_batch_dir=llm_batch_dir,
                llm_output_dir=llm_output_dir,
                repair_report_path=repair_report,
                raw_reviews_path=raw_reviews,
            )

            self.assertEqual(snapshot["trends"][0]["id"], "candidate-1")
            self.assertEqual(snapshot["evidence"][0]["reviewId"], "raw-review-1")
            self.assertEqual(snapshot["metadata"]["evidenceCount"], 1)
            self.assertEqual(snapshot["llmQuality"]["selectedReviewCount"], 1)
            self.assertEqual(snapshot["llmQuality"]["batchCount"], 1)
            self.assertEqual(snapshot["llmQuality"]["themeCount"], 1)
            self.assertEqual(snapshot["llmQuality"]["evidenceCount"], 1)
            self.assertEqual(snapshot["llmQuality"]["validationErrorCount"], 0)
            self.assertEqual(snapshot["llmQuality"]["fixedQuoteCount"], 2)
            self.assertEqual(
                snapshot["reviewSummary"],
                {"rawRows": 3, "cleanedRows": 2, "llmSelectedRows": 1},
            )
            self.assertEqual(
                snapshot["sentimentBuckets"],
                [
                    {
                        "id": "positive",
                        "sourceRows": 1,
                        "selectedRows": 0,
                        "selectionStrategy": "top_500_by_thumbs_up_then_text_length",
                    },
                    {
                        "id": "negative",
                        "sourceRows": 1,
                        "selectedRows": 1,
                        "selectionStrategy": "all",
                    },
                ],
            )
            self.assertEqual(snapshot["portfolioMetrics"][1]["value"], "1")
            self.assertIn("export const dashboardSnapshot", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()