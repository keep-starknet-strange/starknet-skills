#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Case:
    case_id: str
    class_id: str
    expected_detect: bool
    source: str
    source_url: str | None
    code: str


def load_cases(path: Path) -> list[Case]:
    cases: list[Case] = []
    seen_case_ids: set[str] = set()
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"line {i}: case must be object")
        required = {"case_id", "class_id", "expected_detect", "source", "code"}
        missing = required - set(raw.keys())
        if missing:
            raise ValueError(f"line {i}: missing keys: {sorted(missing)}")
        if not isinstance(raw["expected_detect"], bool):
            raise ValueError(f"line {i}: expected_detect must be bool")
        for key in ("case_id", "class_id", "source", "code"):
            if not isinstance(raw[key], str):
                raise ValueError(f"line {i}: {key} must be string")
        if raw["case_id"] in seen_case_ids:
            raise ValueError(f"line {i}: duplicate case_id: {raw['case_id']}")
        seen_case_ids.add(raw["case_id"])
        if raw.get("source_url") is not None and not isinstance(raw["source_url"], str):
            raise ValueError(f"line {i}: source_url must be string when present")
        cases.append(
            Case(
                case_id=raw["case_id"],
                class_id=raw["class_id"],
                expected_detect=raw["expected_detect"],
                source=raw["source"],
                source_url=raw.get("source_url"),
                code=raw["code"],
            )
        )
    return cases


def detect_aa_self_call_session(code: str) -> bool:
    lower = code.lower()
    if "__execute__" not in lower and "session" not in lower:
        return False
    if "call_contract_syscall" not in lower:
        return False
    self_guard_patterns = [
        r"call\.to\s*!=\s*starknet::get_contract_address\(\)",
        r"call\.to\s*!=\s*self",
        r"if\s+\*?call\.to\s*==\s*starknet::get_contract_address\(\)\s*\{[\s\S]{0,120}(panic|assert|revert)",
    ]
    for pattern in self_guard_patterns:
        if re.search(pattern, lower):
            return False
    return True


def detect_unchecked_fee_bound(code: str) -> bool:
    lower = code.lower()
    if "fee" not in lower:
        return False
    if "swap_fee" not in lower and "fee_bps" not in lower:
        return False

    has_forward = bool(
        re.search(r"(swap_fee|fee_bps)\s*\.into\(\)", lower)
        or re.search(r"\.write\((swap_fee|fee_bps)\)", lower)
        or re.search(r"\blet\s+\w+\s*=\s*(swap_fee|fee_bps)\b", lower)
        or re.search(r"\b(array!|vec!\s*\[)[^\n]*(swap_fee|fee_bps)", lower)
    )
    has_bound = bool(
        re.search(r"assert!?\b[^;\n]{0,220}(swap_fee|fee_bps)[^;\n]{0,220}(<=|<)", lower)
        or re.search(r"(swap_fee|fee_bps)\s*(<=|<)\s*(max|10_?000|10000|2_?000|2000)", lower)
        or re.search(r"(swap_fee|fee_bps)\s*\.into\(\)\s*(<=|<)", lower)
    )
    return has_forward and not has_bound


def detect_shutdown_override_precedence(code: str) -> bool:
    lower = code.lower()
    if "infer_shutdown_mode" not in lower or "fixed_shutdown_mode" not in lower:
        return False

    infer_pos = lower.find("infer_shutdown_mode")
    fixed_pos = lower.find("fixed_shutdown_mode")
    infer_early_return = bool(
        re.search(r"infer_shutdown_mode[\s\S]{0,220}if[\s\S]{0,120}return", lower)
    )
    fixed_first = fixed_pos != -1 and infer_pos != -1 and fixed_pos < infer_pos
    return infer_early_return and not fixed_first


