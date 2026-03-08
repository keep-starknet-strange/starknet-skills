#!/usr/bin/env python3
"""Build the Starkskills static site from repository data."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_GITHUB = "https://github.com/keep-starknet-strange/starknet-skills"
REPO_RAW = "https://raw.githubusercontent.com/keep-starknet-strange/starknet-skills/main"

MODULES: list[tuple[str, str]] = [
    ("cairo-auditor", "Deterministic + workflow-guided security review"),
    ("cairo-contract-authoring", "Safe implementation patterns"),
    ("cairo-testing", "Unit/integration/invariant strategy"),
    ("cairo-optimization", "Performance/resource hardening"),
    ("cairo-toolchain", "Build/declare/deploy/verify ops"),
    ("account-abstraction", "Account/session-key threat patterns"),
    ("starknet-network-facts", "Chain semantics and constraints"),
    ("openzeppelin-cairo", "OZ Cairo composition footguns"),
]


@dataclass
class ScorecardMetrics:
    path: Path
    cases: int | None
    precision: float | None
    recall: float | None


@dataclass
class VulnCard:
    name: str
    path: Path
    trigger: str
    detection_rule: str
    source_findings: list[str]
    severity_distribution: dict[str, int]


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def count_md_files(directory: Path) -> int:
    return sum(1 for p in directory.glob("*.md") if p.name != "README.md")


def parse_version(path: Path) -> tuple[int, int, int]:
    match = re.match(r"^v(\d+)\.(\d+)\.(\d+)", path.name)
    if not match:
        return (0, 0, 0)
    return tuple(int(match.group(i)) for i in (1, 2, 3))


def parse_scorecard(path: Path) -> ScorecardMetrics:
    text = path.read_text(encoding="utf-8")
    cases = _find_int(r"- Cases:\s+(\d+)", text)
    precision = _find_float(r"- Precision:\s+([0-9.]+)", text)
    recall = _find_float(r"- Recall:\s+([0-9.]+)", text)
    return ScorecardMetrics(path=path, cases=cases, precision=precision, recall=recall)


def _find_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _find_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def pick_latest_scorecards(scorecard_dir: Path) -> tuple[ScorecardMetrics | None, ScorecardMetrics | None]:
    files = [p for p in scorecard_dir.glob("v*.md") if p.is_file()]
    if not files:
        return None, None

    real_world = [p for p in files if "realworld" in p.name]
    deterministic = [p for p in files if "benchmark" in p.name and "realworld" not in p.name]

    def _pick(candidates: list[Path]) -> ScorecardMetrics | None:
        if not candidates:
            return None
        chosen = max(candidates, key=lambda item: (parse_version(item), item.name))
        return parse_scorecard(chosen)

    return _pick(deterministic), _pick(real_world)


def parse_card_sections(markdown_text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    for line in markdown_text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
            continue
        if current is not None:
            buf.append(line)

    if current is not None:
        sections[current] = "\n".join(buf).strip()

    return sections


def compact_markdown_text(value: str, limit: int = 220) -> str:
    if not value:
        return ""
    text = value
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def parse_source_findings(section: str) -> list[str]:
    ids: list[str] = []
    for line in section.splitlines():
        match = re.search(r"`([^`]+)`", line)
        if match:
            ids.append(match.group(1).strip())
    return ids


def github_blob(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return f"{REPO_GITHUB}/blob/main/{rel}"


def raw_skill_url(skill_name: str) -> str:
    return f"{REPO_RAW}/{skill_name}/SKILL.md"


def require_file(path: Path) -> Path:
    if not path.is_file():
        raise SystemExit(f"[build_site] Required file not found: {path}")
    return path


def require_directory(path: Path) -> Path:
    if not path.is_dir():
        raise SystemExit(f"[build_site] Required directory not found: {path}")
    return path


def fingerprint_files(root: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def build_dataset(root: Path) -> dict:
    manifest_path = require_file(root / "datasets/manifests/audits.jsonl")
    manifests = read_jsonl(manifest_path)

    normalized_findings_dir = require_directory(root / "datasets/normalized/findings")
    normalized_findings_files = sorted(normalized_findings_dir.glob("*.jsonl"))
    if not normalized_findings_files:
        raise SystemExit(f"[build_site] No normalized finding files found in: {normalized_findings_dir}")
    normalized_findings = [
        finding
        for jsonl_path in normalized_findings_files
        for finding in read_jsonl(jsonl_path)
    ]
    finding_by_id = {
        item["finding_id"]: item
        for item in normalized_findings
        if item.get("finding_id")
    }

    normalized_audits_dir = require_directory(root / "datasets/normalized/audits")
    normalized_audits_files = sorted(normalized_audits_dir.glob("*.json"))
    normalized_audits_count = len(normalized_audits_files)

    segments_dir = require_directory(root / "datasets/segments")
    segment_files = sorted(segments_dir.glob("*.jsonl"))
    segments_count = len(segment_files)

    vuln_cards_dir = require_directory(root / "datasets/distilled/vuln-cards")
    vuln_card_paths = sorted(p for p in vuln_cards_dir.glob("*.md") if p.name != "README.md")
    fix_patterns_dir = require_directory(root / "datasets/distilled/fix-patterns")
    test_recipes_dir = require_directory(root / "datasets/distilled/test-recipes")
    fix_pattern_files = sorted(fix_patterns_dir.glob("*.md"))
    test_recipe_files = sorted(test_recipes_dir.glob("*.md"))
    scorecards_dir = require_directory(root / "evals/scorecards")
    scorecard_files = sorted(scorecards_dir.glob("v*.md"))

    vuln_cards: list[VulnCard] = []
    for card_path in vuln_card_paths:
        text = card_path.read_text(encoding="utf-8")
        sections = parse_card_sections(text)
        source_ids = parse_source_findings(sections.get("Source Findings", ""))
        sev_counter = Counter(
            finding_by_id[item_id].get("severity_normalized", "unknown")
            for item_id in source_ids
            if item_id in finding_by_id
        )
        vuln_cards.append(
            VulnCard(
                name=card_path.stem,
                path=card_path,
                trigger=compact_markdown_text(sections.get("Trigger", "")),
                detection_rule=compact_markdown_text(sections.get("Detection Rule", "")),
                source_findings=source_ids,
                severity_distribution=dict(sev_counter),
            )
        )

    deterministic_scorecard, realworld_scorecard = pick_latest_scorecards(scorecards_dir)
    source_fingerprint = fingerprint_files(
        root,
        [
            manifest_path,
            *normalized_findings_files,
            *normalized_audits_files,
            *segment_files,
            *vuln_card_paths,
            *fix_pattern_files,
            *test_recipe_files,
            *scorecard_files,
        ],
    )

    return {
        "source_fingerprint": source_fingerprint,
        "counts": {
            "cataloged_audits": len(manifests),
            "segmented_audits": segments_count,
            "normalized_audits": normalized_audits_count,
            "normalized_findings": len(normalized_findings),
            "distilled_vuln_cards": len(vuln_cards),
            "distilled_fix_patterns": count_md_files(fix_patterns_dir),
            "distilled_test_recipes": count_md_files(test_recipes_dir),
            "skill_modules": len(MODULES),
            "skills_total_with_router": len(MODULES) + 1,
        },
        "latest_scorecards": {
            "deterministic": scorecard_to_dict(deterministic_scorecard, root),
            "realworld": scorecard_to_dict(realworld_scorecard, root),
        },
        "modules": [
            {
                "name": name,
                "description": description,
                "skill_path": f"{name}/SKILL.md",
                "raw_skill_url": raw_skill_url(name),
                "github_url": f"{REPO_GITHUB}/blob/main/{name}/SKILL.md",
            }
            for name, description in MODULES
        ],
        "vuln_cards": [
            {
                "name": card.name,
                "trigger": card.trigger,
                "detection_rule": card.detection_rule,
                "source_findings": card.source_findings,
                "severity_distribution": card.severity_distribution,
                "github_url": github_blob(card.path, root),
            }
            for card in vuln_cards
        ],
        "links": {
            "repo": REPO_GITHUB,
            "router_skill_raw": f"{REPO_RAW}/SKILL.md",
            "router_skill_github": f"{REPO_GITHUB}/blob/main/SKILL.md",
            "quality_workflow": f"{REPO_GITHUB}/actions/workflows/quality.yml",
            "full_evals_workflow": f"{REPO_GITHUB}/actions/workflows/full-evals.yml",
            "heldout_policy": f"{REPO_GITHUB}/blob/main/evals/heldout/README.md",
            "contributing": f"{REPO_GITHUB}/blob/main/CONTRIBUTING.md",
            "cairo_auditor": f"{REPO_GITHUB}/blob/main/cairo-auditor/SKILL.md",
            "cairo_auditor_readme": f"{REPO_GITHUB}/blob/main/cairo-auditor/README.md",
            "pipeline_readme": f"{REPO_GITHUB}/blob/main/datasets/README.md",
            "vuln_cards_dir": f"{REPO_GITHUB}/tree/main/datasets/distilled/vuln-cards",
        },
    }


def scorecard_to_dict(scorecard: ScorecardMetrics | None, root: Path) -> dict | None:
    if scorecard is None:
        return None
    return {
        "path": scorecard.path.relative_to(root).as_posix(),
        "github_url": github_blob(scorecard.path, root),
        "cases": scorecard.cases,
        "precision": scorecard.precision,
        "recall": scorecard.recall,
    }


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def fmt_int(value: int) -> str:
    return f"{value:,}"


def severity_badges(counter: dict[str, int]) -> str:
    if not counter:
        return '<span class="pill pill-muted">none</span>'
    order = ["critical", "high", "medium", "low", "best_practice", "info", "unknown"]
    parts = []
    for key in order:
        if key not in counter:
            continue
        parts.append(f'<span class="pill">{e(key)}: {counter[key]}</span>')
    for key, value in sorted(counter.items()):
        if key in order:
            continue
        parts.append(f'<span class="pill">{e(key)}: {value}</span>')
    return "".join(parts)


def source_finding_links(ids: Iterable[str]) -> str:
    output: list[str] = []
    for item_id in ids:
        output.append(
            (
                '<a class="finding-link" '
                f'href="{e(REPO_GITHUB)}/search?q={e(item_id)}" '
                f'target="_blank" rel="noreferrer">{e(item_id)}</a>'
            )
        )
    return "".join(output) if output else '<span class="muted">none</span>'


def build_index_html(data: dict, domain: str | None) -> str:
    counts = data["counts"]
    links = data["links"]
    scorecard = data["latest_scorecards"].get("realworld") or data["latest_scorecards"].get("deterministic")

    modules_html = "\n".join(
        (
            '<article class="module-card">'
            f'<h3>{e(item["name"])}<span class="status">stable</span></h3>'
            f'<p>{e(item["description"])}</p>'
            '<div class="card-links">'
            f'<a href="{e(item["raw_skill_url"])}" target="_blank" rel="noreferrer">Raw SKILL.md</a>'
            f'<a href="{e(item["github_url"])}" target="_blank" rel="noreferrer">Repo</a>'
            "</div>"
            "</article>"
        )
        for item in data["modules"]
    )

    scorecard_block = ""
    if scorecard:
        scorecard_block = (
            '<div class="scorecard">'
            '<h3>Latest Benchmark Snapshot</h3>'
            '<div class="scorecard-grid">'
            f'<div><span>Cases</span><strong>{e(scorecard.get("cases", "n/a"))}</strong></div>'
            f'<div><span>Precision</span><strong>{e(scorecard.get("precision", "n/a"))}</strong></div>'
            f'<div><span>Recall</span><strong>{e(scorecard.get("recall", "n/a"))}</strong></div>'
            "</div>"
            f'<a href="{e(scorecard["github_url"])}" target="_blank" rel="noreferrer">Open scorecard</a>'
            "</div>"
        )

    domain_note = (
        f'<div class="domain-note">Prepared for <strong>{e(domain)}</strong>.</div>'
        if domain
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Starkskills | Cairo Security Skills for AI Agents</title>
  <meta name="description" content="Production-grade Cairo security knowledge for AI agents, backed by manifest-tracked Starknet audit data." />
  <link rel="stylesheet" href="assets/site.css" />
</head>
<body>
  <header class="hero">
    <div class="badge-row">
      <span class="badge">Starknet Skills</span>
      <span class="badge badge-soft">Flagship: cairo-auditor</span>
    </div>
    <h1>Production-grade Cairo security knowledge for AI agents.</h1>
    <p class="hero-subtitle">Backed by <strong>{fmt_int(counts['cataloged_audits'])}</strong> manifest-cataloged audits, <strong>{fmt_int(counts['normalized_findings'])}</strong> normalized findings, and deterministic benchmark gates.</p>
    {domain_note}
    <div class="install-grid">
      <article>
        <h2>Claude marketplace</h2>
        <pre><code>/plugin marketplace add keep-starknet-strange/starknet-skills
/plugin menu</code></pre>
      </article>
      <article>
        <h2>Raw router URL</h2>
        <pre><code>{e(links['router_skill_raw'])}</code></pre>
      </article>
      <article>
        <h2>Git clone</h2>
        <pre><code>git clone {e(links['repo'])}.git</code></pre>
      </article>
    </div>
  </header>

  <main>
    <section class="section">
      <div class="section-head">
        <h2>Flagship: cairo-auditor</h2>
        <a href="{e(links['cairo_auditor'])}" target="_blank" rel="noreferrer">Open SKILL.md</a>
      </div>
      <p>Systematic review workflow for Cairo contracts: discover in-scope files, run vectorized scans, verify findings through a false-positive gate, and report prioritized fixes with required regression tests.</p>
      <div class="workflow">
        <span>discover</span>
        <span>scan</span>
        <span>verify</span>
        <span>report</span>
      </div>
      {scorecard_block}
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Skill Modules</h2>
        <a href="{e(links['router_skill_github'])}" target="_blank" rel="noreferrer">Router</a>
      </div>
      <div class="module-grid">
        {modules_html}
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Audit Data Pipeline</h2>
        <a href="{e(links['pipeline_readme'])}" target="_blank" rel="noreferrer">Pipeline docs</a>
      </div>
      <div class="pipeline-grid">
        <article><h3>ingest</h3><p>{fmt_int(counts['cataloged_audits'])} audits cataloged in manifest</p></article>
        <article><h3>segment</h3><p>{fmt_int(counts['segmented_audits'])} segmented audit text sets</p></article>
        <article><h3>normalize</h3><p>{fmt_int(counts['normalized_audits'])} normalized audits / {fmt_int(counts['normalized_findings'])} findings</p></article>
        <article><h3>distill</h3><p>{fmt_int(counts['distilled_vuln_cards'])} vuln cards, {fmt_int(counts['distilled_fix_patterns'])} fix patterns, {fmt_int(counts['distilled_test_recipes'])} test recipes</p></article>
        <article><h3>skillize</h3><p>{fmt_int(counts['skills_total_with_router'])} skills including router</p></article>
      </div>
      <p class="pipeline-footnote">Counts are generated from repository data at build time.</p>
    </section>

    <section class="section trust">
      <div class="section-head">
        <h2>Trust & Verification</h2>
        <a href="vuln-cards/">Browse vuln cards</a>
      </div>
      <ul>
        <li><a href="{e(links['quality_workflow'])}" target="_blank" rel="noreferrer">Quality gate CI</a></li>
        <li><a href="{e(links['full_evals_workflow'])}" target="_blank" rel="noreferrer">Full evals workflow</a></li>
        <li><a href="{e(links['heldout_policy'])}" target="_blank" rel="noreferrer">Held-out evaluation policy</a></li>
        <li><a href="{e(links['contributing'])}" target="_blank" rel="noreferrer">Contributing guide</a></li>
      </ul>
    </section>
  </main>

  <footer>
    <span>Source fingerprint: {e(data['source_fingerprint'])}</span>
    <a href="data/site-data.json">site-data.json</a>
  </footer>
</body>
</html>
"""


