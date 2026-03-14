# Deprecation Notice

`starknet-skills` is deprecated and scheduled for archive.

Canonical repository:

- https://github.com/keep-starknet-strange/starknet-agentic
- Skills path: `starknet-agentic/skills/`
- Impacted sibling repo: https://github.com/keep-starknet-strange/starkclaw

## Install (Canonical)

```bash
/plugin marketplace add keep-starknet-strange/starknet-agentic
/plugin install starknet-agentic-skills@keep-starknet-strange-starknet-agentic
```

Router URL:

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-agentic/main/SKILL.md
```

## Skill Mapping

| Legacy (`starknet-skills`) | Canonical (`starknet-agentic`) |
| --- | --- |
| `cairo-auditor` | `skills/cairo-auditor` |
| `cairo-contract-authoring` | `skills/cairo-contract-authoring` |
| `cairo-testing` | `skills/cairo-testing` |
| `cairo-optimization` | `skills/cairo-optimization` |
| `cairo-toolchain` | `skills/cairo-deploy` |
| `account-abstraction` | `skills/account-abstraction` |
| `starknet-network-facts` | `skills/starknet-network-facts` |

## Repository Policy

- No new feature content should be added here.
- Only migration notices and archive-prep maintenance should land in this repository.
