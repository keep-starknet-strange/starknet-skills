---
name: audit-local
description: Run a local security audit on a Cairo repository
allowed-tools: Bash, Read, Grep, Glob
argument-hint: <path-to-cairo-repo>
---

Run a local audit on the Cairo repository at $ARGUMENTS:

1. Verify the path exists and contains `.cairo` files
2. Run `python scripts/quality/audit_local_repo.py --repo-root $ARGUMENTS --scan-id local-$(date +%s)`
3. Group findings by severity: Critical > High > Medium > Low > Info
4. For each finding show: title, severity, file location, recommended fix
5. Summarize: total by severity, top 3 critical issues
