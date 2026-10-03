# Sierra v3 Evaluation Guide

## Overview

Sierra v3 adds **per-finding IR confirmation** and **signal-quality tiers** to the StarkNet skills evaluation pipeline. Sierra is positioned as a **confirmation layer** (not a standalone verdict engine) that provides function-level evidence for findings.

## Signal Quality Tiers

| Tier | Criteria | Example |
|------|----------|---------|
| `high` | `sierra_json` artifact with function-order/invocation signal | Full CEI confirmation |
| `medium` | `contract_class` or `starknet_artifacts.json` only | Marker-level evidence |
| `low` | No analyzable artifact or ambiguous mapping | Needs fallback |

## IR Confirmation Status

Each finding receives one of:

- **`confirmed`**: IR evidence supports the finding (at matching quality tier)
- **`missing`**: No IR evidence available OR high-quality signal explicitly absent
- **`unknown`**: Analysis could not be performed (e.g., repo unreachable)

### Rationale

When `ir_confirmation` is `missing`, the `rationale` field explains why:

- `"missing because no signal"` — no analyzable artifact was produced
- `"missing despite high-quality signal"` — high-quality artifact exists but does not confirm this finding class

## CEI Confirmation Semantics

- **Strong confirmation**: function-level `external → write` order in `sierra_json`
- **Weak telemetry**: repo-level co-occurrence counts (never treated as strong confirmation)

## Output Format

### Markdown Report Columns

| Column | Description |
|--------|-------------|
| `finding_id` | Unique identifier for the finding |
| `repo_url` | GitHub URL of the analyzed repo |
| `finding_class` | Category of the finding (e.g., CEI) |
| `signal_quality` | `high` \| `medium` \| `low` |
| `ir_confirmation` | `confirmed` \| `missing` \| `unknown` |
| `artifact_source` | Comma-separated list of artifact types found |
| `rationale` | Human-readable explanation |

### JSON Report Structure

```json
{
  "total_findings": 42,
  "ir_confirmed": 38,
  "high_quality_signals": 20,
  "coverage_pct": 90.5,
  "rows": [ ... ]
}
```

## CI Behavior

- **PR CI** (`pr-sierra-auxiliary`): Fail-open. Results are logged but never block merging.
- **Nightly/Release** (`sierra-quality-nightly`): Enforces minimum coverage thresholds when `fail_on_low_quality` is enabled (default for scheduled runs).

## Building with Multiple Profiles

The pipeline attempts builds with both `dev` and `release` Scarb profiles. The first profile that produces analyzable Sierra artifacts is recorded. Toolchain retries with `--ignore-cairo-version` fallback are applied automatically.

## References

- [Scarb Profiles](https://docs.swmansion.com/scarb/docs/reference/profiles.html)
- [Scarb Contract Target](https://docs.swmansion.com/scarb/docs/extensions/starknet/contract-target.html)
- [Scarb Targets (sierra-text)](https://docs.swmansion.com/scarb/docs/reference/targets.html)
- [Caracal (Sierra Analyzer)](https://raw.githubusercontent.com/crytic/caracal/master/README.md)
