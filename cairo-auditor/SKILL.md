---
name: cairo-auditor
description: Runs a security audit workflow for Cairo/Starknet contracts with pre-merge and pre-release vulnerability discovery, triage, and remediation planning.
allowed-tools: [Bash, Read, Glob, Grep, Task]
---

# Cairo Auditor

Workflow skill for systematic Cairo contract security review.

## When to Use

- Reviewing contract changes before merge.
- Performing release-gate security checks.
- Triaging suspicious Cairo/Starknet patterns from code review or incidents.

## When NOT to Use

- Writing new contract features from scratch.
- Deployment-only tasks.
- SDK or protocol operation guides.

## Rationalizations to Reject

- "Tests pass so this is safe."
- "This pattern is standard in EVM so it is safe in Cairo."
- "The edge case is impossible in production."
- "We can skip replay/domain checks because signatures are temporary."

## Modes

- `default`: whole-package review using scoped file discovery.
- `deep`: default + adversarial reasoning pass + strict false-positive gate.
- `targeted`: explicit file-path review for fast PR iteration.

## Workflow

1. Discover in-scope Cairo files.
2. Run vectorized scans using vulnerability patterns in `references/vulnerability-db/`.
3. Correlate with historical findings in `../datasets/normalized/findings/`.
4. Prefer distilled classes from `../datasets/distilled/vuln-cards/` when available.
5. Merge and deduplicate findings by root cause.
6. Run false-positive verification gate.
7. Emit prioritized report with remediation guidance and test requirements.

## Reporting Contract

Each finding must include:

- `finding_id`
- `source_audit_id`
- `project`
- `auditor`
- `date`
- `severity_original`
- `severity_normalized`
- `status`
- `contracts`
- `functions`
- `root_cause`
- `exploit_path`
- `trigger_condition`
- `vulnerable_snippet`
- `fixed_snippet`
- `recommendation`
- `test_that_catches_it`
- `false_positive_lookalikes`
- `tags`
- `source_pages`
- `confidence`
- `evidence_strength`
- `reproducibility`
- `notes`

## Evidence Sources

- canonical patterns: `references/vulnerability-db/`
- audit-derived records: `../datasets/normalized/findings/`
- distilled security cards: `../datasets/distilled/vuln-cards/`
- evaluator regressions: `../evals/cases/`

## Output Rule

Only report actionable findings with confidence >= medium unless `deep` mode is requested.
