# Changelog

## v1.8.0 (2026-08-17)

### Added
- **Real-Time Output Streaming (SSE)** — Line-by-line live stdout/stderr streaming over Server-Sent Events (`/jobs/<id>/stream`), allowing users to watch task progress in real time.
- **Active Job Cancellation** — Interactive "Stop / Cancel" button to gracefully terminate running Ansible jobs on demand.
- **Structured Play Recap Badges** — Automatic parsing of Ansible `PLAY RECAP` into visual badges (`ok`, `changed`, `unreachable`, `failed`, `skipped`).
- **Persistent SQLite History** — Embedded database storing complete execution records, timestamps, durations, and output logs with pagination.
- **Advanced Execution Options** — Support for Check Mode (`--check` / dry-run), Diff Mode (`--diff`), Extra Variables (`-e`), Tags (`--tags`), Skip Tags (`--skip-tags`), Forks (`-f`), and SSH Private Key upload/paste.
- **Built-in Playbook Templates** — 1-click templates for System Update, Nginx Setup, Docker Install, User Management, and Diagnostics.
- **Dynamic Inventory Structure Explorer** — Visual tree explorer parsing INI/YAML inventories into groups, hosts, and variables.
- **Log Search & Task Filters** — In-output search (`Ctrl+F`), match counter, and filters for *All*, *Changed Only*, and *Failed Only*.
- **Automated Test Suite** — Comprehensive `pytest` test suite with 39 unit and integration tests covering all services, parsers, and API blueprints.

### Refactored
- **Modular Package Architecture** — Reorganized core application into an `ekumen` package using the Flask Application Factory pattern (`create_app()`) and Blueprints (`runner`, `playbooks`, `inventories`, `collections`, `jobs`, `templates`, `web`), while keeping root entrypoints backwards-compatible.
- **Unified Configuration** — Standardized all configuration variables to use `EKUMEN_*` prefixes with seamless fallback for legacy `ANSIBLE_SHUTTLE_*` variables.
- **Synchronized Inventory Storage** — Connected frontend inventory management to the backend `/inventories` REST API (matching Playbooks), with automated client-side migration for legacy `localStorage` entries.
- **Multi-Worker Output Cache** — Implemented an `OutputCache` service to safely handle file downloads across multi-process Gunicorn deployments.
- **Security & Path Hardening** — Added path containment validation (`os.path.commonpath`) to prevent path traversal in inventory and playbook managers.
- **Frontend Polish & ANSI Terminal Output** — Added ANSI escape sequence decoding for color-accurate terminal logs, Copy-to-Clipboard output button, and keyboard shortcuts (`Ctrl+Enter` to run, `Ctrl+S` to save).

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
