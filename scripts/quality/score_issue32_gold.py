#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SEMVER_RELEASE_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class GoldRow:
    finding_id: str
    repo: str
    ref: str
    file: str
    class_id: str
    expected_detect: bool
    rationale: str

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.repo, self.ref, self.file, self.class_id)


@dataclass(frozen=True)
class FindingRow:
    repo: str
    ref: str
    file: str
    class_id: str

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.repo, self.ref, self.file, self.class_id)


def _precision(tp: int, fp: int) -> float:
    return 0.0 if (tp + fp) == 0 else tp / (tp + fp)


def _recall(tp: int, fn: int) -> float:
    return 0.0 if (tp + fn) == 0 else tp / (tp + fn)


def load_gold(path: Path) -> list[GoldRow]:
    rows: list[GoldRow] = []
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str, str, str]] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        required = {
            "finding_id",
            "repo",
            "ref",
            "file",
            "class_id",
            "expected_detect",
            "rationale",
        }
        missing = sorted(required - set(raw.keys()))
        if missing:
            raise ValueError(f"{path}:{line_no}: missing keys: {missing}")
        if not isinstance(raw["expected_detect"], bool):
            raise ValueError(f"{path}:{line_no}: expected_detect must be boolean")

        row = GoldRow(
            finding_id=str(raw["finding_id"]),
            repo=str(raw["repo"]),
            ref=str(raw["ref"]),
            file=str(raw["file"]),
            class_id=str(raw["class_id"]),
            expected_detect=raw["expected_detect"],
            rationale=str(raw["rationale"]),
        )
        if row.finding_id in seen_ids:
            raise ValueError(f"{path}:{line_no}: duplicate finding_id: {row.finding_id}")
        if row.key in seen_keys:
            raise ValueError(f"{path}:{line_no}: duplicate gold key: {row.key}")
        seen_ids.add(row.finding_id)
        seen_keys.add(row.key)
        rows.append(row)
    return rows


def load_findings(path: Path) -> list[FindingRow]:
    rows: list[FindingRow] = []
    seen: set[tuple[str, str, str, str]] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        required = {"repo", "ref", "file", "class_id"}
        missing = sorted(required - set(raw.keys()))
        if missing:
            raise ValueError(f"{path}:{line_no}: missing keys: {missing}")
        if "predicted_detect" in raw:
            if not isinstance(raw["predicted_detect"], bool):
                raise ValueError(f"{path}:{line_no}: predicted_detect must be boolean")
            if not raw["predicted_detect"]:
                continue
        row = FindingRow(
            repo=str(raw["repo"]),
            ref=str(raw["ref"]),
            file=str(raw["file"]),
            class_id=str(raw["class_id"]),
        )
        if row.key in seen:
            continue
        seen.add(row.key)
        rows.append(row)
    return rows


def _render_markdown(
    *,
    release: str,
    generated_at: str,
    gold_path: Path,
    findings_path: Path,
    tp_rows: list[GoldRow],
    fn_rows: list[GoldRow],
    fp_rows: list[FindingRow],
    new_rows: list[FindingRow],
    scoped_predictions: list[FindingRow],
    class_recall: dict[str, float],
) -> str:
    tp = len(tp_rows)
    fp = len(fp_rows)
    new = len(new_rows)
    fn = len(fn_rows)
    precision = _precision(tp, fp + new)
    recall = _recall(tp, fn)

    lines: list[str] = []
    lines.append(f"# {release} Issue #32 External Gold Scorecard")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Gold set: `{gold_path.as_posix()}`")
    lines.append(f"Findings: `{findings_path.as_posix()}`")
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- Scoped predictions: {len(scoped_predictions)}")
    lines.append(f"- TP: {tp}")
    lines.append(f"- FP (gold negatives): {fp}")
    lines.append(f"- NEW (outside frozen rows): {new}")
    lines.append(f"- FN: {fn}")
    lines.append(f"- Precision (TP/(TP+FP+NEW)): {precision:.3f}")
    lines.append(f"- Recall: {recall:.3f}")
    lines.append("")

    lines.append("## Per-Class Recall")
    lines.append("")
    lines.append("| Class | Recall |")
    lines.append("| --- | ---: |")
    for class_id, value in sorted(class_recall.items()):
        lines.append(f"| {class_id} | {value:.3f} |")
    lines.append("")

    if fn_rows:
        lines.append("## Missed Gold Findings (FN)")
        lines.append("")
        lines.append("| Finding | Class | Repo | File |")
        lines.append("| --- | --- | --- | --- |")
        for row in sorted(fn_rows, key=lambda item: item.finding_id):
            lines.append(
                f"| {row.finding_id} | {row.class_id} | `{row.repo}` | `{row.file}` |"
            )
        lines.append("")

    if fp_rows:
        lines.append("## False Positives Against Gold Negatives (FP)")
        lines.append("")
        lines.append("| Repo | File | Class |")
        lines.append("| --- | --- | --- |")
        for row in sorted(fp_rows, key=lambda item: (item.repo, item.file, item.class_id)):
            lines.append(f"| `{row.repo}` | `{row.file}` | `{row.class_id}` |")
        lines.append("")

    if new_rows:
        lines.append("## New Findings Outside Frozen Gold (NEW)")
        lines.append("")
        lines.append("| Repo | File | Class |")
        lines.append("| --- | --- | --- |")
        for row in sorted(new_rows, key=lambda item: (item.repo, item.file, item.class_id)):
            lines.append(f"| `{row.repo}` | `{row.file}` | `{row.class_id}` |")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- This scorecard is a frozen external benchmark from issue #32 (Tokei + Satoru).")
    lines.append("- FP only counts rows explicitly marked expected_detect=false in gold.")
    lines.append("- NEW tracks extra detections in audited files not present in frozen rows.")
    lines.append("")
    return "\n".join(lines)


