---
name: cairo-contract-authoring
description: Guides Cairo smart-contract authoring on Starknet with safe structure choices, component composition, and implementation workflow references.
license: Apache-2.0
metadata: {"author":"starknet-skills","version":"0.1.1","org":"keep-starknet-strange","source":"starknet-agentic"}
keywords: [cairo, contracts, starknet, openzeppelin, components, storage, interfaces]
allowed-tools: [Bash, Read, Write, Glob, Grep, Task]
user-invocable: true
---

# Cairo Contract Authoring

Use this as the entrypoint for implementation decisions; load references only as needed.

## When to Use

- Writing a new Starknet contract.
- Modifying storage/events/interfaces.
- Composing OpenZeppelin Cairo components.

## When NOT to Use

- Gas/performance tuning (`cairo-optimization`).
- Test strategy design (`cairo-testing`).
- Deployment and release operations (`cairo-toolchain`).

## Quick Start

1. Define interface and storage boundaries first.
2. Implement minimal external/write surface.
3. Add explicit auth and invariant checks.
4. Add tests before broadening feature surface.
5. Run an audit pass with `cairo-auditor`.

## Workflow

- Main authoring flow: [default workflow](workflows/default.md)

## References

- Detailed authoring reference: [legacy reference](references/legacy-full.md)
- Module index: [references index](references/README.md)
