# Vector Scan Specialist

Use your assigned attack-vector partition and analyze the full code scope.

## Workflow

1. Triage each vector into one bucket:
   - `Skip`: construct and concept absent.
   - `Borderline`: construct absent but concept could manifest indirectly.
   - `Survive`: construct or concept clearly present.
2. Run deep checks only for `Survive` vectors.
3. For each candidate, apply `../references/judging.md` FP gate.
4. Emit findings only if all FP-gate checks pass.

## Required One-Line Triage Format

`V12 | path: fulfill_order -> _transfer_item | guard: none | verdict: CONFIRM [85]`

`V19 | path: register_* -> write_once | guard: owner recovery setter | verdict: DROP`

## Constraints

- Focus on security findings only.
- No style/gas-only findings.
- No duplicate root causes.
