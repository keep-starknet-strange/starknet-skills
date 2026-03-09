#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SEVERITY_TO_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}

DEFAULT_RULE_HELP = {
    "AA-SELF-CALL-SESSION": "Session call arrays should block self-call targets or enforce strict selector/target policy.",
    "UNCHECKED_FEE_BOUND": "External/configurable fee parameters should be bounded in the same call path.",
    "SHUTDOWN_OVERRIDE_PRECEDENCE": "Forced/admin override checks should dominate inferred mode checks.",
    "SYSCALL_SELECTOR_FALLBACK_ASSUMPTION": "Avoid selector fallback retries that mask original syscall errors.",
    "IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK": "Upgrade flows should use delay/timelock + explicit scheduling.",
    "UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD": "Guard class hash upgrades with explicit non-zero checks unless framework guarantees are verified.",
    "CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD": "Critical constructor addresses should be validated as non-zero.",
    "CONSTRUCTOR_DEAD_PARAM": "Constructor parameters should be used or removed to avoid misleading security surface.",
    "IRREVOCABLE_ADMIN": "Privileged roles should provide explicit rotation/recovery paths unless immutability is intentional.",
    "ONE_SHOT_REGISTRATION": "One-time registry/initializer slots should have recovery or migration mechanisms.",
    "FEES_RECIPIENT_ZERO_DOS": "Fee recipient addresses should be validated to prevent settlement DOS.",
    "NO_ACCESS_CONTROL_MUTATION": "State-changing privileged mutations should enforce role/caller checks.",
    "CEI_VIOLATION_ERC1155": "Apply CEI ordering for ERC1155 callbacks; update critical state before external interactions.",
}


@dataclass(frozen=True)
class Finding:
    repo: str
    ref: str
    file: str
    class_id: str
    scope: str
    severity: str
    confidence_score: int
    confidence_tier: str
    actionability: str
    gate_status: str
    gate_reason: str


def _load_findings_from_jsonl(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        findings.append(_coerce_finding(raw, source=f"{path}:{line_no}"))
    return findings


def _load_findings_from_scan_json(path: Path) -> list[Finding]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected top-level JSON object")
    rows = raw.get("findings", [])
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected findings list")
    findings: list[Finding] = []
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: findings[{idx}] must be object")
        findings.append(_coerce_finding(item, source=f"{path}:findings[{idx}]"))
    return findings


def _coerce_finding(raw: dict, *, source: str) -> Finding:
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: expected object")
    required = ["repo", "ref", "file", "class_id"]
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"{source}: missing required keys {missing}")

    severity = str(raw.get("severity", "medium")).lower()
    if severity not in SEVERITY_TO_LEVEL:
        severity = "medium"

    score_raw = raw.get("confidence_score", 100)
    try:
        score = int(score_raw)
    except (TypeError, ValueError):
        score = 100

    return Finding(
        repo=str(raw.get("repo", "")),
        ref=str(raw.get("ref", "")),
        file=str(raw.get("file", "")),
        class_id=str(raw.get("class_id", "UNKNOWN")),
        scope=str(raw.get("scope", "prod_scan")),
        severity=severity,
        confidence_score=score,
        confidence_tier=str(raw.get("confidence_tier", "unscored")),
        actionability=str(raw.get("actionability", "unscored")),
        gate_status=str(raw.get("gate_status", "unknown")),
        gate_reason=str(raw.get("gate_reason", "")),
    )


def _tool_version() -> str:
    version_file = REPO_ROOT / "cairo-auditor/VERSION"
    if version_file.is_file():
        value = version_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "dev"


def _build_sarif(*, findings: list[Finding], root_uri: str, run_name: str, information_uri: str) -> dict:
    rules_by_id: dict[str, dict] = {}
    results: list[dict] = []

    for finding in findings:
        if finding.class_id not in rules_by_id:
            rules_by_id[finding.class_id] = {
                "id": finding.class_id,
                "name": finding.class_id,
                "shortDescription": {
                    "text": finding.class_id.replace("_", " ").replace("-", " ").title(),
                },
                "help": {
                    "text": DEFAULT_RULE_HELP.get(
                        finding.class_id,
                        "Review the detector output and confirm exploit path + existing guards.",
                    )
                },
                "defaultConfiguration": {
                    "level": SEVERITY_TO_LEVEL.get(finding.severity, "warning"),
                },
            }

        level = SEVERITY_TO_LEVEL.get(finding.severity, "warning")
        message = (
            f"{finding.class_id} in {finding.file} "
            f"(severity={finding.severity}, score={finding.confidence_score}, "
            f"actionability={finding.actionability}, gate={finding.gate_status})"
        )

        result: dict = {
            "ruleId": finding.class_id,
            "level": level,
            "message": {"text": message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": finding.file,
                            "uriBaseId": "%SRCROOT%",
                        }
                    }
                }
            ],
            "properties": {
                "repo": finding.repo,
                "ref": finding.ref,
                "scope": finding.scope,
                "severity": finding.severity,
                "confidence_score": finding.confidence_score,
                "confidence_tier": finding.confidence_tier,
                "actionability": finding.actionability,
                "gate_status": finding.gate_status,
                "gate_reason": finding.gate_reason,
            },
        }

        if finding.gate_status == "suppressed":
            result["suppressions"] = [
                {
                    "kind": "external",
                    "justification": finding.gate_reason or "suppressed by deterministic gate",
                }
            ]

        results.append(result)

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "automationDetails": {"id": run_name},
                "tool": {
                    "driver": {
                        "name": "starkskills-cairo-auditor",
                        "informationUri": information_uri,
                        "version": _tool_version(),
                        "rules": [rules_by_id[key] for key in sorted(rules_by_id.keys())],
                    }
                },
                "originalUriBaseIds": {
                    "%SRCROOT%": {
                        "uri": root_uri,
                    }
                },
                "results": results,
                "properties": {
                    "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                    "results_total": len(results),
                },
            }
        ],
    }


def _to_file_uri(path: Path) -> str:
    return path.resolve().as_uri().rstrip("/") + "/"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export deterministic findings to SARIF for code-scanning integrations.")
    parser.add_argument("--findings-jsonl", default="", help="Input findings JSONL.")
    parser.add_argument("--scan-json", default="", help="Input scan JSON containing findings list.")
    parser.add_argument("--output", required=True, help="Output SARIF path.")
    parser.add_argument("--root", default=".", help="Source root path for SARIF %%SRCROOT%% URI.")
    parser.add_argument("--run-name", default="starkskills-deterministic", help="SARIF run automation id.")
    parser.add_argument(
        "--information-uri",
        default="https://github.com/keep-starknet-strange/starknet-skills",
        help="Tool information URL embedded in SARIF.",
    )
    args = parser.parse_args()

    if bool(args.findings_jsonl) == bool(args.scan_json):
        parser.error("provide exactly one of --findings-jsonl or --scan-json")

    if args.findings_jsonl:
        findings = _load_findings_from_jsonl(Path(args.findings_jsonl))
    else:
        findings = _load_findings_from_scan_json(Path(args.scan_json))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sarif = _build_sarif(
        findings=findings,
        root_uri=_to_file_uri(Path(args.root)),
        run_name=args.run_name,
        information_uri=args.information_uri,
    )
    output.write_text(json.dumps(sarif, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "output": output.as_posix(),
                "results": len(findings),
                "run_name": args.run_name,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
