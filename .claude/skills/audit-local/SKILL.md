---
name: audit-local
description: Run a local security audit on a Cairo repository
allowed-tools: Bash, Read, Grep, Glob, Python
argument-hint: <path-to-cairo-repo>
---

# Audit Local Skill

## Quick Start

1. Validate and sanitize the target repo path:

   ```bash
   REPO="$ARGUMENTS"
   [ -n "$REPO" ] || { echo "ERROR: repo path is required" >&2; exit 1; }
   echo "$REPO" | grep -qE '^[A-Za-z0-9_./ -]+$' || {
     echo "ERROR: repo path contains unsafe characters" >&2
     exit 1
   }
   if echo "$REPO" | grep -qE '(^|/)\.\.(/|$)'; then
     echo "ERROR: repo path traversal is not allowed" >&2
     exit 1
   fi
   [ -f scripts/quality/audit_local_repo.py ] || {
     echo "ERROR: scripts/quality/audit_local_repo.py not found from current working directory" >&2
     exit 1
   }
   [ -d "$REPO" ] || { echo "ERROR: '$REPO' is not a directory" >&2; exit 1; }
   ```

2. Run the local deterministic audit:
   `python3 scripts/quality/audit_local_repo.py --repo-root "$REPO" --scan-id "local-$(date +%s)"`
3. Report findings grouped by severity (`Critical > High > Medium > Low > Info`) with title, location, and fix.
4. Summarize totals and top-3 highest-severity findings.
5. Follow the full workflow: [Audit Local Workflow](./workflow.md)

## When to Use

- You need a fast deterministic baseline scan on a local Cairo repo.
- You want report artifacts (`.json`, `.md`, optional findings JSONL) for triage.

## When NOT to Use

- You need deep multi-agent reasoning over complex economic logic.
- You are auditing non-Cairo targets or unrelated infrastructure.

## Rationalizations to Reject

- "No findings means secure."
- "It compiled, so access control must be correct."
- "This can wait until after merge."
