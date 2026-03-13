---
paths:
  - "evals/**"
  - "datasets/**"
---

# Eval/Data Change Rules

When modifying evaluation data or datasets:
- JSONL files: one JSON object per line, validate with:
  `python scripts/audit-pipeline/validate_jsonl.py --schema datasets/normalized/finding.schema.json --jsonl <path>`
- JSON files: validate with:
  `python scripts/audit-pipeline/validate_json.py --schema datasets/normalized/audit.schema.json --glob 'datasets/normalized/audits/*.json'`
- New findings must include: confidence tag, provenance, severity
- Redact client-identifying material from audit data
- Detection quality changes must add/update cases in evals/cases/
- `python scripts/quality/validate_skills.py` is only for SKILL/link checks, not dataset schema validation
