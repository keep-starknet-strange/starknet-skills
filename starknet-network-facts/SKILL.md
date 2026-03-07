---
name: starknet-network-facts
description: Starknet network-level constraints and protocol facts that impact contract safety and agent reasoning.
---

# Starknet Network Facts

## When to Use

- Reasoning about chain behavior assumptions in contract logic.
- Validating time, fee, and transaction-version dependencies.

## When NOT to Use

- Contract implementation details unrelated to chain behavior.

## Core Focus

- transaction version expectations
- fee token and bounds assumptions
- block-time-sensitive logic
- sequencer and inclusion model implications
