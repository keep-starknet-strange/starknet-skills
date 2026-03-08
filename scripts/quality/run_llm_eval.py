#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class EvalCase:
    case_id: str
    class_id: str
    expected_detect: bool
    code: str
    source: str
    source_url: str | None


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    seen: set[str] = set()
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        for key in ("case_id", "class_id", "expected_detect", "code", "source"):
            if key not in raw:
                raise ValueError(f"line {i}: missing key '{key}'")
        case_id = raw["case_id"]
        if case_id in seen:
            raise ValueError(f"line {i}: duplicate case_id '{case_id}'")
        seen.add(case_id)
        cases.append(
            EvalCase(
                case_id=case_id,
                class_id=raw["class_id"],
                expected_detect=bool(raw["expected_detect"]),
                code=raw["code"],
                source=raw["source"],
                source_url=raw.get("source_url"),
            )
        )
    return cases


def precision(tp: int, fp: int) -> float:
    denom = tp + fp
    return 1.0 if denom == 0 else tp / denom


def recall(tp: int, fn: int) -> float:
    denom = tp + fn
    return 1.0 if denom == 0 else tp / denom


def build_messages(case: EvalCase) -> list[dict[str, str]]:
    system = (
        "You are a Cairo smart-contract security reviewer. "
        "Given one vulnerability class and one code snippet, decide if the class is present. "
        "Return strict JSON with keys: detected (boolean), confidence (low|medium|high), reason (string)."
    )
    user = (
        f"Class ID: {case.class_id}\n"
        "Task: detect only this class. Ignore unrelated issues.\n"
        "Code:\n"
        "```cairo\n"
        f"{case.code}\n"
        "```\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_model_json(text: str) -> dict:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("model output is not valid JSON object")


def run_single_case(
    *,
    api_key: str,
    model: str,
    case: EvalCase,
    timeout_seconds: int,
    retries: int,
) -> dict[str, object]:
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": build_messages(case),
    }
    body = json.dumps(payload).encode("utf-8")

    last_err = ""
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url="https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
            content = raw["choices"][0]["message"]["content"]
            parsed = parse_model_json(content)
            detected = bool(parsed.get("detected", False))
            confidence = str(parsed.get("confidence", "medium")).lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = "medium"
            reason = str(parsed.get("reason", ""))[:500]
            return {
                "case_id": case.case_id,
                "class_id": case.class_id,
                "expected_detect": case.expected_detect,
                "predicted_detect": detected,
                "confidence": confidence,
                "reason": reason,
                "source": case.source,
                "source_url": case.source_url,
                "error": "",
            }
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError) as exc:
            last_err = str(exc)
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue

    return {
        "case_id": case.case_id,
        "class_id": case.class_id,
        "expected_detect": case.expected_detect,
        "predicted_detect": False,
        "confidence": "low",
        "reason": "",
        "source": case.source,
        "source_url": case.source_url,
        "error": f"model_call_failed: {last_err[:300]}",
    }


def render_markdown(
    *,
    model: str,
    cases_path: Path,
    generated_at: str,
    totals: dict[str, int],
    results: list[dict[str, object]],
) -> str:
    tp = totals["tp"]
    tn = totals["tn"]
    fp = totals["fp"]
    fn = totals["fn"]
    total = tp + tn + fp + fn

    p = precision(tp, fp)
    r = recall(tp, fn)
    acc = (tp + tn) / total if total else 1.0

    lines: list[str] = []
    lines.append("# Cairo Auditor LLM Held-out Eval")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Model: `{model}`")
    lines.append(f"Case pack: `{cases_path.as_posix()}`")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- Cases: {total}")
    lines.append(f"- Precision: {p:.3f}")
    lines.append(f"- Recall: {r:.3f}")
    lines.append(f"- Accuracy: {acc:.3f}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | ---: |")
    lines.append(f"| TP | {tp} |")
    lines.append(f"| FP | {fp} |")
    lines.append(f"| FN | {fn} |")
    lines.append(f"| TN | {tn} |")
    lines.append("")
    lines.append("## Case Outcomes")
    lines.append("")
    lines.append("| Case | Class | Expected | Predicted | Confidence | Outcome | Notes |")
    lines.append("| --- | --- | ---: | ---: | --- | --- | --- |")
    for row in results:
        expected = bool(row["expected_detect"])
        predicted = bool(row["predicted_detect"])
        if predicted and expected:
            outcome = "tp"
        elif predicted and not expected:
            outcome = "fp"
        elif not predicted and expected:
            outcome = "fn"
        else:
            outcome = "tn"
        notes = row.get("error") or row.get("reason") or ""
        notes = str(notes).replace("|", "/")[:120]
        lines.append(
            f"| {row['case_id']} | {row['class_id']} | {str(expected).lower()} | {str(predicted).lower()} | {row['confidence']} | {outcome} | {notes} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LLM-based held-out eval for cairo-auditor.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--min-precision", type=float, default=0.75)
    parser.add_argument("--min-recall", type=float, default=0.75)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM eval")

    cases_path = Path(args.cases)
    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    cases = load_cases(cases_path)

    results: list[dict[str, object]] = []
    totals = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}

    for case in cases:
        row = run_single_case(
            api_key=api_key,
            model=args.model,
            case=case,
            timeout_seconds=args.timeout_seconds,
            retries=args.retries,
        )
        expected = bool(row["expected_detect"])
        predicted = bool(row["predicted_detect"])
        if predicted and expected:
            totals["tp"] += 1
        elif predicted and not expected:
            totals["fp"] += 1
        elif not predicted and expected:
            totals["fn"] += 1
        else:
            totals["tn"] += 1
        results.append(row)

    p = precision(totals["tp"], totals["fp"])
    r = recall(totals["tp"], totals["fn"])
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    report = {
        "generated_at": generated_at,
        "model": args.model,
        "cases": len(cases),
        "precision": p,
        "recall": r,
        "totals": totals,
        "results": results,
        "gate": {
            "min_precision": args.min_precision,
            "min_recall": args.min_recall,
            "passed": p >= args.min_precision and r >= args.min_recall,
        },
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    out_md.write_text(
        render_markdown(
            model=args.model,
            cases_path=cases_path,
            generated_at=generated_at,
            totals=totals,
            results=results,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "cases": len(cases),
                "precision": round(p, 6),
                "recall": round(r, 6),
                "output_json": out_json.as_posix(),
                "output_md": out_md.as_posix(),
            },
            ensure_ascii=True,
        )
    )

    if p < args.min_precision or r < args.min_recall:
        print(
            f"FAILED: precision={p:.3f} recall={r:.3f} "
            f"thresholds=({args.min_precision:.3f}, {args.min_recall:.3f})"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
