# Audit Pipeline Scripts

Prerequisite:

- `python3 -m pip install jsonschema`

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

- Table-of-contents noise, common watermark fragments, and oversized test-output sections are filtered automatically.
- Finding segments are expected to include `File(s):` markers for downstream normalization.
- Held-out audit IDs listed in `evals/heldout/audit_ids.txt` are blocked from segmentation output.

## 3) Validate normalized records

```bash
python3 scripts/audit-pipeline/validate_jsonl.py \
  --schema datasets/normalized/finding.schema.json \
  --jsonl datasets/normalized/findings/csc_vesu_update_2025_03.findings.jsonl
```

Notes:

- Validator reports malformed JSON line-by-line and rejects non-object JSON rows.
- Validator enforces held-out policy by rejecting records whose `audit_id` or `source_audit_id` appears in `evals/heldout/audit_ids.txt`.

## 4) Verify no held-out leakage in datasets

```bash
python3 scripts/audit-pipeline/check_no_heldout_leak.py
```
