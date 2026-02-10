# Changelog

## v1.7.5 (2026-02-10)

### Fixed
- **Install script** — No longer crashes on non-git installs; backs up data dirs and re-clones.
- **Install script** — Preserves existing port on updates instead of resetting to 5000.
- **Install script** — Now prompts for port interactively (skipped when piped).

### Cleaned Up
- Removed duplicate files: `screenshots/` (kept `docs/screenshots/`), root `install.sh` / `install-offline.sh` (kept `scripts/`), `docker/Dockerfile` / `docker/.dockerignore` (kept root copies).
- Updated `docker-compose.yml` to reference root Dockerfile.

## v1.7.4 (2026-02-10)

### Refactored
- **Extracted PlaybookManager** — Playbook CRUD logic moved from `app.py` into its own `playbook_manager.py` class, mirroring `InventoryManager` patterns.
- **Split monolithic frontend** — `script.js` (982 lines) split into 5 focused modules: `theme.js`, `history.js`, `playbooks.js`, `inventories.js`, `collections.js`, and `runner.js`. Consolidated 3 separate `DOMContentLoaded` listeners into one.
- **Direct path lookup** — `get_collection()` and `get_role()` in `collection_manager.py` now use direct filesystem checks (O(1)) instead of scanning all installed items (O(n)).
- **Standardized error handling** — All managers now use consistent `(success, result_or_error)` tuple returns.

### Improved
- **Added structured logging** — Replaced `print()` statements with Python `logging` module across `app.py`, `ansible_runner.py`, `inventory_manager.py`, `collection_manager.py`, and new `playbook_manager.py`.
- **Fixed import ordering** — Moved `os`, `re`, `datetime` imports to the top of `app.py` per PEP 8.
- **Top-level `import yaml`** — Moved inline `import yaml` calls in `collection_manager.py` to the module level.

### Fixed
- **Version sync** — Dockerfile `LABEL version` now matches `Config.VERSION`.
- **Docker Compose** — Removed deprecated `version: '3.8'` key.
- **Dependency pinning** — Pinned `gunicorn>=21.2.0` in `requirements.txt`.
