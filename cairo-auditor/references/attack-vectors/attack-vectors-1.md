# Cairo Attack Vectors (1/4): Access + Upgradeability

**1. Immediate upgrade without delay**
- **D:** privileged `upgrade` path calls `replace_class_syscall`/`upgradeable.upgrade` in same transaction, no schedule/execute separation.
- **FP:** explicit timelock with pending hash and `now >= scheduled + delay` gate.

**2. Missing class-hash non-zero guard (direct syscall path)**
- **D:** direct `replace_class_syscall(new_class_hash)` without `is_non_zero` guard.
- **FP:** guard exists locally or call uses OZ `UpgradeableComponent` that enforces non-zero internally.

**3. Constructor critical role without non-zero guard**
- **D:** constructor writes `owner/admin/upgrade/governor` addresses from params with no zero check.
- **FP:** role intentionally deferred and explicitly set in mandatory follow-up initializer with guard.

**4. Irrevocable privileged role**
- **D:** constructor seeds privileged role but code exposes no rotation/revocation path.
- **FP:** explicit rotate/transfer/renounce flow exists for the same role.

**5. One-shot registration of critical dependency**
- **D:** `register_*` path write-once gates critical address and there is no recovery setter.
- **FP:** owner/governance recovery path exists or dependency is immutable by design and documented.

**6. Ungated privileged mutation**
- **D:** external/public `set_*`, `register_*`, or `upgrade*` mutates critical state with no caller gate.
- **FP:** robust access control (`assert_only_*`, role or caller assertion) on same path.

**7. Caller alias bypass in access checks**
- **D:** caller loaded into variable and compared to unrelated state (wrong role field / stale storage slot).
- **FP:** alias flows to correct authority check and is tied to the exact privileged role.

**8. External ABI mutation hidden behind helper**
- **D:** externally callable function delegates to helper that writes privileged state; parent lacks gate.
- **FP:** gate is in parent or helper and cannot be bypassed.

**9. Upgrade path reachable from non-owner role**
- **D:** upgrade function checks a broad role (or no role hierarchy constraints) enabling unintended upgrader set.
- **FP:** strict dedicated upgrade role with controlled grant/revoke.

**10. Upgrade initializer omission after class replacement**
- **D:** upgrade swaps class but omits required migration/initialization, leaving unsafe defaults.
- **FP:** deterministic migration call executed atomically or proven unnecessary.

**11. Mixed ownership models with orphan role**
- **D:** both Ownable and AccessControl are present and one privileged path is governed by stale/orphan authority.
- **FP:** single authoritative model or explicit bridge between owner and roles.

**12. Emergency controls not actually privileged**
- **D:** `pause`, `unpause`, `emergency_*` paths lack strict auth or rely on mutable weak predicate.
- **FP:** emergency controls require dedicated role and cannot be called through user-facing paths.
