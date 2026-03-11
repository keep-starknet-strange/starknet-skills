---
name: validate
description: Run all local quality checks before submitting a PR
allowed-tools: Bash, Read, Grep, Glob
---

# Validate Skill

## Quick Start

1. Run skill/router validation:
   `python3 scripts/quality/validate_skills.py`
2. Run marketplace metadata validation:
   `python3 scripts/quality/validate_marketplace.py`
3. Run Python lint:
   `ruff check scripts/`
4. Report pass/fail per check with concrete errors.
5. Follow the full workflow: [Validation Workflow](./workflow.md)

## When to Use

- Before opening or merging any PR.
- After changing SKILL.md, references, scripts, or site generation code.

## When NOT to Use

- You need dataset schema validation only (use audit-pipeline validators).
- Required dependencies are missing and checks cannot run.
