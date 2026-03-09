# Cairo Attack Vectors (4/4): Storage + Components + Trust Chains

**37. Constructor dead parameter**
- **D:** constructor accepts parameter never used in state/init path.
- **FP:** parameter intentionally unused only when explicitly documented and harmless.

**38. Map-zero default confusion**
- **D:** zero default map entry is treated as initialized/valid state.
- **FP:** explicit existence flags or sentinel distinction.

**39. Stale storage after burn/revoke**
- **D:** identity/state mappings remain readable/active after burn/revoke when logic assumes deletion.
- **FP:** stale retention intentional and callers gated accordingly.

**40. Cross-contract role dependency break**
- **D:** authorization depends on mutable external contract state that can desync.
- **FP:** dependency is immutable or integrity-checked before sensitive actions.

**41. External decoder/sanitizer trust assumption**
- **D:** policy verification depends on external decoder contract without integrity guarantees.
- **FP:** decoder identity pinned + governance controls + fail-safe checks.

**42. Immutable dependency without recovery path**
- **D:** critical dependency set once with no upgrade/recovery mechanism.
- **FP:** immutable-by-design and covered by explicit threat model/ops runbook.

**43. Registry hash/domain mismatch**
- **D:** hashed keys/signatures omit domain separators or key length semantics.
- **FP:** domain-separated and length-aware hashing.

**44. Nonce monotonicity gap across state transitions**
- **D:** nonce not incremented on all state-reset/unset paths enabling stale replay.
- **FP:** nonce increments across every state transition that can invalidate old signatures.

**45. Event visibility gap for mass revocation**
- **D:** bulk operation updates state without emitting per-item events needed by indexers.
- **FP:** per-item event emission or documented alternative query guarantee.

**46. Upgrade/change audit trail loss**
- **D:** upgrade event omits previous hash/identifier, hindering forensic reconstruction.
- **FP:** event includes old and new identifiers.

**47. Initialization branch deadlock**
- **D:** constructor config can permanently disable required init branch with no alternative path.
- **FP:** constructor validates init preconditions or offers explicit alternate init flow.

**48. Over-broad persistence in helper registries**
- **D:** helper/metadata registries allow arbitrary writes causing spam or indexer DoS.
- **FP:** bounded writes, scoped permissions, or rate-limiting controls.
