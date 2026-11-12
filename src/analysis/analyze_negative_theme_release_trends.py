import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_REVIEWS = Path("data/processed/reviews_with_sentiment_2025_onward_en_us.csv")
DEFAULT_CANDIDATES = Path("outputs/tables/theme_release_candidates.csv")
DEFAULT_RULES = Path("configs/negative_theme_monitoring_rules.json")
DEFAULT_OUTPUT = Path("outputs/tables/negative_theme_release_trends.csv")
DEFAULT_EVIDENCE_OUTPUT = Path(
    "outputs/tables/negative_theme_release_trend_evidence.csv"
)
DEFAULT_SUMMARY_OUTPUT = Path(
    "outputs/tables/negative_theme_release_trends_summary.json"
)

TREND_FIELDNAMES = [
    "candidate_id",
    "theme_id",
    "theme_name_zh",
    "theme_affected_area",
    "release_id",
    "release_date",
    "release_title",
    "release_scope",
    "window_days",
    "pre_window_complete",
    "post_window_complete",
    "pre_eligible_count",
    "post_eligible_count",
    "pre_match_count",
    "post_match_count",
    "pre_match_rate",
    "post_match_rate",
    "rate_change_percentage_points",
    "observation_status",
]
EVIDENCE_FIELDNAMES = [
    "candidate_id",
    "theme_id",
    "release_id",
    "release_date",
    "period",
    "matched_phrases",
    "review_id",
    "review_created_at",
    "app_version",
    "score",
    "review_text_clean",
]


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


def normalize_match_text(value: str) -> str:
    return str(value or "").casefold()


def review_matches_rule(review_text: str, phrases: list[str]) -> tuple[bool, list[str]]:
    normalized_text = normalize_match_text(review_text)
    matched_phrases = [
        phrase
        for phrase in phrases
        if normalize_match_text(phrase) in normalized_text
    ]
    return bool(matched_phrases), matched_phrases


def classify_observation(
    *,
    pre_eligible_count: int,
    post_eligible_count: int,
    post_match_count: int,
    pre_window_complete: bool,
    post_window_complete: bool,
    minimum_eligible_reviews: int = 20,
) -> str:
    if not pre_window_complete:
        return "incomplete_pre_window"
    if not post_window_complete:
        return "incomplete_post_window"
    if (
        pre_eligible_count < minimum_eligible_reviews
        or post_eligible_count < minimum_eligible_reviews
    ):
        return "insufficient_observations"
    if post_match_count >= 3:
        return "continued_after_release"
    if post_match_count >= 1:
        return "limited_post_evidence"
    return "not_observed_after_release"


def calculate_rate(match_count: int, eligible_count: int) -> float | str:
    if eligible_count == 0:
        return ""
    return round(match_count / eligible_count, 6)


def build_evidence_row(
    *,
    candidate: dict,
    period: str,
    matched_phrases: list[str],
    review: dict,
) -> dict:
    return {
        "candidate_id": candidate["candidate_id"],
        "theme_id": candidate["theme_id"],
        "release_id": candidate["release_id"],
        "release_date": candidate["release_date"],
        "period": period,
        "matched_phrases": "|".join(matched_phrases),
        "review_id": review.get("review_id", ""),
        "review_created_at": review.get("review_created_at", ""),
        "app_version": review.get("app_version", ""),
        "score": review.get("score", ""),
        "review_text_clean": review.get("review_text_clean", ""),
    }


