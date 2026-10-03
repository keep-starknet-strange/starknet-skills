#!/usr/bin/env python3
"""Sierra parallel signal quality analysis script.

Produces per-repo and per-finding IR confirmation status with signal-quality tiers.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import requests


class SignalQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IRConfirmation(str, Enum):
    CONFIRMED = "confirmed"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass
class ArtifactInfo:
    artifact_type: str
    path: str
    has_function_order: bool = False
    profile: str = ""
    toolchain: str = ""


@dataclass
class RepoAnalysis:
    repo_url: str
    quality: SignalQuality = SignalQuality.LOW
    ir_confirmation: IRConfirmation = IRConfirmation.UNKNOWN
    artifacts: list[ArtifactInfo] = field(default_factory=list)
    findings: dict[str, dict[str, Any]] = field(default_factory=dict)
    build_profile: str = ""
    toolchain_version: str = ""


def fetch_artifacts(gh_url: str, token: str | None = None) -> list[dict]:
    """Fetch artifacts from GitHub run."""
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
        headers["Accept"] = "application/vnd.github.v3+json"

    runs_url = f"{gh_url}/runs"
    runs = requests.get(runs_url, headers=headers, timeout=30).json()

    artifacts = []
    for run in runs.get("workflow_runs", []) or runs.get("runs", []):
        run_id = run.get("id")
        if not run_id:
            continue
        resp = requests.get(
            f"{gh_url}/runs/{run_id}/artifacts", headers=headers, timeout=30
        )
        for a in resp.json().get("artifacts", []) or []:
            a["run_id"] = run_id
            artifacts.append(a)
    return artifacts


def classify_artifact(artifact: dict) -> ArtifactInfo | None:
    """Classify an artifact by type and analyzability."""
    name = artifact.get("name", "")
    url = artifact.get("archive_download_url", "")

    sierra_json = ".sierra.json" in name or name.endswith("sierra.json")
    starknet_artifacts = ".starknet_artifacts.json" in name or name.endswith("starknet_artifacts.json")
    contract_class = ".contract_class.json" in name or name.endswith("contract_class.json")

    if not (sierra_json or starknet_artifacts or contract_class):
        return None

    artifact_type = "sierra_json" if sierra_json else ("starknet_artifacts" if starknet_artifacts else "contract_class")

    return ArtifactInfo(
        artifact_type=artifact_type,
        path=url,
        has_function_order=sierra_json,
    )


def compute_signal_quality(artifacts: list[ArtifactInfo]) -> tuple[SignalQuality, IRConfirmation]:
    """Compute signal quality and IR confirmation from artifacts."""
    if not artifacts:
        return SignalQuality.LOW, IRConfirmation.MISSING

    has_sierra = any(a.artifact_type == "sierra_json" for a in artifacts)
    has_markers = any(a.artifact_type in ("contract_class", "starknet_artifacts") for a in artifacts)

    if has_sierra:
        return SignalQuality.HIGH, IRConfirmation.CONFIRMED
    elif has_markers:
        return SignalQuality.MEDIUM, IRConfirmation.CONFIRMED
    else:
        return SignalQuality.LOW, IRConfirmation.MISSING


def infer_profile_from_artifact(name: str) -> str:
    """Infer Scarb profile from artifact name."""
    if "release" in name.lower():
        return "release"
    if "dev" in name.lower():
        return "dev"
    return "dev"  # default


def build_profile_matrix(repo_url: str, token: str | None = None) -> list[str]:
    """Return ordered list of profiles to attempt when building."""
    return ["dev", "release"]


def enrich_artifacts_with_profile(artifacts: list[ArtifactInfo]) -> list[ArtifactInfo]:
    """Attach inferred profile and toolchain info to each artifact."""
    for a in artifacts:
        if not a.profile:
            a.profile = "dev"  # default; real pipeline sets this per build attempt
    return artifacts


def analyze_repo(gh_url: str, token: str | None = None) -> RepoAnalysis:
    """Analyze a single repository's Sierra signal quality."""
    analysis = RepoAnalysis(repo_url=gh_url)
    try:
        artifacts = fetch_artifacts(gh_url, token)
    except Exception as e:
        print(f"  [warn] Failed to fetch artifacts for {gh_url}: {e}", file=sys.stderr)
        return analysis

    classified = []
    for art in artifacts:
        info = classify_artifact(art)
        if info:
            info.profile = infer_profile_from_artifact(art.get("name", ""))
            classified.append(info)

    analysis.artifacts = classified
    quality, confirmation = compute_signal_quality(classified)
    analysis.quality = quality
    analysis.ir_confirmation = confirmation
    return analysis


