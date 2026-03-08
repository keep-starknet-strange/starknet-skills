# Low-Profile Rerun Comparison (2026-03-09)

- Baseline labels: `/Users/espejelomar/StarkNet/ai-agents-starknet/starknet-skills/evals/reports/data/external-repo-scan-low-profile-2026-03-08-v2.labels.jsonl`
- New findings: `/Users/espejelomar/StarkNet/ai-agents-starknet/starknet-skills/evals/reports/data/external-repo-scan-low-profile-rerun-2026-03-09.findings.jsonl`

## Metrics on the same labeled set

| Run | TP | FP | FN | TN | Precision | Recall | Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline (stored `predicted_detect`) | 19 | 1 | 0 | 8 | 0.950 | 1.000 | 0.964 |
| Rerun (current detector output) | 19 | 1 | 0 | 8 | 0.950 | 1.000 | 0.964 |

- Prediction changes on labeled findings: **0**

## Additional findings outside labeled pack

- Additional findings: **12**

By class:

- `CEI_VIOLATION_ERC1155`: 1
- `CONSTRUCTOR_DEAD_PARAM`: 1
- `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD`: 3
- `FEES_RECIPIENT_ZERO_DOS`: 1
- `NO_ACCESS_CONTROL_MUTATION`: 6

| Repo | File | Class |
| --- | --- | --- |
| `ForgeYields/starknet_vault_kit` | `packages/vault/src/aum_provider/aum_provider_4626/aum_provider_4626.cairo` | `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` |
| `ForgeYields/starknet_vault_kit` | `packages/vault/src/redeem_request/redeem_request.cairo` | `CEI_VIOLATION_ERC1155` |
| `ForgeYields/starknet_vault_kit` | `packages/vault/src/redeem_request/redeem_request.cairo` | `CONSTRUCTOR_DEAD_PARAM` |
| `ForgeYields/starknet_vault_kit` | `packages/vault/src/redeem_request/redeem_request.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `ForgeYields/starknet_vault_kit` | `packages/vault/src/vault/vault.cairo` | `FEES_RECIPIENT_ZERO_DOS` |
| `ForgeYields/starknet_vault_kit` | `packages/vault_allocator/src/periphery/price_router/price_router.cairo` | `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` |
| `ForgeYields/starknet_vault_kit` | `packages/vault_allocator/src/periphery/price_router_vesu/price_router_vesu.cairo` | `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` |
| `StarkVote/starkvote` | `contracts/src/poll.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `StarkVote/starkvote` | `contracts/src/voter_set_registry.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `cavos-labs/argus` | `contracts/src/jwks_registry.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `medialane-io/medialane-contracts` | `contracts/Medialane-Protocol/src/core/medialane.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `salazarsebas/Zylith` | `src/verifier/coordinator.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
