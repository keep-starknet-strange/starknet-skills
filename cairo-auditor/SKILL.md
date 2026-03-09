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
2. Discover in-scope `.cairo` files and exclude tests/mocks/examples/vendor.
3. Run deterministic preflight context checks:
   - identify risky upgrade/auth/session/external-call surfaces quickly,
   - record likely classes before deep analysis.

### Turn 2: Prepare

1. Read specialist instructions:
   - `agents/vector-scan.md`
   - `references/judging.md`
2. Create 4 specialist bundles, each with:
   - full in-scope Cairo file set,
   - one attack-vector partition:
     - `references/attack-vectors/attack-vectors-1.md`
     - `references/attack-vectors/attack-vectors-2.md`
     - `references/attack-vectors/attack-vectors-3.md`
     - `references/attack-vectors/attack-vectors-4.md`

### Turn 3: Spawn

1. Run 4 parallel vector specialists (one per bundle).
2. In `deep` mode, run `agents/adversarial.md` in parallel as an additional pass.
3. Each specialist must produce findings that pass `references/judging.md`.

### Turn 4: Report

1. Merge specialist outputs.
2. Deduplicate by root cause (keep higher-confidence variant).
3. Sort by confidence/severity.
4. Emit only actionable findings and required regression tests.

## Reporting Contract

Each finding should include:

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

- Report only findings that pass the FP gate.
- Below-threshold confidence findings can be listed as low-confidence notes (no fix block).
