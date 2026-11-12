import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Iterable


DEFAULT_BATCH_DIR = Path("data/processed/llm_inputs")
DEFAULT_INPUT_DIR = Path("outputs/reports/llm_batch_outputs")
DEFAULT_OUTPUT_DIR = Path("outputs/reports/llm_batch_outputs_enriched")
DEFAULT_METADATA_FIELDS = (
    "review_created_at",
    "app_version",
    "thumbs_up_count",
    "sentiment_label",
    "sentiment_score",
    "sentiment_bucket",
)


def load_review_metadata(
    batch_paths: Iterable[Path],
    metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS,
) -> dict:
    metadata = {}
    fields = tuple(metadata_fields)

    for batch_path in batch_paths:
        with batch_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                batch = json.loads(line)
                for review in batch.get("reviews", []):
                    review_id = str(review.get("review_id") or "").strip()
                    if not review_id:
                        raise ValueError(
                            f"Missing review_id in {batch_path} line {line_number}"
                        )
                    if review_id in metadata:
                        raise ValueError(f"Duplicate review_id in LLM batches: {review_id}")

                    metadata[review_id] = {
                        field: review[field] for field in fields if field in review
                    }

    return metadata


def enrich_review_reference(
    reference,
    review_metadata: dict,
    metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS,
) -> dict:
    if isinstance(reference, str):
        original = {"review_id": reference}
    else:
        original = dict(reference)

    review_id = str(original.get("review_id") or "").strip()
    if not review_id:
        raise ValueError("LLM output review reference is missing review_id")
    if review_id not in review_metadata:
        raise ValueError(f"review_id not found in source metadata: {review_id}")

    enriched = {"review_id": review_id}
    source = review_metadata[review_id]
    for field in metadata_fields:
        if field in source:
            enriched[field] = source[field]

    for key, value in original.items():
        if key != "review_id":
            enriched[key] = value

    return enriched


def enrich_llm_output(
    llm_output: dict,
    review_metadata: dict,
    metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS,
) -> dict:
    enriched = deepcopy(llm_output)

    for theme in enriched.get("themes", []):
        theme["evidence"] = [
            enrich_review_reference(evidence, review_metadata, metadata_fields)
            for evidence in theme.get("evidence", [])
        ]

    enriched["excluded_reviews"] = [
        enrich_review_reference(excluded, review_metadata, metadata_fields)
        for excluded in enriched.get("excluded_reviews", [])
    ]

    return enriched


def write_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def enrich_output_file(
    input_path: Path,
    output_path: Path,
    review_metadata: dict,
    metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS,
) -> dict:
    llm_output = json.loads(input_path.read_text(encoding="utf-8"))
    enriched = enrich_llm_output(llm_output, review_metadata, metadata_fields)
    write_json(enriched, output_path)
    return enriched


def iter_llm_output_paths(input_dir: Path, include_smoke: bool = False) -> list[Path]:
    output_paths = sorted(input_dir.glob("*_output.json"))
    if include_smoke:
        return output_paths

    return [path for path in output_paths if "smoke" not in path.name]


def enrich_output_dir(
    input_dir: Path,
    output_dir: Path,
    review_metadata: dict,
    metadata_fields: Iterable[str] = DEFAULT_METADATA_FIELDS,
    include_smoke: bool = False,
) -> list[Path]:
    written_paths = []
    for input_path in iter_llm_output_paths(input_dir, include_smoke=include_smoke):
        output_path = output_dir / input_path.name
        enrich_output_file(input_path, output_path, review_metadata, metadata_fields)
        written_paths.append(output_path)

    return written_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join source review metadata back into LLM VOC JSON outputs by review_id."
    )
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--metadata-fields",
        nargs="+",
        default=list(DEFAULT_METADATA_FIELDS),
        help="Review metadata fields to copy into evidence and excluded_reviews.",
    )
    parser.add_argument(
        "--include-smoke",
        action="store_true",
        help="Also enrich smoke-test output files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batch_paths = sorted(args.batch_dir.glob("*_llm_batches.jsonl"))
    if not batch_paths:
        raise ValueError(f"No LLM batch files found in {args.batch_dir}")

    review_metadata = load_review_metadata(batch_paths, args.metadata_fields)
    written_paths = enrich_output_dir(
        args.input_dir,
        args.output_dir,
        review_metadata,
        args.metadata_fields,
        include_smoke=args.include_smoke,
    )
    print(
        "Enriched "
        f"{len(written_paths)} LLM output file(s) to {args.output_dir} "
        f"using {len(review_metadata)} review metadata record(s)."
    )


if __name__ == "__main__":
    main()
