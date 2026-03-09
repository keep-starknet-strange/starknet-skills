#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scan_external_repos import is_excluded, iter_cairo_files

PACK_FILES = {
    "low-profile": "evals/reports/data/external-repo-scan-low-profile-repos.txt",
    "wave2": "evals/reports/data/external-repo-scan-wave2-repos.txt",
    "less-known": "evals/packs/less-known.txt",
}


@dataclass(frozen=True)
class OutputPaths:
    json: Path
    markdown: Path
    findings_jsonl: Path
    repo_summary_csv: Path
    findings_csv: Path
    manual_triage_csv: Path
    stage2_manifest_json: Path
    stage2_runbook_md: Path


def _slug(text: str) -> str:
    out: list[str] = []
    for ch in text.lower().strip():
        if ch.isalnum() or ch in {"-", "_"}:
            out.append(ch)
        else:
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "external-pack"


def _resolve_repo_file(repo_root: Path, args: argparse.Namespace) -> tuple[Path, str]:
    if args.repos_file:
        path = Path(args.repos_file)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"repos file not found: {path}")
        return path, path.stem

    if args.repos:
        temp_file = (Path(args.output_dir).resolve() / f"{_slug(args.pack)}-inline-repos.txt")
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file.write_text("\n".join(args.repos) + "\n", encoding="utf-8")
        return temp_file, f"{_slug(args.pack)}-inline"

    rel = PACK_FILES.get(args.pack)
    if rel is None:
        raise ValueError(f"unknown pack: {args.pack}")
    path = (repo_root / rel).resolve()
    if not path.exists():
        raise FileNotFoundError(f"pack file missing: {path}")
    return path, _slug(args.pack)


def _build_output_paths(output_dir: Path, scan_id: str) -> OutputPaths:
    base = output_dir / scan_id
    return OutputPaths(
        json=Path(f"{base.as_posix()}.json"),
        markdown=Path(f"{base.as_posix()}.md"),
        findings_jsonl=Path(f"{base.as_posix()}.findings.jsonl"),
        repo_summary_csv=Path(f"{base.as_posix()}.repo-summary.csv"),
        findings_csv=Path(f"{base.as_posix()}.findings.csv"),
        manual_triage_csv=Path(f"{base.as_posix()}.manual-triage.csv"),
        stage2_manifest_json=Path(f"{base.as_posix()}.stage2-manifest.json"),
        stage2_runbook_md=Path(f"{base.as_posix()}.stage2-runbook.md"),
    )


