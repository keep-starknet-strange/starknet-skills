# Wave-2 External Scan Delta (2026-03-09 v3)

- Baseline v2: `evals/reports/data/external-repo-scan-wave2-2026-03-09-v2.json`
- Rerun v3: `evals/reports/data/external-repo-scan-wave2-2026-03-09-v3.json`

- Baseline v2 findings: **31**
- Rerun v3 findings: **30**
- Delta: **-1**

## By Class

| Class | Baseline | Rerun | Delta |
| --- | ---: | ---: | ---: |
| `CEI_VIOLATION_ERC1155` | 0 | 2 | +2 |
| `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` | 10 | 8 | -2 |
| `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` | 17 | 11 | -6 |
| `IRREVOCABLE_ADMIN` | 0 | 7 | +7 |
| `NO_ACCESS_CONTROL_MUTATION` | 3 | 1 | -2 |
| `UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD` | 1 | 1 | +0 |

- Removed: **11**

| Repo | File | Class |
| --- | --- | --- |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/account.cairo` | `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/erc1155.cairo` | `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/erc1155.cairo` | `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/erc20.cairo` | `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/erc20.cairo` | `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/erc721.cairo` | `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/erc721.cairo` | `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` |
| `OpenZeppelin/cairo-contracts` | `packages/presets/src/eth_account.cairo` | `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` |
| `OpenZeppelin/cairo-contracts` | `packages/upgrades/src/upgradeable.cairo` | `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` |
| `karnotxyz/starknet_bridge` | `starknet_bridge/src/bridge/token_bridge.cairo` | `NO_ACCESS_CONTROL_MUTATION` |
| `karnotxyz/starknet_bridge` | `starknet_bridge/src/erc20/erc20.cairo` | `NO_ACCESS_CONTROL_MUTATION` |

- Added: **10**

| Repo | File | Class |
| --- | --- | --- |
| `OpenZeppelin/cairo-contracts` | `packages/token/src/erc1155/erc1155.cairo` | `CEI_VIOLATION_ERC1155` |
| `OpenZeppelin/cairo-contracts` | `packages/token/src/erc721/erc721.cairo` | `CEI_VIOLATION_ERC1155` |
| `keep-starknet-strange/piltover` | `src/appchain.cairo` | `IRREVOCABLE_ADMIN` |
| `keep-starknet-strange/piltover` | `src/config/mock.cairo` | `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` |
| `keep-starknet-strange/piltover` | `src/config/mock.cairo` | `IRREVOCABLE_ADMIN` |
| `spiko-tech/starknet-contracts` | `src/lib.cairo` | `IRREVOCABLE_ADMIN` |
| `spiko-tech/starknet-contracts` | `src/permission_manager.cairo` | `IRREVOCABLE_ADMIN` |
| `spiko-tech/starknet-contracts` | `src/redemption.cairo` | `IRREVOCABLE_ADMIN` |
| `typhoonmixer/typhoon-contracts` | `src/NoteAccount.cairo` | `IRREVOCABLE_ADMIN` |
| `typhoonmixer/typhoon-contracts` | `src/Typhoon.cairo` | `IRREVOCABLE_ADMIN` |

