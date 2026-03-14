---
name: repo-agent-instructions
description: Deprecated. Redirects to starknet-agentic for Cairo/Starknet skills.
---

# Agent Instructions

> [!WARNING]
> This repository is deprecated. Use `keep-starknet-strange/starknet-agentic` as canonical source for skills.
> Migration details: `DEPRECATED.md`.

This repository contains Cairo/Starknet skills for AI coding agents. Each skill is a prescriptive orchestrator — it tells you exactly what to load, what to check, and in what order.

## Available Skills

| Skill | Use when | Entry point |
|-------|----------|-------------|
| **cairo-auditor** | Security review of Cairo contracts | `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-auditor/SKILL.md` |
| **cairo-contract-authoring** | Writing new contracts or modifying existing ones | `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-contract-authoring/SKILL.md` |
| **cairo-testing** | Writing unit, integration, fuzz, or regression tests | `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-testing/SKILL.md` |
| **cairo-optimization** | Profiling and optimizing gas/steps | `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-optimization/SKILL.md` |
| **cairo-deploy** | Build, declare, deploy, verify operations | `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-deploy/SKILL.md` |
| **account-abstraction** | Account abstraction patterns and risks | `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/account-abstraction/SKILL.md` |
| **starknet-network-facts** | Starknet network constraints and semantics | `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/starknet-network-facts/SKILL.md` |

## Recommended Flow

For new contract work, use this sequence:

1. `cairo-contract-authoring` — write the contract
2. `cairo-testing` — add tests
3. `cairo-optimization` — optimize hot paths (if needed)
4. `cairo-auditor` — security review

## How to Use

Each `SKILL.md` file contains:
- **When to Use / When NOT to Use** — scope boundaries
- **Quick Start** — 5-step summary
- **Orchestration** — turn-by-turn instructions with exact tool calls
- **Security-Critical Rules** — non-negotiable constraints
- **References** — links to detailed reference material

Read the `SKILL.md` for the task at hand. Follow its orchestration steps. Load references only when the orchestration tells you to — this keeps context focused.

## Tooling Versions (March 2026)

- Scarb: >= 2.14.0 (recommended 2.16.x)
- Starknet Foundry (snforge/sncast): 0.57.0
- OpenZeppelin Cairo: 3.0.0
- Cairo edition: 2024_07
