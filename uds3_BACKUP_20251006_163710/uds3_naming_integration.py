#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Naming Strategy Integration

Integriert dynamische Namensgebung in die bestehende UDS3-Architektur.
Erweitert SagaDatabaseCRUD und UnifiedDatabaseStrategy um kontextbezogene Namensgebung.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

# Import Naming Strategy
from uds3_naming_strategy import (
    NamingStrategy,
    OrganizationContext,
    NamingConvention,
    create_municipal_strategy,
    create_state_strategy,
    create_federal_strategy,
)

# Import Admin Types
try:
    from uds3_admin_types import AdminDocumentType, AdminLevel, AdminDomain
except ImportError:
    from enum import Enum
    class AdminDocumentType(Enum):
        PERMIT = "genehmigung"
    class AdminLevel(Enum):
        MUNICIPAL = "kommune"
    class AdminDomain(Enum):
        BUILDING_LAW = "bau"


logger = logging.getLogger(__name__)


@dataclass
class NamingContext:
    """
    Kontext für dynamische Namensgebung während Dokumentverarbeitung.
    
    Wird aus Dokument-Metadata extrahiert und an NamingStrategy übergeben.
    """
    
    # Dokument-Kontext
    document_id: str
    document_type: Optional[AdminDocumentType] = None
    
    # Organisations-Kontext
    behoerde: Optional[str] = None  # z.B. "Bauamt Münster"
    abteilung: Optional[str] = None
    bundesland: Optional[str] = None
    kommune: Optional[str] = None
    
    # Rechtskontext
    rechtsgebiet: Optional[str] = None  # z.B. "Baurecht"
    rechtsnorm: Optional[str] = None    # z.B. "BauGB §34"
    
    # Processing-Kontext
    processing_stage: str = "active"  # "active", "archive", "draft"
    access_level: str = "internal"    # "public", "internal", "confidential"
    
    # Administrative Ebene
    admin_level: AdminLevel = AdminLevel.MUNICIPAL
    admin_domain: AdminDomain = AdminDomain.BUILDING_LAW
    
    def to_organization_context(self) -> OrganizationContext:
        """Konvertiert zu OrganizationContext für NamingStrategy"""
        return OrganizationContext(
            level=self.admin_level,
            state=self.bundesland,
            municipality=self.kommune,
            authority=self.behoerde,
            department=self.abteilung,
            domain=self.admin_domain,
            legal_areas=[self.rechtsgebiet] if self.rechtsgebiet else [],
        )
    
    @classmethod
    def from_metadata(cls, document_id: str, metadata: Dict[str, Any]) -> "NamingContext":
        """
        Erstellt NamingContext aus Dokument-Metadata.
        
        Args:
            document_id: Dokument-ID
            metadata: Metadata-Dict mit Feldern wie "behoerde", "rechtsgebiet", etc.
        
        Returns:
            NamingContext Instanz
        """
        # Extrahiere Organisations-Info
        behoerde = metadata.get("behoerde") or metadata.get("authority")
        abteilung = metadata.get("abteilung") or metadata.get("department")
        bundesland = metadata.get("bundesland") or metadata.get("state")
        kommune = metadata.get("kommune") or metadata.get("municipality")
        
        # Extrahiere Rechtskontext
        rechtsgebiet = metadata.get("rechtsgebiet") or metadata.get("legal_area")
        rechtsnorm = metadata.get("rechtsnorm") or metadata.get("legal_norm")
        
        # Dokument-Typ
        doc_type_str = metadata.get("document_type")
        document_type = None
        if doc_type_str:
            try:
                # Versuche String zu AdminDocumentType zu konvertieren
                document_type = AdminDocumentType[doc_type_str.upper()]
            except (KeyError, AttributeError):
                logger.warning(f"Unbekannter document_type: {doc_type_str}")
        
        # Admin Level ableiten
        admin_level = cls._infer_admin_level(bundesland, kommune, metadata)
        
        # Admin Domain ableiten
        admin_domain = cls._infer_admin_domain(behoerde, rechtsgebiet, metadata)
        
        return cls(
            document_id=document_id,
            document_type=document_type,
            behoerde=behoerde,
            abteilung=abteilung,
            bundesland=bundesland,
            kommune=kommune,
            rechtsgebiet=rechtsgebiet,
            rechtsnorm=rechtsnorm,
            processing_stage=metadata.get("processing_stage", "active"),
            access_level=metadata.get("access_level", "internal"),
            admin_level=admin_level,
            admin_domain=admin_domain,
        )
    
    @staticmethod
    def _infer_admin_level(bundesland: Optional[str], kommune: Optional[str], metadata: Dict) -> AdminLevel:
        """Leitet Administrative Ebene aus Kontext ab"""
        level_str = metadata.get("admin_level", "").lower()
        
        if level_str == "federal" or level_str == "bund":
            return AdminLevel.FEDERAL
        elif level_str == "state" or level_str == "land":
            return AdminLevel.STATE
        elif kommune:
            return AdminLevel.MUNICIPAL
        elif bundesland:
            return AdminLevel.STATE
        else:
            return AdminLevel.MUNICIPAL  # Default
    
    @staticmethod
    def _infer_admin_domain(behoerde: Optional[str], rechtsgebiet: Optional[str], metadata: Dict) -> AdminDomain:
        """Leitet Administrative Domain aus Kontext ab"""
        domain_str = metadata.get("admin_domain", "").lower()
        
        if domain_str:
            try:
                return AdminDomain[domain_str.upper()]
            except KeyError:
                pass
        
        # Fallback: Von Behörde oder Rechtsgebiet ableiten
        text = f"{behoerde or ''} {rechtsgebiet or ''}".lower()
        
        if "bau" in text or "bauamt" in text:
            return AdminDomain.BUILDING_LAW
        elif "umwelt" in text:
            return AdminDomain.ENVIRONMENTAL_LAW
        elif "plan" in text or "raumordnung" in text:
            return AdminDomain.PLANNING_LAW
        else:
            return AdminDomain.GENERAL_ADMIN


