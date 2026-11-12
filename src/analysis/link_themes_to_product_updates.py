import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_LLM_OUTPUT_DIR = Path("outputs/reports/llm_batch_outputs_api_repaired_enriched")
DEFAULT_RELEASE_NOTES = Path("data/processed/product_updates/notion_release_notes.csv")
DEFAULT_OUTPUT = Path("outputs/tables/theme_release_candidates.csv")
DEFAULT_SUMMARY = Path("outputs/tables/theme_release_candidates_summary.json")
DEFAULT_MIN_SCORE = 3

BROAD_KEYWORDS = {
    "access",
    "admin",
    "agent",
    "agents",
    "ai",
    "app",
    "block",
    "blocks",
    "control",
    "controls",
    "credit",
    "credits",
    "database",
    "doc",
    "docs",
    "editing",
    "enterprise",
    "file",
    "files",
    "fix",
    "mobile",
    "model",
    "notion",
    "performance",
    "phone",
    "security",
    "simple",
    "speed",
    "sync",
    "table",
    "tables",
    "upload",
    "word",
    "workspace",
}

GENERIC_TITLE_TOKENS = {
    "add",
    "and",
    "app",
    "custom",
    "for",
    "from",
    "meet",
    "mode",
    "more",
    "new",
    "notion",
    "now",
    "platform",
    "the",
    "with",
}

