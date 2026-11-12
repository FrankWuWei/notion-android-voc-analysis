import argparse
import csv
import json
import os
import unittest
from pathlib import Path

from src.analysis.validate_llm_outputs import validate_output_dir


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "portfolio_web.v1.json"
DEFAULT_OUTPUT = ROOT / "web" / "src" / "data" / "portfolioSnapshot.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def as_int(value: object) -> int:
    return int(str(value))


def as_float(value: object) -> float:
    return float(str(value))


def count_analysis_tests(root: Path) -> int:
    original_cwd = Path.cwd()
    try:
        os.chdir(root)
        suite = unittest.defaultTestLoader.discover("tests")
        return suite.countTestCases()
    finally:
        os.chdir(original_cwd)


def find_unique_evidence(
    evidence_rows: list[dict[str, str]],
    theme_id: str,
    selection: dict,
) -> dict:
    matches = [
        row
        for row in evidence_rows
        if row["canonical_theme_id"] == theme_id
        and row["review_id"] == selection["review_id"]
        and row["quote"] == selection["quote"]
    ]
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one evidence row for "
            f"{selection['id']} ({theme_id}), found {len(matches)}"
        )
    row = matches[0]
    return {
        "id": selection["id"],
        "quote": row["quote"],
        "reviewId": row["review_id"],
        "reviewCreatedAt": row["review_created_at"],
        "score": as_int(row["score"]),
        "appVersion": row["app_version"] or None,
        "batchId": row["batch_id"],
        "sentimentBucket": row["sentiment_bucket"],
    }


