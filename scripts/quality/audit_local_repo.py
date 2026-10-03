#!/usr/bin/env python3
"""Local repo integration for Sierra v3 signal quality audit.

Takes a local Starknet project, attempts builds with different profiles,
collects artifacts, and runs the Sierra signal quality analysis.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from sierra_parallel_signal import (
    ArtifactInfo,
    IRConfirmation,
    RepoAnalysis,
    SignalQuality,
    analyze_repo,
    build_finding_report,
    compute_signal_quality,
    infer_profile_from_artifact,
)


class BuildResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class BuildAttempt:
    profile: str
    result: BuildResult
    artifacts: list[ArtifactInfo] = field(default_factory=list)
    error: str = ""
    toolchain_version: str = ""


def run_scarb_build(project_dir: str, profile: str) -> BuildAttempt:
    """Run scarb build with given profile, collecting artifacts."""
    attempt = BuildAttempt(profile=profile, result=BuildResult.SKIPPED)
    cmd = [
        "scarb", "build",
        "--profile", profile,
        "--force",
    ]
    try:
        env = os.environ.copy()
        env["SCARB_LOG"] = "debug"
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        if result.returncode != 0:
            attempt.result = BuildResult.FAILURE
            attempt.error = result.stderr[-500:] if result.stderr else "build failed"
            return attempt

        attempt.result = BuildResult.SUCCESS

        # Collect artifacts
        target_dir = Path(project_dir) / "target" / profile
        if not target_dir.exists():
            target_dir = Path(project_dir) / "target" / "release"

        for artifact_file in target_dir.rglob("*"):
            if artifact_file.is_file():
                name = artifact_file.name
                sierra_json = ".sierra.json" in name or name.endswith("sierra.json")
                starknet_artifacts = ".starknet_artifacts.json" in name or name.endswith("starknet_artifacts.json")
                contract_class = ".contract_class.json" in name or name.endswith("contract_class.json")

                if sierra_json or starknet_artifacts or contract_class:
                    artifact_type = (
                        "sierra_json" if sierra_json
                        else "starknet_artifacts" if starknet_artifacts
                        else "contract_class"
                    )
                    attempt.artifacts.append(ArtifactInfo(
                        artifact_type=artifact_type,
                        path=str(artifact_file),
                        has_function_order=sierra_json,
                        profile=profile,
                    ))

    except subprocess.TimeoutExpired:
        attempt.result = BuildResult.FAILURE
        attempt.error = "timeout"
    except FileNotFoundError:
        attempt.result = BuildResult.SKIPPED
        attempt.error = "scarb not found"
    except Exception as e:
        attempt.result = BuildResult.FAILURE
        attempt.error = str(e)

    return attempt


def build_with_profile_matrix(project_dir: str) -> list[BuildAttempt]:
    """Try building with dev then release profile."""
    attempts = []
    for profile in ["dev", "release"]:
        print(f"  Building with profile: {profile}...")
        attempt = run_scarb_build(project_dir, profile)
        attempts.append(attempt)
        if attempt.result == BuildResult.SUCCESS and attempt.artifacts:
            print(f"  ✓ {profile} produced {len(attempt.artifacts)} analyzable artifacts")
            break  # stop on first successful build with artifacts
    return attempts


def infer_toolchain_version(project_dir: str) -> str:
    """Infer toolchain version from Scarb.toml or scarb --version."""
    scarb_toml = Path(project_dir) / "Scarb.toml"
    if scarb_toml.exists():
        content = scarb_toml.read_text()
        for line in content.splitlines():
            if line.startswith("version = "):
                return line.split("=")[1].strip().strip('"')
    try:
        result = subprocess.run(["scarb", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def audit_local_repo(
    project_dir: str,
    findings_input: str | None = None,
    output_md: str | None = None,
    output_json: str | None = None,
) -> RepoAnalysis:
    """Main entry: build, collect artifacts, analyze signal quality."""
    print(f"Auditing local repo: {project_dir}")
    toolchain = infer_toolchain_version(project_dir)
    print(f"  Toolchain: {toolchain}")

    attempts = build_with_profile_matrix(project_dir)
    all_artifacts: list[ArtifactInfo] = []
    successful_profile = ""
    for attempt in attempts:
        all_artifacts.extend(attempt.artifacts)
        if attempt.result == BuildResult.SUCCESS and not successful_profile:
            successful_profile = attempt.profile

    if not all_artifacts:
        print("  ⚠ No analyzable artifacts found")

    quality, confirmation = compute_signal_quality(all_artifacts)
    print(f"  Signal quality: {quality.value}")
    print(f"  IR confirmation: {confirmation.value}")

    analysis = RepoAnalysis(
        repo_url=project_dir,
        quality=quality,
        ir_confirmation=confirmation,
        artifacts=all_artifacts,
        build_profile=successful_profile,
        toolchain_version=toolchain,
    )

    # If findings provided, also produce per-finding report
    if findings_input:
        with open(findings_input) as f:
            data = json.load(f)
        findings = data.get("findings", [])
        rows = build_finding_report([analysis], findings)

        if output_md:
            from sierra_parallel_signal import write_markdown_report
            write_markdown_report(rows, output_md)
        if output_json:
            from sierra_parallel_signal import write_json_report
            write_json_report(rows, output_json)

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Local Sierra v3 audit")
    parser.add_argument("project_dir", help="Path to Starknet project directory")
    parser.add_argument("--findings", default=None, help="Input findings JSON")
    parser.add_argument("--output-md", default=None, help="Output markdown report")
    parser.add_argument("--output-json", default=None, help="Output JSON report")
    args = parser.parse_args()

    audit_local_repo(
        args.project_dir,
        findings_input=args.findings,
        output_md=args.output_md,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
