#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scan_external_repos import RepoSpec, clone_repo, parse_repo_spec


@dataclass
class RepoSignal:
    repo: str
    ref: str
    projects_total: int
    projects_built: int
    projects_failed: int
    artifacts: int
    artifact_breakdown: dict[str, int]
    marker_counts: dict[str, int]
    function_signals: dict[str, int]
    signal_flags: dict[str, bool | None]
    analysis_status: str
    confirmation: dict[str, object]
    errors: list[str]


MARKERS: dict[str, tuple[str, ...]] = {
    "external_call": ("call_contract_syscall", "library_call"),
    "replace_class_syscall": ("replace_class_syscall",),
    "state_write": ("storage_write_syscall",),
    "state_read": ("storage_read_syscall",),
    "event_emit": ("emit_event_syscall",),
}

UPGRADE_CLASSES = {
    "IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK",
    "UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD",
}
CEI_CLASSES = {
    "CEI_VIOLATION_ERC1155",
}


def run_unchecked(cmd: list[str], cwd: Path, timeout_s: float = 300) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=124,
            stdout="",
            stderr=f"command timed out after {timeout_s:.0f}s: {' '.join(cmd)}",
        )


def find_scarb_projects(repo_dir: Path) -> list[Path]:
    roots: list[Path] = []
    top = repo_dir / "Scarb.toml"
    if top.exists():
        roots.append(repo_dir)
    for path in repo_dir.rglob("Scarb.toml"):
        parent = path.parent
        if parent == repo_dir:
            continue
        rel_parts = parent.relative_to(repo_dir).parts
        if ".git" in rel_parts or "target" in rel_parts:
            continue
        if len(rel_parts) > 4:
            continue
        roots.append(parent)
    unique = sorted({p.resolve() for p in roots})
    return [Path(p) for p in unique]


def _count_markers_in_text(text: str) -> Counter[str]:
    lower = text.lower()
    counts: Counter[str] = Counter()
    for key, needles in MARKERS.items():
        counts[key] = sum(lower.count(needle.lower()) for needle in needles)
    return counts


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def _extract_names_from_contract_debug(debug: dict[str, Any]) -> list[str]:
    names: list[str] = []
    libfunc_names = debug.get("libfunc_names")
    if isinstance(libfunc_names, list):
        for item in libfunc_names:
            if isinstance(item, list) and len(item) > 1 and isinstance(item[1], str):
                names.append(item[1])
            elif isinstance(item, str):
                names.append(item)
    elif isinstance(libfunc_names, dict):
        for value in libfunc_names.values():
            if isinstance(value, str):
                names.append(value)
    return names


def _analyze_contract_class(path: Path) -> tuple[Counter[str], Counter[str], list[str]]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return _count_markers_in_text(path.read_text(encoding="utf-8", errors="ignore")), Counter(), []

    debug = payload.get("sierra_program_debug_info")
    if not isinstance(debug, dict):
        debug = payload.get("debug_info") if isinstance(payload.get("debug_info"), dict) else None
    if not isinstance(debug, dict):
        return _count_markers_in_text(path.read_text(encoding="utf-8", errors="ignore")), Counter(), []

    names = _extract_names_from_contract_debug(debug)
    if not names:
        return Counter(), Counter(), []
    return _count_markers_in_text("\n".join(names)), Counter(), []


def _extract_invocation_name(stmt: dict[str, Any]) -> str | None:
    if "Invocation" not in stmt:
        return None
    inv = stmt.get("Invocation")
    if not isinstance(inv, dict):
        return None
    libfunc = inv.get("libfunc_id")
    if not isinstance(libfunc, dict):
        return None
    debug_name = libfunc.get("debug_name")
    if isinstance(debug_name, str):
        return debug_name
    return None


def _artifact_kind(path: Path) -> str:
    name = path.name
    if name.endswith(".sierra.json"):
        return "sierra_json"
    if name.endswith(".sierra"):
        return "sierra_text"
    if name.endswith(".starknet_artifacts.json"):
        return "starknet_artifacts"
    if name.endswith(".contract_class.json"):
        return "contract_class"
    return "other"


