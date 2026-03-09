#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from benchmark_cairo_auditor import DETECTORS
from scan_external_repos import RepoSpec, is_excluded
from sierra_parallel_signal import analyze_repo


def _git_head(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return "local"


def _scan_local(repo_root: Path, repo_slug: str, ref: str, excluded_markers: tuple[str, ...]) -> tuple[dict[str, object], list[dict[str, object]]]:
    all_files = sorted(repo_root.rglob("*.cairo"))
    prod_files = [p for p in all_files if not is_excluded(p, excluded_markers)]

    findings: list[dict[str, object]] = []
    for file_path in prod_files:
        rel = file_path.relative_to(repo_root).as_posix()
        try:
            code = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            code = file_path.read_text(encoding="utf-8", errors="ignore")

        for class_id, detector in DETECTORS.items():
            if detector(code):
                findings.append(
                    {
                        "repo": repo_slug,
                        "ref": ref,
                        "file": rel,
                        "class_id": class_id,
                        "scope": "prod_scan",
                    }
                )

    summary = {
        "repo": repo_slug,
        "ref": ref,
        "repo_root": repo_root.as_posix(),
        "all_cairo_files": len(all_files),
        "prod_cairo_files": len(prod_files),
        "prod_hits": len(findings),
    }
    return summary, findings


def _render_markdown(
    *,
    scan_id: str,
    generated_at: str,
    summary: dict[str, object],
    class_counts: Counter[str],
    findings: list[dict[str, object]],
    sierra: dict[str, object] | None,
) -> str:
    lines: list[str] = []
    lines.append(f"# Local Cairo Auditor Scan ({scan_id})")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Repo: `{summary['repo_root']}`")
    lines.append(f"Ref: `{summary['ref']}`")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Cairo files (all): {summary['all_cairo_files']}")
    lines.append(f"- Cairo files (prod-only): {summary['prod_cairo_files']}")
    lines.append(f"- Findings: {summary['prod_hits']}")
    lines.append("")

    lines.append("## Findings by Class")
    lines.append("")
    for class_id, count in sorted(class_counts.items()):
        lines.append(f"- `{class_id}`: {count}")
    lines.append("")

    if sierra:
        lines.append("## Sierra Confirmation")
        lines.append("")
        lines.append("Sierra is used as an auxiliary confirmation layer for selected source-level classes.")
        lines.append("")
        lines.append(f"- Projects built/total: {sierra['projects_built']}/{sierra['projects_total']}")
        lines.append(f"- Artifacts parsed: {sierra['artifacts']}")
        lines.append(f"- Replace-class markers: {sierra['marker_counts'].get('replace_class_syscall', 0)}")
        lines.append(f"- Functions with external->write ordering: {sierra['function_signals'].get('functions_external_then_write', 0)}")
        lines.append(f"- Upgrade oracle: {'confirm' if sierra['confirmation'].get('upgrade_ir_confirmed', False) else 'missing' if sierra['confirmation'].get('upgrade_findings', 0) else '-'}")
        lines.append(f"- CEI oracle: {'confirm' if sierra['confirmation'].get('cei_ir_confirmed', False) else 'missing' if sierra['confirmation'].get('cei_findings', 0) else '-'}")
        if sierra["confirmation"].get("cei_example_functions"):
            functions = ", ".join(f"`{f}`" for f in sierra["confirmation"]["cei_example_functions"])
            lines.append(f"- CEI candidate functions: {functions}")
        if sierra.get("errors"):
            lines.append("- Errors:")
            for err in sierra["errors"]:
                lines.append(f"  - {err}")
        lines.append("")

    if findings:
        lines.append("## Findings")
        lines.append("")
        lines.append("| File | Class |")
        lines.append("| --- | --- |")
        for row in findings[:250]:
            lines.append(f"| `{row['file']}` | `{row['class_id']}` |")
        if len(findings) > 250:
            lines.append(f"| ... | ... ({len(findings) - 250} more) |")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a local Cairo repo with deterministic detectors and optional Sierra confirmation.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--scan-id", default="local-cairo-audit")
    parser.add_argument("--exclude", default="test,tests,mock,mocks,example,examples,preset,presets,fixture,fixtures,vendor,vendors")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-findings-jsonl", default="")
    parser.add_argument("--sierra-confirm", action="store_true", help="Run Sierra confirmation layer on this repo.")
    parser.add_argument(
        "--allow-build",
        action="store_true",
        help="Allow scarb build in Sierra confirmation mode.",
    )
    parser.add_argument(
        "--scarb-timeout-seconds",
        type=float,
        default=240,
        help="Timeout budget for each scarb metadata/build command in Sierra confirmation mode.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise ValueError(f"repo root does not exist: {repo_root}")

    repo_slug = repo_root.name
    ref = _git_head(repo_root)
    excluded_markers = tuple(s.strip().lower() for s in args.exclude.split(",") if s.strip())

    summary, findings = _scan_local(repo_root, repo_slug, ref, excluded_markers)
    class_counts = Counter(str(row["class_id"]) for row in findings)

    sierra_payload: dict[str, object] | None = None
    if args.sierra_confirm:
        signal = analyze_repo(
            spec=RepoSpec(slug=repo_slug, ref=None),
            repo_dir=repo_root,
            ref=ref,
            allow_build=args.allow_build,
            detector_class_counts={repo_slug: class_counts},
            scarb_timeout_s=args.scarb_timeout_seconds,
        )
        sierra_payload = {
            "projects_total": signal.projects_total,
            "projects_built": signal.projects_built,
            "projects_failed": signal.projects_failed,
            "artifacts": signal.artifacts,
            "artifact_breakdown": signal.artifact_breakdown,
            "marker_counts": signal.marker_counts,
            "function_signals": signal.function_signals,
            "signal_flags": signal.signal_flags,
            "confirmation": signal.confirmation,
            "errors": signal.errors,
        }

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    payload: dict[str, object] = {
        "scan_id": args.scan_id,
        "generated_at": generated_at,
        "summary": summary,
        "class_counts": dict(class_counts),
        "findings": findings,
        "sierra_confirmation": sierra_payload,
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    out_md.write_text(
        _render_markdown(
            scan_id=args.scan_id,
            generated_at=generated_at,
            summary=summary,
            class_counts=class_counts,
            findings=findings,
            sierra=sierra_payload,
        ),
        encoding="utf-8",
    )

    if args.output_findings_jsonl:
        out_jsonl = Path(args.output_findings_jsonl)
        out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with out_jsonl.open("w", encoding="utf-8") as handle:
            for row in findings:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    print(
        json.dumps(
            {
                "scan_id": args.scan_id,
                "repo_root": repo_root.as_posix(),
                "findings": len(findings),
                "output_json": out_json.as_posix(),
                "output_md": out_md.as_posix(),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
