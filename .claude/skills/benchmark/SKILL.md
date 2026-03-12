---
name: benchmark
description: Run evaluation benchmarks and report precision/recall
allowed-tools: Bash, Read
argument-hint: [--save]
---

# Benchmark Skill

## Quick Start

1. Run auditor benchmark:
   `python3 scripts/quality/benchmark_cairo_auditor.py --cases evals/cases/cairo_auditor_benchmark.jsonl --output /tmp/bench-auditor.md --min-precision 0.90 --min-recall 0.90`
2. Run contract benchmark:
   `python3 scripts/quality/benchmark_contract_skills.py --cases evals/cases/contract_skill_benchmark.jsonl --output /tmp/bench-contracts.md --min-precision 0.95 --min-recall 0.95`
3. If `$ARGUMENTS` contains `--save`, append `--save` to both commands to copy scorecards into `evals/scorecards/`.
4. Report precision/recall and fail conditions per suite.
5. Follow the full workflow: [Benchmark Workflow](./workflow.md)

## When to Use

- You changed skills, references, datasets, or evaluation logic.
- You need comparable KPI numbers before/after a PR.

## When NOT to Use

- You only need schema/structure validation (use validate skill instead).
- Benchmark inputs or dependencies are missing.
