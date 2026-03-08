# starknet-skills

Production-grade skills for high-quality Cairo and Starknet security engineering.

This repository is focused on reasoning quality, audit rigor, and deterministic quality gates.
Operational SDK and protocol execution playbooks belong in `starknet-agentic` / `starkzap`.

## Scope Boundary

- In scope: Cairo correctness, security review patterns, Starknet architectural facts, testing and hardening workflows.
- Out of scope: runtime tool execution guides (MCP tool usage, SDK call recipes, protocol operation runbooks).

## Modules

- `cairo-auditor/` — flagship workflow skill for Cairo security review.
- `cairo-contract-authoring/` — contract structure and implementation patterns.
- `cairo-testing/` — Starknet Foundry testing and fuzzing workflows.
- `cairo-optimization/` — performance and low-level Cairo optimization rules.
- `cairo-toolchain/` — build/declare/deploy/verification and release operations.
- `account-abstraction/` — Starknet account abstraction and account-security semantics.
- `starknet-network-facts/` — network-level constraints and chain behavior guardrails.
- `openzeppelin-cairo/` — OpenZeppelin Cairo composition and hardening patterns.

## Data + Evals

- `datasets/` stores the full audit-to-skills pipeline (`ingest -> segment -> normalize -> distill`).
- `evals/` stores held-out evaluation cases and scorecards.

Do not merge skill changes without updating or passing the corresponding evaluation set.

## Governance

- Contribution guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Code of conduct: `CODE_OF_CONDUCT.md`

## License

MIT (see `LICENSE`).
