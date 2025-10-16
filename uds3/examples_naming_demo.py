#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beispiel: UDS3 Dynamic Naming in Action

Demonstriert wie die dynamische Namensgebung in verschiedenen Szenarien funktioniert.
"""

import sys
from pprint import pprint

# Import Naming Components
from uds3_naming_strategy import (
    NamingStrategy,
    OrganizationContext,
    create_municipal_strategy,
    create_state_strategy,
    create_federal_strategy,
)

from uds3_naming_integration import (
    NamingContext,
    NamingContextManager,
)

try:
    from uds3_admin_types import AdminDocumentType, AdminLevel, AdminDomain
except ImportError:
    print("⚠️  uds3_admin_types nicht gefunden - verwende Mock-Enums")
    from enum import Enum
    
    class AdminDocumentType(Enum):
        PERMIT = "genehmigung"
        DECISION = "bescheid"
        PLAN = "plan"
        LAW = "gesetz"
        REGULATION = "verordnung"
    
    class AdminLevel(Enum):
        FEDERAL = "bund"
        STATE = "land"
        MUNICIPAL = "kommune"
    
    class AdminDomain(Enum):
        BUILDING_LAW = "bau"
        ENVIRONMENTAL_LAW = "umwelt"
        PLANNING_LAW = "planung"
        GENERAL_ADMIN = "allgemein"


def print_section(title: str):
    """Formatiert Section-Header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def demo_basic_naming_strategy():
    """Demo 1: Basis-Verwendung von NamingStrategy"""
    print_section("Demo 1: Basis NamingStrategy")
    
    # Szenario 1: Stadt Münster, Bauamt
    strategy_muenster = create_municipal_strategy(
        municipality="münster",
        authority="bauamt",
        state="nrw",
        domain=AdminDomain.BUILDING_LAW,
    )
    
    print("🏙️  Stadt Münster - Bauamt:")
    print(f"   Vector Collection (chunks):   {strategy_muenster.generate_vector_collection_name(AdminDocumentType.PERMIT, 'chunks')}")
    print(f"   Vector Collection (summaries): {strategy_muenster.generate_vector_collection_name(AdminDocumentType.PERMIT, 'summaries')}")
    print(f"   Relational Table (metadata):   {strategy_muenster.generate_relational_table_name('metadata', AdminDocumentType.PERMIT)}")
    print(f"   Graph Node Label:              {strategy_muenster.generate_graph_node_label('Document', AdminDocumentType.PERMIT)}")
    print(f"   File Storage Bucket:           {strategy_muenster.generate_file_storage_bucket(AdminDocumentType.PERMIT, 'internal')}")
    print(f"   Unified Namespace:             {strategy_muenster.generate_unified_namespace()}")
    
    # Szenario 2: Land NRW, Umweltministerium
    strategy_nrw = create_state_strategy(
        state="nordrhein-westfalen",
        authority="umweltministerium",
        domain=AdminDomain.ENVIRONMENTAL_LAW,
    )
    
    print("\n🏛️  Land NRW - Umweltministerium:")
    print(f"   Vector Collection:    {strategy_nrw.generate_vector_collection_name(AdminDocumentType.REGULATION, 'embeddings')}")
    print(f"   Relational Table:     {strategy_nrw.generate_relational_table_name('permits', AdminDocumentType.REGULATION, 'active')}")
    print(f"   Graph Node Label:     {strategy_nrw.generate_graph_node_label('Regulation', AdminDocumentType.REGULATION)}")
    print(f"   Graph Relationship:   {strategy_nrw.generate_graph_relationship_type('ISSUED_BY', 'umwelt')}")
    
    # Szenario 3: Bundesebene, Justizministerium
    strategy_bund = create_federal_strategy(
        authority="bundesjustizministerium",
        domain=AdminDomain.GENERAL_ADMIN,
    )
    
    print("\n🏛️  Bund - Bundesjustizministerium:")
    print(f"   Vector Collection:    {strategy_bund.generate_vector_collection_name(AdminDocumentType.LAW, 'chunks', 'strafrecht')}")
    print(f"   Relational Table:     {strategy_bund.generate_relational_table_name('gesetze', AdminDocumentType.LAW)}")
    print(f"   Graph Node Label:     {strategy_bund.generate_graph_node_label('Law', AdminDocumentType.LAW)}")
    print(f"   File Bucket (public): {strategy_bund.generate_file_storage_bucket(AdminDocumentType.LAW, 'public')}")


