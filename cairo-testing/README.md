# cairo-testing

Write comprehensive tests for Cairo smart contracts on Starknet — unit, integration, fuzz, and regression.

Built for:

- **Cairo devs** adding tests to a new or existing contract
- **Teams** needing full coverage: success paths, auth failures, event assertions, edge cases
- **Anyone** turning audit findings into permanent regression tests

Tests the contract before the auditor does.

## Usage

```bash
# Write tests for a contract (full coverage)
/cairo-testing

# Ask for specific help
/cairo-testing "add fuzz tests for the deposit function"
/cairo-testing "write regression test for this access control finding"
/cairo-testing "integration tests for my ERC20 + AMM interaction"
```

## How it works

The skill orchestrates a **4-turn workflow**:

1. **Understand** — read the contract, identify all externals, find existing tests, load snforge references
2. **Plan** — output test plan (functions, positive/negative paths, events, fuzz targets). Wait for confirmation.
3. **Implement** — write tests following mandatory coverage rules, verify with `snforge test`
4. **Verify** — walk coverage checklist, report gaps, suggest `cairo-auditor` for additional test targets

## Coverage rules (always enforced)

Every test suite this skill writes satisfies these non-negotiable rules:

- Every storage-mutating external has both a success and a failure test
- Every access-controlled function tested with authorized and unauthorized callers
- Expected panics use `#[should_panic(expected: '...')]` with the exact message
- Event assertions use `spy_events` + `assert_emitted` with full event data
- Fuzz tests use fixed seeds (`seed: 12345`) for reproducibility

## What's included

```
cairo-testing/
  SKILL.md                          # 4-turn orchestration
  references/
    legacy-full.md                  # snforge API: tests, cheatcodes, fuzzing, forks (396 lines)
  workflows/
    default.md                      # 5-phase workflow reference
```

## Recommended flow

```
cairo-contract-authoring → cairo-testing → cairo-auditor
```

Write the contract, add tests, then audit. The testing skill connects both directions — it builds on the contract authoring output and surfaces gaps for the auditor.
