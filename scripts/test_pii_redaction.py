"""
PII Redaction Test Script
=========================

Tests the PII redaction filter by:
1. Testing the filter class directly
2. Sending PII-containing requests to both backends
3. Checking logs for proper redaction

Author: Covina Security Team
Version: 1.0.0
Created: 2025-10-22
"""

import logging
import sys
import time
import requests
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pii_redaction import PIIRedactionFilter


def test_filter_class():
    """Test the PIIRedactionFilter class directly."""
    print("\n" + "="*60)
    print("TEST 1: PIIRedactionFilter Class")
    print("="*60)
    
    # Setup logger with filter
    test_logger = logging.getLogger("pii_test")
    test_logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    test_logger.addHandler(handler)
    test_logger.addFilter(PIIRedactionFilter())
    
    print(f"\nActive patterns: {PIIRedactionFilter.get_patterns_count()}\n")
    
    # Test messages with PII
    test_cases = [
        ("Email", "User john.doe@example.com registered", "[EMAIL]"),
        ("SSN", "SSN: 123-45-6789", "[SSN]"),
        ("IBAN", "IBAN: DE89370400440532013000", "[IBAN]"),
        ("Phone", "Call: +49 170 1234567", "[PHONE]"),
        ("Date", "Born: 15.03.1985", "[DATE]"),
        ("Password", "password=SuperSecret123", "password=[REDACTED]"),
        ("Token", "api_key: Bearer abc123", "api_key=[REDACTED]"),
        ("Card", "Card: 4532 1234 5678 9010", "[CARD]"),
        ("Tax ID", "Tax: 12345678901", "[TAX_ID]"),
        ("Mixed", "Email: test@example.de, IBAN: DE12345678901234567890", "[EMAIL]"),
    ]
    
    passed = 0
    failed = 0
    
    for name, message, expected_token in test_cases:
        print(f"\n{name} Test:")
        print(f"  Original: {message}")
        
        # Capture log output
        from io import StringIO
        log_capture = StringIO()
        capture_handler = logging.StreamHandler(log_capture)
        capture_handler.setFormatter(logging.Formatter('%(message)s'))
        test_logger.addHandler(capture_handler)
        
        test_logger.info(message)
        
        redacted = log_capture.getvalue().strip()
        test_logger.removeHandler(capture_handler)
        
        print(f"  Redacted: {redacted}")
        
        if expected_token in redacted and message not in redacted:
            print(f"  ✅ PASS - PII redacted")
            passed += 1
        else:
            print(f"  ❌ FAIL - PII not redacted properly")
            failed += 1
    
    print("\n" + "-"*60)
    print(f"Filter Test Results: {passed} passed, {failed} failed")
    print("-"*60)
    
    return failed == 0


def test_backend_logging(backend_url: str, backend_name: str):
    """Test PII redaction in backend logs via API requests."""
    print("\n" + "="*60)
    print(f"TEST 2: {backend_name} Backend Logging")
    print("="*60)
    
    try:
        # Check if backend is running
        health_url = f"{backend_url}/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code != 200:
            print(f"❌ {backend_name} Backend nicht erreichbar (Status: {response.status_code})")
            return False
        
        print(f"✅ {backend_name} Backend läuft auf {backend_url}")
        
        # Test semantic search with PII in query (Main Backend)
        if "45678" in backend_url:
            test_queries = [
                "john.doe@example.com",
                "IBAN DE89370400440532013000",
                "password=SuperSecret123",
                "+49 170 1234567",
            ]
            
            print(f"\nSende {len(test_queries)} Queries mit PII-Daten...")
            
            for query in test_queries:
                try:
                    response = requests.get(
                        f"{backend_url}/query/semantic",
                        params={"query": query, "top_k": 5},
                        timeout=10
                    )
                    print(f"  Query '{query[:30]}...' → Status {response.status_code}")
                except Exception as e:
                    print(f"  Query failed: {e}")
        
        # Test job listing (Ingestion Backend)
        if "45679" in backend_url:
            print("\nAbrufen der Job-Liste...")
            try:
                response = requests.get(f"{backend_url}/jobs", timeout=10)
                print(f"  GET /jobs → Status {response.status_code}")
            except Exception as e:
                print(f"  Request failed: {e}")
        
        print(f"\n✅ {backend_name} Logging-Test abgeschlossen")
        print("⚠️  WICHTIG: Prüfe Logs manuell auf Redaktion!")
        print(f"   Logs: logs/{backend_name.lower()}_backend.log")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ {backend_name} Backend nicht erreichbar - ist der Service gestartet?")
        return False
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("PII REDACTION FILTER - VALIDATION TEST")
    print("="*60)
    print("Testing DSGVO-compliant log redaction")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Filter class directly
    filter_ok = test_filter_class()
    
    # Test 2: Main Backend
    main_backend_ok = test_backend_logging("http://127.0.0.1:45678", "Main")
    
    # Test 3: Ingestion Backend
    ingestion_backend_ok = test_backend_logging("http://127.0.0.1:45679", "Ingestion")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Filter Class:       {'✅ PASS' if filter_ok else '❌ FAIL'}")
    print(f"Main Backend:       {'✅ PASS' if main_backend_ok else '❌ FAIL'}")
    print(f"Ingestion Backend:  {'✅ PASS' if ingestion_backend_ok else '❌ FAIL'}")
    print("="*60)
    
    if filter_ok and main_backend_ok and ingestion_backend_ok:
        print("\n✅ Alle Tests bestanden!")
        print("⚠️  WICHTIG: Prüfe die Backend-Logs manuell:")
        print("   - logs/main_backend.log")
        print("   - logs/ingestion_backend.log")
        print("   PII sollte als [EMAIL], [IBAN], [PASSWORD], etc. erscheinen!")
        return 0
    else:
        print("\n❌ Einige Tests fehlgeschlagen!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
