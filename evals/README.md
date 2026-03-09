# Evaluations

Evaluation cases and scorecards for skill quality regression tracking.

## Structure

- `cases/`: held-out cases for detection and remediation quality.
- `contracts/`: runnable Cairo fixture projects for contract skill checks.
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
- External triage tier (`full-evals.yml`): scores human-labeled external findings (`tp`/`fp`) and emits release scorecards + trend markdown.
- Manual gold tier (`full-evals.yml`): checks recall against the frozen `manual-19` positive set and enforces per-class recall floors.

## Benchmark Runner

Run Cairo benchmark and generate a scorecard:

```bash
python scripts/quality/benchmark_cairo_auditor.py \
  --cases evals/cases/cairo_auditor_benchmark.jsonl \
  --output evals/scorecards/v0.2.0-cairo-auditor-benchmark.md \
  --min-precision 0.90 \
  --min-recall 0.90 \
  --min-class-recall 0.90
```

Run contract skill benchmark (compiles/tests fixture contracts and enforces policy assertions):

```bash
python scripts/quality/benchmark_contract_skills.py \
  --cases evals/cases/contract_skill_benchmark.jsonl \
  --output evals/scorecards/v0.4.0-contract-skill-benchmark.md \
  --version v0.4.0 \
  --min-precision 0.95 \
  --min-recall 0.95 \
  --min-evaluated 22 \
  --enforce-min-evaluated \
  --require-tools
```

Interpretation guidance for contract benchmark metrics:

- If evaluated cases are fewer than `22`, treat results as a deterministic smoke gate only.
- Smoke-gate pass means fixture checks are wired correctly and caught seeded regressions.
- Smoke-gate pass does **not** justify broad claims like "overall skill quality is 100%."
- Publishable KPI status requires at least `2` consecutive reportable releases (tracked in trend scorecard).

Render contract benchmark trend report:

```bash
python scripts/quality/render_contract_benchmark_trend.py \
  --scorecards-glob 'evals/scorecards/v*-contract-skill-benchmark.md' \
  --output evals/scorecards/contract-skill-benchmark-trend.md \
  --min-cases 22 \
  --min-consecutive 2
```

Run the real-world Cairo corpus benchmark (public snippets + normalized audit findings):

```bash
python scripts/quality/benchmark_cairo_auditor.py \
  --cases evals/cases/cairo_auditor_realworld_benchmark.jsonl \
  --output evals/scorecards/v0.2.0-cairo-auditor-realworld-benchmark.md \
  --min-precision 0.90 \
  --min-recall 0.90 \
  --min-class-recall 0.90
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

Run external triage scoring (human-labeled external findings):

```bash
python scripts/quality/score_external_triage.py \
  --labels evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09-v5.labels.jsonl \
  --findings evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09-v5.findings.jsonl \
  --release v0.2.0 \
  --output-md evals/scorecards/v0.2.0-cairo-auditor-external-triage.md \
  --output-json evals/scorecards/v0.2.0-cairo-auditor-external-triage.json \
  --output-unlabeled-jsonl evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09-v5.unlabeled.jsonl \
  --trend-md evals/scorecards/cairo-auditor-external-trend.md \
  --min-precision 0.70 \
  --min-recall 0.90 \
  --min-labeled-coverage 0.90
```

Run manual-19 gold recall check:

```bash
python scripts/quality/check_manual_gold_recall.py \
  --gold evals/reports/data/manual-19-gold.jsonl \
  --findings evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09-v5.findings.jsonl \
  --output-md evals/scorecards/v0.2.0-cairo-auditor-manual-19-gold-recall.md \
  --output-json evals/scorecards/v0.2.0-cairo-auditor-manual-19-gold-recall.json \
  --min-recall 0.90 \
  --min-class-recall 0.75
```

Run a local repo audit with one command:

```bash
python scripts/quality/audit_local_repo.py \
  --repo-root /path/to/your/cairo-repo \
  --scan-id local-audit \
  --output-json /tmp/local-audit.json \
  --output-md /tmp/local-audit.md
```

Run Sierra confirmation on low-profile external scan set (build mode):

```bash
python scripts/quality/sierra_parallel_signal.py \
  --scan-id sierra-parallel-low-profile-local \
  --repos-file evals/reports/data/external-repo-scan-low-profile-repos.txt \
  --detector-findings-jsonl evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09-v5.findings.jsonl \
  --allow-build \
  --scarb-timeout-seconds 240 \
  --output-json /tmp/sierra-parallel-low-profile.json \
  --output-md /tmp/sierra-parallel-low-profile.md
```
