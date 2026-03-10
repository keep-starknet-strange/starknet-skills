#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for Python 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover - handled on first config parse
        tomllib = None  # type: ignore[assignment]

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
        if not p.exists():
            raise FileNotFoundError(f"config file not found: {p.as_posix()}")
        if not p.is_file():
            raise ValueError(f"config path must be a file: {p.as_posix()}")
        candidates.append(p)
    else:
        candidates.append((Path.cwd() / ".starkskills.toml").resolve())
        candidates.append((REPO_ROOT / ".starkskills.toml").resolve())

    for candidate in candidates:
        if candidate.exists():
            if tomllib is None:
                raise RuntimeError(
                    "TOML parsing requires Python 3.11+ or the 'tomli' package on Python 3.10."
                )
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
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            input=input_text,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        cmd_preview = " ".join(cmd)
        raise RuntimeError(
            f"command timed out after {timeout}s in {cwd.as_posix()}: {cmd_preview}"
        ) from exc
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


def _safe_ref_token(ref: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", ref.strip())
    cleaned = cleaned.strip("._-")
    return cleaned[:40] if cleaned else "ref"


def _remap_external_findings_for_sarif(*, findings_jsonl: str, workdir: Path, output_path: Path) -> Path:
    src = Path(findings_jsonl)
    if not src.is_file():
        raise FileNotFoundError(f"findings jsonl not found: {src.as_posix()}")
    workdir_resolved = workdir.resolve()

    out_path = output_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    parsed_rows: list[dict[str, Any]] = []
    refs_by_repo: dict[str, set[str]] = {}

    for line_no, line in enumerate(src.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{src.as_posix()}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"{src.as_posix()}:{line_no}: expected JSON object")
        parsed_rows.append(raw)
        repo = str(raw.get("repo", "")).strip()
        ref = str(raw.get("ref", "")).strip()
        if repo:
            refs_by_repo.setdefault(repo, set()).add(ref)

    remapped_lines: list[str] = []
    for raw in parsed_rows:
        repo = str(raw.get("repo", "")).strip()
        file_value = str(raw.get("file", "")).strip()
        if repo and file_value and not Path(file_value).is_absolute():
            clone_dir_override = str(raw.get("clone_dir", "")).strip()
            rel_repo_dir = ""
            if clone_dir_override:
                clone_dir_path = Path(clone_dir_override)
                if not clone_dir_path.is_absolute():
                    clone_dir_path = (workdir_resolved / clone_dir_path).resolve()
                try:
                    rel_repo_dir = clone_dir_path.relative_to(workdir_resolved).as_posix()
                except ValueError:
                    rel_repo_dir = clone_dir_path.name
            else:
                repo_token = repo.replace("/", "__")
                ref = str(raw.get("ref", "")).strip()
                repo_refs = {item for item in refs_by_repo.get(repo, set()) if item}
                has_multi_ref = len(repo_refs) > 1
                candidate_dirs: list[Path] = []
                if ref:
                    ref_token = _safe_ref_token(ref)
                    candidate_dirs.append((workdir_resolved / f"{repo_token}__{ref_token}").resolve())
                    candidate_dirs.append((workdir_resolved / f"{repo_token}@{ref_token}").resolve())
                if not (has_multi_ref and ref):
                    candidate_dirs.append((workdir_resolved / repo_token).resolve())

                resolved_dir: Path | None = None
                for candidate in candidate_dirs:
                    if candidate.exists():
                        resolved_dir = candidate
                        break

                if resolved_dir is not None:
                    try:
                        rel_repo_dir = resolved_dir.relative_to(workdir_resolved).as_posix()
                    except ValueError:
                        rel_repo_dir = resolved_dir.name
                elif has_multi_ref and ref:
                    rel_repo_dir = f"{repo_token}__{_safe_ref_token(ref)}"
                else:
                    rel_repo_dir = repo_token

            mapped = (Path(rel_repo_dir) / file_value).as_posix()
            raw["file"] = mapped
        remapped_lines.append(json.dumps(raw, ensure_ascii=True))

    out_path.write_text("\n".join(remapped_lines) + ("\n" if remapped_lines else ""), encoding="utf-8")
    return out_path


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
    try:
        cfg, cfg_path = _load_config(args.config)
    except Exception as exc:
        print(f"ERROR: failed to load config: {exc}", file=sys.stderr)
        return 1
    rows: list[dict[str, Any]] = []

    rows.append({
        "name": "config",
        "status": "ok",
        "detail": cfg_path.as_posix() if cfg_path else "no config file (using built-in defaults)",
    })

    py_ok = sys.version_info >= (3, 11) or (
        sys.version_info >= (3, 10) and tomllib is not None
    )
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
        default_probe_url = "https://models.github.ai/inference/chat/completions"
        probe_url = str(
            os.environ.get("STARKSKILLS_MODELS_PROBE_URL")
            or _cfg(cfg, "defaults", "models_probe_url", default_probe_url)
        )
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
                os.devnull,
                "-w",
                "%{http_code}",
                probe_url,
                "-H",
                "Content-Type: application/json",
                "-H",
                "@-",
                "-d",
                '{"model":"openai/gpt-4o-mini","messages":[{"role":"user","content":"ping"}],"max_tokens":1}',
            ]
            try:
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
            except RuntimeError as exc:
                rows.append({
                    "name": "github_models_probe",
                    "status": "warn",
                    "detail": str(exc),
                })

    return _print_doctor_report(rows, as_json=args.json)


