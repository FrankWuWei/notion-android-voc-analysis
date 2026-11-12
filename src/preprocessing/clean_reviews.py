import argparse
import csv
import html
import re
import unicodedata
from collections import Counter
from pathlib import Path


DEFAULT_INPUT = Path("data/raw/notion_android_reviews_google_play_2025_onward_en_us.csv")
DEFAULT_OUTPUT = Path("data/interim/reviews_cleaned_2025_onward_en_us.csv")
DEFAULT_MIN_TEXT_CHARS = 3
DEFAULT_MAX_MODEL_CHARS = 2000


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""

    normalized = html.unescape(str(text))
    normalized = unicodedata.normalize("NFKC", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def meaningful_char_count(text: str) -> int:
    return sum(1 for character in text if character.isalnum())


def truncate_for_model(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def clean_rows(
    rows: list[dict],
    min_text_chars: int = DEFAULT_MIN_TEXT_CHARS,
    max_model_chars: int = DEFAULT_MAX_MODEL_CHARS,
) -> tuple[list[dict], Counter]:
    cleaned_rows = []
    seen_review_ids = set()
    stats = Counter()
    stats["input_rows"] = len(rows)

    for row in rows:
        review_id = normalize_text(row.get("review_id"))
        if review_id and review_id in seen_review_ids:
            stats["dropped_duplicate_review_id"] += 1
            continue

        clean_text = normalize_text(row.get("review_text"))
        if not clean_text:
            stats["dropped_empty_text"] += 1
            continue

        if meaningful_char_count(clean_text) < min_text_chars:
            stats["dropped_too_short_text"] += 1
            continue

        model_text, was_truncated = truncate_for_model(clean_text, max_model_chars)
        if was_truncated:
            stats["truncated_for_model"] += 1

        if review_id:
            seen_review_ids.add(review_id)

        cleaned_row = dict(row)
        cleaned_row["review_text"] = row.get("review_text", "")
        cleaned_row["review_text_clean"] = clean_text
        cleaned_row["review_text_for_model"] = model_text
        cleaned_row["review_text_char_count"] = str(len(clean_text))
        cleaned_row["review_text_was_truncated"] = str(was_truncated).lower()
        cleaned_rows.append(cleaned_row)

    stats["output_rows"] = len(cleaned_rows)
    return cleaned_rows, stats


def read_csv(input_path: Path) -> list[dict]:
    with input_path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Light-clean Google Play review text before sentiment analysis."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-text-chars", type=int, default=DEFAULT_MIN_TEXT_CHARS)
    parser.add_argument("--max-model-chars", type=int, default=DEFAULT_MAX_MODEL_CHARS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.input)
    cleaned_rows, stats = clean_rows(
        rows,
        min_text_chars=args.min_text_chars,
        max_model_chars=args.max_model_chars,
    )
    write_csv(cleaned_rows, args.output)

    print(f"Saved {stats['output_rows']} cleaned reviews to {args.output}")
    for key in sorted(stats):
        print(f"{key}: {stats[key]}")


if __name__ == "__main__":
    main()
