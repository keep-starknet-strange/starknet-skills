# Finding Record Schema

Required fields:

- `finding_id`: stable identifier (`AUDITCODE-###`)
- `source_audit`: audit reference label
- `severity`: `critical|high|medium|low|info`
- `file_path`: contract path
- `function_name`: function or entrypoint
- `root_cause`: concise technical cause
- `exploit_path`: concrete attack sequence
- `vulnerable_pattern`: minimal vulnerable snippet or pattern
- `fixed_pattern`: expected secure pattern
- `detection_rule`: how an agent should detect it
- `false_positive_caveat`: known lookalikes
- `required_test`: regression test requirement
- `provenance`: source trace (audit section/page or anchor)
- `confidence`: `low|medium|high`
