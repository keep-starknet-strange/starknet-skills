# Cairo Attack Vectors (1/4): Access Control + Upgradeability

**1. Immediate upgrade without delay**
- **D:** privileged `upgrade` path calls `replace_class_syscall` or `upgradeable.upgrade` in one transaction with no schedule/execute split.
- **FP:** explicit timelock state with pending hash and `now >= scheduled + delay` check.

**2. Missing class-hash non-zero guard (direct syscall path)**
- **D:** direct `replace_class_syscall(new_class_hash)` without `is_non_zero` guard.
- **FP:** local guard exists or call goes through OZ `UpgradeableComponent` internal guard.

**3. Constructor critical role without non-zero guard**
- **D:** constructor writes `owner/admin/upgrade/governor` directly with no non-zero validation.
- **FP:** explicit constructor guard or trusted initializer with proven internal non-zero check.

**4. Irrevocable privileged role**
- **D:** privileged role seeded at deploy time with no reachable rotate/revoke path.
- **FP:** exposed ownership/role rotation path exists (for example Ownable transfer or AccessControl grant/revoke).

**5. One-shot registration of critical dependency**
- **D:** `register_*` write-once gate sets critical dependency and no recovery setter exists (ForgeYields-style risk).
- **FP:** documented immutable dependency or owner/governance recovery path exists.

**6. Ungated privileged mutation**
- **D:** external `set_*`, `register_*`, `upgrade*`, or pause path mutates privileged state without caller gate.
- **FP:** strict access check in-path (`assert_only_*`, role check, or explicit caller assertion).

**7. Caller alias bypass in access checks**
- **D:** caller stored in alias and compared to wrong role slot or stale authority field.
- **FP:** alias resolves to correct authority source tied to the same function path.

**8. External ABI mutation hidden behind helper**
- **D:** externally callable function delegates to helper that mutates privileged state; entrypoint lacks auth.
- **FP:** helper or parent enforces strict auth with no bypass path.

**9. Upgrade path reachable from broad role**
- **D:** upgrade guarded by overly broad role set (for example generic admin role with many holders).
- **FP:** dedicated upgrade role with constrained grant/revoke controls.

**10. Upgrade initializer omission**
- **D:** class replacement leaves migration state uninitialized, enabling unsafe defaults.
- **FP:** migration is atomically executed or new class is migration-free by design and documented.

**11. Mixed ownership models with orphan authority**
- **D:** contract uses both Ownable and AccessControl; privileged paths depend on stale model.
- **FP:** single authority model or explicit synchronization between models.

**12. Emergency controls not actually privileged**
- **D:** `pause`, `unpause`, or `emergency_*` paths callable through weak predicate.
- **FP:** dedicated emergency role, explicit gate, and no user-facing bypass.

**13. Timelock bypass through alternate upgrade entrypoint**
- **D:** one upgrade path enforces delay while another admin path upgrades immediately.
- **FP:** all upgrade routes converge on a shared timelock gate.

**14. Role-admin misconfiguration enables privilege escalation**
- **D:** `set_role_admin` ties sensitive role admin to itself or user-controlled role without constraints.
- **FP:** role hierarchy maps to governance/owner-only admin chain.

**15. Upgrade auth delegated to mutable external contract**
- **D:** upgrade permission depends on external contract state that can be swapped or desynced.
- **FP:** external dependency is immutable or integrity-checked per call.

**16. Initializer re-entry / double-init path**
- **D:** initializer callable more than once or callable post-deploy by non-trusted party.
- **FP:** initialized flag and strict deploy-time only gate prevent re-entry.

**17. Factory dependency validation missing on one constructor branch**
- **D:** multi-branch init validates non-zero dependencies on one branch but not another.
- **FP:** all constructor/init branches apply identical dependency checks.

**18. Role revocation impossible after bootstrap**
- **D:** privileged role granted in constructor but no external revoke flow (common mis-embed of AccessControl).
- **FP:** role management ABI (`grant/revoke/renounce`) is exposed and reachable.

**19. Pause bypass via equivalent state-mutating function**
- **D:** deposits/transfers are paused, but equivalent state-changing route remains open.
- **FP:** pause invariant enforced at shared internal gate for all equivalent routes.

**20. Admin transfer lockout edge**
- **D:** admin transfer path allows zero/self/inconsistent target and can lock governance flows.
- **FP:** transfer validates target and preserves recoverability guarantees.