class NamingContextManager:
    """
    Verwaltet NamingStrategy-Instanzen und resolved Namen für verschiedene Kontexte.
    
    Singleton-Pattern: Eine Instanz pro UnifiedDatabaseStrategy.
    """
    
    def __init__(
        self,
        default_org_context: Optional[OrganizationContext] = None,
        naming_convention: NamingConvention = NamingConvention.SNAKE_CASE,
        global_prefix: str = "uds3",
        enable_caching: bool = True,
    ):
        """
        Args:
            default_org_context: Standard-Organisationskontext (fallback)
            naming_convention: Namenskonvention (snake_case, kebab-case, etc.)
            global_prefix: Globaler Präfix für alle Namen
            enable_caching: Caching von generierten Namen aktivieren
        """
        self.default_org_context = default_org_context or OrganizationContext(
            level=AdminLevel.MUNICIPAL,
            municipality="default",
            authority="verwaltung",
        )
        self.naming_convention = naming_convention
        self.global_prefix = global_prefix
        self.enable_caching = enable_caching
        
        # Cache: {org_context_hash: NamingStrategy}
        self._strategy_cache: Dict[str, NamingStrategy] = {}
        
        # Name-Cache: {(strategy_hash, method, args): name}
        self._name_cache: Dict[tuple, str] = {}
    
    def get_strategy_for_context(self, naming_context: NamingContext) -> NamingStrategy:
        """
        Erstellt oder cached NamingStrategy für gegebenen Kontext.
        
        Args:
            naming_context: Dokument-spezifischer Naming-Kontext
        
        Returns:
            NamingStrategy Instanz
        """
        org_context = naming_context.to_organization_context()
        
        # Cache-Key aus org_context erstellen
        cache_key = self._org_context_hash(org_context)
        
        if cache_key in self._strategy_cache:
            return self._strategy_cache[cache_key]
        
        # Neue Strategy erstellen
        strategy = NamingStrategy(
            org_context=org_context,
            convention=self.naming_convention,
            global_prefix=self.global_prefix,
        )
        
        if self.enable_caching:
            self._strategy_cache[cache_key] = strategy
        
        return strategy
    
    def resolve_vector_collection_name(
        self,
        naming_context: NamingContext,
        content_type: str = "chunks",
    ) -> str:
        """
        Resolved Vector-Collection-Namen für Kontext.
        
        Args:
            naming_context: Naming-Kontext aus Dokument-Metadata
            content_type: "chunks", "summaries", "embeddings"
        
        Returns:
            Collection-Name (z.B. "muenster_bauamt_genehmigungen_chunks")
        """
        cache_key = (
            self._context_hash(naming_context),
            "vector",
            content_type,
            naming_context.document_type,
        )
        
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]
        
        strategy = self.get_strategy_for_context(naming_context)
        
        name = strategy.generate_vector_collection_name(
            document_type=naming_context.document_type,
            content_type=content_type,
            legal_area=naming_context.rechtsgebiet,
        )
        
        if self.enable_caching:
            self._name_cache[cache_key] = name
        
        logger.debug(f"Resolved vector collection: {name} for context: {naming_context.document_id}")
        return name
    
    def resolve_relational_table_name(
        self,
        naming_context: NamingContext,
        entity_type: str = "documents",
    ) -> str:
        """
        Resolved Relational-Tabellen-Namen für Kontext.
        
        Args:
            naming_context: Naming-Kontext
            entity_type: "documents", "metadata", "processing"
        
        Returns:
            Tabellen-Name (z.B. "muenster_bauamt_documents_metadata")
        """
        cache_key = (
            self._context_hash(naming_context),
            "relational",
            entity_type,
            naming_context.processing_stage,
        )
        
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]
        
        strategy = self.get_strategy_for_context(naming_context)
        
        name = strategy.generate_relational_table_name(
            entity_type=entity_type,
            document_type=naming_context.document_type,
            purpose=naming_context.processing_stage,
        )
        
        if self.enable_caching:
            self._name_cache[cache_key] = name
        
        logger.debug(f"Resolved relational table: {name}")
        return name
    
    def resolve_graph_node_label(
        self,
        naming_context: NamingContext,
        node_type: str = "Document",
    ) -> str:
        """
        Resolved Graph-Node-Label für Kontext.
        
        Args:
            naming_context: Naming-Kontext
            node_type: "Document", "Authority", "Process"
        
        Returns:
            Node-Label (z.B. "MuensterBauamtDocument")
        """
        cache_key = (
            self._context_hash(naming_context),
            "graph_node",
            node_type,
            naming_context.document_type,
        )
        
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]
        
        strategy = self.get_strategy_for_context(naming_context)
        
        name = strategy.generate_graph_node_label(
            node_type=node_type,
            document_type=naming_context.document_type,
        )
        
        if self.enable_caching:
            self._name_cache[cache_key] = name
        
        logger.debug(f"Resolved graph node label: {name}")
        return name
    
    def resolve_graph_relationship_type(
        self,
        naming_context: NamingContext,
        rel_type: str,
    ) -> str:
        """
        Resolved Graph-Relationship-Type für Kontext.
        
        Args:
            naming_context: Naming-Kontext
            rel_type: "ISSUED_BY", "REFERENCES", etc.
        
        Returns:
            Relationship-Type (z.B. "BAUAMT_ISSUED_BY")
        """
        cache_key = (
            self._context_hash(naming_context),
            "graph_rel",
            rel_type,
        )
        
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]
        
        strategy = self.get_strategy_for_context(naming_context)
        
        # Kontext: Verwende Behörde als Kontext-Präfix
        context = naming_context.behoerde
        
        name = strategy.generate_graph_relationship_type(
            rel_type=rel_type,
            context=context,
        )
        
        if self.enable_caching:
            self._name_cache[cache_key] = name
        
        return name
    
    def resolve_file_storage_bucket(
        self,
        naming_context: NamingContext,
    ) -> str:
        """
        Resolved File-Storage-Bucket-Namen für Kontext.
        
        Args:
            naming_context: Naming-Kontext
        
        Returns:
            Bucket-Name (z.B. "muenster_bauamt_permits_internal")
        """
        cache_key = (
            self._context_hash(naming_context),
            "file_bucket",
            naming_context.access_level,
        )
        
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]
        
        strategy = self.get_strategy_for_context(naming_context)
        
        name = strategy.generate_file_storage_bucket(
            document_type=naming_context.document_type,
            access_level=naming_context.access_level,
        )
        
        if self.enable_caching:
            self._name_cache[cache_key] = name
        
        return name
    
    def resolve_all_names(self, naming_context: NamingContext) -> Dict[str, str]:
        """
        Resolved alle DB-Namen für einen Kontext auf einmal.
        
        Nützlich für Logging und Debugging.
        
        Returns:
            Dict mit allen resolved Namen:
            {
                "vector_collection": "...",
                "relational_table": "...",
                "graph_node_label": "...",
                "file_bucket": "...",
            }
        """
        return {
            "vector_collection": self.resolve_vector_collection_name(naming_context),
            "vector_summaries": self.resolve_vector_collection_name(naming_context, "summaries"),
            "relational_table": self.resolve_relational_table_name(naming_context),
            "graph_node_label": self.resolve_graph_node_label(naming_context),
            "file_bucket": self.resolve_file_storage_bucket(naming_context),
            "namespace": self.get_strategy_for_context(naming_context).generate_unified_namespace(),
        }
    
    def clear_cache(self):
        """Löscht alle Caches (z.B. für Tests)"""
        self._strategy_cache.clear()
        self._name_cache.clear()
        logger.info("Naming caches cleared")
    
    # Helper Methods
    
    @staticmethod
    def _org_context_hash(org_context: OrganizationContext) -> str:
        """Erstellt Hash-String für OrganizationContext"""
        return (
            f"{org_context.level.value}:"
            f"{org_context.state or ''}:"
            f"{org_context.municipality or ''}:"
            f"{org_context.authority or ''}:"
            f"{org_context.domain.value}"
        )
    
    @staticmethod
    def _context_hash(naming_context: NamingContext) -> str:
        """Erstellt Hash-String für NamingContext"""
        org_ctx = naming_context.to_organization_context()
        return NamingContextManager._org_context_hash(org_ctx)