def build_trend_rows(
    reviews: list[dict],
    candidates: list[dict],
    rules: dict,
) -> tuple[list[dict], list[dict]]:
    candidate_by_id = {
        candidate.get("candidate_id", ""): candidate
        for candidate in candidates
    }
    negative_reviews = [
        review
        for review in reviews
        if review.get("sentiment_bucket") == "negative"
        and parse_datetime(review.get("review_created_at", "")) is not None
    ]
    review_dates = [
        parse_datetime(review["review_created_at"])
        for review in negative_reviews
    ]
    corpus_start = min(review_dates) if review_dates else None
    corpus_end = max(review_dates) if review_dates else None
    window_days = int(rules.get("window_days", 28))
    minimum_eligible_reviews = int(rules.get("minimum_eligible_reviews", 20))
    release_scope = rules.get("release_scope", "general_product_release")
    trend_rows = []
    evidence_rows = []

    for rule in rules.get("rules", []):
        candidate_id = rule.get("candidate_id", "")
        candidate = candidate_by_id.get(candidate_id)
        if candidate is None:
            raise ValueError(f"No candidate found for rule candidate_id={candidate_id}")

        release_dt = parse_datetime(f"{candidate.get('release_date', '')}T00:00:00+00:00")
        if release_dt is None:
            raise ValueError(f"Invalid release_date for candidate_id={candidate_id}")

        pre_start = release_dt - timedelta(days=window_days)
        post_end = release_dt + timedelta(days=window_days)
        pre_window_complete = bool(corpus_start and corpus_start <= pre_start)
        post_window_complete = bool(corpus_end and corpus_end >= post_end)
        pre_reviews = []
        post_reviews = []
        for review in negative_reviews:
            review_dt = parse_datetime(review["review_created_at"])
            if pre_start <= review_dt < release_dt:
                pre_reviews.append(review)
            elif release_dt <= review_dt < post_end:
                post_reviews.append(review)

        phrases = rule.get("match_any_phrases", [])
        pre_matches = [
            (review, review_matches_rule(review.get("review_text_clean", ""), phrases)[1])
            for review in pre_reviews
        ]
        pre_matches = [item for item in pre_matches if item[1]]
        post_matches = [
            (review, review_matches_rule(review.get("review_text_clean", ""), phrases)[1])
            for review in post_reviews
        ]
        post_matches = [item for item in post_matches if item[1]]
        pre_rate = calculate_rate(len(pre_matches), len(pre_reviews))
        post_rate = calculate_rate(len(post_matches), len(post_reviews))
        rate_change = ""
        if pre_rate != "" and post_rate != "":
            rate_change = round((post_rate - pre_rate) * 100, 4)

        observation_status = classify_observation(
            pre_eligible_count=len(pre_reviews),
            post_eligible_count=len(post_reviews),
            post_match_count=len(post_matches),
            pre_window_complete=pre_window_complete,
            post_window_complete=post_window_complete,
            minimum_eligible_reviews=minimum_eligible_reviews,
        )
        trend_rows.append(
            {
                "candidate_id": candidate_id,
                "theme_id": candidate.get("theme_id", ""),
                "theme_name_zh": candidate.get("theme_name_zh", ""),
                "theme_affected_area": candidate.get("theme_affected_area", ""),
                "release_id": candidate.get("release_id", ""),
                "release_date": candidate.get("release_date", ""),
                "release_title": candidate.get("release_title", ""),
                "release_scope": release_scope,
                "window_days": window_days,
                "pre_window_complete": pre_window_complete,
                "post_window_complete": post_window_complete,
                "pre_eligible_count": len(pre_reviews),
                "post_eligible_count": len(post_reviews),
                "pre_match_count": len(pre_matches),
                "post_match_count": len(post_matches),
                "pre_match_rate": pre_rate,
                "post_match_rate": post_rate,
                "rate_change_percentage_points": rate_change,
                "observation_status": observation_status,
            }
        )
        evidence_rows.extend(
            build_evidence_row(
                candidate=candidate,
                period="pre",
                matched_phrases=matched_phrases,
                review=review,
            )
            for review, matched_phrases in pre_matches
        )
        evidence_rows.extend(
            build_evidence_row(
                candidate=candidate,
                period="post",
                matched_phrases=matched_phrases,
                review=review,
            )
            for review, matched_phrases in post_matches
        )

    return trend_rows, evidence_rows


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(rows: list[dict], fieldnames: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def summarize_trends(
    trend_rows: list[dict],
    evidence_rows: list[dict],
    reviews: list[dict],
    rules: dict,
) -> dict:
    negative_dates = [
        parse_datetime(review.get("review_created_at", ""))
        for review in reviews
        if review.get("sentiment_bucket") == "negative"
        and parse_datetime(review.get("review_created_at", "")) is not None
    ]
    return {
        "release_scope": rules.get("release_scope", "general_product_release"),
        "window_days": int(rules.get("window_days", 28)),
        "minimum_eligible_reviews": int(rules.get("minimum_eligible_reviews", 20)),
        "trend_row_count": len(trend_rows),
        "evidence_row_count": len(evidence_rows),
        "review_corpus_min_at": min(negative_dates).isoformat() if negative_dates else "",
        "review_corpus_max_at": max(negative_dates).isoformat() if negative_dates else "",
        "by_observation_status": dict(
            Counter(row["observation_status"] for row in trend_rows)
        ),
    }


def analyze_negative_theme_release_trends(
    *,
    reviews_path: Path,
    candidates_path: Path,
    rules_path: Path,
    output_path: Path,
    evidence_output_path: Path,
    summary_output_path: Path,
) -> dict:
    reviews = read_csv(reviews_path)
    candidates = read_csv(candidates_path)
    rules = read_json(rules_path)
    trend_rows, evidence_rows = build_trend_rows(reviews, candidates, rules)
    summary = summarize_trends(trend_rows, evidence_rows, reviews, rules)
    write_csv(trend_rows, TREND_FIELDNAMES, output_path)
    write_csv(evidence_rows, EVIDENCE_FIELDNAMES, evidence_output_path)
    write_json(summary, summary_output_path)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare selected negative review themes before and after general releases."
    )
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--evidence-output", type=Path, default=DEFAULT_EVIDENCE_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = analyze_negative_theme_release_trends(
        reviews_path=args.reviews,
        candidates_path=args.candidates,
        rules_path=args.rules,
        output_path=args.output,
        evidence_output_path=args.evidence_output,
        summary_output_path=args.summary_output,
    )
    print(
        f"Wrote {summary['trend_row_count']} trend row(s) and "
        f"{summary['evidence_row_count']} evidence row(s) to {args.output}"
    )


if __name__ == "__main__":
    main()
