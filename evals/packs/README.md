# External Benchmark Packs

Curated repo lists for `scripts/quality/audit_external_pack.py` and `scripts/quality/scan_external_repos.py`.

Format:

- one repo per line: `owner/repo` or `owner/repo@ref`
- blank lines and `# comments` are ignored

Built-in pack names:

- `less-known` -> `evals/packs/less-known.txt`
- `low-profile` -> `evals/reports/data/external-repo-scan-low-profile-repos.txt`
- `wave2` -> `evals/reports/data/external-repo-scan-wave2-repos.txt`

Quick run:

```bash
./starkskills audit external --pack less-known --scan-id community-less-known
```
