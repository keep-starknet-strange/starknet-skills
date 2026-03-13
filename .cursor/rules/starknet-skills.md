---
name: cursor-starknet-skills
description: Router and enforcement rules for using starknet-skills in Cursor.
---

# Starknet Skills for Cursor

This project provides Cairo/Starknet skills for AI coding agents. When working on Cairo contracts, load the appropriate skill from this repository.

## Skill Router

Each skill is at `<skill-name>/SKILL.md`. Read it and follow its orchestration steps.

| Task | Skill to load |
|------|---------------|
| Write a new Cairo contract | `cairo-contract-authoring/SKILL.md` |
| Add tests to a contract | `cairo-testing/SKILL.md` |
| Optimize gas/steps | `cairo-optimization/SKILL.md` |
| Security review | `cairo-auditor/SKILL.md` |
| Deploy/declare/verify | `cairo-toolchain/SKILL.md` |

## Current Tooling (March 2026)

- Scarb >= 2.14.0 (recommended 2.16.x)
- Starknet Foundry 0.57.0
- OpenZeppelin Cairo 3.0.0

## Security Rules (always enforced)

1. Every storage-mutating external has explicit access posture: guarded or documented-public.
2. Constructor validates all critical addresses are non-zero.
3. Upgrade flows reject zero class-hash values.
4. Timelock checks read from `get_block_timestamp()`, never from caller arguments.
5. Anti-pattern/secure-pattern pairs enforced — the anti-pattern is never written.
