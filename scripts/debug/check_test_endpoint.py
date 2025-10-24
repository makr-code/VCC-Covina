"""
Test the new test endpoint
"""

import requests
import json

url = "http://127.0.0.1:45678/test-graph-pattern"

pattern_data = {
    "pattern_id": "TEST_SIMPLE",
    "name": "Test Name",
    "description": "Test",
    "category": "workflow",
    "nodes_definition": [{"id": "n1"}],
    "relationships_definition": [],
    "status": "active"
}

print(f"Testing {url}")
response = requests.post(url, json=pattern_data, timeout=30)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    print("\n[OK] Test endpoint works!")
else:
    print(f"\n[FAIL] Test endpoint also fails!")
