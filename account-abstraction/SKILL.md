---
name: account-abstraction
description: Starknet account abstraction correctness and security guidance for validate/execute paths, nonces, signatures, and session policies.
---

# Account Abstraction

## When to Use

- Reviewing account contract validation and execution paths.
- Designing session-key policy boundaries.
- Validating nonce and signature semantics.

## When NOT to Use

- General contract authoring not involving account semantics.

## Core Focus

- `__validate__` constraints and DoS resistance.
- `__execute__` policy enforcement correctness.
- Replay protection and domain separation.
- Privileged selector and self-call protection.
