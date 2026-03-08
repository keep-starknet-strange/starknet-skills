# Default Workflow

1. Environment lock
- Confirm pinned Scarb/foundry versions.
- Validate account config and RPC target.

2. Artifact build
- Build once from a clean tree.
- Record artifact hashes for release evidence.

3. Declare and deploy
- Declare class hash first.
- Deploy with explicit constructor calldata checks.

4. Verify and record
- Confirm class hash/address mapping.
- Publish command transcript + hashes in release notes.
