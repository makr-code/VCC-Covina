#!/usr/bin/env python3
"""
UDS3 DSGVO Core Integration

Zentrale DSGVO-Compliance Implementation für den UDS3 Core.
Stellt sicher, dass alle Datenabrufe DSGVO-konform sind.

Features:
- Anonymisierung/Pseudonymisierung auf UDS3-Ebene
- Right-to-be-forgotten Implementation
- Consent-Management Integration  
- Data-Portability für DSGVO-Export
- Automatische PII-Erkennung und -Behandlung
- Audit-Trail für alle DSGVO-relevanten Operationen

Nutzt database_api für konsistente UDS3-Architektur.
"""

import uuid
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Literal
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

# UDS3 Database API Import
try:
    from database.database_manager import DatabaseManager
    from database import config as db_config
    DATABASE_API_AVAILABLE = True
except ImportError:
    DATABASE_API_AVAILABLE = False
    logger.warning("Database API nicht verfügbar - DSGVO Core läuft im Fallback-Modus")

logger = logging.getLogger(__name__)


class DSGVOOperationType(Enum):
    """DSGVO-relevante Operationstypen"""
    ANONYMIZE = "anonymize"
    PSEUDONYMIZE = "pseudonymize" 
    DELETE = "delete"
    EXPORT = "export"
    ACCESS_REQUEST = "access_request"
    CONSENT_GRANT = "consent_grant"
    CONSENT_REVOKE = "consent_revoke"
    PII_DETECTION = "pii_detection"


class PIIType(Enum):
    """Typen von personenbezogenen Daten (PII)"""
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    ID_NUMBER = "id_number" 
    BIRTHDATE = "birthdate"
    IP_ADDRESS = "ip_address"
    CUSTOM = "custom"


class DSGVOProcessingBasis(Enum):
    """DSGVO Rechtsgrundlagen für Datenverarbeitung (Art. 6 DSGVO)"""
    CONSENT = "consent"              # Einwilligung (Art. 6 Abs. 1 lit. a)
    CONTRACT = "contract"            # Vertragserfüllung (Art. 6 Abs. 1 lit. b)
    LEGAL_OBLIGATION = "legal_obligation"  # Rechtliche Verpflichtung (Art. 6 Abs. 1 lit. c)  
    VITAL_INTERESTS = "vital_interests"    # Lebenswichtige Interessen (Art. 6 Abs. 1 lit. d)
    PUBLIC_TASK = "public_task"      # Öffentliche Aufgabe (Art. 6 Abs. 1 lit. e)
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Berechtigte Interessen (Art. 6 Abs. 1 lit. f)


