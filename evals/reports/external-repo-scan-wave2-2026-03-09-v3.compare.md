# Wave-2 Rerun Delta (v2 -> v3)

| Metric | Baseline | Rerun | Delta |
| --- | ---: | ---: | ---: |
| Findings | 31 | 30 | -1 |

## By Class

| Class | Baseline | Rerun | Delta |
| --- | ---: | ---: | ---: |
| `CRITICAL_ADDRESS_INIT_WITHOUT_NONZERO_GUARD` | 10 | 10 | 0 |
| `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK` | 17 | 17 | 0 |
| `NO_ACCESS_CONTROL_MUTATION` | 3 | 2 | -1 |
| `UPGRADE_CLASS_HASH_WITHOUT_NONZERO_GUARD` | 1 | 1 | 0 |

- Removed: **1**

| Repo | File | Class |
| --- | --- | --- |
| `karnotxyz/starknet_bridge` | `starknet_bridge/src/bridge/token_bridge.cairo` | `NO_ACCESS_CONTROL_MUTATION` |

- Added: **0**
