<p align="center">
  <img alt="cairo-auditor hero" src="../assets/cairo-auditor-hero.svg" width="100%" />
</p>

# cairo-auditor

Flagship Cairo/Starknet audit skill.

<p>
  <img alt="mode default" src="https://img.shields.io/badge/mode-default-0969da" />
  <img alt="mode deep" src="https://img.shields.io/badge/mode-deep-7c3aed" />
  <img alt="fp gate" src="https://img.shields.io/badge/false--positive-gated-2ea043" />
  <img alt="deterministic smoke" src="https://img.shields.io/badge/deterministic%20smoke-pass-f59e0b" />
  <img alt="agent eval" src="https://img.shields.io/badge/agent%20eval-in%20progress-f59e0b" />
</p>

## Usage

```bash
/cairo-auditor
/cairo-auditor deep
/cairo-auditor contracts/account.cairo
```

## Structure

- `SKILL.md`: 4-turn orchestration contract.
- `agents/`: vector + adversarial specialist instructions.
- `references/attack-vectors/`: partitioned D:/FP: vectors.
- `references/judging.md`: strict FP gate and confidence rules.
- `references/vulnerability-db/`: canonical class docs.

## Benchmarks

Deterministic scorecards are smoke/regression gates, not final independent proof.

| Suite | Cases | Precision | Recall | Scorecard |
| --- | ---: | ---: | ---: | --- |
| Core deterministic | 34 | 1.000 | 1.000 | [v0.2.0-cairo-auditor-benchmark.md](../evals/scorecards/v0.2.0-cairo-auditor-benchmark.md) |
| Real-world corpus | 34 | 1.000 | 1.000 | [v0.2.0-cairo-auditor-realworld-benchmark.md](../evals/scorecards/v0.2.0-cairo-auditor-realworld-benchmark.md) |

Additional quality signals:

- External triage: [v0.2.0-cairo-auditor-external-triage.md](../evals/scorecards/v0.2.0-cairo-auditor-external-triage.md)
- Manual gold: [v0.2.0-cairo-auditor-manual-19-gold-recall.md](../evals/scorecards/v0.2.0-cairo-auditor-manual-19-gold-recall.md)
- Sierra auxiliary: [sierra-parallel-low-profile-2026-03-09.md](../evals/reports/sierra-parallel-low-profile-2026-03-09.md)

## References

- Skill policy: [SKILL.md](SKILL.md)
- Workflow docs: [workflows/default.md](workflows/default.md), [workflows/deep.md](workflows/deep.md)
- Vector index: [references/attack-vectors/](references/attack-vectors)
- FP gate: [references/judging.md](references/judging.md)
- Class docs: [references/vulnerability-db/README.md](references/vulnerability-db/README.md)
