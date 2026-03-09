# Quality Scripts

- `validate_skills.py`: skill contract/lint checks for SKILL.md structure and links.
- `parity_check.py`: required repository parity and local tool checks.

## Cairo Auditor Benchmarks

- `benchmark_cairo_auditor.py`
  - deterministic detector benchmark over JSONL case packs
  - emits markdown scorecards
  - enforces precision/recall + per-class recall thresholds
- `score_external_triage.py`
  - computes precision/recall from manually labeled external findings
  - emits release scorecard + trend table
  - tracks labeled coverage against full findings and emits unlabeled backlog queue
- `check_manual_gold_recall.py`
  - validates recall against frozen manual gold findings
  - emits markdown/json recall reports
- `audit_local_repo.py`
  - single-entry local repo audit command
  - runs deterministic detectors on local `.cairo` files
  - optionally runs Sierra confirmation (`--sierra-confirm [--allow-build]`)

## External Scan Tooling

- `scan_external_repos.py`
  - clones configured repos and scans production-scoped `.cairo` files
  - emits JSON/JSONL/markdown artifacts
  - isolates per-repo failures so one repo does not abort the full scan
- `compare_scan_artifacts.py`
  - compares two scan JSON artifacts
  - outputs class/file deltas and added/removed findings

## LLM and Sierra Signals

- `run_llm_eval.py`
  - held-out LLM evaluation tier via GitHub Models API
- `sierra_parallel_signal.py`
  - Sierra-native auxiliary confirmation pass
  - resolves workspace/member target directories via `scarb metadata`
  - parses `.sierra.json`, `.starknet_artifacts.json`, and `*.contract_class.json`
  - emits function-order signal (`external_call` before `state_write`) for CEI triage

## Quick Start

Run a local deterministic audit:

```bash
python scripts/quality/audit_local_repo.py \
  --repo-root /path/to/your/cairo-repo \
  --scan-id local-audit \
  --output-json /path/to/output/local-audit.json \
  --output-md /path/to/output/local-audit.md
```

Run local audit + Sierra confirmation (build mode):

```bash
python scripts/quality/audit_local_repo.py \
  --repo-root /path/to/your/cairo-repo \
  --scan-id local-audit-sierra \
  --sierra-confirm \
  --allow-build \
  --output-json /path/to/output/local-audit-sierra.json \
  --output-md /path/to/output/local-audit-sierra.md
```

Warning: `--allow-build` may execute repository build steps/tooling.
Use build mode only on trusted code, or run in an isolated environment.

## Contract-Skill Benchmarks

- `benchmark_contract_skills.py`
  - deterministic contract fixture benchmark for authoring/testing/toolchain skills
  - validates build/test + regex assertions over secure/insecure fixtures
- `render_contract_benchmark_trend.py`
  - aggregates versioned contract benchmark scorecards into trend markdown
