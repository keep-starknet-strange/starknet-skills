# Cairo Attack Vectors (3/4): Math + Economic Logic

**25. Unchecked fee bound**
- **D:** external/config fee parameter stored/forwarded without max bound.
- **FP:** explicit bound assertion in same call path.

**26. Fee recipient zero-address DoS**
- **D:** fee recipient stored without non-zero guard and later used for transfer.
- **FP:** guard exists at assignment or transfer path gracefully handles zero.

**27. Rounding bias against one side**
- **D:** repeated rounding direction systematically benefits one actor (e.g., redeemer losses rounded up).
- **FP:** documented intentional direction with invariant tests validating fairness bounds.

**28. Felt/int boundary misuse**
- **D:** implicit felt/u* conversion without range checks in financial paths.
- **FP:** checked conversion or bounded domain assertions.

**29. Underflow guarded only by type assumptions**
- **D:** subtraction in sensitive accounting path relies on unchecked preconditions.
- **FP:** explicit `amount <= balance` or equivalent invariant before subtraction.

**30. Oracle trust concentration**
- **D:** single role controls key value inputs (AUM/price) with weak second-layer constraints.
- **FP:** independent checks (caps, deltas, circuit breakers, governance delay).

**31. Share dilution by repeated fee minting edge**
- **D:** fee minting formula accumulates hidden dilution due to rounding asymmetry.
- **FP:** transparent accounting with invariant tests for bounded drift.

**32. Boundary double-spend in period resets**
- **D:** hard reset windows allow back-to-back max spend around boundary.
- **FP:** sliding window or explicitly accepted/documented risk with controls.

**33. Missing amount floor in transfer/approval policy**
- **D:** zero-amount calls can still trigger harmful side effects (approval reset, griefing).
- **FP:** zero amount blocked for side-effecting selectors.

**34. Denominator stabilization hack leaks value**
- **D:** ad-hoc `+1` denominator or sentinel denominator introduces systematic extraction.
- **FP:** stable mathematically justified formulation with tests.

**35. Multi-token spending policy mismatch**
- **D:** policy enforced only for one token while selector scope permits others.
- **FP:** explicit token gate across all spend selectors.

**36. Repricing path bypasses caps through alternate function**
- **D:** cap/limit enforced in one update path but bypassed through settlement/report path.
- **FP:** shared cap invariant enforced across all repricing paths.
