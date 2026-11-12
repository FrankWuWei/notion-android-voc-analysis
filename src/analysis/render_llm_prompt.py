import argparse
import json
from pathlib import Path


DEFAULT_TEMPLATE = Path("prompts/voc_theme_extraction.v1.md")
DEFAULT_BATCH_FILE = Path("data/processed/llm_inputs/negative_llm_batches.jsonl")
DEFAULT_BATCH_ID = "negative_001"
DEFAULT_OUTPUT = Path("outputs/reports/llm_prompts/negative_001_prompt.md")

OUTPUT_SCHEMA = {
    "batch_id": "string",
    "sentiment_bucket": "positive | negative | mixed_or_uncertain",
    "analysis_language": "zh-Hant",
    "themes": [
        {
            "theme_id": "snake_case_string",
            "theme_name_zh": "string",
            "summary_zh": "string",
            "affected_area": "mobile_app | sync | performance | editing | search | ai | account | pricing | onboarding | other",
            "severity": "high | medium | low",
            "evidence": [
                {
                    "review_id": "string",
                    "score": "string",
                    "quote": "exact quote from review_text_for_model",
                    "reason_zh": "string",
                }
            ],
            "suggested_action_zh": "string",
        }
    ],
    "excluded_reviews": [
        {
            "review_id": "string",
            "reason": "non_english | insufficient_information | unrelated",
        }
    ],
}


def load_jsonl_batch(batch_path: Path, batch_id: str) -> dict:
    with batch_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            batch = json.loads(line)
            if batch.get("batch_id") == batch_id:
                return batch

    raise ValueError(f"Batch id not found: {batch_id}")


def render_prompt(template: str, batch: dict, output_schema: dict) -> str:
    replacements = {
        "{{batch_id}}": str(batch["batch_id"]),
        "{{sentiment_bucket}}": str(batch["sentiment_bucket"]),
        "{{review_count}}": str(batch["review_count"]),
        "{{reviews_json}}": json.dumps(
            batch["reviews"],
            ensure_ascii=False,
            indent=2,
        ),
        "{{output_schema_json}}": json.dumps(
            output_schema,
            ensure_ascii=False,
            indent=2,
        ),
    }

    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)

    unresolved = [placeholder for placeholder in replacements if placeholder in rendered]
    if unresolved:
        raise ValueError(f"Unresolved placeholders: {', '.join(unresolved)}")

    return rendered


def write_prompt(rendered_prompt: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_prompt, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a complete LLM prompt from a VOC prompt template and JSONL batch."
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--batch-file", type=Path, default=DEFAULT_BATCH_FILE)
    parser.add_argument("--batch-id", default=DEFAULT_BATCH_ID)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    template = args.template.read_text(encoding="utf-8")
    batch = load_jsonl_batch(args.batch_file, args.batch_id)
    rendered = render_prompt(template, batch, OUTPUT_SCHEMA)
    write_prompt(rendered, args.output)
    print(f"Rendered prompt for {args.batch_id} to {args.output}")


if __name__ == "__main__":
    main()
