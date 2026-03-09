# Finding Validation (Cairo)

Every finding must pass this gate before reporting.

## FP Gate (Required)

Drop the finding if any check fails.

1. **Concrete attack path** exists: caller -> reachable function -> state transition -> loss/impact.
2. **Reachability**: attacker can call the path under actual access control (`assert_only_*`, role checks, caller checks, account validation paths).
3. **No existing guard** blocks the attack (`assert`, non-reentrant lock, OZ component guard, explicit invariant check).

## Confidence Score

Start at `100`, apply deductions:

- Privileged caller required (`owner/admin/governance`) -> `-25`
- Partial path (cannot prove full transition to impact) -> `-20`
- Impact self-contained to attacker-only funds -> `-15`
- Requires narrow environmental assumptions (sequencer timing / unusual offchain behavior) -> `-10`

Report format uses `[score]` confidence tags.

## Do Not Report

- Style/naming/comments/NatSpec-only findings.
- Generic centralization notes without concrete exploit path.
- Gas-only micro-optimizations.
- Duplicate root causes already captured by a higher-confidence finding.

## Cairo-Specific Notes

- Distinguish direct `replace_class_syscall` from OZ `UpgradeableComponent` paths.
- For constructor/address findings, separate critical role loss from expected deploy-time config.
- For session/account flows, reason across `__validate__` and `__execute__` jointly.
