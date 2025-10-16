#!/usr/bin/env python3
"""
Test einzelner Backend-Endpoint mit längerem Timeout
"""
import requests
import json

# Test /database/stats mit 30s Timeout
url = "http://127.0.0.1:45678/database/stats"

print(f"Testing: {url}")
print(f"Timeout: 30 seconds")
print("="*80)

try:
    response = requests.get(url, timeout=30)
    print(f"✅ Status: {response.status_code}")
    print("\nResponse Data:")
    print(json.dumps(response.json(), indent=2))
except requests.exceptions.Timeout:
    print(f"❌ TIMEOUT after 30 seconds")
except Exception as e:
    print(f"❌ ERROR: {e}")