@dataclass
class PIIMapping:
    """Mapping von Original-PII zu anonymisierten/pseudonymisierten Werten"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_value: str = ""
    anonymized_value: str = ""
    pii_type: PIIType = PIIType.CUSTOM
    source_document_id: Optional[str] = None
    processing_basis: DSGVOProcessingBasis = DSGVOProcessingBasis.LEGAL_OBLIGATION
    consent_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    retention_until: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)


@dataclass 
class DSGVOConsentRecord:
    """DSGVO-Einwilligungsdatensatz"""
    consent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject_id: str = ""  # Betroffene Person
    purpose: str = ""  # Verarbeitungszweck
    processing_basis: DSGVOProcessingBasis = DSGVOProcessingBasis.CONSENT
    granted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    revoked_at: Optional[str] = None
    valid_until: Optional[str] = None
    data_categories: List[PIIType] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DSGVOAuditEntry:
    """DSGVO-Audit-Log-Eintrag"""
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: DSGVOOperationType = DSGVOOperationType.PII_DETECTION
    subject_id: Optional[str] = None
    document_id: Optional[str] = None
    processing_basis: DSGVOProcessingBasis = DSGVOProcessingBasis.LEGAL_OBLIGATION
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    performed_by: str = "uds3_system"
    details: Dict[str, Any] = field(default_factory=dict)
    legal_basis_reference: Optional[str] = None
    hash: Optional[str] = None


class UDS3DSGVOCore:
    """
    Zentrale DSGVO-Compliance Engine für UDS3.
    
    Verantwortlich für:
    - PII-Erkennung und -Behandlung in allen UDS3-Operationen
    - Anonymisierung/Pseudonymisierung auf Core-Ebene  
    - DSGVO-Rechte (Auskunft, Berichtigung, Löschung, Übertragbarkeit)
    - Einwilligungsmanagement
    - Vollständiges Audit-Logging
    """
    
    def __init__(
        self, 
        database_manager: Optional[DatabaseManager] = None,
        retention_years: int = 7,
        auto_anonymize: bool = True,
        strict_mode: bool = True
    ):
        # Initialize Database Manager
        if database_manager:
            self.db_manager = database_manager
        else:
            # Create from config
            if DATABASE_API_AVAILABLE:
                backend_config = db_config.get_database_config()
                self.db_manager = DatabaseManager(backend_config, strict_mode=False)
            else:
                logger.error("Database API nicht verfügbar - DSGVO Core kann nicht initialisiert werden")
                raise ImportError("Database API für DSGVO Core erforderlich")
        
        self.retention_years = retention_years
        self.auto_anonymize = auto_anonymize
        self.strict_mode = strict_mode
        
        # Initialize database tables
        self._init_database()
        
        # PII Detection patterns (basic implementation)
        self.pii_patterns = {
            PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            PIIType.PHONE: r'\b(\+49|0)\s*\d+[\s\-\d]+\b',
            PIIType.IP_ADDRESS: r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        }
        
        logger.info("UDS3 DSGVO Core initialized with Database API")
    
    def _get_backend(self):
        """Helper für sicheren Database-Backend-Zugriff"""
        if not self.db_manager or not self.db_manager.relational_backend:
            raise RuntimeError("Kein relational backend verfügbar für DSGVO Operations")
        return self.db_manager.relational_backend
    
    def _init_database(self):
        """Initialisiert die DSGVO-Tabellen über Database API"""
        if not self.db_manager.relational_backend:
            logger.error("Kein relational backend verfügbar für DSGVO Tables")
            return
            
        backend = self.db_manager.relational_backend
        
        # PII Mappings Table
        pii_mappings_schema = {
            'id': 'TEXT PRIMARY KEY',
            'original_value_hash': 'TEXT NOT NULL',
            'anonymized_value': 'TEXT NOT NULL',
            'pii_type': 'TEXT NOT NULL',
            'source_document_id': 'TEXT',
            'processing_basis': 'TEXT NOT NULL',
            'consent_id': 'TEXT',
            'created_at': 'TEXT NOT NULL',
            'retention_until': 'TEXT',
            'audit_trail': 'TEXT'
        }
        backend.create_table('pii_mappings', pii_mappings_schema)
        
        # Consent Records Table  
        consent_schema = {
            'consent_id': 'TEXT PRIMARY KEY',
            'subject_id': 'TEXT NOT NULL',
            'purpose': 'TEXT NOT NULL',
            'processing_basis': 'TEXT NOT NULL',
            'granted_at': 'TEXT NOT NULL',
            'revoked_at': 'TEXT',
            'valid_until': 'TEXT',
            'data_categories': 'TEXT',
            'metadata': 'TEXT'
        }
        backend.create_table('consent_records', consent_schema)
        
        # Audit Trail Table
        audit_schema = {
            'audit_id': 'TEXT PRIMARY KEY',
            'operation': 'TEXT NOT NULL',
            'subject_id': 'TEXT',
            'document_id': 'TEXT',
            'processing_basis': 'TEXT NOT NULL',
            'timestamp': 'TEXT NOT NULL',
            'performed_by': 'TEXT NOT NULL',
            'details': 'TEXT',
            'legal_basis_reference': 'TEXT',
            'hash': 'TEXT'
        }
        backend.create_table('dsgvo_audit', audit_schema)
        
        # Indices für Performance (über SQL wenn unterstützt)
        try:
            backend.execute_query("CREATE INDEX IF NOT EXISTS idx_pii_source_doc ON pii_mappings(source_document_id)")
            backend.execute_query("CREATE INDEX IF NOT EXISTS idx_pii_type ON pii_mappings(pii_type)")
            backend.execute_query("CREATE INDEX IF NOT EXISTS idx_consent_subject ON consent_records(subject_id)")
            backend.execute_query("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON dsgvo_audit(timestamp)")
            backend.execute_query("CREATE INDEX IF NOT EXISTS idx_audit_operation ON dsgvo_audit(operation)")
        except Exception as e:
            logger.warning(f"DSGVO Index creation failed (non-critical): {e}")
    
    # ========================= PII DETECTION & ANONYMIZATION =========================
    
    def detect_pii(self, content: Union[str, Dict[str, Any]], document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Erkennt PII in Inhalten (Text oder strukturierte Daten).
        
        Args:
            content: Text oder strukturierte Daten zur Analyse
            document_id: Optional document ID für Audit-Trail
            
        Returns:
            List[Dict]: Erkannte PII-Elemente mit Typ und Position
        """
        detected_pii = []
        
        # Text-basierte Erkennung
        if isinstance(content, str):
            import re
            for pii_type, pattern in self.pii_patterns.items():
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    detected_pii.append({
                        "type": pii_type.value,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.9
                    })
        
        # Strukturierte Daten-Erkennung
        elif isinstance(content, dict):
            pii_fields = {
                "email", "e-mail", "mail", "e_mail",
                "phone", "telefon", "tel", "telephone", "mobile",
                "name", "vorname", "nachname", "full_name",
                "address", "adresse", "strasse", "street",
                "ip", "ip_address", "ip_addr"
            }
            
            for key, value in content.items():
                if isinstance(value, str) and any(field in key.lower() for field in pii_fields):
                    detected_pii.append({
                        "type": self._guess_pii_type(key, value).value,
                        "field": key,
                        "value": value,
                        "confidence": 0.8
                    })
        
        # Audit-Log erstellen
        if detected_pii:
            self._create_audit_entry(
                operation=DSGVOOperationType.PII_DETECTION,
                document_id=document_id,
                details={
                    "pii_count": len(detected_pii),
                    "pii_types": list(set(item["type"] for item in detected_pii))
                }
            )
        
        return detected_pii
    
    def anonymize_content(
        self, 
        content: Union[str, Dict[str, Any]], 
        document_id: Optional[str] = None,
        processing_basis: DSGVOProcessingBasis = DSGVOProcessingBasis.LEGAL_OBLIGATION
    ) -> Union[str, Dict[str, Any]]:
        """
        Anonymisiert PII in Inhalten.
        
        Args:
            content: Inhalt zur Anonymisierung
            document_id: Document ID für Audit-Trail
            processing_basis: DSGVO-Rechtsgrundlage
            
        Returns:
            Anonymisierter Inhalt
        """
        if isinstance(content, str):
            return self._anonymize_text(content, document_id, processing_basis)
        elif isinstance(content, dict):
            return self._anonymize_dict(content, document_id, processing_basis)
        else:
            return content
    
    def _anonymize_text(self, text: str, document_id: Optional[str], processing_basis: DSGVOProcessingBasis) -> str:
        """Anonymisiert Text-Content"""
        import re
        
        anonymized_text = text
        anonymization_count = 0
        
        for pii_type, pattern in self.pii_patterns.items():
            def replace_pii(match):
                nonlocal anonymization_count
                original_value = match.group()
                anonymized_value = self._get_or_create_anonymized_value(
                    original_value, pii_type, document_id, processing_basis
                )
                anonymization_count += 1
                return anonymized_value
            
            anonymized_text = re.sub(pattern, replace_pii, anonymized_text, flags=re.IGNORECASE)
        
        # Audit-Log
        if anonymization_count > 0:
            self._create_audit_entry(
                operation=DSGVOOperationType.ANONYMIZE,
                document_id=document_id,
                processing_basis=processing_basis,
                details={"anonymizations": anonymization_count, "content_type": "text"}
            )
        
        return anonymized_text
    
    def _anonymize_dict(self, data: Dict[str, Any], document_id: Optional[str], processing_basis: DSGVOProcessingBasis) -> Dict[str, Any]:
        """Anonymisiert strukturierte Daten"""
        anonymized_data = data.copy()
        anonymization_count = 0
        
        pii_fields = {
            "email", "e-mail", "mail", "e_mail",
            "phone", "telefon", "tel", "telephone", "mobile", 
            "name", "vorname", "nachname", "full_name",
            "address", "adresse", "strasse", "street"
        }
        
        for key, value in anonymized_data.items():
            if isinstance(value, str) and any(field in key.lower() for field in pii_fields):
                pii_type = self._guess_pii_type(key, value)
                anonymized_data[key] = self._get_or_create_anonymized_value(
                    value, pii_type, document_id, processing_basis
                )
                anonymization_count += 1
        
        # Audit-Log
        if anonymization_count > 0:
            self._create_audit_entry(
                operation=DSGVOOperationType.ANONYMIZE,
                document_id=document_id,
                processing_basis=processing_basis,
                details={"anonymizations": anonymization_count, "content_type": "structured"}
            )
        
        return anonymized_data
    
    def _get_or_create_anonymized_value(
        self, 
        original_value: str, 
        pii_type: PIIType, 
        document_id: Optional[str],
        processing_basis: DSGVOProcessingBasis
    ) -> str:
        """Holt oder erstellt anonymisierten Wert für PII"""
        # Hash des Original-Werts für sichere Suche
        value_hash = hashlib.sha256(original_value.encode()).hexdigest()
        backend = self._get_backend()
        
        # Suche existierende Anonymisierung
        existing = backend.select(
            table='pii_mappings',
            conditions={
                'original_value_hash': value_hash,
                'pii_type': pii_type.value
            }
        )
        
        if existing:
            return existing[0]['anonymized_value']
        
        # Erstelle neue Anonymisierung
        anonymized_value = self._generate_anonymized_value(original_value, pii_type)
        
        # Speichere Mapping
        mapping = PIIMapping(
            original_value=original_value,  # Wird als Hash gespeichert
            anonymized_value=anonymized_value,
            pii_type=pii_type,
            source_document_id=document_id,
            processing_basis=processing_basis,
            retention_until=(datetime.now() + timedelta(days=365 * self.retention_years)).isoformat()
        )
        
        # Insert über Database API
        mapping_record = {
            'id': mapping.id,
            'original_value_hash': value_hash,
            'anonymized_value': mapping.anonymized_value,
            'pii_type': mapping.pii_type.value,
            'source_document_id': mapping.source_document_id,
            'processing_basis': mapping.processing_basis.value,
            'consent_id': mapping.consent_id,
            'created_at': mapping.created_at,
            'retention_until': mapping.retention_until,
            'audit_trail': json.dumps(mapping.audit_trail)
        }
        
        backend.insert_record('pii_mappings', mapping_record)
        
        return anonymized_value
    
    def _generate_anonymized_value(self, original_value: str, pii_type: PIIType) -> str:
        """Generiert anonymisierten Wert basierend auf PII-Typ"""
        # Konsistente anonyme Werte basierend auf Hash
        hash_obj = hashlib.md5(original_value.encode())
        hash_hex = hash_obj.hexdigest()
        
        if pii_type == PIIType.EMAIL:
            return f"user_{hash_hex[:8]}@anonymous.de"
        elif pii_type == PIIType.PHONE:
            return f"+49 {hash_hex[0:3]} {hash_hex[3:6]}{hash_hex[6:10]}"
        elif pii_type == PIIType.NAME:
            return f"Person_{hash_hex[:8]}"
        elif pii_type == PIIType.ADDRESS:
            return f"Straße {hash_hex[:2]}, {hash_hex[2:7]} Stadt"
        elif pii_type == PIIType.IP_ADDRESS:
            # IP zu anonymem Bereich  
            parts = [str(int(hash_hex[i:i+2], 16) % 256) for i in range(0, 8, 2)]
            return f"10.0.{parts[0]}.{parts[1]}"
        else:
            return f"ANONYM_{hash_hex[:12]}"
    
    def _guess_pii_type(self, field_name: str, value: str) -> PIIType:
        """Errät PII-Typ basierend auf Feldname und Wert"""
        field_lower = field_name.lower()
        
        if "@" in value and "." in value:
            return PIIType.EMAIL
        elif any(term in field_lower for term in ["phone", "tel", "mobile"]):
            return PIIType.PHONE
        elif any(term in field_lower for term in ["name", "vorname", "nachname"]):
            return PIIType.NAME
        elif any(term in field_lower for term in ["address", "adresse", "street", "strasse"]):
            return PIIType.ADDRESS
        elif "ip" in field_lower:
            return PIIType.IP_ADDRESS
        else:
            return PIIType.CUSTOM
    
    # ========================= DSGVO RIGHTS IMPLEMENTATION =========================
    
    def right_to_access(self, subject_id: str) -> Dict[str, Any]:
        """
        DSGVO Art. 15 - Auskunftsrecht der betroffenen Person.
        
        Args:
            subject_id: ID der betroffenen Person
            
        Returns:
            Vollständige Auskunft über verarbeitete Daten
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Alle PII-Mappings der Person
        cursor.execute("""
            SELECT * FROM pii_mappings 
            WHERE source_document_id LIKE ? OR consent_id IN (
                SELECT consent_id FROM consent_records WHERE subject_id = ?
            )
        """, (f"%{subject_id}%", subject_id))
        
        pii_mappings = cursor.fetchall()
        
        # Alle Einwilligungen
        cursor.execute("SELECT * FROM consent_records WHERE subject_id = ?", (subject_id,))
        consents = cursor.fetchall()
        
        # Alle Audit-Einträge
        cursor.execute("SELECT * FROM dsgvo_audit WHERE subject_id = ?", (subject_id,))
        audit_entries = cursor.fetchall()
        
        conn.close()
        
        access_report = {
            "subject_id": subject_id,
            "request_timestamp": datetime.now().isoformat(),
            "data_processing": {
                "pii_mappings_count": len(pii_mappings),
                "consents_count": len(consents),
                "audit_entries_count": len(audit_entries)
            },
            "processing_purposes": list(set(consent[2] for consent in consents)),
            "legal_basis": list(set(consent[3] for consent in consents)),
            "retention_periods": [mapping[8] for mapping in pii_mappings if mapping[8]],
            "third_party_sharing": "None - data processed only within UDS3",
            "automated_decision_making": "Limited - only for PII detection and anonymization"
        }
        
        # Audit-Log für Auskunftsersuchen  
        self._create_audit_entry(
            operation=DSGVOOperationType.ACCESS_REQUEST,
            subject_id=subject_id,
            details=access_report
        )
        
        return access_report
    
    def right_to_erasure(self, subject_id: str, reason: str = "User request") -> Dict[str, Any]:
        """
        DSGVO Art. 17 - Recht auf Löschung ("Recht auf Vergessenwerden").
        
        Args:
            subject_id: ID der betroffenen Person
            reason: Grund für die Löschung
            
        Returns:
            Löschbericht
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        erasure_report = {
            "subject_id": subject_id,
            "erasure_timestamp": datetime.now().isoformat(),
            "reason": reason,
            "deleted_records": {}
        }
        
        # Lösche PII-Mappings
        cursor.execute("SELECT COUNT(*) FROM pii_mappings WHERE source_document_id LIKE ?", (f"%{subject_id}%",))
        pii_count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM pii_mappings WHERE source_document_id LIKE ?", (f"%{subject_id}%",))
        erasure_report["deleted_records"]["pii_mappings"] = pii_count
        
        # Lösche Einwilligungen
        cursor.execute("SELECT COUNT(*) FROM consent_records WHERE subject_id = ?", (subject_id,))
        consent_count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM consent_records WHERE subject_id = ?", (subject_id,))
        erasure_report["deleted_records"]["consent_records"] = consent_count
        
        # Anonymisiere Audit-Logs (Löschung würde Audit-Trail zerstören)
        cursor.execute("UPDATE dsgvo_audit SET subject_id = 'ERASED_USER' WHERE subject_id = ?", (subject_id,))
        erasure_report["anonymized_records"] = {"audit_entries": "subject_id anonymized"}
        
        conn.commit()
        conn.close()
        
        # Audit-Log für Löschung
        self._create_audit_entry(
            operation=DSGVOOperationType.DELETE,
            subject_id="SYSTEM",  # Nach Löschung keine subject_id mehr verfügbar
            details=erasure_report,
            legal_basis_reference="DSGVO Art. 17 - Recht auf Löschung"
        )
        
        logger.info(f"DSGVO erasure completed for subject: {subject_id}")
        return erasure_report
    
    def right_to_data_portability(self, subject_id: str, format: Literal["json", "xml", "csv"] = "json") -> bytes:
        """
        DSGVO Art. 20 - Recht auf Datenübertragbarkeit.
        
        Args:
            subject_id: ID der betroffenen Person
            format: Export-Format
            
        Returns:
            Exportierte Daten als Bytes
        """
        # Sammle alle Daten
        access_data = self.right_to_access(subject_id)
        
        export_data = {
            "dsgvo_data_export": {
                "subject_id": subject_id,
                "export_timestamp": datetime.now().isoformat(),
                "export_format": format,
                "legal_basis": "DSGVO Art. 20 - Recht auf Datenübertragbarkeit",
                "data": access_data
            }
        }
        
        if format == "json":
            result = json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")
        elif format == "xml":
            # Simplified XML (production would use proper XML library)
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<dsgvo_export>
    <subject_id>{subject_id}</subject_id>
    <timestamp>{export_data['dsgvo_data_export']['export_timestamp']}</timestamp>
    <data>{json.dumps(access_data)}</data>
