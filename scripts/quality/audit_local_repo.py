#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from benchmark_cairo_auditor import DETECTORS
from scan_external_repos import RepoSpec, is_excluded
from sierra_parallel_signal import analyze_repo


def _existing_dir(value: str) -> Path:
    path = Path(value).resolve()
    if not path.exists() or not path.is_dir():
        raise argparse.ArgumentTypeError(f"directory does not exist: {path}")
    return path


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


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    safe = []
    for ch in lowered:
        if ch.isalnum() or ch in ("-", "_"):
            safe.append(ch)
        else:
            safe.append("-")
    normalized = "".join(safe).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized or "local-cairo-audit"


def _resolve_path(raw: str, base: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate.resolve()
    return (base / candidate).resolve()


def _next_available_stem(
    output_dir: Path,
    base_stem: str,
    fallback_suffixes: list[str],
    *,
    max_attempts: int = 10_000,
) -> tuple[str, Path]:
    idx = 0
    while idx < max_attempts:
        candidate = base_stem if idx == 0 else f"{base_stem}-{idx}"
        lock_path = output_dir / f".{candidate}.lock"
        try:
            lock_path.touch(exist_ok=False)
        except FileExistsError:
            idx += 1
            continue
        if all(not (output_dir / f"{candidate}{suffix}").exists() for suffix in fallback_suffixes):
            return candidate, lock_path
        lock_path.unlink(missing_ok=True)
        idx += 1
    raise RuntimeError(
        f"could not allocate unique output stem after {max_attempts} attempts: {base_stem}"
    )


def _write_text_output(path: Path, content: str, *, overwrite: bool) -> None:
    mode = "w" if overwrite else "x"
    with path.open(mode, encoding="utf-8") as handle:
        handle.write(content)


def _scan_local(repo_root: Path, repo_slug: str, ref: str, excluded_markers: tuple[str, ...]) -> tuple[dict[str, object], list[dict[str, object]]]:
    repo_resolved = repo_root.resolve()
    all_files: list[Path] = []
    for path in sorted(repo_root.rglob("*.cairo")):
        if path.is_symlink():
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(repo_resolved)
        except ValueError:
            continue
        all_files.append(path)
    prod_files = [p for p in all_files if not is_excluded(p, excluded_markers)]

    findings: list[dict[str, object]] = []
    for file_path in prod_files:
        rel = file_path.relative_to(repo_root).as_posix()
        try:
            code = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            print(
                f"WARNING: utf-8 decode fallback for {rel}; using errors='ignore' ({exc})",
                file=sys.stderr,
            )
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
    parser = argparse.ArgumentParser(
        description=(
            "Scan a local Cairo repo with deterministic detectors and optional Sierra confirmation. "
            "Exit codes: 0 for success, 2 when findings exist and --fail-on-findings is set."
        )
    )
    parser.add_argument("--repo-root", type=_existing_dir, default=Path(".").resolve())
    parser.add_argument("--scan-id", default="local-cairo-audit")
    parser.add_argument("--exclude", default="test,tests,mock,mocks,example,examples,preset,presets,fixture,fixtures,vendor,vendors")
    parser.add_argument(
        "--output-dir",
        default="evals/reports/local",
        help="Directory for generated reports when explicit output files are not provided (relative paths resolve from --repo-root).",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Write JSON report to this path (relative paths resolve from --repo-root). Defaults to output-dir.",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Write Markdown report to this path (relative paths resolve from --repo-root). Defaults to output-dir.",
    )
    parser.add_argument(
        "--output-findings-jsonl",
        default="",
        help="Write findings JSONL to this path (relative paths resolve from --repo-root).",
    )
    parser.add_argument(
        "--write-findings-jsonl",
        action="store_true",
        help="Write findings JSONL to output-dir when --output-findings-jsonl is not set.",
    )
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
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit with code 2 when findings are present.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root

    repo_slug = repo_root.name
    ref = _git_head(repo_root)
    excluded_markers = tuple(s.strip().lower() for s in args.exclude.split(",") if s.strip())
    generated_at = datetime.now(UTC).replace(microsecond=0)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    safe_scan_id = _slug(args.scan_id)
    default_stem = f"{safe_scan_id}-{stamp}"

    output_dir = _resolve_path(args.output_dir, repo_root)
    # Setting --output-findings-jsonl implies --write-findings-jsonl.
    write_findings_jsonl = bool(args.output_findings_jsonl) or args.write_findings_jsonl
    # Only create output_dir when at least one output path falls back to it.
    uses_output_dir = (not args.output_json) or (not args.output_md) or (write_findings_jsonl and not args.output_findings_jsonl)
    if uses_output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    fallback_suffixes: list[str] = []
    if not args.output_json:
        fallback_suffixes.append(".json")
    if not args.output_md:
        fallback_suffixes.append(".md")
    if write_findings_jsonl and not args.output_findings_jsonl:
        fallback_suffixes.append(".findings.jsonl")
    lock_path: Path | None = None
    if fallback_suffixes:
        stem, lock_path = _next_available_stem(output_dir, default_stem, fallback_suffixes)
    else:
        stem = default_stem

    out_json = _resolve_path(args.output_json, repo_root) if args.output_json else (output_dir / f"{stem}.json")
    out_md = _resolve_path(args.output_md, repo_root) if args.output_md else (output_dir / f"{stem}.md")
    json_explicit = bool(args.output_json)
    md_explicit = bool(args.output_md)
    jsonl_explicit = bool(args.output_findings_jsonl)
    out_jsonl: Path | None = None
    if write_findings_jsonl:
        out_jsonl = (
            _resolve_path(args.output_findings_jsonl, repo_root)
            if jsonl_explicit
            else (output_dir / f"{stem}.findings.jsonl")
        )

    resolved_outputs: list[tuple[str, Path]] = [("json", out_json), ("md", out_md)]
    if out_jsonl is not None:
        resolved_outputs.append(("findings_jsonl", out_jsonl))
    by_path: dict[Path, list[str]] = {}
    for label, path in resolved_outputs:
        by_path.setdefault(path, []).append(label)
    duplicates = {path: labels for path, labels in by_path.items() if len(labels) > 1}
    if duplicates:
        detail = "; ".join(
            f"{path.as_posix()}: {', '.join(labels)}" for path, labels in duplicates.items()
        )
        if lock_path:
            lock_path.unlink(missing_ok=True)
            lock_path = None
        parser.error(f"output paths must be distinct ({detail})")
    if out_jsonl is not None and jsonl_explicit and out_jsonl.exists():
        if lock_path:
            lock_path.unlink(missing_ok=True)
            lock_path = None
        parser.error(f"explicit findings JSONL path already exists: {out_jsonl.as_posix()}")

    try:
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

        generated_at_iso = generated_at.isoformat()
        payload: dict[str, object] = {
            "scan_id": args.scan_id,
            "generated_at": generated_at_iso,
            "summary": summary,
            "class_counts": dict(class_counts),
            "findings": findings,
            "sierra_confirmation": sierra_payload,
        }
        sierra_gate_findings = 0
        sierra_gate_reasons: list[str] = []
        if sierra_payload:
            confirmation = sierra_payload.get("confirmation", {})
            if isinstance(confirmation, dict):
                if bool(confirmation.get("upgrade_ir_missing")):
                    sierra_gate_findings += 1
                    sierra_gate_reasons.append("upgrade_ir_missing")
                if bool(confirmation.get("cei_ir_missing")):
                    sierra_gate_findings += 1
                    sierra_gate_reasons.append("cei_ir_missing")

        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_md.parent.mkdir(parents=True, exist_ok=True)

        _write_text_output(
            out_json,
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            overwrite=json_explicit,
        )
        _write_text_output(
            out_md,
            _render_markdown(
                scan_id=args.scan_id,
                generated_at=generated_at_iso,
                summary=summary,
                class_counts=class_counts,
                findings=findings,
                sierra=sierra_payload,
            ),
            overwrite=md_explicit,
        )

        if out_jsonl:
            out_jsonl.parent.mkdir(parents=True, exist_ok=True)
            with out_jsonl.open("x", encoding="utf-8") as handle:
                for row in findings:
                    handle.write(json.dumps(row, ensure_ascii=True) + "\n")

        print(
            json.dumps(
                {
                    "scan_id": args.scan_id,
                    "repo_root": repo_root.as_posix(),
                    "findings": len(findings),
                    "class_counts": dict(class_counts),
                    "output_json": out_json.as_posix(),
                    "output_md": out_md.as_posix(),
                    "output_findings_jsonl": out_jsonl.as_posix() if out_jsonl else None,
                    "sierra_gate_findings": sierra_gate_findings,
                    "sierra_gate_reasons": sierra_gate_reasons,
                },
                ensure_ascii=True,
            )
        )

        if args.fail_on_findings and (findings or sierra_gate_findings):
            print(
                "audit gate: "
                + f"{len(findings)} source finding(s), {sierra_gate_findings} Sierra gap finding(s) "
                + f"detected - exit 2 (see {out_json.as_posix()})",
                file=sys.stderr,
            )
            return 2
        return 0
    except FileExistsError as exc:
        parser.error(f"output path already exists: {Path(exc.filename or '').as_posix()}")
    finally:
        if lock_path:
            lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
