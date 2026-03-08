# Contract Benchmark Fixtures

Deterministic Cairo contract fixtures used by `scripts/quality/benchmark_contract_skills.py`.

## Fixtures

- `secure_owned_vault/`: a contract that follows `cairo-contract-authoring` + `cairo-optimization` guidance (owner guard, constructor non-zero check, `DivRem::div_rem` split pattern).
- `insecure_owned_vault/`: intentionally weak variant used as a negative control (missing owner guard, split via `/` + `%`).

Each fixture is a standalone Scarb package with local unit tests runnable via `snforge test`.
