#!/usr/bin/env python3
"""Test Neo4j Backend Initialization"""

import sys
import logging
sys.path.insert(0, 'C:\\VCC\\uds3')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from uds3.core.polyglot_manager import UDS3PolyglotManager

# Config
config = {
    'relational': {'enabled': True},
    'vector': {'enabled': True},
    'graph': {'enabled': True},
    'file': {'enabled': True}
}

print("=" * 80)
print("TEST: UDS3 PolyglotManager Neo4j Backend")
print("=" * 80)

# Initialize
mgr = UDS3PolyglotManager(backend_config=config, enable_rag=False)

# Check Graph Backend
gb = mgr.db_manager.get_graph_backend()

print(f"\nGraph Backend: {gb}")
print(f"Has driver: {hasattr(gb, 'driver')}")

if hasattr(gb, 'driver'):
    print(f"Driver: {gb.driver}")
    print(f"Driver connected: {gb.driver is not None}")
    
    if gb.driver:
        try:
            gb.driver.verify_connectivity()
            print("✅ Neo4j Driver CONNECTED!")
        except Exception as e:
            print(f"❌ Neo4j Driver ERROR: {e}")
else:
    print("❌ NO DRIVER ATTRIBUTE!")

print("=" * 80)
