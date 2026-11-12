import unittest

from src.analysis.link_themes_to_product_updates import (
    build_theme_record,
    classify_review_timing,
    count_evidence_around_release,
    score_release_candidate,
)


class LinkThemesToProductUpdatesTests(unittest.TestCase):
    def test_build_theme_record_extracts_dates_and_text(self):
        theme = {
            "theme_id": "slow_mobile_performance",
            "theme_name_zh": "行動版速度慢",
            "summary_zh": "Android app loading is slow.",
            "affected_area": "performance",
            "severity": "high",
            "suggested_action_zh": "改善載入速度。",
            "evidence": [
                {
                    "review_created_at": "2026-05-01T00:00:00+00:00",
                    "quote": "very slow loading",
                    "reason_zh": "指出效能問題。",
                },
                {
                    "review_created_at": "2026-05-10T00:00:00+00:00",
                    "quote": "mobile app lags",
                    "reason_zh": "指出卡頓。",
                },
            ],
        }

        record = build_theme_record("negative_001", "negative", theme)

        self.assertEqual(record["first_evidence_at"], "2026-05-01T00:00:00+00:00")
        self.assertEqual(record["last_evidence_at"], "2026-05-10T00:00:00+00:00")
        self.assertEqual(record["evidence_count"], 2)
        self.assertIn("slow_mobile_performance", record["match_text"])
        self.assertIn("very slow loading", record["match_text"])

    def test_score_release_candidate_uses_specific_keywords_for_strong_match(self):
        theme = {
            "affected_area": "performance",
            "match_text": "slow mobile performance loading laggy crash",
        }
        release = {
            "release_id": "r1",
            "affected_area": "performance|mobile_app",
            "keywords": "performance|loading|mobile|laggy",
            "release_title": "Mobile performance improvements",
            "release_summary": "",
        }

        score = score_release_candidate(theme, release)

        self.assertEqual(score["area_overlap"], "performance")
        self.assertIn("loading", score["matched_keywords"].split("|"))
        self.assertIn("loading", score["matched_specific_keywords"].split("|"))
        self.assertEqual(score["match_level"], "strong")
        self.assertGreaterEqual(score["match_score"], 5)

    def test_score_release_candidate_returns_none_for_area_only_match(self):
        theme = {
            "affected_area": "performance",
            "match_text": "slow mobile performance loading laggy crash",
        }
        release = {
            "release_id": "r1",
            "affected_area": "performance",
            "keywords": "excel|powerpoint",
            "release_title": "File updates",
            "release_summary": "",
        }

        self.assertIsNone(score_release_candidate(theme, release))

    def test_score_release_candidate_returns_none_for_broad_keyword_only_match(self):
        theme = {
            "affected_area": "ai",
            "match_text": "ai agent mobile app access workspace",
        }
        release = {
            "release_id": "r1",
            "affected_area": "ai|mobile_app",
            "keywords": "ai|agent|agents|mobile|access|workspace",
            "release_title": "Meet the Notion Agents iOS app",
            "release_summary": "",
        }

        self.assertIsNone(score_release_candidate(theme, release))

    def test_score_release_candidate_requires_stronger_signal_without_area_overlap(self):
        theme = {
            "affected_area": "search",
            "match_text": "quick access search word",
        }
        release = {
            "release_id": "r1",
            "affected_area": "ai|editing",
            "keywords": "access|word|pdf",
            "release_title": "File updates",
            "release_summary": "",
        }

        self.assertIsNone(score_release_candidate(theme, release))

    def test_score_release_candidate_allows_area_plus_specific_title_signal(self):
        theme = {
            "affected_area": "mobile_app",
            "match_text": "mobile navigation home tab inbox swipe",
        }
        release = {
            "release_id": "r1",
            "affected_area": "mobile_app",
            "keywords": "mobile",
            "release_title": "A new home on mobile",
            "release_summary": "",
        }

        score = score_release_candidate(theme, release)

        self.assertEqual(score["area_overlap"], "mobile_app")
        self.assertEqual(score["matched_specific_keywords"], "")
        self.assertIn("home", score["matched_title_terms"].split("|"))
        self.assertEqual(score["match_level"], "medium")

    def test_classify_review_timing(self):
        self.assertEqual(
            classify_review_timing(2, 1)["resolution_hint"],
            "still_reported_after_release",
        )
        self.assertEqual(
            classify_review_timing(2, 0)["resolution_hint"],
            "possibly_addressed_no_later_evidence_in_sample",
        )
        self.assertEqual(
            classify_review_timing(0, 1)["resolution_hint"],
            "not_addressed_by_this_release",
        )

    def test_count_evidence_around_release(self):
        theme = {
            "evidence_dates": [
                "2026-05-01T00:00:00+00:00",
                "2026-05-20T00:00:00+00:00",
            ]
        }

        counts = count_evidence_around_release(theme, "2026-05-10")

        self.assertEqual(counts["pre_release_evidence_count"], 1)
        self.assertEqual(counts["post_release_evidence_count"], 1)


if __name__ == "__main__":
    unittest.main()