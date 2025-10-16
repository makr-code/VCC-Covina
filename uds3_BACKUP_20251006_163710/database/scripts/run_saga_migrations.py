#!/usr/bin/env python3
"""Run saga migrations against the configured relational backend.

This script loads `server_config.json` (if present) or reads environment
variables to build a DatabaseManager instance and then calls the migration
helpers in `db_migrations.py`.

The script is intentionally conservative: it only calls idempotent helpers and
logs errors instead of raising so it can be used in automation safely.
"""
import os
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # parent of the package folder
sys.path.insert(0, str(ROOT))

from database.database_manager import DatabaseManager
from database.db_migrations import ensure_saga_schema, ensure_idempotency_column

logger = logging.getLogger("saga_migrations")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_config() -> dict:
    """Try to read the project's canonical DB config helper first.

    Fallback to the old `server_config.json` parsing if the helper is not
    available or returns an empty result.
    """
    cfg = {}
    try:
        # Prefer the project's config helper which returns the expected shape
        import database.config as db_config
        cfg = db_config.get_database_backend_dict() or {}
    except Exception:
        # Fall back to the older free-form server_config.json
        cfg_path = ROOT / "server_config.json"
        if cfg_path.exists():
            try:
                with cfg_path.open("r", encoding="utf-8") as fh:
                    cfg = json.load(fh)
            except Exception as exc:
                logger.warning("Could not load server_config.json: %s", exc)

    # Allow ENV override for relational DB section (simple host override)
    rel_host = os.environ.get("SAGA_REL_HOST")
    if rel_host:
        # If cfg is a dict with 'relational' key expected by DatabaseManager
        if isinstance(cfg, dict):
            rel = cfg.get("relational", {})
            if not isinstance(rel, dict):
                rel = {}
            rel.update({"host": rel_host, "enabled": True})
            cfg["relational"] = rel
        else:
            # If we fell back to server_config.json (list), set a minimal dict
            cfg = {"relational": {"host": rel_host, "enabled": True}}

    return cfg


def main():
    cfg = load_config()
    # Wenn das Graph-Backend lokal fehlschlägt (z.B. fehlerhafte Neo4j-Adapter),
    # deaktivieren wir es hier temporär, damit wir nur die relationalen
    # Migrationen ausführen können.
    try:
        if isinstance(cfg, dict):
            graph_cfg = cfg.get('graph')
            if isinstance(graph_cfg, dict):
                graph_cfg['enabled'] = False
                cfg['graph'] = graph_cfg
            else:
                cfg['graph'] = {'enabled': False}
    except Exception:
        # Schützt vor unerwarteten Strukturen in der Konfiguration
        pass
    manager = DatabaseManager(cfg)
    rel = manager.get_relational_backend()
    if rel is None:
        logger.error("No relational backend available. Check configuration or set SAGA_REL_HOST env var.")
        return 2

    logger.info("Ensuring saga schema...")
    ensure_saga_schema(rel)

    logger.info("Ensuring idempotency column/index...")
    ensure_idempotency_column(rel)

    logger.info("Migrations completed (idempotent).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