OUTPUT_FIELDNAMES = [
    "candidate_id",
    "batch_id",
    "sentiment_bucket",
    "theme_id",
    "theme_name_zh",
    "theme_affected_area",
    "theme_severity",
    "theme_evidence_count",
    "first_evidence_at",
    "last_evidence_at",
    "release_id",
    "release_date",
    "release_version",
    "release_title",
    "release_affected_area",
    "match_score",
    "match_level",
    "area_overlap",
    "matched_keywords",
    "matched_specific_keywords",
    "matched_title_terms",
    "pre_release_evidence_count",
    "post_release_evidence_count",
    "review_timing_status",
    "resolution_hint",
    "source_url",
]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def split_pipe(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def tokenize(value: str) -> set[str]:
    text = str(value or "").lower()
    tokens = set(re.findall(r"[a-z][a-z0-9_+-]{2,}", text))
    expanded = set(tokens)
    for token in tokens:
        expanded.update(part for part in token.split("_") if len(part) >= 3)
    return expanded


def is_broad_keyword(keyword: str) -> bool:
    normalized = keyword.lower().replace(" ", "_").strip()
    return normalized in BROAD_KEYWORDS or keyword.lower().strip() in BROAD_KEYWORDS


def build_theme_record(batch_id: str, sentiment_bucket: str, theme: dict) -> dict:
    evidence = theme.get("evidence", [])
    evidence_dates = [
        item.get("review_created_at", "")
        for item in evidence
        if item.get("review_created_at")
    ]
    parsed_dates = [parse_datetime(value) for value in evidence_dates]
    parsed_dates = [value for value in parsed_dates if value is not None]

    match_parts = [
        theme.get("theme_id", ""),
        theme.get("theme_name_zh", ""),
        theme.get("summary_zh", ""),
        theme.get("affected_area", ""),
        theme.get("suggested_action_zh", ""),
    ]
    for item in evidence:
        match_parts.extend(
            [
                item.get("quote", ""),
                item.get("reason_zh", ""),
            ]
        )

    return {
        "batch_id": batch_id,
        "sentiment_bucket": sentiment_bucket,
        "theme_id": theme.get("theme_id", ""),
        "theme_name_zh": theme.get("theme_name_zh", ""),
        "affected_area": theme.get("affected_area", ""),
        "severity": theme.get("severity", ""),
        "evidence_count": len(evidence),
        "first_evidence_at": min(parsed_dates).isoformat() if parsed_dates else "",
        "last_evidence_at": max(parsed_dates).isoformat() if parsed_dates else "",
        "evidence_dates": evidence_dates,
        "match_text": normalize_text(" ".join(str(part or "") for part in match_parts)),
    }


def load_theme_records(llm_output_dir: Path) -> list[dict]:
    records = []
    for path in sorted(llm_output_dir.glob("*_output.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        batch_id = data.get("batch_id", path.stem.replace("_output", ""))
        sentiment_bucket = data.get("sentiment_bucket", "")
        for theme in data.get("themes", []):
            records.append(build_theme_record(batch_id, sentiment_bucket, theme))
    return records


def load_release_notes(release_notes_path: Path) -> list[dict]:
    with release_notes_path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def score_release_candidate(theme: dict, release: dict) -> dict | None:
    theme_area = theme.get("affected_area", "")
    release_areas = set(split_pipe(release.get("affected_area", "")))
    area_overlap = sorted({theme_area} & release_areas) if theme_area else []

    release_keywords = split_pipe(release.get("keywords", ""))
    theme_tokens = tokenize(theme.get("match_text", ""))
    matched_keywords = sorted(
        keyword
        for keyword in release_keywords
        if keyword.lower() in theme.get("match_text", "").lower()
        or keyword.lower().replace(" ", "_") in theme_tokens
        or keyword.lower() in theme_tokens
    )

    matched_specific_keywords = [
        keyword for keyword in matched_keywords if not is_broad_keyword(keyword)
    ]
    matched_broad_keywords = [
        keyword for keyword in matched_keywords if is_broad_keyword(keyword)
    ]
    keyword_score = len(matched_specific_keywords) * 2 + min(len(matched_broad_keywords), 1)
    area_score = 2 if area_overlap else 0
    title_tokens = (
        tokenize(release.get("release_title", ""))
        - GENERIC_TITLE_TOKENS
        - BROAD_KEYWORDS
    )
    title_overlap = sorted(title_tokens & theme_tokens)
    title_score = min(len(title_overlap) * 2, 4)
    match_score = area_score + keyword_score + title_score

    if not matched_specific_keywords and not (area_overlap and title_overlap):
        return None
    if not area_overlap and len(matched_specific_keywords) < 2 and len(title_overlap) < 2:
        return None
    if match_score < DEFAULT_MIN_SCORE:
        return None

    if area_overlap and (len(matched_specific_keywords) >= 2 or len(title_overlap) >= 2):
        match_level = "strong"
    elif area_overlap or matched_specific_keywords:
        match_level = "medium"
    else:
        return None

    return {
        "match_score": match_score,
        "match_level": match_level,
        "area_overlap": "|".join(area_overlap),
        "matched_keywords": "|".join(matched_keywords),
        "matched_specific_keywords": "|".join(matched_specific_keywords),
        "matched_title_terms": "|".join(title_overlap),
    }


def count_evidence_around_release(theme: dict, release_date: str) -> dict:
    release_dt = parse_datetime(f"{release_date}T00:00:00+00:00")
    pre_count = 0
    post_count = 0
    if release_dt is None:
        return {
            "pre_release_evidence_count": 0,
            "post_release_evidence_count": 0,
        }

    for value in theme.get("evidence_dates", []):
        evidence_dt = parse_datetime(value)
        if evidence_dt is None:
            continue
        if evidence_dt < release_dt:
            pre_count += 1
        else:
            post_count += 1

    return {
        "pre_release_evidence_count": pre_count,
        "post_release_evidence_count": post_count,
    }


def classify_review_timing(pre_count: int, post_count: int) -> dict:
    if pre_count > 0 and post_count > 0:
        return {
            "review_timing_status": "reported_before_and_after_release",
            "resolution_hint": "still_reported_after_release",
        }
    if pre_count > 0:
        return {
            "review_timing_status": "reported_before_release_only",
            "resolution_hint": "possibly_addressed_no_later_evidence_in_sample",
        }
    if post_count > 0:
        return {
            "review_timing_status": "reported_after_release_only",
            "resolution_hint": "not_addressed_by_this_release",
        }
    return {
        "review_timing_status": "no_dated_evidence",
        "resolution_hint": "unknown_no_dated_evidence",
    }


def build_candidate_row(theme: dict, release: dict, score: dict) -> dict:
    evidence_counts = count_evidence_around_release(theme, release.get("release_date", ""))
    timing = classify_review_timing(
        evidence_counts["pre_release_evidence_count"],
        evidence_counts["post_release_evidence_count"],
    )
    candidate_id = (
        f"{theme['batch_id']}::{theme['theme_id']}::{release.get('release_id', '')}"
    )
    return {
        "candidate_id": candidate_id,
        "batch_id": theme["batch_id"],
        "sentiment_bucket": theme["sentiment_bucket"],
        "theme_id": theme["theme_id"],
        "theme_name_zh": theme["theme_name_zh"],
        "theme_affected_area": theme["affected_area"],
        "theme_severity": theme["severity"],
        "theme_evidence_count": theme["evidence_count"],
        "first_evidence_at": theme["first_evidence_at"],
        "last_evidence_at": theme["last_evidence_at"],
        "release_id": release.get("release_id", ""),
        "release_date": release.get("release_date", ""),
        "release_version": release.get("release_version", ""),
        "release_title": release.get("release_title", ""),
        "release_affected_area": release.get("affected_area", ""),
        "match_score": score["match_score"],
        "match_level": score["match_level"],
        "area_overlap": score["area_overlap"],
        "matched_keywords": score["matched_keywords"],
        "matched_specific_keywords": score["matched_specific_keywords"],
        "matched_title_terms": score["matched_title_terms"],
        "pre_release_evidence_count": evidence_counts["pre_release_evidence_count"],
        "post_release_evidence_count": evidence_counts["post_release_evidence_count"],
        "review_timing_status": timing["review_timing_status"],
        "resolution_hint": timing["resolution_hint"],
        "source_url": release.get("source_url", ""),
    }


def build_candidates(
    theme_records: list[dict],
    release_notes: list[dict],
    min_score: int = DEFAULT_MIN_SCORE,
) -> list[dict]:
    candidates = []
    for theme in theme_records:
        for release in release_notes:
            score = score_release_candidate(theme, release)
            if score is None:
                continue
            if int(score["match_score"]) < min_score:
                continue
            candidates.append(build_candidate_row(theme, release, score))

    return sorted(
        candidates,
        key=lambda row: (
            row["batch_id"],
            row["theme_id"],
            -int(row["match_score"]),
            row["release_date"],
        ),
    )


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def summarize_candidates(theme_count: int, release_count: int, candidates: list[dict]) -> dict:
    by_level = Counter(row["match_level"] for row in candidates)
    by_bucket = Counter(row["sentiment_bucket"] for row in candidates)
    by_area = Counter(row["theme_affected_area"] for row in candidates)
    by_resolution_hint = Counter(row["resolution_hint"] for row in candidates)
    linked_theme_ids = {
        (row["batch_id"], row["theme_id"])
        for row in candidates
    }
    return {
        "theme_count": theme_count,
        "release_count": release_count,
        "candidate_count": len(candidates),
        "linked_theme_count": len(linked_theme_ids),
        "by_match_level": dict(by_level),
        "by_sentiment_bucket": dict(by_bucket),
        "by_theme_affected_area": dict(by_area),
        "by_resolution_hint": dict(by_resolution_hint),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build candidate links between LLM VOC themes and public product updates."
    )
    parser.add_argument("--llm-output-dir", type=Path, default=DEFAULT_LLM_OUTPUT_DIR)
    parser.add_argument("--release-notes", type=Path, default=DEFAULT_RELEASE_NOTES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--min-score", type=int, default=DEFAULT_MIN_SCORE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    themes = load_theme_records(args.llm_output_dir)
    releases = load_release_notes(args.release_notes)
    candidates = build_candidates(themes, releases, min_score=args.min_score)
    write_csv(candidates, args.output)
    summary = summarize_candidates(len(themes), len(releases), candidates)
    write_json(summary, args.summary_output)
    print(
        f"Linked {summary['linked_theme_count']} of {summary['theme_count']} theme(s) "
        f"to {summary['candidate_count']} release candidate(s). "
        f"Saved to {args.output}"
    )


if __name__ == "__main__":
    main()
