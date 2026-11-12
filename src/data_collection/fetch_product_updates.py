import argparse
import csv
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google_play_scraper import app


DEFAULT_APP_ID = "notion.id"
DEFAULT_LANG = "en"
DEFAULT_COUNTRY = "us"
DEFAULT_RELEASES_URL = "https://www.notion.com/releases"
DEFAULT_RAW_DIR = Path("data/raw/product_updates")
DEFAULT_PROCESSED_DIR = Path("data/processed/product_updates")
DEFAULT_RELEASES_HTML = DEFAULT_RAW_DIR / "notion_releases.html"
DEFAULT_APP_DETAIL_JSON = DEFAULT_RAW_DIR / "notion_google_play_app_detail.json"
DEFAULT_RELEASES_CSV = DEFAULT_PROCESSED_DIR / "notion_release_notes.csv"
DEFAULT_RELEASES_JSON = DEFAULT_PROCESSED_DIR / "notion_release_notes.json"
DEFAULT_APP_DETAIL_PROCESSED_JSON = (
    DEFAULT_PROCESSED_DIR / "notion_google_play_app_detail_summary.json"
)

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}
DATE_PATTERN = re.compile(
    r"^(?P<month>"
    + "|".join(MONTHS)
    + r") (?P<day>\d{1,2}), (?P<year>\d{4})(?: (?P<version>\d+(?:\.\d+)*))?$"
)
VERSION_ONLY_PATTERN = re.compile(r"^\d+(?:\.\d+)*$")
NOISE_TEXTS = {
    "Play",
    "Image",
    "Uh-oh!",
    "This video couldn’t be played.",
    "Try watching it on Vimeo directly.",
}
FOOTER_BREAK_TEXTS = {
    "Next page",
    "Previous page",
    "English (US)",
}

AREA_KEYWORDS = {
    "mobile_app": [
        "android",
        "ios",
        "iphone",
        "mobile",
        "phone",
        "tablet",
    ],
    "performance": [
        "performance",
        "faster",
        "speed",
        "slow",
        "loading",
        "crash",
        "crashes",
        "bug",
        "bugs",
        "fix",
        "fixed",
        "stability",
    ],
    "editing": [
        "block",
        "blocks",
        "comment",
        "comments",
        "database",
        "doc",
        "docs",
        "editor",
        "format",
        "formatting",
        "html",
        "merge cells",
        "simple table",
        "table",
        "tables",
        "template",
    ],
    "sync": [
        "excel",
        "export",
        "file",
        "files",
        "import",
        "offline",
        "pdf",
        "powerpoint",
        "sync",
        "upload",
        "word",
    ],
    "ai": [
        "agent",
        "agents",
        "ai",
        "claude",
        "codex",
        "mcp",
        "meeting notes",
        "model",
    ],
    "account": [
        "access",
        "admin",
        "audit",
        "enterprise",
        "login",
        "permission",
        "permissions",
        "role",
        "roles",
        "security",
        "workspace",
    ],
    "pricing": [
        "billing",
        "credit",
        "credits",
        "paid",
        "pricing",
        "subscription",
    ],
    "onboarding": [
        "academy",
        "template",
        "templates",
        "tutorial",
        "workspace setup",
    ],
    "search": [
        "search",
    ],
}
RELEASE_FIELDNAMES = [
    "release_id",
    "release_date",
    "release_version",
    "release_title",
    "release_summary",
    "affected_area",
    "keywords",
    "source_url",
    "raw_date_text",
]


class TextAndLinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items = []
        self._href_stack = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg"}:
            self._skip_depth += 1
            return
        if tag == "a":
            href = dict(attrs).get("href")
            self._href_stack.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "a" and self._href_stack:
            self._href_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = normalize_whitespace(html.unescape(data))
        if text:
            href = self._href_stack[-1] if self._href_stack else None
            self.items.append({"text": text, "href": href})


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_release_date(text: str) -> tuple[str, str] | None:
    match = DATE_PATTERN.match(text)
    if not match:
        return None

    date = datetime(
        int(match.group("year")),
        MONTHS[match.group("month")],
        int(match.group("day")),
    )
    return date.date().isoformat(), match.group("version") or ""


