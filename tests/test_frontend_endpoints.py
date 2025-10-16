#!/usr/bin/env python3
"""
Frontend API Endpoint Test
===========================

Testet alle Frontend-Endpunkte und zeigt die Datenstruktur

Datum: 13. Oktober 2025
"""

import requests
import json
from pprint import pprint

# Konfiguration
BACKEND_URL = "http://127.0.0.1:45678"
INGESTION_URL = "http://127.0.0.1:45679"

def test_endpoint(url, name):
    """Teste einen Endpunkt"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('='*80)
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nData Structure:")
            pprint(data, depth=3, width=120)
            
            # Show top-level keys
            if isinstance(data, dict):
                print(f"\nTop-Level Keys: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"\nList Length: {len(data)}")
                if len(data) > 0:
                    print(f"First Item Keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
        else:
            print(f"Error: {response.text}")
    
    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    """Teste alle wichtigen Endpunkte"""
    
    print("="*80)
    print("COVINA FRONTEND API ENDPOINT TEST")
    print("="*80)
    
    # Main Backend Endpoints
    print("\n\n" + "="*80)
    print("MAIN BACKEND (Port 45678)")
    print("="*80)
    
    test_endpoint(f"{BACKEND_URL}/health", "Health Check")
    test_endpoint(f"{BACKEND_URL}/database/stats", "Database Stats (UDS3)")
    test_endpoint(f"{BACKEND_URL}/uds3/status", "UDS3 Status")
    test_endpoint(f"{BACKEND_URL}/uds3/strategy/status", "UDS3 Strategy Status")
    
    # Ingestion Backend Endpoints
    print("\n\n" + "="*80)
    print("INGESTION BACKEND (Port 45679)")
    print("="*80)
    
    test_endpoint(f"{INGESTION_URL}/health", "Health Check")
    test_endpoint(f"{INGESTION_URL}/jobs?limit=10", "List Jobs (limit=10)")
    
    # Summary
    print("\n\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print("\n📊 Check the output above for:")
    print("  1. Missing data fields")
    print("  2. Incorrect data structure")
    print("  3. Empty values where data expected")
    print("\n💡 Compare with frontend expectations in:")
    print("  - frontend/widgets/uds3_dataset_widget.py")
    print("  - frontend/views/ingestion_view.py")
    print("  - frontend/services/api_client.py")
    print()

if __name__ == "__main__":
    main()
