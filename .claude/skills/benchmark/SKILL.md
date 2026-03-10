---
name: benchmark
description: Run evaluation benchmarks and report precision/recall
allowed-tools: Bash, Read
argument-hint: [--save]
---

Run benchmarks and report results:

1. `python scripts/quality/benchmark_cairo_auditor.py --cases evals/cases/cairo_auditor_benchmark.jsonl --output /tmp/bench-auditor.md`
2. `python scripts/quality/benchmark_contract_skills.py --cases evals/cases/contract_skill_benchmark.jsonl --output /tmp/bench-contracts.md --min-precision 0.95 --min-recall 0.95`
3. Report precision/recall for each
4. Flag regressions below threshold (auditor: 0.90, contracts: 0.95)
5. If $ARGUMENTS contains "--save", copy to `evals/scorecards/`
