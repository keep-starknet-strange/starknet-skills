#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from benchmark_cairo_auditor import DETECTORS


@dataclass
class RepoSpec:
    slug: str
    ref: str | None


@dataclass(frozen=True)
class ConfidenceAssessment:
    severity: str
    score: int
    tier: str
    deductions: tuple[tuple[str, int], ...]
    gate_status: str
    gate_reason: str
    actionability: str


REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REF_RE = re.compile(r"^[A-Za-z0-9._/@+-]{1,200}$")

SEVERITY_BY_CLASS: dict[str, str] = {
    "AA-SELF-CALL-SESSION": "high",
    "UNCHECKED_FEE_BOUND": "medium",
    "SHUTDOWN_OVERRIDE_PRECEDENCE": "medium",
    "SYSCALL_SELECTOR_FALLBACK_ASSUMPTION": "medium",
    "IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK": "high",
    "UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD": "high",
    "CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD": "medium",
    "CONSTRUCTOR_DEAD_PARAM": "low",
    "IRREVOCABLE_ADMIN": "low",
    "ONE_SHOT_REGISTRATION": "low",
    "FEES_RECIPIENT_ZERO_DOS": "high",
    "NO_ACCESS_CONTROL_MUTATION": "high",
    "CEI_VIOLATION_ERC1155": "high",
    "PRECISION_LOSS": "high",
    "UNSAFE_ADMIN_TRANSFER": "high",
    "STALE_STATE_WRITE": "high",
    "UNEXPECTED_ACCESS_CONTROL": "medium",
    "MISSING_FEE_BOUNDS": "medium",
    "OVERLY_RESTRICTIVE_VALIDATION": "low",
    "UNBOUNDED_LOOP": "low",
    "COMMENTED_OUT_ACCESS_CONTROL": "high",
    "UNVALIDATED_ORACLE_PRICES": "high",
    "WRONG_PARAMETER_USAGE": "high",
    "SILENT_NO_OP": "high",
    "UNPROTECTED_INITIALIZER": "high",
    "UNSAFE_TYPE_CONVERSION": "high",
    "INCORRECT_LIST_REMOVAL": "medium",
    "STALE_SNAPSHOT_READ": "medium",
}

PRIVILEGED_PATH_CLASSES = {
    "IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK",
    "IRREVOCABLE_ADMIN",
    "ONE_SHOT_REGISTRATION",
    "UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD",
    "UNSAFE_ADMIN_TRANSFER",
    "UNPROTECTED_INITIALIZER",
    "COMMENTED_OUT_ACCESS_CONTROL",
    "UNVALIDATED_ORACLE_PRICES",
}

SELF_CONTAINED_IMPACT_CLASSES = {
    # Intentionally paired with PARTIAL_PATH_CLASSES so this class remains
    # informational (max score 65 => low_confidence).
    "CONSTRUCTOR_DEAD_PARAM",
}

PARTIAL_PATH_CLASSES = {
    "CONSTRUCTOR_DEAD_PARAM",
    "UNBOUNDED_LOOP",
    "OVERLY_RESTRICTIVE_VALIDATION",
    "STALE_SNAPSHOT_READ",
}

FRAMEWORK_HINT_CLASSES = {
    "CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD",
    "UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD",
}

OWNERSHIP_ROTATION_MARKERS = (
    "transfer_ownership",
    "renounce_ownership",
    "set_owner",
    "update_owner",
)

OZ_UPGRADEABLE_MARKERS = (
    "openzeppelin_upgrades",
    "upgradeablecomponent",
    "upgradeableimpl",
)

FRAMEWORK_GUARD_MARKERS = (
    "ownablecomponent",
    "accesscontrolcomponent",
    "openzeppelin_upgrades",
    "upgradeablecomponent",
)

SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def parse_repo_spec(raw: str) -> RepoSpec:
    raw = raw.strip()
    if not raw:
        raise ValueError("empty repo spec")
    if "@" in raw:
        slug, ref = raw.split("@", 1)
    else:
        slug, ref = raw, None
    if not REPO_SLUG_RE.fullmatch(slug):
        raise ValueError(f"invalid repo slug: {raw}")
    if ref:
        if ref.startswith("-"):
            raise ValueError(f"invalid repo ref (must not start with '-'): {raw}")
        if not REF_RE.fullmatch(ref):
            raise ValueError(f"invalid repo ref: {raw}")
    return RepoSpec(slug=slug, ref=ref or None)