def _analyze_sierra_json(path: Path) -> tuple[Counter[str], Counter[str], list[str]]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return _count_markers_in_text(path.read_text(encoding="utf-8", errors="ignore")), Counter(), []

    statements = payload.get("statements")
    funcs = payload.get("funcs")
    if not isinstance(statements, list) or not isinstance(funcs, list):
        return _count_markers_in_text(path.read_text(encoding="utf-8", errors="ignore")), Counter(), []

    marker_counts: Counter[str] = Counter()
    function_signals: Counter[str] = Counter()
    cei_examples: list[str] = []

    sorted_funcs: list[tuple[int, str]] = []
    for fn in funcs:
        if not isinstance(fn, dict):
            continue
        entry = fn.get("entry_point")
        fn_id = fn.get("id") if isinstance(fn.get("id"), dict) else {}
        fn_name = fn_id.get("debug_name") if isinstance(fn_id, dict) else None
        if not isinstance(entry, int):
            continue
        sorted_funcs.append((entry, fn_name if isinstance(fn_name, str) else "<unknown>"))

    sorted_funcs.sort(key=lambda t: t[0])
    function_signals["functions_total"] = len(sorted_funcs)

    for i, (start, fn_name) in enumerate(sorted_funcs):
        end = sorted_funcs[i + 1][0] if i + 1 < len(sorted_funcs) else len(statements)
        if start >= len(statements) or end <= start:
            continue
        first_external: int | None = None
        first_write: int | None = None
        seen_external = False
        seen_write = False
        seen_upgrade = False

        for idx in range(start, min(end, len(statements))):
            stmt = statements[idx]
            if not isinstance(stmt, dict):
                continue
            debug_name = _extract_invocation_name(stmt)
            if not debug_name:
                continue
            lowered = debug_name.lower()
            for key, needles in MARKERS.items():
                if any(needle in lowered for needle in needles):
                    marker_counts[key] += 1
            if any(needle in lowered for needle in MARKERS["external_call"]):
                seen_external = True
                if first_external is None:
                    first_external = idx
            if any(needle in lowered for needle in MARKERS["state_write"]):
                seen_write = True
                if first_write is None:
                    first_write = idx
            if any(needle in lowered for needle in MARKERS["replace_class_syscall"]):
                seen_upgrade = True

        if seen_external:
            function_signals["functions_with_external_call"] += 1
        if seen_write:
            function_signals["functions_with_state_write"] += 1
        if seen_upgrade:
            function_signals["functions_with_upgrade"] += 1
        if first_external is not None and first_write is not None:
            if first_external < first_write:
                function_signals["functions_external_then_write"] += 1
                if len(cei_examples) < 5:
                    cei_examples.append(fn_name)
            elif first_write < first_external:
                function_signals["functions_write_then_external"] += 1

    return marker_counts, function_signals, cei_examples


def _analyze_artifact(path: Path) -> tuple[Counter[str], Counter[str], list[str]]:
    kind = _artifact_kind(path)
    if kind == "sierra_json":
        return _analyze_sierra_json(path)
    if kind == "contract_class":
        return _analyze_contract_class(path)
    return _count_markers_in_text(path.read_text(encoding="utf-8", errors="ignore")), Counter(), []


def _resolve_target_dirs(project_root: Path, repo_dir: Path, timeout_s: float, errors: list[str]) -> set[Path]:
    target_dirs: set[Path] = set()
    proc = run_unchecked(["scarb", "metadata", "--format-version", "1", "--no-deps"], cwd=project_root, timeout_s=timeout_s)
    if proc.returncode != 0:
        msg = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "scarb metadata failed"
        errors.append(f"{project_root.relative_to(repo_dir).as_posix()}: {msg[:280]}")
        fallback = project_root / "target"
        if fallback.exists():
            target_dirs.add(fallback.resolve())
        return target_dirs

    try:
        payload = json.loads(proc.stdout)
    except Exception as exc:
        errors.append(f"{project_root.relative_to(repo_dir).as_posix()}: metadata parse failed ({str(exc)[:120]})")
        fallback = project_root / "target"
        if fallback.exists():
            target_dirs.add(fallback.resolve())
        return target_dirs

    if isinstance(payload, dict):
        target_dir = payload.get("target_dir")
        if isinstance(target_dir, str) and target_dir:
            td = Path(target_dir)
            if not td.is_absolute():
                td = (project_root / td).resolve()
            target_dirs.add(td)

        workspace = payload.get("workspace")
        if isinstance(workspace, dict):
            ws_root = workspace.get("root")
            if isinstance(ws_root, str) and ws_root:
                ws_target = Path(ws_root) / "target"
                target_dirs.add(ws_target.resolve())

    fallback = (project_root / "target").resolve()
    target_dirs.add(fallback)
    return target_dirs


