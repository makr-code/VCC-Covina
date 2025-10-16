#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UDS3 Identity Service

Stellt das duale Identitätskonzept (UUID ↔ Aktenzeichen) bereit und
persistiert Cross-Database-Mappings in der relationalen Datenbank.

Der Service kapselt sämtliche Datenbankzugriffe, erzwingt einmalige
Aktenzeichen und bietet eine konsistente API für andere Module.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

# Lazy import placeholder, wird erst bei Bedarf aufgelöst
get_relational_db: Any = None

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfungen
    try:
        from database.database_api_base import RelationalDatabaseBackend  # type: ignore
    except Exception:
        from typing import Any

        RelationalDatabaseBackend = Any  # type: ignore
else:  # Laufzeit: generischer Any-Typ
    RelationalDatabaseBackend = Any  # type: ignore

__all__ = [
    "IdentityServiceError",
    "IdentityNotFoundError",
    "AktenzeichenConflictError",
    "IdentityRecord",
    "UDS3IdentityService",
    "get_identity_service",
]


class IdentityServiceError(Exception):
    """Allgemeiner Fehler des Identity-Service."""


class IdentityNotFoundError(IdentityServiceError):
    """Wird geworfen, wenn eine angefragte Identity nicht existiert."""


class AktenzeichenConflictError(IdentityServiceError):
    """Signalisiert einen Konflikt durch ein bereits vergebenes Aktenzeichen."""


