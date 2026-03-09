#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def _load_config(path: str) -> tuple[dict[str, Any], Path | None]:
    candidates: list[Path] = []
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        candidates.append(p)
    else:
        candidates.append((Path.cwd() / ".starkskills.toml").resolve())
        candidates.append((REPO_ROOT / ".starkskills.toml").resolve())

    for candidate in candidates:
        if candidate.exists():
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"invalid config object in {candidate}")
            return data, candidate
    return {}, None


def _cfg(cfg: dict[str, Any], section: str, key: str, default: Any) -> Any:
    sec = cfg.get(section)
    if isinstance(sec, dict) and key in sec:
        return sec[key]
    defaults = cfg.get("defaults")
    if isinstance(defaults, dict) and key in defaults:
        return defaults[key]
    return default


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: float | None = None,
    input_text: str | None = None,
) -> CommandResult:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        input=input_text,
        timeout=timeout,
        check=False,
    )
    return CommandResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def _extract_last_json(text: str) -> dict[str, Any]:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("no JSON object found in command output")


def _resolve_path(value: str | None, fallback: Path) -> Path:
    if value:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()
    return fallback.resolve()


def _maybe_export_sarif(*, findings_jsonl: str | None, scan_json: str | None, output_path: Path, root: Path, run_name: str) -> Path:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/quality/export_findings_sarif.py"),
        "--output",
        output_path.as_posix(),
        "--root",
        root.as_posix(),
        "--run-name",
        run_name,
    ]
    if findings_jsonl:
        cmd.extend(["--findings-jsonl", findings_jsonl])
    elif scan_json:
        cmd.extend(["--scan-json", scan_json])
    else:
        raise ValueError("sarif export requires findings_jsonl or scan_json")

    result = _run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"sarif export failed: {result.stderr or result.stdout}")
    return output_path


def _print_doctor_report(rows: list[dict[str, Any]], *, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"checks": rows}, ensure_ascii=True))
    else:
        print("starkskills doctor")
        for row in rows:
            status = row["status"]
            name = row["name"]
            detail = row.get("detail", "")
            print(f"- [{status}] {name}: {detail}")
    failures = [row for row in rows if row["status"] == "fail"]
    return 1 if failures else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg, cfg_path = _load_config(args.config)
    rows: list[dict[str, Any]] = []

    rows.append({
        "name": "config",
        "status": "ok",
        "detail": cfg_path.as_posix() if cfg_path else "no config file (using built-in defaults)",
    })

    py_ok = sys.version_info >= (3, 11)
    rows.append({
        "name": "python",
        "status": "ok" if py_ok else "fail",
        "detail": sys.version.split()[0],
    })

    for tool in ("git", "rg", "curl", "gh", "scarb", "snforge", "semgrep"):
        path = shutil.which(tool)
        rows.append({
            "name": tool,
            "status": "ok" if path else "warn",
            "detail": path or "not found",
        })

    token = os.getenv("GITHUB_TOKEN", "")
    rows.append({
        "name": "github_token",
        "status": "ok" if token else "warn",
        "detail": "set" if token else "not set (LLM held-out evals unavailable)",
    })

    if args.probe_models:
        if not token:
            rows.append({
                "name": "github_models_probe",
                "status": "warn",
                "detail": "skipped (GITHUB_TOKEN not set)",
            })
        else:
            cmd = [
                "curl",
                "-sS",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "https://models.github.ai/inference/chat/completions",
                "-H",
                "Content-Type: application/json",
                "-H",
                "@-",
                "-d",
                '{"model":"openai/gpt-4o-mini","messages":[{"role":"user","content":"ping"}],"max_tokens":1}',
            ]
            probe = _run(
                cmd,
                cwd=REPO_ROOT,
                timeout=20,
                input_text=f"Authorization: Bearer {token}\n",
            )
            code = (probe.stdout or "").strip()
            ok_codes = {"200", "201"}
            rows.append({
                "name": "github_models_probe",
                "status": "ok" if code in ok_codes else "warn",
                "detail": f"http={code or 'unknown'}",
            })

    return _print_doctor_report(rows, as_json=args.json)


def _print_next_actions(title: str, actions: list[str]) -> None:
    print(f"\nNext actions ({title}):")
    for i, action in enumerate(actions, start=1):
        print(f"{i}. {action}")


