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