def _collect_from_starknet_manifest(path: Path) -> set[Path]:
    refs: set[Path] = set()
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return refs

    contracts = payload.get("contracts")
    if not isinstance(contracts, list):
        return refs

    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        artifacts = contract.get("artifacts")
        if not isinstance(artifacts, dict):
            continue
        for artifact_key, rel in artifacts.items():
            if not isinstance(rel, str) or not rel:
                continue
            if artifact_key != "sierra" and not rel.endswith((".contract_class.json", ".sierra", ".sierra.json")):
                continue
            candidate = (path.parent / rel).resolve()
            if candidate.exists() and candidate.is_file():
                refs.add(candidate)
    return refs


def collect_sierra_artifacts(target_dirs: set[Path]) -> list[Path]:
    artifacts: set[Path] = set()

    for target in target_dirs:
        if not target.exists():
            continue
        for pattern in (
            "**/*.sierra.json",
            "**/*.sierra",
            "**/*.starknet_artifacts.json",
            "**/*.contract_class.json",
        ):
            for path in target.glob(pattern):
                if path.is_file():
                    artifacts.add(path.resolve())

    for path in list(artifacts):
        if path.name.endswith(".starknet_artifacts.json"):
            artifacts.update(_collect_from_starknet_manifest(path))

    return sorted(artifacts)


def _build_confirmation(
    *,
    class_counts: Counter[str],
    marker_counts: Counter[str],
    function_signals: Counter[str],
    cei_examples: list[str],
    signal_observed: bool,
) -> dict[str, object]:
    upgrade_findings = sum(class_counts.get(c, 0) for c in UPGRADE_CLASSES)
    cei_findings = sum(class_counts.get(c, 0) for c in CEI_CLASSES)

    has_upgrade_markers = marker_counts["replace_class_syscall"] > 0
    cei_parallel = function_signals["functions_external_then_write"] > 0

    return {
        "upgrade_findings": upgrade_findings,
        "upgrade_ir_confirmed": signal_observed and upgrade_findings > 0 and has_upgrade_markers,
        "upgrade_ir_missing": signal_observed and upgrade_findings > 0 and not has_upgrade_markers,
        "cei_findings": cei_findings,
        "cei_ir_confirmed": signal_observed and cei_findings > 0 and cei_parallel,
        "cei_ir_missing": signal_observed and cei_findings > 0 and not cei_parallel,
        "cei_example_functions": cei_examples,
    }


def analyze_repo(
    spec: RepoSpec,
    repo_dir: Path,
    ref: str,
    allow_build: bool,
    detector_class_counts: dict[str, Counter[str]],
    scarb_timeout_s: float,
) -> RepoSignal:
    scarb_projects = find_scarb_projects(repo_dir)
    marker_counts: Counter[str] = Counter()
    function_signals: Counter[str] = Counter()
    artifact_breakdown: Counter[str] = Counter()
    errors: list[str] = []
    projects_built = 0
    projects_failed = 0
    artifact_count = 0
    seen_artifacts: set[Path] = set()
    cei_examples: list[str] = []

    for project in scarb_projects:
        target_dirs = _resolve_target_dirs(project, repo_dir, scarb_timeout_s, errors)

        if allow_build:
            proc = run_unchecked(["scarb", "build"], cwd=project, timeout_s=scarb_timeout_s)
            if proc.returncode != 0:
                projects_failed += 1
                msg = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "scarb build failed"
                errors.append(f"{project.relative_to(repo_dir).as_posix()}: {msg[:280]}")
                continue
            projects_built += 1

        artifacts = collect_sierra_artifacts(target_dirs)
        for artifact in artifacts:
            if artifact in seen_artifacts:
                continue
            seen_artifacts.add(artifact)
            artifact_count += 1
            artifact_breakdown[_artifact_kind(artifact)] += 1
            m_counts, fn_signals, fn_examples = _analyze_artifact(artifact)
            marker_counts.update(m_counts)
            function_signals.update(fn_signals)
            for fn_name in fn_examples:
                if fn_name not in cei_examples and len(cei_examples) < 5:
                    cei_examples.append(fn_name)

    signal_observed = artifact_count > 0
    if signal_observed:
        flags: dict[str, bool | None] = {
            "has_external_call_markers": marker_counts["external_call"] > 0,
            "has_state_write_markers": marker_counts["state_write"] > 0,
            "has_upgrade_markers": marker_counts["replace_class_syscall"] > 0,
            "cei_parallel_signal": marker_counts["external_call"] > 0 and marker_counts["state_write"] > 0,
            "has_external_then_write_functions": function_signals["functions_external_then_write"] > 0,
        }
        analysis_status = "completed"
    else:
        flags = {
            "has_external_call_markers": None,
            "has_state_write_markers": None,
            "has_upgrade_markers": None,
            "cei_parallel_signal": None,
            "has_external_then_write_functions": None,
        }
        analysis_status = "skipped_no_artifacts"

    class_counts = detector_class_counts.get(spec.slug, Counter())
    confirmation = _build_confirmation(
        class_counts=class_counts,
        marker_counts=marker_counts,
        function_signals=function_signals,
        cei_examples=cei_examples,
        signal_observed=signal_observed,
    )

    return RepoSignal(
        repo=spec.slug,
        ref=ref,
        projects_total=len(scarb_projects),
        projects_built=projects_built,
        projects_failed=projects_failed,
        artifacts=artifact_count,
        artifact_breakdown=dict(artifact_breakdown),
        marker_counts=dict(marker_counts),
        function_signals=dict(function_signals),
        signal_flags=flags,
        analysis_status=analysis_status,
        confirmation=confirmation,
        errors=errors,
    )


