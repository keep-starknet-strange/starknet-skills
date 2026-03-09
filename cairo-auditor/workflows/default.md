# Default Workflow

1. Discover in-scope Cairo files.
2. Prepare 4 specialist bundles (full code + one attack-vector partition each).
3. Run 4 vector specialists in parallel (triage -> deep pass -> FP gate).
4. Require report formatting contract (`references/report-formatting.md`) for every finding.
5. Merge and dedupe by root cause; run composability pass for interacting findings.
6. Run Sierra v3 per-finding confirmation when Scarb is available (`ir_confirmation`, `signal_quality`, `artifact_source`) using class-to-signal mapping; default to `unknown` for unmapped classes.
7. Emit improvement candidates sorted by `actionable` first, then confidence descending, with required regression tests.
