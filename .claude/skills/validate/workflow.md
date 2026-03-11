# Validation Workflow

1. Run `validate_skills.py` and `validate_marketplace.py`.
2. Run `ruff check scripts/`.
3. If outputs touch evals/datasets, validate with:
   - JSONL: `python scripts/audit-pipeline/validate_jsonl.py --schema datasets/normalized/finding.schema.json --jsonl <path>`
   - JSON: `python scripts/audit-pipeline/validate_json.py --schema datasets/normalized/audit.schema.json --glob 'datasets/normalized/audits/*.json'`
4. Fix failures before requesting review.
5. Re-run checks after each fix to confirm clean status.
