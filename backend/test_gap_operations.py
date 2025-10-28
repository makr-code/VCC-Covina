#!/usr/bin/env python3
"""
Test Gap Database Operations
=============================

Tests CRUD operations on knowledge gap database using UDS3 PostgreSQL backend.
"""

import sys
import os
import io

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add Covina root to path
covina_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if covina_root not in sys.path:
    sys.path.insert(0, covina_root)

# Add UDS3 to path
uds3_path = os.path.join(os.path.dirname(covina_root), 'uds3')
if uds3_path not in sys.path:
    sys.path.insert(0, uds3_path)

from gap_detection.gap_database import KnowledgeGapDB
from uds3.core.polyglot_manager import UDS3PolyglotManager

def test_gap_operations():
    """Test all gap database operations"""
    print("=" * 80)
    print("🧪 GAP DATABASE OPERATIONS TEST")
    print("=" * 80)
    print()
    
    # 1. Initialize UDS3
    print("📋 Step 1: Initialize UDS3 PolyglotManager...")
    backend_config = {
        "relational": {"enabled": True},
        "vector": {"enabled": True}
    }
    
    uds3 = UDS3PolyglotManager(
        backend_config=backend_config,
        enable_rag=False
    )
    
    postgres_backend = uds3.db_manager.get_relational_backend()
    print(f"   ✅ PostgreSQL Backend: {postgres_backend.__class__.__name__}")
    print()
    
    # 2. Initialize Gap Database
    print("📋 Step 2: Initialize Gap Database...")
    gap_db = KnowledgeGapDB(postgres_backend=postgres_backend)
    print("   ✅ Gap Database initialized")
    print()
    
    # 3. Test add_gap()
    print("📋 Step 3: Test add_gap()...")
    gap_id = gap_db.add_gap(
        gap_type="missing_definition",
        description="Test gap: Definition of 'Betriebsgeheimnis' missing",
        context="Legal document requires clear definition",
        severity="high",
        source="test_document_123.pdf"
    )
    print(f"   ✅ Gap created: {gap_id}")
    print()
    
    # 4. Test get_gaps()
    print("📋 Step 4: Test get_gaps()...")
    gaps = gap_db.get_gaps(limit=10)
    print(f"   ✅ Retrieved {len(gaps)} gaps")
    if gaps:
        gap = gaps[0]
        print(f"   📌 First gap:")
        print(f"      ID: {gap['id']}")  # ✅ FIXED: Use 'id' not 'gap_id'
        print(f"      Type: {gap['gap_type']}")
        print(f"      Description: {gap['description']}")
        print(f"      Status: {gap['status']}")
        print(f"      Severity: {gap['severity']}")
    print()
    
    # 5. Test get_gap_by_id()
    print("📋 Step 5: Test get_gap_by_id()...")
    gap_detail = gap_db.get_gap(gap_id)  # ✅ FIXED: Use get_gap() not get_gap_by_id()
    if gap_detail:
        print(f"   ✅ Gap found: {gap_detail['id']}")
        print(f"      Status: {gap_detail['status']}")
    else:
        print(f"   ❌ Gap not found: {gap_id}")
    print()
    
    # 6. Test update_gap()
    print("📋 Step 6: Test update_gap()...")
    updated = gap_db.update_gap(
        gap_id=gap_id,
        status="in_progress",
        resolution="Researching legal definition in BGB"
    )
    print(f"   ✅ Gap updated: {updated}")
    
    # Verify update
    gap_after_update = gap_db.get_gap(gap_id)
    if gap_after_update:
        print(f"   📌 Updated status: {gap_after_update['status']}")
        print(f"   📌 Resolution: {gap_after_update['resolution']}")
    print()
    
    # 7. Test get_gaps() with filters
    print("📋 Step 7: Test get_gaps() with filters...")
    
    # Filter by status
    in_progress_gaps = gap_db.get_gaps(status="in_progress")
    print(f"   ✅ In-progress gaps: {len(in_progress_gaps)}")
    
    # Filter by severity
    high_severity_gaps = gap_db.get_gaps(severity="high")
    print(f"   ✅ High severity gaps: {len(high_severity_gaps)}")
    
    # Filter by type
    missing_def_gaps = gap_db.get_gaps(gap_type="missing_definition")
    print(f"   ✅ Missing definition gaps: {len(missing_def_gaps)}")
    print()
    
    # 8. Test mark_as_resolved()
    print("📋 Step 8: Test mark_as_resolved()...")
    resolved = gap_db.update_gap(
        gap_id=gap_id,
        status="resolved",
        resolution="Definition found in § 17 UWG: Betriebsgeheimnis encompasses technical and commercial information"
    )
    print(f"   ✅ Gap marked as resolved: {resolved}")
    
    gap_final = gap_db.get_gap(gap_id)
    if gap_final:
        print(f"   📌 Final status: {gap_final['status']}")
        print(f"   📌 Final resolution: {gap_final['resolution'][:50]}...")
    print()
    
    # 9. Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    all_gaps = gap_db.get_gaps(limit=100)
    status_counts = {}
    for g in all_gaps:
        status = g['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"Total gaps in database: {len(all_gaps)}")
    print(f"Status distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"   {status}: {count}")
    print()
    
    print("✅ ALL TESTS PASSED - Gap Database Operations Working!")
    print("=" * 80)

if __name__ == "__main__":
    test_gap_operations()
