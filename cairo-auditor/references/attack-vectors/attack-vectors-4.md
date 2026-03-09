# Cairo Attack Vectors (4/4): Storage + Components + Trust Chains

**61. Constructor dead parameter**
- **D:** constructor accepts security-critical parameter but never uses it (ForgeYields redeem request pattern).
- **FP:** parameter is explicitly deprecated/compat-only and cannot affect privilege/invariants.

**62. Map-zero default confusion**
- **D:** zero default map entry is treated as initialized/authorized state.
- **FP:** explicit existence flag or non-zero sentinel separates unset from set.

**63. Stale storage after burn/revoke**
- **D:** post-burn/revoke mappings remain active where logic assumes deletion.
- **FP:** retention is intentional and read paths are gated accordingly.

**64. Cross-contract role dependency break**
- **D:** auth depends on mutable external contract state that can desync or be upgraded unexpectedly.
- **FP:** dependency immutable or validated with integrity checks.

**65. External decoder/sanitizer trust assumption**
- **D:** proof/policy validation relies on external decoder contract without integrity pinning.
- **FP:** decoder identity pinned and governed with fail-safe fallback.

**66. Immutable dependency without recovery path**
- **D:** critical dispatcher/dependency set once and not recoverable after failure.
- **FP:** immutable-by-design and explicitly covered by ops runbook/threat model.

**67. Registry hash/domain mismatch**
- **D:** hashed keys/signatures omit domain separator or key-length semantics.
- **FP:** domain-separated and length-aware hashing.

**68. Nonce monotonicity gap across transitions**
- **D:** nonce not incremented on unset/reset transitions, enabling stale signature replay.
- **FP:** nonce increments on every transition that invalidates signed intent.

**69. Event visibility gap for bulk revocation**
- **D:** bulk state updates omit per-item events needed by indexers.
- **FP:** per-item event emission or equivalent query-safe indexing contract.

**70. Upgrade audit trail loss**
- **D:** upgrade/change event omits prior class hash/identifier.
- **FP:** old and new identifiers emitted atomically.

**71. Initialization branch deadlock**
- **D:** constructor config can permanently disable required init branch.
- **FP:** constructor validates branch preconditions or exposes safe alternate init.

**72. Over-broad registry persistence**
- **D:** helper registry accepts arbitrary writes enabling spam/indexer DoS.
- **FP:** bounded writes, scoped permissions, or explicit pagination caps.

**73. Nonce domain collision across action types**
- **D:** same nonce key reused for distinct actions (set/unset/upgrade) enabling cross-action replay.
- **FP:** nonce scope includes action domain and contract context.

**74. Storage key composition collision**
- **D:** composite storage keys omit one discriminator and collide across logical records.
- **FP:** full key tuple encoded in storage address/hash derivation.

**75. Merkle/root history overwrite without uniqueness check**
- **D:** root history accepts repeated/invalid replacement that weakens finality assumptions.
- **FP:** root insertion enforces expected progression and duplicate handling rules.

**76. Proof verifier address mutability without governance delay**
- **D:** verifier endpoint mutable via immediate admin call, enabling sudden trust shift.
- **FP:** verifier changes timelocked and event-auditable.

**77. ABI variant fallback masks integration breakage**
- **D:** integration tries multiple ABI variants and proceeds on partial decode assumptions.
- **FP:** one canonical ABI and strict decode failure handling.

**78. Pending-owner/admin stale state leak**
- **D:** ownership transfer leaves stale pending/old authority state that still influences checks.
- **FP:** old pending authority cleared on transfer completion.

**79. Wrong event payload branch**
- **D:** event emits mismatched payload (for example claim payload in refund path) and corrupts off-chain state.
- **FP:** event payload strictly tied to executed branch and tested.

**80. Unbounded user-controlled iteration**
- **D:** loops over user-controlled array/span without bound checks can DoS execution.
- **FP:** explicit max bounds and fail-fast checks enforce bounded work.
