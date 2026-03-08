#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class LabelRow:
    finding_id: str
    release: str
    scan_id: str
    repo: str
    file: str
    class_id: str
    predicted_detect: bool
    human_outcome: str  # tp | fp
    confidence: str
    reviewer: str
    reviewed_at: str
    rationale: str


def load_labels(path: Path) -> list[LabelRow]:
    rows: list[LabelRow] = []
    seen_ids: set[str] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        required = {
            "finding_id",
            "release",
            "scan_id",
            "repo",
            "file",
            "class_id",
            "predicted_detect",
            "human_outcome",
            "confidence",
            "reviewer",
            "reviewed_at",
            "rationale",
        }
        missing = sorted(required - set(raw.keys()))
        if missing:
            raise ValueError(f"{path}:{line_no}: missing keys: {missing}")
        finding_id = str(raw["finding_id"])
        if finding_id in seen_ids:
            raise ValueError(f"{path}:{line_no}: duplicate finding_id: {finding_id}")
        seen_ids.add(finding_id)
        human_outcome = str(raw["human_outcome"]).lower()
        if human_outcome not in {"tp", "fp"}:
            raise ValueError(f"{path}:{line_no}: human_outcome must be tp|fp")
        predicted_detect = bool(raw["predicted_detect"])
        rows.append(
            LabelRow(
                finding_id=finding_id,
                release=str(raw["release"]),
                scan_id=str(raw["scan_id"]),
                repo=str(raw["repo"]),
                file=str(raw["file"]),
                class_id=str(raw["class_id"]),
                predicted_detect=predicted_detect,
                human_outcome=human_outcome,
                confidence=str(raw["confidence"]).lower(),
                reviewer=str(raw["reviewer"]),
                reviewed_at=str(raw["reviewed_at"]),
                rationale=str(raw["rationale"]),
            )
        )
    return rows


def precision(tp: int, fp: int) -> float:
    denom = tp + fp
    return 1.0 if denom == 0 else tp / denom


def recall(tp: int, fn: int) -> float:
    denom = tp + fn
    return 1.0 if denom == 0 else tp / denom


def score(rows: list[LabelRow]) -> dict[str, int]:
    totals = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for row in rows:
        expected_detect = row.human_outcome == "tp"
        predicted = row.predicted_detect
        if predicted and expected_detect:
            totals["tp"] += 1
        elif predicted and not expected_detect:
            totals["fp"] += 1
        elif (not predicted) and expected_detect:
            totals["fn"] += 1
        else:
            totals["tn"] += 1
    return totals


def render_release_md(
    *,
    release: str,
    generated_at: str,
    label_path: Path,
    totals: dict[str, int],
    rows: list[LabelRow],
) -> str:
    tp = totals["tp"]
    fp = totals["fp"]
    fn = totals["fn"]
    tn = totals["tn"]
    total = tp + fp + fn + tn
    p = precision(tp, fp)
    r = recall(tp, fn)
    acc = 1.0 if total == 0 else (tp + tn) / total

    lines: list[str] = []
    lines.append(f"# {release} Cairo Auditor External Triage")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Label file: `{label_path.as_posix()}`")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- Findings labeled: {total}")
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
    lines.append("## Labeled Findings")
    lines.append("")
    lines.append("| Finding | Class | Repo | Outcome | Confidence | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in sorted(rows, key=lambda item: item.finding_id):
        note = row.rationale.replace("|", "/")
        lines.append(
            f"| {row.finding_id} | {row.class_id} | `{row.repo}` | {row.human_outcome} | {row.confidence} | {note} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_release_metrics(path: Path) -> tuple[float, float] | None:
    text = path.read_text(encoding="utf-8")
    precision_value = None
    recall_value = None
    for line in text.splitlines():
        if line.startswith("- Precision:"):
            precision_value = float(line.split(":", 1)[1].strip())
        elif line.startswith("- Recall:"):
            recall_value = float(line.split(":", 1)[1].strip())
    if precision_value is None or recall_value is None:
        return None
    return precision_value, recall_value


def update_trend_markdown(
    *,
    release: str,
    release_md: Path,
    trend_md: Path,
    generated_at: str,
) -> None:
    metrics = parse_release_metrics(release_md)
    if metrics is None:
        raise ValueError(f"could not parse precision/recall from {release_md}")
    p, r = metrics

    rows: list[tuple[str, float, float, str]] = []
    if trend_md.exists():
        for line in trend_md.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| v"):
                continue
            parts = [x.strip() for x in line.strip("|").split("|")]
            if len(parts) != 4:
                continue
            rel, p_raw, r_raw, date = parts
            try:
                rows.append((rel, float(p_raw), float(r_raw), date))
            except ValueError:
                continue

    rows = [row for row in rows if row[0] != release]
    rows.append((release, p, r, generated_at.split("T", 1)[0]))
    rows.sort(key=lambda item: item[0])

    lines = [
        "# Cairo Auditor External Triage Trend",
        "",
        "Release-over-release precision/recall from human-labeled external findings.",
        "",
        "| Release | Precision | Recall | Date |",
        "| --- | ---: | ---: | --- |",
    ]
    for rel, p_val, r_val, date in rows:
        lines.append(f"| {rel} | {p_val:.3f} | {r_val:.3f} | {date} |")
    lines.append("")
    trend_md.parent.mkdir(parents=True, exist_ok=True)
    trend_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score human-labeled external scan findings and update release trend."
    )
    parser.add_argument("--labels", required=True, help="JSONL label file path")
    parser.add_argument("--release", required=True, help="Release/version label, e.g. v0.2.0")
    parser.add_argument("--output-md", required=True, help="Release scorecard markdown output path")
    parser.add_argument("--output-json", required=True, help="Release scorecard JSON output path")
    parser.add_argument("--trend-md", required=True, help="Trend markdown output path")
    parser.add_argument("--min-precision", type=float, default=0.7)
    parser.add_argument("--min-recall", type=float, default=0.9)
    args = parser.parse_args()

    label_path = Path(args.labels)
    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    trend_md = Path(args.trend_md)

    rows = load_labels(label_path)
    totals = score(rows)

    tp = totals["tp"]
    fp = totals["fp"]
    fn = totals["fn"]
    p = precision(tp, fp)
    r = recall(tp, fn)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    markdown = render_release_md(
        release=args.release,
        generated_at=generated_at,
        label_path=label_path,
        totals=totals,
        rows=rows,
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(markdown + "\n", encoding="utf-8")

    summary = {
        "generated_at": generated_at,
        "release": args.release,
        "labels_path": label_path.as_posix(),
        "totals": totals,
        "precision": p,
        "recall": r,
        "gate": {
            "min_precision": args.min_precision,
            "min_recall": args.min_recall,
            "passed": p >= args.min_precision and r >= args.min_recall,
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    update_trend_markdown(
        release=args.release,
        release_md=output_md,
        trend_md=trend_md,
        generated_at=generated_at,
    )

    print(
        json.dumps(
            {
                "labels": len(rows),
                "precision": round(p, 6),
                "recall": round(r, 6),
                "output_md": output_md.as_posix(),
                "output_json": output_json.as_posix(),
                "trend_md": trend_md.as_posix(),
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
