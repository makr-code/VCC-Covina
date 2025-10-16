#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Dynamic Naming Strategy

Dynamische, kontextbezogene Benennung für Collections, Tables, Node-Labels
und Relationships basierend auf:
- Behörden-Kontext (Bund, Land, Kommune)
- Rechtsgebiet (Baurecht, Umweltrecht, etc.)
- Organisationsstruktur (Abteilung, Referat, etc.)

Vermeidet statische Namen wie "document_chunks", "documents_metadata"
und generiert stattdessen kontextspezifische Namen wie:
- "bauamt_muenster_baugenehmigungen_chunks"
- "umweltamt_nrw_umweltgenehmigungen"
- "landesverwaltung_nrw_raumplaene"
"""

from __future__ import annotations

import re
import hashlib
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field

# Import Admin Types
try:
    from uds3_admin_types import AdminLevel, AdminDomain, AdminDocumentType
except ImportError:
    # Fallback für Standalone-Tests
    class AdminLevel(Enum):
        FEDERAL = "bund"
        STATE = "land"
        MUNICIPAL = "kommune"
    
    class AdminDomain(Enum):
        BUILDING = "bau"
        ENVIRONMENT = "umwelt"
        PLANNING = "planung"
        GENERAL_ADMIN = "allgemein"
    
    class AdminDocumentType(Enum):
        PERMIT = "genehmigung"
        DECISION = "bescheid"
        PLAN = "plan"


class NamingConvention(Enum):
    """Namenskonventionen für verschiedene DB-Typen"""
    SNAKE_CASE = "snake_case"  # Standard: my_collection_name
    KEBAB_CASE = "kebab-case"   # Alternative: my-collection-name
    CAMEL_CASE = "camelCase"    # Java-Style: myCollectionName
    PASCAL_CASE = "PascalCase"  # Class-Style: MyCollectionName


@dataclass
class OrganizationContext:
    """Behörden-/Organisations-Kontext für Namensgebung"""
    
    # Hierarchie-Ebene
    level: AdminLevel = AdminLevel.MUNICIPAL
    
    # Bundesland (für Land/Kommune)
    state: Optional[str] = None  # "nrw", "bayern", "berlin", etc.
    
    # Kommune/Stadt (für Kommune-Ebene)
    municipality: Optional[str] = None  # "muenster", "koeln", "hamburg"
    
    # Behörde/Amt
    authority: Optional[str] = None  # "bauamt", "umweltamt", "planungsamt"
    
    # Abteilung (optional)
    department: Optional[str] = None  # "baugenehmigungen", "umweltschutz"
    
    # Zuständigkeitsbereich
    domain: AdminDomain = AdminDomain.GENERAL_ADMIN
    
    # Rechtsgebiet(e)
    legal_areas: List[str] = field(default_factory=list)  # ["baurecht", "umweltrecht"]
    
    # Organisationskürzel (optional)
    org_abbreviation: Optional[str] = None  # "BA-MS", "UA-NRW"
    
    def __post_init__(self):
        """Validierung und Normalisierung"""
        # Normalisiere Strings zu lowercase ohne Sonderzeichen
        if self.state:
            self.state = self._normalize(self.state)
        if self.municipality:
            self.municipality = self._normalize(self.municipality)
        if self.authority:
            self.authority = self._normalize(self.authority)
        if self.department:
            self.department = self._normalize(self.department)
        if self.legal_areas:
            self.legal_areas = [self._normalize(area) for area in self.legal_areas]
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalisiert Text für DB-Namen"""
        # Umlaute ersetzen
        text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
        text = text.replace('Ä', 'Ae').replace('Ö', 'Oe').replace('Ü', 'Ue')
        text = text.replace('ß', 'ss')
        # Nur alphanumerische Zeichen und Unterstriche
        text = re.sub(r'[^a-z0-9_]', '_', text.lower())
        # Mehrfache Unterstriche reduzieren
        text = re.sub(r'_+', '_', text)
        # Keine führenden/folgenden Unterstriche
        return text.strip('_')
    
    def get_hierarchy_path(self) -> str:
        """Erstellt hierarchischen Pfad: bund/land/kommune"""
        parts = [self.level.value]
        if self.state:
            parts.append(self.state)
        if self.municipality:
            parts.append(self.municipality)
        return '/'.join(parts)
    
    def get_organization_prefix(self) -> str:
        """Erstellt Organisations-Präfix für Namen"""
        parts = []
        
        # Ebene-spezifisch
        if self.level == AdminLevel.FEDERAL:
            parts.append("bund")
        elif self.level == AdminLevel.STATE and self.state:
            parts.append(self.state)
        elif self.level == AdminLevel.MUNICIPAL:
            if self.municipality:
                parts.append(self.municipality)
            elif self.state:
                parts.append(f"{self.state}_kommune")
        
        # Behörde
        if self.authority:
            parts.append(self.authority)
        elif self.domain and self.domain != AdminDomain.GENERAL_ADMIN:
            parts.append(self.domain.value)
        
        # Abteilung (optional)
        if self.department:
            parts.append(self.department)
        
        return '_'.join(parts) if parts else "org"


