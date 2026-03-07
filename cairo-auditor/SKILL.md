---
name: cairo-auditor
description: Security audit workflow for Cairo/Starknet contracts. Use for pre-merge and pre-release vulnerability discovery, triage, and remediation planning.
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
3. Correlate with historical findings in `references/audit-findings/`.
4. Merge and deduplicate findings by root cause.
5. Run false-positive verification gate.
6. Emit prioritized report with remediation guidance and test requirements.

## Reporting Contract

Each finding must include:

- severity
- file/function location
- root cause
- exploit path
- fix recommendation
- required regression test

## Evidence Sources

- canonical patterns: `references/vulnerability-db/`
- audit-derived cases: `references/audit-findings/`
- evaluator regressions: `../../evals/cases/`

## Output Rule

Only report actionable findings with confidence >= medium unless `deep` mode is requested.