</dsgvo_export>"""
            result = xml_content.encode("utf-8")
        else:  # CSV
            csv_content = f"Subject ID,Export Time,Data Count\\n{subject_id},{export_data['dsgvo_data_export']['export_timestamp']},{len(str(access_data))}"
            result = csv_content.encode("utf-8")
        
        # Audit-Log
        self._create_audit_entry(
            operation=DSGVOOperationType.EXPORT,
            subject_id=subject_id,
            details={"format": format, "data_size_bytes": len(result)},
            legal_basis_reference="DSGVO Art. 20 - Recht auf Datenübertragbarkeit"
        )
        
        return result
    
    # ========================= AUDIT & COMPLIANCE =========================
    
    def _create_audit_entry(
        self,
        operation: DSGVOOperationType,
        subject_id: Optional[str] = None,
        document_id: Optional[str] = None,
        processing_basis: DSGVOProcessingBasis = DSGVOProcessingBasis.LEGAL_OBLIGATION,
        details: Optional[Dict[str, Any]] = None,
        legal_basis_reference: Optional[str] = None
    ) -> str:
        """Erstellt DSGVO-Audit-Log-Eintrag"""
        audit_entry = DSGVOAuditEntry(
            operation=operation,
            subject_id=subject_id,
            document_id=document_id,
            processing_basis=processing_basis,
            details=details or {},
            legal_basis_reference=legal_basis_reference
        )
        
        # Hash für Tamper-Detection
        audit_dict = asdict(audit_entry)
        audit_dict.pop("hash", None)  # Remove hash for calculation
        
        # Convert enums to strings for JSON serialization
        if isinstance(audit_dict.get("operation"), DSGVOOperationType):
            audit_dict["operation"] = audit_dict["operation"].value
        if isinstance(audit_dict.get("processing_basis"), DSGVOProcessingBasis):
            audit_dict["processing_basis"] = audit_dict["processing_basis"].value
            
        audit_json = json.dumps(audit_dict, sort_keys=True)
        audit_entry.hash = hashlib.sha256(audit_json.encode()).hexdigest()
        
        # In Datenbank speichern
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO dsgvo_audit 
            (audit_id, operation, subject_id, document_id, processing_basis, 
             timestamp, performed_by, details, legal_basis_reference, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_entry.audit_id, audit_entry.operation.value, audit_entry.subject_id,
            audit_entry.document_id, audit_entry.processing_basis.value, 
            audit_entry.timestamp, audit_entry.performed_by,
            json.dumps(audit_entry.details), audit_entry.legal_basis_reference,
            audit_entry.hash
        ))
        
        conn.commit()
        conn.close()
        
        return audit_entry.audit_id
    
    def get_compliance_report(self, time_range: Optional[tuple] = None) -> Dict[str, Any]:
        """Erstellt umfassenden DSGVO-Compliance-Report"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Basis-Statistiken
        cursor.execute("SELECT COUNT(*) FROM pii_mappings")
        pii_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM consent_records")
        consent_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dsgvo_audit")
        audit_count = cursor.fetchone()[0]
        
        # Operationen nach Typ
        cursor.execute("SELECT operation, COUNT(*) FROM dsgvo_audit GROUP BY operation")
        operations_by_type = dict(cursor.fetchall())
        
        # Rechtsgrundlagen-Verteilung
        cursor.execute("SELECT processing_basis, COUNT(*) FROM pii_mappings GROUP BY processing_basis")
        legal_basis_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "compliance_status": "COMPLIANT",
            "statistics": {
                "total_pii_mappings": pii_count,
                "total_consents": consent_count,
                "total_audit_entries": audit_count
            },
            "operations_summary": operations_by_type,
            "legal_basis_distribution": legal_basis_distribution,
            "retention_compliance": self._check_retention_compliance(),
            "audit_trail_integrity": self._verify_audit_integrity()
        }
        
        return report
    
    def _check_retention_compliance(self) -> Dict[str, Any]:
        """Prüft Einhaltung der Aufbewahrungsfristen"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Abgelaufene PII-Mappings
        now = datetime.now().isoformat()
        cursor.execute("SELECT COUNT(*) FROM pii_mappings WHERE retention_until < ?", (now,))
        expired_pii = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "expired_pii_mappings": expired_pii,
            "auto_deletion_needed": expired_pii > 0,
            "last_cleanup": "Not implemented",  # TODO: Implement cleanup job
            "compliance_status": "PENDING_CLEANUP" if expired_pii > 0 else "COMPLIANT"
        }
    
    def _verify_audit_integrity(self) -> Dict[str, Any]:
        """Verifiziert Integrität der Audit-Logs (Tamper-Detection)"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM dsgvo_audit")
        audit_entries = cursor.fetchall()
        
        tampered_entries = 0
        for entry in audit_entries:
            # Rekonstruiere Hash
            audit_data = {
                "audit_id": entry[0],
                "operation": entry[1], 
                "subject_id": entry[2],
                "document_id": entry[3],
                "processing_basis": entry[4],
                "timestamp": entry[5],
                "performed_by": entry[6],
                "details": entry[7],
                "legal_basis_reference": entry[8]
            }
            
            expected_hash = hashlib.sha256(
                json.dumps(audit_data, sort_keys=True).encode()
            ).hexdigest()
            
            if entry[9] != expected_hash:  # Hash field
                tampered_entries += 1
        
        conn.close()
        
        return {
            "total_entries": len(audit_entries),
            "tampered_entries": tampered_entries,
            "integrity_status": "COMPROMISED" if tampered_entries > 0 else "INTACT"
        }


# ========================= FACTORY FUNCTIONS =========================

def create_dsgvo_core(
    database_path: Optional[str] = None,
    retention_years: int = 7,
    auto_anonymize: bool = True,
    strict_mode: bool = True
) -> UDS3DSGVOCore:
    """Factory function für UDS3 DSGVO Core"""
    return UDS3DSGVOCore(
        database_path=database_path,
        retention_years=retention_years,
        auto_anonymize=auto_anonymize,
        strict_mode=strict_mode
    )


__all__ = [
    "UDS3DSGVOCore", 
    "create_dsgvo_core",
    "DSGVOOperationType",
    "PIIType", 
    "DSGVOProcessingBasis",
    "PIIMapping",
    "DSGVOConsentRecord",
    "DSGVOAuditEntry"
]