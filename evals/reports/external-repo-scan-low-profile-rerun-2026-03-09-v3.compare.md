# Low-Profile Rerun Delta (v1 -> v3)

- Baseline: `/Users/espejelomar/StarkNet/ai-agents-starknet/starknet-skills/evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09.json`
- Rerun: `/Users/espejelomar/StarkNet/ai-agents-starknet/starknet-skills/evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09-v3.json`

- Baseline findings: **32**
- Rerun findings: **27**
- Delta: **-5**

## By Class

| Class | Baseline | Rerun | Delta |
| --- | ---: | ---: | ---: |
| `CEI_VIOLATION_ERC1155` | 1 | 0 | -1 |
| `CONSTRUCTOR_DEAD_PARAM` | 1 | 1 | 0 |
| `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` | 14 | 14 | 0 |
| `FEES_RECIPIENT_ZERO_DOS` | 1 | 1 | 0 |
| `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` | 8 | 8 | 0 |
| `NO_ACCESS_CONTROL_MUTATION` | 6 | 2 | -4 |
| `UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD` | 1 | 1 | 0 |

- Removed: **5**

| Repo | File | Class |
| --- | --- | --- |
| `ForgeYields/starknet_vault_kit` | `packages/vault/src/redeem_request/redeem_request.cairo` | `CEI_VIOLATION_ERC1155` |
| `ForgeYields/starknet_vault_kit` | `packages/vault/src/redeem_request/redeem_request.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `StarkVote/starkvote` | `contracts/src/poll.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `StarkVote/starkvote` | `contracts/src/voter_set_registry.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `medialane-io/medialane-contracts` | `contracts/Medialane-Protocol/src/core/medialane.cairo` | `NO_ACCESS_CONTROL_MUTATION` |

- Added: **0**

