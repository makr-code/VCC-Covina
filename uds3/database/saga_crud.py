"""Saga-orientierte CRUD-Helfer für alle Covina-Datenbank-Typen.

Dieses Modul stellt abstrakte CRUD-Operationen bereit, die über den
`DatabaseManager` auf die konkreten Backend-Adapter zugreifen. Die
Funktionen sind so gestaltet, dass sie in Saga-Schritten verwendet werden
können: Jede Methode gibt ein `CrudResult` zurück, das neben dem
Erfolgsstatus auch strukturierte Metadaten enthält, die in weiteren
Saga-Schritten (z.\u202fB. für Kompensationen) genutzt werden können.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from database import config
from database.database_manager import DatabaseManager
from .adapter_governance import AdapterGovernanceError

try:
    from database import db_migrations
except Exception:  # pragma: no cover - optional dependency during bootstrap
    db_migrations = None

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CrudResult:
    """Standardisiertes Ergebnis einer CRUD-Operation."""

    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        """Konvertiert das Ergebnis in ein serialisierbares Dict."""
        payload = {"success": self.success, **self.data}
        if self.error:
            payload["error"] = self.error
        return payload


class SagaDatabaseCRUD:
    """Bündelt Saga-taugliche CRUD-Operationen für alle Backend-Typen."""

    def __init__(
        self,
        manager: Optional[DatabaseManager] = None,
        *,
        manager_getter: Optional[Callable[[], DatabaseManager]] = None,
    ) -> None:
        self._manager = manager
        self._manager_getter = manager_getter
        self._fallback_manager: Optional[DatabaseManager] = None

    # ------------------------------------------------------------------
    # Governance Enforcement
    # ------------------------------------------------------------------
    def _enforce_governance(
        self,
        manager: DatabaseManager,
        backend_key: str,
        operation: str,
        payload: Any,
        failure_payload: Dict[str, Any],
    ) -> Optional[CrudResult]:
        ensure = getattr(manager, "ensure_operation_allowed", None)
        enforce_payload = getattr(manager, "enforce_payload_policy", None)
        try:
            if ensure:
                ensure(backend_key, operation)
            if enforce_payload:
                enforce_payload(backend_key, operation, payload)
        except AdapterGovernanceError as exc:
            blocked_payload = dict(failure_payload)
            blocked_payload["governance_blocked"] = True
            return CrudResult(False, blocked_payload, str(exc))
        return None

    # ------------------------------------------------------------------
    # Observability Helpers
    # ------------------------------------------------------------------
    def _get_relational_backend(self, manager: DatabaseManager) -> Optional[Any]:
        backend_getter = getattr(manager, "get_relational_backend", None)
        if callable(backend_getter):
            try:
                return backend_getter()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.debug("Relational backend Zugriff fehlgeschlagen: %s", exc)
        return None

    def _normalize_aktenzeichen(self, candidate: Any) -> Optional[str]:
        if candidate is None:
            return None
        if isinstance(candidate, str):
            candidate = candidate.strip()
            return candidate or None
        normalized = str(candidate).strip()
        return normalized or None

    def _find_key_case_insensitive(self, obj: Any, target: str) -> Optional[Any]:
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    key_lower = key.lower() if isinstance(key, str) else key
                except Exception:
                    key_lower = key
                if key_lower == target:
                    return value
                nested = self._find_key_case_insensitive(value, target)
                if nested is not None:
                    return nested
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                nested = self._find_key_case_insensitive(item, target)
                if nested is not None:
                    return nested
        return None

    def _extract_aktenzeichen(self, *sources: Any) -> Optional[str]:
        for source in sources:
            candidate = self._find_key_case_insensitive(source, "aktenzeichen")
            normalized = self._normalize_aktenzeichen(candidate)
            if normalized:
                return normalized
        return None

    def _safe_json_dump(self, payload: Any, *, max_length: int = 4000) -> str:
        try:
            serialized = json.dumps(payload, ensure_ascii=False, default=str)
        except TypeError:
            serialized = json.dumps(str(payload), ensure_ascii=False, default=str)
        if len(serialized) > max_length:
            return serialized[: max_length - 3] + "..."
        return serialized

    def _persist_identity_trace(
        self,
        relational_backend: Any,
        *,
        aktenzeichen: str,
        stage: str,
        status: str,
        details: str,
    ) -> None:
        try:
            relational_backend.execute_query(
                """
                INSERT INTO administrative_identity_traces (trace_id, aktenzeichen, stage, status, details, observed_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    str(uuid.uuid4()),
                    aktenzeichen,
                    stage,
                    status,
                    details,
                ),
            )
        except Exception as exc:  # pragma: no cover - observability must not break flow
            logger.debug("Identitäts-Trace konnte nicht geschrieben werden: %s", exc)

    def _persist_identity_metrics(
        self,
        relational_backend: Any,
        *,
        aktenzeichen: str,
        metrics: List[Dict[str, Any]],
    ) -> None:
        for entry in metrics:
            try:
                relational_backend.execute_query(
                    """
                    INSERT INTO administrative_identity_metrics (metric_id, aktenzeichen, metric_name, metric_value, units, metadata, observed_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        str(uuid.uuid4()),
                        aktenzeichen,
                        entry.get("metric_name"),
                        entry.get("metric_value"),
                        entry.get("units"),
                        entry.get("metadata"),
                    ),
                )
            except Exception as exc:  # pragma: no cover - observability should not raise
                logger.debug("Identitäts-Metrik konnte nicht geschrieben werden (%s): %s", entry.get("metric_name"), exc)

    def _record_identity_observability(
        self,
        manager: DatabaseManager,
        backend_key: str,
        operation: str,
        start_time: float,
        payload: Dict[str, Any],
        result: CrudResult,
    ) -> None:
        relational_backend = self._get_relational_backend(manager)
        if relational_backend is None:
            return

        aktenzeichen = self._extract_aktenzeichen(payload, result.data)
        if not aktenzeichen:
            return

        try:
            duration_ms = max(int((time.perf_counter() - start_time) * 1000), 0)
        except Exception:  # pragma: no cover - fallback bei Zeitmessfehlern
            duration_ms = 0

        stage = f"{backend_key}.{operation}"
        governance_blocked = bool(result.data.get("governance_blocked"))
        status = "success" if result.success else ("governance_blocked" if governance_blocked else "error")

        trace_details = self._safe_json_dump(
            {
                "payload": payload,
                "result": result.data,
                "error": result.error,
            }
        )

        metrics_metadata = self._safe_json_dump(
            {
                "backend": backend_key,
                "operation": operation,
                "success": result.success,
                "status": status,
                "governance_blocked": governance_blocked,
                "error": result.error,
                "document_id": payload.get("document_id"),
                "collection": payload.get("collection"),
            }
        )

        metric_entries: List[Dict[str, Any]] = [
            {
                "metric_name": f"{stage}.attempt",
                "metric_value": 1.0,
                "units": "count",
                "metadata": metrics_metadata,
            },
            {
                "metric_name": f"{stage}.success",
                "metric_value": 1.0 if result.success else 0.0,
                "units": "boolean",
                "metadata": metrics_metadata,
            },
            {
                "metric_name": f"{stage}.duration_ms",
                "metric_value": float(duration_ms),
                "units": "ms",
                "metadata": metrics_metadata,
            },
        ]

        if not result.success:
            metric_entries.append(
                {
                    "metric_name": f"{stage}.error",
                    "metric_value": 1.0,
                    "units": "count",
                    "metadata": metrics_metadata,
                }
            )

        if governance_blocked:
            metric_entries.append(
                {
                    "metric_name": f"{stage}.governance_blocked",
                    "metric_value": 1.0,
                    "units": "count",
                    "metadata": metrics_metadata,
                }
            )

        if "chunk_count" in result.data:
            metric_entries.append(
                {
                    "metric_name": f"{stage}.chunk_count",
                    "metric_value": float(result.data.get("chunk_count") or 0),
                    "units": "count",
                    "metadata": metrics_metadata,
                }
            )

        self._persist_identity_trace(
            relational_backend,
            aktenzeichen=aktenzeichen,
            stage=stage,
            status=status,
            details=trace_details,
        )
        self._persist_identity_metrics(
            relational_backend,
            aktenzeichen=aktenzeichen,
            metrics=metric_entries,
        )

    # ------------------------------------------------------------------
    # Saga Event Helper
    # ------------------------------------------------------------------
    def write_saga_event(self, saga_id: str, step_name: str, status: str, payload: Dict[str, Any], error: Optional[str] = None) -> None:
        """Atomar: Schreibe oder aktualisiere ein Saga-Event in `uds3_saga_events`.

        status: PENDING|SUCCESS|FAIL|COMPENSATED
        """
        manager = self._get_manager()
        relational = self._get_relational_backend(manager)
        if relational is None:
            logger.debug("Kein relationaler Backend vorhanden, Saga-Event nicht geschrieben")
            return

        if db_migrations is not None:
            readiness_flag = "_uds3_saga_schema_ready"
            if not getattr(relational, readiness_flag, False):
                try:
                    db_migrations.ensure_saga_schema(relational)
                    setattr(relational, readiness_flag, True)
                except Exception as exc:  # pragma: no cover - migrations best-effort
                    logger.debug("ensure_saga_schema fehlgeschlagen: %s", exc)

        event = {
            'event_id': str(uuid.uuid4()),
            'saga_id': saga_id,
            'trace_id': None,
            'step_name': step_name,
            'event_type': 'step',
            'status': status,
            'duration_ms': None,
            'payload': json.dumps(payload, ensure_ascii=False, default=str),
            'created_at': None,
        }

        # Extract idempotency key if present in payload (common field)
        idempotency_key = None
        if isinstance(payload, dict):
            idempotency_key = payload.get('idempotency_key') or payload.get('idempotency')

        if idempotency_key is not None:
            # include explicitly so _safe_insert can map to a dedicated column if present
            event['idempotency_key'] = idempotency_key


        def _safe_insert(table: str, record: Dict[str, Any]) -> bool:
            """Insert helper that inserts only columns present in the relational table schema.

            Falls Tabelle nur ein 'data' JSON-Feld hat, nutzt `insert_record` falls verfügbar.
            """
            try:
                cols = None
                if hasattr(relational, 'get_table_schema'):
                    schema = relational.get_table_schema(table)
                    cols = list(schema.keys()) if isinstance(schema, dict) else None
                else:
                    # Fallback: try PRAGMA (SQLite)
                    try:
                        rows = relational.execute_query(f"PRAGMA table_info({table})")
                        cols = [r['name'] for r in rows]
                    except Exception:
                        cols = None

                # If the table has a single 'data' column and insert_record exists, use it
                if cols and cols == ['data'] and hasattr(relational, 'insert_record'):
                    return relational.insert_record(table, record)

                # Prepare insert using only matching columns
                if cols:
                    insert_keys = [k for k in record.keys() if k in cols]
                    # If the table has an idempotency_key column, ensure we include it if available
                    if 'idempotency_key' in cols and idempotency_key is not None and 'idempotency_key' not in record:
                        record['idempotency_key'] = idempotency_key
                    if not insert_keys and hasattr(relational, 'insert_record'):
                        return relational.insert_record(table, record)
                    if not insert_keys:
                        # No overlapping columns; as last resort, try insert_record
                        if hasattr(relational, 'insert_record'):
                            return relational.insert_record(table, record)
                        return False

                    values = tuple(record[k] for k in insert_keys)
                    placeholders = ', '.join(['?' for _ in insert_keys])
                    col_list = ', '.join(insert_keys)
                    relational.execute_query(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})", values)
                    return True

                # No schema info: fallback to insert_record or generic insert
                if hasattr(relational, 'insert_record'):
                    return relational.insert_record(table, record)
                if hasattr(relational, 'insert'):
                    # Be careful: relational.insert may expect 'id' column; avoid adding it
                    try:
                        relational.insert(table, record)
                        return True
                    except Exception:
                        return False
                # As final fallback, try execute_query with provided keys
                cols = list(record.keys())
                placeholders = ', '.join(['?' for _ in cols])
                relational.execute_query(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", tuple(record.values()))
                return True
            except Exception as exc:
                logger.debug("_safe_insert failed for %s: %s", table, exc)
                return False

        # perform event insert
        success_event = _safe_insert('uds3_saga_events', event)
        if status in ('SUCCESS', 'FAIL', 'COMPENSATED'):
            audit = {
                'audit_id': str(uuid.uuid4()),
                'saga_id': saga_id,
                'saga_name': None,
                'trace_id': None,
                'identity_key': None,
                'document_id': payload.get('document_id') if isinstance(payload, dict) else None,
                'step_name': step_name,
                'event_type': 'step_result',
                'status': status,
                'duration_ms': None,
                'details': json.dumps({'error': error} if error else {}, ensure_ascii=False, default=str),
                'actor': None,
                'created_at': None,
            }
            success_audit = _safe_insert('uds3_audit_log', audit)
            if not success_audit:
                logger.debug("Audit insert failed for saga %s step %s", saga_id, step_name)

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    def _get_manager(self) -> DatabaseManager:
        if self._manager is not None:
            return self._manager
        if self._manager_getter is not None:
            self._manager = self._manager_getter()
            return self._manager
        if self._fallback_manager is None:
            backend_dict = config.get_database_backend_dict()
            self._fallback_manager = DatabaseManager(backend_dict)
        return self._fallback_manager

    def _backend_unavailable(self, backend_name: str, document_id: Optional[str] = None) -> CrudResult:
        message = f"{backend_name} backend ist nicht konfiguriert oder nicht verfügbar"
        data: Dict[str, Any] = {"backend": backend_name}
        if document_id:
            data["document_id"] = document_id
        return CrudResult(False, data, message)

    def _is_available(self, backend: Any) -> bool:
        try:
            return bool(getattr(backend, "is_available", lambda: True)())
        except Exception:  # pragma: no cover - defensiv
            return False

    # ------------------------------------------------------------------
    # Vector Backend (z.\u202fB. ChromaDB)
    # ------------------------------------------------------------------
    def vector_create(
        self,
        document_id: str,
        chunks: Sequence[str],
        metadata: Optional[Dict[str, Any]] = None,
        *,
        collection: str = "document_chunks",
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        observability_payload: Dict[str, Any] = {
            "document_id": document_id,
            "collection": collection,
            "metadata": dict(metadata or {}),
            "chunks": list(chunks or []),
        }
        backend = getattr(manager, "get_vector_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("vector", document_id)
            self._record_identity_observability(manager, "vector", "create", start_time, observability_payload, result)
            return result

        meta_template = dict(metadata or {})
        documents = list(chunks or [])
        observability_payload["chunk_count"] = len(documents)
        if not documents:
            result = CrudResult(
                False,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": [],
                    "chunk_count": 0,
                },
                "Keine Chunks für Vector-Create übergeben",
            )
            self._record_identity_observability(manager, "vector", "create", start_time, observability_payload, result)
            return result

        failure_payload = {
            "document_id": document_id,
            "collection": collection,
            "chunk_ids": [],
            "chunk_count": len(documents),
        }
        enforcement_result = self._enforce_governance(
            manager,
            "vector",
            "create",
            {"chunks": documents, "metadata": meta_template},
            failure_payload,
        )
        if enforcement_result is not None:
            self._record_identity_observability(manager, "vector", "create", start_time, observability_payload, enforcement_result)
            return enforcement_result

        if hasattr(backend, "create_collection"):
            try:
                backend.create_collection(collection, metadata={"created_by": "uds3_saga"})
            except Exception as exc:  # pragma: no cover - Logging & Weiter
                logger.debug("Vector-Collection konnte nicht erstellt werden: %s", exc)

        chunk_ids: List[str] = [f"{document_id}::chunk::{index}" for index in range(len(documents))]
        metadatas: List[Dict[str, Any]] = []
        for index in range(len(documents)):
            chunk_meta = dict(meta_template)
            chunk_meta.setdefault("document_id", document_id)
            chunk_meta["chunk_index"] = index
            metadatas.append(chunk_meta)

        success = False
        error: Optional[str] = None
        try:
            if hasattr(backend, "add_documents"):
                success = bool(
                    backend.add_documents(
                        collection_name=collection,
                        documents=documents,
                        metadatas=metadatas,
                        ids=chunk_ids,
                    )
                )
            elif hasattr(backend, "add_chunk_with_strategy"):
                success = True
                for index, chunk in enumerate(documents):
                    if not backend.add_chunk_with_strategy(
                        collection_name=collection,
                        document_id=document_id,
                        chunk_index=index,
                        content=chunk,
                        metadata=meta_template,
                    ):
                        success = False
                        break
            else:
                error = "Vector-Backend unterstützt keine Dokument-Insert-Funktion"
        except Exception as exc:  # pragma: no cover - Laufzeitfehler auffangen
            success = False
            error = str(exc)

        data = {
            "document_id": document_id,
            "collection": collection,
            "chunk_ids": chunk_ids,
            "chunk_count": len(chunk_ids),
        }
        if not success and error is None:
            error = "Vector-Backend hat die Einfügung verweigert"
        observability_payload["chunk_ids"] = chunk_ids
        result = CrudResult(success, data, error)
        self._record_identity_observability(manager, "vector", "create", start_time, observability_payload, result)
        return result

    def vector_read(
        self,
        document_id: str,
        *,
        collection: str = "document_chunks",
        chunk_ids: Optional[Iterable[str]] = None,
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        backend = getattr(manager, "get_vector_backend", lambda: None)()
        if not backend or not self._is_available(backend) or not hasattr(backend, "get_collection"):
            result = self._backend_unavailable("vector", document_id)
            self._record_identity_observability(
                manager,
                "vector",
                "read",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": list(chunk_ids) if chunk_ids else None,
                },
                result,
            )
            return result
        chunk_id_list = list(chunk_ids) if chunk_ids else None
        enforcement_result = self._enforce_governance(
            manager,
            "vector",
            "read",
            {"document_id": document_id, "chunk_ids": chunk_id_list},
            {"document_id": document_id, "collection": collection},
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "vector",
                "read",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": chunk_id_list,
                },
                enforcement_result,
            )
            return enforcement_result

        collection_ref = backend.get_collection(collection)
        if not collection_ref:
            result = CrudResult(False, {"document_id": document_id, "collection": collection}, "Collection nicht gefunden")
            self._record_identity_observability(
                manager,
                "vector",
                "read",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": chunk_id_list,
                },
                result,
            )
            return result

        try:
            result = None
            if chunk_id_list:
                result = collection_ref.get(ids=chunk_id_list)
            else:
                result = collection_ref.get(where={"document_id": document_id})
        except Exception as exc:
            obs_payload = {
                "document_id": document_id,
                "collection": collection,
                "chunk_ids": chunk_id_list,
            }
            crud_result = CrudResult(False, {"document_id": document_id, "collection": collection}, str(exc))
            self._record_identity_observability(
                manager,
                "vector",
                "read",
                start_time,
                obs_payload,
                crud_result,
            )
            return crud_result

        def _flatten(value: Any) -> Any:
            if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
                return value[0]
            return value

        payload = {
            "document_id": document_id,
            "collection": collection,
            "ids": _flatten(result.get("ids", [])) if result else [],
            "documents": _flatten(result.get("documents", [])) if result else [],
            "metadatas": _flatten(result.get("metadatas", [])) if result else [],
        }
        success = bool(payload["ids"])
        if not success:
            crud_result = CrudResult(False, payload, "Keine passenden Vector-Einträge gefunden")
            self._record_identity_observability(
                manager,
                "vector",
                "read",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": chunk_id_list,
                },
                crud_result,
            )
            return crud_result
        success_result = CrudResult(True, payload)
        self._record_identity_observability(
            manager,
            "vector",
            "read",
            start_time,
            {
                "document_id": document_id,
                "collection": collection,
                "chunk_ids": chunk_id_list,
            },
            success_result,
        )
        return success_result

    def vector_update(
        self,
        document_id: str,
        chunks: Sequence[str],
        metadata: Optional[Dict[str, Any]] = None,
        *,
        collection: str = "document_chunks",
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        payload = {"chunks": list(chunks or []), "metadata": dict(metadata or {})}
        failure_payload = {
            "document_id": document_id,
            "collection": collection,
            "chunk_count": len(payload["chunks"]),
        }
        enforcement_result = self._enforce_governance(manager, "vector", "update", payload, failure_payload)
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "vector",
                "update",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunks": list(chunks or []),
                    "metadata": dict(metadata or {}),
                },
                enforcement_result,
            )
            return enforcement_result
        delete_result = self.vector_delete(document_id, collection=collection)
        if not delete_result.success:
            logger.debug("Vector-Update: Löschen bestehender Daten schlug fehl: %s", delete_result.error)
        create_result = self.vector_create(document_id, chunks, metadata, collection=collection)
        self._record_identity_observability(
            manager,
            "vector",
            "update",
            start_time,
            {
                "document_id": document_id,
                "collection": collection,
                "chunks": list(chunks or []),
                "metadata": dict(metadata or {}),
            },
            create_result,
        )
        return create_result

    def vector_delete(
        self,
        document_id: str,
        *,
        collection: str = "document_chunks",
        chunk_ids: Optional[Iterable[str]] = None,
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        chunk_id_list = list(chunk_ids) if chunk_ids else None
        failure_payload = {
            "document_id": document_id,
            "collection": collection,
            "deleted_chunk_ids": chunk_id_list,
        }
        enforcement_result = self._enforce_governance(
            manager,
            "vector",
            "delete",
            {"chunk_ids": chunk_id_list},
            failure_payload,
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "vector",
                "delete",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": chunk_id_list,
                },
                enforcement_result,
            )
            return enforcement_result
        backend = getattr(manager, "get_vector_backend", lambda: None)()
        if not backend or not self._is_available(backend) or not hasattr(backend, "get_collection"):
            result = self._backend_unavailable("vector", document_id)
            self._record_identity_observability(
                manager,
                "vector",
                "delete",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": chunk_id_list,
                },
                result,
            )
            return result

        collection_ref = backend.get_collection(collection)
        if not collection_ref:
            result = CrudResult(True, {"document_id": document_id, "collection": collection, "deleted_chunk_ids": []})
            self._record_identity_observability(
                manager,
                "vector",
                "delete",
                start_time,
                {
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_ids": chunk_id_list,
                },
                result,
            )
            return result

        ids_list = chunk_id_list
        try:
            if ids_list:
                collection_ref.delete(ids=ids_list)
            else:
                collection_ref.delete(where={"document_id": document_id})
            success = True
            error = None
        except Exception as exc:
            success = False
            error = str(exc)

        data = {
            "document_id": document_id,
            "collection": collection,
            "deleted_chunk_ids": ids_list,
        }
        result = CrudResult(success, data, error)
        self._record_identity_observability(
            manager,
            "vector",
            "delete",
            start_time,
            {
                "document_id": document_id,
                "collection": collection,
                "chunk_ids": chunk_id_list,
            },
            result,
        )
        return result

    # ------------------------------------------------------------------
    # Graph Backend (z.\u202fB. Neo4j)
    # ------------------------------------------------------------------
    def graph_create(
        self,
        document_id: str,
        properties: Optional[Dict[str, Any]] = None,
        *,
        label: str = "Document",
        merge_key: str = "id",
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        observability_payload = {
            "document_id": document_id,
            "label": label,
            "properties": dict(properties or {}),
        }
        backend = getattr(manager, "get_graph_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("graph", document_id)
            self._record_identity_observability(
                manager,
                "graph",
                "create",
                start_time,
                observability_payload,
                result,
            )
            return result

        node_properties = dict(properties or {})
        node_properties.setdefault(merge_key, document_id)
        failure_payload = {
            "document_id": document_id,
            "label": label,
        }
        enforcement_result = self._enforce_governance(
            manager,
            "graph",
            "create",
            node_properties,
            failure_payload,
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "graph",
                "create",
                start_time,
                observability_payload,
                enforcement_result,
            )
            return enforcement_result
        try:
            node_identifier = backend.create_node(label, node_properties, merge_key=merge_key)
        except Exception as exc:
            result = CrudResult(False, {"document_id": document_id, "label": label}, str(exc))
            self._record_identity_observability(
                manager,
                "graph",
                "create",
                start_time,
                observability_payload,
                result,
            )
            return result

        if not node_identifier:
            result = CrudResult(
                False,
                {"document_id": document_id, "label": label},
                "Graph-Knoten konnte nicht erstellt werden",
            )
            self._record_identity_observability(
                manager,
                "graph",
                "create",
                start_time,
                observability_payload,
                result,
            )
            return result

        relationships_created: List[Dict[str, Any]] = []
        for relation in node_properties.pop("relationships", []) or []:
            try:
                rel_type = relation.get("type")
                target = relation.get("target")
                rel_props = relation.get("properties", {}) or {}
                if rel_type and target and hasattr(backend, "create_edge"):
                    backend.create_edge(node_identifier, target, rel_type, rel_props)
                    relationships_created.append({"type": rel_type, "target": target})
            except Exception as exc:  # pragma: no cover - Fehler protokollieren
                logger.warning("Graph-Relationship konnte nicht erstellt werden: %s", exc)

        data = {
            "document_id": document_id,
            "label": label,
            "graph_id": node_identifier,
            "relationships": relationships_created,
        }
        result = CrudResult(True, data)
        self._record_identity_observability(
            manager,
            "graph",
            "create",
            start_time,
            observability_payload,
            result,
        )
        return result

    def graph_read(self, identifier: str) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        backend = getattr(manager, "get_graph_backend", lambda: None)()
        observability_payload = {"identifier": identifier}
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("graph")
            self._record_identity_observability(manager, "graph", "read", start_time, observability_payload, result)
            return result
        if not hasattr(backend, "get_node"):
            result = CrudResult(False, {"identifier": identifier}, "Graph-Backend unterstützt keine Read-Operation")
            self._record_identity_observability(manager, "graph", "read", start_time, observability_payload, result)
            return result
        try:
            node = backend.get_node(identifier)
        except Exception as exc:
            result = CrudResult(False, {"identifier": identifier}, str(exc))
            self._record_identity_observability(manager, "graph", "read", start_time, observability_payload, result)
            return result
        if not node:
            result = CrudResult(False, {"identifier": identifier}, "Graph-Knoten nicht gefunden")
            self._record_identity_observability(manager, "graph", "read", start_time, observability_payload, result)
            return result
        result = CrudResult(True, {"identifier": identifier, "node": node})
        self._record_identity_observability(manager, "graph", "read", start_time, observability_payload, result)
        return result

    def graph_update(
        self,
        identifier: str,
        updates: Dict[str, Any],
        *,
        label: str = "Document",
        merge_key: str = "id",
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        observability_payload = {
            "identifier": identifier,
            "updates": dict(updates or {}),
            "label": label,
        }
        backend = getattr(manager, "get_graph_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("graph")
            self._record_identity_observability(manager, "graph", "update", start_time, observability_payload, result)
            return result

        props = dict(updates or {})
        props.setdefault(merge_key, identifier.split("::")[-1] if "::" in identifier else identifier)
        enforcement_result = self._enforce_governance(
            manager,
            "graph",
            "update",
            props,
            {"identifier": identifier, "updates": updates},
        )
        if enforcement_result is not None:
            self._record_identity_observability(manager, "graph", "update", start_time, observability_payload, enforcement_result)
            return enforcement_result
        try:
            node_identifier = backend.create_node(label, props, merge_key=merge_key)
        except Exception as exc:
            result = CrudResult(False, {"identifier": identifier}, str(exc))
            self._record_identity_observability(manager, "graph", "update", start_time, observability_payload, result)
            return result
        if not node_identifier:
            result = CrudResult(False, {"identifier": identifier}, "Graph-Update fehlgeschlagen")
            self._record_identity_observability(manager, "graph", "update", start_time, observability_payload, result)
            return result
        result = CrudResult(True, {"identifier": node_identifier, "updates": updates})
        self._record_identity_observability(manager, "graph", "update", start_time, observability_payload, result)
        return result

    def graph_delete(self, identifier: str) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        backend = getattr(manager, "get_graph_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("graph")
            self._record_identity_observability(
                manager,
                "graph",
                "delete",
                start_time,
                {"identifier": identifier},
                result,
            )
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "graph",
            "delete",
            {"identifier": identifier},
            {"identifier": identifier},
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "graph",
                "delete",
                start_time,
                {"identifier": identifier},
                enforcement_result,
            )
            return enforcement_result
        try:
            success = backend.delete_node(identifier)
        except Exception as exc:
            result = CrudResult(False, {"identifier": identifier}, str(exc))
            self._record_identity_observability(
                manager,
                "graph",
                "delete",
                start_time,
                {"identifier": identifier},
                result,
            )
            return result
        result = CrudResult(success, {"identifier": identifier})
        self._record_identity_observability(
            manager,
            "graph",
            "delete",
            start_time,
            {"identifier": identifier},
            result,
        )
        return result

    # ------------------------------------------------------------------
    # Relationale Backends (z.\u202fB. SQLite/PostgreSQL)
    # ------------------------------------------------------------------
    def relational_create(self, record: Dict[str, Any]) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        observability_payload = dict(record or {})
        backend = getattr(manager, "get_relational_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("relational", record.get("document_id"))
            self._record_identity_observability(manager, "relational", "create", start_time, observability_payload, result)
            return result

        payload = dict(record)
        enforcement_result = self._enforce_governance(
            manager,
            "relational",
            "create",
            payload,
            payload,
        )
        if enforcement_result is not None:
            self._record_identity_observability(manager, "relational", "create", start_time, observability_payload, enforcement_result)
            return enforcement_result
        try:
            document_id = backend.upsert_documents_metadata(payload)
        except AttributeError:
            # Fallback für generische Insert-Funktion
            try:
                document_id = backend.insert("documents_metadata", payload)
            except Exception as exc:  # pragma: no cover - Fallback
                result = CrudResult(False, payload, str(exc))
                self._record_identity_observability(manager, "relational", "create", start_time, observability_payload, result)
                return result
        except Exception as exc:
            result = CrudResult(False, payload, str(exc))
            self._record_identity_observability(manager, "relational", "create", start_time, observability_payload, result)
            return result

        if not document_id:
            result = CrudResult(False, payload, "Relationale Einfügung fehlgeschlagen")
            self._record_identity_observability(manager, "relational", "create", start_time, observability_payload, result)
            return result

        data = dict(payload)
        data["document_id"] = document_id
        result = CrudResult(True, data)
        observability_payload["document_id"] = document_id or observability_payload.get("document_id")
        self._record_identity_observability(manager, "relational", "create", start_time, observability_payload, result)
        return result

    def relational_read(self, document_id: str) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        backend = getattr(manager, "get_relational_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("relational", document_id)
            self._record_identity_observability(
                manager,
                "relational",
                "read",
                start_time,
                {"document_id": document_id},
                result,
            )
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "relational",
            "read",
            {"document_id": document_id},
            {"document_id": document_id},
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "relational",
                "read",
                start_time,
                {"document_id": document_id},
                enforcement_result,
            )
            return enforcement_result
        try:
            rows = backend.select("documents_metadata", {"document_id": document_id})
        except Exception as exc:
            result = CrudResult(False, {"document_id": document_id}, str(exc))
            self._record_identity_observability(
                manager,
                "relational",
                "read",
                start_time,
                {"document_id": document_id},
                result,
            )
            return result
        if not rows:
            result = CrudResult(False, {"document_id": document_id}, "Kein Datensatz gefunden")
            self._record_identity_observability(
                manager,
                "relational",
                "read",
                start_time,
                {"document_id": document_id},
                result,
            )
            return result
        result = CrudResult(True, {"document_id": document_id, "records": rows})
        self._record_identity_observability(
            manager,
            "relational",
            "read",
            start_time,
            {"document_id": document_id},
            result,
        )
        return result

    def relational_update(self, document_id: str, updates: Dict[str, Any]) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        observability_payload = {"document_id": document_id, "updates": dict(updates or {})}
        backend = getattr(manager, "get_relational_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("relational", document_id)
            self._record_identity_observability(manager, "relational", "update", start_time, observability_payload, result)
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "relational",
            "update",
            dict(updates or {}),
            {"document_id": document_id, "updates": updates},
        )
        if enforcement_result is not None:
            self._record_identity_observability(manager, "relational", "update", start_time, observability_payload, enforcement_result)
            return enforcement_result
        try:
            success = backend.update("documents_metadata", updates, {"document_id": document_id})
        except Exception as exc:
            result = CrudResult(False, {"document_id": document_id, "updates": updates}, str(exc))
            self._record_identity_observability(manager, "relational", "update", start_time, observability_payload, result)
            return result
        result = CrudResult(success, {"document_id": document_id, "updates": updates})
        self._record_identity_observability(manager, "relational", "update", start_time, observability_payload, result)
        return result

    def relational_delete(self, document_id: str) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        backend = getattr(manager, "get_relational_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("relational", document_id)
            self._record_identity_observability(
                manager,
                "relational",
                "delete",
                start_time,
                {"document_id": document_id},
                result,
            )
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "relational",
            "delete",
            {"document_id": document_id},
            {"document_id": document_id},
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "relational",
                "delete",
                start_time,
                {"document_id": document_id},
                enforcement_result,
            )
            return enforcement_result
        try:
            success = backend.delete("documents_metadata", {"document_id": document_id})
        except Exception as exc:
            result = CrudResult(False, {"document_id": document_id}, str(exc))
            self._record_identity_observability(
                manager,
                "relational",
                "delete",
                start_time,
                {"document_id": document_id},
                result,
            )
            return result
        result = CrudResult(success, {"document_id": document_id})
        self._record_identity_observability(
            manager,
            "relational",
            "delete",
            start_time,
            {"document_id": document_id},
            result,
        )
        return result

    # ------------------------------------------------------------------
    # File Storage Backend
    # ------------------------------------------------------------------
    def file_create(
        self,
        document_id: str,
        *,
        source_path: Optional[str] = None,
        data: Optional[bytes] = None,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        observability_payload = {
            "document_id": document_id,
            "source_path": source_path,
            "filename": filename,
            "metadata": dict(metadata or {}),
        }
        backend = getattr(manager, "get_file_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("file", document_id)
            self._record_identity_observability(manager, "file", "create", start_time, observability_payload, result)
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "file",
            "create",
            {
                "document_id": document_id,
                "source_path": source_path,
                "filename": filename,
                "metadata": metadata,
            },
            {"document_id": document_id},
        )
        if enforcement_result is not None:
            self._record_identity_observability(manager, "file", "create", start_time, observability_payload, enforcement_result)
            return enforcement_result
        try:
            info = backend.store_asset(
                source_path=source_path,
                data=data,
                filename=filename,
                metadata={"document_id": document_id, **(metadata or {})},
            )
        except Exception as exc:
            result = CrudResult(False, {"document_id": document_id}, str(exc))
            self._record_identity_observability(manager, "file", "create", start_time, observability_payload, result)
            return result
        payload = dict(info)
        payload["document_id"] = document_id
        result = CrudResult(True, payload)
        self._record_identity_observability(manager, "file", "create", start_time, observability_payload, result)
        return result

    def file_read(self, asset_id: str) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        backend = getattr(manager, "get_file_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("file")
            self._record_identity_observability(
                manager,
                "file",
                "read",
                start_time,
                {"asset_id": asset_id},
                result,
            )
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "file",
            "read",
            {"asset_id": asset_id},
            {"asset_id": asset_id},
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "file",
                "read",
                start_time,
                {"asset_id": asset_id},
                enforcement_result,
            )
            return enforcement_result
        search_pattern = os.path.join(getattr(backend, "root_path", ""), "**", f"{asset_id}*")
        matches = glob.glob(search_pattern, recursive=True)
        if not matches:
            result = CrudResult(False, {"asset_id": asset_id}, "Asset nicht gefunden")
            self._record_identity_observability(
                manager,
                "file",
                "read",
                start_time,
                {"asset_id": asset_id},
                result,
            )
            return result
        path = matches[0]
        try:
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
        except OSError as exc:
            result = CrudResult(False, {"asset_id": asset_id}, str(exc))
            self._record_identity_observability(
                manager,
                "file",
                "read",
                start_time,
                {"asset_id": asset_id},
                result,
            )
            return result
        result = CrudResult(
            True,
            {
                "asset_id": asset_id,
                "path": path,
                "size": size,
                "modified_at": mtime,
            },
        )
        self._record_identity_observability(
            manager,
            "file",
            "read",
            start_time,
            {"asset_id": asset_id},
            result,
        )
        return result

    def file_update(
        self,
        asset_id: str,
        *,
        data: Optional[bytes] = None,
        source_path: Optional[str] = None,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        observability_payload = {
            "asset_id": asset_id,
            "source_path": source_path,
            "filename": filename,
            "metadata": dict(metadata or {}),
        }
        backend = getattr(manager, "get_file_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("file")
            self._record_identity_observability(manager, "file", "update", start_time, observability_payload, result)
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "file",
            "update",
            {
                "asset_id": asset_id,
                "source_path": source_path,
                "filename": filename,
                "metadata": metadata,
            },
            {"asset_id": asset_id},
        )
        if enforcement_result is not None:
            self._record_identity_observability(manager, "file", "update", start_time, observability_payload, enforcement_result)
            return enforcement_result
        try:
            info = backend.store_asset(
                source_path=source_path,
                data=data,
                filename=filename,
                metadata=metadata,
                content_hash=asset_id,
            )
        except Exception as exc:
            result = CrudResult(False, {"asset_id": asset_id}, str(exc))
            self._record_identity_observability(manager, "file", "update", start_time, observability_payload, result)
            return result
        payload = dict(info)
        payload["asset_id"] = asset_id
        result = CrudResult(True, payload)
        self._record_identity_observability(manager, "file", "update", start_time, observability_payload, result)
        return result

    def file_delete(self, asset_id: str) -> CrudResult:
        manager = self._get_manager()
        start_time = time.perf_counter()
        backend = getattr(manager, "get_file_backend", lambda: None)()
        if not backend or not self._is_available(backend):
            result = self._backend_unavailable("file")
            self._record_identity_observability(
                manager,
                "file",
                "delete",
                start_time,
                {"asset_id": asset_id},
                result,
            )
            return result
        enforcement_result = self._enforce_governance(
            manager,
            "file",
            "delete",
            {"asset_id": asset_id},
            {"asset_id": asset_id},
        )
        if enforcement_result is not None:
            self._record_identity_observability(
                manager,
                "file",
                "delete",
                start_time,
                {"asset_id": asset_id},
                enforcement_result,
            )
            return enforcement_result
        search_pattern = os.path.join(getattr(backend, "root_path", ""), "**", f"{asset_id}*")
        matches = glob.glob(search_pattern, recursive=True)
        deleted: List[str] = []
        errors: List[str] = []
        for path in matches:
            try:
                os.remove(path)
                deleted.append(path)
            except OSError as exc:
                errors.append(str(exc))
        success = not errors
        error = ", ".join(errors) if errors else None
        result = CrudResult(success, {"asset_id": asset_id, "deleted_paths": deleted}, error)
        self._record_identity_observability(
            manager,
            "file",
            "delete",
            start_time,
            {"asset_id": asset_id},
            result,
        )
        return result


__all__ = ["CrudResult", "SagaDatabaseCRUD"]
