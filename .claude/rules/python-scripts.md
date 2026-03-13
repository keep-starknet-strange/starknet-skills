---
paths:
  - "scripts/**/*.py"
---

# Python Script Conventions

- Python 3.12, ruff defaults (no pyproject.toml overrides)
- Run `ruff check` on changed files before committing
- Scripts in scripts/quality/ are the primary validation tools
- Use explicit version pinning for dependencies (jsonschema==4.23.0, pyyaml==6.0.2)
