# Cairo Attack Vectors (2/4): External Calls + Reentrancy + Messaging

**13. CEI violation on ERC1155 transfer path**
- **D:** state mutation occurs after `safe_transfer_from` (or helper chain reaching it).
- **FP:** all critical state committed before interaction or robust non-reentrant guard exists.

**14. Session self-call hazard**
- **D:** session execution loop permits calls to account contract itself.
- **FP:** explicit self-target block and policy constraints prevent self-call.

**15. Selector fallback assumption**
- **D:** on syscall error, code retries alternate selector in same execution path.
- **FP:** single canonical selector with fail-fast handling.

**16. Untrusted callback caller**
- **D:** callback handler mutates state without validating `msg.sender`/caller contract identity.
- **FP:** callback bound to expected contract address.

**17. External call proxy without target constraints**
- **D:** privileged function forwards arbitrary calls (`call_contract_syscall`) to unconstrained target.
- **FP:** target/method allowlist or strict Merkle/policy verification.

**18. Cross-function reentrancy window**
- **D:** helper performs external interaction, parent mutates critical state afterward.
- **FP:** interaction function only called after all state effects or lock is global across helper chain.

**19. Transfer consistency mismatch**
- **D:** `transfer_from` disabled while `safe_transfer_from` still allows equivalent state movement unexpectedly.
- **FP:** behavior documented and intentionally constrained by separate invariant checks.

**20. Caller-controlled reward contract invocation**
- **D:** harvest/claim path accepts arbitrary contract address and invokes it.
- **FP:** target is policy-checked and caller scope tightly privileged.

**21. L1/L2 message replay gap**
- **D:** consumed message hash/nonce not tracked, allowing repeated processing.
- **FP:** replay protection with hash+nonce uniqueness.

**22. Callback state confusion with stale flags**
- **D:** callback depends on state flags set later in the same transaction.
- **FP:** callback reads state written before interaction.

**23. Fee-transfer call result ignored**
- **D:** transfer syscall/call result ignored and state advances as if payment succeeded.
- **FP:** failure path reverts and prevents downstream state changes.

**24. External denial path silently swallowed**
- **D:** errors caught but execution continues with optimistic state transitions.
- **FP:** explicit revert on denial or compensating rollback.
