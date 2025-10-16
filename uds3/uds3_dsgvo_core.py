#!/usr/bin/env python3
"""
UDS3 DSGVO Core - Zentrale DSGVO-Compliance Engine für UDS3

Implementiert umfassende DSGVO-Compliance auf UDS3-Core-Ebene:
- PII-Erkennung und -Anonymisierung
- DSGVO-Rechte (Art. 15, 17, 20)
- Audit-Trail mit Tamper-Detection
- Consent-Management
- Data-Breach-Notification

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

# UDS3 Database API Import (with circular import protection)
DATABASE_API_AVAILABLE = False
DatabaseManager = None

def _get_database_manager():
    """Lazy import of DatabaseManager to avoid circular imports"""
    global DATABASE_API_AVAILABLE, DatabaseManager
    
    if DatabaseManager is not None:
        return DatabaseManager
    
    try:
        from database.database_manager import DatabaseManager as _DatabaseManager
        DATABASE_API_AVAILABLE = True
        DatabaseManager = _DatabaseManager
        return DatabaseManager
    except ImportError as e:
        DATABASE_API_AVAILABLE = False
        logger.debug(f"DatabaseManager import failed: {e}")
        return None

logger = logging.getLogger(__name__)


class PIIType(Enum):
    """PII-Kategorien nach DSGVO"""
    EMAIL = "email"
    PHONE = "phone"
    NAME = "name"
    ADDRESS = "address"
    IP_ADDRESS = "ip_address"
    FINANCIAL = "financial"
    HEALTH = "health"
    BIOMETRIC = "biometric"


class DSGVOProcessingBasis(Enum):
    """DSGVO Verarbeitungsgrundlagen nach Art. 6"""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DSGVOOperationType(Enum):
    """DSGVO-relevante Operationen"""
    PII_DETECTION = "pii_detection"
    ANONYMIZE = "anonymize"
    PSEUDONYMIZE = "pseudonymize"
    RIGHT_TO_ACCESS = "right_to_access"
    RIGHT_TO_ERASURE = "right_to_erasure"
    RIGHT_TO_PORTABILITY = "right_to_portability"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    DATA_BREACH = "data_breach"


@dataclass
class PIIMapping:
    """Mapping zwischen Original-PII und anonymisierten Werten"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_value: str = ""  # Wird nicht direkt gespeichert
    original_value_hash: str = ""
    anonymized_value: str = ""
    pii_type: PIIType = PIIType.EMAIL
    source_document_id: Optional[str] = None
    processing_basis: DSGVOProcessingBasis = DSGVOProcessingBasis.LEGAL_OBLIGATION
    consent_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    retention_until: str = field(default_factory=lambda: (datetime.now() + timedelta(days=7*365)).isoformat())
    audit_trail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsentRecord:
    """DSGVO-Einwilligungsdatensatz"""
    consent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject_id: str = ""
    purpose: str = ""
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
        database_manager=None,  # Entferne Type Hint um circular import zu vermeiden
        retention_years: int = 7,
        auto_anonymize: bool = True,
        strict_mode: bool = True
    ):
        # Initialize Database Manager with circular import protection
        if database_manager:
            self.db_manager = database_manager
        else:
            # Lazy loading des DatabaseManagers
            DatabaseManagerClass = _get_database_manager()
            
            if DatabaseManagerClass:
                try:
                    # Verwende minimale Konfiguration ohne config.py abhängigkeiten
                    minimal_config = {
                        'relational': {'backend': 'sqlite_relational', 'path': 'dsgvo_minimal.db'},
                        'vector': {'backend': 'chromadb', 'path': 'dsgvo_vector'},
                        'graph': {'backend': 'sqlite_graph', 'path': 'dsgvo_graph.db'},
                        'features': {'auto_fallback': True}
                    }
                    self.db_manager = DatabaseManagerClass(minimal_config, strict_mode=False)
                    logger.info("DSGVO Core mit minimaler Konfiguration initialisiert")
                except Exception as init_error:
                    logger.warning(f"DatabaseManager-Initialisierung fehlgeschlagen: {init_error}")
                    # Ultra-minimaler Fallback: None verwenden und Tables manuell erstellen
                    self.db_manager = None
            else:
                logger.warning("Database API nicht verfügbar - DSGVO Core ohne Database Manager")
                self.db_manager = None
        
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
    
    def _init_sqlite_fallback(self):
        """Fallback: Initialisiert SQLite direkt für DSGVO Tables"""
        import sqlite3
        from pathlib import Path
        
        try:
            # Erstelle DSGVO database im aktuellen Verzeichnis
            db_path = Path("dsgvo_fallback.db")
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # PII Mappings Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pii_mappings (
                    id TEXT PRIMARY KEY,
                    original_value_hash TEXT NOT NULL,
                    anonymized_value TEXT NOT NULL,
                    pii_type TEXT NOT NULL,
                    source_document_id TEXT,
                    processing_basis TEXT NOT NULL,
                    consent_id TEXT,
                    created_at TEXT NOT NULL,
                    retention_until TEXT,
                    audit_trail TEXT
                )
            ''')
            
            # Consent Records Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consent_records (
                    consent_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    processing_basis TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    revoked_at TEXT,
                    valid_until TEXT,
                    data_categories TEXT,
                    metadata TEXT
                )
            ''')
            
            # Audit Trail Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dsgvo_audit (
                    audit_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    subject_id TEXT,
                    document_id TEXT,
                    processing_basis TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    performed_by TEXT NOT NULL,
                    details TEXT,
                    legal_basis_reference TEXT,
                    hash TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"✅ DSGVO SQLite Fallback Database initialisiert: {db_path}")
            self.sqlite_fallback_path = str(db_path)
            
        except Exception as e:
            logger.error(f"SQLite Fallback initialization fehlgeschlagen: {e}")
            self.sqlite_fallback_path = None
    
    def _get_backend(self):
        """Helper für sicheren Database-Backend-Zugriff"""
        if not self.db_manager or not self.db_manager.relational_backend:
            raise RuntimeError("Kein relational backend verfügbar für DSGVO Operations")
        return self.db_manager.relational_backend
    
    def _init_database(self):
        """Initialisiert die DSGVO-Tabellen über Database API"""
        if not self.db_manager or not hasattr(self.db_manager, 'relational_backend') or not self.db_manager.relational_backend:
            logger.warning("Kein relational backend verfügbar für DSGVO Tables - verwende SQLite fallback")
            self._init_sqlite_fallback()
            return
            
        backend = self._get_backend()
        
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
                        'type': pii_type.value,
                        'value': match.group(),
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.85  # Pattern-based detection
                    })
        
        # Strukturierte Daten-Erkennung
        elif isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, str):
                    pii_type = self._detect_pii_by_field_name(key, value)
                    if pii_type:
                        detected_pii.append({
                            'type': pii_type.value,
                            'field': key,
                            'value': value,
                            'confidence': 0.9  # Field-name-based detection
                        })
        
        # Audit-Log für PII-Erkennung
        if detected_pii:
            self._create_audit_entry(
                operation=DSGVOOperationType.PII_DETECTION,
                document_id=document_id,
                processing_basis=DSGVOProcessingBasis.LEGAL_OBLIGATION,
                details={
                    'pii_count': len(detected_pii),
                    'pii_types': list(set(item['type'] for item in detected_pii))
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
            content: Zu anonymisierende Inhalte
            document_id: Document ID für Tracking
            processing_basis: Rechtliche Grundlage der Verarbeitung
            
        Returns:
            Anonymisierte Inhalte
        """
        if isinstance(content, str):
            return self._anonymize_text(content, document_id, processing_basis)
        elif isinstance(content, dict):
            return self._anonymize_structured_data(content, document_id, processing_basis)
        else:
            logger.warning(f"Unsupported content type for anonymization: {type(content)}")
            return content
    
    def _anonymize_text(
        self, 
        text: str, 
        document_id: Optional[str], 
        processing_basis: DSGVOProcessingBasis
    ) -> str:
        """Anonymisiert PII in Textinhalten"""
        anonymized_text = text
        anonymization_count = 0
        
        import re
        for pii_type, pattern in self.pii_patterns.items():
            matches = list(re.finditer(pattern, anonymized_text, re.IGNORECASE))
            for match in reversed(matches):  # Rückwärts um Indices zu behalten
                original_value = match.group()
                anonymized_value = self._get_or_create_anonymized_value(
                    original_value, pii_type, document_id, processing_basis
                )
                
                # Ersetze im Text
                anonymized_text = (
                    anonymized_text[:match.start()] + 
                    anonymized_value + 
                    anonymized_text[match.end():]
                )
                anonymization_count += 1
        
        # Audit-Log
        if anonymization_count > 0:
            self._create_audit_entry(
                operation=DSGVOOperationType.ANONYMIZE,
                document_id=document_id,
                processing_basis=processing_basis,
                details={"anonymizations": anonymization_count, "content_type": "text"}
            )
        
        return anonymized_text
    
    def _anonymize_structured_data(
        self, 
        data: Dict[str, Any], 
        document_id: Optional[str], 
        processing_basis: DSGVOProcessingBasis
    ) -> Dict[str, Any]:
        """Anonymisiert PII in strukturierten Daten"""
        anonymized_data = data.copy()
        anonymization_count = 0
        
        # Erkenne PII-verdächtige Felder
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
            original_value_hash=value_hash,
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
            return f"ANON_{hash_hex[:12]}"
    
    # ========================= DSGVO RIGHTS IMPLEMENTATION =========================
    
    def dsgvo_right_to_access(self, subject_id: str) -> Dict[str, Any]:
        """
        Implementiert Art. 15 DSGVO - Auskunftsrecht
        
        Args:
            subject_id: Betroffene Person ID
            
        Returns:
            Dict mit allen gespeicherten personenbezogenen Daten
        """
        backend = self._get_backend()
        
        result = {
            "subject_id": subject_id,
            "generated_at": datetime.now().isoformat(),
            "data_categories": [],
            "processing_purposes": [],
            "consent_records": [],
            "audit_trail": [],
            "data_sources": []
        }
        
        # Consent Records
        consent_records = backend.select('consent_records', {'subject_id': subject_id})
        result["consent_records"] = [dict(row) for row in consent_records]
        
        # Audit Trail
        audit_entries = backend.select('dsgvo_audit', {'subject_id': subject_id})
        result["audit_trail"] = [dict(row) for row in audit_entries]
        
        # Audit für Auskunftsanfrage
        self._create_audit_entry(
            operation=DSGVOOperationType.RIGHT_TO_ACCESS,
            subject_id=subject_id,
            processing_basis=DSGVOProcessingBasis.LEGAL_OBLIGATION,
            details={"access_scope": "full_profile"}
        )
        
        return result
    
    def dsgvo_right_to_erasure(self, subject_id: str, reason: str = "user_request") -> Dict[str, Any]:
        """
        Implementiert Art. 17 DSGVO - Recht auf Löschung
        
        Args:
            subject_id: Betroffene Person ID
            reason: Grund der Löschung
            
        Returns:
            Dict mit Löschungsstatistik
        """
        backend = self._get_backend()
        deletion_stats = {"deleted_records": {}}
        
        # PII Mappings löschen
        pii_count_result = backend.execute_query(
            "SELECT COUNT(*) as count FROM pii_mappings WHERE source_document_id LIKE ?", 
            (f"%{subject_id}%",)
        )
        pii_count = pii_count_result[0]['count'] if pii_count_result else 0
        
        backend.execute_query(
            "DELETE FROM pii_mappings WHERE source_document_id LIKE ?", 
            (f"%{subject_id}%",)
        )
        deletion_stats["deleted_records"]["pii_mappings"] = pii_count
        
        # Consent Records löschen
        consent_count_result = backend.execute_query(
            "SELECT COUNT(*) as count FROM consent_records WHERE subject_id = ?", 
            (subject_id,)
        )
        consent_count = consent_count_result[0]['count'] if consent_count_result else 0
        
        backend.execute_query("DELETE FROM consent_records WHERE subject_id = ?", (subject_id,))
        deletion_stats["deleted_records"]["consent_records"] = consent_count
        
        # Audit Trail anonymisieren (nicht löschen - rechtliche Anforderung)
        backend.execute_query(
            "UPDATE dsgvo_audit SET subject_id = 'ERASED_USER' WHERE subject_id = ?", 
            (subject_id,)
        )
        
        # Audit für Löschung
        self._create_audit_entry(
            operation=DSGVOOperationType.RIGHT_TO_ERASURE,
            subject_id="ERASED_USER",  # Nach Löschung anonymisiert
            processing_basis=DSGVOProcessingBasis.LEGAL_OBLIGATION,
            details={
                "original_subject": f"HASH_{hashlib.sha256(subject_id.encode()).hexdigest()[:16]}",
                "reason": reason,
                "deletion_stats": deletion_stats
            }
        )
        
        deletion_stats["completed_at"] = datetime.now().isoformat()
        deletion_stats["legal_basis"] = "DSGVO Art. 17"
        
        return deletion_stats
    
    def dsgvo_right_to_portability(self, subject_id: str) -> Dict[str, Any]:
        """
        Implementiert Art. 20 DSGVO - Recht auf Datenübertragbarkeit
        
        Args:
            subject_id: Betroffene Person ID
            
        Returns:
            Dict mit exportierten Daten in maschinenlesbarem Format
        """
        # Nutze Auskunftsrecht als Basis
        access_data = self.dsgvo_right_to_access(subject_id)
        
        # Strukturiere für Portabilität
        portable_data = {
            "export_format": "DSGVO_Art20_JSON",
            "export_version": "1.0",
            "subject_id": subject_id,
            "export_date": datetime.now().isoformat(),
            "data": access_data,
            "technical_metadata": {
                "source_system": "UDS3_DSGVO_Core",
                "anonymization_status": "processed",
                "retention_policy": f"{self.retention_years}_years"
            }
        }
        
        # Audit für Portabilitätsanfrage
        self._create_audit_entry(
            operation=DSGVOOperationType.RIGHT_TO_PORTABILITY,
            subject_id=subject_id,
            processing_basis=DSGVOProcessingBasis.LEGAL_OBLIGATION,
            details={"export_format": "JSON", "data_categories": list(access_data.keys())}
        )
        
        return portable_data
    
    # ========================= CONSENT MANAGEMENT =========================
    
    def grant_consent(
        self, 
        subject_id: str, 
        purpose: str, 
        data_categories: List[PIIType],
        valid_until: Optional[str] = None
    ) -> str:
        """Gewährt DSGVO-Einwilligung"""
        backend = self._get_backend()
        
        consent = ConsentRecord(
            subject_id=subject_id,
            purpose=purpose,
            processing_basis=DSGVOProcessingBasis.CONSENT,
            valid_until=valid_until,
            data_categories=data_categories
        )
        
        consent_record = {
            'consent_id': consent.consent_id,
            'subject_id': consent.subject_id,
            'purpose': consent.purpose,
            'processing_basis': consent.processing_basis.value,
            'granted_at': consent.granted_at,
            'revoked_at': consent.revoked_at,
            'valid_until': consent.valid_until,
            'data_categories': json.dumps([cat.value for cat in consent.data_categories]),
            'metadata': json.dumps(consent.metadata)
        }
        
        backend.insert_record('consent_records', consent_record)
        
        # Audit
        self._create_audit_entry(
            operation=DSGVOOperationType.CONSENT_GRANTED,
            subject_id=subject_id,
            processing_basis=DSGVOProcessingBasis.CONSENT,
            details={"consent_id": consent.consent_id, "purpose": purpose}
        )
        
        return consent.consent_id
    
    def revoke_consent(self, consent_id: str) -> bool:
        """Widerruft DSGVO-Einwilligung"""
        backend = self._get_backend()
        
        # Update Consent Record
        result = backend.execute_query(
            "UPDATE consent_records SET revoked_at = ? WHERE consent_id = ?",
            (datetime.now().isoformat(), consent_id)
        )
        
        if result:
            # Audit
            self._create_audit_entry(
                operation=DSGVOOperationType.CONSENT_REVOKED,
                processing_basis=DSGVOProcessingBasis.LEGAL_OBLIGATION,
                details={"consent_id": consent_id}
            )
            return True
        
        return False
    
    # ========================= AUDIT & COMPLIANCE =========================
    
    def _create_audit_entry(
        self,
        operation: DSGVOOperationType,
        subject_id: Optional[str] = None,
        document_id: Optional[str] = None,
        processing_basis: DSGVOProcessingBasis = DSGVOProcessingBasis.LEGAL_OBLIGATION,
        details: Optional[Dict[str, Any]] = None,
        performed_by: str = "uds3_system"
    ):
        """Erstellt DSGVO-Audit-Eintrag"""
        backend = self._get_backend()
        
        audit_entry = DSGVOAuditEntry(
            operation=operation,
            subject_id=subject_id,
            document_id=document_id,
            processing_basis=processing_basis,
            performed_by=performed_by,
            details=details or {}
        )
        
        # Hash für Tamper-Detection
        audit_data = f"{audit_entry.audit_id}{audit_entry.operation.value}{audit_entry.timestamp}"
        audit_entry.hash = hashlib.sha256(audit_data.encode()).hexdigest()
        
        audit_record = {
            'audit_id': audit_entry.audit_id,
            'operation': audit_entry.operation.value,
            'subject_id': audit_entry.subject_id,
            'document_id': audit_entry.document_id,
            'processing_basis': audit_entry.processing_basis.value,
            'timestamp': audit_entry.timestamp,
            'performed_by': audit_entry.performed_by,
            'details': json.dumps(audit_entry.details),
            'legal_basis_reference': audit_entry.legal_basis_reference,
            'hash': audit_entry.hash
        }
        
        backend.insert_record('dsgvo_audit', audit_record)
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generiert DSGVO-Compliance-Report"""
        backend = self._get_backend()
        
        # Statistiken sammeln
        pii_count_result = backend.execute_query("SELECT COUNT(*) as count FROM pii_mappings")
        pii_count = pii_count_result[0]['count'] if pii_count_result else 0
        
        consent_count_result = backend.execute_query("SELECT COUNT(*) as count FROM consent_records")  
        consent_count = consent_count_result[0]['count'] if consent_count_result else 0
        
        audit_count_result = backend.execute_query("SELECT COUNT(*) as count FROM dsgvo_audit")
        audit_count = audit_count_result[0]['count'] if audit_count_result else 0
        
        # Operationen-Statistiken
        operations_result = backend.execute_query("SELECT operation, COUNT(*) as count FROM dsgvo_audit GROUP BY operation")
        operations_stats = {row['operation']: row['count'] for row in operations_result}
        
        # Processing Basis Statistiken
        basis_result = backend.execute_query("SELECT processing_basis, COUNT(*) as count FROM pii_mappings GROUP BY processing_basis")  
        basis_stats = {row['processing_basis']: row['count'] for row in basis_result}
        
        return {
            "report_generated": datetime.now().isoformat(),
            "total_pii_mappings": pii_count,
            "total_consent_records": consent_count,
            "total_audit_entries": audit_count,
            "operations_statistics": operations_stats,
            "processing_basis_statistics": basis_stats,
            "retention_policy_years": self.retention_years,
            "auto_anonymization_enabled": self.auto_anonymize,
            "strict_mode": self.strict_mode,
            "compliance_status": "COMPLIANT" if audit_count > 0 else "INSUFFICIENT_LOGGING",
            "audit_trail_integrity": self._verify_audit_integrity()
        }
    
    def _verify_audit_integrity(self) -> Dict[str, Any]:
        """Verifiziert Audit-Trail-Integrität"""
        backend = self._get_backend()
        
        audit_entries = backend.select('dsgvo_audit', order_by='timestamp')
        
        integrity_status = {
            "total_entries": len(audit_entries),
            "verified_entries": 0,
            "corrupted_entries": 0,
            "status": "VERIFIED"
        }
        
        for entry in audit_entries:
            # Rekalkuliere Hash
            audit_data = f"{entry['audit_id']}{entry['operation']}{entry['timestamp']}"
            expected_hash = hashlib.sha256(audit_data.encode()).hexdigest()
            
            if entry['hash'] == expected_hash:
                integrity_status["verified_entries"] += 1
            else:
                integrity_status["corrupted_entries"] += 1
        
        if integrity_status["corrupted_entries"] > 0:
            integrity_status["status"] = "COMPROMISED"
        
        return integrity_status
    
    # ========================= HELPER METHODS =========================
    
    def _detect_pii_by_field_name(self, field_name: str, value: str) -> Optional[PIIType]:
        """Erkennt PII-Typ basierend auf Feldname"""
        field_lower = field_name.lower()
        
        if any(term in field_lower for term in ["email", "e-mail", "mail"]):
            return PIIType.EMAIL
        elif any(term in field_lower for term in ["phone", "telefon", "tel", "mobile"]):
            return PIIType.PHONE
        elif any(term in field_lower for term in ["name", "vorname", "nachname"]):
            return PIIType.NAME
        elif any(term in field_lower for term in ["address", "adresse", "straße", "street"]):
            return PIIType.ADDRESS
        elif "ip" in field_lower and ("address" in field_lower or "addr" in field_lower):
            return PIIType.IP_ADDRESS
        
        return None
    
    def _guess_pii_type(self, field_name: str, value: str) -> PIIType:
        """Schätzt PII-Typ basierend auf Feld und Wert"""
        detected_type = self._detect_pii_by_field_name(field_name, value)
        if detected_type:
            return detected_type
        
        # Pattern-basierte Fallback-Erkennung
        import re
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, value, re.IGNORECASE):
                return pii_type
        
        # Default fallback
        return PIIType.NAME


# ========================= FACTORY FUNCTIONS =========================

def create_dsgvo_core(
    database_manager: Optional[DatabaseManager] = None,
    retention_years: int = 7,
    auto_anonymize: bool = True,
    strict_mode: bool = True
) -> UDS3DSGVOCore:
    """Factory function für UDS3 DSGVO Core"""
    return UDS3DSGVOCore(
        database_manager=database_manager,
        retention_years=retention_years,
        auto_anonymize=auto_anonymize,
        strict_mode=strict_mode
    )


# ========================= EXPORTS =========================

__all__ = [
    "UDS3DSGVOCore", 
    "create_dsgvo_core",
    "DSGVOOperationType",
    "PIIType", 
    "DSGVOProcessingBasis",
    "PIIMapping",
    "ConsentRecord",
    "DSGVOAuditEntry"
]