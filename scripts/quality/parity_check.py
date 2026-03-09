#!/usr/bin/env python3
"""Local parity checks against pashov/ethskills-style quality bars.

This script is intended for local verification and scorecard generation.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | FAIL | SKIP
    detail: str


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def has_text(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def markdown_section(path: Path, heading: str) -> str | None:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start = idx + 1
            break
    if start is None:
        return None

    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def require_exists(path: Path) -> bool:
    return path.exists()


def main() -> int:
    results: list[CheckResult] = []

    # 1) Skill contract validation.
    res = run([sys.executable, "scripts/quality/validate_skills.py"])
    if res.returncode == 0:
        results.append(CheckResult("skill-contract-validator", "PASS", res.stdout.strip()))
    else:
        results.append(CheckResult("skill-contract-validator", "FAIL", (res.stderr or res.stdout).strip()))

    # 2) Baseline governance files.
    required = ["LICENSE", "SECURITY.md", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "README.md", "SKILL.md"]
    missing = [p for p in required if not require_exists(ROOT / p)]
    if not missing:
        results.append(CheckResult("governance-and-entry-files", "PASS", "all required files present"))
    else:
        results.append(CheckResult("governance-and-entry-files", "FAIL", f"missing: {', '.join(missing)}"))

    # 3) Plugin marketplace metadata consistency.
    market = run([sys.executable, "scripts/quality/validate_marketplace.py"])
    if market.returncode == 0:
        results.append(CheckResult("plugin-marketplace-metadata", "PASS", market.stdout.strip()))
    else:
        results.append(CheckResult("plugin-marketplace-metadata", "FAIL", (market.stderr or market.stdout).strip()))

    # 4) Install onboarding in README.
    install_section = markdown_section(ROOT / "README.md", "## Install & Use")
    if install_section is None:
        results.append(CheckResult("readme-install-flow", "FAIL", "README missing 'Install & Use' section"))
    else:
        command_markers = [
            "/plugin marketplace add",
            "/plugin menu",
            "pip install",
            "npm install",
            "brew install",
        ]
        has_command_marker = any(marker in install_section for marker in command_markers)
        has_plugin_identifier = "starknet-skills" in install_section
        if has_command_marker and has_plugin_identifier:
            results.append(
                CheckResult(
                    "readme-install-flow",
                    "PASS",
                    "README install section includes concrete commands and plugin identifier",
                )
            )
        else:
            results.append(
                CheckResult(
                    "readme-install-flow",
                    "FAIL",
                    "README install section missing concrete install command and/or plugin identifier",
                )
            )

    # 5) CLI accuracy: snforge flags.
    try:
        snforge = run(["snforge", "test", "--help"])
    except FileNotFoundError:
        results.append(CheckResult("snforge-cli-check", "SKIP", "snforge unavailable"))
    else:
        if snforge.returncode != 0:
            results.append(
                CheckResult(
                    "snforge-cli-check",
                    "FAIL",
                    (snforge.stderr or snforge.stdout).strip() or "snforge --help returned non-zero exit code",
                )
            )
        else:
            doc = (ROOT / "cairo-testing/references/legacy-full.md").read_text(encoding="utf-8")
            has_exact = "--exact" in snforge.stdout
            forbids_filter = "--filter" not in snforge.stdout
            doc_has_filter = "--filter" in doc
            if has_exact and forbids_filter and not doc_has_filter:
                results.append(
                    CheckResult("snforge-cli-check", "PASS", "docs match snforge 0.56 filter/exact behavior")
                )
            else:
                results.append(
                    CheckResult(
                        "snforge-cli-check",
                        "FAIL",
                        f"has_exact={has_exact}, forbids_filter={forbids_filter}, doc_has_filter={doc_has_filter}",
                    )
                )

    # 6) CLI accuracy: sncast account import and verify backends.
    try:
        sncast_account = run(["sncast", "account", "--help"])
        sncast_verify = run(["sncast", "verify", "--help"])
    except FileNotFoundError:
        results.append(CheckResult("sncast-cli-check", "SKIP", "sncast unavailable"))
    else:
        if sncast_account.returncode != 0 or sncast_verify.returncode != 0:
            stderr = "\n".join(
                part.strip()
                for part in [sncast_account.stderr, sncast_verify.stderr, sncast_account.stdout, sncast_verify.stdout]
                if part and part.strip()
            )
            results.append(
                CheckResult(
                    "sncast-cli-check",
                    "FAIL",
                    stderr or "sncast account/verify --help returned non-zero exit code",
                )
            )
        else:
            doc_toolchain = (ROOT / "cairo-toolchain/references/legacy-full.md").read_text(encoding="utf-8")
            has_import = "import" in sncast_account.stdout
            no_add_subcmd = " add " not in sncast_account.stdout
            mentions_import = "sncast account import" in doc_toolchain
            mentions_add = "sncast account add" in doc_toolchain
            verifier_ok = "[possible values: walnut, voyager]" in sncast_verify.stdout
            docs_mention_both = "both Walnut and Voyager" in doc_toolchain
            uses_json = "sncast --json declare" in doc_toolchain and "jq -r '.class_hash'" in doc_toolchain

            if all([has_import, no_add_subcmd, mentions_import, not mentions_add, verifier_ok, docs_mention_both, uses_json]):
                results.append(
                    CheckResult("sncast-cli-check", "PASS", "docs match sncast 0.56 account/verify/json patterns")
                )
            else:
                results.append(
                    CheckResult(
                        "sncast-cli-check",
                        "FAIL",
                        (
                            f"has_import={has_import}, no_add_subcmd={no_add_subcmd}, mentions_import={mentions_import}, "
                            f"mentions_add={mentions_add}, verifier_ok={verifier_ok}, docs_mention_both={docs_mention_both}, uses_json={uses_json}"
                        ),
                    )
                )

    # 7) Trail of Bits-style authoring contract (explicit parity signal).
    non_root_skills = sorted(p for p in ROOT.rglob("SKILL.md") if p.parent != ROOT)
    tob_errors: list[str] = []
    for skill in non_root_skills:
        content = skill.read_text(encoding="utf-8")
        lines = content.splitlines()
        if len(lines) > 500:
            tob_errors.append(f"{skill}: exceeds 500 lines")
        if "## When to Use" not in content or "## When NOT to Use" not in content:
            tob_errors.append(f"{skill}: missing required section(s)")
        if "auditor" in skill.as_posix() and "## Rationalizations to Reject" not in content:
            tob_errors.append(f"{skill}: missing Rationalizations to Reject")
        if "## Quick Start" not in content:
            tob_errors.append(f"{skill}: missing Quick Start")

        body = content.split("---", 2)[-1]
        local_links = [
            m.group(1)
            for m in LINK_RE.finditer(body)
            if not m.group(1).startswith(("http://", "https://"))
        ]
        if not local_links:
            tob_errors.append(f"{skill}: no local markdown links for progressive disclosure")

    if not tob_errors:
        results.append(
            CheckResult(
                "trailofbits-authoring-parity",
                "PASS",
                f"{len(non_root_skills)} module SKILLs satisfy sections/quickstart/progressive-disclosure checks",
            )
        )
    else:
        results.append(
            CheckResult(
                "trailofbits-authoring-parity",
                "FAIL",
                "; ".join(tob_errors),
            )
        )

    # Print summary.
    width = max(len(r.name) for r in results)
    failures = 0
    for r in results:
        print(f"{r.name.ljust(width)}  {r.status:4}  {r.detail}")
        if r.status == "FAIL":
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
