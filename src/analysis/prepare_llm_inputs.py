import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


DEFAULT_INPUT = Path("data/processed/reviews_with_sentiment_2025_onward_en_us.csv")
DEFAULT_OUTPUT_DIR = Path("data/processed/llm_inputs")
DEFAULT_BATCH_SIZE = 150
DEFAULT_POSITIVE_LIMIT = 500
BUCKETS = ("positive", "negative", "mixed_or_uncertain")
LLM_FIELDS = (
    "review_id",
    "score",
    "review_created_at",
    "app_version",
    "thumbs_up_count",
    "sentiment_label",
    "sentiment_score",
    "sentiment_bucket",
    "review_text_for_model",
)


def parse_int(value: str | int | None, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def select_rows_for_bucket(
    rows: list[dict],
    bucket: str,
    positive_limit: int = DEFAULT_POSITIVE_LIMIT,
) -> tuple[list[dict], str]:
    bucket_rows = [row for row in rows if row.get("sentiment_bucket") == bucket]

    if bucket != "positive":
        return bucket_rows, "all"

    selected = sorted(
        bucket_rows,
        key=lambda row: (
            parse_int(row.get("thumbs_up_count")),
            parse_int(row.get("review_text_char_count")),
            row.get("review_created_at", ""),
        ),
        reverse=True,
    )[:positive_limit]
    return selected, f"top_{positive_limit}_by_thumbs_up_then_text_length"


def prepare_records(rows: list[dict]) -> list[dict]:
    return [{field: row.get(field, "") for field in LLM_FIELDS} for row in rows]


def build_batches(
    rows: list[dict],
    bucket: str,
    batch_size: int,
    source_file: str,
    selection_strategy: str,
) -> list[dict]:
    records = prepare_records(rows)
    batches = []
    total_batches = math.ceil(len(records) / batch_size) if records else 0

    for index in range(total_batches):
        start = index * batch_size
        end = start + batch_size
        batch_records = records[start:end]
        batches.append(
            {
                "batch_id": f"{bucket}_{index + 1:03d}",
                "sentiment_bucket": bucket,
                "source_file": source_file,
                "selection_strategy": selection_strategy,
                "batch_index": index + 1,
                "total_batches": total_batches,
                "review_count": len(batch_records),
                "reviews": batch_records,
            }
        )

    return batches


def write_jsonl_batches(batches: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for batch in batches:
            file.write(json.dumps(batch, ensure_ascii=False) + "\n")


def write_manifest(manifest: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_csv(input_path: Path) -> list[dict]:
    with input_path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def prepare_llm_inputs(
    input_path: Path,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    positive_limit: int = DEFAULT_POSITIVE_LIMIT,
) -> dict:
    rows = read_csv(input_path)
    manifest = {
        "source_file": str(input_path),
        "output_dir": str(output_dir),
        "batch_size": batch_size,
        "positive_limit": positive_limit,
        "input_rows": len(rows),
        "source_bucket_counts": dict(Counter(row.get("sentiment_bucket") for row in rows)),
        "buckets": {},
    }

    for bucket in BUCKETS:
        selected_rows, selection_strategy = select_rows_for_bucket(
            rows,
            bucket,
            positive_limit=positive_limit,
        )
        batches = build_batches(
            selected_rows,
            bucket=bucket,
            batch_size=batch_size,
            source_file=str(input_path),
            selection_strategy=selection_strategy,
        )
        output_path = output_dir / f"{bucket}_llm_batches.jsonl"
        write_jsonl_batches(batches, output_path)

        manifest["buckets"][bucket] = {
            "source_rows": manifest["source_bucket_counts"].get(bucket, 0),
            "selected_rows": len(selected_rows),
            "batch_count": len(batches),
            "output_file": str(output_path),
            "selection_strategy": selection_strategy,
        }

    manifest_path = output_dir / "manifest.json"
    write_manifest(manifest, manifest_path)
    manifest["manifest_file"] = str(manifest_path)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare bucketed JSONL batches for later LLM analysis."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--positive-limit", type=int, default=DEFAULT_POSITIVE_LIMIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = prepare_llm_inputs(
        input_path=args.input,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        positive_limit=args.positive_limit,
    )
    print(f"Prepared LLM inputs in {args.output_dir}")
    for bucket, details in manifest["buckets"].items():
        print(
            f"{bucket}: selected={details['selected_rows']} "
            f"batches={details['batch_count']} "
            f"strategy={details['selection_strategy']}"
        )


if __name__ == "__main__":
    main()
