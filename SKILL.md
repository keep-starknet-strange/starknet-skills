---
name: starknet-skills
description: Routes Cairo/Starknet coding and audit tasks to the smallest relevant module for focused, high-quality execution.
---

# Starknet Skills Router

> [!WARNING]
> Deprecated router. Canonical router moved to:
> `https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/SKILL.md`
> See [DEPRECATED.md](DEPRECATED.md).

Use this file to choose the smallest relevant module.

## Start Here

- For contract security review: [cairo-auditor](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-auditor/SKILL.md)
- For writing new contracts: [cairo-contract-authoring](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-contract-authoring/SKILL.md)
- For testing and fuzzing: [cairo-testing](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-testing/SKILL.md)
- For gas/perf optimization: [cairo-optimization](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-optimization/SKILL.md)
- For build/declare/deploy/release operations: [cairo-deploy](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-deploy/SKILL.md)
- For account abstraction rules and risks: [account-abstraction](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/account-abstraction/SKILL.md)
- For Starknet network constraints: [starknet-network-facts](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/starknet-network-facts/SKILL.md)

## Routing Policy

- Prefer one module first.
- Add a second module only when blocked.
- Keep context narrow and evidence-based.

## Recommended Build-to-Audit Flow

For new contract work, use this sequence:

1. [cairo-contract-authoring](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-contract-authoring/SKILL.md)
2. [cairo-testing](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-testing/SKILL.md)
3. [cairo-optimization](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-optimization/SKILL.md) (if performance matters)
4. [cairo-auditor](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-auditor/SKILL.md)

`cairo-contract-authoring`, `cairo-testing`, and `cairo-optimization` output a **Handoff Block** at the end of their workflows — a structured summary (files touched, security posture, test status) that can be passed as input to the next skill. Canonical format reference: [skill-handoff.md](https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/skills/cairo-contract-authoring/references/skill-handoff.md).
