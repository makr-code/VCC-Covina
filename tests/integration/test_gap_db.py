#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Knowledge Gap Database Connection
Quick test to verify PostgreSQL connection and methods work
"""

import sys
from pathlib import Path

# Add Covina root to path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_connection():
    """Test basic database connection and methods"""
    print("="*60)
    print("TESTING KNOWLEDGE GAP DATABASE CONNECTION")
    print("="*60)
    
    try:
        from gap_detection.gap_database import KnowledgeGapDB
        
        print("\n1. Creating database instance...")
        db = KnowledgeGapDB()
        print("   ✅ Database instance created")
        
        print("\n2. Testing get_gaps() method...")
        gaps = db.get_gaps(limit=5)
        print(f"   ✅ Retrieved {len(gaps)} gaps")
        
        print("\n3. Testing get_knowledge_gaps() method (GUI alias)...")
        gaps2 = db.get_knowledge_gaps(limit=5)
        print(f"   ✅ Retrieved {len(gaps2)} gaps via alias")
        
        print("\n4. Testing get_statistics() method...")
        stats = db.get_statistics()
        print(f"   ✅ Statistics: {stats}")
        
        print("\n5. Testing add_gap() method...")
        gap_id = db.add_gap(
            gap_type="test_connection",
            description="Test gap created by connection test",
            severity="low",
            tags=["test", "connection"],
            metadata={"test": True}
        )
        print(f"   ✅ Created test gap with ID: {gap_id}")
        
        if gap_id:
            print("\n6. Testing get_gap() method...")
            gap = db.get_gap(gap_id)
            print(f"   ✅ Retrieved gap: {gap['description'][:50]}...")
            
            print("\n7. Testing update_gap() method...")
            success = db.update_gap(gap_id, status="in_progress")
            print(f"   ✅ Updated gap status: {success}")
            
            print("\n8. Testing resolve_gap() method...")
            success = db.resolve_gap(gap_id, "Test completed successfully")
            print(f"   ✅ Resolved gap: {success}")
            
            print("\n9. Testing get_gap_history() method...")
            history = db.get_gap_history(gap_id)
            print(f"   ✅ Retrieved {len(history)} history entries")
            
            print("\n10. Testing delete_gap() method...")
            success = db.delete_gap(gap_id)
            print(f"   ✅ Deleted gap: {success}")
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED! ✅")
        print("="*60)
        
        db.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
