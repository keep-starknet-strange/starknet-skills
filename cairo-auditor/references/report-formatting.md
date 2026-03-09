# Report Formatting

Use this exact structure for each finding.

## Finding Template

`[{confidence}] **{title}**`

`Location: {file}:{line}`

`Class: {class_id} | Category: {category} | Actionability: {actionability}`

`Needs PoC: {needs_poc} | IR: {ir_confirmation} [{signal_quality}] via {artifact_source}`

`Description:`

- One paragraph explaining exploit path and impact.

`Recommended improvement:`

```diff
- vulnerable line(s)
+ fixed line(s)
```

`Required tests:`

- Regression test that reproduces the vulnerable path.
- Guard test that proves fix blocks exploit.

## Actionability Rules

- `actionable`: concrete, reviewable improvement path exists.
- `low_confidence`: pattern matched but proof path is incomplete; report without diff block.
- `suppressed`: FP gate failed; do not report.

## Confidence Threshold Rule

- Findings with confidence `<75` can be reported, but omit the `Recommended improvement` diff block.
- Findings that fail FP gate must be dropped and not reported.
- Severity labels (`high/critical`) are manual signoff-only metadata and should never be auto-assigned by deterministic scanners.

## Deduplication Rule

When two findings share the same root cause, keep one:

- keep higher confidence,
- merge broader attack path details,
- keep a single fix/test block.
