# starknet-skills

Cairo/Starknet reasoning skills for agents. 7 modules, evaluation-backed.

## Key Paths

- Skills: `cairo-auditor/`, `cairo-contract-authoring/`, `cairo-testing/`, `cairo-optimization/`, `cairo-toolchain/`, `account-abstraction/`, `starknet-network-facts/`
- Each skill: `SKILL.md` (entry) → `references/` + `workflows/`
- Data: `datasets/audits/` (raw → extracted → normalized → distilled)
- Evals: `evals/cases/*.jsonl`, `evals/contracts/`, `evals/scorecards/`

## Hard Rules

- No operational SDK content — only correctness, security, eval-backed guidance
- Boundary changes MUST call out impacted repos: `keep-starknet-strange/starknet-agentic` and `keep-starknet-strange/starkclaw`
- Detection/remediation changes MUST include eval case updates
- Skill files require: "When to Use", "When NOT to Use"; security skills also: "Rationalizations to Reject"
- Keep SKILL.md concise; details go in `references/` and `workflows/`

## Commands

```bash
python3 scripts/quality/validate_skills.py     # structure check
python3 scripts/quality/validate_marketplace.py # marketplace metadata
python3 scripts/quality/parity_check.py         # optional, needs snforge+sncast
ruff check scripts/                             # Python lint
```

## Stack

Python 3.12 · Scarb 2.16.1 · Starknet Foundry 0.57.0 · ruff · shellcheck

## Style

- Python: ruff defaults
- Skill Markdown: YAML frontmatter required (`name`, `description`)
- JSONL: one JSON object per line, validate against `datasets/manifests/` and `datasets/normalized/` schemas

## Compact instructions

When compacting, preserve: modified file list, validation command outputs, architectural decisions about skill structure. Drop exploration attempts and file read contents.