def _parse_semver_release(label: str) -> tuple[int, int, int] | None:
    match = SEMVER_RELEASE_RE.fullmatch(label.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _parse_trend_rows(path: Path) -> list[tuple[str, int, int, int, int, float, float, str]]:
    if not path.exists():
        return []
    rows: list[tuple[str, int, int, int, int, float, float, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [x.strip() for x in line.strip("|").split("|")]
        if len(parts) != 8:
            continue
        rel, tp_raw, fp_raw, new_raw, fn_raw, p_raw, r_raw, date = parts
        try:
            rows.append(
                (
                    rel,
                    int(tp_raw),
                    int(fp_raw),
                    int(new_raw),
                    int(fn_raw),
                    float(p_raw),
                    float(r_raw),
                    date,
                )
            )
        except ValueError:
            continue
    return rows


def _write_trend(
    *,
    path: Path,
    release: str,
    tp: int,
    fp: int,
    new: int,
    fn: int,
    precision: float,
    recall: float,
    generated_at: str,
) -> None:
    rows = [row for row in _parse_trend_rows(path) if row[0] != release]
    rows.append((release, tp, fp, new, fn, precision, recall, generated_at.split("T", 1)[0]))
    indexed_rows = list(enumerate(rows))

    def _trend_sort_key(item: tuple[int, tuple[str, int, int, int, int, float, float, str]]) -> tuple[object, ...]:
        idx, row = item
        parsed = _parse_semver_release(row[0])
        if parsed is None:
            # Preserve insertion order for non-semver labels (e.g. main/nightly).
            return (1, idx)
        # Semantic ordering for version releases (e.g., v0.2.10 after v0.2.9).
        return (0, parsed[0], parsed[1], parsed[2], idx)

    indexed_rows.sort(key=_trend_sort_key)
    rows = [row for _, row in indexed_rows]

    lines = [
        "# Cairo Auditor Issue #32 Trend",
        "",
        "Release-over-release metrics against frozen issue #32 external gold benchmark.",
        "",
        "Precision is computed as `TP / (TP + FP + NEW)`.",
        "",
        "| Release | TP | FP | NEW | FN | Precision | Recall | Date |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for rel, tp_v, fp_v, new_v, fn_v, p_v, r_v, date in rows:
        lines.append(
            f"| {rel} | {tp_v} | {fp_v} | {new_v} | {fn_v} | {p_v:.3f} | {r_v:.3f} | {date} |"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score deterministic findings against frozen Issue #32 external gold benchmark."
    )
    parser.add_argument("--gold", required=True)
    parser.add_argument("--findings", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--trend-md", required=True)
    parser.add_argument("--output-fn-jsonl", default="")
    parser.add_argument("--output-fp-jsonl", default="")
    parser.add_argument("--min-precision", type=float, default=0.0)
    parser.add_argument("--min-recall", type=float, default=0.0)
    parser.add_argument("--min-class-recall", type=float, default=0.0)
    args = parser.parse_args()

    gold_path = Path(args.gold)
    findings_path = Path(args.findings)
    out_md = Path(args.output_md)
    out_json = Path(args.output_json)
    trend_md = Path(args.trend_md)

    gold_rows = load_gold(gold_path)
    if not gold_rows:
        raise ValueError(f"{gold_path}: gold set is empty")

    finding_rows = load_findings(findings_path)

    positive_rows = [row for row in gold_rows if row.expected_detect]
    if not positive_rows:
        raise ValueError(f"{gold_path}: no expected_detect=true rows")

    negative_rows = [row for row in gold_rows if not row.expected_detect]

    gold_lookup = {row.key: row for row in gold_rows}
    positive_keys = {row.key for row in positive_rows}
    negative_keys = {row.key for row in negative_rows}
    scoped_files = {(row.repo, row.ref, row.file) for row in gold_rows}

    scoped_predictions = [
        row
        for row in finding_rows
        if (row.repo, row.ref, row.file) in scoped_files
    ]
    scoped_pred_keys = {row.key for row in scoped_predictions}

    tp_keys = positive_keys & scoped_pred_keys
    fn_keys = positive_keys - scoped_pred_keys
    fp_gold_negative = scoped_pred_keys & negative_keys
    new_keys = scoped_pred_keys - positive_keys - negative_keys
    fp_keys = fp_gold_negative

    tp_rows = [gold_lookup[key] for key in tp_keys]
    fn_rows = [gold_lookup[key] for key in fn_keys]

    prediction_lookup = {row.key: row for row in scoped_predictions}
    fp_rows = [prediction_lookup[key] for key in fp_keys]
    new_rows = [prediction_lookup[key] for key in new_keys]

    tp = len(tp_rows)
    fp = len(fp_rows)
    new = len(new_rows)
    fn = len(fn_rows)
    precision = _precision(tp, fp + new)
    recall = _recall(tp, fn)

    per_class_total: dict[str, int] = defaultdict(int)
    per_class_tp: dict[str, int] = defaultdict(int)
    for row in positive_rows:
        per_class_total[row.class_id] += 1
    for row in tp_rows:
        per_class_tp[row.class_id] += 1

    class_recall = {
        class_id: _recall(per_class_tp.get(class_id, 0), per_class_total[class_id] - per_class_tp.get(class_id, 0))
        for class_id in sorted(per_class_total)
    }
    class_violations = [
        {"class_id": class_id, "recall": value}
        for class_id, value in sorted(class_recall.items())
        if value < args.min_class_recall
    ]

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    markdown = _render_markdown(
        release=args.release,
        generated_at=generated_at,
        gold_path=gold_path,
        findings_path=findings_path,
        tp_rows=tp_rows,
        fn_rows=fn_rows,
        fp_rows=fp_rows,
        new_rows=new_rows,
        scoped_predictions=scoped_predictions,
        class_recall=class_recall,
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown + "\n", encoding="utf-8")

    summary = {
        "release": args.release,
        "generated_at": generated_at,
        "gold_count": len(gold_rows),
        "gold_positive_count": len(positive_rows),
        "gold_negative_count": len(negative_rows),
        "scoped_prediction_count": len(scoped_predictions),
        "tp": tp,
        "fp": fp,
        "new": new,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "min_precision": args.min_precision,
        "min_recall": args.min_recall,
        "min_class_recall": args.min_class_recall,
        "class_recall": class_recall,
        "class_violations": class_violations,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.output_fn_jsonl:
        fn_path = Path(args.output_fn_jsonl)
        fn_path.parent.mkdir(parents=True, exist_ok=True)
        with fn_path.open("w", encoding="utf-8") as handle:
            for row in sorted(fn_rows, key=lambda item: item.finding_id):
                handle.write(
                    json.dumps(
                        {
                            "finding_id": row.finding_id,
                            "repo": row.repo,
                            "ref": row.ref,
                            "file": row.file,
                            "class_id": row.class_id,
                            "expected_detect": row.expected_detect,
                            "rationale": row.rationale,
                        },
                        ensure_ascii=True,
                    )
                    + "\n"
                )

    if args.output_fp_jsonl:
        fp_path = Path(args.output_fp_jsonl)
        fp_path.parent.mkdir(parents=True, exist_ok=True)
        with fp_path.open("w", encoding="utf-8") as handle:
            for row in sorted(fp_rows, key=lambda item: (item.repo, item.file, item.class_id)):
                handle.write(
                    json.dumps(
                        {
                            "repo": row.repo,
                            "ref": row.ref,
                            "file": row.file,
                            "class_id": row.class_id,
                            "predicted_detect": True,
                        },
                        ensure_ascii=True,
                    )
                    + "\n"
                )

    _write_trend(
        path=trend_md,
        release=args.release,
        tp=tp,
        fp=fp,
        new=new,
        fn=fn,
        precision=precision,
        recall=recall,
        generated_at=generated_at,
    )

    print(
        json.dumps(
            {
                "release": args.release,
                "tp": tp,
                "fp": fp,
                "new": new,
                "fn": fn,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "output_md": out_md.as_posix(),
                "output_json": out_json.as_posix(),
                "trend_md": trend_md.as_posix(),
            },
            ensure_ascii=True,
        )
    )

    if precision < args.min_precision or recall < args.min_recall:
        return 1
    if class_violations:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
