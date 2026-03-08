---
name: openzeppelin-cairo
description: OpenZeppelin Cairo composition, upgrade, access control, and safety patterns.
license: Apache-2.0
metadata: {"author":"starknet-skills","version":"0.1.1","org":"keep-starknet-strange"}
keywords: [openzeppelin, cairo, components, upgradeability, access-control]
allowed-tools: [Bash, Read, Write, Glob, Grep, Task]
user-invocable: true
---

# OpenZeppelin Cairo

## When to Use

- Integrating OZ Cairo components (ownable, access, token, upgradeable, security).
- Reviewing component composition and privileged function exposure.

## When NOT to Use

- Non-OZ custom architecture not relying on component patterns.

## Core Focus

- safe component composition and substorage layout
- initializer and upgrade protections
- role/owner boundary correctness
- implications of embedded impl selectors
