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
  <img alt="smoke" src="https://img.shields.io/badge/deterministic%20smoke-pass-2ea043" />
</p>

Cairo/Starknet skill modules for agent reliability: security review, authoring, testing, optimization, toolchain, account abstraction, and network facts.

> Reasoning + security knowledge layer. For operational tooling see [starknet-agentic](https://github.com/keep-starknet-strange/starknet-agentic) and [starkzap](https://github.com/keep-starknet-strange/starkzap).

## How It Works

Each skill is plain markdown. Point an agent at the URL and it gets domain-specific context.

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/cairo-auditor/SKILL.md
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/cairo-testing/SKILL.md
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md
```

## Install & Use

### Router URL

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md
```

### Claude Code Plugin

```bash
/plugin marketplace add keep-starknet-strange/starknet-skills
/plugin install starknet-skills
```

### Local clone

```bash
git clone https://github.com/keep-starknet-strange/starknet-skills.git
```

## First Local Audit (60s)

```bash
python scripts/quality/audit_local_repo.py \
  --repo-root /path/to/your/cairo-repo \
  --scan-id local-audit
```

Optional Sierra confirmation (trusted repos only):

```bash
python scripts/quality/audit_local_repo.py \
  --repo-root /path/to/your/cairo-repo \
  --scan-id local-audit-sierra \
  --sierra-confirm \
  --allow-build
```

Warning: `--allow-build` may execute repository build steps/tooling.
Use build mode only on trusted code, or run in an isolated environment.

Reports are written under `<repo-root>/evals/reports/local/` by default (`.md`, `.json`).
Add `--write-findings-jsonl` to emit `.findings.jsonl`.
If a target filename already exists, the script appends `-N` to avoid overwrite.

## Skills

| Module | What LLMs Get Wrong |
| --- | --- |
| [cairo-auditor](cairo-auditor/SKILL.md) | Miss Starknet upgrade/account edge cases and weak FP gates |
| [cairo-contract-authoring](cairo-contract-authoring/SKILL.md) | Applies Solidity structure directly to Cairo components |
| [cairo-testing](cairo-testing/SKILL.md) | Stops at unit tests, skips invariants and adversarial checks |
| [cairo-optimization](cairo-optimization/SKILL.md) | Optimizes wrong paths without trace/Sierra context |
| [cairo-toolchain](cairo-toolchain/SKILL.md) | Uses stale Scarb/sncast/snforge workflows |
| [account-abstraction](account-abstraction/SKILL.md) | Misses session/self-call and validation pitfalls |
| [starknet-network-facts](starknet-network-facts/SKILL.md) | Hallucinates network semantics and fee/timing assumptions |

Recommended sequence for new contracts: `cairo-contract-authoring` -> `cairo-testing` -> `cairo-auditor`.

## Data Pipeline

```text
ingest -> segment -> normalize -> distill -> skillize
  24        26         217          9          7
audits   corpora    findings     assets     skills
```

- Ingest: [`datasets/manifests/audits.jsonl`](datasets/manifests/audits.jsonl)
- Normalize: [`datasets/normalized/findings/`](datasets/normalized/findings)
- Distill: vuln cards + fix patterns + test recipes in [`datasets/distilled/`](datasets/distilled)
- Skillize: module skills + router [`SKILL.md`](SKILL.md)

## Benchmarks

Deterministic benchmark scorecards are **smoke/regression gates**, not final proof of auditor quality.

- Deterministic smoke:
  - [v0.2.0-cairo-auditor-benchmark.md](evals/scorecards/v0.2.0-cairo-auditor-benchmark.md)
  - [v0.2.0-cairo-auditor-realworld-benchmark.md](evals/scorecards/v0.2.0-cairo-auditor-realworld-benchmark.md)
- Human-labeled external triage:
  - [v0.2.0-cairo-auditor-external-triage.md](evals/scorecards/v0.2.0-cairo-auditor-external-triage.md)
  - [cairo-auditor-external-trend.md](evals/scorecards/cairo-auditor-external-trend.md)
- Manual gold recall:
  - [v0.2.0-cairo-auditor-manual-19-gold-recall.md](evals/scorecards/v0.2.0-cairo-auditor-manual-19-gold-recall.md)
- Contract-skill benchmark:
  - [v0.5.0-contract-skill-benchmark.md](evals/scorecards/v0.5.0-contract-skill-benchmark.md)
  - [v0.4.0-contract-skill-benchmark.md](evals/scorecards/v0.4.0-contract-skill-benchmark.md)
  - [contract-skill-benchmark-trend.md](evals/scorecards/contract-skill-benchmark-trend.md)
- KPI publication gate:
  - [contract-kpi-publication-gate.md](evals/scorecards/contract-kpi-publication-gate.md)

## Methodology

Skills are authored from audit-backed source material, then checked against deterministic benchmarks and held-out evaluation rules before landing. The goal is narrow, reusable corrections for common Cairo and Starknet failure modes, not general prose documentation.

Current workflow status:
- `quality.yml` is the required per-PR gate
- `full-evals.yml` runs on schedule/workflow dispatch and auto-triggers for PRs touching `SKILL.md`, `references/**`, `evals/**`, `scripts/quality/**`, or `.github/workflows/**`
- build-side generation eval tracks contract authoring quality (prompt -> generated code -> build/test/static checks) as informational telemetry in `full-evals.yml`
- external triage trends live under [`evals/scorecards/`](evals/scorecards)
Evaluation policy: [evals/README.md](evals/README.md)

## Website

- Site: [starkskills.org](https://starkskills.org)
- Source: [website/](website/)
- Generator: [scripts/site/build_site.py](scripts/site/build_site.py)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [THIRD_PARTY.md](THIRD_PARTY.md).

Core local gates:
- `python3 scripts/quality/validate_skills.py`
- `python3 scripts/quality/validate_marketplace.py`
- `python3 scripts/quality/parity_check.py`

## License

MIT