def build_finding_report(analyses: list[RepoAnalysis], findings: list[dict]) -> list[dict]:
    """Build per-finding report rows with ir_confirmation and signal_quality."""
    rows = []
    # Build lookup: repo_url -> analysis
    repo_map = {a.repo_url: a for a in analyses}

    for finding in findings:
        repo_url = finding.get("repo_url", "")
        analysis = repo_map.get(repo_url)
        if analysis is None:
            sig_q = SignalQuality.LOW
            ir_conf = IRConfirmation.UNKNOWN
            rationale = "no artifact data available"
        else:
            sig_q = analysis.quality
            ir_conf = analysis.ir_confirmation
            if ir_conf == IRConfirmation.MISSING:
                if sig_q == SignalQuality.LOW:
                    rationale = "missing because no signal"
                else:
                    rationale = "missing despite high-quality signal"
            else:
                rationale = ""

        row = {
            "finding_id": finding.get("id", finding.get("finding_id", "")),
            "repo_url": repo_url,
            "finding_class": finding.get("class", finding.get("finding_class", "")),
            "signal_quality": sig_q.value,
            "ir_confirmation": ir_conf.value,
            "artifact_source": ",".join(a.artifact_type for a in analysis.artifacts) if analysis else "",
            "rationale": rationale,
        }
        rows.append(row)
    return rows


def write_markdown_report(rows: list[dict], output_path: str) -> None:
    """Write a markdown summary report."""
    lines = [
        "# Sierra v3 Signal Quality Report",
        "",
        "| Finding ID | Repo URL | Class | Signal Quality | IR Confirmation | Artifact Source | Rationale |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['finding_id']} | {r['repo_url']} | {r['finding_class']} "
            f"| {r['signal_quality']} | {r['ir_confirmation']} "
            f"| {r['artifact_source']} | {r['rationale']} |"
        )
    lines.append("")
    lines.append("## KPI Summary")
    lines.append("")
    total = len(rows)
    confirmed = sum(1 for r in rows if r["ir_confirmation"] == "confirmed")
    high = sum(1 for r in rows if r["signal_quality"] == "high")
    lines.append(f"- Total findings: {total}")
    lines.append(f"- IR Confirmed: {confirmed}")
    lines.append(f"- High quality signals: {high}")
    lines.append(f"- Coverage: {confirmed / total * 100:.1f}%" if total else "- Coverage: N/A")
    lines.append("")

    Path(output_path).write_text("\n".join(lines))
    print(f"Report written to {output_path}")


def write_json_report(rows: list[dict], output_path: str) -> None:
    """Write a JSON summary report."""
    total = len(rows)
    confirmed = sum(1 for r in rows if r["ir_confirmation"] == "confirmed")
    high = sum(1 for r in rows if r["signal_quality"] == "high")
    summary = {
        "total_findings": total,
        "ir_confirmed": confirmed,
        "high_quality_signals": high,
        "coverage_pct": round(confirmed / total * 100, 1) if total else 0,
        "rows": rows,
    }
    Path(output_path).write_text(json.dumps(summary, indent=2))
    print(f"JSON report written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Sierra v3 signal quality analysis")
    parser.add_argument("--input", required=True, help="Input JSON with findings list")
    parser.add_argument("--gh-token", default=None, help="GitHub token")
    parser.add_argument("--output-md", default=None, help="Output markdown report path")
    parser.add_argument("--output-json", default=None, help="Output JSON report path")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    findings = data.get("findings", [])
    repo_urls = list({f.get("repo_url", "") for f in findings if f.get("repo_url")})

    print(f"Analyzing {len(repo_urls)} repos, {len(findings)} findings...")
    analyses = []
    for url in repo_urls:
        print(f"  Analyzing {url}...")
        analyses.append(analyze_repo(url, args.gh_token))

    rows = build_finding_report(analyses, findings)

    if args.output_md:
        write_markdown_report(rows, args.output_md)
    if args.output_json:
        write_json_report(rows, args.output_json)

    # Print summary to stdout for CI
    total = len(rows)
    confirmed = sum(1 for r in rows if r["ir_confirmation"] == "confirmed")
    high = sum(1 for r in rows if r["signal_quality"] == "high")
    print(f"\n=== Sierra v3 KPI ===")
    print(f"Total findings: {total}")
    print(f"IR Confirmed: {confirmed}")
    print(f"High quality: {high}")
    print(f"Coverage: {confirmed / total * 100:.1f}%" if total else "Coverage: N/A")

    if total and confirmed == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
