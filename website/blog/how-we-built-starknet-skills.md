---
name: how-we-built-starknet-skills
description: Technical deep dive on the Starknet Skills architecture, data pipeline, and benchmark methodology.
---

# How We Built Starknet Skills: Teaching AI Agents to Actually Audit Cairo

*March 2026*

Ask an LLM to audit a Cairo contract and you'll get a confident-sounding list of generic warnings. "Consider reentrancy." "Add access control." "Watch for overflow." None of it is wrong, exactly. And almost none of it is useful.

The problem isn't that LLMs can't reason about code. It's that they don't know *what matters* in Cairo and Starknet. They apply Solidity mental models to a fundamentally different architecture — felt-based arithmetic, the component system, `replace_class_syscall` upgrades, account abstraction validation flows, Sierra IR compilation. Without domain-specific knowledge, agents hallucinate security patterns that don't exist and miss vulnerability classes that do.

We built [starknet-skills](https://github.com/keep-starknet-strange/starknet-skills) to fix this. It's an open-source knowledge layer — plain markdown files that any AI coding agent can read — built from 24 real security audits, 217 normalized findings, and 13 canonical vulnerability classes. The flagship module, `cairo-auditor`, turns a general-purpose LLM into a structured security reviewer that runs 120 attack vectors across four parallel specialists (30 vectors per partition) with false-positive gating, confidence scoring, and optional Sierra IR confirmation.

This post explains how it works, why we made the design choices we did, and how you can use it today.

## The Data Foundation: 24 Audits -> 217 Findings -> 13 Classes

Every skill starts with real data. We ingested 24 public security audit reports from 10 firms — Nethermind, Cairo Security Clan, CODESPECT, Blaize, Zellic, zkSecurity, and others — covering DeFi protocols (Vesu, Nostra, StarkDeFi, Kapan Finance), infrastructure (Piltover, Hyperlane, L3 Bridge), and applications (Cartridge, LayerAkira).

```text
ingest → segment → normalize → distill → skillize
  24        26         217          9          7
audits   corpora    findings     assets     skills
```

Each audit PDF was extracted, segmented into traceable chunks with page bounds for lineage, then normalized into a structured finding format:

```json
{
  "finding_id": "ERIM-NOSTRA-L02",
  "severity_normalized": "low",
  "root_cause": "Fee parameter forwarded without upper bound",
  "exploit_path": "Admin can set arbitrarily high fee...",
  "vulnerable_snippet": "fn set_fee(ref self, fee: u256) { ... }",
  "fixed_snippet": "assert!(fee <= MAX_FEE, 'fee_too_high');",
  "tags": ["fee-config", "input-validation"],
  "confidence": "high"
}
```

The 217 normalized findings break down by severity: 17 critical, 26 high, 30 medium, 60 low, 47 informational, and 37 best-practice. From these, we distilled 13 canonical vulnerability classes currently implemented in the vuln-db — each with a vulnerable pattern, secure pattern, detection heuristics, false-positive caveats, and minimum required tests.

These aren't theoretical categories. Every pattern traces back to at least one real audit finding from a real protocol. When the auditor skill tells an agent to check for `IMMEDIATE-UPGRADE-WITHOUT-TIMELOCK`, it's because actual Cairo contracts shipped with exactly that bug.

## The Auditor Architecture: 4 Turns, 120 Vectors, 4 Parallel Specialists

The `cairo-auditor` skill is a prescriptive orchestrator. It doesn't just give the agent context — it tells it exactly what tool calls to make, which files to load, and in what order. The orchestration runs in four turns:

### Turn 1: Discover

The agent identifies the audit mode (`default`, `deep`, or `targeted`), discovers in-scope `.cairo` files (excluding tests, mocks, vendor, and generated code), and runs a deterministic preflight to identify likely vulnerability classes:

```bash
python scripts/quality/audit_local_repo.py \
  --repo-root /path/to/repo \
  --scan-id local-audit
```

The preflight uses 13 regex-based detectors — fast pattern matching on source code to flag which vulnerability classes are likely present. This isn't the final analysis; it's a signal for what the deep pass should focus on.

### Turn 2: Prepare

The agent loads specialist instructions and builds four bundles. Each bundle contains the full in-scope Cairo code plus one partition of the 120 attack vectors (30 per partition).

The vectors are split into four thematic groups:

| Partition | Focus | Example vectors |
|-----------|-------|-----------------|
| 1 | Access control + upgradeability | Ungated mutations, irrevocable admin, zero-hash upgrades |
| 2 | External calls + reentrancy + messaging | CEI violations, session self-call, L1/L2 replay gaps |
| 3 | Math + pricing + economic logic | Fee bounds, rounding bias, oracle trust, precision loss |
| 4 | Storage + components + trust chains | Map-zero defaults, stale storage, namespace overlap |

Each vector has a **D** (deterministic vulnerable pattern) and **FP** (false-positive caveats). For example:

> **V1 — Immediate upgrade without delay**
> D: `replace_class_syscall` reachable in the same transaction as scheduling, with no `get_block_timestamp` check enforcing a minimum delay.
> FP: Delay enforced by a separate timelock contract whose `execute` path is the only caller.

### Turn 3: Spawn Parallel Specialists

Four vector-scan specialists run in parallel — one per bundle. Each specialist follows a strict protocol:

**Triage pass**: For every vector, classify it as `Skip` (construct and concept absent), `Borderline` (construct absent but concept could appear via equivalent mechanism), or `Survive` (construct or exploit clearly present).

**Deep pass**: Only for `Survive` vectors. Trace the concrete caller → entrypoint → state change → impact path. Confirm attacker reachability. Confirm no existing guard blocks the exploit. Output in structured format:

```text
V15 | path: entry() -> helper() -> sink() | guard: none | verdict: CONFIRM [85]
```

**False-positive gate**: Every finding must pass three checks or it's dropped:

1. **Concrete attack path exists**: caller → reachable function → state transition → loss/impact.
2. **Reachability**: threat actor in scope can actually call the path under real access control.
3. **No existing guard**: no `assert`, reentrancy lock, OZ guard, or invariant check blocks it.

**Confidence scoring**: Starts at 100, with deductions:
- Privileged caller required → -25
- Partial path (can't prove full transition to impact) → -20
- Impact self-contained to attacker-only funds → -15
- Narrow environmental assumptions → -10

Findings below 75 confidence become low-confidence notes without fix blocks. This prevents the "wall of medium-severity noise" problem that makes generic LLM audits useless.

In `deep` mode, a fifth specialist — the adversarial agent — runs in parallel, specifically looking for cross-contract exploit paths and composability attacks that individual vector scans would miss.

### Turn 4: Report

The agent merges all specialist outputs, deduplicates by root cause (keeping the higher-confidence variant), runs a composability pass for interacting findings, and if Scarb/Sierra is available, runs IR confirmation. The final report is sorted by priority and includes concrete fix diffs and required regression tests for every finding.

## Sierra IR Confirmation

The source-level analysis catches patterns. Sierra confirmation validates them against the compiled intermediate representation.

When you pass `--sierra-confirm --allow-build`, the system builds the project with Scarb, collects `.sierra.json` and `.contract_class.json` artifacts, and extracts `libfunc` debug names. It then checks two things:

1. **Upgrade confirmation**: Does `replace_class_syscall` actually appear in the compiled IR? This catches false positives where the source code imports but never uses an upgrade path.

2. **CEI confirmation**: Does any function call an external contract (`call_contract_syscall`) before writing state (`storage_write_syscall`)? This confirms checks-effects-interactions violations at the IR level, where inlining and optimization may have changed the execution order from what the source suggests.


| Repo                          | Artifacts | ReplaceClass | CEI Oracle |
| ForgeYields/starknet_vault_kit| 32        | 21           | confirm    |
| medialane-io/medialane        | 6         | 1            | missing    |


Sierra confirmation is a secondary signal, not a verdict engine. The skill architecture treats it as evidence that strengthens or weakens source-level findings — not as standalone detection.

## Beyond Auditing: The Full Skill Pipeline

The auditor is the most complex skill, but it's part of a four-skill pipeline designed for the full contract lifecycle:

### 1. cairo-contract-authoring

Guides agents through writing correct, secure Cairo contracts with OpenZeppelin 3.0.0 components. Five mandatory security rules:

- Timelock checks must read from `get_block_timestamp()`, never from caller arguments
- Every storage-mutating external has explicit access posture (guarded or documented-public)
- Upgrade flows reject zero class hash
- Constructor validates non-zero critical addresses
- Anti-pattern/secure-pattern pairs are enforced, not suggested

### 2. cairo-testing

Structured testing strategy with `snforge` — unit, integration, fuzz, fork, and regression modes. Five mandatory coverage rules ensure agents don't stop at happy-path unit tests:

- Unit tests for all state-mutating selectors
- Negative tests for auth and input failures
- At least one fuzz/property test for core invariants
- Fixed findings become permanent regression tests
- Run the auditor and fix findings before merge

### 3. cairo-optimization

Profile-driven optimization with `snforge test --detailed-resources`. Agents must baseline before optimizing, apply one class at a time, re-test after each change, and re-profile to verify gains. Twelve optimization rules cover `DivRem`, `BoundedInt`, storage packing, loop hoisting, and arithmetic patterns.

### 4. Cross-Skill Handoffs

When a skill finishes, it outputs a structured **Handoff Block** — files touched, security posture table, verified checklist, and suggested focus for the next skill:

```markdown
## Handoff: cairo-contract-authoring → cairo-testing

**Security posture:**
| Function | Access | Notes |
|----------|--------|-------|
| `transfer` | guarded (owner) | — |
| `get_balance` | public (view) | read-only |

**Suggested focus for cairo-testing:**
- Write negative tests for each guarded function.
- Add fuzz tests for functions with numeric inputs.
```

This lets agents chain skills without losing context.

## Works Everywhere

The skills are plain markdown — they work with any tool that reads files. We've tested with Claude Code, Cursor, OpenAI Codex, GitHub Copilot, Gemini CLI, JetBrains Junie, VS Code, and 20+ other tools that support the [Agent Skills](https://agentskills.io) open standard.

Install in Claude Code:

```bash
/plugin marketplace add keep-starknet-strange/starknet-skills
/plugin install starknet-skills
```

Install anywhere else — paste the router URL:

```text
https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main/SKILL.md
```

Then try:

```text
Audit src/vault.cairo for security issues using cairo-auditor
```

The agent reads the skill, follows the 4-turn orchestration, spawns the parallel specialists, applies the FP gate, and produces a structured findings report with fix diffs and regression tests.

## Results

Deterministic benchmarks (smoke/regression gates, not final proof):

| Metric | Value |
|--------|-------|
| Benchmark cases | 42 |
| Precision | 1.000 |
| Recall | 1.000 |
| Vulnerability classes covered | 13 (detectors and vuln-db classes) |
| Attack vectors | 120 across 4 partitions (30 each) |
| Source audits | 24 from 10 firms |
| Normalized findings | 217 |

External triage on real protocol code: 0.81 precision, 1.00 recall on 32 labeled findings.

These numbers are informational. They tell us the skill is working directionally — not that it replaces a human auditor. The value proposition is different: skills make agents reliably better at catching the patterns they currently miss, with structured FP gating to prevent noise.

## What's Next

- **Tier-C skill expansion**: `cairo-toolchain`, `account-abstraction`, and `starknet-network-facts` are functional today and will keep getting deeper references, eval coverage, and stricter handoff contracts.
- **More vulnerability patterns**: The vuln-db grows with each new audit ingested. We're tracking emerging patterns in Starknet DeFi and cross-chain messaging.
- **Community contributions**: The repo is MIT-licensed. If you've found a Cairo vulnerability class that isn't covered, open a PR. Every new pattern makes every agent that uses the skill better.

---

**Links:**
- GitHub: [keep-starknet-strange/starknet-skills](https://github.com/keep-starknet-strange/starknet-skills)
- Website: [starkskills.org](https://starkskills.org)
- Agent Skills standard: [agentskills.io](https://agentskills.io)
