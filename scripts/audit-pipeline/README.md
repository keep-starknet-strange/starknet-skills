# Audit Pipeline Scripts

## 1) Generate manifest hashes

```bash
python3 scripts/audit-pipeline/generate_manifest.py \
  --seed datasets/manifests/audit_metadata.seed.json \
  --output datasets/manifests/audits.jsonl
```

## 2) Segment extracted text

```bash
python3 scripts/audit-pipeline/segment_text.py \
  --audit-id csc_vesu_update_2025_03 \
  --input datasets/audits/extracted/Vesu_Update_Audit_Report.txt \
  --output datasets/segments/csc_vesu_update_2025_03.jsonl
```

Notes:

- Table-of-contents noise and oversized test-output sections are filtered automatically.
- Finding segments are expected to include `File(s):` markers for downstream normalization.

## 3) Validate normalized records

```bash
python3 scripts/audit-pipeline/validate_jsonl.py \
  --schema datasets/normalized/finding.schema.json \
  --jsonl datasets/normalized/findings/csc_vesu_update_2025_03.findings.jsonl
```
