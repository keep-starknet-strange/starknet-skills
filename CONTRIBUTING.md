# Contributing

## Quality Bar

Every change must satisfy both tests:

1. Would a strong stock model still get this wrong without this content?
2. Does this change improve deterministic quality outcomes (fewer misses, fewer false positives, better remediation quality)?

If both answers are not yes, do not add the content.

## Required Structure in Skill Files

Each `SKILL.md` must include:

- `When to Use`
- `When NOT to Use`

Security/audit skills must also include:

- `Rationalizations to Reject`

Keep entry skills short and link one level deep to `references/` and `workflows/`.

## Evaluation-Driven Changes

Skill changes that affect detection or remediation quality must include one of:

- New/updated case in `evals/cases/`
- Updated benchmark scorecard in `evals/scorecards/`

No merge without green quality gates:

- formatting/build/tests
- static analysis where applicable
- evaluator pass threshold

## Audit Data Handling

When ingesting external audits into `datasets/audits/`:

- redact confidential or client-identifying material
- preserve technical root cause and exploitability detail
- tag confidence and provenance for every finding
