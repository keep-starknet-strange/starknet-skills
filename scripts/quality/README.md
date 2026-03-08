# Quality Scripts

- `validate_skills.py` enforces repository SKILL.md contract checks:
  - required frontmatter (`name`, `description`)
  - valid YAML frontmatter parsing (PyYAML)
  - kebab-case and max length for `name`
  - third-person trigger-style `description`
  - `When to Use` / `When NOT to Use` sections for module skills
  - `Rationalizations to Reject` for audit/security skills
  - max 500 lines per SKILL.md
  - one-level markdown link depth for progressive disclosure
  - markdown link target existence and in-repo resolution

- `parity_check.py` runs local parity checks against baseline quality bars:
  - skill contract validator pass
  - required governance/entry files present
  - README install/use onboarding present
  - `cairo-testing` docs match installed `snforge` CLI behavior
  - `cairo-toolchain` docs match installed `sncast` CLI behavior
  - explicit Trail of Bits-style authoring parity:
    - required sections
    - quick start in each module skill
    - progressive-disclosure markdown links from entry skills

- `benchmark_cairo_auditor.py` runs a deterministic benchmark on Cairo snippets:
  - case packs:
    - `evals/cases/cairo_auditor_benchmark.jsonl`
    - `evals/cases/cairo_auditor_realworld_benchmark.jsonl`
  - class-level TP/FP/FN/TN metrics
  - scorecard output to `evals/scorecards/*.md`
  - precision/recall threshold gate for CI
  - per-class recall threshold gate for CI

- `score_external_triage.py` scores human-reviewed external scan findings:
  - label pack:
    - `evals/reports/data/external-repo-scan-low-profile-2026-03-08-v2.labels.jsonl`
  - computes TP/FP/FN/TN, precision, recall from `tp`/`fp` outcomes
  - emits release scorecard (`evals/scorecards/v*.md`) and trend table
  - enforces minimum precision/recall thresholds in CI

- `scan_external_repos.py` runs detector sweeps against public Cairo repos:
  - clones target repositories at provided refs
  - scans production `.cairo` files (test/mock paths excluded by default)
  - emits machine-readable scan artifact + optional markdown summary
  - isolates per-repo clone/build failures (best-effort scan continues)

- `compare_scan_artifacts.py` compares two external scan JSON artifacts:
  - emits class-level deltas + added/removed finding sets
  - writes portable repo-relative paths (no local machine path leakage)

- `check_manual_gold_recall.py` validates detector recall against frozen manual positives:
  - gold set:
    - `evals/reports/data/manual-19-gold.jsonl`
  - computes overall and per-class recall
  - enforces recall thresholds in CI

- `sierra_parallel_signal.py` computes a Sierra-native auxiliary signal:
  - builds Scarb projects for target repos
  - scans generated Sierra artifacts for external/state marker frequencies
  - emits side-by-side comparison context with detector hit counts