def build_snapshot(root: Path, config_path: Path) -> dict:
    config = load_json(config_path)
    raw_rows = load_csv(root / "data/raw/notion_android_reviews_google_play_2025_onward_en_us.csv")
    clean_rows = load_csv(root / "data/interim/reviews_cleaned_2025_onward_en_us.csv")
    sentiment_rows = load_csv(root / "data/processed/reviews_with_sentiment_2025_onward_en_us.csv")
    manifest = load_json(root / "data/processed/llm_inputs/manifest.json")
    canonical_summary = load_json(root / "outputs/tables/canonical_themes_summary.json")
    canonical_themes = load_csv(root / "outputs/tables/canonical_themes.csv")
    canonical_evidence = load_csv(root / "outputs/tables/canonical_theme_evidence.csv")
    repair_report = load_json(root / "outputs/reports/llm_batch_outputs_api_repair_report.json")
    quote_reviews = load_json(root / "configs/llm_quote_reviews.v1.json")
    release_summary = load_json(
        root / "outputs/tables/negative_theme_release_trends_summary.json"
    )
    release_trends = load_csv(
        root / "outputs/tables/negative_theme_release_trends.csv"
    )
    release_evidence = load_csv(
        root / "outputs/tables/negative_theme_release_trend_evidence.csv"
    )
    monitoring_rules = load_json(
        root / "configs/negative_theme_monitoring_rules.json"
    )

    validation = validate_output_dir(
        root / "data/processed/llm_inputs",
        root / "outputs/reports/llm_batch_outputs_api_repaired_enriched",
        require_all=True,
    )

    review_dates = sorted(row["review_created_at"][:10] for row in clean_rows)
    deep_analysis_count = sum(
        as_int(bucket["selected_rows"]) for bucket in manifest["buckets"].values()
    )
    llm_batch_count = sum(
        as_int(bucket["batch_count"]) for bucket in manifest["buckets"].values()
    )
    analysis_test_count = count_analysis_tests(root)

    facts = {
        "raw_review_count": len(raw_rows),
        "effective_review_count": len(clean_rows),
        "positive_review_count": as_int(manifest["source_bucket_counts"]["positive"]),
        "negative_review_count": as_int(manifest["source_bucket_counts"]["negative"]),
        "uncertain_review_count": as_int(
            manifest["source_bucket_counts"]["mixed_or_uncertain"]
        ),
        "deep_analysis_review_count": deep_analysis_count,
        "llm_batch_count": llm_batch_count,
        "batch_theme_count": as_int(canonical_summary["source_theme_count"]),
        "evidence_count": as_int(canonical_summary["evidence_count"]),
        "unique_evidence_review_count": as_int(canonical_summary["unique_review_count"]),
        "canonical_theme_count": as_int(canonical_summary["canonical_theme_count"]),
        "pain_theme_count": as_int(
            canonical_summary["by_group"]["pain"]["canonical_theme_count"]
        ),
        "positive_value_count": as_int(
            canonical_summary["by_group"]["positive_value"]["canonical_theme_count"]
        ),
        "extended_candidate_count": as_int(release_summary["trend_row_count"]),
        "extended_evidence_count": as_int(release_summary["evidence_row_count"]),
        "analysis_test_count": analysis_test_count,
        "source_validation_error_count": len(validation["errors"]),
        "review_period_start": review_dates[0],
        "review_period_end": review_dates[-1],
    }

    for key, expected_value in config["expected"].items():
        actual_value = facts.get(key)
        if actual_value != expected_value:
            raise ValueError(
                f"Portfolio fact drift for {key}: expected {expected_value!r}, "
                f"got {actual_value!r}"
            )

    if validation["total_themes"] != facts["batch_theme_count"]:
        raise ValueError("Validated theme total does not match canonical theme summary")
    if validation["total_evidence"] != facts["evidence_count"]:
        raise ValueError("Validated evidence total does not match canonical theme summary")

    themes_by_id = {row["canonical_theme_id"]: row for row in canonical_themes}

    main_themes = []
    negative_and_uncertain_batches = (
        as_int(manifest["buckets"]["negative"]["batch_count"])
        + as_int(manifest["buckets"]["mixed_or_uncertain"]["batch_count"])
    )
    for selection in config["main_theme_selections"]:
        theme_id = selection["theme_id"]
        if theme_id not in themes_by_id:
            raise ValueError(f"Unknown main theme: {theme_id}")
        theme = themes_by_id[theme_id]
        main_themes.append(
            {
                "id": theme_id,
                "nameZh": theme["canonical_theme_name_zh"],
                "descriptionZh": theme["description_zh"],
                "batchCoverage": as_int(theme["batch_count"]),
                "batchCoverageTotal": negative_and_uncertain_batches,
                "evidenceCount": as_int(theme["evidence_count"]),
                "evidence": [
                    find_unique_evidence(canonical_evidence, theme_id, evidence)
                    for evidence in selection["evidence"]
                ],
            }
        )

    positive_values = []
    for selection in config["positive_value_selections"]:
        theme_id = selection["theme_id"]
        if theme_id not in themes_by_id:
            raise ValueError(f"Unknown positive value: {theme_id}")
        theme = themes_by_id[theme_id]
        positive_values.append(
            {
                "id": theme_id,
                "nameZh": theme["canonical_theme_name_zh"],
                "descriptionZh": theme["description_zh"],
                "evidenceCount": as_int(theme["evidence_count"]),
                "evidence": find_unique_evidence(
                    canonical_evidence, theme_id, selection["evidence"]
                ),
            }
        )

    quality_config = config["quality_case"]
    source_reviews = {row["review_id"]: row for row in sentiment_rows}
    source_review = source_reviews.get(quality_config["review_id"])
    if source_review is None:
        raise ValueError("Quality case review is missing from the sentiment dataset")
    if source_review["review_text"] != quality_config["expected_source_review"]:
        raise ValueError("Quality case source review changed")

    quality_decisions = [
        decision
        for decision in quote_reviews["decisions"]
        if decision["batch_id"] == quality_config["batch_id"]
        and decision["theme_id"] == quality_config["theme_id"]
        and decision["review_id"] == quality_config["review_id"]
    ]
    if len(quality_decisions) != 1 or quality_decisions[0]["action"] != "drop":
        raise ValueError("Quality case must have exactly one versioned drop decision")

    extended_config = config["extended_validation_example"]
    extended_trend_matches = [
        row
        for row in release_trends
        if row["candidate_id"] == extended_config["candidate_id"]
    ]
    if len(extended_trend_matches) != 1:
        raise ValueError(
            "Extended validation example must match exactly one trend row"
        )
    extended_trend = extended_trend_matches[0]

    extended_evidence_matches = [
        row
        for row in release_evidence
        if row["candidate_id"] == extended_config["candidate_id"]
        and row["review_id"] == extended_config["evidence_review_id"]
    ]
    if len(extended_evidence_matches) != 1:
        raise ValueError(
            "Extended validation example must match exactly one evidence row"
        )
    extended_evidence_row = extended_evidence_matches[0]
    if extended_config["quote"] not in extended_evidence_row["review_text_clean"]:
        raise ValueError("Extended validation example quote is not in the source review")

    extended_rule_matches = [
        rule
        for rule in monitoring_rules["rules"]
        if rule["candidate_id"] == extended_config["candidate_id"]
    ]
    if len(extended_rule_matches) != 1:
        raise ValueError(
            "Extended validation example must match exactly one monitoring rule"
        )
    extended_rule = extended_rule_matches[0]

    extended_actual = {
        "release_date": extended_trend["release_date"],
        "pre_eligible_count": as_int(extended_trend["pre_eligible_count"]),
        "post_eligible_count": as_int(extended_trend["post_eligible_count"]),
        "pre_match_count": as_int(extended_trend["pre_match_count"]),
        "post_match_count": as_int(extended_trend["post_match_count"]),
    }
    for key, expected_value in extended_config["expected"].items():
        actual_value = extended_actual.get(key)
        if actual_value != expected_value:
            raise ValueError(
                f"Extended validation example drift for {key}: "
                f"expected {expected_value!r}, got {actual_value!r}"
            )

    return {
        "schemaVersion": 1,
        "sourceDigestSha256": canonical_summary["source_digest_sha256"],
        "scope": {
            "platform": "Android",
            "store": "Google Play",
            "market": "US",
            "language": "English",
            "periodStart": facts["review_period_start"],
            "periodEnd": facts["review_period_end"],
            "rawReviews": facts["raw_review_count"],
            "effectiveReviews": facts["effective_review_count"],
        },
        "pipeline": {
            "sentiment": {
                "positive": facts["positive_review_count"],
                "negative": facts["negative_review_count"],
                "uncertain": facts["uncertain_review_count"],
            },
            "deepAnalysisReviews": facts["deep_analysis_review_count"],
            "llmBatches": facts["llm_batch_count"],
            "validatedBatchThemes": facts["batch_theme_count"],
            "sourceVerbatimEvidence": facts["evidence_count"],
            "uniqueEvidenceReviews": facts["unique_evidence_review_count"],
            "canonicalThemes": facts["canonical_theme_count"],
            "painThemes": facts["pain_theme_count"],
            "positiveValues": facts["positive_value_count"],
            "validatedBatches": validation["actual_outputs"],
            "expectedBatches": validation["expected_batches"],
            "sourceValidationErrors": facts["source_validation_error_count"],
        },
        "qualityAudit": {
            "reviewedNonVerbatimQuotes": (
                as_int(repair_report["reviewed_quote_replacement"])
                + as_int(repair_report["reviewed_quote_drop"])
            ),
            "replacedWithSupportingVerbatimQuote": as_int(
                repair_report["reviewed_quote_replacement"]
            ),
            "droppedAsUnsupported": as_int(repair_report["reviewed_quote_drop"]),
            "correctedScores": as_int(repair_report["fixed_score"]),
        },
        "qualityCase": {
            "batchId": quality_config["batch_id"],
            "themeId": quality_config["theme_id"],
            "modelQuote": quality_config["model_quote"],
            "sourceReview": source_review["review_text"],
            "reviewId": source_review["review_id"],
            "reviewCreatedAt": source_review["review_created_at"],
            "score": as_int(source_review["score"]),
            "appVersion": source_review["app_version"] or None,
            "decision": quality_decisions[0]["action"],
            "reasonZh": quality_decisions[0]["reason_zh"],
        },
        "mainThemes": main_themes,
        "positiveValues": positive_values,
        "extendedValidation": {
            "windowDays": as_int(release_summary["window_days"]),
            "candidateCases": as_int(release_summary["trend_row_count"]),
            "ruleMatchedReviews": as_int(release_summary["evidence_row_count"]),
            "scope": release_summary["release_scope"],
            "example": {
                "candidateId": extended_trend["candidate_id"],
                "themeId": extended_trend["theme_id"],
                "themeNameZh": extended_trend["theme_name_zh"],
                "releaseDate": extended_trend["release_date"],
                "releaseTitle": extended_trend["release_title"],
                "releaseScope": extended_trend["release_scope"],
                "windowDays": as_int(extended_trend["window_days"]),
                "before": {
                    "eligibleReviews": as_int(extended_trend["pre_eligible_count"]),
                    "matchedReviews": as_int(extended_trend["pre_match_count"]),
                    "matchRate": as_float(extended_trend["pre_match_rate"]),
                },
                "after": {
                    "eligibleReviews": as_int(extended_trend["post_eligible_count"]),
                    "matchedReviews": as_int(extended_trend["post_match_count"]),
                    "matchRate": as_float(extended_trend["post_match_rate"]),
                },
                "rateChangePercentagePoints": as_float(
                    extended_trend["rate_change_percentage_points"]
                ),
                "observationStatus": extended_trend["observation_status"],
                "rulePhrases": extended_rule["match_any_phrases"],
                "evidence": {
                    "quote": extended_config["quote"],
                    "sourceReview": extended_evidence_row["review_text_clean"],
                    "reviewId": extended_evidence_row["review_id"],
                    "reviewCreatedAt": extended_evidence_row["review_created_at"],
                    "score": as_int(extended_evidence_row["score"]),
                    "appVersion": extended_evidence_row["app_version"] or None,
                    "period": extended_evidence_row["period"],
                    "matchedPhrases": [
                        phrase
                        for phrase in extended_evidence_row["matched_phrases"].split("|")
                        if phrase
                    ],
                },
            },
        },
        "engineering": {
            "analysisTestCount": facts["analysis_test_count"],
            "configVersion": config["version"],
            "canonicalTaxonomyVersion": canonical_summary["taxonomy_version"],
            "quoteReviewVersion": repair_report["quote_review_version"],
        },
        "countingBoundary": canonical_summary["counting_boundary"],
    }


def write_snapshot(snapshot: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the static, validated data snapshot for the portfolio website."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = build_snapshot(ROOT, args.config)
    write_snapshot(snapshot, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "schema_version": snapshot["schemaVersion"],
                "effective_reviews": snapshot["scope"]["effectiveReviews"],
                "main_themes": len(snapshot["mainThemes"]),
                "representative_evidence": sum(
                    len(theme["evidence"]) for theme in snapshot["mainThemes"]
                )
                + len(snapshot["positiveValues"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
