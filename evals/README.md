# Evaluations

Evaluation cases and scorecards for skill quality regression tracking.

## Structure

- `cases/`: held-out cases for detection and remediation quality.
- `heldout/`: explicit hold-out policy and reserved sets excluded from distillation.
- `scorecards/`: run outputs and aggregate metrics by version.

## Minimum Gate

For changes affecting security detection behavior:

- Baseline is the latest `main` scorecard for the same module and case set.
- High/Critical recall must not regress on `evals/cases/` + documented held-out set.
- False-positive rate must not increase by more than +1.0 percentage point and must remain <= 2.0% absolute.

## CI Tiers

- Per-PR (`quality.yml`): schema validation, manifest uniqueness checks, and held-out leakage policy checks.
- Full tier (`full-evals.yml`): parity checks + held-out leakage guard; run on schedule, workflow-dispatch, or pull requests labeled `full-evals`.
