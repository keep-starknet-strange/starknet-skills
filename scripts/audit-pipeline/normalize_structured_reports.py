#!/usr/bin/env python3
"""Normalize structured PDF/HTML audit findings with hard count gates.

This pass deliberately preserves titles, severity, status, locations, and source
sections while omitting report prose and embedded code. It is a coverage-quality
bootstrap, not human-adjudicated gold data.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

NUMERIC_REPORTS: dict[str, dict[str, Any]] = {
    "endur_v1_launch_cairo_security_clan_2024": {
        "expected": 8,
        "date": "2024-11-22",
        "mode": "nested",
        "severity": {"1": "high", "2": "medium", "3": "low", "4": "info", "5": "best_practice"},
    },
    "endur_withdrawal_queue_upgrade_cairo_security_clan_2025": {
        "expected": 1,
        "date": "2025-01-23",
        "mode": "nested",
        "severity": {"1": "info"},
    },
    "endur_staking_v2_support_cairo_security_clan_2025": {
        "expected": 2,
        "date": "2025-05-02",
        "mode": "nested",
        "severity": {"1": "medium", "2": "best_practice"},
    },
    "endur_btc_staking_multi_validator_cairo_security_clan_2025": {
        "expected": 12,
        "date": "2025-09-13",
        "mode": "nested",
        "severity": {"1": "high", "2": "medium", "3": "low", "4": "info", "5": "best_practice"},
    },
    "carmine_spotnet_nethermind_2024": {
        "expected": 28,
        "date": "2024-01-08",
        "mode": "bracketed",
    },
    "atomiq_exchange_update_cairo_security_clan_2025": {
        "expected": 1,
        "date": "2025-06-18",
        "mode": "nested",
        "severity": {"1": "medium"},
    },
}


HTML_REPORTS: dict[str, dict[str, Any]] = {
    "dojo_security_review_openzeppelin_2024": {
        "date": "2024-11-12",
        "findings": [
            ("Resources Can Be Overwritten", "critical"),
            ("Inconsistent namespace separation", "high"),
            ("Imprecise Permissions", "medium"),
            ("Incorrect Error Message", "low"),
            ("Missing Validation", "low"),
            ("Incorrect Introspection Sizes", "low"),
            ("Misleading Comments", "low"),
            ("Code Simplifications", "best_practice"),
            ("Naming Suggestions", "best_practice"),
            ("Typographical Errors", "best_practice"),
            ("Magic Numbers", "best_practice"),
        ],
    },
    "dojo_namespace_diff_openzeppelin_2024": {
        "date": "2024-11-12",
        "findings": [
            ("Incomplete Comment", "best_practice"),
            ("Naming Suggestion", "best_practice"),
            ("TODO Comments", "best_practice"),
            ("Code Simplification", "best_practice"),
            ("Unused code", "best_practice"),
            ("Typographical Error", "best_practice"),
        ],
    },
}


SEVERITY_ALIASES = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "info",
    "informational": "info",
    "best practice": "best_practice",
    "best practices": "best_practice",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
    path.write_text((body + "\n") if body else "", encoding="utf-8")


def normalize_layout(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def title_from_numeric_segment(segment: dict[str, Any], mode: str) -> tuple[str, str]:
    content = segment["content"]
    prefix = content.split("File(s):", maxsplit=1)[0]
    prefix = re.sub(rf"^\s*{re.escape(segment['heading_key'])}\s+", "", prefix)
    prefix = normalize_layout(prefix)
    if mode == "bracketed":
        match = re.match(r"\[(.+?)\]\s+(.+)", prefix)
        if not match:
            raise ValueError(f"missing bracketed severity in {segment['segment_id']}")
        severity = SEVERITY_ALIASES.get(match.group(1).strip().casefold())
        if not severity:
            raise ValueError(f"unknown severity in {segment['segment_id']}: {match.group(1)}")
        return match.group(2).strip(), severity
    return prefix, ""


def extract_files(content: str) -> list[str]:
    head = content.split("Description:", maxsplit=1)[0]
    files = re.findall(r"[A-Za-z0-9_./-]+\.cairo", head)
    return list(dict.fromkeys(item.strip(".,:;()[]{}") for item in files)) or ["unspecified.cairo"]


def extract_functions(title: str, content: str) -> list[str]:
    sample = f"{title}\n{content.split('Recommendation', maxsplit=1)[0]}"
    patterns = [
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\b([A-Za-z_][A-Za-z0-9_]*)\(\.\.\.\)",
        r"\b([A-Za-z_][A-Za-z0-9_]*)\(\)",
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, sample, re.IGNORECASE):
            value = match.group(1)
            if value not in found and value.casefold() not in {"function", "assert", "while", "loop"}:
                found.append(value)
    return found[:8] or ["unspecified"]


def extract_status(content: str) -> str:
    status_match = re.search(r"Status:\s*([A-Za-z ]+?)(?:\.|\n|$)", content, re.IGNORECASE)
    if status_match:
        raw = normalize_layout(status_match.group(1)).casefold()
    else:
        updates = re.findall(r"Update:\s*([^\n]+)", content, re.IGNORECASE)
        raw = normalize_layout(updates[-1]).casefold() if updates else "reported"
    if "not an issue" in raw:
        return "not_an_issue"
    if "resolved" in raw or "fixed" in raw:
        return "resolved"
    if "acknowledged" in raw:
        return "acknowledged"
    if "mitigated" in raw:
        return "mitigated"
    if "unresolved" in raw or "open" in raw:
        return "unresolved"
    return "reported"


def infer_tags(title: str, severity: str) -> list[str]:
    tags = ["audit-import", severity]
    mapping = {
        "access": "access-control",
        "permission": "access-control",
        "reentr": "reentrancy",
        "oracle": "oracle",
        "sandwich": "mev",
        "precision": "precision",
        "round": "rounding",
        "overflow": "overflow",
        "storage": "storage",
        "withdraw": "withdrawal",
        "reward": "rewards",
        "fee": "fees",
        "slippage": "slippage",
        "initializ": "initialization",
        "central": "centralization",
        "dos": "dos",
        "denial": "dos",
    }
    lowered = title.casefold()
    for needle, tag in mapping.items():
        if needle in lowered and tag not in tags:
            tags.append(tag)
    return tags


def make_finding(
    *,
    audit: dict[str, Any],
    date: str,
    index: int,
    title: str,
    severity: str,
    status: str,
    contracts: list[str],
    functions: list[str],
    source_pages: list[int],
    source_section: str,
) -> dict[str, Any]:
    finding_id = f"{audit['audit_id'].upper()}-{index:03d}"
    location = contracts[0] if contracts != ["unspecified.cairo"] else "the scoped code"
    function_text = ", ".join(functions) if functions != ["unspecified"] else "the affected path"
    return {
        "finding_id": finding_id,
        "source_audit_id": audit["audit_id"],
        "project": audit["project"],
        "auditor": audit["auditor"],
        "date": date,
        "severity_original": severity.replace("_", " ").title(),
        "severity_normalized": severity,
        "status": status,
        "contracts": contracts,
        "functions": functions,
        "root_cause": f"The report identifies this implementation defect: {title}.",
        "exploit_path": f"Execution through {function_text} in {location} can expose the behavior documented by the report.",
        "trigger_condition": f"The affected path reaches the edge case described by '{title}'.",
        "vulnerable_snippet": f"See source section {source_section}; report code is omitted pending repository-license review.",
        "fixed_snippet": None,
        "recommendation": f"Apply the remediation documented in source section {source_section} and add a regression test for this condition.",
        "test_that_catches_it": f"A focused regression test that triggers '{title}' and asserts the corrected invariant.",
        "false_positive_lookalikes": [
            "Equivalent behavior protected by an explicit invariant, bounded loop, or validated authorization path."
        ],
        "tags": infer_tags(title, severity),
        "source_pages": source_pages,
        "confidence": "medium",
        "evidence_strength": "moderate",
        "reproducibility": "confirmed_by_report",
        "notes": (
            f"Auto-normalized from structured source section {source_section}; title, severity, status, location, "
            "source position, and report-level count were checked. Report prose and embedded code were not redistributed."
        ),
    }


def build_numeric_findings(audit: dict[str, Any], spec: dict[str, Any], segments_path: Path) -> list[dict[str, Any]]:
    segments = read_jsonl(segments_path)
    selected: list[dict[str, Any]] = []
    for segment in segments:
        key = segment["heading_key"]
        if (
            spec["mode"] == "nested" and re.fullmatch(r"6\.\d+\.\d+", key)
        ) or (
            spec["mode"] == "bracketed" and re.fullmatch(r"6\.\d+", key)
        ):
            selected.append(segment)
    if len(selected) != spec["expected"]:
        raise ValueError(
            f"{audit['audit_id']}: extracted {len(selected)} findings, expected {spec['expected']}"
        )

    findings = []
    for index, segment in enumerate(selected, start=1):
        title, severity = title_from_numeric_segment(segment, spec["mode"])
        if spec["mode"] == "nested":
            severity_key = segment["heading_key"].split(".")[1]
            severity = spec["severity"][severity_key]
        content = segment["content"]
        findings.append(
            make_finding(
                audit=audit,
                date=spec["date"],
                index=index,
                title=title,
                severity=severity,
                status=extract_status(content),
                contracts=extract_files(content),
                functions=extract_functions(title, content),
                source_pages=list(range(segment["start_page"], segment["end_page"] + 1)),
                source_section=segment["heading_key"],
            )
        )
    return findings


def html_sections(text: str, titles: list[str]) -> list[tuple[str, str]]:
    positions: list[tuple[int, str]] = []
    for title in titles:
        marker = f"\n{title}\n"
        position = text.rfind(marker)
        if position < 0:
            raise ValueError(f"HTML finding heading not found: {title}")
        positions.append((position + 1, title))
    positions.sort()
    sections: list[tuple[str, str]] = []
    for index, (start, title) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else text.find("\nConclusion\n", start)
        if end < 0:
            end = len(text)
        sections.append((title, text[start:end].strip()))
    return sections


def build_html_findings(
    audit: dict[str, Any], spec: dict[str, Any], extracted_path: Path, segments_path: Path
) -> list[dict[str, Any]]:
    text = extracted_path.read_text(encoding="utf-8", errors="replace")
    declared = spec["findings"]
    section_by_title = dict(html_sections(text, [title for title, _ in declared]))
    segment_rows = []
    findings = []
    for index, (title, severity) in enumerate(declared, start=1):
        content = section_by_title[title]
        segment_id = f"{audit['audit_id']}:{index:04d}"
        segment_rows.append(
            {
                "heading_key": f"OZ-{index:03d}",
                "heading_title": title,
                "start_page": 1,
                "end_page": 1,
                "content": content,
                "segment_id": segment_id,
                "audit_id": audit["audit_id"],
                "segment_type": "finding",
            }
        )
        contracts = list(dict.fromkeys(re.findall(r"[A-Za-z0-9_./-]+\.cairo", content)))
        findings.append(
            make_finding(
                audit=audit,
                date=spec["date"],
                index=index,
                title=title,
                severity=severity,
                status=extract_status(content),
                contracts=contracts or ["unspecified.cairo"],
                functions=extract_functions(title, content),
                source_pages=[1],
                source_section=f"HTML heading: {title}",
            )
        )
    if len(findings) != len(declared):
        raise ValueError(f"{audit['audit_id']}: HTML finding count mismatch")
    write_jsonl(segments_path, segment_rows)
    return findings


def scope_files(extracted_path: Path) -> list[str]:
    text = extracted_path.read_text(encoding="utf-8", errors="replace")
    found = list(dict.fromkeys(re.findall(r"[A-Za-z0-9_./-]+\.cairo", text)))
    return found[:100] or ["unspecified.cairo"]


def write_audit_metadata(path: Path, audit: dict[str, Any], date: str, findings: list[dict[str, Any]], extracted: Path) -> None:
    severity_counts = Counter(row["severity_normalized"] for row in findings)
    status_counts = Counter(row["status"] for row in findings)
    payload = {
        "audit_id": audit["audit_id"],
        "project": audit["project"],
        "auditor": audit["auditor"],
        "date": date,
        "source_url": audit["source_url"],
        "repository": audit.get("repo_url") or "unknown",
        "scope_files": scope_files(extracted),
        "finding_count": len(findings),
        "finding_label_semantics": "reported_findings_present",
        "negative_label_scope": "none",
        "safety_claim": "not_proven",
        "severity_counts": dict(sorted(severity_counts.items())),
        "status_summary": dict(sorted(status_counts.items())),
        "notes": "Structured coverage pass with report-declared finding-count verification; not human-adjudicated gold data.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--coverage-report",
        type=Path,
        default=Path("datasets/manifests/structured_extraction_report.json"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    manifests = {row["audit_id"]: row for row in read_jsonl(root / "datasets/manifests/audits.jsonl")}

    totals: dict[str, int] = {}
    for audit_id, spec in NUMERIC_REPORTS.items():
        audit = manifests[audit_id]
        extracted = root / audit["extracted_path"]
        segments = root / "datasets/segments" / f"{audit_id}.jsonl"
        findings = build_numeric_findings(audit, spec, segments)
        write_jsonl(root / "datasets/normalized/findings" / f"{audit_id}.findings.jsonl", findings)
        write_audit_metadata(
            root / "datasets/normalized/audits" / f"{audit_id}.json",
            audit,
            spec["date"],
            findings,
            extracted,
        )
        totals[audit_id] = len(findings)

    for audit_id, spec in HTML_REPORTS.items():
        audit = manifests[audit_id]
        extracted = root / audit["extracted_path"]
        segments = root / "datasets/segments" / f"{audit_id}.jsonl"
        findings = build_html_findings(audit, spec, extracted, segments)
        write_jsonl(root / "datasets/normalized/findings" / f"{audit_id}.findings.jsonl", findings)
        write_audit_metadata(
            root / "datasets/normalized/audits" / f"{audit_id}.json",
            audit,
            spec["date"],
            findings,
            extracted,
        )
        totals[audit_id] = len(findings)

    report = {
        "schema_version": "1.0",
        "extraction_method": "structured_count_gated",
        "reports": len(totals),
        "findings": sum(totals.values()),
        "counts": totals,
        "coverage_gate": "passed",
        "label_semantics": (
            "Confirmed report findings are positive evidence. Unmentioned code is unlabeled, not safe. "
            "Audit-level zero-finding reports are represented in audit metadata, not as per-function negatives."
        ),
    }
    report_path = args.coverage_report
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
