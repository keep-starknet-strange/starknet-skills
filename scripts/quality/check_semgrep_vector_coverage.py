#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VECTOR_PATTERN = re.compile(r"^\*\*(\d+)\.\s+", re.MULTILINE)
CORE_LIST_PATTERN = re.compile(r"attack_vectors_core:\s*\[([^\]]*)\]")
INT_PATTERN = re.compile(r"\d+")


def _extract_attack_vectors(path: Path) -> set[int]:
    content = path.read_text(encoding="utf-8")
    return {int(x) for x in VECTOR_PATTERN.findall(content)}


def _extract_semgrep_core_vectors(path: Path) -> set[int]:
    content = path.read_text(encoding="utf-8")
    found: set[int] = set()
    for raw_list in CORE_LIST_PATTERN.findall(content):
        for raw_int in INT_PATTERN.findall(raw_list):
            found.add(int(raw_int))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Semgrep rule metadata covers required core attack vectors."
    )
    parser.add_argument(
        "--vectors-glob",
        default="cairo-auditor/references/attack-vectors/attack-vectors-*.md",
        help="Glob for attack-vector markdown files.",
    )
    parser.add_argument(
        "--rules-glob",
        default="cairo-auditor/references/semgrep/rules/*.yaml",
        help="Glob for Semgrep rule packs.",
    )
    parser.add_argument(
        "--core-min",
        type=int,
        default=1,
        help="Inclusive lower bound for required core vectors.",
    )
    parser.add_argument(
        "--core-max",
        type=int,
        default=80,
        help="Inclusive upper bound for required core vectors.",
    )
    args = parser.parse_args()

    vector_paths = sorted(Path(".").glob(args.vectors_glob))
    if not vector_paths:
        raise SystemExit(f"no vector files matched: {args.vectors_glob}")

    rule_paths = sorted(Path(".").glob(args.rules_glob))
    if not rule_paths:
        raise SystemExit(f"no semgrep rule files matched: {args.rules_glob}")

    available_vectors: set[int] = set()
    for path in vector_paths:
        available_vectors.update(_extract_attack_vectors(path))

    required_vectors = {
        vector_id
        for vector_id in available_vectors
        if args.core_min <= vector_id <= args.core_max
    }

    semgrep_vectors: set[int] = set()
    by_rule_file: dict[str, list[int]] = {}
    for path in rule_paths:
        present = sorted(_extract_semgrep_core_vectors(path))
        by_rule_file[path.as_posix()] = present
        semgrep_vectors.update(present)

    missing = sorted(required_vectors - semgrep_vectors)
    out_of_range = sorted(
        vector_id
        for vector_id in semgrep_vectors
        if vector_id < args.core_min or vector_id > args.core_max
    )

    summary = {
        "vector_files": [p.as_posix() for p in vector_paths],
        "rules_files": [p.as_posix() for p in rule_paths],
        "core_min": args.core_min,
        "core_max": args.core_max,
        "required_count": len(required_vectors),
        "covered_count": len(required_vectors & semgrep_vectors),
        "missing": missing,
        "out_of_range_refs": out_of_range,
        "covered_core_vectors": sorted(required_vectors & semgrep_vectors),
        "by_rule_file": by_rule_file,
    }
    print(json.dumps(summary, ensure_ascii=True))

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
