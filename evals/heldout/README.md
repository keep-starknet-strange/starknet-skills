# Held-out Evaluation Set

This directory tracks evaluation inputs excluded from distillation/training artifacts.

Current held-out source:

- `evals/cases/case-aa-self-call-session.json`

Policy:

- Do not copy held-out records into `datasets/distilled/*`.
- Use held-out cases for regression checks of recall and false positives.
