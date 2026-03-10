---
paths:
  - "evals/**"
  - "datasets/**"
---

When modifying evaluation data or datasets:
- JSONL files: one JSON object per line, validate against datasets/schemas/
- New findings must include: confidence tag, provenance, severity
- Redact client-identifying material from audit data
- Detection quality changes must add/update cases in evals/cases/
- Run `python scripts/quality/validate_skills.py` to verify schema compliance