def demo_naming_context_from_metadata():
    """Demo 2: NamingContext aus Dokument-Metadata"""
    print_section("Demo 2: NamingContext aus Dokument-Metadata")
    
    # Simuliere Dokument-Metadata
    metadata_examples = [
        {
            "document_id": "BAU-2024-001",
            "behoerde": "Bauamt",
            "kommune": "Köln",
            "bundesland": "NRW",
            "rechtsgebiet": "Baurecht",
            "document_type": "PERMIT",
            "admin_level": "municipal",
            "rechtsnorm": "BauGB §34",
        },
        {
            "document_id": "UMW-NRW-042",
            "behoerde": "Umweltamt",
            "bundesland": "Nordrhein-Westfalen",
            "rechtsgebiet": "Umweltrecht",
            "document_type": "DECISION",
            "admin_level": "state",
        },
        {
            "document_id": "BGBl-2023-1234",
            "behoerde": "Bundesjustizministerium",
            "rechtsgebiet": "Strafrecht",
            "document_type": "LAW",
            "admin_level": "federal",
            "access_level": "public",
        },
    ]
    
    naming_mgr = NamingContextManager()
    
    for i, metadata in enumerate(metadata_examples, 1):
        print(f"\n📄 Dokument {i}: {metadata['document_id']}")
        print(f"   Behörde: {metadata.get('behoerde', 'N/A')}")
        print(f"   Ebene: {metadata.get('admin_level', 'N/A')}")
        print(f"   Rechtsgebiet: {metadata.get('rechtsgebiet', 'N/A')}")
        
        # NamingContext erstellen
        naming_ctx = NamingContext.from_metadata(metadata["document_id"], metadata)
        
        # Namen resolven
        resolved = naming_mgr.resolve_all_names(naming_ctx)
        
        print("\n   → Generierte Namen:")
        print(f"      Vector Collection: {resolved['vector_collection']}")
        print(f"      Relational Table:  {resolved['relational_table']}")
        print(f"      Graph Node:        {resolved['graph_node_label']}")
        print(f"      File Bucket:       {resolved['file_bucket']}")
        print(f"      Namespace:         {resolved['namespace']}")


def demo_multi_tenant_scenario():
    """Demo 3: Multi-Tenant-Szenario"""
    print_section("Demo 3: Multi-Tenant-Szenario")
    
    print("🎯 Szenario: Mehrere Kommunen nutzen dieselbe UDS3-Instanz\n")
    
    # Verschiedene Kommunen
    municipalities = [
        {"name": "Münster", "state": "nrw"},
        {"name": "Köln", "state": "nrw"},
        {"name": "München", "state": "bayern"},
        {"name": "Stuttgart", "state": "baden-württemberg"},
    ]
    
    naming_mgr = NamingContextManager()
    
    for muni in municipalities:
        # Metadata für Baugenehmigung
        metadata = {
            "behoerde": "Bauamt",
            "kommune": muni["name"],
            "bundesland": muni["state"],
            "rechtsgebiet": "Baurecht",
            "document_type": "PERMIT",
            "admin_level": "municipal",
        }
        
        naming_ctx = NamingContext.from_metadata(f"BAU-{muni['name']}-001", metadata)
        
        collection = naming_mgr.resolve_vector_collection_name(naming_ctx)
        table = naming_mgr.resolve_relational_table_name(naming_ctx)
        
        print(f"📍 {muni['name']:15} → Vector: {collection:40} | Table: {table}")
    
    print("\n✅ Jede Kommune hat separate Collections/Tables!")
    print("   → Keine Datenvermischung")
    print("   → Separate Zugriffskontrollen möglich")
    print("   → Skalierbare Multi-Tenancy")


