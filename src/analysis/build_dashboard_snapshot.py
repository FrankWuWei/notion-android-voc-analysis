"""Build the static dashboard data module from final analysis artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

if __package__:
    from .validate_llm_outputs import validate_output_dir
else:
    from validate_llm_outputs import validate_output_dir


DEFAULT_RAW_REVIEWS = Path("data/raw/notion_android_reviews_google_play_2025_onward_en_us.csv")
DEFAULT_REVIEWS = Path("data/processed/reviews_with_sentiment_2025_onward_en_us.csv")
DEFAULT_TRENDS = Path("outputs/tables/negative_theme_release_trends.csv")
DEFAULT_EVIDENCE = Path("outputs/tables/negative_theme_release_trend_evidence.csv")
DEFAULT_RULES = Path("configs/negative_theme_monitoring_rules.json")
DEFAULT_LLM_MANIFEST = Path("data/processed/llm_inputs/manifest.json")
DEFAULT_LLM_BATCH_DIR = Path("data/processed/llm_inputs")
DEFAULT_LLM_OUTPUT_DIR = Path("outputs/reports/llm_batch_outputs_api_repaired_enriched")
DEFAULT_REPAIR_REPORT = Path("outputs/reports/llm_batch_outputs_api_repair_report.json")
DEFAULT_OUTPUT = Path("web/src/data/dashboardSnapshot.ts")
SENTIMENT_BUCKET_ORDER = ("positive", "negative", "mixed_or_uncertain")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def as_int(value: str | int | None) -> int:
    return int(value or 0)


def as_float(value: str | float | None) -> float:
    return float(value or 0)


def date_only(value: str) -> str:
    return value[:10] if value else ""


def build_sentiment_buckets(manifest: dict) -> list[dict]:
    buckets = manifest.get("buckets", {})
    ordered_ids = [
        bucket_id
        for bucket_id in SENTIMENT_BUCKET_ORDER
        if bucket_id in buckets
    ]
    ordered_ids.extend(sorted(set(buckets) - set(ordered_ids)))
    return [
        {
            "id": bucket_id,
            "sourceRows": as_int(buckets[bucket_id].get("source_rows")),
            "selectedRows": as_int(buckets[bucket_id].get("selected_rows")),
            "selectionStrategy": buckets[bucket_id].get("selection_strategy", ""),
        }
        for bucket_id in ordered_ids
    ]


def build_interpretation(status: str, post_match_count: int) -> str:
    if status == "limited_post_evidence":
        return f"更新後仍有 {post_match_count} 則相關評論；樣本數有限，建議持續追蹤。"
    if status == "not_observed_after_release":
        return "更新後 28 天未出現相同關鍵詞組；不代表 Android 問題已修復。"
    return "此案例未符合完整觀察條件，僅保留作為資料背景。"


def build_llm_quality(
    manifest_path: Path,
    batch_dir: Path,
    output_dir: Path,
    repair_report_path: Path,
) -> dict:
    manifest = read_json(manifest_path)
    repair_report = read_json(repair_report_path)
    validation = validate_output_dir(batch_dir, output_dir, require_all=True)
    selected_review_count = sum(
        as_int(bucket.get("selected_rows"))
        for bucket in manifest.get("buckets", {}).values()
    )

    return {
        "selectedReviewCount": selected_review_count,
        "expectedBatchCount": as_int(validation.get("expected_batches")),
        "batchCount": as_int(validation.get("actual_outputs")),
        "themeCount": as_int(validation.get("total_themes")),
        "evidenceCount": as_int(validation.get("total_evidence")),
        "excludedReviewCount": as_int(validation.get("total_excluded")),
        "validationErrorCount": as_int(validation.get("error_count")),
        "fixedQuoteCount": as_int(repair_report.get("fixed_quote")),
        "fixedScoreCount": as_int(repair_report.get("fixed_score")),
        "droppedEvidenceCount": as_int(repair_report.get("dropped_evidence")),
        "droppedExcludedCount": as_int(repair_report.get("dropped_excluded")),
    }


def build_dashboard_snapshot(
    reviews_path: Path,
    trends_path: Path,
    evidence_path: Path,
    rules_path: Path,
    output_path: Path,
    *,
    llm_manifest_path: Path = DEFAULT_LLM_MANIFEST,
    llm_batch_dir: Path = DEFAULT_LLM_BATCH_DIR,
    llm_output_dir: Path = DEFAULT_LLM_OUTPUT_DIR,
    repair_report_path: Path = DEFAULT_REPAIR_REPORT,
    raw_reviews_path: Path = DEFAULT_RAW_REVIEWS,
) -> dict:
    raw_reviews = read_csv(raw_reviews_path)
    reviews = read_csv(reviews_path)
    trend_rows = read_csv(trends_path)
    evidence_rows = read_csv(evidence_path)
    rules = read_json(rules_path)
    llm_manifest = read_json(llm_manifest_path)
    sentiment_buckets = build_sentiment_buckets(llm_manifest)
    llm_quality = build_llm_quality(
        llm_manifest_path,
        llm_batch_dir,
        llm_output_dir,
        repair_report_path,
    )
    phrases_by_candidate = {
        rule["candidate_id"]: rule.get("match_any_phrases", [])
        for rule in rules.get("rules", [])
    }

    review_dates = sorted(
        date_only(row.get("review_created_at", ""))
        for row in reviews
        if row.get("review_created_at")
    )

    trends = []
    for row in trend_rows:
        candidate_id = row["candidate_id"]
        pre_matches = as_int(row.get("pre_match_count"))
        post_matches = as_int(row.get("post_match_count"))
        trends.append(
            {
                "id": candidate_id,
                "themeId": row.get("theme_id", ""),
                "theme": row.get("theme_name_zh", ""),
                "area": row.get("theme_affected_area", "other"),
                "releaseDate": row.get("release_date", ""),
                "releaseTitle": row.get("release_title", ""),
                "releaseScope": row.get("release_scope", "general_product_release"),
                "windowDays": as_int(row.get("window_days")),
                "pre": {
                    "matches": pre_matches,
                    "eligible": as_int(row.get("pre_eligible_count")),
                    "rate": round(as_float(row.get("pre_match_rate")) * 100, 2),
                },
                "post": {
                    "matches": post_matches,
                    "eligible": as_int(row.get("post_eligible_count")),
                    "rate": round(as_float(row.get("post_match_rate")) * 100, 2),
                },
                "change": round(as_float(row.get("rate_change_percentage_points")), 2),
                "status": row.get("observation_status", ""),
                "phrases": phrases_by_candidate.get(candidate_id, []),
                "interpretation": build_interpretation(row.get("observation_status", ""), post_matches),
            }
        )

    trend_ids = {trend["id"] for trend in trends}
    evidence = [
        {
            "reviewId": row.get("review_id", ""),
            "trendId": row.get("candidate_id", ""),
            "period": row.get("period", ""),
            "date": date_only(row.get("review_created_at", "")),
            "version": row.get("app_version", "") or "未提供",
            "score": as_int(row.get("score")),
            "phrases": [phrase for phrase in row.get("matched_phrases", "").split("|") if phrase],
            "text": row.get("review_text_clean", ""),
        }
        for row in evidence_rows
        if row.get("candidate_id") in trend_ids
    ]

    review_range_start = review_dates[0] if review_dates else ""
    review_range_end = review_dates[-1] if review_dates else ""
    window_days = as_int(rules.get("window_days"))
    snapshot = {
        "metadata": {
            "reviewRangeStart": review_range_start,
            "reviewRangeEnd": review_range_end,
            "trendReleaseScope": rules.get("release_scope", "general_product_release"),
            "windowDays": window_days,
            "selectionCriteria": "具完整 28 天觀察期間、跨產品面向且可回查原始評論；僅作為代表案例。",
            "sourceFiles": [
                str(raw_reviews_path).replace("\\", "/"),
                str(reviews_path).replace("\\", "/"),
                str(llm_manifest_path).replace("\\", "/"),
                str(llm_output_dir).replace("\\", "/"),
                str(trends_path).replace("\\", "/"),
                str(evidence_path).replace("\\", "/"),
            ],
            "evidenceCount": len(evidence),
        },
        "reviewSummary": {
            "rawRows": len(raw_reviews),
            "cleanedRows": len(reviews),
            "llmSelectedRows": llm_quality["selectedReviewCount"],
        },
        "sentimentBuckets": sentiment_buckets,
        "llmQuality": llm_quality,
        "portfolioMetrics": [
            {
                "value": f"{len(reviews):,}",
                "label": "清洗後評論",
                "note": "Google Play 美國區英文評論",
            },
            {
                "value": f"{llm_quality['selectedReviewCount']:,}",
                "label": "大型語言模型輸入",
                "note": "負面與不確定評論全量；正向代表樣本",
            },
            {
                "value": f"{llm_quality['themeCount']:,}",
                "label": "驗證後主題",
                "note": f"來自 {llm_quality['batchCount']} 個分析批次",
            },
            {
                "value": f"{llm_quality['evidenceCount']:,}",
                "label": "LLM 主題證據",
                "note": "評論識別碼、星等與原文引文",
            },
        ],
        "trends": trends,
        "evidence": evidence,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "// Generated by src/analysis/build_dashboard_snapshot.py. Do not edit manually.\n"
        f"export const dashboardSnapshot = {json.dumps(snapshot, ensure_ascii=False, indent=2)} as const\n",
        encoding="utf-8",
    )
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the portfolio dashboard data snapshot.")
    parser.add_argument("--raw-reviews", type=Path, default=DEFAULT_RAW_REVIEWS)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--trends", type=Path, default=DEFAULT_TRENDS)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--llm-manifest", type=Path, default=DEFAULT_LLM_MANIFEST)
    parser.add_argument("--llm-batch-dir", type=Path, default=DEFAULT_LLM_BATCH_DIR)
    parser.add_argument("--llm-output-dir", type=Path, default=DEFAULT_LLM_OUTPUT_DIR)
    parser.add_argument("--repair-report", type=Path, default=DEFAULT_REPAIR_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = build_dashboard_snapshot(
        args.reviews,
        args.trends,
        args.evidence,
        args.rules,
        args.output,
        llm_manifest_path=args.llm_manifest,
        llm_batch_dir=args.llm_batch_dir,
        llm_output_dir=args.llm_output_dir,
        repair_report_path=args.repair_report,
        raw_reviews_path=args.raw_reviews,
    )
    print(
        f"Wrote {len(snapshot['trends'])} trends, {len(snapshot['evidence'])} trend evidence rows, "
        f"and {snapshot['llmQuality']['evidenceCount']} validated LLM evidence rows to {args.output}"
    )


if __name__ == "__main__":
    main()