def _print_next_actions(title: str, actions: list[str]) -> None:
    print(f"\nNext actions ({title}):")
    for i, action in enumerate(actions, start=1):
        print(f"{i}. {action}")


def cmd_audit_local(args: argparse.Namespace) -> int:
    try:
        cfg, cfg_path = _load_config(args.config)
    except Exception as exc:
        print(f"ERROR: failed to load config: {exc}", file=sys.stderr)
        return 1
    repo_root = _resolve_path(args.repo_root, Path.cwd())
    output_dir_default = repo_root / str(_cfg(cfg, "local", "output_dir", "evals/reports/local"))
    output_dir = _resolve_path(args.output_dir, output_dir_default)
    e2e_timeout_raw = (
        args.e2e_timeout_seconds
        if args.e2e_timeout_seconds is not None
        else _cfg(cfg, "local", "e2e_timeout_seconds", None)
    )
    e2e_timeout = float(e2e_timeout_raw) if e2e_timeout_raw not in (None, "") else None

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

    try:
        result = _run(
            cmd,
            cwd=REPO_ROOT,
            timeout=e2e_timeout,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
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
        try:
            out_json = Path(str(payload.get("output_json", "")))
            findings_jsonl = payload.get("output_findings_jsonl")
            default_sarif = (
                out_json.with_suffix(".sarif.json")
                if out_json.name
                else (output_dir / f"{args.scan_id}.sarif.json")
            )
            sarif_out = _resolve_path(args.sarif_output, default_sarif)
            sarif_path = _maybe_export_sarif(
                findings_jsonl=str(findings_jsonl) if findings_jsonl else None,
                scan_json=out_json.as_posix() if out_json else None,
                output_path=sarif_out,
                root=repo_root,
                run_name=f"starkskills-local-{args.scan_id}",
            )
            print(json.dumps({"sarif_output": sarif_path.as_posix()}, ensure_ascii=True))
        except Exception as exc:
            print(f"ERROR: SARIF export failed in _maybe_export_sarif: {exc}", file=sys.stderr)
            return 1

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
    try:
        cfg, cfg_path = _load_config(args.config)
    except Exception as exc:
        print(f"ERROR: failed to load config: {exc}", file=sys.stderr)
        return 1, {}
    output_dir = _resolve_path(args.output_dir, REPO_ROOT / str(_cfg(cfg, "defaults", "output_dir", "evals/reports/data")))
    default_workdir = Path(tempfile.gettempdir()) / "starknet-skills-external-scan"
    workdir = _resolve_path(
        args.workdir,
        Path(str(_cfg(cfg, "defaults", "workdir", default_workdir.as_posix()))),
    )
    scan_timeout_seconds = float(
        args.scan_timeout_seconds
        if args.scan_timeout_seconds is not None
        else _cfg(cfg, "defaults", "scan_timeout_seconds", 1200)
    )
    bundle_max_files = int(
        args.bundle_max_files
        if args.bundle_max_files is not None
        else _cfg(cfg, "defaults", "bundle_max_files", 150)
    )
    bundle_max_bytes = int(
        args.bundle_max_bytes
        if args.bundle_max_bytes is not None
        else _cfg(cfg, "defaults", "bundle_max_bytes", 800000)
    )
    bundle_max_chars = int(
        args.bundle_max_chars
        if args.bundle_max_chars is not None
        else _cfg(cfg, "defaults", "bundle_max_chars", 900000)
    )
    e2e_timeout_raw = (
        args.e2e_timeout_seconds
        if args.e2e_timeout_seconds is not None
        else _cfg(cfg, "defaults", "e2e_timeout_seconds", None)
    )
    e2e_timeout = float(e2e_timeout_raw) if e2e_timeout_raw not in (None, "") else None

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
        str(scan_timeout_seconds),
        "--bundle-max-files",
        str(bundle_max_files),
        "--bundle-max-bytes",
        str(bundle_max_bytes),
        "--bundle-max-chars",
        str(bundle_max_chars),
    ]

    if args.repos_file:
        repos_file = _resolve_path(args.repos_file, Path.cwd())
        cmd.extend(["--repos-file", repos_file.as_posix()])
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
        prepare_stage2 = _cfg(cfg, "external", "prepare_stage2", None)
        if prepare_stage2 is True:
            cmd.append("--prepare-stage2")
        elif prepare_stage2 is False:
            cmd.append("--no-prepare-stage2")

    try:
        result = _run(
            cmd,
            cwd=REPO_ROOT,
            timeout=e2e_timeout,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1, {}
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
    payload["_resolved_workdir"] = workdir.as_posix()
    return 0, payload


def _external_common(args: argparse.Namespace, *, deep_mode: bool) -> int:
    force_stage2 = args.prepare_stage2
    if deep_mode and force_stage2 is None:
        force_stage2 = True
    code, payload = _run_pack_backend(args, force_stage2=force_stage2)
    if code != 0:
        return code

    sarif_path: Path | None = None
    if args.format in {"sarif", "both"}:
        try:
            findings_jsonl = payload.get("findings_jsonl")
            base_json = Path(str(payload.get("json", "")))
            default_sarif = (
                base_json.with_suffix(".sarif.json")
                if base_json.name
                else (Path.cwd() / f"{args.scan_id}.sarif.json")
            )
            sarif_out = _resolve_path(args.sarif_output, default_sarif)
            sarif_findings_jsonl = str(findings_jsonl) if findings_jsonl else None
            sarif_root = Path.cwd()
            resolved_workdir = str(payload.get("_resolved_workdir", "")).strip()
            if sarif_findings_jsonl and resolved_workdir:
                workdir_path = Path(resolved_workdir).resolve()
                with tempfile.TemporaryDirectory(prefix="starkskills-sarif-remap-") as temp_dir:
                    remapped_findings = _remap_external_findings_for_sarif(
                        findings_jsonl=sarif_findings_jsonl,
                        workdir=workdir_path,
                        output_path=Path(temp_dir) / Path(sarif_findings_jsonl).name,
                    )
                    sarif_path = _maybe_export_sarif(
                        findings_jsonl=remapped_findings.as_posix(),
                        scan_json=base_json.as_posix() if base_json else None,
                        output_path=sarif_out,
                        root=workdir_path,
                        run_name=f"starkskills-external-{args.scan_id}",
                    )
            else:
                sarif_path = _maybe_export_sarif(
                    findings_jsonl=sarif_findings_jsonl,
                    scan_json=base_json.as_posix() if base_json else None,
                    output_path=sarif_out,
                    root=sarif_root,
                    run_name=f"starkskills-external-{args.scan_id}",
                )
            print(json.dumps({"sarif_output": sarif_path.as_posix()}, ensure_ascii=True))
        except Exception as exc:
            print(f"ERROR: SARIF export failed in _external_common: {exc}", file=sys.stderr)
            return 1

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
    local.add_argument(
        "--e2e-timeout-seconds",
        type=float,
        default=None,
        help="Optional end-to-end timeout for the local audit wrapper subprocess.",
    )
    local.set_defaults(func=cmd_audit_local)

    for mode in ("external", "deep"):
        p = audit_sub.add_parser(mode, help=f"Run {mode} external benchmark pack workflow.")
        p.add_argument("--config", default="", help="Path to .starkskills.toml config.")
        p.add_argument(
            "--pack",
            default="less-known",
            choices=["less-known", "low-profile", "wave2", "issue32"],
        )
        p.add_argument("--repos-file", default="")
        p.add_argument("--repos", nargs="*", default=[])
        p.add_argument("--scan-id", default="")
        p.add_argument("--output-dir", default="")
        p.add_argument("--workdir", default="")
        p.add_argument("--exclude", default="")
        p.add_argument("--detectors", default="")
        p.add_argument("--git-host", default="")
        p.add_argument("--manual-triage-id-prefix", default="")
        p.add_argument(
            "--scan-timeout-seconds",
            type=float,
            default=None,
            help="Stage-1 backend scan timeout in seconds.",
        )
        p.add_argument(
            "--e2e-timeout-seconds",
            type=float,
            default=None,
            help="Optional end-to-end timeout for the wrapper subprocess.",
        )
        p.add_argument(
            "--bundle-max-files",
            type=int,
            default=None,
            help="Max production Cairo files embedded per Stage-2 bundle.",
        )
        p.add_argument(
            "--bundle-max-bytes",
            type=int,
            default=None,
            help="Max cumulative source bytes embedded per Stage-2 bundle.",
        )
        p.add_argument(
            "--bundle-max-chars",
            type=int,
            default=None,
            help="Max cumulative source characters embedded per Stage-2 bundle.",
        )
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