def demo_rechtsgebiet_separation():
    """Demo 4: Trennung nach Rechtsgebieten"""
    print_section("Demo 4: Trennung nach Rechtsgebieten")
    
    print("🎯 Szenario: Stadt Münster mit verschiedenen Rechtsgebieten\n")
    
    rechtsgebiete = [
        {"gebiet": "Baurecht", "doc_type": "PERMIT"},
        {"gebiet": "Umweltrecht", "doc_type": "DECISION"},
        {"gebiet": "Planungsrecht", "doc_type": "PLAN"},
        {"gebiet": "Ordnungsrecht", "doc_type": "DECISION"},
    ]
    
    naming_mgr = NamingContextManager()
    
    for rg in rechtsgebiete:
        metadata = {
            "behoerde": "Stadtverwaltung",
            "kommune": "Münster",
            "bundesland": "NRW",
            "rechtsgebiet": rg["gebiet"],
            "document_type": rg["doc_type"],
            "admin_level": "municipal",
        }
        
        naming_ctx = NamingContext.from_metadata(f"DOC-{rg['gebiet']}", metadata)
        
        collection = naming_mgr.resolve_vector_collection_name(naming_ctx)
        node_label = naming_mgr.resolve_graph_node_label(naming_ctx)
        
        print(f"⚖️  {rg['gebiet']:20} → Vector: {collection:45} | Graph: {node_label}")
    
    print("\n✅ Separate Collections pro Rechtsgebiet!")
    print("   → Gezielte Suche nur in relevantem Rechtsgebiet")
    print("   → Bessere Performance (kleinere Indizes)")
    print("   → Klare Daten-Organisation")


def demo_processing_stages():
    """Demo 5: Verschiedene Processing-Stages"""
    print_section("Demo 5: Processing-Stages (Active, Archive, Draft)")
    
    print("🎯 Szenario: Dokument-Lifecycle mit verschiedenen Stages\n")
    
    stages = ["draft", "active", "archive", "deleted"]
    
    naming_mgr = NamingContextManager()
    
    base_metadata = {
        "behoerde": "Bauamt",
        "kommune": "Dortmund",
        "bundesland": "NRW",
        "rechtsgebiet": "Baurecht",
        "document_type": "PERMIT",
        "admin_level": "municipal",
    }
    
    for stage in stages:
        metadata = {**base_metadata, "processing_stage": stage}
        naming_ctx = NamingContext.from_metadata(f"BAU-2024-{stage}", metadata)
        
        table = naming_mgr.resolve_relational_table_name(naming_ctx)
        
        print(f"📊 Stage: {stage:10} → Table: {table}")
    
    print("\n✅ Separate Tabellen pro Processing-Stage!")
    print("   → Aktive Dokumente in separater Tabelle (schnelle Queries)")
    print("   → Archive in eigener Tabelle (weniger Index-Load)")
    print("   → Drafts isoliert (keine Vermischung mit finalen Dokumenten)")


def demo_access_levels():
    """Demo 6: Verschiedene Access-Levels für File-Storage"""
    print_section("Demo 6: Access-Levels (Public, Internal, Confidential)")
    
    print("🎯 Szenario: Verschiedene Sicherheitsstufen für Dokumente\n")
    
    access_levels = ["public", "internal", "confidential", "classified"]
    
    naming_mgr = NamingContextManager()
    
    base_metadata = {
        "behoerde": "Ordnungsamt",
        "kommune": "Essen",
        "bundesland": "NRW",
        "rechtsgebiet": "Ordnungsrecht",
        "document_type": "DECISION",
        "admin_level": "municipal",
    }
    
    for level in access_levels:
        metadata = {**base_metadata, "access_level": level}
        naming_ctx = NamingContext.from_metadata(f"ORD-{level}", metadata)
        
        bucket = naming_mgr.resolve_file_storage_bucket(naming_ctx)
        
        print(f"🔒 Access: {level:15} → Bucket: {bucket}")
    
    print("\n✅ Separate Buckets pro Access-Level!")
    print("   → Physische Trennung sensibler Daten")
    print("   → Separate Zugriffsrichtlinien pro Bucket")
    print("   → Compliance-konforme Datenhaltung")


