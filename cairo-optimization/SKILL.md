---
name: cairo-optimization
description: Improves Cairo performance and resource usage after correctness is established, with an entry workflow and references for full optimization patterns.
license: Apache-2.0
metadata: {"author":"feltroidprime","contributors":["starknet-agentic"],"version":"1.1.1","org":"keep-starknet-strange","upstream":"https://github.com/feltroidprime/cairo-skills/tree/main/skills/cairo-coding"}
keywords: [cairo, optimization, gas, bounded-int, storage-packing, arithmetic, starknet]
allowed-tools: [Bash, Read, Write, Glob, Grep, Task]
user-invocable: true
---

# Cairo Optimization

Apply only after tests pass and behavior is locked.

## When to Use

- Improving gas/resource usage in hot paths.
- Rewriting expensive loops/arithmetic patterns.
- Optimizing storage layout and integer choices.

## When NOT to Use

- Early feature prototyping without tests.
- Security review as a substitute for correctness proofs.

## Quick Start

1. Confirm baseline behavior with tests.
2. Identify hotspots via resource reports.
3. Apply one optimization class at a time.
4. Re-run tests and compare resource deltas.

## Workflow

- Main optimization flow: [default workflow](workflows/default.md)

## References

- Detailed optimization rules: [legacy reference](references/legacy-full.md)
- Module index: [references index](references/README.md)
