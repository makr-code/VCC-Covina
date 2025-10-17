"""
Integration Test für Graph Pattern API
Testet CRUD-Operationen über HTTP API
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:45678"

def test_list_graph_patterns():
    """Test 1: List all graph patterns"""
    print("\n" + "="*60)
    print("Test 1: GET /graph-golden-dataset (List All)")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/graph-golden-dataset")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Retrieved {len(data.get('patterns', []))} patterns")
        print(f"Total count: {data.get('total', 0)}")
        
        # Show first few patterns
        patterns = data.get('patterns', [])
        for i, pattern in enumerate(patterns[:3]):
            print(f"\nPattern {i+1}:")
            print(f"  - ID: {pattern.get('id')}")
            print(f"  - Name: {pattern.get('name')}")
            print(f"  - Source: {pattern.get('source_node_type')}")
            print(f"  - Target: {pattern.get('target_node_type')}")
            print(f"  - Relationship: {pattern.get('relationship_type')}")
        
        return True
    else:
        print(f"❌ Failed! Response: {response.text}")
        return False

def test_create_graph_pattern():
    """Test 2: Create a new graph pattern"""
    print("\n" + "="*60)
    print("Test 2: POST /graph-golden-dataset (Create)")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pattern_data = {
        "pattern_id": f"TEST_PATTERN_{timestamp}",
        "name": f"Test Pattern {timestamp}",
        "description": f"Test pattern created at {timestamp}",
        "category": "workflow",
        "nodes_definition": [
            {
                "id": "node1",
                "label": "Document",
                "properties": {"type": "invoice"}
            },
            {
                "id": "node2",
                "label": "Person",
                "properties": {"role": "author"}
            }
        ],
        "relationships_definition": [
            {
                "from": "node1",
                "to": "node2",
                "type": "AUTHORED_BY",
                "properties": {"confidence": 0.95}
            }
        ],
        "validation_rules": {
            "min_confidence": 0.9,
            "required_properties": ["type", "role"]
        },
        "created_by": "test_suite",
        "tags": ["test", "automated"],
        "status": "active"
    }
    
    print(f"Creating pattern: {pattern_data['pattern_id']}")
    
    response = requests.post(
        f"{BASE_URL}/graph-golden-dataset",
        json=pattern_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Pattern created")
        print(f"   Pattern ID: {result.get('pattern_id')}")
        print(f"   Database ID: {result.get('id')}")
        print(f"   Message: {result.get('message')}")
        return result.get('id')  # Return database ID for verification
    else:
        print(f"❌ Failed! Response: {response.text}")
        return None

def test_verify_pattern(pattern_id):
    """Test 3: Verify pattern was created"""
    print("\n" + "="*60)
    print("Test 3: Verify Pattern Creation")
    print("="*60)
    
    if not pattern_id:
        print("❌ No pattern ID to verify")
        return False
    
    response = requests.get(f"{BASE_URL}/graph-golden-dataset")
    
    if response.status_code == 200:
        data = response.json()
        patterns = data.get('patterns', [])
        
        # Find our pattern
        found = False
        for pattern in patterns:
            if pattern.get('id') == pattern_id:
                found = True
                print(f"✅ Pattern found in database!")
                print(f"   ID: {pattern.get('id')}")
                print(f"   Name: {pattern.get('name')}")
                print(f"   Source: {pattern.get('source_node_type')}")
                print(f"   Target: {pattern.get('target_node_type')}")
                print(f"   Relationship: {pattern.get('relationship_type')}")
                break
        
        if not found:
            print(f"❌ Pattern {pattern_id} not found in database")
            return False
        
        return True
    else:
        print(f"❌ Failed to retrieve patterns")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Graph Pattern API Integration Test")
    print(f"Backend: {BASE_URL}")
    print("="*60)
    
    # Test 1: List patterns
    test1_result = test_list_graph_patterns()
    
    # Test 2: Create pattern
    pattern_id = test_create_graph_pattern()
    
    # Test 3: Verify creation
    test3_result = test_verify_pattern(pattern_id)
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Test 1 (List): {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"Test 2 (Create): {'✅ PASS' if pattern_id else '❌ FAIL'}")
    print(f"Test 3 (Verify): {'✅ PASS' if test3_result else '❌ FAIL'}")
    
    total = sum([test1_result, bool(pattern_id), test3_result])
    print(f"\nOverall: {total}/3 tests passed")
    
    if total == 3:
        print("🎉 All tests PASSED! Graph Pattern API is operational!")
    else:
        print("⚠️ Some tests failed. Check logs above.")
