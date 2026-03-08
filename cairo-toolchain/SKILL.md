---
name: cairo-toolchain
description: Use for Starknet build, declare, deploy, verify, and release operations with a deterministic workflow and references for command-level details.
license: Apache-2.0
metadata: {"author":"starknet-skills","version":"0.1.1","org":"keep-starknet-strange","source":"starknet-agentic"}
keywords: [cairo, deploy, sncast, starknet, sepolia, mainnet, declare, verification]
allowed-tools: [Bash, Read, Write, Glob, Grep, Task]
user-invocable: true
---

# Cairo Toolchain

Use this entrypoint for deployment/release sequencing; load command details from references.

## When to Use

- Building and declaring class hashes.
- Deploying accounts and contracts.
- Verifying contract artifacts and release evidence.

## When NOT to Use

- Contract implementation (`cairo-contract-authoring`).
- Test suite design (`cairo-testing`).
- Pure optimization passes (`cairo-optimization`).

## Quick Start

1. Pin tool versions.
2. Build deterministic artifacts.
3. Declare before deploy.
4. Verify deployment outputs and provenance.
5. Store release evidence.

## Workflow

- Main deployment workflow: `workflows/default.md`

## References

- Detailed toolchain commands: `references/legacy-full.md`
- Module index: `references/README.md`
