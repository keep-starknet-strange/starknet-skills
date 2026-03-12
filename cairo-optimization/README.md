# cairo-optimization

Optimize Cairo smart contracts on Starknet — profile first, optimize second, verify always.

Built for:

- **Cairo devs** reducing gas/steps in hot paths after tests pass
- **Teams** applying BoundedInt optimizations for modular arithmetic and limb assembly
- **Anyone** profiling contract execution to find and fix bottlenecks

Optimizes with evidence, not guesswork.

## Usage

```bash
# Optimize a contract (full profile → plan → optimize → verify)
/cairo-optimization

# Ask for specific help
/cairo-optimization "profile my NTT function and find hotspots"
/cairo-optimization "convert this arithmetic to BoundedInt"
/cairo-optimization "pack these storage fields into fewer slots"
```

## How it works

The skill orchestrates a **4-turn workflow**:

1. **Baseline** — confirm tests pass, profile hot paths, identify top hotspots
2. **Plan** — match hotspots to optimization rules, list anti-patterns found. Wait for confirmation.
3. **Optimize** — apply one class at a time, re-test and re-profile after each change
4. **Verify** — compare before/after profiles, report step deltas, suggest `cairo-auditor` for regression check

## Optimization rules (12 rules, always enforced)

| # | Rule | Instead of | Use |
|---|------|-----------|-----|
| 1 | Combined quotient+remainder | `x / m` + `x % m` | `DivRem::div_rem(x, m)` |
| 2 | Cheap loop conditions | `while i < n` | `while i != n` |
| 3 | Constant powers of 2 | `2_u32.pow(k)` | match-based lookup table |
| 4 | Pointer-based iteration | `*data.at(i)` | `pop_front` / `for` / `multi_pop_front` |
| 5 | Cache array length | `.len()` in loop condition | `let n = data.len();` before loop |
| 6 | Pointer-based slicing | Manual loop extraction | `span.slice(start, length)` |
| 7 | Cheap parity/halving | `index & 1`, `index / 2` | `DivRem::div_rem(index, 2)` |
| 8 | Smallest integer type | `u256` when range < 2^128 | `u128` |
| 9 | Storage slot packing | One slot per field | `StorePacking` trait |
| 10 | BoundedInt for limbs | Bitwise ops / raw math | `bounded_int::{div_rem, mul, add}` |
| 11 | Fast 2-input Poseidon | `poseidon_hash_span([x,y])` | `hades_permutation(x, y, 2)` |
| 12 | Bulk felt252 to BoundedInt | `downcast` / `try_into` | `u128s_from_felt252` + `upcast` |

## What's included

```
cairo-optimization/
  SKILL.md                              # 4-turn orchestration
  references/
    legacy-full.md                      # 12 optimization rules + BoundedInt deep-dive (495 lines)
    profiling.md                        # Profiling CLI, metrics, troubleshooting (219 lines)
    anti-pattern-pairs.md               # 5 anti-pattern/optimized-pattern pairs (101 lines)
  workflows/
    default.md                          # 5-phase workflow reference
  scripts/
    profile.py                          # Profiling CLI (snforge + scarb modes)
    bounded_int_calc.py                 # BoundedInt bounds calculator
```

## Recommended flow

```
cairo-contract-authoring → cairo-testing → cairo-optimization → cairo-auditor
```

Write the contract, add tests, optimize hot paths, then audit. Never optimize before tests pass.
