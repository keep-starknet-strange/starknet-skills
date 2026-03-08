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


def load_blocked_audit_ids(repo_root: Path) -> set[str]:
    blocklist = repo_root / "evals" / "heldout" / "audit_ids.txt"
    if not blocklist.exists():
        return set()
    blocked = set()
    for raw in blocklist.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        blocked.add(line)
    return blocked


def main() -> int:
    parser = argparse.ArgumentParser(description="Lightweight JSONL validator using schema required/properties")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--jsonl", required=True)
    args = parser.parse_args()

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError("schema must be a JSON object")
    required = schema.get("required", [])
    allowed = set(schema.get("properties", {}).keys())
    if not isinstance(required, list) or not all(isinstance(k, str) for k in required):
        raise ValueError("schema.required must be a string array")
    if not allowed:
        raise ValueError("schema.properties must define allowed keys")
    repo_root = Path(__file__).resolve().parents[2]
    blocked_audit_ids = load_blocked_audit_ids(repo_root)

    err_count = 0
    for i, line in enumerate(Path(args.jsonl).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            err_count += 1
            print(f"line {i}: invalid json: {exc.msg}")
            continue
        if not isinstance(rec, dict):
            err_count += 1
            print(f"line {i}: top-level JSON value must be an object")
            continue
        errs = validate_record(rec, required, allowed)
        for key in ("audit_id", "source_audit_id"):
            value = rec.get(key)
            if isinstance(value, str) and value in blocked_audit_ids:
                errs.append(f"blocked by held-out policy: {key}={value}")
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
