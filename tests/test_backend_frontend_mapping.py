#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend-Frontend Endpunkt-Mapping Report
Validiert alle kritischen Endpunkte für Daten-Display
"""
import requests
import json
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Backend URLs
MAIN_BACKEND = "http://127.0.0.1:45678"
INGESTION_BACKEND = "http://127.0.0.1:45679"

def test_endpoint(url, name, timeout=30):
    """Test einzelner Endpunkt"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"Timeout: {timeout}s")
    print("-"*80)
    
    try:
        response = requests.get(url, timeout=timeout)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle list response (e.g. /jobs returns array)
            if isinstance(data, list):
                print(f"Response Type: List with {len(data)} items")
                if len(data) > 0 and isinstance(data[0], dict):
                    print(f"First Item Keys: {list(data[0].keys())}")
            else:
                # Zeige Datenstruktur (erste Ebene)
                print(f"Response Keys: {list(data.keys())}")
                
                # Zeige wichtige Felder
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        if isinstance(value, list):
                            print(f"  - {key}: {len(value)} items")
                        else:
                            print(f"  - {key}: {len(value)} keys")
                    else:
                        print(f"  - {key}: {value}")
        else:
            print(f"Response: {response.text[:200]}")
            
        return True
        
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Teste alle kritischen Endpunkte"""
    
    print("="*80)
    print("BACKEND-FRONTEND ENDPUNKT-VALIDIERUNG")
    print("="*80)
    
    results = {}
    
    # ===== MAIN BACKEND (Port 45678) =====
    print("\n\n" + "="*80)
    print("MAIN BACKEND - Port 45678")
    print("="*80)
    
    # Health Check
    results['main_health'] = test_endpoint(
        f"{MAIN_BACKEND}/health",
        "Main Backend Health Check"
    )
    
    # Database Stats (kritisch für UDS3 Datasets Widget!)
    results['database_stats'] = test_endpoint(
        f"{MAIN_BACKEND}/database/stats",
        "Database Statistics (UDS3 Datasets Widget)"
    )
    
    # UDS3 Status
    results['uds3_status'] = test_endpoint(
        f"{MAIN_BACKEND}/uds3/status",
        "UDS3 Status (Processing Mode)"
    )
    
    # UDS3 Strategy Status
    results['uds3_strategy'] = test_endpoint(
        f"{MAIN_BACKEND}/uds3/strategy/status",
        "UDS3 Strategy Status (Backend Availability)"
    )
    
    # System Stats (für System Status View)
    results['system_stats'] = test_endpoint(
        f"{MAIN_BACKEND}/system/stats",
        "System Statistics (System Status View)"
    )
    
    # Document Search (für Home Dashboard)
    results['document_search'] = test_endpoint(
        f"{MAIN_BACKEND}/documents/search?query=test&limit=5",
        "Document Search (Home Dashboard)"
    )
    
    # ===== INGESTION BACKEND (Port 45679) =====
    print("\n\n" + "="*80)
    print("INGESTION BACKEND - Port 45679")
    print("="*80)
    
    # Health Check
    results['ingestion_health'] = test_endpoint(
        f"{INGESTION_BACKEND}/health",
        "Ingestion Backend Health Check"
    )
    
    # Job List (kritisch für Ingestion View!)
    results['job_list'] = test_endpoint(
        f"{INGESTION_BACKEND}/jobs?limit=10",
        "Job List (Ingestion View)"
    )
    
    # Job Stats
    results['job_stats'] = test_endpoint(
        f"{INGESTION_BACKEND}/jobs/stats",
        "Job Statistics (Ingestion View)"
    )
    
    # ===== ZUSAMMENFASSUNG =====
    print("\n\n" + "="*80)
    print("ZUSAMMENFASSUNG")
    print("="*80)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n✅ Erfolgreiche Endpunkte: {success_count}/{total_count}")
    print(f"❌ Fehlgeschlagene Endpunkte: {total_count - success_count}/{total_count}")
    
    print("\nDetails:")
    for endpoint, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {endpoint}")
    
    # Kritische Endpunkte für Daten-Display
    print("\n" + "="*80)
    print("KRITISCHE ENDPUNKTE FÜR FRONTEND-DATEN-DISPLAY:")
    print("="*80)
    
    critical = {
        'database_stats': 'UDS3 Datasets Widget',
        'job_list': 'Ingestion View (Job Table)',
        'job_stats': 'Ingestion View (Charts)',
        'system_stats': 'System Status View',
        'document_search': 'Home Dashboard (Recent Documents)'
    }
    
    for endpoint, widget in critical.items():
        status = "✅" if results.get(endpoint, False) else "❌"
        print(f"  {status} {endpoint:20s} → {widget}")
    
    # Empfehlungen
    failed_critical = [name for name in critical.keys() if not results.get(name, False)]
    
    if failed_critical:
        print("\n⚠️  WARNUNG: Kritische Endpunkte fehlgeschlagen!")
        print("\nFrontend Widgets mit fehlenden Daten:")
        for endpoint in failed_critical:
            print(f"  - {critical[endpoint]} (Endpunkt: {endpoint})")
    else:
        print("\n✅ Alle kritischen Endpunkte funktionieren!")
        print("   Frontend sollte jetzt alle Daten anzeigen können.")

if __name__ == "__main__":
    main()
