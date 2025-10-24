"""
Test with detailed error capture and logging
"""

import requests
import json
import time
import subprocess

# Start a log tail in background
print("Starting log monitoring...")

# Make the request
url = "http://127.0.0.1:45678/graph-golden-dataset"

pattern_data = {
    "pattern_id": f"TEST_DETAILED_{int(time.time())}",
    "name": "Test Detailed Error",
    "description": "Test to capture detailed error",
    "category": "workflow",
    "nodes_definition": [{"id": "n1", "label": "Doc"}],
    "relationships_definition": [],
    "status": "active"
}

print(f"\nSending POST to {url}")
print(f"Pattern ID: {pattern_data['pattern_id']}")

try:
    response = requests.post(url, json=pattern_data, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    print(f"Response Headers: {dict(response.headers)}")
    
    # Try to parse as JSON
    try:
        json_response = response.json()
        print(f"\nJSON Response: {json.dumps(json_response, indent=2)}")
    except:
        print("\nCouldn't parse as JSON")
        
except requests.exceptions.Timeout:
    print("\n[FAIL] Request timed out!")
except Exception as e:
    print(f"\n[FAIL] Exception: {e}")
    import traceback
    traceback.print_exc()

# Now check the database to see if it was created
print("\n" + "="*60)
print("Checking database...")
print("="*60)

import psycopg

try:
    conn = psycopg.connect(
        host='192.168.178.94',
        port=5432,
        user='postgres',
        password='postgres',
        dbname='postgres',
        connect_timeout=5
    )
    
    cur = conn.cursor()
    cur.execute(
        "SELECT pattern_id, name FROM graph_golden_dataset WHERE pattern_id = %s",
        (pattern_data['pattern_id'],)
    )
    
    row = cur.fetchone()
    
    if row:
        print(f"[OK] Pattern found in database!")
        print(f"   Pattern ID: {row[0]}")
        print(f"   Name: {row[1]}")
        print("\n[CONCLUSION] CREATE works, but response fails!")
    else:
        print(f"[FAIL] Pattern NOT found in database")
        print("\n[CONCLUSION] CREATE completely failed")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"[FAIL] DB Error: {e}")
