import argparse
import csv
from pathlib import Path


DEFAULT_INPUT = Path("data/interim/reviews_cleaned_2025_onward_en_us.csv")
DEFAULT_OUTPUT = Path("data/processed/reviews_with_sentiment_2025_onward_en_us.csv")
DEFAULT_MODEL = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
DEFAULT_CONFIDENCE_THRESHOLD = 0.8
DEFAULT_BATCH_SIZE = 32
DEFAULT_TEXT_COLUMN = "review_text_for_model"


def parse_rating(value: str | int | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def assign_sentiment_bucket(
    label: str,
    confidence: float,
    rating: str | int | None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> str:
    normalized_label = label.upper()
    parsed_rating = parse_rating(rating)

    if confidence < confidence_threshold:
        return "mixed_or_uncertain"

    if parsed_rating == 3:
        return "mixed_or_uncertain"

    if normalized_label == "POSITIVE":
        if parsed_rating in (1, 2):
            return "mixed_or_uncertain"
        return "positive"

    if normalized_label == "NEGATIVE":
        if parsed_rating in (4, 5):
            return "mixed_or_uncertain"
        return "negative"

    return "mixed_or_uncertain"


def apply_sentiment_results(
    rows: list[dict],
    sentiment_results: list[dict],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    model_name: str = DEFAULT_MODEL,
) -> list[dict]:
    if len(rows) != len(sentiment_results):
        raise ValueError("Rows and sentiment results must have the same length.")

    enriched_rows = []
    for row, result in zip(rows, sentiment_results):
        label = str(result["label"]).upper()
        score = float(result["score"])

        enriched_row = dict(row)
        enriched_row["sentiment_label"] = label
        enriched_row["sentiment_score"] = f"{score:.6f}"
        enriched_row["sentiment_bucket"] = assign_sentiment_bucket(
            label,
            score,
            row.get("score"),
            confidence_threshold=confidence_threshold,
        )
        enriched_row["sentiment_model"] = model_name
        enriched_rows.append(enriched_row)

    return enriched_rows


def load_classifier(model_name: str):
    from transformers import pipeline

    return pipeline("sentiment-analysis", model=model_name)


def classify_rows(
    rows: list[dict],
    model_name: str = DEFAULT_MODEL,
    text_column: str = DEFAULT_TEXT_COLUMN,
    batch_size: int = DEFAULT_BATCH_SIZE,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[dict]:
    classifier = load_classifier(model_name)
    texts = [row[text_column] for row in rows]
    results = classifier(
        texts,
        batch_size=batch_size,
        truncation=True,
        max_length=512,
    )
    return apply_sentiment_results(
        rows,
        results,
        confidence_threshold=confidence_threshold,
        model_name=model_name,
    )


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
        description="Classify cleaned Google Play reviews with a sentiment model."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--text-column", default=DEFAULT_TEXT_COLUMN)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.input)
    enriched_rows = classify_rows(
        rows,
        model_name=args.model,
        text_column=args.text_column,
        batch_size=args.batch_size,
        confidence_threshold=args.confidence_threshold,
    )
    write_csv(enriched_rows, args.output)
    print(f"Saved {len(enriched_rows)} sentiment-classified reviews to {args.output}")


if __name__ == "__main__":
    main()