def run(cmd: list[str], cwd: Path | None = None, timeout: float = 300) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        cwd_str = cwd.as_posix() if cwd else "."
        cmd_str = " ".join(cmd)
        raise RuntimeError(f"command timed out after {timeout}s in {cwd_str}: {cmd_str}") from exc
    return proc.stdout.strip()


def repo_git_url(spec: RepoSpec, git_host: str) -> str:
    host = git_host.strip().rstrip("/")
    if not host:
        raise ValueError("git_host cannot be empty")
    parsed = urllib.parse.urlparse(host)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid git_host: {git_host}")
    return f"{host}/{spec.slug}.git"


def clone_repo(spec: RepoSpec, workdir: Path, git_host: str) -> tuple[Path, str]:
    repo_dir = workdir / spec.slug.replace("/", "__")
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    url = repo_git_url(spec, git_host)
    clone_cmd = ["git", "clone", "--depth", "1", url, str(repo_dir)]
    run(clone_cmd)
    if spec.ref:
        checked_out = False
        try:
            run(["git", "checkout", spec.ref], cwd=repo_dir)
            checked_out = True
        except Exception:
            checked_out = False

        if not checked_out:
            fetch_attempts = [
                ["git", "fetch", "--depth", "1", "origin", spec.ref],
                ["git", "fetch", "origin", spec.ref],
                ["git", "fetch", "--unshallow", "origin"],
                ["git", "fetch", "origin", "--tags", "--prune"],
            ]
            last_error: Exception | None = None
            for fetch_cmd in fetch_attempts:
                try:
                    run(fetch_cmd, cwd=repo_dir)
                except Exception as exc:
                    last_error = exc
                    continue
                try:
                    run(["git", "checkout", spec.ref], cwd=repo_dir)
                    checked_out = True
                    break
                except Exception as exc:
                    last_error = exc
                    continue
            if not checked_out:
                detail = str(last_error) if last_error else "unknown checkout failure"
                raise RuntimeError(
                    f"failed to resolve ref {spec.ref!r} for {spec.slug}: {detail}"
                )
    resolved_ref = run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
    return repo_dir, resolved_ref


def iter_cairo_files(repo_dir: Path) -> list[Path]:
    files: list[Path] = []
    repo_resolved = repo_dir.resolve()
    for path in repo_dir.rglob("*.cairo"):
        if not path.is_file() or path.is_symlink():
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(repo_resolved)
        except ValueError:
            continue
        files.append(path)
    return sorted(files)


def is_excluded(path: Path, excluded_markers: tuple[str, ...]) -> bool:
    """Return True when a repo-relative path should be excluded from prod scope."""
    parts = [p.lower() for p in path.as_posix().split("/")]
    for marker in excluded_markers:
        if any(
            part == marker
            or Path(part).stem.lower() == marker
            or part.startswith(f"{marker}_")
            or part.endswith(f"_{marker}")
            or part.startswith(f"{marker}-")
            or part.endswith(f"-{marker}")
            for part in parts
        ):
            return True
    return False


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(p in text for p in patterns)


def _confidence_tier(score: int) -> str:
    if score >= 85:
        return "high"
    if score >= 75:
        return "medium"
    return "low"


def assess_finding(*, class_id: str, code: str) -> ConfidenceAssessment:
    code_l = code.lower()
    severity = SEVERITY_BY_CLASS.get(class_id, "medium")
    deductions: list[tuple[str, int]] = []
    gate_status = "pass"
    gate_reason = ""

    if class_id in PRIVILEGED_PATH_CLASSES:
        deductions.append(("privileged-caller-path", 25))
    if class_id in PARTIAL_PATH_CLASSES:
        deductions.append(("partial-path-needs-context", 20))
    if class_id in SELF_CONTAINED_IMPACT_CLASSES:
        deductions.append(("potentially-self-contained-impact", 15))
    if class_id in FRAMEWORK_HINT_CLASSES and _contains_any(code_l, FRAMEWORK_GUARD_MARKERS):
        deductions.append(("framework-guard-surface-present", 10))

    if class_id == "IRREVOCABLE_ADMIN" and _contains_any(code_l, OWNERSHIP_ROTATION_MARKERS):
        # File-level heuristic note: this signal may be unrelated to the flagged surface.
        gate_reason = "ownership-rotation-surface-detected-file-level-heuristic"
    elif class_id == "UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD" and _contains_any(
        code_l, OZ_UPGRADEABLE_MARKERS
    ):
        gate_status = "suppressed"
        gate_reason = "openzeppelin-upgrade-guard-surface-detected"

    score = max(0, 100 - sum(value for _, value in deductions))
    tier = _confidence_tier(score)

    if gate_status == "suppressed":
        actionability = "suppressed"
    elif score >= 75:
        actionability = "actionable"
    else:
        actionability = "low_confidence"

    return ConfidenceAssessment(
        severity=severity,
        score=score,
        tier=tier,
        deductions=tuple(deductions),
        gate_status=gate_status,
        gate_reason=gate_reason,
        actionability=actionability,
    )


