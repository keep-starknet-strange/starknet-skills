---
name: cairo-auditor
description: Systematic Cairo/Starknet security audit workflow with deterministic preflight, parallel vector specialists, adversarial reasoning, and strict false-positive gating.
allowed-tools: [Bash, Read, Glob, Grep, Task]
---

# Cairo Auditor

## When to Use

- Security review for Cairo/Starknet contracts before merge.
- Release-gate audits for account/session/upgrade critical paths.
- Triage of suspicious findings from CI, reviewers, or external reports.

## When NOT to Use

- Feature implementation tasks.
- Deployment-only ops.
- SDK/tutorial requests.

## Rationalizations to Reject

- "Tests passed, so it is secure."
- "This is normal in EVM, so Cairo is the same."
- "It needs admin privileges, so it is not a vulnerability."
- "We can ignore replay or nonce edges for now."

## Modes

- `default`: full in-scope scan with four specialist vector passes.
- `deep`: default + adversarial exploit-path pass.
- `targeted`: explicit file set, same validation gate, faster iteration.

## Quick Start

1. Open [workflows/default.md](workflows/default.md) for standard audits, or [workflows/deep.md](workflows/deep.md) for adversarial mode.
2. Load [agents/vector-scan.md](agents/vector-scan.md), [references/judging.md](references/judging.md), and [references/README.md](references/README.md).
3. Select attack-vector partitions from `references/attack-vectors/attack-vectors-1.md` through `references/attack-vectors/attack-vectors-4.md`.
4. Run deterministic preflight on target repo:

   ```bash
   python scripts/quality/audit_local_repo.py \
     --repo-root /path/to/repo \
     --scan-id local-audit
   ```

5. Format output using [references/report-formatting.md](references/report-formatting.md), then validate against `references/vulnerability-db/README.md`.

## Orchestration (4 Turns)

### Turn 1: Discover

1. Determine mode (`default`, `deep`, `targeted`).
2. Discover in-scope `.cairo` files; exclude tests/mocks/examples/vendor/generated paths.
3. Run deterministic preflight checks to identify likely classes (upgrade/auth/session/external-call).

### Turn 2: Prepare

1. Load specialist instructions and references:
   - [agents/vector-scan.md](agents/vector-scan.md)
   - [references/judging.md](references/judging.md)
   - [references/report-formatting.md](references/report-formatting.md)
2. Build a deterministic bundle workspace and in-scope file list:

   ```bash
   export SCAN_ID="${SCAN_ID:-cairo-audit-$(date +%Y%m%d)}"
   export REPO_ROOT="/path/to/repo"
   export SKILLS_ROOT="${SKILLS_ROOT:-$(pwd)}"
   export BUNDLE_ROOT="/tmp/cairo-auditor/${SCAN_ID}"
   mkdir -p "$BUNDLE_ROOT"

   python - <<'PY'
from pathlib import Path
import sys

repo_root = Path(__import__("os").environ["REPO_ROOT"]).resolve()
skills_root = Path(__import__("os").environ["SKILLS_ROOT"]).resolve()
bundle_root = Path(__import__("os").environ["BUNDLE_ROOT"]).resolve()

sys.path.insert(0, str((skills_root / "scripts/quality").resolve()))
from scan_external_repos import iter_cairo_files, is_excluded

excluded = (
    "test", "tests", "mock", "mocks", "example", "examples",
    "preset", "presets", "fixture", "fixtures",
    "vendor", "vendors", "generated",
)

in_scope: list[str] = []
for file_path in iter_cairo_files(repo_root):
    rel = file_path.relative_to(repo_root)
    if is_excluded(rel, excluded):
        continue
    in_scope.append(rel.as_posix())

out_path = bundle_root / "in-scope-files.txt"
out_path.write_text("\n".join(in_scope) + ("\n" if in_scope else ""), encoding="utf-8")
print(f"in-scope files: {len(in_scope)}")
PY
   ```

