---
name: cross-skill-handoff
description: Canonical handoff template and chain mappings between starknet-skills modules.
---

# Cross-Skill Handoff

When a skill completes its workflow, it outputs a **Handoff Block** — a structured summary the user can pass to the next skill as input context. This replaces the generic "run X next" suggestion with actionable data.

## Handoff Block Format

Every handoff block uses this exact template:

```markdown
## Handoff: {source-skill} → {target-skill}

**Files touched:**
- `src/contract.cairo` (new / modified)
- `src/interfaces.cairo` (new / modified)

**Security posture:**
| Function | Access | Notes |
|----------|--------|-------|
| `transfer` | guarded (owner) | — |
| `get_balance` | public (view) | read-only |

**Verified:**
- [ ] `scarb build` passes
- [ ] `snforge test` passes (N tests)
- [ ] All externals have explicit access posture

**Open concerns:**
- (anything the next skill should focus on)

**Suggested focus for {target-skill}:**
- (specific instructions for the next skill)
```

## Handoff Chains

### authoring → testing

Source: `cairo-contract-authoring` Turn 4.
Target: `cairo-testing` Turn 1.

The handoff includes:
- **Files touched** — which `.cairo` files were created or modified.
- **Security posture table** — every external function with its access posture, so testing knows what auth paths to cover.
- **Suggested focus** — "Write negative tests for each guarded function. Add fuzz tests for functions with numeric inputs. Verify events with spy_events."

### testing → optimization

Source: `cairo-testing` Turn 4.
Target: `cairo-optimization` Turn 1.

The handoff includes:
- **Files touched** — contract files and test files.
- **Test count** — how many tests pass, confirming the baseline is locked.
- **Gas baseline** — if `snforge test --detailed-resources` was run, include per-test gas numbers.
- **Suggested focus** — "Profile the hot paths identified during testing. Tests are passing — safe to optimize."

### testing → auditor

Source: `cairo-testing` Turn 4.
Target: `cairo-auditor` Turn 1.

The handoff includes:
- **Files touched** — all in-scope `.cairo` files.
- **Security posture table** — from authoring, passed through testing.
- **Test coverage summary** — which functions have positive/negative/fuzz tests.
- **Suggested focus** — "Focus on functions that lack negative tests. Check upgrade paths and timelock logic."

### optimization → auditor

Source: `cairo-optimization` Turn 4.
Target: `cairo-auditor` Turn 1.

The handoff includes:
- **Files touched** — only the files modified during optimization.
- **Before/after metrics** — step counts per optimized function.
- **Suggested focus** — "Verify optimizations did not introduce security regressions. Focus on changed arithmetic and storage packing."

### optimization → testing

Source: `cairo-optimization` Turn 4.
Target: `cairo-testing` Turn 1.

The handoff includes:
- **Files touched** — optimized contract files.
- **Behavior-sensitive rewrites** — arithmetic/loop/storage changes that need regression assertions.
- **Before/after metrics** — step deltas to prioritize perf-regression tests.
- **Suggested focus** — "Add regression tests around optimized paths and assert outputs/invariants stayed identical."

## How to Use

The handoff block is output by the source skill at the end of its Turn 4. The user can:

1. **Copy-paste it** as input when invoking the next skill: `/cairo-testing "Here's the handoff from authoring: ..."`.
2. **Skip it** if they want to start the next skill fresh — the handoff is optional context, not required.
3. **Edit it** to add or remove focus areas before passing it along.