# Decorator für automatische Namens-Resolution

def with_dynamic_naming(method):
    """
    Decorator für CRUD-Methoden: Resolved Collection/Table/Label-Namen automatisch.
    
    Sucht im kwargs nach "metadata" und erstellt daraus NamingContext.
    Ersetzt statische Namen durch dynamische Namen.
    
    Usage:
        @with_dynamic_naming
        def vector_create(self, document_id, chunks, metadata, collection="document_chunks"):
            # collection wird automatisch durch dynamischen Namen ersetzt
            ...
    """
    def wrapper(self, *args, **kwargs):
        # Prüfe ob NamingContextManager verfügbar ist
        if not hasattr(self, "_naming_manager") or not self._naming_manager:
            # Fallback: Keine dynamische Namensgebung
            return method(self, *args, **kwargs)
        
        # Extrahiere metadata
        metadata = kwargs.get("metadata") or (args[2] if len(args) > 2 else {})
        if not metadata or not isinstance(metadata, dict):
            # Keine Metadata: Fallback zu Default
            return method(self, *args, **kwargs)
        
        # Extrahiere document_id
        document_id = kwargs.get("document_id") or (args[0] if len(args) > 0 else None)
        if not document_id:
            return method(self, *args, **kwargs)
        
        # Erstelle NamingContext
        naming_context = NamingContext.from_metadata(document_id, metadata)
        
        # Resolved Namen basierend auf Methoden-Name
        method_name = method.__name__
        
        if "vector" in method_name:
            # Vector-Methoden: collection parameter ersetzen
            content_type = kwargs.get("content_type", "chunks")
            resolved_name = self._naming_manager.resolve_vector_collection_name(
                naming_context, content_type
            )
            kwargs["collection"] = resolved_name
        
        elif "relational" in method_name:
            # Relational-Methoden: table parameter ersetzen
            entity_type = kwargs.get("entity_type", "documents")
            resolved_name = self._naming_manager.resolve_relational_table_name(
                naming_context, entity_type
            )
            kwargs["table"] = resolved_name
        
        elif "graph" in method_name and "node" in method_name:
            # Graph-Node-Methoden: label parameter ersetzen
            node_type = kwargs.get("node_type", "Document")
            resolved_name = self._naming_manager.resolve_graph_node_label(
                naming_context, node_type
            )
            kwargs["label"] = resolved_name
        
        elif "file" in method_name:
            # File-Methoden: bucket/database parameter ersetzen
            resolved_name = self._naming_manager.resolve_file_storage_bucket(naming_context)
            kwargs["bucket"] = resolved_name
        
        return method(self, *args, **kwargs)
    
    return wrapper


