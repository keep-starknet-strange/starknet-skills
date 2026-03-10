---
paths:
  - "**/SKILL.md"
  - "**/references/**"
  - "**/workflows/**"
---

When editing skill files:
- SKILL.md must have YAML frontmatter with `name` and `description`
- Must include "When to Use" and "When NOT to Use" sections
- Security/audit skills must include "Rationalizations to Reject"
- Keep SKILL.md under 500 lines; split into references/ and workflows/
- One level of linking depth only (no chained references)
- Run `python scripts/quality/validate_skills.py` after changes
