"""Consolidate validated batch-level LLM themes without another model/API call.

The output measures source-theme, batch, and validated-evidence coverage. It does
not assign every review in the corpus to a theme and therefore must not be used
as full-corpus prevalence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_INPUT_DIR = Path("outputs/reports/llm_batch_outputs_api_repaired_enriched")
DEFAULT_TAXONOMY = Path("configs/canonical_themes.v1.json")
DEFAULT_THEMES_OUTPUT = Path("outputs/tables/canonical_themes.csv")
DEFAULT_MAPPING_OUTPUT = Path("outputs/tables/canonical_theme_source_mapping.csv")
DEFAULT_EVIDENCE_OUTPUT = Path("outputs/tables/canonical_theme_evidence.csv")
DEFAULT_SUMMARY_OUTPUT = Path("outputs/tables/canonical_themes_summary.json")

PAIN_BUCKETS = {"negative", "mixed_or_uncertain"}
MAPPING_METHOD = "affected_area_and_theme_id_rules_v1"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_taxonomy(path: Path) -> dict:
    data = read_json(path)
    definitions: dict[str, dict] = {}
    for group_key, group_id in (
        ("pain_themes", "pain"),
        ("positive_value_themes", "positive_value"),
    ):
        for item in data.get(group_key, []):
            theme_id = item["id"]
            if theme_id in definitions:
                raise ValueError(f"Duplicate canonical theme id: {theme_id}")
            definitions[theme_id] = {**item, "theme_group": group_id}
    if not definitions:
        raise ValueError(f"No canonical theme definitions found in {path}")
    return {"metadata": data, "definitions": definitions}


def flatten_themes(input_dir: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(input_dir.glob("*_output.json")):
        payload = read_json(path)
        batch_id = str(payload.get("batch_id", ""))
        bucket = str(payload.get("sentiment_bucket", ""))
        if not batch_id or not bucket:
            raise ValueError(f"Missing batch metadata in {path}")
        for theme in payload.get("themes", []):
            theme_id = str(theme.get("theme_id", ""))
            if not theme_id:
                raise ValueError(f"Missing theme_id in {path}")
            records.append(
                {
                    "source_file": str(path).replace("\\", "/"),
                    "source_theme_id": f"{batch_id}::{theme_id}",
                    "batch_id": batch_id,
                    "sentiment_bucket": bucket,
                    "theme_id": theme_id,
                    "theme_name_zh": str(theme.get("theme_name_zh", "")),
                    "summary_zh": str(theme.get("summary_zh", "")),
                    "affected_area": str(theme.get("affected_area", "other")),
                    "severity": str(theme.get("severity", "")),
                    "evidence": list(theme.get("evidence", [])),
                }
            )
    if not records:
        raise ValueError(f"No *_output.json themes found in {input_dir}")
    return records


def canonical_theme_id(record: dict) -> str:
    """Map one batch-level theme to a stable, reviewable canonical family."""

    bucket = record["sentiment_bucket"]
    area = record["affected_area"]
    theme_id = record["theme_id"].lower()

    if bucket == "positive":
        if area == "ai":
            return "ai_assistance_value"
        if area == "sync":
            return "cross_device_mobile_value"
        if area == "editing":
            if "writing_note_taking" in theme_id:
                return "productivity_organization_value"
            return "customization_template_value"
        if area in {"mobile_app", "onboarding"}:
            return "usability_learning_value"
        if area == "pricing" or "support_and_continuous" in theme_id:
            return "accessible_value_and_trust"
        return "productivity_organization_value"

    if bucket not in PAIN_BUCKETS:
        raise ValueError(f"Unsupported sentiment bucket: {bucket}")

    content_terms = (
        "render",
        "blank_screen",
        "page_visibility",
        "widget",
        "upload_issue",
        "media_upload",
        "load_failure",
        "loading_failure",
        "content_not",
        "unreliable_access",
    )
    if area in {"mobile_app", "editing", "sync"} and any(
        term in theme_id for term in content_terms
    ):
        return "content_rendering_access"

    if area == "editing":
        if "mobile" in theme_id and any(
            term in theme_id for term in ("feature_gap", "workflow", "navigation")
        ):
            return "mobile_ux_feature_parity"
        if any(
            term in theme_id
            for term in ("customization", "display_options", "feature_gaps")
        ):
            return "customization_feature_gaps"
        return "editing_input_controls"
    if area == "mobile_app":
        return "mobile_ux_feature_parity"
    if area == "onboarding":
        if "account_gate" in theme_id:
            return "account_access_auth"
        return "onboarding_learnability"
    if area == "other":
        if "data_loss" in theme_id or "bugs" in theme_id:
            return "sync_offline_data_integrity"
        if "mobile" in theme_id:
            return "mobile_ux_feature_parity"
        return "customization_feature_gaps"

    area_mapping = {
        "performance": "performance_stability",
        "sync": "sync_offline_data_integrity",
        "ai": "ai_intrusion_controls",
        "account": "account_access_auth",
        "pricing": "pricing_subscription_gating",
        "search": "search_discovery",
    }
    try:
        return area_mapping[area]
    except KeyError as exc:
        raise ValueError(
            f"No canonical rule for {record['source_theme_id']} (area={area})"
        ) from exc


def consolidate(records: list[dict], taxonomy: dict) -> dict:
    definitions = taxonomy["definitions"]
    mappings: list[dict] = []
    evidence_rows: list[dict] = []
    aggregate: dict[str, dict] = {}

    for record in records:
        canonical_id = canonical_theme_id(record)
        if canonical_id not in definitions:
            raise ValueError(
                f"Canonical theme {canonical_id} is not defined for "
                f"{record['source_theme_id']}"
            )
        definition = definitions[canonical_id]
        expected_group = (
            "positive_value" if record["sentiment_bucket"] == "positive" else "pain"
        )
        if definition["theme_group"] != expected_group:
            raise ValueError(
                f"Theme group mismatch for {record['source_theme_id']}: "
                f"{canonical_id} is {definition['theme_group']}"
            )

        mappings.append(
            {
                "canonical_theme_id": canonical_id,
                "canonical_theme_name_zh": definition["name_zh"],
                "theme_group": definition["theme_group"],
                "source_theme_id": record["source_theme_id"],
                "batch_id": record["batch_id"],
                "sentiment_bucket": record["sentiment_bucket"],
                "theme_id": record["theme_id"],
                "theme_name_zh": record["theme_name_zh"],
                "affected_area": record["affected_area"],
                "severity": record["severity"],
                "evidence_count": len(record["evidence"]),
                "mapping_method": MAPPING_METHOD,
            }
        )

        item = aggregate.setdefault(
            canonical_id,
            {
                "definition": definition,
                "source_theme_ids": set(),
                "batch_ids": set(),
                "review_ids": set(),
                "bucket_counts": Counter(),
                "severity_counts": Counter(),
                "evidence_count": 0,
                "evidence_dates": [],
            },
        )
        item["source_theme_ids"].add(record["source_theme_id"])
        item["batch_ids"].add(record["batch_id"])
        item["bucket_counts"][record["sentiment_bucket"]] += 1
        item["severity_counts"][record["severity"]] += 1

        for evidence in record["evidence"]:
            review_id = str(evidence.get("review_id", ""))
            if review_id:
                item["review_ids"].add(review_id)
            created_at = str(evidence.get("review_created_at", ""))
            if created_at:
                item["evidence_dates"].append(created_at[:10])
            item["evidence_count"] += 1
            evidence_rows.append(
                {
                    "canonical_theme_id": canonical_id,
                    "canonical_theme_name_zh": definition["name_zh"],
                    "theme_group": definition["theme_group"],
                    "source_theme_id": record["source_theme_id"],
                    "batch_id": record["batch_id"],
                    "sentiment_bucket": record["sentiment_bucket"],
                    "source_theme_name_zh": record["theme_name_zh"],
                    "review_id": review_id,
                    "review_created_at": created_at,
                    "app_version": str(evidence.get("app_version", "")),
                    "thumbs_up_count": str(evidence.get("thumbs_up_count", "")),
                    "score": str(evidence.get("score", "")),
                    "quote": str(evidence.get("quote", "")),
                    "reason_zh": str(evidence.get("reason_zh", "")),
                }
            )

    theme_rows: list[dict] = []
    for canonical_id, item in aggregate.items():
        definition = item["definition"]
        dates = sorted(item["evidence_dates"])
        theme_rows.append(
            {
                "canonical_theme_id": canonical_id,
                "canonical_theme_name_zh": definition["name_zh"],
                "theme_group": definition["theme_group"],
                "description_zh": definition["description_zh"],
                "source_theme_count": len(item["source_theme_ids"]),
                "batch_count": len(item["batch_ids"]),
                "evidence_count": item["evidence_count"],
                "unique_review_count": len(item["review_ids"]),
                "negative_source_theme_count": item["bucket_counts"]["negative"],
                "mixed_or_uncertain_source_theme_count": item["bucket_counts"][
                    "mixed_or_uncertain"
                ],
                "positive_source_theme_count": item["bucket_counts"]["positive"],
                "high_severity_source_theme_count": item["severity_counts"]["high"],
                "medium_severity_source_theme_count": item["severity_counts"]["medium"],
                "low_severity_source_theme_count": item["severity_counts"]["low"],
                "first_evidence_at": dates[0] if dates else "",
                "last_evidence_at": dates[-1] if dates else "",
                "counting_boundary": taxonomy["metadata"]["counting_boundary"],
            }
        )

    group_order = {"pain": 0, "positive_value": 1}
    theme_rows.sort(
        key=lambda row: (
            group_order[row["theme_group"]],
            -int(row["batch_count"]),
            -int(row["source_theme_count"]),
            row["canonical_theme_id"],
        )
    )
    mappings.sort(key=lambda row: (row["theme_group"], row["canonical_theme_id"], row["source_theme_id"]))
    evidence_rows.sort(
        key=lambda row: (
            row["theme_group"],
            row["canonical_theme_id"],
            row["batch_id"],
            row["review_id"],
        )
    )
    return {"themes": theme_rows, "mappings": mappings, "evidence": evidence_rows}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def source_digest(input_dir: Path, taxonomy_path: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(input_dir.glob("*_output.json")) + [taxonomy_path]
    for path in paths:
        digest.update(str(path).replace("\\", "/").encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_summary(result: dict, input_dir: Path, taxonomy_path: Path) -> dict:
    themes = result["themes"]
    mappings = result["mappings"]
    evidence = result["evidence"]
    by_group: dict[str, dict] = {}
    for group in ("pain", "positive_value"):
        group_themes = [row for row in themes if row["theme_group"] == group]
        group_mappings = [row for row in mappings if row["theme_group"] == group]
        group_evidence = [row for row in evidence if row["theme_group"] == group]
        by_group[group] = {
            "canonical_theme_count": len(group_themes),
            "source_theme_count": len(group_mappings),
            "batch_count": len({row["batch_id"] for row in group_mappings}),
            "evidence_count": len(group_evidence),
            "unique_review_count": len(
                {row["review_id"] for row in group_evidence if row["review_id"]}
            ),
        }
    return {
        "method": MAPPING_METHOD,
        "taxonomy_version": 1,
        "source_digest_sha256": source_digest(input_dir, taxonomy_path),
        "counting_boundary": (
            "Source-theme, batch, and validated-evidence coverage only; "
            "not full-corpus prevalence."
        ),
        "source_theme_count": len(mappings),
        "canonical_theme_count": len(themes),
        "evidence_count": len(evidence),
        "unique_review_count": len(
            {row["review_id"] for row in evidence if row["review_id"]}
        ),
        "by_group": by_group,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolidate validated batch-level themes without another API call."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--themes-output", type=Path, default=DEFAULT_THEMES_OUTPUT)
    parser.add_argument("--mapping-output", type=Path, default=DEFAULT_MAPPING_OUTPUT)
    parser.add_argument("--evidence-output", type=Path, default=DEFAULT_EVIDENCE_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taxonomy = load_taxonomy(args.taxonomy)
    records = flatten_themes(args.input_dir)
    result = consolidate(records, taxonomy)
    summary = build_summary(result, args.input_dir, args.taxonomy)

    write_csv(args.themes_output, result["themes"])
    write_csv(args.mapping_output, result["mappings"])
    write_csv(args.evidence_output, result["evidence"])
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
