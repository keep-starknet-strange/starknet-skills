# Default Workflow

1. Environment lock
- Confirm pinned Scarb/foundry versions.
- Validate account config and RPC target.

1. Audit gate
- Manual pre-deploy gate (not auto-enforced by `quality.yml`).
- Run `python scripts/quality/audit_local_repo.py --repo-root /path/to/repo --scan-id release-gate --fail-on-findings`.
- If findings exist, fix and add regression tests before deployment.

1. Artifact build
- Build once from a clean tree.
- Record artifact hashes for release evidence.

1. Declare and deploy
- Declare class hash first.
- Deploy with explicit constructor calldata checks.

1. Verify and record
- Confirm class hash/address mapping.
- Publish command transcript + hashes in release notes.
