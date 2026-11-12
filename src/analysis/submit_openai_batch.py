import argparse
import json
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_REQUEST_FILE = Path(
    "outputs/reports/openai_batch_requests/voc_theme_analysis_requests.jsonl"
)
API_BASE_URL = "https://api.openai.com/v1"


def api_key_from_env() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return api_key


def encode_multipart_form(file_path: Path, fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"----voc-analysis-{uuid.uuid4().hex}"
    parts = []

    for name, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    parts.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"\r\n'
            ).encode("utf-8"),
            b"Content-Type: application/jsonl\r\n\r\n",
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def request_json(
    method: str,
    path: str,
    api_key: str,
    body: dict | None = None,
    data: bytes | None = None,
    content_type: str = "application/json",
) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"}
    request_data = data
    if body is not None:
        request_data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif data is not None:
        headers["Content-Type"] = content_type

    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=request_data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(format_http_error(exc, method, path)) from exc


def format_http_error(exc: urllib.error.HTTPError, method: str, path: str) -> str:
    detail = exc.read().decode("utf-8", errors="replace")
    try:
        detail = json.dumps(json.loads(detail), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        pass
    return f"OpenAI API HTTP {exc.code} {exc.reason} for {method} {path}:\n{detail}"


def upload_batch_file(request_file: Path, api_key: str) -> dict:
    data, content_type = encode_multipart_form(request_file, {"purpose": "batch"})
    return request_json(
        method="POST",
        path="/files",
        api_key=api_key,
        data=data,
        content_type=content_type,
    )


def create_batch(
    input_file_id: str,
    api_key: str,
    endpoint: str = "/v1/responses",
    completion_window: str = "24h",
    metadata: dict | None = None,
) -> dict:
    body = {
        "input_file_id": input_file_id,
        "endpoint": endpoint,
        "completion_window": completion_window,
    }
    if metadata:
        body["metadata"] = metadata
    return request_json("POST", "/batches", api_key, body=body)


def retrieve_batch(batch_id: str, api_key: str) -> dict:
    return request_json("GET", f"/batches/{batch_id}", api_key)


def count_jsonl_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit or inspect OpenAI Batch API jobs for VOC theme extraction."
    )
    parser.add_argument("--request-file", type=Path, default=DEFAULT_REQUEST_FILE)
    parser.add_argument("--completion-window", default="24h")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the request file count without uploading it.",
    )
    parser.add_argument("--status", help="Only retrieve the status for this batch id.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.status:
        batch = retrieve_batch(args.status, api_key_from_env())
        print(json.dumps(batch, ensure_ascii=False, indent=2))
        return

    if not args.request_file.exists():
        raise ValueError(f"Request file not found: {args.request_file}")

    request_count = count_jsonl_lines(args.request_file)
    if args.dry_run:
        print(f"Dry run OK: {request_count} request(s) in {args.request_file}")
        return

    api_key = api_key_from_env()
    uploaded = upload_batch_file(args.request_file, api_key)
    print(f"Uploaded batch input file: {uploaded['id']}")
    batch = create_batch(
        input_file_id=uploaded["id"],
        api_key=api_key,
        completion_window=args.completion_window,
        metadata={"project": "notion_android_voc_analysis"},
    )
    print(json.dumps(batch, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


