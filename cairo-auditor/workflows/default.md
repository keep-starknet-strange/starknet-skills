# Default Workflow

1. Discover in-scope Cairo files.
2. Prepare 4 specialist bundles (full code + one attack-vector partition each).
3. Run 4 vector specialists in parallel (triage -> deep pass -> FP gate).
4. Require report formatting contract (`references/report-formatting.md`) for every finding.
5. Merge and dedupe by root cause; run composability pass for interacting findings.
6. Run Sierra v3 per-finding confirmation when Scarb is available (`ir_confirmation`, `signal_quality`, `artifact_source`) using class-to-signal mapping (detector class -> Sierra signal). If Scarb is unavailable, skip IR confirmation and keep `ir_confirmation=unknown`, `signal_quality=low`, `artifact_source=none`.
7. Emit improvement candidates with actionable findings first, then non-actionable findings; within each group sort by confidence descending, with required regression tests.