def cmd_audit_local(args: argparse.Namespace) -> int:
    cfg, cfg_path = _load_config(args.config)
    repo_root = _resolve_path(args.repo_root, Path.cwd())
    output_dir_default = repo_root / str(_cfg(cfg, "local", "output_dir", "evals/reports/local"))
    output_dir = _resolve_path(args.output_dir, output_dir_default)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/quality/audit_local_repo.py"),
        "--repo-root",
        repo_root.as_posix(),
        "--scan-id",
        args.scan_id,
        "--output-dir",
        output_dir.as_posix(),
        "--exclude",
        args.exclude or str(_cfg(cfg, "defaults", "exclude", "test,tests,mock,mocks,example,examples,preset,presets,fixture,fixtures,vendor,vendors")),
    ]

    write_jsonl = args.write_findings_jsonl if args.write_findings_jsonl is not None else bool(
        _cfg(cfg, "local", "write_findings_jsonl", True)
    )
    if write_jsonl:
        cmd.append("--write-findings-jsonl")

    sierra = args.sierra if args.sierra is not None else bool(_cfg(cfg, "local", "sierra_confirm", False))
    allow_build = args.allow_build if args.allow_build is not None else bool(_cfg(cfg, "local", "allow_build", False))
    if sierra:
        cmd.append("--sierra-confirm")
        cmd.extend([
            "--scarb-timeout-seconds",
            str(float(_cfg(cfg, "local", "scarb_timeout_seconds", 240))),
        ])
        if allow_build:
            cmd.append("--allow-build")

    if args.fail_on_findings:
        cmd.append("--fail-on-findings")

    result = _run(cmd, cwd=REPO_ROOT, timeout=float(_cfg(cfg, "defaults", "scan_timeout_seconds", 1200)))
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)

    if result.returncode not in {0, 2}:
        return result.returncode

    try:
        payload = _extract_last_json(result.stdout)
    except ValueError as exc:
        tail = result.stdout[-2000:] if result.stdout else ""
        print(
            f"ERROR: could not parse JSON summary from local audit output: {exc}",
            file=sys.stderr,
        )
        if tail:
            print(f"---- stdout tail ----\n{tail}", file=sys.stderr)
        return 1
    sarif_path: Path | None = None
    if args.format in {"sarif", "both"}:
        out_json = Path(str(payload.get("output_json", "")))
        findings_jsonl = payload.get("output_findings_jsonl")
        default_sarif = out_json.with_suffix(".sarif.json") if out_json.name else (output_dir / f"{args.scan_id}.sarif.json")
        sarif_out = _resolve_path(args.sarif_output, default_sarif)
        sarif_path = _maybe_export_sarif(
            findings_jsonl=str(findings_jsonl) if findings_jsonl else None,
            scan_json=out_json.as_posix() if out_json else None,
            output_path=sarif_out,
            root=repo_root,
            run_name=f"starkskills-local-{args.scan_id}",
        )
        print(json.dumps({"sarif_output": sarif_path.as_posix()}, ensure_ascii=True))

    actions = [
        f"Open markdown report: {payload.get('output_md')}",
        f"Open JSON report: {payload.get('output_json')}",
    ]
    if payload.get("output_findings_jsonl"):
        actions.append(f"Review findings JSONL: {payload.get('output_findings_jsonl')}")
    if sarif_path is not None:
        actions.append(f"Upload SARIF to GitHub Code Scanning: {sarif_path.as_posix()}")
    if not sierra:
        actions.append("Re-run with Sierra confirmation for deeper validation: starkskills audit local --sierra --allow-build")
    _print_next_actions("local", actions)

    return result.returncode


def _run_pack_backend(args: argparse.Namespace, *, force_stage2: bool | None) -> tuple[int, dict[str, Any]]:
    cfg, cfg_path = _load_config(args.config)
    output_dir = _resolve_path(args.output_dir, REPO_ROOT / str(_cfg(cfg, "defaults", "output_dir", "evals/reports/data")))
    default_workdir = Path(tempfile.gettempdir()) / "starknet-skills-external-scan"
    workdir = _resolve_path(
        args.workdir,
        Path(str(_cfg(cfg, "defaults", "workdir", default_workdir.as_posix()))),
    )

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/quality/audit_external_pack.py"),
        "--pack",
        args.pack,
        "--scan-id",
        args.scan_id,
        "--output-dir",
        output_dir.as_posix(),
        "--workdir",
        workdir.as_posix(),
        "--exclude",
        args.exclude or str(_cfg(cfg, "defaults", "exclude", "test,tests,mock,mocks,example,examples,preset,presets,fixture,fixtures,vendor,vendors")),
        "--scan-timeout-seconds",
        str(float(_cfg(cfg, "defaults", "scan_timeout_seconds", 1200))),
        "--bundle-max-files",
        str(int(_cfg(cfg, "defaults", "bundle_max_files", 150))),
        "--bundle-max-bytes",
        str(int(_cfg(cfg, "defaults", "bundle_max_bytes", 800000))),
    ]

    if args.repos_file:
        cmd.extend(["--repos-file", args.repos_file])
    elif args.repos:
        cmd.extend(["--repos", *args.repos])

    if args.detectors:
        cmd.extend(["--detectors", args.detectors])
    if args.git_host:
        cmd.extend(["--git-host", args.git_host])

    if args.manual_triage_id_prefix:
        cmd.extend(["--manual-triage-id-prefix", args.manual_triage_id_prefix])

    if force_stage2 is True:
        cmd.append("--prepare-stage2")
    elif force_stage2 is False:
        cmd.append("--no-prepare-stage2")
    else:
        prepare_stage2 = bool(_cfg(cfg, "external", "prepare_stage2", False))
        cmd.append("--prepare-stage2" if prepare_stage2 else "--no-prepare-stage2")

    result = _run(cmd, cwd=REPO_ROOT, timeout=float(_cfg(cfg, "defaults", "scan_timeout_seconds", 1200)) + 60)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        return result.returncode, {}
    try:
        payload = _extract_last_json(result.stdout)
    except ValueError as exc:
        tail = result.stdout[-2000:] if result.stdout else ""
        print(
            f"ERROR: could not parse JSON summary from external audit output: {exc}",
            file=sys.stderr,
        )
        if tail:
            print(f"---- stdout tail ----\n{tail}", file=sys.stderr)
        return 1, {}
    return 0, payload


