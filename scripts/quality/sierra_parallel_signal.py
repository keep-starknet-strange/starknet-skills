#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scan_external_repos import RepoSpec, clone_repo, parse_repo_spec


@dataclass
class RepoSignal:
    repo: str
    ref: str
    projects_total: int
    projects_built: int
    projects_failed: int
    artifacts: int
    marker_counts: dict[str, int]
    signal_flags: dict[str, bool]
    errors: list[str]


MARKERS: dict[str, tuple[str, ...]] = {
    "external_call": ("call_contract_syscall", "library_call", "replace_class_syscall"),
    "state_write": ("storage_write_syscall",),
    "state_read": ("storage_read_syscall",),
    "event_emit": ("emit_event_syscall",),
}


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
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


def count_markers_in_file(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    counts: dict[str, int] = {}
    for key, needles in MARKERS.items():
        counts[key] = sum(text.count(needle.lower()) for needle in needles)
    return counts


def collect_sierra_artifacts(project_root: Path) -> list[Path]:
    target = project_root / "target"
    if not target.exists():
        return []
    artifacts: list[Path] = []
    for pattern in ("**/*.sierra.json", "**/*.sierra"):
        artifacts.extend(target.glob(pattern))
    return sorted({p.resolve() for p in artifacts if p.is_file()})


def analyze_repo(spec: RepoSpec, repo_dir: Path, ref: str) -> RepoSignal:
    scarb_projects = find_scarb_projects(repo_dir)
    marker_counts: Counter[str] = Counter()
    errors: list[str] = []
    projects_built = 0
    projects_failed = 0
    artifact_count = 0

    for project in scarb_projects:
        proc = run(["scarb", "build"], cwd=project)
        if proc.returncode != 0:
            projects_failed += 1
            msg = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "scarb build failed"
            errors.append(f"{project.relative_to(repo_dir).as_posix()}: {msg[:280]}")
            continue
        projects_built += 1
        artifacts = collect_sierra_artifacts(project)
        artifact_count += len(artifacts)
        for artifact in artifacts:
            counts = count_markers_in_file(artifact)
            marker_counts.update(counts)

    flags = {
        "has_external_call_markers": marker_counts["external_call"] > 0,
        "has_state_write_markers": marker_counts["state_write"] > 0,
        "has_upgrade_markers": marker_counts["external_call"] > 0 and marker_counts["external_call"] >= marker_counts["state_read"],
        "cei_parallel_signal": marker_counts["external_call"] > 0 and marker_counts["state_write"] > 0,
    }

    return RepoSignal(
        repo=spec.slug,
        ref=ref,
        projects_total=len(scarb_projects),
        projects_built=projects_built,
        projects_failed=projects_failed,
        artifacts=artifact_count,
        marker_counts=dict(marker_counts),
        signal_flags=flags,
        errors=errors,
    )


def load_detector_hits(path: Path) -> dict[str, int]:
    per_repo: dict[str, int] = defaultdict(int)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        repo = str(row.get("repo", ""))
        if repo:
            per_repo[repo] += 1
    return dict(per_repo)


def render_markdown(
    *,
    scan_id: str,
    generated_at: str,
    rows: list[RepoSignal],
    detector_hits: dict[str, int],
    detector_findings: str,
) -> str:
    lines: list[str] = []
    lines.append(f"# Sierra Parallel Signal ({scan_id})")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    if detector_findings:
        lines.append(f"Detector findings compared: `{detector_findings}`")
    lines.append("")
    lines.append("| Repo | Projects (built/total) | Artifacts | External | StateWrite | CEI Signal | Detector Hits |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- | ---: |")
    for row in rows:
        ext = row.marker_counts.get("external_call", 0)
        sw = row.marker_counts.get("state_write", 0)
        cei = "yes" if row.signal_flags.get("cei_parallel_signal", False) else "no"
        hits = detector_hits.get(row.repo, 0)
        lines.append(
            f"| `{row.repo}` | {row.projects_built}/{row.projects_total} | {row.artifacts} | {ext} | {sw} | {cei} | {hits} |"
        )
    lines.append("")
    errors = [(row.repo, err) for row in rows for err in row.errors]
    if errors:
        lines.append("## Build Errors")
        lines.append("")
        for repo, err in errors:
            lines.append(f"- `{repo}`: {err}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Sierra-native parallel signals across external repos.")
    parser.add_argument("--scan-id", required=True)
    parser.add_argument("--repos", nargs="*", default=[])
    parser.add_argument("--repos-file", default="")
    parser.add_argument("--workdir", default="/tmp/starknet-skills-sierra-scan")
    parser.add_argument("--detector-findings-jsonl", default="")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
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

    rows: list[RepoSignal] = []
    for spec in repo_specs:
        try:
            repo_dir, ref = clone_repo(spec, workdir)
            rows.append(analyze_repo(spec, repo_dir, ref))
        except Exception as exc:
            rows.append(
                RepoSignal(
                    repo=spec.slug,
                    ref=spec.ref or "",
                    projects_total=0,
                    projects_built=0,
                    projects_failed=0,
                    artifacts=0,
                    marker_counts={},
                    signal_flags={
                        "has_external_call_markers": False,
                        "has_state_write_markers": False,
                        "has_upgrade_markers": False,
                        "cei_parallel_signal": False,
                    },
                    errors=[f"clone_or_analysis_failed: {str(exc)[:300]}"],
                )
            )

    detector_hits: dict[str, int] = {}
    if args.detector_findings_jsonl:
        detector_hits = load_detector_hits(Path(args.detector_findings_jsonl))

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    payload = {
        "scan_id": args.scan_id,
        "generated_at": generated_at,
        "detector_findings_jsonl": args.detector_findings_jsonl,
        "repos": [
            {
                "repo": row.repo,
                "ref": row.ref,
                "projects_total": row.projects_total,
                "projects_built": row.projects_built,
                "projects_failed": row.projects_failed,
                "artifacts": row.artifacts,
                "marker_counts": row.marker_counts,
                "signal_flags": row.signal_flags,
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