def build_vuln_cards_html(data: dict) -> str:
    rows = []
    for card in data["vuln_cards"]:
        rows.append(
            "<tr>"
            f"<td><a href=\"{e(card['github_url'])}\" target=\"_blank\" rel=\"noreferrer\">{e(card['name'])}</a></td>"
            f"<td>{severity_badges(card['severity_distribution'])}</td>"
            f"<td>{e(card['trigger'])}</td>"
            f"<td>{e(card['detection_rule'])}</td>"
            f"<td>{source_finding_links(card['source_findings'])}</td>"
            "</tr>"
        )

    row_markup = "\n".join(rows) if rows else "<tr><td colspan=\"5\">No vuln cards published yet.</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Starkskills | Vulnerability Cards</title>
  <meta name="description" content="Browsable vulnerability cards distilled from Starknet audit findings." />
  <link rel="stylesheet" href="../assets/site.css" />
</head>
<body>
  <header class="subpage-hero">
    <a class="back-link" href="../">← Back to landing page</a>
    <h1>Vulnerability Card Browser</h1>
    <p>Distilled classes from <strong>{fmt_int(data['counts']['normalized_findings'])}</strong> normalized findings.</p>
  </header>

  <main>
    <section class="section">
      <div class="section-head">
        <h2>Card Index</h2>
        <a href="{e(data['links']['vuln_cards_dir'])}" target="_blank" rel="noreferrer">Open repo directory</a>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Class</th>
              <th>Severity Distribution</th>
              <th>Trigger Condition</th>
              <th>Detection Rule</th>
              <th>Source Findings</th>
            </tr>
          </thead>
          <tbody>
            {row_markup}
          </tbody>
        </table>
      </div>
    </section>
  </main>

  <footer>
    <span>Source fingerprint: {e(data['source_fingerprint'])}</span>
    <a href="../data/site-data.json">site-data.json</a>
  </footer>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Optional production domain to write into website/CNAME",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    website = root / "website"

    data = build_dataset(root)

    (website / "data").mkdir(parents=True, exist_ok=True)
    (website / "vuln-cards").mkdir(parents=True, exist_ok=True)

    (website / "data/site-data.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (website / "index.html").write_text(build_index_html(data, args.domain), encoding="utf-8")
    (website / "vuln-cards/index.html").write_text(build_vuln_cards_html(data), encoding="utf-8")

    # Ensure GitHub Pages serves paths literally and applies custom domain when configured.
    (website / ".nojekyll").write_text("\n", encoding="utf-8")
    if args.domain:
        (website / "CNAME").write_text(args.domain.strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
