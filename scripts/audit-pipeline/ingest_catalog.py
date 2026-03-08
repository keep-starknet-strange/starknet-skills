#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


USER_AGENT = "starknet-skills-audit-ingest/1.0 (+https://github.com/keep-starknet-strange/starknet-skills)"
DEFAULT_TIMEOUT_SECONDS = 45
EXTRACTOR_VERSION = "ingest_catalog.py@v1"


@dataclass
class CatalogRow:
    project: str
    source_url: str | None
    auditor: str
    date: str | None
    repository: str | None
    notes: str | None
    status: str
    license: str | None
    usage_rights: str | None
    redaction_status: str | None


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "unknown"


def parse_date(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-01-01"
    return None


def optional_text(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    if cleaned.startswith("https://github.com/") and "/blob/" in cleaned:
        parts = cleaned.split("/")
        blob_idx = parts.index("blob")
        owner = parts[3]
        repo = parts[4]
        ref = parts[blob_idx + 1]
        path = "/".join(parts[blob_idx + 2 :])
        cleaned = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    return cleaned.replace(" ", "%20")


def classify_source_type(original_url: str, normalized_url: str) -> str:
    if "drive.google.com" in original_url:
        return "drive"
    if original_url.startswith("https://github.com/") and "/blob/" in original_url:
        return "github_blob"
    if normalized_url.startswith("https://raw.githubusercontent.com/"):
        return "github_raw"
    if normalized_url.lower().endswith(".pdf"):
        return "direct_pdf"
    return "html"


def is_audited(status: str) -> bool:
    return "audited" in status.lower() and "in progress" not in status.lower()


def load_catalog(path: Path) -> list[CatalogRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("catalog file must contain a JSON array")

    rows: list[CatalogRow] = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"catalog row {idx} must be a JSON object")
        project = str(item.get("project", "")).strip()
        auditor = str(item.get("auditor", "")).strip()
        status = str(item.get("status", "")).strip()
        if not project or not auditor or not status:
            raise ValueError(f"catalog row {idx} missing project/auditor/status")
        source_url_value = item.get("source_url")
        source_url = (
            str(source_url_value).strip() if isinstance(source_url_value, str) and source_url_value.strip() else None
        )
        rows.append(
            CatalogRow(
                project=project,
                source_url=source_url,
                auditor=auditor,
                date=optional_text(item.get("date")),
                repository=optional_text(item.get("repository")),
                notes=optional_text(item.get("notes")),
                status=status,
                license=optional_text(item.get("license")),
                usage_rights=optional_text(item.get("usage_rights")),
                redaction_status=optional_text(item.get("redaction_status")),
            )
        )
    return rows


def choose_audit_id(row: CatalogRow, used: set[str]) -> str:
    year = "unknown"
    if row.date:
        match = re.search(r"\b(20\d{2})\b", row.date)
        if match:
            year = match.group(1)
    base = "_".join([slugify(row.project), slugify(row.auditor), year])
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}_{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def ensure_pdf_tools() -> None:
    has_pdftotext = shutil_which("pdftotext") is not None
    has_mutool = shutil_which("mutool") is not None
    if not has_pdftotext and not has_mutool:
        raise RuntimeError("pdftotext or mutool is required for extraction")


def shutil_which(name: str) -> str | None:
    return subprocess.run(
        ["bash", "-lc", f"command -v {name}"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip() or None


def download_pdf(url: str, output_path: Path) -> None:
    request = urllib.request.Request(url=url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        payload = response.read()
    if not payload.startswith(b"%PDF-"):
        raise ValueError("downloaded payload is not a PDF")
    output_path.write_bytes(payload)


def extract_text(raw_pdf_path: Path, extracted_txt_path: Path) -> None:
    pdftotext_cmd = ["pdftotext", "-layout", str(raw_pdf_path), str(extracted_txt_path)]
    pdftotext = subprocess.run(pdftotext_cmd, check=False, capture_output=True, text=True)
    if pdftotext.returncode == 0 and extracted_txt_path.exists():
        return

    mutool_cmd = ["mutool", "draw", "-F", "txt", "-o", str(extracted_txt_path), str(raw_pdf_path)]
    mutool = subprocess.run(mutool_cmd, check=False, capture_output=True, text=True)
    if mutool.returncode == 0 and extracted_txt_path.exists():
        return

    raise RuntimeError(
        "text extraction failed; pdftotext stderr="
        + pdftotext.stderr.strip()
        + " | mutool stderr="
        + mutool.stderr.strip()
    )


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def to_seed_record(
    row: CatalogRow,
    *,
    audit_id: str,
    source_type: str,
    raw_relpath: str,
    extracted_relpath: str,
) -> dict[str, Any]:
    usage_rights = row.usage_rights or "public_reference_only"
    if usage_rights not in {
        "public_redistributable",
        "public_reference_only",
        "restricted_no_redistribution",
        "unknown",
    }:
        usage_rights = "unknown"

    redaction_status = row.redaction_status or "none"
    if redaction_status not in {"none", "partial", "required", "unknown"}:
        redaction_status = "unknown"

    return {
        "audit_id": audit_id,
        "project": row.project,
        "auditor": row.auditor,
        "date": parse_date(row.date),
        "source_url": row.source_url,
        "source_type": source_type,
        "repo_url": row.repository,
        "raw_path": raw_relpath,
        "extracted_path": extracted_relpath,
        "license": row.license or "unknown",
        "usage_rights": usage_rights,
        "redaction_status": redaction_status,
        "extractor_version": EXTRACTOR_VERSION,
        "notes": row.notes or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest catalog audits: download PDFs, extract text, and write seed + ingest report."
    )
    parser.add_argument(
        "--catalog",
        required=True,
        help="Path to catalog JSON list (project/source_url/auditor/date/repository/notes/status).",
    )
    parser.add_argument(
        "--seed-out",
        required=True,
        help="Output JSON array path for generated seed rows (for generate_manifest.py).",
    )
    parser.add_argument(
        "--report-out",
        required=True,
        help="Output JSONL path for per-row ingest status report.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of successful ingests (0 = no limit).",
    )
    args = parser.parse_args()

    ensure_pdf_tools()

    repo_root = Path(__file__).resolve().parents[2]
    raw_dir = repo_root / "datasets" / "audits" / "raw"
    extracted_dir = repo_root / "datasets" / "audits" / "extracted"
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    rows = load_catalog(Path(args.catalog))
    used_audit_ids: set[str] = set()
    seed_rows: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    success_count = 0

    for row in rows:
        audit_id = choose_audit_id(row, used_audit_ids)
        report: dict[str, Any] = {
            "audit_id": audit_id,
            "project": row.project,
            "auditor": row.auditor,
            "status": row.status,
            "source_url": row.source_url,
        }

        if not is_audited(row.status):
            report["result"] = "skipped"
            report["reason"] = "status_not_audited"
            report_rows.append(report)
            continue
        if not row.source_url:
            report["result"] = "skipped"
            report["reason"] = "missing_source_url"
            report_rows.append(report)
            continue
        if args.limit and success_count >= args.limit:
            report["result"] = "skipped"
            report["reason"] = "limit_reached"
            report_rows.append(report)
            continue

        normalized_url = normalize_url(row.source_url)
        parsed = urllib.parse.urlparse(normalized_url)
        if parsed.scheme != "https":
            report["result"] = "skipped"
            report["reason"] = "non_https_source"
            report_rows.append(report)
            continue

        source_type = classify_source_type(row.source_url, normalized_url)
        if source_type in {"drive", "html"}:
            report["result"] = "skipped"
            report["reason"] = f"unsupported_source_type:{source_type}"
            report_rows.append(report)
            continue

        raw_path = raw_dir / f"{audit_id}.pdf"
        extracted_path = extracted_dir / f"{audit_id}.txt"
        try:
            download_pdf(normalized_url, raw_path)
            extract_text(raw_path, extracted_path)
        except Exception as exc:  # noqa: BLE001 - per-row failure should not abort full ingest
            raw_path.unlink(missing_ok=True)
            extracted_path.unlink(missing_ok=True)
            report["result"] = "failed"
            report["reason"] = str(exc)
            report_rows.append(report)
            continue

        rec = to_seed_record(
            row,
            audit_id=audit_id,
            source_type=source_type,
            raw_relpath=raw_path.relative_to(repo_root).as_posix(),
            extracted_relpath=extracted_path.relative_to(repo_root).as_posix(),
        )

        report["result"] = "ingested"
        report["raw_sha256"] = sha256_file(raw_path)
        report["extracted_sha256"] = sha256_file(extracted_path)
        report_rows.append(report)
        seed_rows.append(rec)
        success_count += 1

    seed_out = Path(args.seed_out)
    seed_out.parent.mkdir(parents=True, exist_ok=True)
    seed_out.write_text(json.dumps(seed_rows, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    report_out = Path(args.report_out)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    with report_out.open("w", encoding="utf-8") as handle:
        for rec in report_rows:
            handle.write(json.dumps(rec, ensure_ascii=True) + "\n")

    print(
        json.dumps(
            {
                "rows_total": len(rows),
                "rows_ingested": success_count,
                "seed_out": str(seed_out),
                "report_out": str(report_out),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
