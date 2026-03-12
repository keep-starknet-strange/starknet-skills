# cairo-contract-authoring

Write Cairo smart contracts on Starknet — correct, secure, and component-ready from the start.

Built for:

- **Cairo devs** starting a new Starknet contract
- **Teams** composing OpenZeppelin components (Ownable, ERC20, ERC721, AccessControl, Upgradeable)
- **Anyone** modifying storage, events, or interfaces on existing contracts

Writes code with security patterns baked in — not bolted on after.

## Usage

```bash
# Write a new contract (full scaffold)
/cairo-contract-authoring

# Ask for specific help
/cairo-contract-authoring "ERC20 token with owner-only minting and upgradeable"
/cairo-contract-authoring "add AccessControl to my existing contract"
```

## How it works

The skill orchestrates a **4-turn workflow**:

1. **Understand** — classify your request (new contract / modify existing / wire component), read existing code, load the right references
2. **Plan** — output interface, storage, component, event, and security posture plan. Wait for your confirmation.
3. **Implement** — write code following mandatory security rules, wire OZ components, verify compilation with `scarb build`
4. **Verify** — re-check every external function for security posture, run tests, suggest `cairo-testing` and `cairo-auditor` as next steps

## Security rules (always enforced)

Every contract this skill writes satisfies these non-negotiable rules:

- Every storage-mutating external function has explicit access posture: **guarded** (owner/role check) or **documented-public** (with inline reason)
- Constructor validates all critical addresses are non-zero
- Upgrade flows reject zero class hash
- Timelock checks read from `get_block_timestamp()`, never from caller arguments
- Anti-pattern/secure-pattern pairs are enforced — the anti-pattern is never written

## What's included

```
cairo-contract-authoring/
  SKILL.md                          # 4-turn orchestration
  references/
    language.md                     # Cairo language fundamentals (320 lines)
    legacy-full.md                  # Contract patterns + OZ components (493 lines)
    anti-pattern-pairs.md           # 6 secure/insecure code pairs (140 lines)
    audit-handoff.md                # Post-authoring audit flow
  workflows/
    default.md                      # 5-phase workflow reference
```

## Recommended flow

```
cairo-contract-authoring → cairo-testing → cairo-auditor
```

Write the contract, add tests, then audit. The authoring skill includes a handoff step that connects to the auditor.
