# cairo-auditor

<p>
  <img alt="mode default" src="https://img.shields.io/badge/mode-default-0969da" />
  <img alt="mode deep" src="https://img.shields.io/badge/mode-deep-8250df" />
  <img alt="false positive gate" src="https://img.shields.io/badge/false--positive-gated-2ea043" />
  <img alt="bench precision" src="https://img.shields.io/badge/benchmark%20precision-100%25-f0883e" />
  <img alt="bench recall" src="https://img.shields.io/badge/benchmark%20recall-100%25-f0883e" />
</p>

Flagship workflow skill for Cairo/Starknet contract security review.

## Usage

```bash
# default repo scan
/cairo-auditor

# deeper review with stricter adversarial pass
/cairo-auditor deep

# targeted review for one or more files
/cairo-auditor contracts/account.cairo
```

## Structure

- `SKILL.md`: orchestration policy + reporting contract.
- `workflows/`: default/deep execution steps.
- `agents/`: vector/adversarial sub-agent instructions.
- `references/vulnerability-db/`: canonical vulnerability classes.
- `references/audit-findings/`: compiled handbook-style reference.
- `scripts/`: extraction and normalization helpers.

## Benchmark Snapshot

Published benchmark:

- [v0.2.0-cairo-auditor-benchmark.md](../evals/scorecards/v0.2.0-cairo-auditor-benchmark.md)

Benchmark case pack:

- [cairo_auditor_benchmark.jsonl](../evals/cases/cairo_auditor_benchmark.jsonl)

Cases include vulnerable and hardened Cairo snippets derived from:

- normalized findings in `datasets/normalized/findings/`
- AA session-key escalation pattern (`AA-SELF-CALL-SESSION`)

## References

- Module policy: [SKILL.md](SKILL.md)
- Vulnerability classes: [references/vulnerability-db/README.md](references/vulnerability-db/README.md)
- Release gate checklist: [references/checklists/release-gate.md](references/checklists/release-gate.md)
