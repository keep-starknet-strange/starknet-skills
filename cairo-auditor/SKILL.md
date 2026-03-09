---
name: cairo-auditor
description: Systematic Cairo/Starknet security audit workflow with deterministic preflight, parallel vector specialists, adversarial reasoning, and strict false-positive gating.
allowed-tools: [Bash, Read, Glob, Grep, Task]
---

# Cairo Auditor

## When to Use

- Security review for Cairo/Starknet contracts before merge.
- Release-gate audits for account/session/upgrade critical paths.
- Triage of suspicious findings from CI, reviewers, or external reports.

## When NOT to Use

- Feature implementation tasks.
- Deployment-only ops.
- SDK/tutorial requests.

## Rationalizations to Reject

- "Tests passed, so it is secure."
- "This is normal in EVM, so Cairo is the same."
- "It needs admin privileges, so it is not a vulnerability."
- "We can ignore replay or nonce edges for now."

## Modes

- `default`: full in-scope scan with four specialist vector passes.
- `deep`: default + adversarial exploit-path pass.
- `targeted`: explicit file set, same validation gate, faster iteration.

## Orchestration (4 Turns)

### Turn 1: Discover

1. Determine mode (`default`, `deep`, `targeted`).
2. Discover in-scope `.cairo` files; exclude tests/mocks/examples/vendor/generated paths.
3. Run deterministic preflight checks to identify likely classes (upgrade/auth/session/external-call).

### Turn 2: Prepare

1. Load specialist instructions and references:
   - `agents/vector-scan.md`
   - `references/judging.md`
   - `references/report-formatting.md`
2. Build four specialist bundles. Each bundle includes:
   - full in-scope Cairo code,
   - one vector partition:
     - `references/attack-vectors/attack-vectors-1.md`
     - `references/attack-vectors/attack-vectors-2.md`
     - `references/attack-vectors/attack-vectors-3.md`
     - `references/attack-vectors/attack-vectors-4.md`
3. Record line counts per bundle for parallel chunk-reading instructions.

### Turn 3: Spawn

1. Spawn 4 parallel vector specialists (one per bundle) following `agents/vector-scan.md`.
2. In `deep` mode, spawn `agents/adversarial.md` in parallel.
3. Each specialist must:
   - triage vectors (`Skip/Borderline/Survive`),
   - apply FP gate from `references/judging.md`,
   - output only findings formatted by `references/report-formatting.md`.

### Turn 4: Report

1. Merge outputs.
2. Deduplicate by root cause (keep higher-confidence variant).
3. Run composability pass when multiple findings interact.
4. If Scarb/Sierra is available, run Sierra confirmation for CEI and upgrade classes.
5. Sort by priority and confidence.
6. Emit actionable findings + required regression tests.

## Reporting Contract

Each finding must include:

- `class_id`
- `severity`
- `confidence`
- `entry_point`
- `attack_path`
- `guard_analysis`
- `affected_files`
- `recommended_fix`
- `required_tests`

## Evidence Priority

1. `references/vulnerability-db/`
2. `references/attack-vectors/`
3. `../datasets/normalized/findings/`
4. `../datasets/distilled/vuln-cards/`
5. `../evals/cases/`

## Output Rule

- Report only findings that pass FP gate.
- Findings below confidence threshold may be listed as low-confidence notes without a fix block.
