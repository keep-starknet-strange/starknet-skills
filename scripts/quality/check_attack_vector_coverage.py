#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


VECTOR_PATTERN = re.compile(r"^\*\*(\d+)\.\s+", re.MULTILINE)


def _extract_vector_ids(path: Path) -> list[int]:
    content = path.read_text(encoding="utf-8")
    return [int(x) for x in VECTOR_PATTERN.findall(content)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate attack-vector corpus size and ID uniqueness."
    )
    parser.add_argument(
        "--vectors-glob",
        default="cairo-auditor/references/attack-vectors/attack-vectors-*.md",
        help="Glob for attack vector markdown files.",
    )
    parser.add_argument(
        "--min-vectors",
        type=int,
        default=120,
        help="Minimum total number of vectors required.",
    )
    args = parser.parse_args()

    vector_paths = sorted(Path(".").glob(args.vectors_glob))
    if not vector_paths:
        raise SystemExit(f"no vector files matched: {args.vectors_glob}")

    by_file: dict[str, int] = {}
    seen: dict[int, str] = {}
    duplicates: list[dict[str, object]] = []
    total = 0

    for path in vector_paths:
        ids = _extract_vector_ids(path)
        by_file[path.as_posix()] = len(ids)
        total += len(ids)
        for vector_id in ids:
            if vector_id in seen:
                duplicates.append(
                    {
                        "vector_id": vector_id,
                        "first_file": seen[vector_id],
                        "duplicate_file": path.as_posix(),
                    }
                )
            else:
                seen[vector_id] = path.as_posix()

    total_unique = len(seen)
    summary = {
        "vector_files": [p.as_posix() for p in vector_paths],
        "by_file": by_file,
        "total_vectors": total_unique,
        "total_vectors_raw": total,
        "min_vectors": args.min_vectors,
        "duplicates": duplicates,
    }
    print(json.dumps(summary, ensure_ascii=True))

    if duplicates:
        return 1
    if total_unique < args.min_vectors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
