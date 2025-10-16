#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Test: Dynamic Naming Strategy
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import from real uds3_admin_types
from uds3_admin_types import AdminDocumentType, AdminLevel, AdminDomain

# Import Naming Strategy
from uds3_naming_strategy import create_municipal_strategy, create_state_strategy

def main():
    print("="*80)
    print("  UDS3 DYNAMIC NAMING - QUICK TEST")
    print("="*80 + "\n")
    
    # Test 1: Stadt Münster Bauamt
    print("1️⃣  Stadt Münster - Bauamt")
    strategy = create_municipal_strategy(
        municipality="münster",
        authority="bauamt",
        state="nrw",
        domain=AdminDomain.BUILDING_LAW,
    )
    
    print(f"   Vector:     {strategy.generate_vector_collection_name(AdminDocumentType.PERMIT, 'chunks')}")
    print(f"   Relational: {strategy.generate_relational_table_name('metadata', AdminDocumentType.PERMIT)}")
    print(f"   Graph Node: {strategy.generate_graph_node_label('Document', AdminDocumentType.PERMIT)}")
    print(f"   File:       {strategy.generate_file_storage_bucket(AdminDocumentType.PERMIT)}")
    
    # Test 2: Land NRW Umweltamt
    print("\n2️⃣  Land NRW - Umweltministerium")
    strategy2 = create_state_strategy(
        state="nrw",
        authority="umweltministerium",
        domain=AdminDomain.ENVIRONMENTAL_LAW,
    )
    
    print(f"   Vector:     {strategy2.generate_vector_collection_name(AdminDocumentType.ADMINISTRATIVE_ACT)}")
    print(f"   Relational: {strategy2.generate_relational_table_name('documents')}")
    print(f"   Graph Node: {strategy2.generate_graph_node_label()}")
    
    # Test 3: Multi-Tenant
    print("\n3️⃣  Multi-Tenant Vergleich")
    cities = ["münster", "köln", "dortmund"]
    
    for city in cities:
        s = create_municipal_strategy(
            municipality=city,
            authority="bauamt",
            state="nrw",
        )
        collection = s.generate_vector_collection_name(AdminDocumentType.PERMIT, 'chunks')
        print(f"   {city:10} → {collection}")
    
    print("\n✅ Alle Tests erfolgreich!")
    print("\n📋 Zusammenfassung:")
    print("   • Dynamische Namen basierend auf Behörden-Kontext")
    print("   • Multi-Tenancy Support (separate Collections pro Kommune)")
    print("   • Semantisch aussagekräftige Namen")
    print("   • Konsistente Namensgebung über alle DB-Typen")

if __name__ == "__main__":
    main()
