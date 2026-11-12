import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.validate_llm_outputs import load_source_batches, output_path_batch_id


DEFAULT_BATCH_DIR = Path("data/processed/llm_inputs")
DEFAULT_INPUT_DIR = Path("outputs/reports/llm_batch_outputs_api")
DEFAULT_OUTPUT_DIR = Path("outputs/reports/llm_batch_outputs_api_repaired")
DEFAULT_REPORT = Path("outputs/reports/llm_batch_outputs_api_repair_report.json")
DEFAULT_QUOTE_REVIEWS = Path("configs/llm_quote_reviews.v1.json")
ALLOWED_EXCLUDED_REASONS = {
    "non_english",
    "insufficient_information",
    "unrelated",
}


def quote_review_key(batch_id: str, theme_id: str, review_id: str) -> tuple[str, str, str]:
    return batch_id, theme_id, review_id


def load_quote_reviews(path: Path) -> tuple[int, dict[tuple[str, str, str], dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = int(data.get("version") or 0)
    if version < 1:
        raise ValueError(f"Invalid quote review version in {path}: {version}")

    decisions = {}
    for index, item in enumerate(data.get("decisions", []), start=1):
        key = quote_review_key(
            str(item.get("batch_id") or "").strip(),
            str(item.get("theme_id") or "").strip(),
            str(item.get("review_id") or "").strip(),
        )
        if not all(key):
            raise ValueError(f"Quote review decision {index} has an incomplete key")
        if key in decisions:
            raise ValueError(f"Duplicate quote review decision: {key}")

        action = item.get("action")
        if action not in {"replace", "drop"}:
            raise ValueError(f"Invalid quote review action for {key}: {action}")
        if action == "replace" and not str(item.get("replacement_quote") or ""):
            raise ValueError(f"Replacement quote is required for {key}")
        decisions[key] = item

    return version, decisions


def build_source_review_map(source_batch: dict) -> dict[str, dict]:
    return {
        str(review.get("review_id") or "").strip(): review
        for review in source_batch.get("reviews", [])
        if str(review.get("review_id") or "").strip()
    }


def empty_report(batch_id: str) -> dict:
    return {
        "batch_id": batch_id,
        "fixed_score": 0,
        "fixed_quote": 0,
        "reviewed_quote_replacement": 0,
        "reviewed_quote_drop": 0,
        "dropped_evidence": 0,
        "dropped_themes": 0,
        "dropped_excluded": 0,
    }


def repair_evidence(
    evidence: dict,
    source_reviews: dict[str, dict],
    report: dict,
    *,
    theme_id: str,
    quote_reviews: dict[tuple[str, str, str], dict],
    used_quote_reviews: set[tuple[str, str, str]],
) -> dict | None:
    review_id = str(evidence.get("review_id") or "").strip()
    if review_id not in source_reviews:
        report["dropped_evidence"] += 1
        return None

    source = source_reviews[review_id]
    repaired = dict(evidence)

    source_score = str(source.get("score", ""))
    if str(repaired.get("score", "")) != source_score:
        repaired["score"] = source_score
        report["fixed_score"] += 1

    source_text = str(source.get("review_text_for_model") or "")
    quote = str(repaired.get("quote") or "")
    if not quote or quote not in source_text:
        key = quote_review_key(report["batch_id"], theme_id, review_id)
        decision = quote_reviews.get(key)
        if decision is None:
            raise ValueError(
                "Non-traceable quote has no semantic review decision: "
                f"batch={key[0]} theme={key[1]} review_id={key[2]}"
            )
        used_quote_reviews.add(key)

        if decision["action"] == "drop":
            report["reviewed_quote_drop"] += 1
            report["dropped_evidence"] += 1
            return None

        replacement_quote = str(decision.get("replacement_quote") or "")
        if replacement_quote not in source_text:
            raise ValueError(f"Reviewed replacement quote is not traceable for {key}")
        repaired["quote"] = replacement_quote
        report["fixed_quote"] += 1
        report["reviewed_quote_replacement"] += 1

    if not repaired["quote"]:
        report["dropped_evidence"] += 1
        return None

    return repaired


def repair_excluded_review(
    excluded_review: dict,
    source_reviews: dict[str, dict],
    report: dict,
) -> dict | None:
    review_id = str(excluded_review.get("review_id") or "").strip()
    reason = excluded_review.get("reason")
    if review_id not in source_reviews or reason not in ALLOWED_EXCLUDED_REASONS:
        report["dropped_excluded"] += 1
        return None
    return dict(excluded_review)


def repair_llm_output(
    llm_output: dict,
    source_reviews: dict[str, dict],
    quote_reviews: dict[tuple[str, str, str], dict] | None = None,
    used_quote_reviews: set[tuple[str, str, str]] | None = None,
) -> tuple[dict, dict]:
    repaired = deepcopy(llm_output)
    report = empty_report(str(repaired.get("batch_id") or ""))
    quote_reviews = quote_reviews or {}
    used_quote_reviews = used_quote_reviews if used_quote_reviews is not None else set()

    repaired_themes = []
    for theme in repaired.get("themes", []):
        theme_id = str(theme.get("theme_id") or "").strip()
        evidence_items = []
        for evidence in theme.get("evidence", []):
            repaired_evidence = repair_evidence(
                evidence,
                source_reviews,
                report,
                theme_id=theme_id,
                quote_reviews=quote_reviews,
                used_quote_reviews=used_quote_reviews,
            )
            if repaired_evidence is not None:
                evidence_items.append(repaired_evidence)

        if evidence_items:
            theme["evidence"] = evidence_items
            repaired_themes.append(theme)
        else:
            report["dropped_themes"] += 1

    repaired["themes"] = repaired_themes
    repaired["excluded_reviews"] = [
        item
        for item in (
            repair_excluded_review(excluded, source_reviews, report)
            for excluded in repaired.get("excluded_reviews", [])
        )
        if item is not None
    ]

    return repaired, report


def write_json(data: dict | list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def repair_output_dir(
    batch_dir: Path,
    input_dir: Path,
    output_dir: Path,
    quote_reviews: dict[tuple[str, str, str], dict],
) -> list[dict]:
    source_batches = load_source_batches(batch_dir)
    reports = []
    used_quote_reviews: set[tuple[str, str, str]] = set()
    for input_path in sorted(input_dir.glob("*_output.json")):
        batch_id = output_path_batch_id(input_path)
        if batch_id not in source_batches:
            raise ValueError(f"Output has no matching source batch: {batch_id}")

        source_reviews = build_source_review_map(source_batches[batch_id])
        llm_output = json.loads(input_path.read_text(encoding="utf-8"))
        repaired, report = repair_llm_output(
            llm_output,
            source_reviews,
            quote_reviews,
            used_quote_reviews,
        )
        write_json(repaired, output_dir / input_path.name)
        reports.append(report)

    unused_quote_reviews = set(quote_reviews) - used_quote_reviews
    if unused_quote_reviews:
        raise ValueError(
            "Quote review decisions were not used by the current inputs: "
            + ", ".join(str(key) for key in sorted(unused_quote_reviews))
        )

    return reports


def summarize_reports(reports: list[dict], quote_review_version: int) -> dict:
    summary = {
        "batches": len(reports),
        "quote_review_version": quote_review_version,
        "fixed_score": 0,
        "fixed_quote": 0,
        "reviewed_quote_replacement": 0,
        "reviewed_quote_drop": 0,
        "dropped_evidence": 0,
        "dropped_themes": 0,
        "dropped_excluded": 0,
        "by_batch": reports,
    }
    for report in reports:
        for key in (
            "fixed_score",
            "fixed_quote",
            "reviewed_quote_replacement",
            "reviewed_quote_drop",
            "dropped_evidence",
            "dropped_themes",
            "dropped_excluded",
        ):
            summary[key] += report[key]
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair API LLM outputs by enforcing traceable review_id, score, and quote values."
    )
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--quote-reviews", type=Path, default=DEFAULT_QUOTE_REVIEWS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    quote_review_version, quote_reviews = load_quote_reviews(args.quote_reviews)
    reports = repair_output_dir(
        args.batch_dir,
        args.input_dir,
        args.output_dir,
        quote_reviews,
    )
    summary = summarize_reports(reports, quote_review_version)
    write_json(summary, args.report)
    print(
        f"Repaired {summary['batches']} LLM output file(s) to {args.output_dir}. "
        f"fixed_quote={summary['fixed_quote']} "
        f"fixed_score={summary['fixed_score']} "
        f"reviewed_quote_drop={summary['reviewed_quote_drop']} "
        f"dropped_evidence={summary['dropped_evidence']} "
        f"dropped_themes={summary['dropped_themes']} "
        f"dropped_excluded={summary['dropped_excluded']}"
    )


if __name__ == "__main__":
    main()