def load_detector_summary(path: Path) -> tuple[dict[str, int], dict[str, Counter[str]]]:
    per_repo_hits: dict[str, int] = defaultdict(int)
    per_repo_classes: dict[str, Counter[str]] = defaultdict(Counter)

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        repo = str(row.get("repo", ""))
        class_id = str(row.get("class_id", ""))
        if not repo:
            continue
        per_repo_hits[repo] += 1
        if class_id:
            per_repo_classes[repo][class_id] += 1

    return dict(per_repo_hits), {repo: counts for repo, counts in per_repo_classes.items()}


def render_markdown(
    *,
    scan_id: str,
    generated_at: str,
    rows: list[RepoSignal],
    detector_hits: dict[str, int],
    detector_findings: str,
    allow_build: bool,
) -> str:
    lines: list[str] = []
    lines.append(f"# Sierra Parallel Signal ({scan_id})")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Build mode: {'enabled (unsafe for untrusted repos)' if allow_build else 'disabled (safe mode)'}")
    if detector_findings:
        lines.append(f"Detector findings compared: `{detector_findings}`")
    lines.append("")
    lines.append("Sierra is used here as a confirmation layer for source-level detections (not as a standalone verdict engine).")
    lines.append("")
    lines.append("| Repo | Projects (built/total) | Artifacts | Status | ReplaceClass | Fn Ext->Write | Detector Hits | Upgrade Oracle | CEI Oracle |")
    lines.append("| --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |")
    for row in rows:
        replace = row.marker_counts.get("replace_class_syscall", 0)
        ext_then_write = row.function_signals.get("functions_external_then_write", 0)
        hits = detector_hits.get(row.repo, 0)

        upgrade_findings = int(row.confirmation.get("upgrade_findings", 0))
        if upgrade_findings == 0:
            upgrade_oracle = "-"
        elif row.analysis_status != "completed":
            upgrade_oracle = "unknown"
        else:
            upgrade_oracle = "confirm" if row.confirmation.get("upgrade_ir_confirmed", False) else "missing"

        cei_findings = int(row.confirmation.get("cei_findings", 0))
        if cei_findings == 0:
            cei_oracle = "-"
        elif row.analysis_status != "completed":
            cei_oracle = "unknown"
        else:
            cei_oracle = "confirm" if row.confirmation.get("cei_ir_confirmed", False) else "missing"

        lines.append(
            f"| `{row.repo}` | {row.projects_built}/{row.projects_total} | {row.artifacts} | {row.analysis_status} | {replace} | {ext_then_write} | {hits} | {upgrade_oracle} | {cei_oracle} |"
        )

    lines.append("")
    lines.append("## Artifact Coverage")
    lines.append("")
    for row in rows:
        breakdown = row.artifact_breakdown or {}
        parts = [f"{k}={v}" for k, v in sorted(breakdown.items())]
        lines.append(f"- `{row.repo}`: {', '.join(parts) if parts else 'none'}")
    lines.append("")

    mismatches: list[str] = []
    for row in rows:
        if row.confirmation.get("upgrade_ir_missing", False):
            mismatches.append(f"`{row.repo}` upgrade findings present but no `replace_class_syscall` marker found")
        if row.confirmation.get("cei_ir_missing", False):
            mismatches.append(f"`{row.repo}` CEI findings present but no function-level external->write pattern found")
    if mismatches:
        lines.append("## Confirmation Gaps")
        lines.append("")
        for item in mismatches:
            lines.append(f"- {item}")
        lines.append("")

    ceis = [
        (
            row.repo,
            row.confirmation.get("cei_example_functions", []),
        )
        for row in rows
        if row.confirmation.get("cei_example_functions")
    ]
    if ceis:
        lines.append("## CEI Function Examples (IR)")
        lines.append("")
        for repo, functions in ceis:
            values = ", ".join(f"`{f}`" for f in list(functions)[:5])
            lines.append(f"- `{repo}`: {values}")
        lines.append("")

    errors = [(row.repo, err) for row in rows for err in row.errors]
    if errors:
        lines.append("## Build / Metadata Errors")
        lines.append("")
        for repo, err in errors:
            lines.append(f"- `{repo}`: {err}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Sierra-native parallel confirmation signals across external repos.")
    parser.add_argument("--scan-id", required=True)
    parser.add_argument("--repos", nargs="*", default=[])
    parser.add_argument("--repos-file", default="")
    parser.add_argument("--workdir", default="/tmp/starknet-skills-sierra-scan")
    parser.add_argument("--git-host", default="https://github.com")
    parser.add_argument("--detector-findings-jsonl", default="")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--allow-build",
        action="store_true",
        help="Run `scarb build` inside cloned repos (unsafe for untrusted repos).",
    )
    parser.add_argument(
        "--scarb-timeout-seconds",
        type=float,
        default=240,
        help="Timeout budget for each scarb metadata/build command.",
    )
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

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    detector_hits: dict[str, int] = {}
    detector_class_counts: dict[str, Counter[str]] = {}
    if args.detector_findings_jsonl:
        detector_hits, detector_class_counts = load_detector_summary(Path(args.detector_findings_jsonl))

    rows: list[RepoSignal] = []
    for spec in repo_specs:
        try:
            repo_dir, ref = clone_repo(spec, workdir, args.git_host)
            rows.append(
                analyze_repo(
                    spec,
                    repo_dir,
                    ref,
                    args.allow_build,
                    detector_class_counts,
                    args.scarb_timeout_seconds,
                )
            )
        except Exception as exc:
            rows.append(
                RepoSignal(
                    repo=spec.slug,
                    ref=spec.ref or "",
                    projects_total=0,
                    projects_built=0,
                    projects_failed=0,
                    artifacts=0,
                    artifact_breakdown={},
                    marker_counts={},
                    function_signals={},
                    signal_flags={
                        "has_external_call_markers": None,
                        "has_state_write_markers": None,
                        "has_upgrade_markers": None,
                        "cei_parallel_signal": None,
                        "has_external_then_write_functions": None,
                    },
                    analysis_status="failed",
                    confirmation={
                        "upgrade_findings": 0,
                        "upgrade_ir_confirmed": False,
                        "upgrade_ir_missing": False,
                        "cei_findings": 0,
                        "cei_ir_confirmed": False,
                        "cei_ir_missing": False,
                        "cei_example_functions": [],
                    },
                    errors=[f"clone_or_analysis_failed: {str(exc)[:300]}"],
                )
            )

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    payload = {
        "scan_id": args.scan_id,
        "generated_at": generated_at,
        "git_host": args.git_host,
        "allow_build": args.allow_build,
        "scarb_timeout_seconds": args.scarb_timeout_seconds,
        "detector_findings_jsonl": args.detector_findings_jsonl,
        "repos": [
            {
                "repo": row.repo,
                "ref": row.ref,
                "projects_total": row.projects_total,
                "projects_built": row.projects_built,
                "projects_failed": row.projects_failed,
                "artifacts": row.artifacts,
                "artifact_breakdown": row.artifact_breakdown,
                "marker_counts": row.marker_counts,
                "function_signals": row.function_signals,
                "signal_flags": row.signal_flags,
                "analysis_status": row.analysis_status,
                "confirmation": row.confirmation,
                "errors": row.errors,
                "detector_hits": detector_hits.get(row.repo, 0),
            }
            for row in rows
        ],
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    markdown = render_markdown(
        scan_id=args.scan_id,
        generated_at=generated_at,
        rows=rows,
        detector_hits=detector_hits,
        detector_findings=args.detector_findings_jsonl,
        allow_build=args.allow_build,
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")

    print(
        json.dumps(
            {
                "scan_id": args.scan_id,
                "repos": len(rows),
                "output_json": out_json.as_posix(),
                "output_md": out_md.as_posix(),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
