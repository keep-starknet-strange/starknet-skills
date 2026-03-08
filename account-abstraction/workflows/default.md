# Default Workflow

1. Surface map
- Enumerate all entrypoints across validate/execute paths.
- Separate owner-only, session-key, and public paths.

2. Validation guarantees
- Ensure `__validate__` is bounded and deterministic.
- Reject expensive or stateful behavior that can degrade sequencer performance.

3. Policy enforcement
- Verify selector deny/allow semantics for session keys.
- Verify token, allowance, and spending-window constraints.

4. Replay resistance
- Check nonce monotonicity and domain-separated signature hashing.
- Add regression tests for previously fixed replay vectors.
