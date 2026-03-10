---
name: validate
description: Run all local quality checks before submitting a PR
allowed-tools: Bash, Read, Grep, Glob
---

Run all local quality checks and report results:

1. `python scripts/quality/validate_skills.py`
2. `python scripts/quality/validate_marketplace.py`
3. `ruff check scripts/`

Report pass/fail for each check with specific errors. If a check fails, suggest the fix but ask before applying.
