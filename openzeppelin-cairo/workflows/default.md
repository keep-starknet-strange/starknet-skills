# Default Workflow

1. Component map
- List all OZ components and embedded implementations in scope.
- Identify all externally reachable selectors introduced by embedding.

2. Privilege review
- Verify owner/role checks on every privileged selector.
- Verify initializer and upgrade selectors cannot be called by unauthorized callers.

3. Storage safety
- Confirm substorage layout and versioning remain compatible.
- Add regression tests for upgrade and role-transition invariants.
