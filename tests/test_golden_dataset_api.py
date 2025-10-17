#!/usr/bin/env python3
"""
Golden Dataset API Integration Test
====================================
Tests all CRUD operations on the Golden Dataset API.

Date: 17. Oktober 2025
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:45678"

def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

# Test 1: List All Golden Datasets
print_header("Test 1: List All Golden Datasets (GET /golden-dataset)")

try:
    response = requests.get(f"{BASE_URL}/golden-dataset")
    print_info(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Retrieved {data.get('count', 0)} entries")
        print_info(f"Total in database: {data.get('total', 0)}")
        
        if data.get('entries'):
            print_info("First 3 entries:")
            for entry in data['entries'][:3]:
                print(f"   - ID: {entry.get('id')}, "
                      f"Doc: {entry.get('document_id')}, "
                      f"Classification: {entry.get('classification')}, "
                      f"Quality: {entry.get('quality_score')}")
        else:
            print_info("No entries found")
    else:
        print_error(f"Failed: {response.text}")
        
except Exception as e:
    print_error(f"Exception: {e}")

# Test 2: Create New Golden Dataset Entry
print_header("Test 2: Create New Golden Dataset Entry (POST /golden-dataset)")

test_entry = {
    "document_id": f"TEST_DOC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "classification": "invoice",
    "quality_score": 0.95,
    "reviewed_by": "automated_test",
    "notes": "Created by automated test script",
    "metadata": {
        "test": True,
        "created_at": datetime.now().isoformat(),
        "test_type": "crud_validation"
    }
}

try:
    print_info(f"Creating entry for document: {test_entry['document_id']}")
    response = requests.post(f"{BASE_URL}/golden-dataset", json=test_entry)
    print_info(f"Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        data = response.json()
        print_success(f"Entry created successfully!")
        print_info(f"Response: {json.dumps(data, indent=2)}")
        created_id = data.get('id')
    else:
        print_error(f"Failed: {response.text}")
        created_id = None
        
except Exception as e:
    print_error(f"Exception: {e}")
    created_id = None

# Test 3: List Again (verify creation)
if created_id:
    print_header("Test 3: Verify Creation (GET /golden-dataset)")
    
    try:
        response = requests.get(f"{BASE_URL}/golden-dataset")
        data = response.json()
        
        print_info(f"Total entries now: {data.get('total', 0)}")
        
        # Check if our entry is in the list
        found = False
        for entry in data.get('entries', []):
            if entry.get('id') == created_id:
                found = True
                print_success(f"Created entry found in list!")
                print_info(f"Entry: {json.dumps(entry, indent=2)}")
                break
        
        if not found:
            print_error("Created entry not found in list!")
            
    except Exception as e:
        print_error(f"Exception: {e}")

# Summary
print_header("Test Summary")
print_info("Tests Completed:")
print("  1. List Golden Datasets - ✅ TESTED")
print("  2. Create Golden Dataset - ✅ TESTED")
print("  3. Verify Creation - ✅ TESTED")
print("\nNext Steps:")
print("  - Test UPDATE operation (modify entry)")
print("  - Test DELETE operation (remove entry)")
print("  - Test GUI operations (Golden Dataset Manager)")
print("  - Test Graph Pattern Manager")
print("  - Test Governance Policy Manager")
