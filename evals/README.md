# Evaluations

Evaluation cases and scorecards for skill quality regression tracking.

## Structure

- `cases/`: held-out cases for detection and remediation quality.
- `heldout/`: explicit hold-out policy and reserved sets excluded from distillation.
- `reports/`: external repository scan reports and triage notes.
- `scorecards/`: run outputs and aggregate metrics by version.

## Minimum Gate

For changes affecting security detection behavior:

- Baseline is the latest `main` scorecard for the same module and case set.
- High/Critical recall must not regress on `evals/cases/` + documented held-out set.
- False-positive rate must not increase by more than +1.0 percentage point and must remain <= 2.0% absolute.

## CI Tiers

- Per-PR (`quality.yml`): schema validation, manifest uniqueness checks, and held-out leakage policy checks.
- Full tier (`full-evals.yml`): parity checks + held-out leakage guard + deterministic benchmarks; run on schedule, workflow-dispatch, or pull requests labeled `full-evals`.
- LLM held-out tier (`full-evals.yml`): runs with GitHub Models via `GITHUB_TOKEN` and `permissions: models: read`, enforcing precision/recall gates on a separate held-out case pack.
  - The workflow probes GitHub Models first; if model access is not available for the repo/org token, the LLM tier is skipped and deterministic gates still run.

## Benchmark Runner

Run Cairo benchmark and generate a scorecard:

```bash
python scripts/quality/benchmark_cairo_auditor.py \
  --cases evals/cases/cairo_auditor_benchmark.jsonl \
  --output evals/scorecards/v0.2.0-cairo-auditor-benchmark.md \
  --min-precision 0.90 \
  --min-recall 0.90
```

Run the real-world Cairo corpus benchmark (public snippets + normalized audit findings):

```bash
python scripts/quality/benchmark_cairo_auditor.py \
  --cases evals/cases/cairo_auditor_realworld_benchmark.jsonl \
  --output evals/scorecards/v0.2.0-cairo-auditor-realworld-benchmark.md \
  --min-precision 0.90 \
  --min-recall 0.90
```

Run LLM held-out eval (GitHub Models + `GITHUB_TOKEN`):

```bash
GITHUB_TOKEN=... python scripts/quality/run_llm_eval.py \
  --cases evals/heldout/cairo_auditor_llm_eval_cases.jsonl \
  --output-json evals/scorecards/v0.2.0-cairo-auditor-llm-heldout.json \
  --output-md evals/scorecards/v0.2.0-cairo-auditor-llm-heldout.md \
  --model openai/gpt-4o \
  --min-precision 0.75 \
  --min-recall 0.75
```
