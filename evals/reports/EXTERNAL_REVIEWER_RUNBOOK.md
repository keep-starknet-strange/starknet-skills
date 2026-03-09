# External Reviewer Runbook (Cairo Auditor)

This runbook standardizes external manual review so results are comparable release-over-release.

## Goal

Given deterministic scanner findings, reviewers decide:

- whether each alert is `tp` or `fp`,
- whether it is a `security_bug`, `design_tradeoff`, or `quality_smell`,
- whether it still needs PoC (`needs_poc=true`).

Severity (`critical/high/...`) is optional manual metadata only and must not be inferred by scanner output.

## Inputs Required

Maintainer provides:

1. Findings JSONL:
   - `evals/reports/data/<scan-id>.findings.jsonl`
2. Manual triage CSV:
   - `evals/reports/data/<scan-id>.manual-triage.csv`
3. Repo list + pinned refs:
   - `evals/packs/<pack>.txt` or explicit list

## Review Standard (Pashov-style FP gate)

For each candidate, confirm all 3 checks before marking true positive:

1. Concrete attack path exists (caller -> entry point -> state change -> impact).
2. Path is reachable by attacker class in scope.
3. No existing guard already blocks exploit path.

If any check fails, mark `manual_verdict=fp`.

## CSV Fields to Fill

In `<scan-id>.manual-triage.csv`, fill at least:

- `manual_verdict`: `tp` or `fp`
- `triage_category`: `security_bug` | `design_tradeoff` | `quality_smell`
- `needs_poc`: `true` or `false`
- `reviewer_1`: primary reviewer id/handle
- `reviewer_2`: secondary reviewer id/handle (strongly recommended)
- `manual_notes`: one concrete rationale with file-level evidence

Optional:

- `security_countable`: force include/exclude in security metric (`true`/`false`)
- `manual_severity`: `critical` | `high` | `medium` | `low` | `info`

## Category Policy

- `security_bug`: exploit path can violate security property or funds/safety invariants.
- `design_tradeoff`: intentional design/hardening concern; actionable but not always exploitable.
- `quality_smell`: maintainability/correctness smell without clear exploit path.

Recommended default:

- if uncertain exploitability, use `design_tradeoff` and `needs_poc=true`.

## Security Metric Inclusion Rule

A row is counted in `security_precision` when:

- `triage_category=security_bug`,
- `needs_poc=false`,
- dual signoff exists (`reviewer_1` and `reviewer_2`),
- unless explicitly overridden by `security_countable`.

## Convert Reviewed CSV to Labels JSONL

After reviewers complete CSV:

```bash
python3 scripts/quality/build_external_labels_from_triage_csv.py \
  --triage-csv evals/reports/data/<scan-id>.manual-triage.csv \
  --release v0.2.0 \
  --scan-id <scan-id> \
  --output-jsonl evals/reports/data/<scan-id>.labels.jsonl
```

Then score:

```bash
python3 scripts/quality/score_external_triage.py \
  --labels evals/reports/data/<scan-id>.labels.jsonl \
  --findings evals/reports/data/<scan-id>.findings.jsonl \
  --release v0.2.0 \
  --output-md evals/scorecards/v0.2.0-cairo-auditor-external-triage.md \
  --output-json evals/scorecards/v0.2.0-cairo-auditor-external-triage.json \
  --trend-md evals/scorecards/cairo-auditor-external-trend.md
```

## Reviewer Delivery Checklist

- [ ] Every row has `manual_verdict`
- [ ] Every row has rationale with code evidence
- [ ] Every row has `triage_category`
- [ ] Ambiguous rows set `needs_poc=true`
- [ ] Dual signoff filled for countable security rows

