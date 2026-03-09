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

<p align="center"><strong>Cairo/Starknet skills for agents</strong></p>

Cairo/Starknet skill modules for agent reliability: security review, contract authoring, testing, optimization, toolchain, account abstraction, and network facts.

> Reasoning + security knowledge layer. For operational tooling, see [starknet-agentic](https://github.com/keep-starknet-strange/starknet-agentic) and [starkzap](https://github.com/keep-starknet-strange/starkzap).

## Install & Use

### Router URL (fastest)

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md
```

### Claude Code Plugin

```bash
/plugin marketplace add keep-starknet-strange/starknet-skills
/plugin menu
/plugin install starknet-skills
# Optional: install only the flagship audit module
/plugin install cairo-auditor@starknet-skills
```

### Maintainer Publish Checklist

```bash
# 1) Validate manifests (root marketplace + module plugin)
claude plugin validate .
claude plugin validate cairo-auditor
python3 scripts/quality/validate_marketplace.py

# 2) Merge to main, then cut release
VERSION="<sync with .claude-plugin/marketplace.json metadata.version>"
git tag "v${VERSION}"
git push origin "v${VERSION}"
gh release create "v${VERSION}" --generate-notes
```

### Local clone

```bash
git clone https://github.com/keep-starknet-strange/starknet-skills.git
```

## First Local Audit (60s)

Unified CLI (recommended):

```bash
./starkskills doctor
./starkskills audit local --repo-root /path/to/your/cairo-repo --scan-id local-audit
```

Optional defaults file:


```bash
cp .starkskills.toml.example .starkskills.toml
```

Script entrypoint (direct):

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

### Reading Sierra v3 Output

`ir_confirmation` is evidence status, not severity:

| ir_confirmation | signal_quality | Interpretation |
| --- | --- | --- |
| `confirmed` | `high` | Strong IR evidence for the improvement candidate. |
| `confirmed` | `medium`/`low` | Pattern-level IR support; useful but weaker confidence. |
| `missing` | `high` | High-quality IR path checked and no matching signal found. |
| `missing` | `medium`/`low` | Weak negative evidence; usually treat as inconclusive. |
| `unknown` | any | No analyzable IR path for this class/artifact combination. |

`artifact_source` indicates where the IR evidence came from:
- `sierra_json`: strongest, function-level analysis.
- `contract_class`: marker-level analysis.
- `sierra_text`: grep-level fallback.
- `none`: no analyzable artifact was available.

Reports are written under `<repo-root>/evals/reports/local/` by default (`.md`, `.json`).
Add `--write-findings-jsonl` to emit `.findings.jsonl`.
If a target filename already exists, the script appends `-N` to avoid overwrite.

External benchmark packs in one command:

```bash
./starkskills audit external --pack less-known --scan-id community-wave
./starkskills audit deep --pack less-known --scan-id community-wave-deep
```

Optional SARIF export for code scanning:

```bash
./starkskills audit local --repo-root /path/to/repo --format sarif
```

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
| [cairo-auditor](cairo-auditor/SKILL.md) | Misses Starknet upgrade/account edge cases and weak FP gates |
| [cairo-contract-authoring](cairo-contract-authoring/SKILL.md) | Applies Solidity structure directly to Cairo components |
| [cairo-testing](cairo-testing/SKILL.md) | Stops at unit tests and skips invariants/adversarial regression coverage |
| [cairo-optimization](cairo-optimization/SKILL.md) | Optimizes wrong paths without trace/Sierra context |
| [cairo-toolchain](cairo-toolchain/SKILL.md) | Uses stale Scarb/snforge/sncast workflows |
| [account-abstraction](account-abstraction/SKILL.md) | Misses session-key/self-call and validation-flow pitfalls |
| [starknet-network-facts](starknet-network-facts/SKILL.md) | Hallucinates network semantics and fee/timing assumptions |

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
- `full-evals.yml` runs on schedule/workflow dispatch and auto-triggers on `pull_request` events (`opened`, `synchronize`, `reopened`, `ready_for_review`) when touched paths match `SKILL.md`, `**/SKILL.md`, `**/references/**`, `evals/**`, `scripts/quality/**`, or `.github/workflows/**`.
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
