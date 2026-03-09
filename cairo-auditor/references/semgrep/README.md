# Semgrep Adapter Rules (Cairo Auditor)

This directory contains optional Semgrep rules used as an auxiliary detector layer.

Design goals:
- fail-open in CI/local runs when Semgrep is unavailable,
- fast pattern coverage for high-signal classes,
- no replacement for deterministic detector and FP gate workflow.

Runner:
- `scripts/quality/run_semgrep_cairo.py`

Default config:
- `cairo-auditor/references/semgrep/cairo-auditor-rules.yaml`