def _run_scan(
    *,
    repo_root: Path,
    repos_file: Path,
    outputs: OutputPaths,
    scan_id: str,
    workdir: Path,
    exclude: str,
    detectors: str,
    git_host: str,
    manual_prefix: str,
    timeout_seconds: float,
) -> dict[str, object]:
    scan_script = repo_root / "scripts/quality/scan_external_repos.py"
    cmd = [
        sys.executable,
        str(scan_script),
        "--scan-id",
        scan_id,
        "--repos-file",
        str(repos_file),
        "--output-json",
        str(outputs.json),
        "--output-md",
        str(outputs.markdown),
        "--output-findings-jsonl",
        str(outputs.findings_jsonl),
        "--output-repo-summary-csv",
        str(outputs.repo_summary_csv),
        "--output-findings-csv",
        str(outputs.findings_csv),
        "--output-manual-triage-csv",
        str(outputs.manual_triage_csv),
        "--manual-triage-id-prefix",
        manual_prefix,
        "--workdir",
        str(workdir),
        "--exclude",
        exclude,
        "--git-host",
        git_host,
    ]
    if detectors.strip():
        cmd.extend(["--detectors", detectors.strip()])

    try:
        proc = subprocess.run(
            cmd,
            check=True,
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        cmd_str = " ".join(cmd)
        raise RuntimeError(
            f"Stage-1 scan timed out after {timeout_seconds}s while running: {cmd_str}. "
            f"Original error: {exc}"
        ) from exc
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    return json.loads(outputs.json.read_text(encoding="utf-8"))


def _load_reference(repo_root: Path, rel: str) -> str:
    path = (repo_root / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"required stage-2 reference missing: {path}. "
            "Ensure cairo-auditor references are present (for example: "
            "`git submodule update --init --recursive`)."
        )
    return path.read_text(encoding="utf-8")


def _render_bundle(
    *,
    repo_slug: str,
    ref: str,
    actionable_findings: list[dict[str, object]],
    included_sources: list[tuple[str, str]],
    judging_text: str,
    report_formatting_text: str,
    vector_text: str,
    vector_file: str,
    truncation_notes: list[str],
) -> str:
    lines: list[str] = []
    lines.append(f"# Stage-2 Specialist Bundle: {repo_slug}")
    lines.append("")
    lines.append(f"- Repo: `{repo_slug}`")
    lines.append(f"- Ref: `{ref}`")
    lines.append(f"- Vector partition: `{vector_file}`")
    lines.append(f"- Actionable findings from Stage-1: `{len(actionable_findings)}`")
    lines.append("")
    lines.append("## Stage-1 Actionable Findings")
    lines.append("")
    lines.append("| File | Class | Severity | Score |")
    lines.append("| --- | --- | --- | ---: |")
    for finding in actionable_findings:
        lines.append(
            f"| `{finding['file']}` | `{finding['class_id']}` | {finding.get('severity', 'medium')} | {finding.get('confidence_score', 100)} |"
        )
    lines.append("")
    lines.append("## In-Scope Source (Production Files)")
    lines.append("")
    if truncation_notes:
        lines.append("Warnings:")
        lines.append("")
        for note in truncation_notes:
            lines.append(f"- {note}")
        lines.append("")
    for rel_path, code in included_sources:
        lines.append(f"### {rel_path}")
        lines.append("```cairo")
        lines.append(code.rstrip())
        lines.append("```")
        lines.append("")
    lines.append("## Judging (FP Gate + Confidence)")
    lines.append("")
    lines.append(judging_text.rstrip())
    lines.append("")
    lines.append("## Report Formatting")
    lines.append("")
    lines.append(report_formatting_text.rstrip())
    lines.append("")
    lines.append("## Attack Vectors")
    lines.append("")
    lines.append(vector_text.rstrip())
    lines.append("")
    return "\n".join(lines)


def _prepare_stage2(
    *,
    repo_root: Path,
    payload: dict[str, object],
    output_paths: OutputPaths,
    workdir: Path,
    excluded_markers: tuple[str, ...],
    bundle_max_files: int,
    bundle_max_bytes: int,
    bundle_max_chars: int,
) -> None:
    findings = [row for row in payload.get("findings", []) if isinstance(row, dict)]
    actionable = [row for row in findings if row.get("actionability") == "actionable"]

    by_repo: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in actionable:
        by_repo[str(row["repo"])].append(row)

    stage2_dir = output_paths.stage2_manifest_json.parent / f"{output_paths.json.stem}.stage2-bundles"
    stage2_dir.mkdir(parents=True, exist_ok=True)

    repo_index = {str(row.get("repo")): row for row in payload.get("repos", []) if isinstance(row, dict)}

    manifest: dict[str, object] = {
        "scan_id": payload.get("scan_id", "unknown"),
        "generated_at": payload.get("generated_at", ""),
        "stage": "deterministic_stage1_plus_stage2_bundle_prepare",
        "repos_with_actionable_findings": len(by_repo),
        "warnings": [],
        "repos": [],
    }

    runbook_lines: list[str] = []
    runbook_lines.append(f"# Stage-2 Deep Pass Runbook ({payload.get('scan_id', 'unknown')})")
    runbook_lines.append("")
    runbook_lines.append("This runbook is generated from deterministic Stage-1 findings.")
    runbook_lines.append("Use `cairo-auditor` in `deep` mode with each bundle below.")
    runbook_lines.append("")

    vector_files = [
        "cairo-auditor/references/attack-vectors/attack-vectors-1.md",
        "cairo-auditor/references/attack-vectors/attack-vectors-2.md",
        "cairo-auditor/references/attack-vectors/attack-vectors-3.md",
        "cairo-auditor/references/attack-vectors/attack-vectors-4.md",
    ]
    required_refs = [
        "cairo-auditor/references/judging.md",
        "cairo-auditor/references/report-formatting.md",
        *vector_files,
    ]
    reference_map: dict[str, str] = {}
    missing_refs: list[str] = []
    for rel in required_refs:
        try:
            reference_map[rel] = _load_reference(repo_root, rel)
        except FileNotFoundError as exc:
            missing_refs.append(str(exc))

    if missing_refs:
        manifest["warnings"] = missing_refs
        runbook_lines.append("Stage-2 bundle preparation skipped due to missing reference files:")
        runbook_lines.append("")
        for msg in missing_refs:
            runbook_lines.append(f"- {msg}")
        runbook_lines.append("")
        output_paths.stage2_manifest_json.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        output_paths.stage2_runbook_md.write_text("\n".join(runbook_lines) + "\n", encoding="utf-8")
        return

    judging_text = reference_map["cairo-auditor/references/judging.md"]
    report_formatting_text = reference_map["cairo-auditor/references/report-formatting.md"]
    vector_texts = [reference_map[rel] for rel in vector_files]

    for repo_slug, repo_findings in sorted(by_repo.items()):
        ref = str(repo_index.get(repo_slug, {}).get("ref", ""))
        repo_clone_dir = workdir / repo_slug.replace("/", "__")
        if not repo_clone_dir.exists():
            warning = (
                f"clone directory missing for actionable repo: {repo_slug} "
                f"({repo_clone_dir.as_posix()})"
            )
            print(f"WARNING: {warning}", file=sys.stderr)
            cast_warnings = manifest.get("warnings")
            if isinstance(cast_warnings, list):
                cast_warnings.append(warning)
            runbook_lines.append(f"## {repo_slug}")
            runbook_lines.append("")
            runbook_lines.append(f"- Ref: `{ref}`")
            runbook_lines.append(f"- Warning: {warning}")
            runbook_lines.append("")
            manifest["repos"].append(
                {
                    "repo": repo_slug,
                    "ref": ref,
                    "clone_dir": repo_clone_dir.as_posix(),
                    "skipped": True,
                    "skip_reason": "clone_dir_missing",
                    "actionable_findings": len(repo_findings),
                }
            )
            continue

        prod_files = [
            path
            for path in iter_cairo_files(repo_clone_dir)
            if not is_excluded(path.relative_to(repo_clone_dir), excluded_markers)
        ]
        selected_files: list[Path] = []
        total_bytes = 0
        truncated_by_count = False
        truncated_by_bytes = False
        for path in prod_files:
            if len(selected_files) >= bundle_max_files:
                truncated_by_count = True
                break
            try:
                file_size = path.stat().st_size
            except OSError:
                file_size = 0
            if (total_bytes + file_size) > bundle_max_bytes:
                truncated_by_bytes = True
                break
            selected_files.append(path)
            total_bytes += file_size

        included_sources: list[tuple[str, str]] = []
        embedded_bytes = 0
        embedded_chars = 0
        truncated_by_chars = False
        for path in selected_files:
            rel = path.relative_to(repo_clone_dir).as_posix()
            try:
                code = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                code = path.read_text(encoding="utf-8", errors="ignore")
            if (embedded_chars + len(code)) > bundle_max_chars:
                truncated_by_chars = True
                break
            included_sources.append((rel, code))
            embedded_chars += len(code)
            embedded_bytes += len(code.encode("utf-8"))

        repo_bundle_dir = stage2_dir / repo_slug.replace("/", "__")
        repo_bundle_dir.mkdir(parents=True, exist_ok=True)

        truncation_notes: list[str] = []
        if truncated_by_count:
            truncation_notes.append(
                f"Source list truncated by file-count cap (`--bundle-max-files={bundle_max_files}`)."
            )
        if truncated_by_bytes:
            truncation_notes.append(
                f"Source list truncated by byte-size cap (`--bundle-max-bytes={bundle_max_bytes}`)."
            )
        if truncated_by_chars:
            truncation_notes.append(
                f"Source list truncated by character cap (`--bundle-max-chars={bundle_max_chars}`)."
            )
        if not included_sources and prod_files:
            truncation_notes.append(
                "No files were included under current limits; increase bundle caps for full context."
            )

        bundle_entries: list[dict[str, object]] = []
        for i, (vector_file, vector_text) in enumerate(zip(vector_files, vector_texts), start=1):
            bundle_text = _render_bundle(
                repo_slug=repo_slug,
                ref=ref,
                actionable_findings=sorted(
                    repo_findings,
                    key=lambda row: (
                        str(row.get("file", "")),
                        str(row.get("class_id", "")),
                    ),
                ),
                included_sources=included_sources,
                judging_text=judging_text,
                report_formatting_text=report_formatting_text,
                vector_text=vector_text,
                vector_file=vector_file,
                truncation_notes=truncation_notes,
            )
            bundle_path = repo_bundle_dir / f"audit-agent-{i}-bundle.md"
            bundle_path.write_text(bundle_text, encoding="utf-8")
            line_count = len(bundle_text.splitlines())
            bundle_entries.append(
                {
                    "agent": i,
                    "vector_file": vector_file,
                    "bundle_path": bundle_path.as_posix(),
                    "lines": line_count,
                }
            )

        runbook_lines.append(f"## {repo_slug}")
        runbook_lines.append("")
        runbook_lines.append(f"- Ref: `{ref}`")
        runbook_lines.append(f"- Clone dir: `{repo_clone_dir.as_posix()}`")
        runbook_lines.append(f"- Actionable Stage-1 findings: `{len(repo_findings)}`")
        runbook_lines.append(f"- Bundle dir: `{repo_bundle_dir.as_posix()}`")
        runbook_lines.append("")
        runbook_lines.append("Specialist bundles:")
        runbook_lines.append("")
        for entry in bundle_entries:
            runbook_lines.append(
                f"- Agent {entry['agent']}: `{entry['bundle_path']}` ({entry['lines']} lines, vectors from `{entry['vector_file']}`)"
            )
        runbook_lines.append("")

        manifest["repos"].append(
            {
                "repo": repo_slug,
                "ref": ref,
                "clone_dir": repo_clone_dir.as_posix(),
                "bundle_dir": repo_bundle_dir.as_posix(),
                "prod_files_total": len(prod_files),
                "prod_files_included": len(included_sources),
                "bundle_bytes_included": embedded_bytes,
                "bundle_chars_included": embedded_chars,
                "truncated": bool(truncation_notes),
                "truncated_by_count": truncated_by_count,
                "truncated_by_bytes": truncated_by_bytes,
                "truncated_by_chars": truncated_by_chars,
                "actionable_findings": len(repo_findings),
                "bundles": bundle_entries,
            }
        )

    output_paths.stage2_manifest_json.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_paths.stage2_runbook_md.write_text("\n".join(runbook_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-shot deterministic external pack scan with built-in CSV artifacts and Stage-2 bundle preparation."
    )
    parser.add_argument("--pack", default="less-known", choices=sorted(PACK_FILES.keys()))
    parser.add_argument("--repos-file", default="")
    parser.add_argument("--repos", nargs="*", default=[])
    parser.add_argument("--scan-id", default="")
    parser.add_argument("--output-dir", default="evals/reports/data")
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
    parser.add_argument("--manual-triage-id-prefix", default="")
    parser.add_argument(
        "--scan-timeout-seconds",
        type=float,
        default=1200,
        help="Timeout budget for the Stage-1 scan subprocess.",
    )
    parser.add_argument(
        "--prepare-stage2",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prepare Stage-2 deep-pass specialist bundles from actionable Stage-1 findings.",
    )
    parser.add_argument(
        "--bundle-max-files",
        type=int,
        default=150,
        help="Maximum production cairo files embedded per Stage-2 bundle.",
    )
    parser.add_argument(
        "--bundle-max-bytes",
        type=int,
        default=800_000,
        help="Maximum cumulative source bytes embedded per Stage-2 bundle.",
    )
    parser.add_argument(
        "--bundle-max-chars",
        type=int,
        default=900_000,
        help="Maximum cumulative source characters embedded per Stage-2 bundle.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (repo_root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    repos_file, source_slug = _resolve_repo_file(repo_root, args)
    scan_id = args.scan_id.strip() or f"external-pack-{source_slug}-{date.today().isoformat()}"
    outputs = _build_output_paths(output_dir, scan_id)

    manual_prefix = args.manual_triage_id_prefix.strip()
    if not manual_prefix:
        manual_prefix = _slug(source_slug).upper().replace("-", "")[:10] or "PACK"

    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    payload = _run_scan(
        repo_root=repo_root,
        repos_file=repos_file,
        outputs=outputs,
        scan_id=scan_id,
        workdir=workdir,
        exclude=args.exclude,
        detectors=args.detectors,
        git_host=args.git_host,
        manual_prefix=manual_prefix,
        timeout_seconds=args.scan_timeout_seconds,
    )

    if args.prepare_stage2:
        excluded_markers = tuple(part.strip().lower() for part in args.exclude.split(",") if part.strip())
        _prepare_stage2(
            repo_root=repo_root,
            payload=payload,
            output_paths=outputs,
            workdir=workdir,
            excluded_markers=excluded_markers,
            bundle_max_files=args.bundle_max_files,
            bundle_max_bytes=args.bundle_max_bytes,
            bundle_max_chars=args.bundle_max_chars,
        )

    findings = [row for row in payload.get("findings", []) if isinstance(row, dict)]
    actionable = Counter(str(row.get("actionability", "")) for row in findings).get("actionable", 0)

    print(
        json.dumps(
            {
                "scan_id": scan_id,
                "pack": args.pack,
                "repos_file": repos_file.as_posix(),
                "repos_scanned": len(payload.get("repos", [])),
                "raw_findings": len(findings),
                "actionable_findings": actionable,
                "json": outputs.json.as_posix(),
                "markdown": outputs.markdown.as_posix(),
                "findings_jsonl": outputs.findings_jsonl.as_posix(),
                "repo_summary_csv": outputs.repo_summary_csv.as_posix(),
                "findings_csv": outputs.findings_csv.as_posix(),
                "manual_triage_csv": outputs.manual_triage_csv.as_posix(),
                "stage2_manifest_json": outputs.stage2_manifest_json.as_posix()
                if args.prepare_stage2
                else "",
                "stage2_runbook_md": outputs.stage2_runbook_md.as_posix() if args.prepare_stage2 else "",
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
