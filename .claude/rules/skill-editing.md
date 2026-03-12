---
paths:
  - "**/SKILL.md"
  - "**/references/**"
  - "**/workflows/**"
  - ".claude/skills/**/workflow.md"
---

# SKILL Editing Rules

When editing skill files:
- SKILL.md must have YAML frontmatter with `name` and `description`
- Must include a concise `## Quick Start` section
- Must include "When to Use" and "When NOT to Use" sections
- Security/audit skills must include "Rationalizations to Reject"
- Must include at least one local Markdown link for progressive disclosure (for example `./workflow.md` or `./reference.md`)
- Keep SKILL.md under 500 lines; keep deep details in `references/` and `workflows/`
- One level of linking depth only (no chained references)
- Run `python scripts/quality/validate_skills.py` after changes