# Beispiel: Erweiterte SagaDatabaseCRUD mit Naming

class DynamicNamingSagaCRUD:
    """
    Wrapper für SagaDatabaseCRUD mit dynamischer Namensgebung.
    
    Kann als Drop-In-Replacement für SagaDatabaseCRUD verwendet werden.
    """
    
    def __init__(
        self,
        saga_crud_instance,  # Original SagaDatabaseCRUD
        naming_manager: Optional[NamingContextManager] = None,
    ):
        """
        Args:
            saga_crud_instance: Bestehende SagaDatabaseCRUD-Instanz
            naming_manager: NamingContextManager (oder None für Default)
        """
        self._saga_crud = saga_crud_instance
        self._naming_manager = naming_manager or NamingContextManager()
    
    # Vector Operations mit dynamischer Namensgebung
    
    def vector_create(
        self,
        document_id: str,
        chunks: List[str],
        metadata: Dict[str, Any],
        collection: Optional[str] = None,
    ):
        """
        Vector-Create mit dynamischer Collection-Namensgebung.
        
        Args:
            document_id: Dokument-ID
            chunks: Text-Chunks
            metadata: Metadata mit Behörden-/Rechtskontext
            collection: Optional statischer Name (überschreibt dynamische Naming)
        """
        if collection is None:
            # Dynamic Naming
            naming_context = NamingContext.from_metadata(document_id, metadata)
            collection = self._naming_manager.resolve_vector_collection_name(naming_context)
        
        logger.info(f"Vector CREATE in collection: {collection}")
        
        # Delegiere an original CRUD
        return self._saga_crud.vector_create(document_id, chunks, metadata, collection=collection)
    
    def vector_update(
        self,
        document_id: str,
        chunks: List[str],
        metadata: Dict[str, Any],
        collection: Optional[str] = None,
    ):
        if collection is None:
            naming_context = NamingContext.from_metadata(document_id, metadata)
            collection = self._naming_manager.resolve_vector_collection_name(naming_context)
        
        return self._saga_crud.vector_update(document_id, chunks, metadata, collection=collection)
    
    def vector_delete(
        self,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        collection: Optional[str] = None,
        **kwargs
    ):
        if collection is None and metadata:
            naming_context = NamingContext.from_metadata(document_id, metadata)
            collection = self._naming_manager.resolve_vector_collection_name(naming_context)
        
        return self._saga_crud.vector_delete(document_id, collection=collection, **kwargs)
    
    # Relational Operations
    
    def relational_create(
        self,
        document_data: Dict[str, Any],
        table: Optional[str] = None,
    ):
        if table is None and "document_id" in document_data:
            naming_context = NamingContext.from_metadata(
                document_data["document_id"], document_data
            )
            table = self._naming_manager.resolve_relational_table_name(naming_context)
        
        logger.info(f"Relational CREATE in table: {table}")
        
        return self._saga_crud.relational_create(document_data, table=table)
    
    # Graph Operations
    
    def graph_create(
        self,
        document_id: str,
        properties: Dict[str, Any],
        label: Optional[str] = None,
    ):
        if label is None:
            naming_context = NamingContext.from_metadata(document_id, properties)
            label = self._naming_manager.resolve_graph_node_label(naming_context)
        
        logger.info(f"Graph CREATE node with label: {label}")
        
        return self._saga_crud.graph_create(document_id, properties, label=label)
    
    # Delegation für andere Methoden
    
    def __getattr__(self, name):
        """Delegiert alle anderen Methoden an original SagaCRUD"""
        return getattr(self._saga_crud, name)


