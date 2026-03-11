# Validation Workflow

1. Run `validate_skills.py` and `validate_marketplace.py`.
2. Run `ruff check scripts/`.
3. If outputs touch evals/datasets, run audit-pipeline schema validators.
4. Fix failures before requesting review.
5. Re-run checks after each fix to confirm clean status.
