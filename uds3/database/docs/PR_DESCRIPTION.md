PR: Make database adapters import-safe and add lazy backend startup

Summary
-------
This PR hardens the database API layer and adapters so importing the package in
an environment without optional database drivers does not crash. It also refactors
`DatabaseManager` to defer backend connections to an explicit start phase.

Key changes
-----------
- Adapters: deferred heavy client initialization from __init__ to `connect()`.
  - Adapters now warn at import-time when optional libraries are missing.
  - connect() returns False on failure instead of raising at import-time.
- DatabaseManager:
  - Do not call `connect()` during __init__; instantiate adapters and store them in `_backends_to_start`.
  - New API: `start_all_backends(backend_names=None, timeout_per_backend=5)`.
  - Support `autostart` flag in manager constructor and factory helpers.
  - Consistent attribute naming `keyvalue_backend`.
- Tests: added unit tests verifying startup behavior and error propagation.
- CHANGELOG and PR description added.

Why
---
This change prevents import-time crashes in minimal environments (e.g. CI, docs,
lightweight tooling) and centralizes error handling for failed backend starts. It
also gives calling code explicit control over when to open connections.

Compatibility
-------------
- Backwards compatible for code that calls `connect()` explicitly on backends.
- If callers relied on immediate `connect()` side-effects during `DatabaseManager` init,
  they should either set `autostart=True` in their config or call `start_all_backends()`
  after creating the manager.

Testing
-------
- Unit tests included that run under standard Python `unittest`.
- Integration tests that require optional drivers are left out; CI should run
  those in environments where the drivers are available.

Follow-ups
----------
- Add CI job that runs the full adapter integration matrix (with/without optional drivers).
- Update docs in `docs/` to explain `autostart` and recommended usage patterns.