# Factory Function

def create_naming_enabled_saga_crud(
    saga_crud_instance,
    org_context: Optional[OrganizationContext] = None,
    naming_manager: Optional[NamingContextManager] = None,
    **naming_config
) -> DynamicNamingSagaCRUD:
    """
    Factory: Erstellt DynamicNamingSagaCRUD mit Konfiguration.
    
    Args:
        saga_crud_instance: Bestehende SagaDatabaseCRUD-Instanz
        org_context: Standard-Organisationskontext
        naming_manager: Bestehende NamingContextManager-Instanz (überschreibt naming_config)
        **naming_config: Weitere Konfiguration für NamingContextManager
    
    Returns:
        DynamicNamingSagaCRUD Instanz
    """
    # Verwende bestehenden naming_manager oder erstelle neuen
    if naming_manager is None:
        naming_manager = NamingContextManager(
            default_org_context=org_context,
            **naming_config
        )
    
    return DynamicNamingSagaCRUD(
        saga_crud_instance=saga_crud_instance,
        naming_manager=naming_manager,
    )


# Beispiel-Usage
if __name__ == "__main__":
    print("=== UDS3 Naming Integration - Beispiel ===\n")
    
    # Beispiel-Metadata
    metadata_muenster = {
        "behoerde": "Bauamt",
        "kommune": "Münster",
        "bundesland": "NRW",
        "rechtsgebiet": "Baurecht",
        "document_type": "PERMIT",
        "admin_level": "municipal",
    }
    
    # NamingContext erstellen
    naming_ctx = NamingContext.from_metadata("doc_12345", metadata_muenster)
    
    # NamingContextManager
    naming_mgr = NamingContextManager()
    
    # Namen resolven
    resolved_names = naming_mgr.resolve_all_names(naming_ctx)
    
    print("📋 Resolved Namen für Münster Bauamt Baugenehmigung:")
    for key, value in resolved_names.items():
        print(f"  {key:25} → {value}")
    
    print("\n✅ Integration erfolgreich!")
