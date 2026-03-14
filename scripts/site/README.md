# Site Build Script

Static site generator for the `website/` landing page and vulnerability browser.

> [!WARNING]
> This site pipeline is legacy because `starknet-skills` is deprecated. Canonical skills live in `keep-starknet-strange/starknet-agentic`.

## Usage

From repo root:

```bash
python3 scripts/site/build_site.py --domain starkskills.org
```

Optional link-target overrides:

```bash
python3 scripts/site/build_site.py \
  --domain starkskills.org \
  --repo-slug keep-starknet-strange/starknet-agentic \
  --repo-ref main
```

Output files:

- `website/index.html`
- `website/vuln-cards/index.html`
- `website/data/site-data.json`
- `website/CNAME` (when `--domain` is supplied)

The generator reads repository source-of-truth data from `datasets/` and `evals/` so pipeline counters stay synchronized with the corpus.

The generator fails fast with explicit errors when required dataset paths are missing.
Output is deterministic (based on source-file fingerprint), which allows CI to assert snapshots are up to date.