@dataclass
class NamingStrategy:
    """Zentrale Namensgebungsstrategie für UDS3"""
    
    # Organisations-Kontext
    org_context: OrganizationContext
    
    # Namenskonvention
    convention: NamingConvention = NamingConvention.SNAKE_CASE
    
    # Präfix für alle Namen (optional)
    global_prefix: Optional[str] = "uds3"
    
    # Suffix für Versionierung (optional)
    version_suffix: Optional[str] = None  # z.B. "v2", "2024"
    
    # Maximale Länge für Namen (DB-abhängig)
    max_length: int = 64
    
    # Hash-Suffixe bei langen Namen
    use_hash_suffix: bool = True
    
    # Cache für generierte Namen
    _name_cache: Dict[str, str] = field(default_factory=dict, init=False, repr=False)
    
    def generate_vector_collection_name(
        self,
        document_type: Optional[AdminDocumentType] = None,
        content_type: str = "chunks",  # "chunks", "summaries", "embeddings"
        legal_area: Optional[str] = None,
    ) -> str:
        """
        Generiert Vector-DB Collection-Namen.
        
        Beispiele:
        - muenster_bauamt_baugenehmigungen_chunks
        - nrw_umweltamt_umweltschutz_embeddings
        - bund_gesetze_chunks
        """
        parts = [self.org_context.get_organization_prefix()]
        
        # Rechtsgebiet oder Dokumenttyp
        if legal_area:
            parts.append(self.org_context._normalize(legal_area))
        elif document_type:
            parts.append(self._get_doctype_name(document_type))
        
        # Content-Type
        parts.append(content_type)
        
        return self._build_name(parts, db_type="vector")
    
    def generate_relational_table_name(
        self,
        entity_type: str = "documents",  # "documents", "metadata", "processing"
        document_type: Optional[AdminDocumentType] = None,
        purpose: Optional[str] = None,  # "audit", "archive", "active"
    ) -> str:
        """
        Generiert Relational-DB Tabellennamen.
        
        Beispiele:
        - muenster_bauamt_documents_metadata
        - nrw_umweltamt_permits_active
        - bund_gesetze_archive
        """
        parts = [self.org_context.get_organization_prefix()]
        
        # Entity-Type
        if document_type:
            parts.append(self._get_doctype_name(document_type))
        parts.append(entity_type)
        
        # Purpose/Status
        if purpose:
            parts.append(purpose)
        
        return self._build_name(parts, db_type="relational")
    
    def generate_graph_node_label(
        self,
        node_type: str = "Document",  # "Document", "Authority", "Process"
        document_type: Optional[AdminDocumentType] = None,
        specialization: Optional[str] = None,
    ) -> str:
        """
        Generiert Graph-DB Node-Labels.
        
        Beispiele:
        - MuensterBauamtDocument
        - NRWUmweltPermit
        - BundGesetz
        
        Note: Graph Labels verwenden PascalCase
        """
        parts = []
        
        # Organisations-Präfix (PascalCase)
        org_prefix = self.org_context.get_organization_prefix()
        parts.append(self._to_pascal_case(org_prefix))
        
        # Dokumenttyp oder Spezialisierung
        if document_type:
            parts.append(self._to_pascal_case(self._get_doctype_name(document_type)))
        elif specialization:
            parts.append(self._to_pascal_case(specialization))
        
        # Node-Type
        if node_type != "Document" or not document_type:
            parts.append(node_type)
        
        # Labels sollten nicht zu lang sein
        label = ''.join(parts)
        if len(label) > self.max_length:
            # Kürze intelligently
            label = self._shorten_label(label)
        
        return label
    
    def generate_graph_relationship_type(
        self,
        rel_type: str,  # "ISSUED_BY", "REFERENCES", "SUPERSEDES"
        context: Optional[str] = None,  # Zusätzlicher Kontext
    ) -> str:
        """
        Generiert Graph-DB Relationship-Types.
        
        Beispiele:
        - BAUAMT_ISSUED_BY
        - NRW_REFERENCES
        - SUPERSEDES (ohne Kontext)
        
        Note: Relationships verwenden UPPER_SNAKE_CASE
        """
        parts = []
        
        # Optional: Organisations-Kontext
        if context:
            parts.append(self.org_context._normalize(context).upper())
        
        # Relationship-Type
        parts.append(rel_type.upper())
        
        return '_'.join(parts)
    
    def generate_file_storage_bucket(
        self,
        document_type: Optional[AdminDocumentType] = None,
        access_level: str = "internal",  # "public", "internal", "confidential"
    ) -> str:
        """
        Generiert File-Storage Bucket/Database-Namen.
        
        Beispiele:
        - muenster_bauamt_permits_internal
        - nrw_umwelt_documents_confidential
        - bund_gesetze_public
        """
        parts = [self.org_context.get_organization_prefix()]
        
        if document_type:
            parts.append(self._get_doctype_name(document_type))
        else:
            parts.append("documents")
        
        parts.append(access_level)
        
        return self._build_name(parts, db_type="file")
    
    def generate_unified_namespace(self) -> str:
        """
        Generiert einheitlichen Namespace für Cross-DB Queries.
        
        Beispiele:
        - muenster_bauamt
        - nrw_umweltamt
        - bund_justiz
        """
        return self.org_context.get_organization_prefix()
    
    # Helper Methods
    
    def _get_doctype_name(self, doc_type: AdminDocumentType) -> str:
        """Konvertiert DocumentType zu kurzen, lesbaren Namen"""
        # Einfach den Enum-Value verwenden (z.B. "permit" → "permit")
        # Oder spezielle Mappings für deutsche Namen
        name = doc_type.value.lower()
        
        # Entferne Unterstriche, ersetze durch lesbare Form
        name = name.replace("_", "")
        
        return name
    
    def _build_name(self, parts: List[str], db_type: str) -> str:
        """Baut finalen Namen aus Teilen"""
        # Global Prefix
        if self.global_prefix:
            parts.insert(0, self.global_prefix)
        
        # Join mit Konvention
        if self.convention == NamingConvention.SNAKE_CASE:
            name = '_'.join(parts)
        elif self.convention == NamingConvention.KEBAB_CASE:
            name = '-'.join(parts)
        elif self.convention == NamingConvention.CAMEL_CASE:
            name = parts[0] + ''.join(p.capitalize() for p in parts[1:])
        else:  # PASCAL_CASE
            name = ''.join(p.capitalize() for p in parts)
        
        # Version Suffix
        if self.version_suffix:
            name = f"{name}_{self.version_suffix}"
        
        # Längen-Check
        if len(name) > self.max_length:
            if self.use_hash_suffix:
                # Kürze und füge Hash hinzu
                name = self._shorten_with_hash(name)
            else:
                name = name[:self.max_length]
        
        # Cache
        cache_key = f"{db_type}:{':'.join(parts)}"
        self._name_cache[cache_key] = name
        
        return name
    
    def _shorten_with_hash(self, name: str) -> str:
        """Kürzt Namen und fügt Hash-Suffix hinzu"""
        # Hash der vollen Namen
        hash_val = hashlib.md5(name.encode()).hexdigest()[:8]
        
        # Kürze auf max_length - 9 (für _hash)
        shortened = name[:self.max_length - 9]
        
        return f"{shortened}_{hash_val}"
    
    def _shorten_label(self, label: str) -> str:
        """Kürzt Graph-Labels intelligent"""
        # Entferne Vokale außer am Anfang
        if len(label) <= self.max_length:
            return label
        
        # Behalte erste 3 Buchstaben jedes Wortes
        parts = re.findall(r'[A-Z][a-z]*', label)
        shortened = ''.join(p[:3] for p in parts)
        
        if len(shortened) > self.max_length:
            shortened = shortened[:self.max_length]
        
        return shortened
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """Konvertiert snake_case zu PascalCase"""
        return ''.join(word.capitalize() for word in snake_str.split('_'))