@dataclass(slots=True)
class IdentityRecord:
    """Domänenobjekt für eine Identity inkl. Mapping-Informationen."""

    uuid: str
    aktenzeichen: Optional[str]
    status: str
    source_system: Optional[str]
    mappings: Dict[str, Optional[str]]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class UDS3IdentityService:
    """Service zur Verwaltung von UUID-Identitäten und Aktenzeichen."""

    def __init__(self, relational_backend: Optional[Any] = None):
        self.logger = logging.getLogger("uds3.identity.service")
        backend = relational_backend or self._resolve_relational_backend()
        self.relational_backend = backend
        if self.relational_backend is None:
            self.logger.warning("⚠️ Relationales Backend nicht verfügbar - verwende SQLite fallback")
            self.relational_backend = self._create_sqlite_fallback()

        self._lock = threading.RLock()
        self._ensure_schema()

    def _create_sqlite_fallback(self):
        """Creates a minimal SQLite fallback backend"""
        import sqlite3
        from pathlib import Path
        
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        db_path = data_dir / "uds3_identity_fallback.db"
        
        class SQLiteFallbackBackend:
            def __init__(self, db_path):
                self.db_path = db_path
            
            def execute_query(self, sql, params=None):
                """Execute SQL query and return results"""
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(sql, params or [])
                    return cursor.fetchall()
            
            def execute(self, sql, params=None):
                """Execute SQL with params"""
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql, params or [])
                    conn.commit()
                    return cursor.fetchall()
            
            def execute_many(self, sql, params_list):
                """Execute SQL with multiple params"""
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.executemany(sql, params_list)
                    conn.commit()
            
            def execute_and_return(self, sql, params=None):
                """Execute SQL and return results"""
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(sql, params or [])
                    return cursor.fetchall()
        
        return SQLiteFallbackBackend(db_path)

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------
    def generate_uuid(
        self,
        *,
        source_system: Optional[str] = None,
        aktenzeichen: Optional[str] = None,
        status: str = "registered",
        actor: str = "system",
    ) -> IdentityRecord:
        """Erzeugt eine neue UUID und legt sie in der Identity-Tabelle ab."""

        normalized_aktz = self._normalize_aktenzeichen(aktenzeichen)
        with self._lock:
            new_uuid = self._normalize_uuid(str(uuid.uuid4()))
            now = datetime.now(timezone.utc).isoformat()
            result = self._execute(
                """
                INSERT INTO administrative_identities (uuid, aktenzeichen, status, source_system, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_uuid,
                    normalized_aktz,
                    status,
                    source_system,
                    now,
                    now,
                ),
            )
            if not result:
                raise IdentityServiceError("Identity konnte nicht erstellt werden")

            self.record_audit(
                new_uuid,
                action="create_uuid",
                details={
                    "source_system": source_system,
                    "aktenzeichen": normalized_aktz,
                },
                actor=actor,
            )

            return self.resolve_by_uuid(new_uuid)

    def ensure_identity(
        self,
        uuid_value: str,
        *,
        aktenzeichen: Optional[str] = None,
        source_system: Optional[str] = None,
        status: str = "registered",
        actor: str = "system",
    ) -> IdentityRecord:
        """Stellt sicher, dass eine Identity mit der angegebenen UUID existiert."""

        normalized_uuid = self._normalize_uuid(uuid_value)
        normalized_aktz = self._normalize_aktenzeichen(aktenzeichen)

        with self._lock:
            existing = self._fetch_identity(normalized_uuid)
            if existing:
                if normalized_aktz and existing.get("aktenzeichen") != normalized_aktz:
                    return self.register_aktenzeichen(
                        normalized_uuid,
                        normalized_aktz,
                        actor=actor,
                        status=status,
                    )
                return self.resolve_by_uuid(normalized_uuid)

            now = datetime.now(timezone.utc).isoformat()
            result = self._execute(
                """
                INSERT INTO administrative_identities (uuid, aktenzeichen, status, source_system, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_uuid,
                    normalized_aktz,
                    status,
                    source_system,
                    now,
                    now,
                ),
            )
            if not result:
                raise IdentityServiceError("Identity konnte nicht erstellt werden")

            self.record_audit(
                normalized_uuid,
                action="ensure_identity",
                details={
                    "source_system": source_system,
                    "aktenzeichen": normalized_aktz,
                },
                actor=actor,
            )

            return self.resolve_by_uuid(normalized_uuid)

    def register_aktenzeichen(
        self,
        uuid_value: str,
        aktenzeichen: str,
        *,
        actor: str = "system",
        status: Optional[str] = None,
    ) -> IdentityRecord:
        """Registriert oder aktualisiert das Aktenzeichen für eine bestehende UUID."""

        normalized_uuid = self._normalize_uuid(uuid_value)
        normalized_aktz = self._normalize_aktenzeichen(aktenzeichen)

        with self._lock:
            record = self.resolve_by_uuid(normalized_uuid)
            now = datetime.now(timezone.utc).isoformat()
            result = self._execute(
                """
                UPDATE administrative_identities
                   SET aktenzeichen = ?,
                       status = COALESCE(?, status),
                       updated_at = ?
                 WHERE uuid = ?
                """,
                (
                    normalized_aktz,
                    status,
                    now,
                    normalized_uuid,
                ),
            )
            if not result:
                raise IdentityServiceError("Aktenzeichen konnte nicht gesetzt werden")

            self.record_audit(
                normalized_uuid,
                action="register_aktenzeichen",
                details={"aktenzeichen": normalized_aktz, "status": status},
                actor=actor,
            )

            return self.resolve_by_uuid(normalized_uuid)

    def bind_backend_ids(
        self,
        uuid_value: str,
        *,
        relational_id: Optional[str] = None,
        graph_id: Optional[str] = None,
        vector_id: Optional[str] = None,
        file_storage_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        actor: str = "system",
    ) -> IdentityRecord:
        """Persistiert Backend-spezifische IDs im Mapping."""

        normalized_uuid = self._normalize_uuid(uuid_value)
        with self._lock:
            identity = self.resolve_by_uuid(normalized_uuid)
            current_mapping = self._fetch_mapping(normalized_uuid)
            current_metadata = self._deserialize_metadata(
                current_mapping.get("metadata")
            )

            updated_mapping = {
                "relational_id": relational_id
                if relational_id is not None
                else current_mapping.get("relational_id"),
                "graph_id": graph_id
                if graph_id is not None
                else current_mapping.get("graph_id"),
                "vector_id": vector_id
                if vector_id is not None
                else current_mapping.get("vector_id"),
                "file_storage_id": file_storage_id
                if file_storage_id is not None
                else current_mapping.get("file_storage_id"),
            }
            updated_metadata = current_metadata.copy()
            if metadata:
                updated_metadata.update(metadata)

            now = datetime.now(timezone.utc).isoformat()
            metadata_json = (
                json.dumps(updated_metadata, ensure_ascii=False)
                if updated_metadata
                else None
            )

            if current_mapping:
                result = self._execute(
                    """
                    UPDATE administrative_identity_mappings
                       SET aktenzeichen = ?,
                           relational_id = ?,
                           graph_id = ?,
                           vector_id = ?,
                           file_storage_id = ?,
                           metadata = ?,
                           updated_at = ?
                     WHERE uuid = ?
                    """,
                    (
                        identity.aktenzeichen,
                        updated_mapping["relational_id"],
                        updated_mapping["graph_id"],
                        updated_mapping["vector_id"],
                        updated_mapping["file_storage_id"],
                        metadata_json,
                        now,
                        normalized_uuid,
                    ),
                )
            else:
                result = self._execute(
                    """
                    INSERT INTO administrative_identity_mappings (
                        uuid,
                        aktenzeichen,
                        relational_id,
                        graph_id,
                        vector_id,
                        file_storage_id,
                        metadata,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        normalized_uuid,
                        identity.aktenzeichen,
                        updated_mapping["relational_id"],
                        updated_mapping["graph_id"],
                        updated_mapping["vector_id"],
                        updated_mapping["file_storage_id"],
                        metadata_json,
                        now,
                    ),
                )

            if not result:
                raise IdentityServiceError("Mapping konnte nicht gespeichert werden")

            self.record_audit(
                normalized_uuid,
                action="bind_backend_ids",
                details={"mappings": updated_mapping, "metadata": updated_metadata},
                actor=actor,
            )

            return self.resolve_by_uuid(normalized_uuid)

    def resolve_by_uuid(self, uuid_value: str) -> IdentityRecord:
        """Lädt eine Identity anhand der UUID."""

        normalized_uuid = self._normalize_uuid(uuid_value)
        identity_row = self._fetch_identity(normalized_uuid)
        if identity_row is None:
            raise IdentityNotFoundError(
                f"Identity mit UUID '{normalized_uuid}' nicht gefunden"
            )

        mapping_row = self._fetch_mapping(normalized_uuid)
        return self._build_record(identity_row, mapping_row)

    def resolve_by_aktenzeichen(self, aktenzeichen: str) -> IdentityRecord:
        """Lädt eine Identity anhand des Aktenzeichens."""

        normalized_aktz = self._normalize_aktenzeichen(aktenzeichen)
        row = self.relational_backend.execute_query(
            """
            SELECT uuid, aktenzeichen, status, source_system, created_at, updated_at
              FROM administrative_identities
             WHERE aktenzeichen = ?
                         ORDER BY updated_at DESC
                         LIMIT 1
            """,
            (normalized_aktz,),
        )
        if not row:
            raise IdentityNotFoundError(
                f"Aktenzeichen '{normalized_aktz}' ist unbekannt"
            )

        identity_row = row[0]
        mapping_row = self._fetch_mapping(identity_row["uuid"])
        return self._build_record(identity_row, mapping_row)

    def record_audit(
        self,
        uuid_value: str,
        *,
        action: str,
        details: Dict[str, Any],
        actor: str = "system",
    ) -> None:
        """Persistiert einen Audit-Eintrag."""

        normalized_uuid = self._normalize_uuid(uuid_value)
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self._execute(
            """
            INSERT INTO administrative_identity_audit (audit_id, uuid, action, actor, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                normalized_uuid,
                action,
                actor,
                json.dumps(details or {}, ensure_ascii=False),
                now,
            ),
        )

    # ------------------------------------------------------------------
    # Interne Helfer
    # ------------------------------------------------------------------
    def _ensure_schema(self) -> None:
        """Erzeugt erforderliche Tabellen und Indizes, falls noch nicht vorhanden."""

        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS administrative_identities (
                uuid TEXT PRIMARY KEY,
                aktenzeichen TEXT,
                status TEXT DEFAULT 'registered',
                source_system TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS administrative_identity_mappings (
                uuid TEXT PRIMARY KEY REFERENCES administrative_identities(uuid) ON DELETE CASCADE,
                aktenzeichen TEXT,
                relational_id TEXT,
                graph_id TEXT,
                vector_id TEXT,
                file_storage_id TEXT,
                metadata TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS administrative_identity_audit (
                audit_id TEXT PRIMARY KEY,
                uuid TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS administrative_identity_metrics (
                metric_id TEXT PRIMARY KEY,
                aktenzeichen TEXT NOT NULL REFERENCES administrative_identities(aktenzeichen) ON DELETE CASCADE,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                units TEXT,
                metadata TEXT,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS administrative_identity_traces (
                trace_id TEXT PRIMARY KEY,
                aktenzeichen TEXT NOT NULL REFERENCES administrative_identities(aktenzeichen) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_aktenzeichen ON administrative_identities(aktenzeichen)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_mappings_relational ON administrative_identity_mappings(relational_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_mappings_graph ON administrative_identity_mappings(graph_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_mappings_vector ON administrative_identity_mappings(vector_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_mappings_file ON administrative_identity_mappings(file_storage_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_audit_uuid ON administrative_identity_audit(uuid)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_metrics_aktz ON administrative_identity_metrics(aktenzeichen)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_metrics_name ON administrative_identity_metrics(metric_name)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_metrics_observed ON administrative_identity_metrics(observed_at)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_traces_aktz ON administrative_identity_traces(aktenzeichen)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_traces_stage ON administrative_identity_traces(stage)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_identity_traces_status ON administrative_identity_traces(status)
            """,
        ]

        for statement in ddl_statements:
            self.relational_backend.execute_query(statement)

    def _resolve_relational_backend(self) -> Optional[Any]:
        """Lädt das relationale Backend lazily und cached den Resolver."""

        global get_relational_db

        if callable(get_relational_db):
            try:
                return get_relational_db()
            except Exception as exc:  # pragma: no cover - defensive fallback
                self.logger.warning(
                    "Relational-Backend (cached) konnte nicht geladen werden: %s", exc
                )
                return None

        try:
            from database.database_api import get_relational_db as resolver  # type: ignore
        except ImportError:
            self.logger.debug(
                "database_api nicht verfügbar – Identity-Service arbeitet ohne relationales Backend"
            )
            return None

        get_relational_db = resolver
        try:
            return resolver()
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.logger.warning(
                "Relational-Backend konnte nicht initialisiert werden: %s", exc
            )
            return None

    def _execute(self, query: str, params: tuple) -> bool:
        """Wrapper für execute_query mit Fehlerprüfung."""

        result = self.relational_backend.execute_query(query, params)
        if not result:
            return False
        first = result[0]
        affected = first.get("affected_rows") if isinstance(first, dict) else None
        return affected is None or affected > 0

    def _fetch_identity(self, uuid_value: str) -> Optional[Dict[str, Any]]:
        rows = self.relational_backend.execute_query(
            """
            SELECT uuid, aktenzeichen, status, source_system, created_at, updated_at
              FROM administrative_identities
             WHERE uuid = ?
             LIMIT 1
            """,
            (uuid_value,),
        )
        return rows[0] if rows else None

    def _fetch_mapping(self, uuid_value: str) -> Dict[str, Any]:
        rows = self.relational_backend.execute_query(
            """
            SELECT uuid, aktenzeichen, relational_id, graph_id, vector_id, file_storage_id, metadata, updated_at
              FROM administrative_identity_mappings
             WHERE uuid = ?
             LIMIT 1
            """,
            (uuid_value,),
        )
        return rows[0] if rows else {}

    @staticmethod
    def _deserialize_metadata(value: Any) -> Dict[str, Any]:
        if not value:
            return {}
        if isinstance(value, dict):
            return value.copy()
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {"raw": value}

    def _build_record(
        self, identity_row: Dict[str, Any], mapping_row: Dict[str, Any]
    ) -> IdentityRecord:
        metadata_dict = self._deserialize_metadata(
            mapping_row.get("metadata") if mapping_row else None
        )

        mappings = {
            "relational_id": mapping_row.get("relational_id") if mapping_row else None,
            "graph_id": mapping_row.get("graph_id") if mapping_row else None,
            "vector_id": mapping_row.get("vector_id") if mapping_row else None,
            "file_storage_id": mapping_row.get("file_storage_id")
            if mapping_row
            else None,
        }

        return IdentityRecord(
            uuid=identity_row["uuid"],
            aktenzeichen=identity_row.get("aktenzeichen"),
            status=identity_row.get("status", "registered"),
            source_system=identity_row.get("source_system"),
            mappings=mappings,
            metadata=metadata_dict,
            created_at=self._parse_datetime(identity_row.get("created_at")),
            updated_at=self._parse_datetime(identity_row.get("updated_at")),
        )

    @staticmethod
    def _normalize_uuid(uuid_value: str) -> str:
        return str(uuid_value).strip().lower()

    @staticmethod
    def _normalize_aktenzeichen(aktenzeichen: Optional[str]) -> Optional[str]:
        if aktenzeichen is None:
            return None
        normalized = aktenzeichen.strip()
        return normalized or None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if not value:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            # SQLite liefert ggf. "YYYY-MM-DD HH:MM:SS"
            try:
                parsed = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
                return parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.now(timezone.utc)


_identity_service: Optional[UDS3IdentityService] = None
_identity_lock = threading.Lock()


def get_identity_service(
    relational_backend: Optional[Any] = None,
) -> UDS3IdentityService:
    """Singleton-Zugriff auf den Identity-Service."""

    global _identity_service
    if _identity_service is None:
        with _identity_lock:
            if _identity_service is None:
                _identity_service = UDS3IdentityService(relational_backend)
    return _identity_service
