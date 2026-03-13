---
title: "How We Built cairo-auditor: Teaching AI Agents to Actually Audit Cairo"
date: 2026-03-13
authors: [omarespejel]
tags: [cairo, security, auditing, starknet]
description: "How cairo-auditor uses a 4-turn orchestration, parallel vector specialists, and a false-positive gate to turn a general LLM into a structured Cairo security reviewer."
---

# How We Built cairo-auditor: Teaching AI Agents to Actually Audit Cairo

*March 2026*

Ask an LLM to audit a Cairo contract and you'll get a confident-sounding list of generic warnings. "Consider reentrancy." "Add access control." "Watch for overflow." None of it is wrong, exactly. And almost none of it is useful.

The problem isn't that LLMs can't reason about code. It's that they don't know *what matters* in Cairo and Starknet. They apply Solidity mental models to a fundamentally different architecture — felt-based arithmetic instead of fixed-width integers, OpenZeppelin's component system instead of inheritance, `replace_class_syscall` upgrades instead of proxy patterns, account abstraction validation flows that have no EVM equivalent, and Sierra IR compilation that can reorder operations in ways the source doesn't show. Without domain-specific knowledge, agents hallucinate security patterns that don't exist and miss vulnerability classes that do.

We built [cairo-auditor](https://github.com/keep-starknet-strange/starknet-skills/tree/main/cairo-auditor) to fix this. It's an open-source skill — a plain markdown file that any AI coding agent can read — that turns a general-purpose LLM into a structured security reviewer. It runs 170 Cairo-specific attack vectors across four parallel specialists, gates every finding through a false-positive filter with confidence scoring, and optionally validates findings against compiled Sierra IR.

This post explains how it works, why we made the design choices we did, and how to use it today.

## Why a Skill, Not a Tool

Traditional static analysis tools (Slither, Mythril, Semgrep) parse code into an AST or CFG and run detectors against it. They're deterministic, fast, and narrow — they catch what they're programmed to catch and nothing else.

LLMs are the opposite. They can reason about intent, trace multi-step attack paths, and understand context. But without structured guidance, they produce vague findings, miss domain-specific patterns, and generate false positives that drown out real issues.

A skill bridges this gap. It gives the LLM the domain knowledge it's missing (what vulnerability classes actually exist in Cairo, what false-positive patterns look like, how to validate findings) while preserving what LLMs are good at (reasoning about novel code, tracing cross-function paths, explaining impact in context).

The skill is a markdown file. It works with Claude Code, Cursor, OpenAI Codex, GitHub Copilot, Gemini CLI, JetBrains Junie, and [30+ other tools](https://agentskills.io) that can read files. No binary, no API key, no integration work.

## The Data Foundation

Every vector in the skill traces back to a real vulnerability in a real Cairo protocol.

We ingested 26 public security audit reports from 10 firms — Nethermind, Cairo Security Clan, CODESPECT, Blaize, Zellic, zkSecurity, and others — covering DeFi protocols (Vesu, Nostra, StarkDeFi, Kapan Finance), infrastructure (Piltover, Hyperlane, L3 Bridge), and applications (Cartridge, LayerAkira).

```text
ingest → segment → normalize → distill → skillize
  26        26         217          9          7
audits   corpora    findings     assets     skills
```

Each audit report was extracted, segmented into traceable chunks with page bounds for lineage, and normalized into a structured format:

```json
{
  "finding_id": "ERIM-NOSTRA-L02",
  "severity_normalized": "low",
  "root_cause": "Fee parameter forwarded without upper bound",
  "exploit_path": "Admin can set arbitrarily high fee...",
  "vulnerable_snippet": "fn set_fee(ref self, fee: u256) { ... }",
  "fixed_snippet": "assert!(fee <= MAX_FEE, 'fee_too_high');",
  "tags": ["fee-config", "input-validation"]
}
```

The 217 normalized findings break down: 17 critical, 26 high, 30 medium, 60 low, 47 informational, 37 best-practice. From these we distilled 28 canonical vulnerability classes — each with a vulnerable pattern, secure pattern, detection heuristics, false-positive caveats, and minimum required tests.

When the auditor tells an agent to check for `IMMEDIATE-UPGRADE-WITHOUT-TIMELOCK`, it's because actual Cairo contracts shipped with that exact bug, caught by human auditors at real security firms, in real audit engagements.

## How the Auditor Works: 4 Turns

The skill is a prescriptive orchestrator. It doesn't just give the agent context — it tells it exactly what tool calls to make, which files to load, and in what order. The orchestration runs in four turns.

### Turn 1: Discover

The agent picks an audit mode:

- **default**: full in-scope scan with four parallel vector passes.
- **deep**: default + an adversarial exploit-path specialist.
- **targeted**: explicit file set, same validation gate, faster iteration.

It discovers in-scope `.cairo` files (excluding tests, mocks, examples, vendor, and generated paths), then runs a deterministic preflight:

```bash
python scripts/quality/audit_local_repo.py \
  --repo-root /path/to/repo --scan-id local-audit
```

The preflight uses 13 regex-based detectors — fast pattern matching that flags likely vulnerability classes in seconds. These detectors cover the most recurrent patterns across our 26-audit corpus: `IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK`, `NO_ACCESS_CONTROL_MUTATION`, `CEI_VIOLATION_ERC1155`, `UNPROTECTED_INITIALIZER`, and 9 others.

This isn't the final analysis. It's a triage signal — which classes are likely present, so the deep pass knows where to focus.

### Turn 2: Prepare

The agent loads three reference files and builds four specialist bundles.

**References loaded:**
- `agents/vector-scan.md` — the specialist's operating manual
- `references/judging.md` — the false-positive gate and confidence scoring rules
- `references/report-formatting.md` — the exact structure every finding must follow

**Four bundles built**, each containing the full in-scope Cairo code plus one of four attack-vector partitions:

| Partition | Focus | Vectors | Examples |
|-----------|-------|---------|----------|
| 1 | Access control + upgradeability | ~40 | Ungated mutations, irrevocable admin, zero-hash upgrades, upgrade initializer omission |
| 2 | External calls + reentrancy + messaging | ~40 | CEI violations, session self-call, L1/L2 replay, callback state confusion |
| 3 | Math + pricing + economic logic | ~40 | Fee bounds, rounding bias, oracle trust, precision loss, liquidation edge cases |
| 4 | Storage + components + trust chains | ~40 | Map-zero defaults, stale storage, namespace overlap, nonce monotonicity gaps |

Each vector has two parts. **D** is the deterministic vulnerable pattern — the concrete code shape. **FP** is the false-positive caveat — the guard or context that makes the pattern safe. For example:

> **V1 — Immediate upgrade without delay**
> D: privileged `upgrade` path calls `replace_class_syscall` or `upgradeable.upgrade` in one transaction with no schedule/execute split.
> FP: explicit timelock state with pending hash and `now >= scheduled + delay` check.
> **V21 — CEI violation on ERC1155 transfer path**
> D: `safe_transfer_from` calls external receiver callback before internal balance accounting completes.
> FP: reentrancy guard wraps the full transfer scope.

This D/FP pairing is critical. It's what prevents the "wall of noise" problem. The agent doesn't just scan for the pattern — it's told exactly when the pattern is a false alarm.

### Turn 3: Spawn Parallel Specialists

Four vector-scan specialists run simultaneously — one per bundle. Each follows a strict protocol defined in `agents/vector-scan.md`:

**Step 1 — Bundle reading**: Read the code in parallel 1000-line chunks. No unbounded reads.

**Step 2 — Triage**: Classify every vector into exactly one bucket:
- `Skip`: named construct and underlying exploit concept are absent.
- `Borderline`: named construct absent but exploit concept could appear via equivalent mechanism.
- `Survive`: construct or exploit concept is clearly present in code.

Output format:

```text
Skip: V3, V7, V11, V12, V14
Borderline: V8 (helper delegates to unguarded internal)
Survive: V1, V2, V5, V6, V9, V10, V13
Total: 14 classified
```

**Step 3 — Deep pass**: Only for `Survive` vectors. Each gets three required checks:

1. Trace concrete caller → entrypoint → state change → impact path.
2. Confirm attacker reachability under actual access control.
3. Confirm no existing guard blocks the exploit.

One-line verdict format before the full finding:

```text
V1 | path: upgrade() -> replace_class_syscall() | guard: none | verdict: CONFIRM [90]
V6 | path: set_config() -> storage_write() | guard: assert_only_owner | verdict: DROP (guarded)
```

**Step 4 — Composability check**: If 2+ findings survive, test whether they compound. Auth weakness + arbitrary external call = stronger combined impact than either alone. The compound note goes into the higher-confidence finding.

**Step 5 — Hard stop**: No rescanning dropped vectors. No scanning outside the assigned partition. Return formatted findings or `No findings.`

In `deep` mode, a fifth specialist — the adversarial agent — runs in parallel. It specifically hunts for multi-step exploit paths that cross function and contract boundaries:

- Multi-step call chains (parent → helper → external interaction → late state mutation)
- Trust-chain composition (owner → manager → allocator → adapter)
- Session/account validation-execute interplay
- Upgrade/admin takeover paths

Each adversarial candidate requires: attacker capability assumptions, exact reachable path, guard bypass analysis, concrete impact, and a confidence score. Candidates that can't produce a concrete path to impact are dropped.

### Turn 4: Report

The agent merges all specialist outputs and runs three passes:

**Deduplication**: When two findings share the same root cause, keep the higher-confidence one. Merge broader attack path details. One fix, one test block.

**Composability**: When findings interact, document the compound impact in the stronger finding.

**Sierra confirmation** (optional): If Scarb is available, validate upgrade and CEI findings against compiled IR (details below).

The final report is sorted by priority:
- `P0`: direct loss, permanent lock, or upgrade takeover.
- `P1`: high-impact auth/logic flaw with realistic exploit path.
- `P2`: medium-impact misconfiguration or constrained exploit.
- `P3`: low-impact hardening issue.

Every finding follows an exact template:

```text
[P1] **Immediate upgrade without timelock**

Location: src/upgrade.cairo:42

Class: IMMEDIATE_UPGRADE_WITHOUT_TIMELOCK | Confidence: [90] | Severity: high

Description:
The `upgrade` function calls `replace_class_syscall` directly without
a schedule/execute split or minimum delay check. Any address with the
admin role can replace the contract class in a single transaction.

Fix:
- self.upgradeable.upgrade(new_class_hash);
+ assert!(new_class_hash.is_non_zero(), 'zero_class_hash');
+ self.pending_upgrade.write(PendingUpgrade { hash: new_class_hash, executable_after: get_block_timestamp() + MIN_DELAY });

Required tests:
- Regression test: call upgrade() and verify class changes in one tx (should fail after fix).
- Guard test: schedule upgrade, attempt execute before delay expires, verify revert.
```

No vague recommendations. Concrete fix diff. Concrete test recipes.

## The False-Positive Gate

This is the single most important design decision in the skill.

Generic LLM audits produce dozens of findings. Most are noise — correct-sounding observations that either aren't exploitable or are already guarded. Developers triage the list, get frustrated, and ignore everything. The real bugs hide in the noise.

The cairo-auditor enforces a hard gate. Every finding must pass three checks **or it's dropped**:

1. **Concrete attack path exists**: caller → reachable function → state transition → loss/impact. Not "could potentially lead to..." — an actual traced path.

2. **Reachability**: the threat actor in scope can call the path under actual access control. If the function is `assert_only_owner`, the finding stays in scope but is framed as governance/admin risk with a confidence deduction.

3. **No existing guard**: no `assert`, non-reentrant lock, OZ component guard, or explicit invariant check already blocks the attack.

Then the confidence score:

| Condition | Deduction |
|-----------|-----------|
| Privileged caller required (owner/admin/governance) | -25 |
| Partial path (can't prove full transition to impact) | -20 |
| Impact self-contained to attacker-only funds | -15 |
| Requires narrow environmental assumptions (sequencer timing, unusual off-chain behavior) | -10 |
| Safety depends on indirect framework behavior that is present but not locally asserted | -10 |

Findings below 75 become low-confidence notes — reported but without fix blocks. This is how we separate "this is almost certainly a bug, here's the fix" from "this looks suspicious but we can't fully confirm the path."

The gate also has an explicit **Do Not Report** list:

- Style/naming/NatSpec-only findings
- Linter/compiler warnings already enforced by toolchain
- Generic centralization notes without concrete exploit path
- Gas-only micro-optimizations
- Missing events without security or accounting impact
- Theoretical attacks requiring compromised prover/sequencer
- Duplicate root causes already captured by a higher-confidence finding

This list comes directly from auditor fatigue patterns — the categories that real security teams consistently flag as wasted review time.

## Sierra IR Confirmation

Source-level analysis catches patterns. Sierra confirmation validates them against the compiled intermediate representation.

Cairo compiles to Sierra (Safe Intermediate Representation) before execution. Sierra is a linear sequence of typed statements with explicit branch targets and libfunc (library function) calls. The compiled output can differ from what the source suggests — inlining, dead-code elimination, and optimization passes may change execution order.

When you run with `--sierra-confirm --allow-build`, the system:

1. Builds the project with Scarb.
2. Collects `.sierra.json` and `.contract_class.json` artifacts.
3. Extracts `libfunc` debug names from `sierra_program_debug_info`.
4. Tracks syscall markers per function entry point:
   - `call_contract_syscall`, `library_call` → external call
   - `storage_write_syscall` → state mutation
   - `storage_read_syscall` → state access
   - `replace_class_syscall` → upgrade marker
   - `emit_event_syscall` → event emission

Two confirmation checks:

**Upgrade confirmation**: Does `replace_class_syscall` actually appear in the compiled IR? This catches false positives where source code imports `UpgradeableComponent` but never wires the upgrade function into an externally reachable selector.

**CEI confirmation**: Does any function call an external contract before writing state? For each function entry point, the system tracks the index of the first external call statement and the first state write statement. If external call comes first, it's a CEI violation signal.

Real results from our 7-repo evaluation:

```text
| Repo                            | Built | Artifacts | ReplaceClass | Ext→Write | Upgrade | CEI     |
| ForgeYields/starknet_vault_kit  | 3/3   | 32        | 21           | 0         | confirm | —       |
| kiroshi-market/kiroshi-protocol | 2/2   | 6         | 2            | 0         | confirm | —       |
| medialane-io/medialane          | 1/1   | 6         | 1            | 0         | confirm | missing |
| StarkVote/starkvote             | 4/4   | 7         | 0            | 0         | —       | —       |
```

`medialane-io/medialane` had CEI findings at the source level but no `external_call → state_write` ordering in the compiled Sierra — flagging a potential false positive that would have survived without IR confirmation.

Sierra confirmation is a secondary signal. It strengthens or weakens source-level findings. It doesn't replace the LLM analysis — it validates it against ground truth from the compiler.

## The Vulnerability Database

Behind the 170 attack vectors sits a structured database of 28 canonical vulnerability classes. Each class has its own reference file with a consistent format:

```markdown
# UNPROTECTED-INITIALIZER

## Description
Initializer function remains externally callable without caller
authorization, enabling front-run or hostile initialization.

## Vulnerable Pattern
- public `initialize` outside constructor-only path
- only guard is `is_zero()` one-time check
- initializer writes privileged contract addresses/roles

## Secure Pattern
- constructor-only initialization, or
- protected initializer restricted to deployer/factory/governance

## Detection Heuristics
- publicly reachable `initialize` with storage writes
- no access control assertions in initializer body

## False Positive Caveats
- initializer callable only in factory-controlled deployment
  transaction pattern with proven atomicity

## Minimum Tests
- unauthorized initializer call reverts
- repeated initialization reverts
```

The 28 classes cover the full taxonomy we've seen across 26 audits: access control failures, upgrade safety, arithmetic/precision, state management, external interactions, economic logic, storage layout, and specialized patterns.

Each class links back to the normalized findings that motivated it. The skill's evidence priority hierarchy makes this explicit:

1. `references/vulnerability-db/` — canonical patterns (highest weight)
2. `references/attack-vectors/` — the 170 concrete vectors
3. `datasets/normalized/findings/` — raw normalized audit data
4. `datasets/distilled/vuln-cards/` — distilled pattern cards
5. `evals/cases/` — benchmark test cases

## Evaluation

We measure the skill at three levels:

**Deterministic benchmark** (42 cases): 18 true positives, 24 true negatives, 0 false positives, 0 false negatives. Precision 1.000, recall 1.000 across all 13 detector classes. Test cases sourced from real protocol code (Argus, Kiroshi, Nostra, ForgeYields).

**External triage** (32 human-labeled findings on real repos): Precision 0.812, recall 1.000. The 6 false positives are tracked in [trend reports](https://github.com/keep-starknet-strange/starknet-skills/blob/main/evals/scorecards/cairo-auditor-external-trend.md) and drive vuln-db refinement.

**Manual gold recall** (19 reserved findings): ≥0.90 overall recall, ≥0.75 per-class recall.

These benchmarks are smoke/regression gates — they verify the skill isn't broken, not that it's perfect. Every PR that touches the skill or its references triggers a full eval run. Regressions block merge.

The honest framing: the skill makes agents reliably better at catching Cairo-specific patterns with structured FP gating to prevent noise. It doesn't replace a human security auditor. It's a force multiplier — the difference between an agent that says "consider reentrancy" and one that traces `V21 | path: safe_transfer_from() -> on_erc1155_received() -> _update_balance() | guard: none | verdict: CONFIRM [85]`.

## Try It

Paste this URL into any agent:

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/cairo-auditor/SKILL.md
```

Then:

```text
Audit src/vault.cairo for security issues using cairo-auditor
```

The agent reads the skill, follows the 4-turn orchestration, spawns parallel specialists, applies the FP gate, and produces structured findings with fix diffs and regression tests.

If you're using Claude Code plugin installs, use the latest commands from the [README Install & Use](https://github.com/keep-starknet-strange/starknet-skills#install--use) section.

The [full skill](https://github.com/keep-starknet-strange/starknet-skills/tree/main/cairo-auditor), [vulnerability database](https://github.com/keep-starknet-strange/starknet-skills/tree/main/cairo-auditor/references/vulnerability-db), and [26-audit dataset](https://github.com/keep-starknet-strange/starknet-skills/tree/main/datasets) are MIT-licensed. If you've found a Cairo vulnerability class that isn't covered, [open a PR](https://github.com/keep-starknet-strange/starknet-skills/blob/main/CONTRIBUTING.md). Every new pattern makes every agent that uses the skill better.

---

**Links:**
- GitHub: [keep-starknet-strange/starknet-skills](https://github.com/keep-starknet-strange/starknet-skills)
- Website: [starkskills.org](https://starkskills.org)
- Agent Skills standard: [agentskills.io](https://agentskills.io)
