import argparse
import json
import os
import urllib.request
from pathlib import Path


DEFAULT_BATCH_OUTPUT_FILE = Path("outputs/reports/openai_batch_results/batch_output.jsonl")
DEFAULT_BATCH_ERROR_FILE = Path("outputs/reports/openai_batch_results/batch_errors.jsonl")
DEFAULT_OUTPUT_DIR = Path("outputs/reports/llm_batch_outputs_api")
API_BASE_URL = "https://api.openai.com/v1"


def extract_response_text(body: dict) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks = []
    for item in body.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and "text" in content:
                chunks.append(str(content["text"]))

    if chunks:
        return "".join(chunks).strip()

    choices = body.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

    raise ValueError("Could not find model output text in batch response body")


def parse_json_text(text: str) -> dict:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.removeprefix("```json").removeprefix("```").strip()
        clean = clean.removesuffix("```").strip()
    return json.loads(clean)


def parse_batch_result_line(line: str) -> tuple[str, dict]:
    result = json.loads(line)
    custom_id = str(result.get("custom_id") or "").strip()
    if not custom_id:
        raise ValueError("Batch result line is missing custom_id")
    if result.get("error"):
        raise ValueError(f"{custom_id} failed: {result['error']}")

    response = result.get("response") or {}
    status_code = response.get("status_code")
    if status_code != 200:
        raise ValueError(f"{custom_id} returned status_code={status_code}")

    text = extract_response_text(response.get("body") or {})
    return custom_id, parse_json_text(text)


def write_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_result_outputs(batch_output_file: Path, output_dir: Path) -> list[Path]:
    written_paths = []
    with batch_output_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                custom_id, output = parse_batch_result_line(line)
            except Exception as exc:
                raise ValueError(
                    f"Failed to parse {batch_output_file} line {line_number}: {exc}"
                ) from exc
            output_path = output_dir / f"{custom_id}_output.json"
            write_json(output, output_path)
            written_paths.append(output_path)

    return written_paths


def describe_missing_batch_output(batch: dict) -> str:
    counts = batch.get("request_counts") or {}
    details = [
        f"Batch {batch.get('id')} has no output_file_id",
        f"status={batch.get('status')}",
        f"error_file_id={batch.get('error_file_id')}",
        f"total={counts.get('total')}",
        f"completed={counts.get('completed')}",
        f"failed={counts.get('failed')}",
    ]
    return "; ".join(details)


def download_file(file_id: str, output_path: Path, api_key: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(
        api_request_bytes("GET", f"/files/{file_id}/content", api_key)
    )
    return output_path


def api_request_json(method: str, path: str, api_key: str) -> dict:
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        method=method,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def api_request_bytes(method: str, path: str, api_key: str) -> bytes:
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        method=method,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def download_batch_output(
    batch_id: str,
    output_path: Path,
    api_key: str,
    error_output_path: Path | None = None,
) -> Path:
    batch = api_request_json("GET", f"/batches/{batch_id}", api_key)
    output_file_id = batch.get("output_file_id")
    if not output_file_id:
        message = describe_missing_batch_output(batch)
        error_file_id = batch.get("error_file_id")
        if error_file_id and error_output_path is not None:
            download_file(error_file_id, error_output_path, api_key)
            message = f"{message}; downloaded_error_file={error_output_path}"
        raise ValueError(message)

    return download_file(output_file_id, output_path, api_key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and split OpenAI Batch API VOC results into per-batch JSON files."
    )
    parser.add_argument("--batch-output-file", type=Path, default=DEFAULT_BATCH_OUTPUT_FILE)
    parser.add_argument("--batch-error-file", type=Path, default=DEFAULT_BATCH_ERROR_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--batch-id",
        help="Optional OpenAI batch id. When provided, download its output file first.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batch_output_file = args.batch_output_file
    if args.batch_id:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when --batch-id is provided")
        batch_output_file = download_batch_output(
            args.batch_id,
            batch_output_file,
            api_key,
            error_output_path=args.batch_error_file,
        )

    written_paths = write_result_outputs(batch_output_file, args.output_dir)
    print(f"Wrote {len(written_paths)} LLM output file(s) to {args.output_dir}")


if __name__ == "__main__":
    main()