def release_id(release_date: str, release_title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", release_title.lower()).strip("-")
    return f"{release_date}-{slug}"[:120]


def classify_affected_areas(title: str, summary: str) -> tuple[list[str], list[str]]:
    text = f"{title} {summary}".lower()
    areas = []
    matched_keywords = []

    for area, keywords in AREA_KEYWORDS.items():
        area_matches = []
        for keyword in keywords:
            if keyword in text:
                area_matches.append(keyword)
        if area_matches:
            areas.append(area)
            matched_keywords.extend(area_matches)

    if not areas:
        areas = ["other"]

    return areas, sorted(set(matched_keywords))


def extract_text_and_links(page_html: str) -> list[dict]:
    parser = TextAndLinkExtractor()
    parser.feed(page_html)
    return parser.items


def is_noise(text: str) -> bool:
    if text in NOISE_TEXTS:
        return True
    if text.startswith("Uh-oh!"):
        return True
    if text.startswith("Please watch it on"):
        return True
    if text in {"YouTube", "Vimeo"}:
        return True
    if text.startswith("http"):
        return True
    return False


def parse_notion_releases(page_html: str, source_url: str) -> list[dict]:
    items = extract_text_and_links(page_html)
    releases = []
    index = 0

    while index < len(items):
        raw_date_text = items[index]["text"]
        parsed_date = parse_release_date(raw_date_text)
        if not parsed_date:
            index += 1
            continue

        release_date, release_version = parsed_date
        section = []
        index += 1
        while index < len(items) and not parse_release_date(items[index]["text"]):
            if items[index]["text"] in FOOTER_BREAK_TEXTS:
                index = len(items)
                break
            if not is_noise(items[index]["text"]):
                section.append(items[index])
            index += 1

        if not section:
            continue

        if VERSION_ONLY_PATTERN.match(section[0]["text"]):
            release_version = release_version or section[0]["text"]
            section = section[1:]

        if not section:
            continue

        title_item = section[0]
        title = title_item["text"]
        summary_parts = [
            item["text"]
            for item in section[1:]
            if item["text"] != title and not is_noise(item["text"])
        ]
        summary = normalize_whitespace(" ".join(summary_parts))
        areas, keywords = classify_affected_areas(title, summary)
        href = title_item.get("href")

        releases.append(
            {
                "release_id": release_id(release_date, title),
                "release_date": release_date,
                "release_version": release_version,
                "release_title": title,
                "release_summary": summary,
                "affected_area": "|".join(areas),
                "keywords": "|".join(keywords),
                "source_url": urljoin(source_url, href) if href else source_url,
                "raw_date_text": raw_date_text,
            }
        )

    return releases


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "notion-android-voc-analysis/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_google_play_app_detail(app_id: str, lang: str, country: str) -> dict:
    detail = app(app_id, lang=lang, country=country)
    updated = detail.get("updated")
    updated_at = ""
    if isinstance(updated, int):
        updated_at = datetime.fromtimestamp(updated, tz=timezone.utc).isoformat()

    return {
        "app_id": detail.get("appId"),
        "title": detail.get("title"),
        "summary": detail.get("summary"),
        "released": detail.get("released"),
        "updated": updated,
        "updated_at": updated_at,
        "version": detail.get("version"),
        "score": detail.get("score"),
        "ratings": detail.get("ratings"),
        "reviews": detail.get("reviews"),
        "installs": detail.get("installs"),
        "url": detail.get("url"),
    }


def write_text(text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def write_json(data: dict | list, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RELEASE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and parse public product update signals for Notion."
    )
    parser.add_argument("--releases-url", default=DEFAULT_RELEASES_URL)
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--lang", default=DEFAULT_LANG)
    parser.add_argument("--country", default=DEFAULT_COUNTRY)
    parser.add_argument("--raw-html-output", type=Path, default=DEFAULT_RELEASES_HTML)
    parser.add_argument("--raw-app-output", type=Path, default=DEFAULT_APP_DETAIL_JSON)
    parser.add_argument("--releases-csv-output", type=Path, default=DEFAULT_RELEASES_CSV)
    parser.add_argument("--releases-json-output", type=Path, default=DEFAULT_RELEASES_JSON)
    parser.add_argument(
        "--app-summary-output",
        type=Path,
        default=DEFAULT_APP_DETAIL_PROCESSED_JSON,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    releases_html = fetch_text(args.releases_url)
    write_text(releases_html, args.raw_html_output)
    releases = parse_notion_releases(releases_html, args.releases_url)
    write_csv(releases, args.releases_csv_output)
    write_json(releases, args.releases_json_output)

    app_detail = fetch_google_play_app_detail(args.app_id, args.lang, args.country)
    write_json(app_detail, args.raw_app_output)
    write_json(app_detail, args.app_summary_output)

    print(
        f"Saved {len(releases)} release note row(s) to {args.releases_csv_output} "
        f"and Google Play app detail to {args.app_summary_output}"
    )


if __name__ == "__main__":
    main()



