#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate audits.jsonl with hashes from seed metadata")
    parser.add_argument("--seed", required=True, help="Path to seed metadata JSON array")
    parser.add_argument("--output", required=True, help="Path to output JSONL")
    args = parser.parse_args()

    seed_path = Path(args.seed)
    out_path = Path(args.output)
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_resolved = repo_root.resolve()

    rows = json.loads(seed_path.read_text())
    generated = []
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    for row in rows:
        raw_path = (repo_root_resolved / row["raw_path"]).resolve()
        extracted_path = (repo_root_resolved / row["extracted_path"]).resolve()
        try:
            raw_path.relative_to(repo_root_resolved)
            extracted_path.relative_to(repo_root_resolved)
        except ValueError as exc:
            raise ValueError(f"seed path escapes repo root for audit_id={row.get('audit_id')}") from exc

        if not raw_path.exists():
            raise FileNotFoundError(f"Missing raw artifact: {raw_path}")
        if not extracted_path.exists():
            raise FileNotFoundError(f"Missing extracted artifact: {extracted_path}")

        rec = dict(row)
        rec["raw_sha256"] = sha256_file(raw_path)
        rec["extracted_sha256"] = sha256_file(extracted_path)
        rec["ingested_at"] = now
        generated.append(rec)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in generated:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
