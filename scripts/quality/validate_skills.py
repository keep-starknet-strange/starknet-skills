#!/usr/bin/env python3
"""Repository-level SKILL.md quality checks.

This validator enforces a minimal, deterministic subset of modern skill-authoring
standards for the starknet-skills repository.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")


def parse_frontmatter(text: str) -> tuple[dict[str, str], int] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break

    if end is None:
        return None

    raw = lines[1:end]
    parsed: dict[str, str] = {}
    for line in raw:
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip().strip('"')

    return parsed, end + 1


def check_skill(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) > 500:
        errors.append(f"{path}: exceeds 500 lines ({len(lines)})")

    if "/Users/" in text or "C:\\Users\\" in text:
        errors.append(f"{path}: contains absolute local filesystem paths")

    parsed = parse_frontmatter(text)
    if parsed is None:
        errors.append(f"{path}: missing valid YAML frontmatter block")
        return errors

    frontmatter, body_start = parsed
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")

    if not name:
        errors.append(f"{path}: frontmatter missing 'name'")
    else:
        if len(name) > 64:
            errors.append(f"{path}: skill name too long (>64): {name}")
        if not SKILL_NAME_RE.match(name):
            errors.append(f"{path}: skill name is not kebab-case: {name}")

    if not description:
        errors.append(f"{path}: frontmatter missing 'description'")

    # For non-root skills, enforce folder/name consistency and required sections.
    if path.parent != ROOT:
        if name and path.parent.name != name:
            errors.append(
                f"{path}: directory name '{path.parent.name}' must match frontmatter name '{name}'"
            )

        body = "\n".join(lines[body_start:])
        if "## When to Use" not in body:
            errors.append(f"{path}: missing '## When to Use' section")
        if "## When NOT to Use" not in body:
            errors.append(f"{path}: missing '## When NOT to Use' section")

        if "auditor" in path.as_posix() and "## Rationalizations to Reject" not in body:
            errors.append(f"{path}: security/audit skill missing '## Rationalizations to Reject'")

        # Enforce one-level deep markdown links for progressive disclosure.
        for m in LINK_RE.finditer(body):
            target = m.group(1)
            if target.startswith("http://") or target.startswith("https://"):
                continue
            normalized = target.split("#", 1)[0]
            depth = normalized.count("/")
            if depth > 1:
                errors.append(
                    f"{path}: markdown link '{target}' is deeper than one level from SKILL.md"
                )

    return errors


def main() -> int:
    skill_files = sorted(
        p
        for p in ROOT.rglob("SKILL.md")
        if ".venv" not in p.as_posix() and "/tmp/" not in p.as_posix()
    )

    all_errors: list[str] = []
    for path in skill_files:
        all_errors.extend(check_skill(path))

    if all_errors:
        print("SKILL validation failed:")
        for e in all_errors:
            print(f"- {e}")
        return 1

    print(f"OK: validated {len(skill_files)} SKILL.md files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