3. Build one shared source bundle and four specialist bundles:

   ```bash
   python - <<'PY'
from pathlib import Path
import re
import os

repo_root = Path(os.environ["REPO_ROOT"]).resolve()
skills_root = Path(os.environ["SKILLS_ROOT"]).resolve()
bundle_root = Path(os.environ["BUNDLE_ROOT"]).resolve()
scope_file = bundle_root / "in-scope-files.txt"
source_bundle = bundle_root / "source-bundle.md"

def fence_for(text: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)

parts: list[str] = []
for rel in scope_file.read_text(encoding="utf-8").splitlines():
    if not rel:
        continue
    code_path = (repo_root / rel).resolve()
    try:
        code = code_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        code = code_path.read_text(encoding="utf-8", errors="ignore")
    fence = fence_for(code)
    parts.extend([f"### {rel}", f"{fence}cairo", code.rstrip(), fence, ""])

source_bundle.write_text("\n".join(parts) + ("\n" if parts else ""), encoding="utf-8")

for i in range(1, 5):
    refs = [
        "cairo-auditor/references/judging.md",
        "cairo-auditor/references/report-formatting.md",
        f"cairo-auditor/references/attack-vectors/attack-vectors-{i}.md",
    ]
    chunks = [(skills_root / ref).read_text(encoding="utf-8").rstrip() for ref in refs]
    chunks.append(source_bundle.read_text(encoding="utf-8").rstrip())
    out = bundle_root / f"audit-agent-{i}-bundle.md"
    out.write_text("\n\n".join(chunk for chunk in chunks if chunk) + "\n", encoding="utf-8")
PY
   ```

4. Record bundle size before spawn:

   ```bash
   wc -l "$BUNDLE_ROOT"/audit-agent-*-bundle.md
   ```

### Turn 3: Spawn

1. Spawn 4 parallel vector specialists (one per bundle) following `agents/vector-scan.md`, pinned to Sonnet (`model=sonnet`).
2. In `deep` mode, spawn [agents/adversarial.md](agents/adversarial.md) pinned to Opus (`model=opus`).
3. Keep the model split strict: specialists stay on Sonnet; adversarial stays on Opus. If Opus is unavailable, note the fallback explicitly in final output.
4. Each specialist must:
   - triage vectors (`Skip/Borderline/Survive`),
   - apply FP gate from [references/judging.md](references/judging.md),
   - output only findings formatted by [references/report-formatting.md](references/report-formatting.md).

### Turn 4: Report

1. Merge outputs.
2. Deduplicate by root cause (keep higher-confidence variant).
3. Run composability pass when multiple findings interact.
4. If Scarb/Sierra is available, run Sierra confirmation with class-to-signal mapping (first-wave: CEI and upgrade classes).
5. Use Sierra v3 per-finding evidence (`ir_confirmation`, `signal_quality`, `artifact_source`) and keep `unknown` for unmapped classes.
6. Sort findings by `actionable` first, then confidence descending.
7. Emit actionable findings + required regression tests.

## Reporting Contract

Each finding must include:

- `class_id`
- `category` (`security_bug` | `design_tradeoff` | `quality_smell`)
- `confidence`
- `needs_poc` (`true` | `false`)
- `actionability` (`actionable` | `low_confidence` | `suppressed`)
- `entry_point`
- `attack_path`
- `guard_analysis`
- `ir_confirmation` (`confirmed` | `missing` | `unknown`)
- `signal_quality` (`high` | `medium` | `low`)
- `artifact_source` (`sierra_json` | `contract_class` | `sierra_text` | `none`)
- `affected_files`
- `recommended_improvement`
- `required_tests`

Do not auto-assign `high/critical` severity in scanner output. Severity is manual signoff metadata only.

## Evidence Priority

1. `references/vulnerability-db/`
2. `references/attack-vectors/`
3. `../datasets/normalized/findings/`
4. `../datasets/distilled/vuln-cards/`
5. `../evals/cases/`

## Output Rule

- Report only findings that pass FP gate.
- Findings with confidence `<75` may be listed as low-confidence notes without a fix block.
