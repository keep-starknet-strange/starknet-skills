# Audit Local Workflow

1. Confirm target repository path and sanitize shell input.
2. Run `scripts/quality/audit_local_repo.py` with a unique `--scan-id`.
3. Capture artifacts (`.json`, `.md`, optional findings JSONL).
4. Triage by severity first, then confidence.
5. Convert accepted findings into eval updates when appropriate.
