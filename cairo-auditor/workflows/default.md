# Default Workflow

1. Discover in-scope `.cairo` files under source directories.
2. Exclude tests, mocks, generated output, and vendored dependencies.
3. Run vector scans against vulnerability-db patterns.
4. Deduplicate by root cause.
5. Emit prioritized report with required regression tests.
