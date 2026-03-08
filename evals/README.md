# Evaluations

Evaluation cases and scorecards for skill quality regression tracking.

## Structure

- `cases/`: held-out cases for detection and remediation quality.
- `heldout/`: explicit hold-out policy and reserved sets excluded from distillation.
- `scorecards/`: run outputs and aggregate metrics by version.

## Minimum Gate

For changes affecting security detection behavior:

- High/Critical recall must not regress.
- False-positive rate must not increase beyond allowed threshold.
