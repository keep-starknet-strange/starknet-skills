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

- `score_external_triage.py` scores human-reviewed external scan findings:
  - label pack:
    - `evals/reports/data/external-repo-scan-low-profile-2026-03-08-v2.labels.jsonl`
  - computes TP/FP/FN/TN, precision, recall from `tp`/`fp` outcomes
  - emits release scorecard (`evals/scorecards/v*.md`) and trend table
  - enforces minimum precision/recall thresholds in CI

- `benchmark_contract_skills.py` runs deterministic contract-oriented skill checks:
  - case pack:
    - `evals/cases/contract_skill_benchmark.jsonl`
  - fixture projects:
    - `evals/contracts/secure_owned_vault/`
    - `evals/contracts/insecure_owned_vault/`
    - `evals/contracts/secure_upgrade_controller/`
    - `evals/contracts/insecure_upgrade_controller/`
    - `evals/contracts/secure_math_patterns/`
    - `evals/contracts/insecure_math_patterns/`
  - checks:
    - `scarb build`
    - `snforge test`
    - source-level must-match / must-not-match regex assertions
    - security-class coverage reporting (`auth`, `timelock`, `upgrade_safety`, etc.)
  - emits scorecard markdown and enforces precision/recall thresholds
  - supports reportable-gate thresholds (`--min-evaluated`, `--enforce-min-evaluated`)
  - defaults to `60` minimum evaluated cases for reportable interpretation
  - fails on zero evaluated cases unless `--allow-empty-evaluated` is explicitly set

- `mutation_test_contract_benchmark.py` validates rule strength by mutating secure fixtures:
  - removes/flips selected guards in secure fixtures
  - runs benchmark after each mutation
  - requires benchmark failure for every mutation (guard-regression detection)

- `render_contract_benchmark_trend.py` builds release trend reporting for contract benchmarks:
  - scans `evals/scorecards/v*-contract-skill-benchmark.md`
  - marks releases as reportable/non-reportable via minimum case policy
  - tracks consecutive reportable releases for KPI publication readiness
  - emits `evals/scorecards/contract-skill-benchmark-trend.md`

- `check_contract_kpi_release_gate.py` enforces KPI publication policy:
  - requires minimum consecutive reportable releases
  - requires explicit security reviewer signoff for latest release
  - emits `evals/scorecards/contract-kpi-publication-gate.md`
