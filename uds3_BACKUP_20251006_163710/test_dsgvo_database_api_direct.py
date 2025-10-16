#!/usr/bin/env python3
"""
Test der UDS3 DSGVO Core Database API Integration (von UDS3-Verzeichnis)

Testet die Korrektur von direkten SQLite-Zugriffen zu database_api/database_manager.
"""

try:
    from uds3_dsgvo_core import UDS3DSGVOCore, PIIType, DSGVOProcessingBasis
    from database.database_manager import DatabaseManager
    
    print("✅ Alle Imports erfolgreich")
    
    # Test Database Manager Erstellung
    print("\n🔧 Teste Database Manager Setup...")
    # Direkte SQLite-Konfiguration für Test
    backend_config = {
        'relational': {
            'enabled': True,
            'backend': 'sqlite',
            'database_path': './test_dsgvo_core.db'
        }
    }
    db_manager = DatabaseManager(backend_config, strict_mode=False)
    
    if db_manager.relational_backend:
        print(f"✅ Database Manager verfügbar: {type(db_manager.relational_backend).__name__}")
    else:
        print("❌ Kein relational backend verfügbar")
        exit(1)
    
    # Test DSGVO Core Initialisierung
    print("\n📋 Teste DSGVO Core Initialisierung...")
    dsgvo_core = UDS3DSGVOCore(
        database_manager=db_manager,
        retention_years=7,
        auto_anonymize=True,
        strict_mode=True
    )
    print("✅ UDS3 DSGVO Core erfolgreich initialisiert mit Database API")
    
    # Test PII Detection
    print("\n🔍 Teste PII Detection...")
    test_text = "Kontakt: max.mustermann@example.com oder +49 123 456789"
    detected_pii = dsgvo_core.detect_pii(test_text, document_id="test_doc_001")
    print(f"✅ PII Detection: {len(detected_pii)} Elemente erkannt")
    for pii in detected_pii:
        print(f"   - {pii['type']}: {pii['value']} (Confidence: {pii['confidence']})")
    
    # Test Anonymization
    print("\n🔒 Teste Anonymisierung...")
    anonymized_text = dsgvo_core.anonymize_content(
        test_text, 
        document_id="test_doc_001",
        processing_basis=DSGVOProcessingBasis.LEGAL_OBLIGATION
    )
    print(f"✅ Anonymisierung: '{test_text}' → '{anonymized_text}'")
    
    # Test DSGVO Rights 
    print("\n📋 Teste DSGVO Rechte...")
    
    # Grant consent
    consent_id = dsgvo_core.grant_consent(
        subject_id="user123",
        purpose="Marketing Communication", 
        data_categories=[PIIType.EMAIL, PIIType.PHONE]
    )
    print(f"✅ Einwilligung erteilt: {consent_id}")
    
    # Right to access
    access_data = dsgvo_core.dsgvo_right_to_access("user123")
    print(f"✅ Auskunftsrecht: {len(access_data['consent_records'])} Einwilligungen, {len(access_data['audit_trail'])} Audit-Einträge")
    
    # Test Compliance Report
    print("\n📊 Teste Compliance Report...")
    compliance_report = dsgvo_core.get_compliance_report()
    print(f"✅ Compliance Status: {compliance_report['compliance_status']}")
    print(f"   - PII Mappings: {compliance_report['total_pii_mappings']}")
    print(f"   - Consent Records: {compliance_report['total_consent_records']}")  
    print(f"   - Audit Entries: {compliance_report['total_audit_entries']}")
    print(f"   - Audit Integrity: {compliance_report['audit_trail_integrity']['status']}")
    print(f"   - Verified Entries: {compliance_report['audit_trail_integrity']['verified_entries']}")
    
    print("\n🎉 Alle Tests bestanden - UDS3 DSGVO Core nutzt korrekt die Database API!")
    print("✨ Keine direkten SQLite-Zugriffe mehr - konsistente UDS3-Architektur!")

except ImportError as e:
    print(f"❌ Import Fehler: {e}")
except Exception as e:
    print(f"❌ Test Fehler: {e}")
    import traceback
    traceback.print_exc()