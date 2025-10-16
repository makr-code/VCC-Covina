# Changelog

## Unreleased

- Hardened database adapters to avoid import-time network/drivers initialisation.
  - Many adapters now defer heavy client initialization to `connect()` and set availability flags.
  - Replaced import-time ImportError raises with warnings; adapters will fail gracefully on `connect()` if optional libs are missing.
- Refactored `DatabaseManager` to lazily start backends:
  - `DatabaseManager(..., autostart=False)` now defers `connect()` and collects instances in `_backends_to_start`.
  - Added `start_all_backends(backend_names=None, timeout_per_backend=5)` to explicitly start deferred backends and update module status.
  - Factory functions `create_database_manager()` and `get_database_manager()` honor `autostart` config flag.
- Fixes:
  - Consistent attribute naming for key-value backend (`keyvalue_backend`).
  - Fixed indentation/regression introduced during refactors.
- Tests:
  - Added unit tests for manager behavior and error propagation under `tests/`.


## Previous

- See repository history for earlier releases.
