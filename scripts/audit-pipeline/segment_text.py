#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

NUMERIC_HEADING = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.+?)\s*$")
ID_HEADING = re.compile(r"^\s*([A-Z]{1,3}-\d{2})\s+(.+?)\s*$")


@dataclass
class Seg:
    heading_key: str
    heading_title: str
    start_page: int
    lines: list[str]


def detect_heading(line: str) -> tuple[str, str] | None:
    m = ID_HEADING.match(line)
    if m:
        if "..." in line or ". . ." in line:
            return None
        return (m.group(1), m.group(2).strip())
    m = NUMERIC_HEADING.match(line)
    if m:
        if "..." in line or ". . ." in line or re.search(r"\.\s+\d+\s*$", line):
            return None
        return (m.group(1), m.group(2).strip())
    return None


def segment_text(text: str) -> list[dict]:
    pages = text.split("\f")
    segments: list[dict] = []
    current: Seg | None = None
    current_page = 1

    for page_idx, page in enumerate(pages, start=1):
        current_page = page_idx
        for raw in page.splitlines():
            line = raw.rstrip()
            heading = detect_heading(line)
            if heading:
                if current and current.lines:
                    segments.append(
                        {
                            "heading_key": current.heading_key,
                            "heading_title": current.heading_title,
                            "start_page": current.start_page,
                            "end_page": current_page,
                            "content": "\n".join(current.lines).strip(),
                        }
                    )
                current = Seg(heading_key=heading[0], heading_title=heading[1], start_page=page_idx, lines=[line])
            elif current is not None:
                current.lines.append(line)

    if current and current.lines:
        segments.append(
            {
                "heading_key": current.heading_key,
                "heading_title": current.heading_title,
                "start_page": current.start_page,
                "end_page": current_page,
                "content": "\n".join(current.lines).strip(),
            }
        )

    return segments


def seg_type(heading_key: str) -> str:
    if ID_HEADING.match(f"{heading_key} x"):
        return "finding"
    if re.match(r"^\d+\.\d+\.\d+$", heading_key):
        return "finding_candidate"
    return "section"


def is_toc_noise(seg: dict) -> bool:
    title = seg["heading_title"]
    content = seg["content"]
    dotted_title = ("..." in title) or (". . ." in title)
    short_content = len(content.splitlines()) <= 2
    early_page = seg["start_page"] <= 3
    has_detail_markers = any(
        marker in content for marker in ("File(s):", "Description:", "Recommendation", "Status:")
    )
    return dotted_title and short_content and early_page and not has_detail_markers


def is_low_signal(seg: dict) -> bool:
    title = seg["heading_title"].lower()
    if "tests output" in title or "compilation output" in title:
        return True
    if ID_HEADING.match(f"{seg['heading_key']} x"):
        if "File(s):" not in seg["content"] and seg["start_page"] <= 5:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Segment extracted audit text by headings")
    parser.add_argument("--audit-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    segments = segment_text(in_path.read_text(encoding="utf-8", errors="ignore"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        idx = 0
        for seg in segments:
            if is_toc_noise(seg):
                continue
            if is_low_signal(seg):
                continue
            idx += 1
            seg["segment_id"] = f"{args.audit_id}:{idx:04d}"
            seg["audit_id"] = args.audit_id
            seg["segment_type"] = seg_type(seg["heading_key"])
            f.write(json.dumps(seg, ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
