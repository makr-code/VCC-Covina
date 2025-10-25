#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test if UDS3 PolyglotManager can create PostgreSQL backend"""

import sys
import io
import logging

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.WARNING)

try:
    from uds3.core.polyglot_manager import UDS3PolyglotManager
    
    backend_config = {
        "relational": {"enabled": True}
    }
    
    print("Creating UDS3PolyglotManager...")
    manager = UDS3PolyglotManager(backend_config=backend_config, enable_rag=False)
    
    print("\n[OK] UDS3PolyglotManager created")
    print(f"   db_manager type: {type(manager.db_manager)}")
    print(f"   db_manager module: {type(manager.db_manager).__module__}")
    print(f"   db_manager attributes: {dir(manager.db_manager)[:10]}")
    
    # Check if databases attribute exists
    if hasattr(manager.db_manager, 'databases'):
        print(f"   databases attribute: EXISTS ({len(manager.db_manager.databases)} items)")
    else:
        print(f"   databases attribute: MISSING!")
    
    # Check if method exists
    if hasattr(manager.db_manager, 'get_relational_backend'):
        print(f"   get_relational_backend method: EXISTS")
    else:
        print(f"   get_relational_backend method: MISSING!")
    
    # Check if relational_backend attribute exists
    if hasattr(manager.db_manager, 'relational_backend'):
        print(f"   relational_backend attribute: EXISTS ({manager.db_manager.relational_backend})")
    else:
        print(f"   relational_backend attribute: MISSING!")
    
    # Check start_all_backends was called
    print(f"\n_backends_to_start: {manager.db_manager._backends_to_start}")
    
    print("\nCalling get_relational_backend()...")
    postgres_backend = manager.db_manager.get_relational_backend()
    
    if postgres_backend:
        print(f"[SUCCESS] ✅ PostgreSQL Backend CONNECTED!")
        print(f"   Backend class: {type(postgres_backend).__name__}")
        print(f"   Backend object: {postgres_backend}")
        print(f"   Has connection_pool: {hasattr(postgres_backend, 'connection_pool')}")
        
        # Test connectivity
        try:
            if hasattr(postgres_backend, 'connection_pool'):
                stats = postgres_backend.connection_pool.get_stats()
                print(f"   Pool stats: {stats}")
                print("\n🎉 SUCCESS! Backend is fully operational!")
        except Exception as e:
            print(f"   Connectivity test failed: {e}")
    else:
        print(f"[ERROR] PostgreSQL Backend: None")
        print("   Backend registered but not started?")
        print(f"   Autostart enabled: {manager.db_manager.autostart}")
        
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
