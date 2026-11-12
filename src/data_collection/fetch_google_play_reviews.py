import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews


DEFAULT_APP_ID = "notion.id"
DEFAULT_LANG = "en"
DEFAULT_COUNTRY = "us"
DEFAULT_OUTPUT = Path("data/raw/notion_android_reviews_google_play.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Google Play reviews for the Notion Android app."
    )
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--lang", default=DEFAULT_LANG)
    parser.add_argument("--country", default=DEFAULT_COUNTRY)
    parser.add_argument("--cutoff", default="2025-01-01")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def normalize_review(review: dict) -> dict:
    at = review.get("at")
    if at and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)

    return {
        "review_id": review.get("reviewId"),
        "user_name": review.get("userName"),
        "score": review.get("score"),
        "thumbs_up_count": review.get("thumbsUpCount"),
        "review_created_at": at.isoformat() if at else None,
        "review_text": review.get("content"),
        "reply_text": review.get("replyContent"),
        "reply_created_at": review.get("repliedAt").isoformat()
        if review.get("repliedAt")
        else None,
        "app_version": review.get("reviewCreatedVersion"),
    }


def fetch_reviews(
    app_id: str,
    lang: str,
    country: str,
    cutoff: datetime,
    batch_size: int,
    max_pages: int,
) -> list[dict]:
    all_reviews = []
    seen_review_ids = set()
    continuation_token = None

    for _ in range(max_pages):
        page_reviews, continuation_token = reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=continuation_token,
        )

        if not page_reviews:
            break

        stop_at_cutoff = False
        for review in page_reviews:
            review_id = review.get("reviewId")
            if review_id in seen_review_ids:
                continue

            created_at = review.get("at")
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            if created_at and created_at < cutoff:
                stop_at_cutoff = True
                continue

            seen_review_ids.add(review_id)
            all_reviews.append(normalize_review(review))

        if stop_at_cutoff or continuation_token is None:
            break

    return all_reviews


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "review_id",
        "user_name",
        "score",
        "thumbs_up_count",
        "review_created_at",
        "review_text",
        "reply_text",
        "reply_created_at",
        "app_version",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    cutoff = datetime.fromisoformat(args.cutoff).replace(tzinfo=timezone.utc)

    rows = fetch_reviews(
        app_id=args.app_id,
        lang=args.lang,
        country=args.country,
        cutoff=cutoff,
        batch_size=args.batch_size,
        max_pages=args.max_pages,
    )
    write_csv(rows, args.output)
    print(f"Saved {len(rows)} reviews to {args.output}")


if __name__ == "__main__":
    main()
