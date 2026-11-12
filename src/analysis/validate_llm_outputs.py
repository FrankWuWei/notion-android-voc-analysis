import argparse
import json
from collections import defaultdict
from pathlib import Path


DEFAULT_BATCH_DIR = Path("data/processed/llm_inputs")
DEFAULT_OUTPUT_DIR = Path("outputs/reports/llm_batch_outputs_api")
ALLOWED_EXCLUDED_REASONS = {
    "non_english",
    "insufficient_information",
    "unrelated",
}


def load_source_batches(batch_dir: Path) -> dict[str, dict]:
    batches = {}
    for batch_path in sorted(batch_dir.glob("*_llm_batches.jsonl")):
        if "smoke" in batch_path.name:
            continue
        with batch_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                batch = json.loads(line)
                batch_id = str(batch.get("batch_id") or "")
                if not batch_id:
                    raise ValueError(f"Missing batch_id in {batch_path} line {line_number}")
                if batch_id in batches:
                    raise ValueError(f"Duplicate batch_id in source batches: {batch_id}")
                batches[batch_id] = batch
    return batches


def review_map(batch: dict) -> dict[str, dict]:
    return {str(review.get("review_id")): review for review in batch.get("reviews", [])}


def output_path_batch_id(path: Path) -> str:
    name = path.name
    suffix = "_output.json"
    if not name.endswith(suffix):
        raise ValueError(f"Unexpected LLM output filename: {path}")
    return name[: -len(suffix)]


def validate_review_reference(
    reference: dict,
    source_reviews: dict[str, dict],
    batch_id: str,
    location: str,
) -> list[str]:
    errors = []
    review_id = str(reference.get("review_id") or "").strip()
    if not review_id:
        return [f"{batch_id} {location}: missing review_id"]
    if review_id not in source_reviews:
        return [f"{batch_id} {location}: review_id not found: {review_id}"]

    source = source_reviews[review_id]
    if "score" in reference:
        expected_score = str(source.get("score", ""))
        actual_score = str(reference.get("score", ""))
        if actual_score != expected_score:
            errors.append(
                f"{batch_id} {location}: score mismatch for {review_id}: "
                f"expected {expected_score}, got {actual_score}"
            )

    quote = reference.get("quote")
    if quote is not None:
        source_text = str(source.get("review_text_for_model") or "")
        if str(quote) not in source_text:
            errors.append(f"{batch_id} {location}: quote not found for {review_id}")

    return errors


def validate_llm_output(output: dict, source_batch: dict, expected_batch_id: str) -> dict:
    errors = []
    source_reviews = review_map(source_batch)
    evidence_count = 0
    excluded_count = 0

    if output.get("batch_id") != expected_batch_id:
        errors.append(
            f"{expected_batch_id}: batch_id mismatch: got {output.get('batch_id')}"
        )
    if output.get("sentiment_bucket") != source_batch.get("sentiment_bucket"):
        errors.append(
            f"{expected_batch_id}: sentiment_bucket mismatch: "
            f"expected {source_batch.get('sentiment_bucket')}, "
            f"got {output.get('sentiment_bucket')}"
        )
    if output.get("analysis_language") != "zh-Hant":
        errors.append(
            f"{expected_batch_id}: analysis_language should be zh-Hant, "
            f"got {output.get('analysis_language')}"
        )

    themes = output.get("themes")
    if not isinstance(themes, list):
        errors.append(f"{expected_batch_id}: themes must be a list")
        themes = []

    for theme_index, theme in enumerate(themes, start=1):
        evidence = theme.get("evidence") if isinstance(theme, dict) else None
        if not isinstance(evidence, list):
            errors.append(f"{expected_batch_id} theme {theme_index}: evidence must be a list")
            continue
        if not evidence:
            errors.append(f"{expected_batch_id} theme {theme_index}: evidence is empty")
        for evidence_index, item in enumerate(evidence, start=1):
            evidence_count += 1
            errors.extend(
                validate_review_reference(
                    item,
                    source_reviews,
                    expected_batch_id,
                    f"theme {theme_index} evidence {evidence_index}",
                )
            )

    excluded_reviews = output.get("excluded_reviews")
    if not isinstance(excluded_reviews, list):
        errors.append(f"{expected_batch_id}: excluded_reviews must be a list")
        excluded_reviews = []

    for excluded_index, item in enumerate(excluded_reviews, start=1):
        excluded_count += 1
        if item.get("reason") not in ALLOWED_EXCLUDED_REASONS:
            errors.append(
                f"{expected_batch_id} excluded {excluded_index}: invalid reason "
                f"{item.get('reason')}"
            )
        errors.extend(
            validate_review_reference(
                item,
                source_reviews,
                expected_batch_id,
                f"excluded {excluded_index}",
            )
        )

    return {
        "errors": errors,
        "theme_count": len(themes),
        "evidence_count": evidence_count,
        "excluded_count": excluded_count,
    }


def validate_output_dir(
    batch_dir: Path = DEFAULT_BATCH_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    require_all: bool = False,
) -> dict:
    source_batches = load_source_batches(batch_dir)
    output_paths = sorted(output_dir.glob("*_output.json"))
    errors = []
    total_themes = 0
    total_evidence = 0
    total_excluded = 0
    by_bucket = defaultdict(lambda: {"batches": 0, "themes": 0, "evidence": 0, "excluded": 0})
    seen_batch_ids = set()

    for output_path in output_paths:
        batch_id = output_path_batch_id(output_path)
        seen_batch_ids.add(batch_id)
        if batch_id not in source_batches:
            errors.append(f"{batch_id}: output has no matching source batch")
            continue
        output = json.loads(output_path.read_text(encoding="utf-8"))
        summary = validate_llm_output(output, source_batches[batch_id], batch_id)
        errors.extend(summary["errors"])
        total_themes += summary["theme_count"]
        total_evidence += summary["evidence_count"]
        total_excluded += summary["excluded_count"]

        bucket = str(source_batches[batch_id].get("sentiment_bucket") or "unknown")
        by_bucket[bucket]["batches"] += 1
        by_bucket[bucket]["themes"] += summary["theme_count"]
        by_bucket[bucket]["evidence"] += summary["evidence_count"]
        by_bucket[bucket]["excluded"] += summary["excluded_count"]

    if require_all:
        missing = sorted(set(source_batches) - seen_batch_ids)
        for batch_id in missing:
            errors.append(f"{batch_id}: missing output file")

    return {
        "expected_batches": len(source_batches),
        "actual_outputs": len(output_paths),
        "total_themes": total_themes,
        "total_evidence": total_evidence,
        "total_excluded": total_excluded,
        "by_bucket": dict(by_bucket),
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate VOC LLM JSON outputs against their source review batches."
    )
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Require one output JSON file for every source batch.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = validate_output_dir(args.batch_dir, args.output_dir, args.require_all)
    printable = dict(result)
    printable["error_count"] = len(result["errors"])
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
