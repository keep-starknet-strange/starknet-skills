# Site Build Script

Static site generator for the `website/` landing page and vulnerability browser.

## Usage

From repo root:

```bash
python3 scripts/site/build_site.py --domain starkskills.org
```

Output files:

- `website/index.html`
- `website/vuln-cards/index.html`
- `website/data/site-data.json`
- `website/CNAME` (when `--domain` is supplied)

The generator reads repository source-of-truth data from `datasets/` and `evals/` so pipeline counters stay synchronized with the corpus.
