#!/usr/bin/env python3
"""Local parity checks against pashov/ethskills-style quality bars.

This script is intended for local verification and scorecard generation.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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

    # 3) Install onboarding in README.
    if has_text(ROOT / "README.md", "## Install & Use"):
        results.append(CheckResult("readme-install-flow", "PASS", "README includes install/use section"))
    else:
        results.append(CheckResult("readme-install-flow", "FAIL", "README missing 'Install & Use' section"))

    # 4) CLI accuracy: snforge flags.
    snforge = run(["snforge", "test", "--help"])
    if snforge.returncode != 0:
        results.append(CheckResult("snforge-cli-check", "SKIP", "snforge unavailable"))
    else:
        doc = (ROOT / "cairo-testing/references/legacy-full.md").read_text(encoding="utf-8")
        has_exact = "--exact" in snforge.stdout
        forbids_filter = "--filter" not in snforge.stdout
        doc_has_filter = "--filter" in doc
        if has_exact and forbids_filter and not doc_has_filter:
            results.append(CheckResult("snforge-cli-check", "PASS", "docs match snforge 0.56 filter/exact behavior"))
        else:
            results.append(
                CheckResult(
                    "snforge-cli-check",
                    "FAIL",
                    f"has_exact={has_exact}, forbids_filter={forbids_filter}, doc_has_filter={doc_has_filter}",
                )
            )

    # 5) CLI accuracy: sncast account import and verify backends.
    sncast_account = run(["sncast", "account", "--help"])
    sncast_verify = run(["sncast", "verify", "--help"])
    if sncast_account.returncode != 0 or sncast_verify.returncode != 0:
        results.append(CheckResult("sncast-cli-check", "SKIP", "sncast unavailable"))
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
            results.append(CheckResult("sncast-cli-check", "PASS", "docs match sncast 0.56 account/verify/json patterns"))
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
