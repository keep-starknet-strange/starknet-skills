<p align="center">
  <img alt="cairo-auditor hero" src="../assets/cairo-auditor-hero.svg" width="100%" />
</p>

# cairo-auditor

Flagship Cairo/Starknet security review skill.

<p>
  <img alt="mode default" src="https://img.shields.io/badge/mode-default-0969da" />
  <img alt="mode deep" src="https://img.shields.io/badge/mode-deep-7c3aed" />
  <img alt="false positive gate" src="https://img.shields.io/badge/false--positive-gated-2ea043" />
  <img alt="benchmark precision" src="https://img.shields.io/badge/precision-1.000-f59e0b" />
  <img alt="benchmark recall" src="https://img.shields.io/badge/recall-1.000-f59e0b" />
</p>

## Usage

```bash
# default repo scan
/cairo-auditor

# deep adversarial pass
/cairo-auditor deep

# targeted scan
/cairo-auditor contracts/account.cairo
```

## Structure

- `SKILL.md`: orchestration policy + output contract.
- `workflows/`: default/deep execution steps.
- `agents/`: vector and adversarial sub-agent playbooks.
- `references/vulnerability-db/`: canonical vulnerability classes.
- `references/audit-findings/`: distilled audit-derived findings.
- `scripts/`: extraction and normalization helpers.

## Benchmarks

| Suite | Cases | Precision | Recall | Scorecard |
| --- | ---: | ---: | ---: | --- |
| Core deterministic | 12 | 1.000 | 1.000 | [v0.2.0-cairo-auditor-benchmark.md](../evals/scorecards/v0.2.0-cairo-auditor-benchmark.md) |
| Real-world corpus | 11 | 1.000 | 1.000 | [v0.2.0-cairo-auditor-realworld-benchmark.md](../evals/scorecards/v0.2.0-cairo-auditor-realworld-benchmark.md) |

Case packs:

- [cairo_auditor_benchmark.jsonl](../evals/cases/cairo_auditor_benchmark.jsonl)
- [cairo_auditor_realworld_benchmark.jsonl](../evals/cases/cairo_auditor_realworld_benchmark.jsonl)

## References

- Module policy: [SKILL.md](SKILL.md)
- Vulnerability classes: [references/vulnerability-db/README.md](references/vulnerability-db/README.md)
- Release gate checklist: [references/checklists/release-gate.md](references/checklists/release-gate.md)
