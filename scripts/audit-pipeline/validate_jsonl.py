#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_record(rec: dict, required: list[str], allowed: set[str]) -> list[str]:
    errors = []
    for key in required:
        if key not in rec:
            errors.append(f"missing required key: {key}")
        elif rec[key] in (None, "", []):
            errors.append(f"empty required key: {key}")
    if "severity_normalized" in rec and rec.get("severity_normalized") not in {
        "critical",
        "high",
        "medium",
        "low",
        "info",
        "best_practice",
    }:
        errors.append(f"invalid severity_normalized: {rec.get('severity_normalized')}")
    if "confidence" in rec and rec.get("confidence") not in {"low", "medium", "high"}:
        errors.append(f"invalid confidence: {rec.get('confidence')}")
    unknown = set(rec.keys()) - allowed
    if unknown:
        errors.append("unknown keys: " + ", ".join(sorted(unknown)))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lightweight JSONL validator using schema required/properties")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--jsonl", required=True)
    args = parser.parse_args()

    schema = json.loads(Path(args.schema).read_text())
    required = schema.get("required", [])
    allowed = set(schema.get("properties", {}).keys())

    err_count = 0
    for i, line in enumerate(Path(args.jsonl).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        rec = json.loads(line)
        errs = validate_record(rec, required, allowed)
        if errs:
            err_count += 1
            print(f"line {i}: {'; '.join(errs)}")

    if err_count:
        print(f"FAILED: {err_count} invalid records")
        return 1
    print(f"OK: {args.jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