# Factory Functions für häufige Szenarien

def create_municipal_strategy(
    municipality: str,
    authority: str,
    state: str = "nrw",
    **kwargs
) -> NamingStrategy:
    """Erstellt Naming-Strategy für Kommune"""
    org_context = OrganizationContext(
        level=AdminLevel.MUNICIPAL,
        state=state,
        municipality=municipality,
        authority=authority,
        **kwargs
    )
    return NamingStrategy(org_context=org_context)


def create_state_strategy(
    state: str,
    authority: str,
    **kwargs
) -> NamingStrategy:
    """Erstellt Naming-Strategy für Landesbehörde"""
    org_context = OrganizationContext(
        level=AdminLevel.STATE,
        state=state,
        authority=authority,
        **kwargs
    )
    return NamingStrategy(org_context=org_context)


def create_federal_strategy(
    authority: str,
    **kwargs
) -> NamingStrategy:
    """Erstellt Naming-Strategy für Bundesbehörde"""
    org_context = OrganizationContext(
        level=AdminLevel.FEDERAL,
        authority=authority,
        **kwargs
    )
    return NamingStrategy(org_context=org_context)


# Beispiel-Usage
if __name__ == "__main__":
    print("=== UDS3 Dynamic Naming Strategy - Beispiele ===\n")
    
    # Beispiel 1: Kommune Münster, Bauamt
    strategy_ms = create_municipal_strategy(
        municipality="muenster",
        authority="bauamt",
        state="nrw",
        domain=AdminDomain.BUILDING
    )
    
    print("📍 Münster Bauamt:")
    print(f"  Vector Collection: {strategy_ms.generate_vector_collection_name(AdminDocumentType.PERMIT)}")
    print(f"  Relational Table:  {strategy_ms.generate_relational_table_name('metadata', AdminDocumentType.PERMIT)}")
    print(f"  Graph Node Label:  {strategy_ms.generate_graph_node_label('Document', AdminDocumentType.PERMIT)}")
    print(f"  File Bucket:       {strategy_ms.generate_file_storage_bucket(AdminDocumentType.PERMIT)}")
    print(f"  Namespace:         {strategy_ms.generate_unified_namespace()}\n")
    
    # Beispiel 2: Land NRW, Umweltamt
    strategy_nrw = create_state_strategy(
        state="nrw",
        authority="umweltamt",
        domain=AdminDomain.ENVIRONMENT
    )
    
    print("🏛️ NRW Umweltamt:")
    print(f"  Vector Collection: {strategy_nrw.generate_vector_collection_name(content_type='embeddings')}")
    print(f"  Relational Table:  {strategy_nrw.generate_relational_table_name('permits', purpose='active')}")
    print(f"  Graph Node Label:  {strategy_nrw.generate_graph_node_label('Authority')}")
    print(f"  Relationship:      {strategy_nrw.generate_graph_relationship_type('ISSUED_BY')}")
    print(f"  Namespace:         {strategy_nrw.generate_unified_namespace()}\n")
    
    # Beispiel 3: Bund, Justizministerium
    strategy_bund = create_federal_strategy(
        authority="justiz",
        domain=AdminDomain.GENERAL
    )
    
    print("🏛️ Bundesjustizministerium:")
    print(f"  Vector Collection: {strategy_bund.generate_vector_collection_name(legal_area='strafrecht')}")
    print(f"  Relational Table:  {strategy_bund.generate_relational_table_name('gesetze')}")
    print(f"  Graph Node Label:  {strategy_bund.generate_graph_node_label('Law')}")
    print(f"  File Bucket:       {strategy_bund.generate_file_storage_bucket(access_level='public')}")
    print(f"  Namespace:         {strategy_bund.generate_unified_namespace()}\n")