def scan_repo(
    *,
    spec: RepoSpec,
    repo_dir: Path,
    resolved_ref: str,
    git_host: str,
    detector_map: dict[str, Callable[[str], bool]],
    excluded_markers: tuple[str, ...],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    all_files = iter_cairo_files(repo_dir)
    prod_files = [
        p for p in all_files if not is_excluded(p.relative_to(repo_dir), excluded_markers)
    ]

    findings: list[dict[str, object]] = []
    for file_path in prod_files:
        rel = file_path.relative_to(repo_dir).as_posix()
        try:
            code = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(
                f"WARNING: utf-8 decode fallback for {spec.slug}:{rel}; using errors='ignore'",
                file=sys.stderr,
            )
            code = file_path.read_text(encoding="utf-8", errors="ignore")

        for class_id, detector in detector_map.items():
            if detector(code):
                assessment = assess_finding(class_id=class_id, code=code)
                findings.append(
                    {
                        "repo": spec.slug,
                        "ref": resolved_ref,
                        "file": rel,
                        "class_id": class_id,
                        "scope": "prod_scan",
                        "predicted_detect": True,
                        "severity": assessment.severity,
                        "confidence_score": assessment.score,
                        "confidence_tier": assessment.tier,
                        "confidence_deductions": [
                            {"reason": reason, "value": value}
                            for reason, value in assessment.deductions
                        ],
                        "gate_status": assessment.gate_status,
                        "gate_reason": assessment.gate_reason,
                        "actionability": assessment.actionability,
                        "scan_stage": "deterministic_stage1",
                    }
                )

    counts_by_actionability = Counter(str(row["actionability"]) for row in findings)
    repo_summary = {
        "repo": spec.slug,
        "url": repo_git_url(spec, git_host),
        "ref": resolved_ref,
        "all_cairo_files": len(all_files),
        "prod_cairo_files": len(prod_files),
        "prod_hits": len(findings),
        "prod_hits_actionable": counts_by_actionability.get("actionable", 0),
        "prod_hits_low_confidence": counts_by_actionability.get("low_confidence", 0),
        "prod_hits_suppressed": counts_by_actionability.get("suppressed", 0),
    }
    return repo_summary, findings


def render_markdown(
    *,
    scan_id: str,
    generated_at: str,
    repo_summaries: list[dict[str, object]],
    class_counts: Counter[str],
    repo_counts: Counter[str],
    findings: list[dict[str, object]],
    output_json: Path,
) -> str:
    json_path = output_json.as_posix()
    try:
        json_path = output_json.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        json_path = output_json.name

    by_actionability = Counter(str(row["actionability"]) for row in findings)

    lines: list[str] = []
    lines.append(f"# External Repo Detector Sweep ({scan_id})")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append("")
    lines.append("Machine-readable artifact:")
    lines.append("")
    lines.append(f"- `{json_path}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    for i, row in enumerate(repo_summaries, start=1):
        lines.append(f"{i}. `{row['repo']}@{str(row['ref'])[:12]}`")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("| Repo | Cairo files (all) | Cairo files (prod-only) | Raw Hits | Actionable | Low-Confidence | Suppressed |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in repo_summaries:
        lines.append(
            "| {repo} | {all_files} | {prod_files} | {raw} | {actionable} | {low} | {suppressed} |".format(
                repo=row["repo"],
                all_files=row["all_cairo_files"],
                prod_files=row["prod_cairo_files"],
                raw=row["prod_hits"],
                actionable=row["prod_hits_actionable"],
                low=row["prod_hits_low_confidence"],
                suppressed=row["prod_hits_suppressed"],
            )
        )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(f"- Total raw findings: **{len(findings)}**")
    lines.append(f"- Actionable findings (`score >= 75` and gate pass): **{by_actionability.get('actionable', 0)}**")
    lines.append(f"- Low-confidence notes: **{by_actionability.get('low_confidence', 0)}**")
    lines.append(f"- Suppressed by strict gate: **{by_actionability.get('suppressed', 0)}**")
    lines.append("")
    lines.append("By class:")
    lines.append("")
    for class_id, count in sorted(class_counts.items()):
        lines.append(f"- `{class_id}`: {count}")
    lines.append("")
    lines.append("By repo:")
    lines.append("")
    for row in sorted(repo_summaries, key=lambda item: str(item["repo"])):
        repo = str(row["repo"])
        lines.append(f"- `{repo}`: {repo_counts.get(repo, 0)}")
    lines.append("")
    if findings:
        lines.append("## Findings")
        lines.append("")
        lines.append("| Repo | File | Class | Severity | Score | Tier | Actionability | Gate |")
        lines.append("| --- | --- | --- | --- | ---: | --- | --- | --- |")
        for row in findings:
            gate = str(row.get("gate_status", "pass"))
            gate_reason = str(row.get("gate_reason", ""))
            gate_display = gate if not gate_reason else f"{gate} ({gate_reason})"
            lines.append(
                "| `{repo}` | `{file}` | `{class_id}` | {severity} | {score} | {tier} | {actionability} | {gate} |".format(
                    repo=row["repo"],
                    file=row["file"],
                    class_id=row["class_id"],
                    severity=row.get("severity", "medium"),
                    score=row.get("confidence_score", 100),
                    tier=row.get("confidence_tier", "high"),
                    actionability=row.get("actionability", "actionable"),
                    gate=gate_display,
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(SPREADSHEET_FORMULA_PREFIXES):
        return "'" + text
    return text


def write_repo_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "repo",
        "ref",
        "all_cairo_files",
        "prod_cairo_files",
        "prod_hits",
        "prod_hits_actionable",
        "prod_hits_low_confidence",
        "prod_hits_suppressed",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_safe(row.get(key, "")) for key in fieldnames})


def write_findings_csv(path: Path, findings: list[dict[str, object]]) -> None:
    fieldnames = [
        "repo",
        "ref",
        "file",
        "class_id",
        "scope",
        "severity",
        "confidence_score",
        "confidence_tier",
        "actionability",
        "gate_status",
        "gate_reason",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in findings:
            writer.writerow({key: _csv_safe(row.get(key, "")) for key in fieldnames})


def write_manual_triage_csv(path: Path, findings: list[dict[str, object]], *, id_prefix: str) -> None:
    fieldnames = [
        "finding_id",
        "repo",
        "ref",
        "file",
        "class_id",
        "scope",
        "predicted_detect",
        "severity",
        "confidence_score",
        "confidence_tier",
        "actionability",
        "gate_status",
        "gate_reason",
        "manual_verdict",
        "manual_notes",
    ]
    rows_sorted = sorted(
        findings,
        key=lambda row: (
            str(row.get("repo", "")),
            str(row.get("file", "")),
            str(row.get("class_id", "")),
        ),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(rows_sorted, start=1):
            out = {key: _csv_safe(row.get(key, "")) for key in fieldnames}
            out["finding_id"] = _csv_safe(f"{id_prefix}-{i:03d}")
            out["manual_verdict"] = ""
            out["manual_notes"] = ""
            writer.writerow(out)


def derive_default_csv_path(output_json: Path, suffix: str) -> Path:
    base = output_json.with_suffix("")
    return Path(f"{base.as_posix()}.{suffix}.csv")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan external repos with cairo-auditor detectors.")
    parser.add_argument("--scan-id", required=True)
    parser.add_argument("--repos", nargs="*", default=[])
    parser.add_argument("--repos-file", default="")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", default="")
    parser.add_argument("--output-findings-jsonl", default="")
    parser.add_argument("--output-repo-summary-csv", default="")
    parser.add_argument("--output-findings-csv", default="")
    parser.add_argument("--output-manual-triage-csv", default="")
    parser.add_argument("--manual-triage-id-prefix", default="EXT")
    parser.add_argument(
        "--write-csv",
        action="store_true",
        help="Write repo-summary/findings/manual-triage CSV outputs next to --output-json.",
    )
    parser.add_argument(
        "--workdir",
        default=str(Path(tempfile.gettempdir()) / "starknet-skills-external-scan"),
    )
    parser.add_argument(
        "--exclude",
        default="test,tests,mock,mocks,example,examples,preset,presets,fixture,fixtures,vendor,vendors",
    )
    parser.add_argument("--detectors", default="")
    parser.add_argument("--git-host", default="https://github.com")
    args = parser.parse_args()

    repo_specs: list[RepoSpec] = []
    for raw in args.repos:
        repo_specs.append(parse_repo_spec(raw))
    if args.repos_file:
        for line in Path(args.repos_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            repo_specs.append(parse_repo_spec(line))
    if not repo_specs:
        raise ValueError("no repos provided")

    detector_map = DETECTORS
    if args.detectors:
        selected = [d.strip() for d in args.detectors.split(",") if d.strip()]
        missing = [d for d in selected if d not in DETECTORS]
        if missing:
            raise ValueError(f"unknown detector(s): {missing}")
        detector_map = {k: DETECTORS[k] for k in selected}

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    excluded_markers = tuple(s.strip().lower() for s in args.exclude.split(",") if s.strip())

    repo_summaries: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []

    for spec in repo_specs:
        try:
            repo_dir, resolved_ref = clone_repo(spec, workdir, args.git_host)
            summary, repo_findings = scan_repo(
                spec=spec,
                repo_dir=repo_dir,
                resolved_ref=resolved_ref,
                git_host=args.git_host,
                detector_map=detector_map,
                excluded_markers=excluded_markers,
            )
            repo_summaries.append(summary)
            findings.extend(repo_findings)
        except Exception as exc:
            msg = str(exc).splitlines()[0][:400]
            print(f"WARNING: skipping {spec.slug}: {msg}", file=sys.stderr)
            failures.append({"repo": spec.slug, "ref": spec.ref or "", "error": msg})

    class_counts = Counter(str(row["class_id"]) for row in findings)
    repo_counts = Counter(str(row["repo"]) for row in findings)
    actionability_counts = Counter(str(row["actionability"]) for row in findings)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, object] = {
        "scan_id": args.scan_id,
        "generated_at": generated_at,
        "scanner": {
            "tool": "scripts/quality/scan_external_repos.py",
            "detectors_source": "scripts/quality/benchmark_cairo_auditor.py",
            "detectors": sorted(detector_map.keys()),
            "exclude_markers": list(excluded_markers),
            "confidence_model": {
                "start_score": 100,
                "threshold_actionable": 75,
                "deductions": {
                    "privileged-caller-path": 25,
                    "partial-path-needs-context": 20,
                    "potentially-self-contained-impact": 15,
                    "framework-guard-surface-present": 10,
                },
            },
        },
        "repos": repo_summaries,
        "summary": {
            "all_cairo_files": sum(int(r["all_cairo_files"]) for r in repo_summaries),
            "prod_cairo_files": sum(int(r["prod_cairo_files"]) for r in repo_summaries),
            "prod_hits": len(findings),
            "prod_hits_actionable": actionability_counts.get("actionable", 0),
            "prod_hits_low_confidence": actionability_counts.get("low_confidence", 0),
            "prod_hits_suppressed": actionability_counts.get("suppressed", 0),
        },
        "failures": failures,
        "findings": findings,
    }
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.output_findings_jsonl:
        out_jsonl = Path(args.output_findings_jsonl)
        out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with out_jsonl.open("w", encoding="utf-8") as handle:
            for row in findings:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    if args.output_md:
        out_md = Path(args.output_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        markdown = render_markdown(
            scan_id=args.scan_id,
            generated_at=generated_at,
            repo_summaries=repo_summaries,
            class_counts=class_counts,
            repo_counts=repo_counts,
            findings=findings,
            output_json=output_json,
        )
        out_md.write_text(markdown, encoding="utf-8")

    output_repo_summary_csv = Path(args.output_repo_summary_csv) if args.output_repo_summary_csv else None
    output_findings_csv = Path(args.output_findings_csv) if args.output_findings_csv else None
    output_manual_triage_csv = Path(args.output_manual_triage_csv) if args.output_manual_triage_csv else None

    if args.write_csv:
        if output_repo_summary_csv is None:
            output_repo_summary_csv = derive_default_csv_path(output_json, "repo-summary")
        if output_findings_csv is None:
            output_findings_csv = derive_default_csv_path(output_json, "findings")
        if output_manual_triage_csv is None:
            output_manual_triage_csv = derive_default_csv_path(output_json, "manual-triage")

    if output_repo_summary_csv is not None:
        write_repo_summary_csv(output_repo_summary_csv, repo_summaries)
    if output_findings_csv is not None:
        write_findings_csv(output_findings_csv, findings)
    if output_manual_triage_csv is not None:
        write_manual_triage_csv(
            output_manual_triage_csv,
            findings,
            id_prefix=args.manual_triage_id_prefix,
        )

    print(
        json.dumps(
            {
                "scan_id": args.scan_id,
                "repos": len(repo_summaries),
                "findings": len(findings),
                "actionable": actionability_counts.get("actionable", 0),
                "output": output_json.as_posix(),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
