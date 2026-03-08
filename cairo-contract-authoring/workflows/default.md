# Default Workflow

1. Scope
- Define contract responsibilities and explicit non-goals.
- Freeze external interface signatures before deep implementation.

2. State model
- Encode invariants in storage layout and typed wrappers.
- Separate privileged and unprivileged mutation paths.

3. Surface hardening
- Minimize public selectors.
- Add strict argument validation and auth checks.

4. Test-first tightening
- Add unit tests for nominal/failure paths.
- Add property/fuzz tests for invariant-sensitive logic.

5. Security review
- Run `cairo-auditor` in default mode.
- Patch findings and add regression tests.
