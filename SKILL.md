---
name: starknet-skills
description: Routes Cairo/Starknet coding and audit tasks to the smallest relevant module for focused, high-quality execution.
---

# Starknet Skills Router

Use this file to choose the smallest relevant module.

## Start Here

- For contract security review: [cairo-auditor](cairo-auditor/SKILL.md)
- For writing new contracts: [cairo-contract-authoring](cairo-contract-authoring/SKILL.md)
- For testing and fuzzing: [cairo-testing](cairo-testing/SKILL.md)
- For gas/perf optimization: [cairo-optimization](cairo-optimization/SKILL.md)
- For build/declare/deploy/release operations: [cairo-toolchain](cairo-toolchain/SKILL.md)
- For account abstraction rules and risks: [account-abstraction](account-abstraction/SKILL.md)
- For Starknet network constraints: [starknet-network-facts](starknet-network-facts/SKILL.md)

## Routing Policy

- Prefer one module first.
- Add a second module only when blocked.
- Keep context narrow and evidence-based.

## Recommended Build-to-Audit Flow

For new contract work, use this sequence:

1. [cairo-contract-authoring](cairo-contract-authoring/SKILL.md)
2. [cairo-testing](cairo-testing/SKILL.md)
3. [cairo-optimization](cairo-optimization/SKILL.md) (if performance matters)
4. [cairo-auditor](cairo-auditor/SKILL.md)

`cairo-contract-authoring`, `cairo-testing`, and `cairo-optimization` output a **Handoff Block** at the end of their workflows — a structured summary (files touched, security posture, test status) that can be passed as input to the next skill. See [references/skill-handoff.md](references/skill-handoff.md) for the format.
