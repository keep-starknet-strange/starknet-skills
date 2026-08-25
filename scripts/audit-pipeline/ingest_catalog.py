#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, ClassVar


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
    duplicate_of: str | None


class MainContentHTMLParser(HTMLParser):
    """Extract readable, heading-preserving text from a public audit page."""

    BLOCK_TAGS: ClassVar[frozenset[str]] = frozenset(
        {"h1", "h2", "h3", "h4", "p", "li", "pre", "blockquote", "tr"}
    )
    SKIP_TAGS: ClassVar[frozenset[str]] = frozenset(
        {"script", "style", "svg", "nav", "footer", "noscript"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.main_depth = 0
        self.skip_depth = 0
        self.current: list[str] = []
        self.lines: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "main" and attrs_map.get("id") == "main-content":
            self.in_main = True
            self.main_depth = 1
            return
        if self.in_main and tag == "main":
            self.main_depth += 1
        if not self.in_main:
            return
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if not self.in_main:
            return
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self._flush()
        if tag == "main":
            self.main_depth -= 1
            if self.main_depth == 0:
                self._flush()
                self.in_main = False

    def handle_data(self, data: str) -> None:
        if self.in_main and self.skip_depth == 0:
            cleaned = re.sub(r"\s+", " ", data).strip()
            if cleaned:
                self.current.append(cleaned)

    def _flush(self) -> None:
        if not self.current:
            return
        line = re.sub(r"\s+", " ", " ".join(self.current)).strip()
        if line and (not self.lines or self.lines[-1] != line):
            self.lines.append(line)
        self.current = []

    def text(self) -> str:
        self._flush()
        return "\n".join(self.lines) + "\n"


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
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text
    if re.fullmatch(r"\d{4}", text):
        return text
    return None


def optional_text(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    drive_match = re.search(r"drive\.google\.com/file/d/([^/?]+)", cleaned)
    if drive_match:
        file_id = urllib.parse.quote(drive_match.group(1), safe="")
        return (
            "https://drive.usercontent.google.com/download"
            f"?id={file_id}&export=download&confirm=t"
        )
    if cleaned.startswith("https://github.com/") and "/blob/" in cleaned:
        separator = "&" if "?" in cleaned else "?"
        cleaned = f"{cleaned}{separator}raw=1"
    return cleaned.replace(" ", "%20")


def classify_source_type(original_url: str, normalized_url: str) -> str:
    if "drive.google.com" in original_url:
        return "drive"
    if original_url.startswith("https://github.com/") and "/blob/" in original_url:
        return "github_blob"
    if normalized_url.startswith("https://raw.githubusercontent.com/"):
        return "github_raw"
    if urllib.parse.urlparse(normalized_url).path.lower().endswith(".pdf"):
        return "direct_pdf"
    return "html"


def is_audited(status: str) -> bool:
    normalized = re.sub(r"\s+", " ", status).strip().casefold()
    return (
        re.search(r"\baudited\b", normalized) is not None
        and "in progress" not in normalized
        and "not audited" not in normalized
        and "unaudited" not in normalized
    )


def load_catalog(path: Path) -> list[CatalogRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError("catalog file must contain a JSON array")

    rows: list[CatalogRow] = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise TypeError(f"catalog row {idx} must be a JSON object")
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
                duplicate_of=optional_text(item.get("duplicate_of")),
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


def load_existing_manifest_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        rec = json.loads(line)
        if not isinstance(rec, dict):
            raise TypeError(f"{path}: line {i} must be object")
        records.append(rec)
    return records


def ensure_pdf_tools() -> None:
    has_pdftotext = shutil_which("pdftotext") is not None
    has_mutool = shutil_which("mutool") is not None
    if not has_pdftotext and not has_mutool:
        raise RuntimeError("pdftotext or mutool is required for extraction")


def shutil_which(name: str) -> str | None:
    return shutil.which(name)


def is_safe_hostname(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    if not infos:
        return False

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def validate_https_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("source URL must use https")
    if not parsed.hostname:
        raise ValueError("source URL missing hostname")
    if not is_safe_hostname(parsed.hostname):
        raise ValueError("source URL host resolves to private/reserved address")
    return parsed


class SafeHTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_pdf(url: str, output_path: Path) -> str:
    validate_https_url(url)
    opener = urllib.request.build_opener(SafeHTTPSRedirectHandler())
    request = urllib.request.Request(url=url, headers={"User-Agent": USER_AGENT})
    with opener.open(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        validate_https_url(response.geturl())
        payload = response.read()
    if not payload.startswith(b"%PDF-"):
        raise ValueError("downloaded payload is not a PDF")
    source_sha256 = hashlib.sha256(payload).hexdigest()
    output_path.write_bytes(payload)
    return source_sha256


def download_html(url: str, output_path: Path) -> str:
    validate_https_url(url)
    opener = urllib.request.build_opener(SafeHTTPSRedirectHandler())
    request = urllib.request.Request(url=url, headers={"User-Agent": USER_AGENT})
    with opener.open(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        validate_https_url(response.geturl())
        payload = response.read()
        content_type = response.headers.get_content_type()
    if content_type not in {"text/html", "application/xhtml+xml"} and b"<html" not in payload[:4096].lower():
        raise ValueError("downloaded payload is not HTML")
    output_path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def extract_html_text(raw_html_path: Path, extracted_txt_path: Path) -> None:
    parser = MainContentHTMLParser()
    parser.feed(raw_html_path.read_text(encoding="utf-8", errors="replace"))
    text = parser.text()
    if len(text.strip()) < 200:
        raise ValueError("HTML page did not contain enough main-content text")
    extracted_txt_path.write_text(text, encoding="utf-8")


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
    source_sha256: str,
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
        "source_sha256": source_sha256,
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
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore the prior manifest when intentionally rebuilding canonical identities.",
    )
    args = parser.parse_args()

    ensure_pdf_tools()

    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "datasets" / "manifests" / "audits.jsonl"
    raw_dir = repo_root / "datasets" / "audits" / "raw"
    extracted_dir = repo_root / "datasets" / "audits" / "extracted"
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    rows = load_catalog(Path(args.catalog))
    existing_records = [] if args.fresh else load_existing_manifest_records(manifest_path)
    existing_id_by_source_url: dict[str, str] = {}
    existing_source_sha_by_url: dict[str, str] = {}
    used_audit_ids: set[str] = set()
    seen_content_key_to_id: dict[str, str] = {}
    for rec in existing_records:
        audit_id = rec.get("audit_id")
        if isinstance(audit_id, str):
            used_audit_ids.add(audit_id)
        source_url = rec.get("source_url")
        if isinstance(source_url, str) and isinstance(audit_id, str):
            existing_id_by_source_url[source_url] = audit_id
        source_sha = rec.get("source_sha256")
        if isinstance(source_url, str) and isinstance(source_sha, str):
            existing_source_sha_by_url[source_url] = source_sha
        raw_sha = rec.get("raw_sha256")
        extracted_sha = rec.get("extracted_sha256")
        if isinstance(audit_id, str) and isinstance(raw_sha, str) and isinstance(extracted_sha, str):
            seen_content_key_to_id[f"{raw_sha}:{extracted_sha}"] = audit_id

    seed_rows: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    success_count = 0

    for row in rows:
        if row.source_url and row.source_url in existing_id_by_source_url:
            audit_id = existing_id_by_source_url[row.source_url]
        else:
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
        if row.duplicate_of:
            report["result"] = "skipped"
            report["reason"] = f"duplicate_content_of:{row.duplicate_of}"
            report_rows.append(report)
            continue
        if args.limit and success_count >= args.limit:
            report["result"] = "skipped"
            report["reason"] = "limit_reached"
            report_rows.append(report)
            continue

        normalized_url = normalize_url(row.source_url)
        try:
            validate_https_url(normalized_url)
        except ValueError:
            report["result"] = "skipped"
            report["reason"] = "invalid_or_unsafe_source_url"
            report_rows.append(report)
            continue

        source_type = classify_source_type(row.source_url, normalized_url)
        raw_suffix = ".html" if source_type == "html" else ".pdf"
        raw_path = raw_dir / f"{audit_id}{raw_suffix}"
        extracted_path = extracted_dir / f"{audit_id}.txt"
        source_sha256 = ""
        reused_existing_artifacts = False
        try:
            if raw_path.exists() and extracted_path.exists():
                reused_existing_artifacts = True
                source_sha256 = existing_source_sha_by_url.get(row.source_url or "")
                if not source_sha256:
                    source_sha256 = sha256_file(raw_path)
            else:
                if source_type == "html":
                    source_sha256 = download_html(normalized_url, raw_path)
                    extract_html_text(raw_path, extracted_path)
                else:
                    source_sha256 = download_pdf(normalized_url, raw_path)
                    extract_text(raw_path, extracted_path)
        except Exception as exc:  # noqa: BLE001 - per-row failure should not abort full ingest
            raw_path.unlink(missing_ok=True)
            extracted_path.unlink(missing_ok=True)
            report["result"] = "failed"
            report["reason"] = str(exc)
            report_rows.append(report)
            continue

        raw_sha256 = sha256_file(raw_path)
        extracted_sha256 = sha256_file(extracted_path)
        content_key = f"{raw_sha256}:{extracted_sha256}"
        duplicate_of = seen_content_key_to_id.get(content_key)
        if duplicate_of is not None and duplicate_of != audit_id:
            report["result"] = "skipped"
            report["reason"] = f"duplicate_content_of:{duplicate_of}"
            report["raw_sha256"] = raw_sha256
            report["extracted_sha256"] = extracted_sha256
            report_rows.append(report)
            if not reused_existing_artifacts:
                raw_path.unlink(missing_ok=True)
                extracted_path.unlink(missing_ok=True)
            continue

        seen_content_key_to_id[content_key] = audit_id
        rec = to_seed_record(
            row,
            audit_id=audit_id,
            source_type=source_type,
            raw_relpath=raw_path.relative_to(repo_root).as_posix(),
            extracted_relpath=extracted_path.relative_to(repo_root).as_posix(),
            source_sha256=source_sha256,
        )

        report["result"] = "ingested"
        report["raw_sha256"] = raw_sha256
        report["extracted_sha256"] = extracted_sha256
        if reused_existing_artifacts:
            report["reason"] = "reused_existing_artifacts"
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