def detect_selector_fallback_assumption(code: str) -> bool:
    lower = code.lower()
    if "is_err" not in lower:
        return False
    pattern = re.compile(
        r"call_contract_syscall\([^)]*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,[^)]*\)"
        r"[\s\S]{0,260}if\s*\(?\s*result\.is_err\(\)\s*\)?\s*\{"
        r"[\s\S]{0,260}call_contract_syscall\([^)]*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,",
        re.IGNORECASE,
    )
    for first_selector, second_selector in pattern.findall(code):
        if first_selector != second_selector and (
            first_selector.lower().startswith("selector_")
            or second_selector.lower().startswith("selector_")
        ):
            return True
    return False


def _upgrade_snippets(lower: str) -> list[str]:
    snippets: list[str] = []
    for match in re.finditer(r"fn\s+upgrade\s*\(", lower):
        start = match.start()
        snippets.append(lower[start : start + 1800])
    return snippets


def _iter_functions(lower: str) -> list[tuple[str, str, str]]:
    functions: list[tuple[str, str, str]] = []
    for match in re.finditer(r"fn\s+([a-z_][a-z0-9_]*)\s*\(([^)]*)\)\s*\{", lower, flags=re.IGNORECASE):
        fn_name = match.group(1)
        signature = match.group(2)
        body_start = match.end()
        depth = 1
        i = body_start
        while i < len(lower) and depth > 0:
            ch = lower[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        if depth != 0:
            continue
        functions.append((fn_name, signature, lower[body_start : i - 1]))
    return functions


def _extract_fn_signature_and_body(lower: str, fn_name: str) -> tuple[str | None, str | None]:
    for name, signature, body in _iter_functions(lower):
        if name.lower() == fn_name.lower():
            return signature, body
    return None, None


def _has_nonzero_class_hash_guard(snippet: str) -> bool:
    return bool(
        re.search(r"assert!?\([^)]*new_class_hash[^)]*is_non_zero", snippet)
        or re.search(r"assert!?\([^)]*new_class_hash[^)]*!=\s*0", snippet)
        or re.search(r"assert!?\([^)]*!\s*new_class_hash\.is_zero\(\)", snippet)
        or re.search(r"assert!?\([^)]*new_class_hash\.is_zero\(\)[^)]*==\s*false", snippet)
        or re.search(r"if\s*\([^)]*new_class_hash[^)]*is_non_zero", snippet)
        or re.search(r"if\s*\([^)]*new_class_hash[^)]*!=\s*0", snippet)
        or re.search(r"if\s*\([^)]*new_class_hash\.is_zero\(\)\s*\)\s*\{[\s\S]{0,180}(panic|assert|revert)", snippet)
        or re.search(r"if\s+new_class_hash[^:\n]{0,80}is_non_zero", snippet)
        or re.search(r"if\s+new_class_hash[^:\n]{0,80}!=\s*0", snippet)
    )


def detect_immediate_upgrade_without_timelock(code: str) -> bool:
    lower = code.lower()
    snippets = _upgrade_snippets(lower)
    if not snippets:
        return False

    timelock_markers = (
        "timelock",
        "schedule_upgrade",
        "upgrade_delay",
        "pending_upgrade",
        "executable_after",
    )

    for snippet in snippets:
        has_upgrade_call = (
            "replace_class_syscall" in snippet or "upgradeable.upgrade" in snippet
        )
        if not has_upgrade_call:
            continue
        if any(marker in snippet for marker in timelock_markers):
            continue
        return True
    return False


def detect_upgrade_class_hash_without_nonzero_guard(code: str) -> bool:
    lower = code.lower()
    snippets = _upgrade_snippets(lower)
    if not snippets:
        return False

    # OZ UpgradeableComponent::upgrade() already checks non-zero class hash internally.
    uses_oz_upgradeable_component = any(
        marker in lower
        for marker in (
            "upgradeablecomponent",
            "openzeppelin_upgrades",
            "openzeppelin::upgrades",
        )
    )

    for snippet in snippets:
        has_direct_syscall = "replace_class_syscall" in snippet
        has_component_upgrade = "upgradeable.upgrade" in snippet
        if not has_direct_syscall and not has_component_upgrade:
            continue
        if "new_class_hash" not in snippet:
            continue
        has_nonzero_guard = _has_nonzero_class_hash_guard(snippet)

        if has_direct_syscall and not has_nonzero_guard:
            return True
        if has_component_upgrade and not has_nonzero_guard and not uses_oz_upgradeable_component:
            return True
    return False


def detect_critical_address_init_without_nonzero_guard(code: str) -> bool:
    lower = code.lower()
    constructor_sig, body = _extract_fn_signature_and_body(lower, "constructor")
    if constructor_sig is None or body is None:
        return False

    params = re.findall(r"([a-z_][a-z0-9_]*)\s*:\s*contractaddress", constructor_sig)
    if not params:
        return False

    privileged_markers = (
        "owner",
        "admin",
        "manager",
        "coordinator",
        "governor",
        "operator",
        "pauser",
        "upgrade",
    )
    high_impact_dependency_markers = (
        "reclaim",
        "vault",
        "token",
        "oracle",
        "router",
        "dispatcher",
    )
    critical_markers = privileged_markers + high_impact_dependency_markers
    critical_params = [p for p in params if any(marker in p for marker in critical_markers)]
    if not critical_params:
        return False

    for param in critical_params:
        has_guard = bool(
            re.search(
                rf"(assert|is_non_zero|is_zero|!=\s*0)[^\n]{{0,100}}\b{param}\b"
                rf"|\b{param}\b[^\n]{{0,100}}(assert|is_non_zero|is_zero|!=\s*0)",
                body,
            )
        )
        if has_guard:
            continue
        used_for_init = bool(
            re.search(rf"\b\w+\.write\(\s*{param}\b", body)
            or re.search(rf"\binitializer\([^)]*\b{param}\b", body)
            or re.search(rf"\b_grant_role\([^)]*\b{param}\b", body)
        )
        if used_for_init:
            return True
    return False


def detect_constructor_dead_param(code: str) -> bool:
    lower = code.lower()
    constructor_sig, body = _extract_fn_signature_and_body(lower, "constructor")
    if constructor_sig is None or body is None:
        return False

    params = re.findall(r"([a-z_][a-z0-9_]*)\s*:\s*contractaddress", constructor_sig)
    if not params:
        return False

    for param in params:
        if not re.search(rf"\b{param}\b", body):
            return True
    return False


def detect_fees_recipient_zero_dos(code: str) -> bool:
    lower = code.lower()
    if "fees_recipient" not in lower:
        return False

    writes_fees_recipient = bool(re.search(r"\b\w+\.write\(\s*fees_recipient\b", lower))
    if not writes_fees_recipient:
        return False

    has_nonzero_guard = bool(
        re.search(r"assert\([^)]*fees_recipient[^)]*is_non_zero", lower)
        or re.search(r"assert\([^)]*fees_recipient[^)]*!=\s*0", lower)
        or re.search(r"if\s*\([^)]*fees_recipient\.is_zero\(\)\s*\)\s*\{[\s\S]{0,120}(panic|assert|revert)", lower)
    )
    if has_nonzero_guard:
        return False

    downstream_usage = bool(
        re.search(r"(transfer|send|call_contract_syscall)\([^)]*fees_recipient", lower)
        or re.search(r"contractaddressinto{[^}]*value:\s*fees_recipient", lower)
        or re.search(r"self\.\w*fees_recipient\w*\.read\(\)", lower)
    )
    return downstream_usage


def detect_no_access_control_mutation(code: str) -> bool:
    lower = code.lower()
    if "#[starknet::contract]" not in lower:
        return False
    risky_prefixes = (
        "set_",
        "register_",
        "upgrade",
        "pause",
        "unpause",
        "configure_",
        "create_",
        "grant_",
        "revoke_",
    )
    access_markers = (
        "assert_only_owner",
        "assert_only_role",
        "ownable.assert_only_owner",
        "accesscontrol.assert_only_role",
        "access_control.assert_only_role",
        "get_caller_address() ==",
        "get_caller_address()!=",
        "assert!(get_caller_address() ==",
        "assert!(get_caller_address()!=",
        "caller == self.",
        "caller != self.",
    )
    mutation_markers = (
        ".write(",
        "_grant_role(",
        "_revoke_role(",
        "replace_class_syscall(",
        "upgradeable.upgrade(",
        "initializer(",
    )

    for fn_name, signature, body in _iter_functions(lower):
        if fn_name in {"constructor", "__validate__", "__execute__", "__validate_declare__"}:
            continue
        if not fn_name.startswith(risky_prefixes):
            continue
        if "ref self" not in signature:
            continue
        if not any(marker in body for marker in mutation_markers):
            continue
        has_access_guard = any(marker in body for marker in access_markers) or bool(
            re.search(r"assert!?\([^)]*get_caller_address\(\)\s*(==|!=)", body)
        )
        if has_access_guard:
            continue
        return True
    return False


def detect_cei_violation_erc1155(code: str) -> bool:
    lower = code.lower()
    if "safe_transfer_from" not in lower and "_transfer_item(" not in lower:
        return False

    for _fn_name, _signature, body in _iter_functions(lower):
        interaction_positions = [
            pos for pos in (body.find("safe_transfer_from"), body.find("_transfer_item(")) if pos != -1
        ]
        if not interaction_positions:
            continue
        if "reentrancy" in body or "non_reentrant" in body or "entered" in body:
            continue

        transfer_pos = min(interaction_positions)
        before = body[:transfer_pos]
        after = body[transfer_pos:]
        state_markers = (
            ".write(",
            ".update(",
            "status =",
            "is_fulfilled",
            "is_claimed",
            "fulfilled =",
            "order_status",
            "state =",
        )
        has_state_update_after = any(marker in after for marker in state_markers)
        has_state_update_before = any(marker in before for marker in state_markers)
        if has_state_update_after and not has_state_update_before:
            return True
    return False


DETECTORS = {
    "AA-SELF-CALL-SESSION": detect_aa_self_call_session,
    "UNCHECKED_FEE_BOUND": detect_unchecked_fee_bound,
    "SHUTDOWN_OVERRIDE_PRECEDENCE": detect_shutdown_override_precedence,
    "SYSCALL_SELECTOR_FALLBACK_ASSUMPTION": detect_selector_fallback_assumption,
    "IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK": detect_immediate_upgrade_without_timelock,
    "UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD": detect_upgrade_class_hash_without_nonzero_guard,
    "CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD": detect_critical_address_init_without_nonzero_guard,
    "CONSTRUCTOR_DEAD_PARAM": detect_constructor_dead_param,
    "FEES_RECIPIENT_ZERO_DOS": detect_fees_recipient_zero_dos,
    "NO_ACCESS_CONTROL_MUTATION": detect_no_access_control_mutation,
    "CEI_VIOLATION_ERC1155": detect_cei_violation_erc1155,
}


def precision(tp: int, fp: int) -> float:
    denom = tp + fp
    if denom == 0:
        return 1.0
    return tp / denom


def recall(tp: int, fn: int) -> float:
    denom = tp + fn
    if denom == 0:
        return 1.0
    return tp / denom


def run_benchmark(cases: list[Case]) -> tuple[list[dict[str, object]], dict[str, int]]:
    results: list[dict[str, object]] = []
    totals = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    for case in cases:
        detector = DETECTORS.get(case.class_id)
        if detector is None:
            raise ValueError(f"unsupported class_id: {case.class_id}")
        predicted = detector(case.code)
        expected = case.expected_detect
        if predicted and expected:
            outcome = "tp"
        elif predicted and not expected:
            outcome = "fp"
        elif not predicted and expected:
            outcome = "fn"
        else:
            outcome = "tn"
        totals[outcome] += 1
        results.append(
            {
                "case_id": case.case_id,
                "class_id": case.class_id,
                "expected_detect": expected,
                "predicted_detect": predicted,
                "outcome": outcome,
                "source": case.source,
                "source_url": case.source_url,
            }
        )
    return results, totals


def render_markdown(
    *,
    cases_path: Path,
    version: str,
    title: str,
    results: list[dict[str, object]],
    totals: dict[str, int],
    generated_at: str,
) -> str:
    tp = totals["tp"]
    tn = totals["tn"]
    fp = totals["fp"]
    fn = totals["fn"]
    total = tp + tn + fp + fn

    overall_precision = precision(tp, fp)
    overall_recall = recall(tp, fn)
    overall_accuracy = (tp + tn) / total if total else 1.0

    per_class: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    )
    for row in results:
        class_row = per_class[str(row["class_id"])]
        class_row[str(row["outcome"])] += 1

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Version: {version}")
    lines.append(f"Case pack: `{cases_path.as_posix()}`")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- Cases: {total}")
    lines.append(f"- Precision: {overall_precision:.3f}")
    lines.append(f"- Recall: {overall_recall:.3f}")
    lines.append(f"- Accuracy: {overall_accuracy:.3f}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | ---: |")
    lines.append(f"| TP | {tp} |")
    lines.append(f"| FP | {fp} |")
    lines.append(f"| FN | {fn} |")
    lines.append(f"| TN | {tn} |")
    lines.append("")
    lines.append("## Per Class")
    lines.append("")
    lines.append("| Class | TP | FP | FN | TN | Precision | Recall |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for class_id in sorted(per_class):
        row = per_class[class_id]
        p = precision(row["tp"], row["fp"])
        r = recall(row["tp"], row["fn"])
        lines.append(
            f"| {class_id} | {row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} | {p:.3f} | {r:.3f} |"
        )
    lines.append("")
    lines.append("## Case Outcomes")
    lines.append("")
    lines.append("| Case | Class | Expected | Predicted | Outcome | Source |")
    lines.append("| --- | --- | ---: | ---: | --- | --- |")
    for row in results:
        source = str(row["source"])
        if row.get("source_url"):
            source = f"[{source}]({row['source_url']})"
        lines.append(
            f"| {row['case_id']} | {row['class_id']} | {str(row['expected_detect']).lower()} | {str(row['predicted_detect']).lower()} | {row['outcome']} | {source} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- This benchmark is a deterministic preflight gate for known Cairo vulnerability classes."
    )
    lines.append(
        "- It complements (not replaces) prompt-based held-out evaluation for full agent behavior."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic cairo-auditor benchmark and emit markdown scorecard."
    )
    parser.add_argument("--cases", required=True, help="JSONL benchmark cases path")
    parser.add_argument("--output", required=True, help="Output markdown scorecard path")
    parser.add_argument("--version", default="v0.2.0", help="Version label for scorecard")
    parser.add_argument("--title", default="", help="Optional markdown H1 title override")
    parser.add_argument("--min-precision", type=float, default=0.9)
    parser.add_argument("--min-recall", type=float, default=0.9)
    args = parser.parse_args()

    cases_path = Path(args.cases)
    output_path = Path(args.output)

    cases = load_cases(cases_path)
    results, totals = run_benchmark(cases)

    tp = totals["tp"]
    fp = totals["fp"]
    fn = totals["fn"]
    overall_precision = precision(tp, fp)
    overall_recall = recall(tp, fn)

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    title = args.title.strip() or (
        f"{args.version} {cases_path.stem.replace('_', ' ').replace('-', ' ').title()}"
    )
    markdown = render_markdown(
        cases_path=cases_path,
        version=args.version,
        title=title,
        results=results,
        totals=totals,
        generated_at=generated_at,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "cases": len(cases),
                "precision": round(overall_precision, 6),
                "recall": round(overall_recall, 6),
                "output": output_path.as_posix(),
            },
            ensure_ascii=True,
        )
    )

    if overall_precision < args.min_precision or overall_recall < args.min_recall:
        print(
            f"FAILED: precision={overall_precision:.3f} recall={overall_recall:.3f} "
            f"thresholds=({args.min_precision:.3f}, {args.min_recall:.3f})"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
