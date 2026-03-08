# starknet-skills

<p align="center">
  <img alt="starknet-skills hero" src="assets/readme-hero.png" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/keep-starknet-strange/starknet-skills/actions/workflows/quality.yml">
    <img alt="quality gate" src="https://img.shields.io/github/actions/workflow/status/keep-starknet-strange/starknet-skills/quality.yml?branch=main&label=quality%20gate&color=2ea043" />
  </a>
  <img alt="modules" src="https://img.shields.io/badge/modules-7-0f172a" />
  <img alt="audits" src="https://img.shields.io/badge/audits-24-0f172a" />
  <img alt="smoke" src="https://img.shields.io/badge/smoke-pass-2ea043" />
</p>

LLMs hallucinate Cairo patterns, miss Starknet-specific footguns, and skip regression tests. This repo fixes that: 7 audited skill modules plus a router, backed by 24 real-world audit reports and 217 normalized findings.

> Reasoning + security knowledge layer. For operational tooling see [starknet-agentic](https://github.com/keep-starknet-strange/starknet-agentic) and [starkzap](https://github.com/keep-starknet-strange/starkzap).

## How It Works

Each skill is a standalone markdown file. Point any AI agent at a URL and it gets the Cairo or Starknet context immediately. No SDK, no dependencies, no package manager.

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/cairo-auditor/SKILL.md  <- audit workflow
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/cairo-testing/SKILL.md  <- test strategy
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md                <- router
```

## Install & Use

### Give your agent the router URL

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md
```

### Claude Code Plugin

Install directly from GitHub:

```bash
/plugin marketplace add keep-starknet-strange/starknet-skills
/plugin install starknet-skills
```

### Local clone

```bash
git clone https://github.com/keep-starknet-strange/starknet-skills.git
```

## Skills

| Module | What LLMs Get Wrong |
| --- | --- |
| [cairo-auditor](cairo-auditor/SKILL.md) | Skip false-positive gates, miss Starknet-specific upgrade and account-footgun patterns |
| [cairo-contract-authoring](cairo-contract-authoring/SKILL.md) | Copy Solidity structure into Cairo and miss component-specific patterns |
| [cairo-testing](cairo-testing/SKILL.md) | Stop at unit tests, skip invariants, and use stale `snforge` patterns |
| [cairo-optimization](cairo-optimization/SKILL.md) | Ignore Sierra and trace-level costs, then optimize the wrong storage paths |
| [cairo-toolchain](cairo-toolchain/SKILL.md) | Use stale declare/deploy flows and wrong Scarb or Starkli commands |
| [account-abstraction](account-abstraction/SKILL.md) | Miss session-key threats, self-call hazards, and validation edge cases |
| [starknet-network-facts](starknet-network-facts/SKILL.md) | Hallucinate fee semantics, timing assumptions, and network constraints |

## Data Pipeline

```text
ingest -> segment -> normalize -> distill -> skillize
  24        26         217          9          7
audits   corpora    findings     assets     skills
```

- **Ingest**: 24 real-world audit reports cataloged in [`datasets/manifests/audits.jsonl`](datasets/manifests/audits.jsonl)
- **Normalize**: 217 findings with structured metadata under [`datasets/normalized/findings/`](datasets/normalized/findings)
- **Distill**: 9 reusable assets across vuln cards, fix patterns, and test recipes
- **Skillize**: 7 focused skill modules plus the top-level router [`SKILL.md`](SKILL.md)

Full pipeline docs: [datasets/README.md](datasets/README.md)  
Evaluation policy: [evals/README.md](evals/README.md)

## Benchmarks

cairo-auditor real-world benchmark:

| Metric | Score |
| --- | --- |
| Cases | 17 |
| Precision | 1.0 |
| Recall | 1.0 |

Scorecards:
- [v0.2.0-cairo-auditor-benchmark.md](evals/scorecards/v0.2.0-cairo-auditor-benchmark.md)
- [v0.2.0-cairo-auditor-realworld-benchmark.md](evals/scorecards/v0.2.0-cairo-auditor-realworld-benchmark.md)
- [v0.4.0-contract-skill-benchmark.md](evals/scorecards/v0.4.0-contract-skill-benchmark.md)
- [contract-skill-benchmark-trend.md](evals/scorecards/contract-skill-benchmark-trend.md)
- [v0.2.0-cairo-auditor-external-triage.md](evals/scorecards/v0.2.0-cairo-auditor-external-triage.md)
- [cairo-auditor-external-trend.md](evals/scorecards/cairo-auditor-external-trend.md)

## Methodology

Skills are authored from audit-backed source material, then checked against deterministic benchmarks and held-out evaluation rules before landing. The goal is narrow, reusable corrections for common Cairo and Starknet failure modes, not general prose documentation.

Current workflow status:
- `quality.yml` is the required per-PR gate
- `full-evals.yml` runs on schedule, workflow dispatch, or explicitly labeled PRs
- external triage trends live under [`evals/scorecards/`](evals/scorecards)

## Website

- Site: [starkskills.org](https://starkskills.org)
- Static site source: [website/](website/)
- Site generator: [scripts/site/build_site.py](scripts/site/build_site.py)

## Contributing

Something wrong or missing? Humans and agents are welcome to [open a PR](CONTRIBUTING.md).

Also relevant:
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [THIRD_PARTY.md](THIRD_PARTY.md)
- skill contract validator: `python scripts/quality/validate_skills.py`
- parity + eval preflight: `python scripts/quality/parity_check.py`

## License

MIT
