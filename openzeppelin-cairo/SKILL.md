---
name: openzeppelin-cairo
description: OpenZeppelin Cairo composition, upgrade, access control, and safety patterns.
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
