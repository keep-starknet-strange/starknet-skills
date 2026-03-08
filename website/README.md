# starkskills.org static site

This directory is the deploy artifact for the public site.

## Local regenerate

```bash
python3 scripts/site/build_site.py --domain starkskills.org
```

## What is generated

- `index.html`: landing page with install methods, auditor spotlight, module grid, pipeline counters, and trust links.
- `vuln-cards/index.html`: browsable vulnerability card table.
- `data/site-data.json`: raw generated metrics and links.

These files are intentionally committed so reviewers can inspect snapshots in PRs.
Freshness is enforced in CI by regenerating and diff-checking these artifacts in `.github/workflows/quality.yml`.

## Deployment

GitHub Pages workflow: `.github/workflows/site.yml`.

Expected Pages source: GitHub Actions.

Custom domain settings:

- GitHub repo Pages `Custom domain`: `starkskills.org`
- DNS at Namecheap:
  - `A @ 185.199.108.153`
  - `A @ 185.199.109.153`
  - `A @ 185.199.110.153`
  - `A @ 185.199.111.153`
  - `CNAME www starkskills.org`

The build script writes `website/CNAME` automatically when `--domain` is provided.
