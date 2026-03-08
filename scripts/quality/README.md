# Quality Scripts

- `validate_skills.py` enforces repository SKILL.md contract checks:
  - required frontmatter (`name`, `description`)
  - valid YAML frontmatter parsing (PyYAML)
  - kebab-case and max length for `name`
  - third-person trigger-style `description`
  - `When to Use` / `When NOT to Use` sections for module skills
  - `Rationalizations to Reject` for audit/security skills
  - max 500 lines per SKILL.md
  - one-level markdown link depth for progressive disclosure
  - markdown link target existence and in-repo resolution
