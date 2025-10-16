#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Saga Step Builders - Extracted from uds3_core.py
======================================================
OPTIMIZED (1. Oktober 2025): Saga Step Builder Logik aus uds3_core.py extrahiert

EXTRACTION: Lines 1253-2660 aus uds3_core.py (~1400 LOC)
PURPOSE: Reduziere uds3_core.py von 4097 LOC auf <3000 LOC

Dieses Modul enthält die Saga Step Builder-Methoden:
- _build_create_document_step_specs()
- _build_update_document_step_specs()
- _build_delete_document_step_specs()

Pattern: Mixin-Class für saubere Integration in UnifiedDatabaseStrategy
"""

import logging
import hashlib
import uuid
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Conditional imports für optionale Features
try:
    from database.security_quality import SecurityLevel
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    SecurityLevel = None  # type: ignore

try:
    from uds3_identity_service import IdentityServiceError
    IDENTITY_SERVICE_AVAILABLE = True
except ImportError:
    IDENTITY_SERVICE_AVAILABLE = False
    IdentityServiceError = Exception  # type: ignore

try:
    from uds3_saga_orchestrator import SagaExecutionError
    SAGA_AVAILABLE = True
except ImportError:
    SAGA_AVAILABLE = True
    # Fallback Definition
    class SagaExecutionError(Exception):  # type: ignore
        """Saga Execution Error Fallback"""
        pass


class UDS3SagaStepBuildersMixin:
    """
    Mixin für Saga Step Builder-Methoden
    
    Wird in UnifiedDatabaseStrategy gemischt für saubere Modularisierung.
    Alle Methoden erwarten Zugriff auf self (UnifiedDatabaseStrategy Instanz).
    """
    
    # Diese Methoden werden aus uds3_core.py hier verschoben
    # Sie erwarten self.security_manager, self.quality_manager, self.identity_service, etc.
    
    def _build_create_document_step_specs(
        self, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Baut Saga Step Specs für Dokument-Erstellung
        
        EXTRAHIERT aus uds3_core.py (Lines 1253-1693)
        
        Args:
            context: Saga Execution Context mit create_result, metadata, etc.
        
        Returns:
            List[Dict]: Saga Step Specifications
        """
        create_result = context["create_result"]
        metadata = context["metadata"]

        def _mark_optional_skip(
            result_dict: Dict[str, Any], message: Optional[str]
        ) -> Dict[str, Any]:
            result_dict["success"] = True
            result_dict["skipped"] = True
            if message:
                result_dict.setdefault("warning", message)
                create_result["issues"].append(message)
            return result_dict

        def _is_optional_backend_error(message: Optional[str]) -> bool:
            if not message:
                return False
            lowered = message.lower()
            return any(
                phrase in lowered
                for phrase in [
                    "nicht konfiguriert",
                    "nicht verfügbar",
                    "not configured",
                    "not available",
                ]
            )

        def security_action(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            metadata_local = ctx["metadata"]
            file_path_local = ctx["file_path"]
            content_local = ctx["content"]
            security_lvl = ctx["security_level"]
            aktenzeichen = metadata_local.get("aktenzeichen")

            try:
                content_bytes = (content_local or "").encode("utf-8")
            except AttributeError:
                content_bytes = b""
            file_hash = hashlib.sha256(content_bytes).hexdigest()
            metadata_local.setdefault("file_hash", file_hash)
            metadata_local.setdefault("file_path", file_path_local)
            metadata_local.setdefault("file_size", len(content_bytes))

            identity_record = None
            document_uuid: Optional[str] = None
            document_id: Optional[str] = None

            if self.security_manager:
                security_info = self.security_manager.generate_secure_document_id(
                    content_local,
                    file_path_local,
                    security_lvl or (SecurityLevel.INTERNAL if SECURITY_AVAILABLE else None),
                )
                create_result["security_info"] = security_info or {}
                create_result["security_info"].setdefault("file_hash", file_hash)
                document_id = security_info.get("document_id")
                document_uuid = security_info.get("document_uuid")

                audit_entry = self.security_manager.create_audit_log_entry(
                    "CREATE_DOCUMENT",
                    document_id,
                    details={"file_path": file_path_local},
                )
                create_result["audit_entry"] = audit_entry

                if document_uuid is None and document_id:
                    document_uuid = self._infer_uuid_from_document_id(document_id)

                if self.identity_service and document_uuid:
                    try:
                        identity_record = self.identity_service.register_uuid(
                            uuid=document_uuid,
                            source_system="uds3.security",
                            aktenzeichen=aktenzeichen,
                            actor="uds3_core",
                        )
                    except IdentityServiceError as exc:
                        logger.warning(f"Identity Service registration failed: {exc}")
                elif self.identity_service:
                    identity_record = self.identity_service.generate_uuid(
                        source_system="uds3.security",
                        aktenzeichen=aktenzeichen,
                        actor="uds3_core",
                    )
                    document_uuid = identity_record.uuid
                    if not document_id:
                        document_id = self._format_document_id(document_uuid)
                    create_result.setdefault("security_info", {})["document_uuid"] = (
                        document_uuid
                    )
                    create_result["security_info"].setdefault(
                        "document_id", document_id
                    )
            else:
                if self.identity_service:
                    identity_record = self.identity_service.generate_uuid(
                        source_system="uds3.core",
                        aktenzeichen=aktenzeichen,
                        actor="uds3_core",
                    )
                    document_uuid = identity_record.uuid
                    document_id = self._format_document_id(document_uuid)
                    create_result["security_info"] = {
                        "document_id": document_id,
                        "document_uuid": document_uuid,
                        "file_hash": file_hash,
                    }
                else:
                    generated_uuid = uuid.uuid4()
                    document_uuid = str(generated_uuid)
                    document_id = f"doc_{generated_uuid.hex}"
                    create_result["security_info"] = {
                        "document_id": document_id,
                        "file_hash": file_hash,
                    }

            identity_key_candidate = metadata_local.get("aktenzeichen")
            if identity_record is not None:
                identity_key_candidate = (
                    getattr(identity_record, "identity_key", None)
                    or getattr(identity_record, "aktenzeichen", None)
                    or (
                        identity_record.get("identity_key")
                        if isinstance(identity_record, dict)
                        else None
                    )
                    or (
                        identity_record.get("aktenzeichen")
                        if isinstance(identity_record, dict)
                        else None
                    )
                    or getattr(identity_record, "uuid", None)
                    or (
                        identity_record.get("uuid")
                        if isinstance(identity_record, dict)
                        else None
                    )
                    or identity_key_candidate
                )
                ctx["identity_uuid"] = (
                    getattr(identity_record, "uuid", None)
                    or getattr(identity_record, "identity_uuid", None)
                    or (
                        identity_record.get("uuid")
                        if isinstance(identity_record, dict)
                        else None
                    )
                    or (
                        identity_record.get("identity_uuid")
                        if isinstance(identity_record, dict)
                        else None
                    )
                )

            if identity_key_candidate:
                ctx["identity_key"] = identity_key_candidate
                ctx["aktenzeichen"] = identity_key_candidate
                metadata_local.setdefault("aktenzeichen", identity_key_candidate)

            ctx["document_uuid"] = document_uuid
            ctx["document_id"] = document_id
            ctx["identity_record"] = identity_record
            ctx["document_data"] = {
                "document_id": document_id,
                "id": document_id,
                "uuid": document_uuid,
                "identity_key": ctx.get("identity_key") or identity_key_candidate,
                "title": metadata_local.get("title", os.path.basename(file_path_local)),
                "content": content_local,
                "file_path": file_path_local,
                "file_hash": metadata_local.get("file_hash", file_hash),
                "file_size": metadata_local.get("file_size"),
                "created_at": datetime.now().isoformat(),
                **metadata_local,
            }
            return None

        def security_compensation(ctx: Dict[str, Any]) -> None:
            ctx.setdefault("compensations", []).append("security_identity_reset")

        def vector_action(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            document_id = ctx["document_id"]
            result = self._execute_vector_create(
                document_id,
                ctx["content"],
                ctx["chunks"],
                ctx.get("metadata"),
            )
            if not result.get("success", False):
                error_message = result.get("error")
                if _is_optional_backend_error(error_message):
                    _mark_optional_skip(result, error_message)
                else:
                    raise SagaExecutionError(
                        error_message or "Vector Operation fehlgeschlagen"
                    )
            ctx["vector_result"] = result
            create_result["database_operations"]["vector"] = result
            return None

        def vector_compensation(ctx: Dict[str, Any]) -> None:
            vector_payload = ctx.get("vector_result") or {}
            if vector_payload.get("skipped"):
                return
            chunk_ids = vector_payload.get("chunk_ids")
            collection = vector_payload.get("collection", "document_chunks")
            document_id = ctx.get("document_id")
            if document_id:
                crud_result = self.saga_crud.vector_delete(
                    document_id,
                    collection=collection,
                    chunk_ids=chunk_ids,
                )
                if not crud_result.success and crud_result.error:
                    logger.error(f"Vector compensation failed: {crud_result.error}")

        def graph_action(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            document_id = ctx["document_id"]
            result = self._execute_graph_create(
                document_id, ctx["content"], ctx["metadata"]
            )
            if not result.get("success", False):
                error_message = result.get("error")
                if _is_optional_backend_error(error_message):
                    _mark_optional_skip(result, error_message)
                else:
                    raise SagaExecutionError(
                        error_message or "Graph Operation fehlgeschlagen"
                    )
            ctx["graph_result"] = result
            create_result["database_operations"]["graph"] = result
            return None

        def graph_compensation(ctx: Dict[str, Any]) -> None:
            graph_payload = ctx.get("graph_result") or {}
            if graph_payload.get("skipped"):
                return
            identifier = graph_payload.get("graph_id") or graph_payload.get("id")
            if identifier is None and ctx.get("document_id"):
                identifier = f"Document::{ctx['document_id']}"
            if identifier:
                crud_result = self.saga_crud.graph_delete(identifier)
                if not crud_result.success and crud_result.error:
                    logger.error(f"Graph compensation failed: {crud_result.error}")

        def relational_action(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            result = self._execute_relational_create(ctx["document_data"])
            ctx["relational_result"] = result
            create_result["database_operations"]["relational"] = result
            if not result.get("success", False):
                error_message = result.get("error")
                if _is_optional_backend_error(error_message):
                    _mark_optional_skip(result, error_message)
                raise SagaExecutionError(
                    error_message or "Relationale Operation fehlgeschlagen"
                )
            return None

        def relational_compensation(ctx: Dict[str, Any]) -> None:
            relational_payload = ctx.get("relational_result") or {}
            document_id = relational_payload.get("document_id") or ctx.get(
                "document_id"
            )
            if document_id:
                crud_result = self.saga_crud.relational_delete(document_id)
                if not crud_result.success and crud_result.error:
                    logger.error(f"Relational compensation failed: {crud_result.error}")

        def file_storage_action(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            result = self._execute_file_storage_create(
                ctx["document_id"],
                ctx["file_path"],
                ctx["metadata"],
                ctx.get("content"),
            )
            if not result.get("success", False):
                error_message = result.get("error")
                if _is_optional_backend_error(error_message):
                    _mark_optional_skip(result, error_message)
                else:
                    raise SagaExecutionError(
                        error_message or "File Storage Operation fehlgeschlagen"
                    )
            ctx["file_storage_result"] = result
            create_result["database_operations"]["file_storage"] = result
            return None

        def file_storage_compensation(ctx: Dict[str, Any]) -> None:
            payload = ctx.get("file_storage_result") or {}
            if payload.get("skipped"):
                return
            asset_id = payload.get("asset_id") or payload.get("file_storage_id")
            if asset_id:
                crud_result = self.saga_crud.file_delete(asset_id)
                if not crud_result.success and crud_result.error:
                    logger.error(f"File storage compensation failed: {crud_result.error}")

        def identity_binding_action(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not self.identity_service or not ctx.get("document_uuid"):
                return None
            try:
                vector_result = ctx.get("vector_result", {})
                graph_result = ctx.get("graph_result", {})
                relational_result = ctx.get("relational_result", {})
                file_storage_result = ctx.get("file_storage_result", {})

                self.identity_service.bind_database_ids(
                    uuid=ctx["document_uuid"],
                    relational_id=relational_result.get("document_id"),
                    graph_id=graph_result.get("graph_id") or graph_result.get("id"),
                    vector_id=vector_result.get("document_id"),
                    file_storage_id=file_storage_result.get("asset_id") if file_storage_result else None,
                    actor="uds3_core",
                )
            except IdentityServiceError as exc:
                logger.warning(f"Identity binding failed (non-critical): {exc}")
                create_result["issues"].append(f"Identity binding warning: {exc}")
            return None

        def validation_action(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            vector_result = ctx.get("vector_result", {})
            graph_result = ctx.get("graph_result", {})
            relational_result = ctx.get("relational_result", {})
            file_storage_result = ctx.get("file_storage_result")
            document_id = ctx.get("document_id")
            document_data = ctx.get("document_data", {})

            if self.quality_manager:
                quality_score = self.quality_manager.assess_document_quality(
                    document_data={
                        "content": ctx.get("content", ""),
                        "metadata": ctx.get("metadata", {}),
                        "file_hash": document_data.get("file_hash", ""),
                    }
                )
                create_result["quality_score"] = quality_score

            validation_result = self._validate_cross_db_consistency(
                document_id,
                vector_result,
                graph_result,
                relational_result,
                file_storage_result,
            )
            create_result["validation_results"] = validation_result

            if self.security_manager and create_result.get("security_info"):
                integrity_check = self.security_manager.verify_document_integrity(
                    document_id=document_id,
                    expected_hash=create_result["security_info"].get("file_hash"),
                )
                create_result["security_info"]["integrity_verified"] = integrity_check

            all_db_success = all(
                result.get("success", False) or result.get("skipped", False)
                for result in create_result["database_operations"].values()
            )
            validation_success = validation_result.get("overall_valid", True)
            create_result["success"] = all_db_success and validation_success

            if create_result["success"]:
                self.document_mapping[document_id] = {
                    "vector_id": vector_result.get("document_id") if not vector_result.get("skipped") else None,
                    "graph_id": graph_result.get("graph_id") or graph_result.get("id") if not graph_result.get("skipped") else None,
                    "relational_id": relational_result.get("document_id"),
                    "file_storage_id": file_storage_result.get("asset_id") if file_storage_result and not file_storage_result.get("skipped") else None,
                    "identity_key": ctx.get("identity_key"),
                    "uuid": ctx.get("document_uuid"),
                    "created_at": datetime.now().isoformat(),
                }
            return None

        return [
            {
                "name": "security_and_identity",
                "action": security_action,
                "compensation": security_compensation,
            },
            {
                "name": "vector_create",
                "action": vector_action,
                "compensation": vector_compensation,
            },
            {
                "name": "graph_create",
                "action": graph_action,
                "compensation": graph_compensation,
            },
            {
                "name": "relational_create",
                "action": relational_action,
                "compensation": relational_compensation,
            },
            {
                "name": "file_storage_create",
                "action": file_storage_action,
                "compensation": file_storage_compensation,
            },
            {
                "name": "identity_mapping",
                "action": identity_binding_action,
                "compensation": None,
            },
            {
                "name": "validation_and_finalize",
                "action": validation_action,
                "compensation": None,
            },
        ]
    
    def _build_update_document_step_specs(
        self, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Baut Saga Step Specs für Dokument-Update
        
        EXTRAHIERT aus uds3_core.py (Lines 1694-2251)
        
        NOTE: Implementierung wird hier fortgesetzt...
        Aus Platzgründen ist dies ein Platzhalter für die vollständige Methode.
        """
        # TODO: Vollständige Implementierung aus uds3_core.py kopieren
        # Diese Methode ist ~550 LOC lang
        raise NotImplementedError("_build_update_document_step_specs wird noch extrahiert")
    
    def _build_delete_document_step_specs(
        self, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Baut Saga Step Specs für Dokument-Löschung
        
        EXTRAHIERT aus uds3_core.py (Lines 2252-2660)
        
        NOTE: Implementierung wird hier fortgesetzt...
        Aus Platzgründen ist dies ein Platzhalter für die vollständige Methode.
        """
        # TODO: Vollständige Implementierung aus uds3_core.py kopieren
        # Diese Methode ist ~400 LOC lang
        raise NotImplementedError("_build_delete_document_step_specs wird noch extrahiert")


# Export
__all__ = ["UDS3SagaStepBuildersMixin"]
