"""
Direct test of Graph Golden Dataset API with detailed error output
"""

import requests
import json

url = "http://127.0.0.1:45678/graph-golden-dataset"

pattern_data = {
    "pattern_id": "TEST_DEBUG",
    "name": "Test Debug",
    "description": "Debug pattern",
    "category": "workflow",
    "nodes_definition": [{"id": "n1", "label": "Doc"}],
    "relationships_definition": [],
    "status": "active"
}

print("Sending POST request...")
print(f"Data: {json.dumps(pattern_data, indent=2)}")

try:
    response = requests.post(url, json=pattern_data, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS!")
    else:
        print("\n❌ FAILED!")
        # Try to get JSON error details
        try:
            error_json = response.json()
            print(f"Error JSON: {json.dumps(error_json, indent=2)}")
        except:
            pass
            
except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()
