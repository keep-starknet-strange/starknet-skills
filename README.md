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
  <img alt="findings snapshot" src="https://img.shields.io/badge/normalized%20findings-snapshot-0f172a" />
  <img alt="smoke" src="https://img.shields.io/badge/deterministic%20smoke-pass-2ea043" />
</p>

<p align="center"><strong>Audit-grade Cairo/Starknet skills for agents</strong></p>

Cairo/Starknet skill modules for agent reliability: security review, contract authoring, testing, optimization, toolchain, account abstraction, and network facts.

> Reasoning + security knowledge layer. For operational tooling, see [starknet-agentic](https://github.com/keep-starknet-strange/starknet-agentic) and [starkzap](https://github.com/keep-starknet-strange/starkzap).

## Quick Start

### Router URL (fastest)

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

## How It Works

Each skill is plain markdown. Point an agent at a `SKILL.md` URL and it loads focused Cairo/Starknet context.

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/cairo-auditor/SKILL.md
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/cairo-testing/SKILL.md
```

## Skill Modules

| Module | What LLMs Commonly Miss |
| --- | --- |
| [cairo-auditor](cairo-auditor/SKILL.md) | Starknet upgrade/account edge cases and weak FP gates |
| [cairo-contract-authoring](cairo-contract-authoring/SKILL.md) | Applies Solidity structure directly to Cairo components |
| [cairo-testing](cairo-testing/SKILL.md) | Invariants, adversarial tests, and regression discipline |
| [cairo-optimization](cairo-optimization/SKILL.md) | Optimizes wrong paths without trace/Sierra context |
| [cairo-toolchain](cairo-toolchain/SKILL.md) | Uses stale Scarb/snforge/sncast workflows |
| [account-abstraction](account-abstraction/SKILL.md) | Session-key/self-call pitfalls and validation flow |
| [starknet-network-facts](starknet-network-facts/SKILL.md) | Network semantics hallucinations and fee/timing assumptions |

Recommended sequence for new contracts: `cairo-contract-authoring` -> `cairo-testing` -> `cairo-auditor`.

## Data Pipeline

```text
ingest -> segment -> normalize -> distill -> skillize
  24        26         217          9          7
audits   corpora    findings     assets     skills
```

> Snapshot counts are maintainer-updated. When normalized findings change, update
> this table and badge labels together.

- Ingest manifest: [`datasets/manifests/audits.jsonl`](datasets/manifests/audits.jsonl)
- Normalized findings: [`datasets/normalized/findings/`](datasets/normalized/findings)
- Distilled assets: [`datasets/distilled/`](datasets/distilled)
- Router skill index: [`SKILL.md`](SKILL.md)

## Quality Signals

Deterministic benchmarks are **smoke/regression gates**, not final proof of auditor quality.

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

Skills are authored from audit-backed source material, then checked with deterministic gates and held-out evaluation policy before landing. The goal is reusable, high-signal corrections for common Cairo/Starknet failure modes, not generic documentation.

Current workflow:
- `quality.yml` is the required per-PR gate.
- `full-evals.yml` runs on schedule/workflow dispatch and auto-triggers for PRs touching `SKILL.md`, `references/**`, `evals/**`, `scripts/quality/**`, or `.github/workflows/**`.
- Build-side generation eval tracks contract authoring quality (`prompt -> generated code -> build/test/static checks`) as informational telemetry in `full-evals.yml`.
- External triage trends live under [`evals/scorecards/`](evals/scorecards).
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