def demo_comparison_static_vs_dynamic():
    """Demo 7: Vergleich Statisch vs. Dynamisch"""
    print_section("Demo 7: Statische vs. Dynamische Namensgebung")
    
    print("📊 Vergleich für 3 Dokumente:\n")
    
    documents = [
        {
            "id": "BAU-MS-001",
            "behoerde": "Bauamt Münster",
            "document_type": "PERMIT",
            "rechtsgebiet": "Baurecht",
        },
        {
            "id": "UMW-K-042",
            "behoerde": "Umweltamt Köln",
            "document_type": "DECISION",
            "rechtsgebiet": "Umweltrecht",
        },
        {
            "id": "PLAN-DO-12",
            "behoerde": "Planungsamt Dortmund",
            "document_type": "PLAN",
            "rechtsgebiet": "Planungsrecht",
        },
    ]
    
    print("❌ STATISCHE Namensgebung (Alt):")
    print(f"   Alle Dokumente → Vector: 'document_chunks'")
    print(f"   Alle Dokumente → Table:  'documents_metadata'")
    print(f"   Alle Dokumente → Node:   'Document'")
    print("\n   Problem: Keine Trennung, alle Daten gemischt!\n")
    
    print("✅ DYNAMISCHE Namensgebung (Neu):\n")
    
    naming_mgr = NamingContextManager()
    
    for doc in documents:
        metadata = {
            "behoerde": doc["behoerde"],
            "kommune": doc["behoerde"].split()[-1],
            "bundesland": "NRW",
            "rechtsgebiet": doc["rechtsgebiet"],
            "document_type": doc["document_type"],
            "admin_level": "municipal",
        }
        
        naming_ctx = NamingContext.from_metadata(doc["id"], metadata)
        
        collection = naming_mgr.resolve_vector_collection_name(naming_ctx)
        table = naming_mgr.resolve_relational_table_name(naming_ctx)
        node = naming_mgr.resolve_graph_node_label(naming_ctx)
        
        print(f"   📄 {doc['id']:12} ({doc['document_type']:10})")
        print(f"      Vector: {collection}")
        print(f"      Table:  {table}")
        print(f"      Node:   {node}\n")
    
    print("✅ Vorteile:")
    print("   • Klare Datentrennung pro Behörde")
    print("   • Gezielte Suche nur in relevanten Collections")
    print("   • Multi-Tenancy ohne Datenvermischung")
    print("   • Semantisch aussagekräftige Namen")
    print("   • Bessere Performance (kleinere Indizes)")


def demo_integration_with_existing_code():
    """Demo 8: Integration mit bestehendem Code"""
    print_section("Demo 8: Integration mit bestehendem UDS3-Code")
    
    print("🔧 Beispiel: Anpassung von saga_crud.py\n")
    
    print("❌ ALT (saga_crud.py, Zeile 470):")
    print("   def vector_create(self, document_id, chunks, metadata, collection='document_chunks'):")
    print("       # Statischer Default-Name\n")
    
    print("✅ NEU (mit NamingContextManager):")
    print("   def vector_create(self, document_id, chunks, metadata, collection=None):")
    print("       if collection is None:")
    print("           # Dynamische Namensgebung")
    print("           naming_ctx = NamingContext.from_metadata(document_id, metadata)")
    print("           collection = self.naming_manager.resolve_vector_collection_name(naming_ctx)")
    print("       # Rest bleibt gleich...\n")
    
    print("✅ Vorteile:")
    print("   • Abwärtskompatibel (collection-Parameter bleibt)")
    print("   • Opt-In: Wenn collection=None, dann dynamisch")
    print("   • Minimale Code-Änderungen")
    print("   • Kein Breaking Change für Tests")


def main():
    """Hauptprogramm: Alle Demos ausführen"""
    print("\n" + "="*80)
    print("  UDS3 DYNAMIC NAMING STRATEGY - COMPREHENSIVE DEMO")
    print("="*80)
    
    try:
        demo_basic_naming_strategy()
        demo_naming_context_from_metadata()
        demo_multi_tenant_scenario()
        demo_rechtsgebiet_separation()
        demo_processing_stages()
        demo_access_levels()
        demo_comparison_static_vs_dynamic()
        demo_integration_with_existing_code()
        
        print_section("✅ ALLE DEMOS ERFOLGREICH")
        
        print("\n📋 ZUSAMMENFASSUNG:")
        print("   • Dynamische Namensgebung basierend auf Behörden-Kontext")
        print("   • Multi-Tenancy Support (verschiedene Kommunen/Länder)")
        print("   • Rechtsgebiete-Trennung")
        print("   • Processing-Stages (Draft, Active, Archive)")
        print("   • Access-Level-Trennung (Public, Internal, Confidential)")
        print("   • Abwärtskompatibel mit bestehendem Code")
        print("   • Opt-In: Kein Breaking Change")
        
        print("\n📚 NÄCHSTE SCHRITTE:")
        print("   1. saga_crud.py anpassen (vector_create, graph_create, etc.)")
        print("   2. uds3_core.py erweitern (_create_vector_operations, etc.)")
        print("   3. Tests schreiben (test_naming_strategy.py)")
        print("   4. Migration-Strategie für bestehende Daten")
        print("   5. Dokumentation aktualisieren")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