def _external_common(args: argparse.Namespace, *, deep_mode: bool) -> int:
    code, payload = _run_pack_backend(args, force_stage2=True if deep_mode else args.prepare_stage2)
    if code != 0:
        return code

    sarif_path: Path | None = None
    if args.format in {"sarif", "both"}:
        findings_jsonl = payload.get("findings_jsonl")
        base_json = Path(str(payload.get("json", "")))
        default_sarif = base_json.with_suffix(".sarif.json") if base_json.name else (Path.cwd() / f"{args.scan_id}.sarif.json")
        sarif_out = _resolve_path(args.sarif_output, default_sarif)
        sarif_path = _maybe_export_sarif(
            findings_jsonl=str(findings_jsonl) if findings_jsonl else None,
            scan_json=base_json.as_posix() if base_json else None,
            output_path=sarif_out,
            root=Path.cwd(),
            run_name=f"starkskills-external-{args.scan_id}",
        )
        print(json.dumps({"sarif_output": sarif_path.as_posix()}, ensure_ascii=True))

    title = "deep" if deep_mode else "external"
    actions = [
        f"Open markdown report: {payload.get('markdown')}",
        f"Manual triage sheet: {payload.get('manual_triage_csv')}",
        f"Repo summary CSV: {payload.get('repo_summary_csv')}",
    ]
    if payload.get("stage2_runbook_md"):
        actions.append(f"Use Stage-2 runbook for vector-specialist deep pass: {payload.get('stage2_runbook_md')}")
    if sarif_path is not None:
        actions.append(f"Upload SARIF to GitHub Code Scanning: {sarif_path.as_posix()}")
    actions.append("After manual labeling, score triage with: python scripts/quality/score_external_triage.py ...")
    _print_next_actions(title, actions)
    return 0


def cmd_audit_external(args: argparse.Namespace) -> int:
    return _external_common(args, deep_mode=False)


def cmd_audit_deep(args: argparse.Namespace) -> int:
    return _external_common(args, deep_mode=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="starkskills",
        description="Unified CLI for starknet-skills auditing workflows.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check local toolchain and optional GitHub Models readiness.")
    doctor.add_argument("--config", default="", help="Path to .starkskills.toml config.")
    doctor.add_argument("--probe-models", action="store_true", help="Probe GitHub Models endpoint if GITHUB_TOKEN is set.")
    doctor.add_argument("--json", action="store_true", help="Emit doctor report as JSON.")
    doctor.set_defaults(func=cmd_doctor)

    audit = sub.add_parser("audit", help="Run local/external/deep audits.")
    audit_sub = audit.add_subparsers(dest="audit_mode", required=True)

    local = audit_sub.add_parser("local", help="Run deterministic audit on a local Cairo repo.")
    local.add_argument("--config", default="", help="Path to .starkskills.toml config.")
    local.add_argument("--repo-root", default=".")
    local.add_argument("--scan-id", default="local-audit")
    local.add_argument("--exclude", default="")
    local.add_argument("--output-dir", default="")
    local.add_argument("--sierra", action=argparse.BooleanOptionalAction, default=None)
    local.add_argument("--allow-build", action=argparse.BooleanOptionalAction, default=None)
    local.add_argument("--write-findings-jsonl", action=argparse.BooleanOptionalAction, default=None)
    local.add_argument("--fail-on-findings", action="store_true")
    local.add_argument("--format", choices=["text", "sarif", "both"], default="text")
    local.add_argument("--sarif-output", default="")
    local.set_defaults(func=cmd_audit_local)

    for mode in ("external", "deep"):
        p = audit_sub.add_parser(mode, help=f"Run {mode} external benchmark pack workflow.")
        p.add_argument("--config", default="", help="Path to .starkskills.toml config.")
        p.add_argument("--pack", default="less-known", choices=["less-known", "low-profile", "wave2"])
        p.add_argument("--repos-file", default="")
        p.add_argument("--repos", nargs="*", default=[])
        p.add_argument("--scan-id", default=f"{mode}-audit")
        p.add_argument("--output-dir", default="")
        p.add_argument("--workdir", default="")
        p.add_argument("--exclude", default="")
        p.add_argument("--detectors", default="")
        p.add_argument("--git-host", default="")
        p.add_argument("--manual-triage-id-prefix", default="")
        p.add_argument("--prepare-stage2", action=argparse.BooleanOptionalAction, default=None)
        p.add_argument("--format", choices=["text", "sarif", "both"], default="text")
        p.add_argument("--sarif-output", default="")

    audit_sub.choices["external"].set_defaults(func=cmd_audit_external)
    audit_sub.choices["deep"].set_defaults(func=cmd_audit_deep)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
