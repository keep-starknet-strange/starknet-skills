# Benchmark Workflow

1. Run auditor and contract benchmark scripts with explicit thresholds.
2. Review precision/recall and fail messages.
3. Compare against prior scorecards for regression detection.
4. If save is requested, rerun benchmarks with `--output` paths under `evals/scorecards/`.
5. Document benchmark deltas in the PR description.
