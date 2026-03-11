# Benchmark Workflow

1. Run auditor benchmark:
   `python scripts/quality/benchmark_cairo_auditor.py --cases evals/cases/cairo_auditor_benchmark.jsonl --output /tmp/bench-auditor.md --min-precision 0.90 --min-recall 0.90`
2. Run contract benchmark:
   `python scripts/quality/benchmark_contract_skills.py --cases evals/cases/contract_skill_benchmark.jsonl --output /tmp/bench-contracts.md --min-precision 0.95 --min-recall 0.95`
3. If persistence is requested, rerun both commands with `--save`.
4. Read prior files in `evals/scorecards/` and compare for regression detection.
5. Document benchmark deltas in the PR description.
