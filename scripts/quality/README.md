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

- `validate_marketplace.py` enforces `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` consistency:
  - same plugin name across files
  - synchronized version fields
  - root plugin entry present with `source: "./"`

- `parity_check.py` runs local parity checks against baseline quality bars:
  - skill contract validator pass
  - required governance/entry files present
  - README install/use onboarding present
  - `cairo-testing` docs match installed `snforge` CLI behavior
  - `cairo-toolchain` docs match installed `sncast` CLI behavior
  - explicit Trail of Bits-style authoring parity:
    - required sections
    - quick start in each module skill
    - progressive-disclosure markdown links from entry skills
