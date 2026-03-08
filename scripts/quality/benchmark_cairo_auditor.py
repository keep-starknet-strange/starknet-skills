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
        re.search(r"assert\([^)]*(swap_fee|fee_bps)[^)]*(<=|<)", lower)
        or re.search(r"(swap_fee|fee_bps)\s*(<=|<)\s*(max|10_?000|10000|2_?000|2000)", lower)
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
    call_count = len(re.findall(r"call_contract_syscall", lower))
    has_error_branch = "is_err" in lower
    has_selector_alias = "selector_" in lower
    return call_count >= 2 and has_error_branch and has_selector_alias


DETECTORS = {
    "AA-SELF-CALL-SESSION": detect_aa_self_call_session,
    "UNCHECKED_FEE_BOUND": detect_unchecked_fee_bound,
    "SHUTDOWN_OVERRIDE_PRECEDENCE": detect_shutdown_override_precedence,
    "SYSCALL_SELECTOR_FALLBACK_ASSUMPTION": detect_selector_fallback_assumption,
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
    lines.append("# v0.2.0 Cairo Auditor Benchmark")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
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
    markdown = render_markdown(
        cases_path=cases_path,
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
