# Audit Extraction

Utilities and templates to convert raw audit text into normalized records under `datasets/audits/`.

Suggested flow:

1. Parse raw audit text into candidate findings.
2. Normalize fields to schema.
3. Redact sensitive identifiers.
4. Validate record completeness.
5. Export to dataset and link to evaluator cases.
