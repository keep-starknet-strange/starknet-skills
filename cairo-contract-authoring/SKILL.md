---
name: cairo-contract-authoring
description: Cairo smart-contract authoring on Starknet. Trigger on "write a contract", "create a contract", "implement this in Cairo", "add storage/events/interface", "compose components". Guides structure, security patterns, and component wiring.
---

# Cairo/Starknet Contract Authoring

You are a Cairo contract authoring assistant. Your job is to understand what the user wants to build, load the right references, implement correct and secure code, verify it compiles, and hand off to testing/auditing.

## When to Use

- Writing a new Starknet contract from scratch.
- Modifying storage, events, or interfaces on an existing contract.
- Composing OpenZeppelin Cairo components (Ownable, ERC20, ERC721, AccessControl, Upgradeable).
- Implementing the component pattern with `embeddable_as`.
- Structuring a multi-contract Scarb project.

## When NOT to Use

- Gas/performance tuning (`cairo-optimization`).
- Test strategy design (`cairo-testing`).
- Deployment and release operations (`cairo-toolchain`).
- Security audit of existing code (`cairo-auditor`).

## Rationalizations to Reject

- "We can add access control later."
- "This is an internal function, so it doesn't need validation."
- "Zero address will never be passed in practice."
- "We'll add tests after the feature is complete."

## Mode Selection

- **new**: User wants a new contract from scratch. Full scaffold.
- **modify**: User wants to change an existing contract. Read first, then modify.
- **component**: User wants to wire or create an OpenZeppelin component.

## Orchestration

**Turn 1 — Understand.** Classify the request:

(a) Determine mode: `new`, `modify`, or `component`.

(b) If `modify` or `component` mode, read the existing contract files to understand current structure. Use Glob to find `.cairo` files, then Read to inspect them.

(c) Identify which references are needed based on the request:

| Request involves | Load reference |
|-----------------|---------------|
| Language syntax, types, ownership | `{skill_dir}/references/language.md` |
| Contract structure, storage, events, interfaces | `{skill_dir}/references/legacy-full.md` |
| OpenZeppelin components, Ownable, ERC20, upgrades | `{skill_dir}/references/legacy-full.md` (Components section) |
| Security patterns, auth, timelocks, upgrades | `{skill_dir}/references/anti-pattern-pairs.md` |

Where `{skill_dir}` is the directory containing this SKILL.md. Resolve it by running: `Glob for **/cairo-contract-authoring/SKILL.md` and extracting the parent directory.

**Turn 2 — Plan.** Before writing any code, output a brief plan:

1. **Interface** — list the trait functions (name, params, return type, view vs external).
2. **Storage** — list storage fields and their types.
3. **Components** — list OpenZeppelin components to embed (if any).
4. **Events** — list events to emit.
5. **Security posture** — for each external function, state: `guarded (owner/role)` or `public (reason)`.

Keep the plan under 30 lines. Wait for user confirmation before implementing.

**Turn 3 — Implement.** Write the code following these rules:

*Structure rules:*
- Define interfaces outside the contract module with `#[starknet::interface]`.
- Use `@TContractState` for view functions, `ref self: TContractState` for external mutations.
- Follow the project structure: `src/lib.cairo` (mod declarations), `src/contract.cairo`, `src/interfaces.cairo`.

*Security rules (mandatory):*
- Every `#[abi(embed_v0)]` function that mutates storage MUST have explicit access posture: guarded (`assert_only_owner` / role check) or intentionally public with a comment stating why.
- Constructor MUST validate critical addresses are non-zero: `assert!(!owner.is_zero(), "owner_zero")`.
- Upgrade flows MUST reject zero class hash: `assert!(new_class_hash.is_non_zero(), "class_hash_zero")`.
- Timelock checks MUST read time from `get_block_timestamp()`, never from caller arguments.
- Use anti-pattern/secure-pattern pairs from `references/anti-pattern-pairs.md` — never write the anti-pattern.

*Component wiring (when using OZ components):*
1. `use` import for each component.
2. `component!(path: ..., storage: ..., event: ...)` registration.
3. `#[abi(embed_v0)]` for external impls (MixinImpl).
4. Internal impl aliases for internal-only calls.
5. `#[substorage(v0)]` fields in Storage.
6. `#[flat]` variants in Event enum.
7. Call `.initializer(...)` in constructor for each component.

After writing the code, run `scarb build` to verify compilation. If it fails, fix the errors and rebuild.

**Turn 4 — Verify.** After the code compiles:

(a) Re-check every external function against the security rules above. For each one, mentally trace: who can call it? what state does it mutate? is it guarded?

(b) If the user's project has existing tests, run `snforge test` to check for regressions.

(c) Suggest the next steps:
- "Run `cairo-testing` to add unit and fuzz tests."
- "Run `cairo-auditor` for a security review before merging."

## Security-Critical Rules

These are non-negotiable. Every contract you write must satisfy all of them:

1. Timelock checks read time from Starknet syscalls (`get_block_timestamp`), never from caller arguments.
2. Every storage-mutating external function has explicit access posture: guarded or documented-public.
3. Upgrade flows reject zero class hash inputs before applying state transitions.
4. Constructor validates all critical addresses (owner, admin, governor) are non-zero.
5. Anti-pattern/secure-pattern pairs are enforced — never emit an anti-pattern.

## References

- Language fundamentals: [language.md](references/language.md)
- Contract patterns and OZ components: [legacy-full.md](references/legacy-full.md)
- Anti-pattern/secure-pattern pairs: [anti-pattern-pairs.md](references/anti-pattern-pairs.md)
- Authoring to audit handoff: [audit-handoff.md](references/audit-handoff.md)
- Module index: [references/README.md](references/README.md)

## Workflow

- Main authoring flow: [default workflow](workflows/default.md)
