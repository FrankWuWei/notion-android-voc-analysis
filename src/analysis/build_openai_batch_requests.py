import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.render_llm_prompt import OUTPUT_SCHEMA, render_prompt


DEFAULT_BATCH_DIR = Path("data/processed/llm_inputs")
DEFAULT_TEMPLATE = Path("prompts/voc_theme_extraction.v1.md")
DEFAULT_OUTPUT = Path("outputs/reports/openai_batch_requests/voc_theme_analysis_requests.jsonl")
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_TEMPERATURE = None
DEFAULT_REASONING_EFFORT = "low"

LLM_OUTPUT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "batch_id",
        "sentiment_bucket",
        "analysis_language",
        "themes",
        "excluded_reviews",
    ],
    "properties": {
        "batch_id": {"type": "string"},
        "sentiment_bucket": {
            "type": "string",
            "enum": ["positive", "negative", "mixed_or_uncertain"],
        },
        "analysis_language": {"type": "string", "enum": ["zh-Hant"]},
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "theme_id",
                    "theme_name_zh",
                    "summary_zh",
                    "affected_area",
                    "severity",
                    "evidence",
                    "suggested_action_zh",
                ],
                "properties": {
                    "theme_id": {"type": "string"},
                    "theme_name_zh": {"type": "string"},
                    "summary_zh": {"type": "string"},
                    "affected_area": {
                        "type": "string",
                        "enum": [
                            "mobile_app",
                            "sync",
                            "performance",
                            "editing",
                            "search",
                            "ai",
                            "account",
                            "pricing",
                            "onboarding",
                            "other",
                        ],
                    },
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["review_id", "score", "quote", "reason_zh"],
                            "properties": {
                                "review_id": {"type": "string"},
                                "score": {"type": "string"},
                                "quote": {"type": "string"},
                                "reason_zh": {"type": "string"},
                            },
                        },
                    },
                    "suggested_action_zh": {"type": "string"},
                },
            },
        },
        "excluded_reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["review_id", "reason"],
                "properties": {
                    "review_id": {"type": "string"},
                    "reason": {
                        "type": "string",
                        "enum": [
                            "non_english",
                            "insufficient_information",
                            "unrelated",
                        ],
                    },
                },
            },
        },
    },
}


def iter_batches(batch_paths: Iterable[Path]) -> Iterable[dict]:
    for batch_path in batch_paths:
        with batch_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                batch = json.loads(line)
                if "batch_id" not in batch:
                    raise ValueError(f"Missing batch_id in {batch_path} line {line_number}")
                yield batch


def response_format() -> dict:
    return {
        "type": "json_schema",
        "name": "voc_theme_analysis",
        "strict": True,
        "schema": LLM_OUTPUT_JSON_SCHEMA,
    }


def build_response_body(
    batch: dict,
    template: str,
    model: str,
    temperature: float | None = DEFAULT_TEMPERATURE,
    reasoning_effort: str | None = DEFAULT_REASONING_EFFORT,
    max_output_tokens: int | None = None,
) -> dict:
    body = {
        "model": model,
        "input": render_prompt(template, batch, OUTPUT_SCHEMA),
        "store": False,
        "text": {"format": response_format()},
        "metadata": {
            "batch_id": str(batch["batch_id"]),
            "sentiment_bucket": str(batch.get("sentiment_bucket", "")),
        },
    }
    if temperature is not None:
        body["temperature"] = temperature
    if reasoning_effort:
        body["reasoning"] = {"effort": reasoning_effort}
    if max_output_tokens is not None:
        body["max_output_tokens"] = max_output_tokens

    return body


def build_batch_request(
    batch: dict,
    template: str,
    model: str,
    temperature: float | None = DEFAULT_TEMPERATURE,
    reasoning_effort: str | None = DEFAULT_REASONING_EFFORT,
    max_output_tokens: int | None = None,
) -> dict:
    return {
        "custom_id": str(batch["batch_id"]),
        "method": "POST",
        "url": "/v1/responses",
        "body": build_response_body(
            batch=batch,
            template=template,
            model=model,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        ),
    }


def find_batch_paths(batch_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in batch_dir.glob("*_llm_batches.jsonl")
        if "smoke" not in path.name
    )


def write_batch_requests(
    batch_paths: Iterable[Path],
    template: str,
    output_path: Path,
    model: str = DEFAULT_MODEL,
    temperature: float | None = DEFAULT_TEMPERATURE,
    reasoning_effort: str | None = DEFAULT_REASONING_EFFORT,
    max_output_tokens: int | None = None,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with output_path.open("w", encoding="utf-8") as file:
        for batch in iter_batches(batch_paths):
            request = build_batch_request(
                batch=batch,
                template=template,
                model=model,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
            )
            file.write(json.dumps(request, ensure_ascii=False) + "\n")
            written += 1

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build OpenAI Batch API JSONL requests for VOC theme extraction."
    )
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        help="Set to empty string to omit reasoning configuration.",
    )
    parser.add_argument("--max-output-tokens", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batch_paths = find_batch_paths(args.batch_dir)
    if not batch_paths:
        raise ValueError(f"No *_llm_batches.jsonl files found in {args.batch_dir}")

    template = args.template.read_text(encoding="utf-8")
    written = write_batch_requests(
        batch_paths=batch_paths,
        template=template,
        output_path=args.output,
        model=args.model,
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort or None,
        max_output_tokens=args.max_output_tokens,
    )
    print(f"Wrote {written} OpenAI batch request(s) to {args.output}")


if __name__ == "__main__":
    main()


