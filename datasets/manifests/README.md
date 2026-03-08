# Audit Manifests

`audits.jsonl` is the canonical ingest/provenance registry.

Each record must include:

- stable `audit_id`
- source URLs
- local artifact paths
- sha256 hashes for raw/extracted artifacts
- project/auditor/date metadata
