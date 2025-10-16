#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostgreSQL Key-Value Backend.

Leichtgewichtiger Adapter, der ein Key-Value-Interface auf einer PostgreSQL-Tabelle
bereitstellt. Nutzt ``psycopg`` (v3) und speichert Werte als JSONB.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

try:  # pragma: no cover - optional, abhängig von psycopg-Version
    from psycopg.types.json import Json, Jsonb  # type: ignore
    _JSON_WRAPPERS = (Json, Jsonb)
except Exception:  # pragma: no cover - ältere psycopg-Version
    _JSON_WRAPPERS = tuple()

from database.database_api_base import DatabaseBackend

logger = logging.getLogger(__name__)


class PostgreSQLKeyValueBackend(DatabaseBackend):
    """Key-Value-Backend auf Basis einer PostgreSQL-Tabelle."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        cfg = config or {}

        self._dsn = cfg.get("dsn") or cfg.get("connection_string")
        self._host = cfg.get("host", "localhost")
        self._port = int(cfg.get("port", 5432) or 5432)
        self._user = cfg.get("user") or cfg.get("username") or "postgres"
        self._password = cfg.get("password") or cfg.get("secret") or ""
        self._database = cfg.get("database") or cfg.get("dbname") or "postgres"
        self._connect_timeout = int(cfg.get("connect_timeout", 10))

        settings = cfg.get("settings") or {}
        self._table = settings.get("table", "kv_store")
        self._auto_create = settings.get("auto_create_table", True)

        self.client: Optional[psycopg.Connection] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        try:
            if self._dsn:
                self.client = psycopg.connect(
                    self._dsn,
                    row_factory=dict_row,
                    connect_timeout=self._connect_timeout,
                )
            else:
                self.client = psycopg.connect(
                    host=self._host,
                    port=self._port,
                    user=self._user,
                    password=self._password,
                    dbname=self._database,
                    row_factory=dict_row,
                    connect_timeout=self._connect_timeout,
                )
            self.client.autocommit = True
            self._is_connected = True

            if self._auto_create:
                self._ensure_table()

            logger.info("PostgreSQL Key-Value Backend connected -> %s:%s/%s", self._host, self._port, self._database)
            return True
        except Exception as exc:  # pragma: no cover - echte Verbindungsfehler
            logger.exception("PostgreSQL Key-Value connect failed: %s", exc)
            self.client = None
            self._is_connected = False
            return False

    def disconnect(self):
        try:
            if self.client:
                self.client.close()
        finally:
            self.client = None
            self._is_connected = False

    def is_available(self) -> bool:
        return bool(self.client and not self.client.closed)

    def get_backend_type(self) -> str:
        return "postgresql-keyvalue"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def _ensure_table(self) -> None:
        if not self.client:
            return
        table_ident = sql.Identifier(self._table)
        index_ident = sql.Identifier(f"{self._table}_expires_idx")
        create_table = sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {table} (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL,
                ttl_seconds INTEGER,
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        ).format(table=table_ident)
        create_index = sql.SQL(
            """
            CREATE INDEX IF NOT EXISTS {index} ON {table} (expires_at)
            """
        ).format(index=index_ident, table=table_ident)
        with self.client.cursor() as cur:
            cur.execute(create_table)
            cur.execute(create_index)

    def _normalize_value(self, stored: Any) -> Any:
        if stored is None:
            return None
        if isinstance(stored, (dict, list, int, float, bool, type(None))):
            return stored
        if _JSON_WRAPPERS and isinstance(stored, _JSON_WRAPPERS):
            try:
                return stored.loads()
            except Exception:
                try:
                    return stored.unwrap()
                except Exception:
                    pass
        if hasattr(stored, 'loads'):
            try:
                return stored.loads()
            except Exception:
                pass
        try:
            return json.loads(stored)
        except Exception:
            return stored

    def _is_expired(self, expires_at: Optional[datetime]) -> bool:
        if not expires_at:
            return False
        return expires_at <= datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Public API similar to Redis adapters
    # ------------------------------------------------------------------
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self.client:
            raise RuntimeError("PostgreSQL key-value backend not connected")

        ttl_seconds = int(ttl) if ttl is not None else None
        expires_at = None
        if ttl_seconds is not None and ttl_seconds > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        payload = json.dumps(value)
        with self.client.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                    INSERT INTO {table} (key, value, ttl_seconds, expires_at, created_at, updated_at)
                    VALUES (%s, %s::jsonb, %s, %s, NOW(), NOW())
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        ttl_seconds = EXCLUDED.ttl_seconds,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = NOW();
                    """
                ).format(table=sql.Identifier(self._table)),
                (key, payload, ttl_seconds, expires_at),
            )
        return True

    def get(self, key: str, default: Any = None) -> Any:
        if not self.client:
            raise RuntimeError("PostgreSQL key-value backend not connected")
        with self.client.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT value, expires_at FROM {table} WHERE key = %s").format(
                    table=sql.Identifier(self._table)
                ),
                (key,),
            )
            row = cur.fetchone()
        if not row:
            return default

        expires_at = row.get("expires_at") if isinstance(row, dict) else row["expires_at"]
        if self._is_expired(expires_at):
            self.delete(key)
            return default

        stored = row.get("value") if isinstance(row, dict) else row["value"]
        return self._normalize_value(stored)

    def delete(self, key: str) -> bool:
        if not self.client:
            raise RuntimeError("PostgreSQL key-value backend not connected")
        with self.client.cursor() as cur:
            cur.execute(
                sql.SQL("DELETE FROM {table} WHERE key = %s").format(table=sql.Identifier(self._table)),
                (key,),
            )
            return cur.rowcount > 0

    def exists(self, key: str) -> bool:
        if not self.client:
            raise RuntimeError("PostgreSQL key-value backend not connected")
        with self.client.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT 1 FROM {table} WHERE key = %s").format(table=sql.Identifier(self._table)),
                (key,),
            )
            return cur.fetchone() is not None

    def keys(self, pattern: Optional[str] = None) -> List[str]:
        if not self.client:
            raise RuntimeError("PostgreSQL key-value backend not connected")
        sql_pattern = "%"
        if pattern:
            sql_pattern = pattern.replace("*", "%")
        with self.client.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT key FROM {table} WHERE key LIKE %s").format(table=sql.Identifier(self._table)),
                (sql_pattern,),
            )
            rows = cur.fetchall() or []
        return [row["key"] if isinstance(row, dict) else row[0] for row in rows]

    def clear(self) -> int:
        if not self.client:
            raise RuntimeError("PostgreSQL key-value backend not connected")
        with self.client.cursor() as cur:
            cur.execute(sql.SQL("DELETE FROM {table}").format(table=sql.Identifier(self._table)))
            return cur.rowcount or 0

    # ------------------------------------------------------------------
    # Monitoring helpers
    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "backend": self.get_backend_type(),
            "table": self._table,
            "connected": self.is_available(),
        }
        if not self.client:
            return info
        with self.client.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE expires_at IS NOT NULL) AS expiring FROM {table}"
                ).format(table=sql.Identifier(self._table))
            )
            row = cur.fetchone()
        if row:
            info["keys_total"] = row.get("total") if isinstance(row, dict) else row[0]
            info["keys_expiring"] = row.get("expiring") if isinstance(row, dict) else row[1]
        return info

    def list_collections(self) -> Iterable[str]:
        return [self._table]


def get_backend_class():
    return PostgreSQLKeyValueBackend
