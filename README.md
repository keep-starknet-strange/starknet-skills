<p align="center">
  <img alt="starknet-skills banner" src="https://img.shields.io/badge/starknet-skills-0f172a?style=for-the-badge&logo=starknet&logoColor=white" />
</p>

<p align="center">
  <a href="https://github.com/keep-starknet-strange/starknet-skills/actions/workflows/quality.yml">
    <img alt="quality gate" src="https://img.shields.io/github/actions/workflow/status/keep-starknet-strange/starknet-skills/quality.yml?branch=main&label=quality%20gate" />
  </a>
  <img alt="modules" src="https://img.shields.io/badge/modules-8-2ea043" />
  <img alt="catalog rows" src="https://img.shields.io/badge/audit%20catalog-44-0969da" />
  <img alt="ingested audits" src="https://img.shields.io/badge/ingested%20audits-27-8250df" />
  <a href="LICENSE">
    <img alt="license" src="https://img.shields.io/badge/license-MIT-f0883e" />
  </a>
</p>

# starknet-skills

Production-grade Cairo/Starknet skills for secure coding, auditing, and release quality.

Operational tool-usage playbooks stay in `starknet-agentic`/`starkzap`; this repo is the reasoning + security layer.

## Install & Use

Preferred (Claude marketplace):

```bash
/plugin marketplace add keep-starknet-strange/starknet-skills
/plugin menu
```

Direct router usage:

```bash
git clone https://github.com/keep-starknet-strange/starknet-skills.git
# then load local SKILL.md
```

Raw router URL:

- [SKILL.md](https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md)

## Quick Paths

| Module | Purpose |
| --- | --- |
| [cairo-auditor](cairo-auditor/SKILL.md) | Systematic Cairo security review workflow |
| [cairo-contract-authoring](cairo-contract-authoring/SKILL.md) | Safe implementation patterns |
| [cairo-testing](cairo-testing/SKILL.md) | Unit/integration/invariant strategy |
| [cairo-optimization](cairo-optimization/SKILL.md) | Performance + gas/resource hardening |
| [cairo-toolchain](cairo-toolchain/SKILL.md) | Build/declare/deploy/verify operations |
| [account-abstraction](account-abstraction/SKILL.md) | Account/session-key risk patterns |
| [starknet-network-facts](starknet-network-facts/SKILL.md) | Chain-level constraints and semantics |
| [openzeppelin-cairo](openzeppelin-cairo/SKILL.md) | OZ Cairo composition and footguns |

## Data & Evals

- [datasets/README.md](datasets/README.md): canonical pipeline (`ingest -> segment -> normalize -> distill -> skillize`).
- [evals/README.md](evals/README.md): held-out policy and benchmark gates.
- Latest benchmark scorecard: [v0.2.0-cairo-auditor-benchmark.md](evals/scorecards/v0.2.0-cairo-auditor-benchmark.md)

## Scope Boundary

- In scope: Cairo correctness, security review patterns, Starknet architecture, testing and hardening workflows.
- Out of scope: runtime MCP/SDK operation guides and protocol interaction playbooks.

## Governance

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Skill contract validator: `python scripts/quality/validate_skills.py`
- Quality parity + benchmark gates: `python scripts/quality/parity_check.py`
