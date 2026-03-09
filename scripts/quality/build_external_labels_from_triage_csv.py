#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

VALID_OUTCOMES = {"tp", "fp"}
VALID_TRIAGE_CATEGORIES = {"security_bug", "design_tradeoff", "quality_smell"}
VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n", ""}


def parse_bool(value: str, *, field: str, row_id: str) -> bool:
    lowered = value.strip().lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    raise ValueError(f"{row_id}: invalid boolean in {field}: {value!r}")


def get_required(row: dict[str, str], field: str, *, row_id: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ValueError(f"{row_id}: missing required field {field}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert manual triage CSV into external-triage labels JSONL."
    )
    parser.add_argument("--triage-csv", required=True, help="Path to manual triage CSV.")
    parser.add_argument("--release", required=True, help="Release tag, e.g. v0.2.0.")
    parser.add_argument("--scan-id", required=True, help="Scan id for label records.")
    parser.add_argument("--output-jsonl", required=True, help="Output labels JSONL path.")
    parser.add_argument(
        "--reviewed-at",
        default=date.today().isoformat(),
        help="Reviewed date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--default-reviewer",
        default="",
        help="Fallback reviewer handle when reviewer_1/reviewer is empty.",
    )
    args = parser.parse_args()

    triage_csv = Path(args.triage_csv)
    output_jsonl = Path(args.output_jsonl)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    labels: list[dict[str, object]] = []
    skipped = 0

    with triage_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            row_id = row.get("finding_id", "").strip() or f"row-{idx}"
            manual_verdict = row.get("manual_verdict", "").strip().lower()
            if not manual_verdict:
                skipped += 1
                continue
            if manual_verdict not in VALID_OUTCOMES:
                raise ValueError(f"{row_id}: manual_verdict must be tp|fp")

            triage_category = row.get("triage_category", "").strip().lower() or row.get(
                "category", "security_bug"
            ).strip().lower()
            if triage_category not in VALID_TRIAGE_CATEGORIES:
                raise ValueError(f"{row_id}: invalid triage_category: {triage_category!r}")

            needs_poc = parse_bool(row.get("needs_poc", "false"), field="needs_poc", row_id=row_id)
            security_countable_raw = row.get("security_countable", "").strip()
            security_countable: bool | None
            if security_countable_raw == "":
                security_countable = None
            else:
                security_countable = parse_bool(
                    security_countable_raw, field="security_countable", row_id=row_id
                )

            manual_severity = row.get("manual_severity", "").strip().lower()
            if manual_severity and manual_severity not in VALID_SEVERITIES:
                raise ValueError(f"{row_id}: invalid manual_severity: {manual_severity!r}")

            reviewer = (
                row.get("reviewer_1", "").strip()
                or row.get("reviewer", "").strip()
                or args.default_reviewer.strip()
            )
            if not reviewer:
                raise ValueError(f"{row_id}: reviewer_1/reviewer missing and no --default-reviewer")
            reviewer_1 = row.get("reviewer_1", "").strip() or reviewer
            reviewer_2 = row.get("reviewer_2", "").strip()

            rationale = row.get("manual_notes", "").strip() or row.get("rationale", "").strip()
            if not rationale:
                raise ValueError(f"{row_id}: missing manual_notes/rationale")

            record: dict[str, object] = {
                "finding_id": get_required(row, "finding_id", row_id=row_id),
                "release": args.release,
                "scan_id": args.scan_id,
                "repo": get_required(row, "repo", row_id=row_id),
                "ref": get_required(row, "ref", row_id=row_id),
                "file": get_required(row, "file", row_id=row_id),
                "class_id": get_required(row, "class_id", row_id=row_id),
                "predicted_detect": parse_bool(
                    row.get("predicted_detect", "true"), field="predicted_detect", row_id=row_id
                ),
                "human_outcome": manual_verdict,
                "confidence": row.get("confidence_tier", "").strip().lower() or "medium",
                "reviewer": reviewer,
                "reviewed_at": args.reviewed_at,
                "rationale": rationale,
                "triage_category": triage_category,
                "needs_poc": needs_poc,
                "reviewer_1": reviewer_1,
            }
            if reviewer_2:
                record["reviewer_2"] = reviewer_2
            if security_countable is not None:
                record["security_countable"] = security_countable
            if manual_severity:
                record["manual_severity"] = manual_severity

            labels.append(record)

    with output_jsonl.open("w", encoding="utf-8") as handle:
        for row in labels:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    print(
        json.dumps(
            {
                "triage_csv": triage_csv.as_posix(),
                "output_jsonl": output_jsonl.as_posix(),
                "labels_written": len(labels),
                "rows_skipped_without_manual_verdict": skipped,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
