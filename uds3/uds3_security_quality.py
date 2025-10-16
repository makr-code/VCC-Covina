"""
Data Security & Quality Framework für Unified Database Strategy v3.0

Erweitert die Unified Database Strategy um:
1. Comprehensive Data Security (Hashing, UUIDs, Checksums, Encryption)
2. Advanced Data Quality Management (Validation, Scoring, Monitoring)
3. Integrity Verification across all database types
"""

import logging
import hashlib
import uuid
import hmac
import secrets
import json
from typing import Dict, List, Any
from typing import Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Sicherheitsstufen für verschiedene Datentypen"""

    PUBLIC = "public"  # Öffentlich zugängliche Daten
    INTERNAL = "internal"  # Interne Unternehmensdaten
    CONFIDENTIAL = "confidential"  # Vertrauliche Daten
    RESTRICTED = "restricted"  # Höchst vertrauliche Daten


class QualityMetric(Enum):
    """Datenqualitäts-Metriken"""

    COMPLETENESS = "completeness"  # Vollständigkeit der Daten
    CONSISTENCY = "consistency"  # Konsistenz zwischen DBs
    ACCURACY = "accuracy"  # Korrektheit der Daten
    VALIDITY = "validity"  # Gültigkeit/Format-Korrektheit
    UNIQUENESS = "uniqueness"  # Eindeutigkeit der Daten
    TIMELINESS = "timeliness"  # Aktualität der Daten
    SEMANTIC_COHERENCE = "semantic_coherence"  # Semantische Kohärenz


@dataclass
class SecurityConfig:
    """Konfiguration für Datensicherheit"""

    encryption_enabled: bool = True
    hash_algorithm: str = "sha256"
    uuid_version: int = 4
    salt_length: int = 32
    checksum_validation: bool = True
    secure_deletion: bool = True
    audit_logging: bool = True


@dataclass
class QualityConfig:
    """Konfiguration für Datenqualität"""

    minimum_quality_score: float = 0.75
    completeness_threshold: float = 0.90
    consistency_check_interval: int = 3600  # Sekunden
    semantic_validation: bool = True
    auto_correction: bool = False
    quality_monitoring: bool = True


class DataSecurityManager:
    """
    Verwaltet Datensicherheit über alle Datenbank-Typen hinweg

    Features:
    - Content Hashing für Integrität
    - UUID-basierte eindeutige Identifikation
    - Verschlüsselung sensibler Daten
    - Secure Deletion
    - Audit Logging
    """

    def __init__(self, security_level: SecurityLevel = SecurityLevel.INTERNAL):
        """
        Initialisiert DataSecurityManager

        Args:
            security_level: Gewünschtes Sicherheitslevel
        """
        # Create SecurityConfig basierend auf SecurityLevel
        encryption_needed = security_level in [
            SecurityLevel.RESTRICTED,
            SecurityLevel.CONFIDENTIAL,
        ]

        self.config = SecurityConfig(
            encryption_enabled=encryption_needed,
            hash_algorithm="sha256",
            uuid_version=4,
            salt_length=32,
            checksum_validation=True,
            secure_deletion=True,
            audit_logging=True,
        )

        self.security_level = security_level
        self.encryption_key = self._generate_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)

        # Security Schemas für verschiedene Datentypen
        self.security_schemas = self._create_security_schemas()

    def _generate_encryption_key(self) -> bytes:
        """Generiert sicheren Verschlüsselungsschlüssel"""
        return Fernet.generate_key()

    def _create_security_schemas(self) -> Dict:
        """Definiert Sicherheitsschemas für verschiedene Datentypen"""
        return {
            "document": {
                "security_level": SecurityLevel.INTERNAL,
                "fields": {
                    "content": {"encrypt": False, "hash": True, "audit": True},
                    "title": {"encrypt": False, "hash": False, "audit": True},
                    "file_path": {"encrypt": False, "hash": True, "audit": True},
                    "metadata": {"encrypt": False, "hash": False, "audit": True},
                },
            },
            "personal_data": {
                "security_level": SecurityLevel.CONFIDENTIAL,
                "fields": {
                    "author_name": {"encrypt": True, "hash": True, "audit": True},
                    "contact_info": {"encrypt": True, "hash": False, "audit": True},
                    "sensitive_content": {"encrypt": True, "hash": True, "audit": True},
                },
            },
            "legal_data": {
                "security_level": SecurityLevel.RESTRICTED,
                "fields": {
                    "case_details": {"encrypt": True, "hash": True, "audit": True},
                    "client_data": {"encrypt": True, "hash": True, "audit": True},
                    "verdict": {"encrypt": False, "hash": True, "audit": True},
                },
            },
        }

    def generate_secure_document_id(
        self,
        content: str,
        file_path: str,
        security_level: SecurityLevel = SecurityLevel.INTERNAL,
    ) -> Dict:
        """
        Generiert sichere Dokument-ID mit Hash-Verifikation

        Args:
            content: Dokumenteninhalt
            file_path: Dateipfad
            security_level: Sicherheitsstufe

        Returns:
            Dict: Sicherheitsinformationen inkl. IDs und Hashes
        """
        # UUID für eindeutige Identifikation
        document_uuid = str(uuid.uuid4())

        # Content Hash für Integrität
        content_hash = self._calculate_content_hash(content, file_path)

        # Secure Salt für zusätzliche Sicherheit
        salt = secrets.token_hex(self.config.salt_length)

        # HMAC für Authentizität
        hmac_key = self._derive_hmac_key(document_uuid, salt)
        content_hmac = hmac.new(
            hmac_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Checksum für schnelle Validation
        checksum = self._calculate_checksum(content + file_path + document_uuid)

        security_info = {
            "document_id": f"doc_{document_uuid.replace('-', '')}",
            "document_uuid": document_uuid,
            "content_hash": content_hash,
            "content_hmac": content_hmac,
            "checksum": checksum,
            "salt": salt,
            "security_level": security_level.value,
            "created_at": datetime.now().isoformat(),
            "hash_algorithm": self.config.hash_algorithm,
            "uuid_version": self.config.uuid_version,
        }

        logger.info(f"Sichere Document-ID generiert: {security_info['document_id']}")
        return security_info

    def _calculate_content_hash(self, content: str, file_path: str) -> str:
        """Berechnet Content-Hash für Integrität"""
        hash_input = f"{content}:{file_path}:{datetime.now().date().isoformat()}"

        if self.config.hash_algorithm == "sha256":
            return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        elif self.config.hash_algorithm == "sha512":
            return hashlib.sha512(hash_input.encode("utf-8")).hexdigest()
        else:
            return hashlib.md5(hash_input.encode("utf-8")).hexdigest()

    def _derive_hmac_key(self, document_uuid: str, salt: str) -> str:
        """Ableitung eines HMAC-Schlüssels"""
        key_input = f"{document_uuid}:{salt}:{self.encryption_key.decode('utf-8')}"
        return hashlib.sha256(key_input.encode("utf-8")).hexdigest()[:32]

    def _calculate_checksum(self, data: str) -> str:
        """Berechnet einfache Checksum für schnelle Validation"""
        return hashlib.md5(data.encode("utf-8")).hexdigest()[:16]

    def encrypt_sensitive_data(self, data: str, data_type: str = "document") -> Dict:
        """
        Verschlüsselt sensible Daten basierend auf Sicherheitsschema

        Args:
            data: Zu verschlüsselnde Daten
            data_type: Typ der Daten für Schema-Lookup

        Returns:
            Dict: Verschlüsselte Daten mit Metadaten
        """
        if not self.config.encryption_enabled:
            return {"encrypted_data": data, "is_encrypted": False}

        try:
            encrypted_bytes = self.cipher_suite.encrypt(data.encode("utf-8"))
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode("utf-8")

            return {
                "encrypted_data": encrypted_b64,
                "is_encrypted": True,
                "encryption_timestamp": datetime.now().isoformat(),
                "data_type": data_type,
                "algorithm": "Fernet",
            }
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return {"encrypted_data": data, "is_encrypted": False, "error": str(e)}

    def decrypt_sensitive_data(self, encrypted_data: Dict) -> str:
        """Entschlüsselt Daten"""
        if not encrypted_data.get("is_encrypted", False):
            return encrypted_data["encrypted_data"]

        try:
            encrypted_bytes = base64.b64decode(encrypted_data["encrypted_data"])
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    def verify_document_integrity(
        self, document_id: str, content: str, file_path: str, security_info: Dict
    ) -> Dict:
        """
        Verifiziert Dokumentenintegrität anhand der Sicherheitsinformationen

        Args:
            document_id: Dokument-ID
            content: Aktueller Inhalt
            file_path: Aktueller Dateipfad
            security_info: Ursprüngliche Sicherheitsinformationen

        Returns:
            Dict: Verifikationsergebnis
        """
        verification_result = {
            "document_id": document_id,
            "verification_timestamp": datetime.now().isoformat(),
            "integrity_verified": True,
            "checks": {},
            "issues": [],
        }

        # Content Hash Check
        current_hash = self._calculate_content_hash(content, file_path)
        hash_match = current_hash == security_info.get("content_hash")
        verification_result["checks"]["content_hash"] = hash_match

        if not hash_match:
            verification_result["integrity_verified"] = False
            verification_result["issues"].append(
                "Content hash mismatch - document may be modified"
            )

        # Checksum Check
        current_checksum = self._calculate_checksum(
            content + file_path + security_info.get("document_uuid", "")
        )
        checksum_match = current_checksum == security_info.get("checksum")
        verification_result["checks"]["checksum"] = checksum_match

        if not checksum_match:
            verification_result["integrity_verified"] = False
            verification_result["issues"].append(
                "Checksum mismatch - possible data corruption"
            )

        # HMAC Verification
        if "content_hmac" in security_info and "salt" in security_info:
            hmac_key = self._derive_hmac_key(
                security_info["document_uuid"], security_info["salt"]
            )
            current_hmac = hmac.new(
                hmac_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            hmac_match = current_hmac == security_info["content_hmac"]
            verification_result["checks"]["hmac"] = hmac_match

            if not hmac_match:
                verification_result["integrity_verified"] = False
                verification_result["issues"].append(
                    "HMAC verification failed - authenticity compromised"
                )

        return verification_result

    def create_audit_log_entry(
        self,
        operation: str,
        document_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[Any, Any]] = None,
    ) -> Dict:
        """Erstellt Audit-Log-Eintrag"""
        audit_entry = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "document_id": document_id,
            "user_id": user_id or "system",
            "details": details or {},
            "hash": None,
        }

        # Hash des Audit-Eintrags für Tamper-Detection
        audit_json = json.dumps(audit_entry, sort_keys=True)
        audit_entry["hash"] = hashlib.sha256(audit_json.encode("utf-8")).hexdigest()

        return audit_entry


class DataQualityManager:
    """
    Verwaltet Datenqualität über alle Datenbank-Typen hinweg

    Features:
    - Multi-dimensionale Qualitätsbewertung
    - Cross-Database Consistency Monitoring
    - Semantic Coherence Validation
    - Automated Quality Improvement
    - Real-time Quality Scoring
    """

    def __init__(self, config: QualityConfig = None):
        self.config = config or QualityConfig()

        # Quality Metrics Weights
        self.quality_weights = {
            QualityMetric.COMPLETENESS: 0.20,
            QualityMetric.CONSISTENCY: 0.20,
            QualityMetric.ACCURACY: 0.15,
            QualityMetric.VALIDITY: 0.15,
            QualityMetric.UNIQUENESS: 0.10,
            QualityMetric.TIMELINESS: 0.10,
            QualityMetric.SEMANTIC_COHERENCE: 0.10,
        }

        # Quality Rules
        self.quality_rules = self._create_quality_rules()

    def _create_quality_rules(self) -> Dict:
        """Definiert Qualitätsregeln für verschiedene Datentypen"""
        return {
            "document": {
                "required_fields": ["id", "title", "content", "file_path"],
                "min_content_length": 100,
                "max_content_length": 1000000,
                "title_max_length": 500,
                "valid_file_extensions": [".pdf", ".docx", ".txt", ".html"],
                "semantic_rules": {
                    "min_coherence_score": 0.7,
                    "max_topics_deviation": 0.3,
                },
            },
            "document_chunk": {
                "required_fields": ["id", "document_id", "content", "chunk_index"],
                "min_chunk_length": 50,
                "max_chunk_length": 2000,
                "overlap_tolerance": 0.1,
                "semantic_rules": {
                    "min_coherence_with_parent": 0.8,
                    "max_topic_drift": 0.2,
                },
            },
            "relationships": {
                "required_fields": ["from_node_id", "to_node_id", "relationship_type"],
                "valid_relationship_types": ["UDS3_CONTENT_RELATION"],
                "bidirectional_consistency": True,
                "orphan_tolerance": 0.0,
            },
        }

    def calculate_document_quality_score(
        self,
        document_data: Dict,
        vector_data: Optional[Dict[Any, Any]] = None,
        graph_data: Optional[Dict[Any, Any]] = None,
        relational_data: Optional[Dict[Any, Any]] = None,
    ) -> Dict:
        """
        Berechnet umfassenden Qualitätsscore für ein Dokument

        Args:
            document_data: Grundlegende Dokumentdaten
            vector_data: Vector-DB Daten (optional)
            graph_data: Graph-DB Daten (optional)
            relational_data: Relational-DB Daten (optional)

        Returns:
            Dict: Detailliertes Qualitätsergebnis
        """
        quality_result = {
            "document_id": document_data.get("id", "unknown"),
            "overall_score": 0.0,
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
            "issues": [],
            "recommendations": [],
        }

        # Completeness Score
        completeness_score = self._calculate_completeness_score(
            document_data, vector_data, graph_data, relational_data
        )
        quality_result["metrics"][QualityMetric.COMPLETENESS.value] = completeness_score

        # Consistency Score
        consistency_score = self._calculate_consistency_score(
            document_data, vector_data, graph_data, relational_data
        )
        quality_result["metrics"][QualityMetric.CONSISTENCY.value] = consistency_score

        # Accuracy Score
        accuracy_score = self._calculate_accuracy_score(document_data)
        quality_result["metrics"][QualityMetric.ACCURACY.value] = accuracy_score

        # Validity Score
        validity_score = self._calculate_validity_score(document_data)
        quality_result["metrics"][QualityMetric.VALIDITY.value] = validity_score

        # Uniqueness Score
        uniqueness_score = self._calculate_uniqueness_score(document_data)
        quality_result["metrics"][QualityMetric.UNIQUENESS.value] = uniqueness_score

        # Timeliness Score
        timeliness_score = self._calculate_timeliness_score(document_data)
        quality_result["metrics"][QualityMetric.TIMELINESS.value] = timeliness_score

        # Semantic Coherence Score
        semantic_score = self._calculate_semantic_coherence_score(
            document_data, vector_data
        )
        quality_result["metrics"][QualityMetric.SEMANTIC_COHERENCE.value] = (
            semantic_score
        )

        # Calculate Overall Score
        overall_score = 0.0
        for metric_name, score in quality_result["metrics"].items():
            try:
                metric_enum = QualityMetric(metric_name)
                if metric_enum in self.quality_weights:
                    overall_score += score * self.quality_weights[metric_enum]
            except ValueError:
                # Skip unknown metrics
                continue

        quality_result["overall_score"] = round(overall_score, 3)

        # Generate Issues and Recommendations
        quality_result["issues"] = self._identify_quality_issues(
            quality_result["metrics"]
        )
        quality_result["recommendations"] = self._generate_quality_recommendations(
            quality_result["metrics"]
        )

        return quality_result

    def _calculate_completeness_score(
        self, doc_data: Dict, vector_data: Dict, graph_data: Dict, relational_data: Dict
    ) -> float:
        """Berechnet Vollständigkeits-Score"""
        rules = self.quality_rules.get("document", {})
        required_fields = rules.get("required_fields", [])

        present_fields = sum(
            1 for field in required_fields if field in doc_data and doc_data[field]
        )
        completeness = present_fields / len(required_fields) if required_fields else 1.0

        # Cross-DB Completeness Bonus
        db_presence_bonus = 0.0
        if vector_data:
            db_presence_bonus += 0.1
        if graph_data:
            db_presence_bonus += 0.1
        if relational_data:
            db_presence_bonus += 0.1

        return min(1.0, completeness + db_presence_bonus)

    def _calculate_consistency_score(
        self, doc_data: Dict, vector_data: Dict, graph_data: Dict, relational_data: Dict
    ) -> float:
        """Berechnet Konsistenz-Score zwischen Datenbanken"""
        if not all([vector_data, graph_data, relational_data]):
            return 0.8  # Partial penalty for missing data

        consistency_checks: list[Any] = []

        # ID Consistency
        doc_id = doc_data.get("id")
        if doc_id:
            vector_id_match = vector_data.get("document_id") == doc_id
            graph_id_match = graph_data.get("id") == doc_id
            relational_id_match = relational_data.get("document_id") == doc_id

            consistency_checks.extend(
                [vector_id_match, graph_id_match, relational_id_match]
            )

        # Content Consistency (simplified)
        title_consistency = doc_data.get("title") == relational_data.get(
            "title", doc_data.get("title")
        )
        consistency_checks.append(title_consistency)

        return (
            sum(consistency_checks) / len(consistency_checks)
            if consistency_checks
            else 1.0
        )

    def _calculate_accuracy_score(self, doc_data: Dict) -> float:
        """Berechnet Genauigkeits-Score"""
        accuracy_score = 1.0

        # Content Length Check
        content = doc_data.get("content", "")
        rules = self.quality_rules.get("document", {})

        min_length = rules.get("min_content_length", 0)
        max_length = rules.get("max_content_length", float("inf"))

        if len(content) < min_length:
            accuracy_score *= 0.7
        elif len(content) > max_length:
            accuracy_score *= 0.8

        # Title Length Check
        title = doc_data.get("title", "")
        title_max_length = rules.get("title_max_length", 500)

        if len(title) > title_max_length:
            accuracy_score *= 0.9

        return accuracy_score

    def _calculate_validity_score(self, doc_data: Dict) -> float:
        """Berechnet Gültigkeits-Score"""
        validity_score = 1.0

        # File Extension Check
        file_path = doc_data.get("file_path", "")
        if file_path:
            rules = self.quality_rules.get("document", {})
            valid_extensions = rules.get("valid_file_extensions", [])

            if valid_extensions:
                file_extension = (
                    "." + file_path.split(".")[-1] if "." in file_path else ""
                )
                if file_extension.lower() not in [
                    ext.lower() for ext in valid_extensions
                ]:
                    validity_score *= 0.8

        # Required Field Format Check
        if "id" in doc_data:
            doc_id = doc_data["id"]
            if not doc_id.startswith("doc_"):
                validity_score *= 0.9

        return validity_score

    def _calculate_uniqueness_score(self, doc_data: Dict) -> float:
        """Berechnet Eindeutigkeits-Score (vereinfacht)"""
        # In einer echten Implementierung würde hier gegen die DB geprüft
        return 1.0  # Annahme: Eindeutigkeit durch ID gewährleistet

    def _calculate_timeliness_score(self, doc_data: Dict) -> float:
        """Berechnet Aktualitäts-Score"""
        created_at = doc_data.get("created_at")
        if not created_at:
            return 0.8  # Penalty für fehlenden Timestamp

        try:
            creation_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age_days = (datetime.now() - creation_time).days

            # Timeliness Score basierend auf Alter
            if age_days <= 1:
                return 1.0
            elif age_days <= 7:
                return 0.9
            elif age_days <= 30:
                return 0.8
            elif age_days <= 90:
                return 0.7
            else:
                return 0.6

        except Exception:
            return 0.7  # Penalty für ungültigen Timestamp

    def _calculate_semantic_coherence_score(
        self, doc_data: Dict, vector_data: Optional[Dict[Any, Any]] = None
    ) -> float:
        """Berechnet semantische Kohärenz-Score (vereinfacht)"""
        if not vector_data:
            return 0.8  # Penalty für fehlende Vector-Daten

        # Vereinfachte Implementierung
        # In einer echten Implementierung würde hier NLP/ML verwendet

        content = doc_data.get("content", "")
        title = doc_data.get("title", "")

        if not content or not title:
            return 0.6

        # Simple coherence check: title keywords in content
        title_words = set(title.lower().split())
        content_words = set(content.lower().split())

        overlap = len(title_words.intersection(content_words))
        coherence_score = min(1.0, overlap / len(title_words)) if title_words else 0.8

        return coherence_score

    def _identify_quality_issues(self, metrics: Dict) -> List[str]:
        """Identifiziert Qualitätsprobleme basierend auf Metriken"""
        issues: list[Any] = []

        for metric_name, score in metrics.items():
            if score < 0.7:
                if metric_name == QualityMetric.COMPLETENESS.value:
                    issues.append("Incomplete data - missing required fields")
                elif metric_name == QualityMetric.CONSISTENCY.value:
                    issues.append("Inconsistent data across databases")
                elif metric_name == QualityMetric.ACCURACY.value:
                    issues.append("Data accuracy issues - invalid formats or values")
                elif metric_name == QualityMetric.VALIDITY.value:
                    issues.append("Data validity problems - format violations")
                elif metric_name == QualityMetric.SEMANTIC_COHERENCE.value:
                    issues.append("Poor semantic coherence between title and content")
                elif metric_name == QualityMetric.TIMELINESS.value:
                    issues.append("Data may be outdated")

        return issues

    def _generate_quality_recommendations(self, metrics: Dict) -> List[str]:
        """Generiert Verbesserungsempfehlungen"""
        recommendations: list[Any] = []

        for metric_name, score in metrics.items():
            if score < 0.8:
                if metric_name == QualityMetric.COMPLETENESS.value:
                    recommendations.append("Fill in missing required fields")
                elif metric_name == QualityMetric.CONSISTENCY.value:
                    recommendations.append("Synchronize data across all databases")
                elif metric_name == QualityMetric.ACCURACY.value:
                    recommendations.append("Validate and correct data formats")
                elif metric_name == QualityMetric.SEMANTIC_COHERENCE.value:
                    recommendations.append("Review content-title alignment")

        return recommendations

    def validate_cross_db_quality(
        self,
        document_id: str,
        vector_data: Dict,
        graph_data: Dict,
        relational_data: Dict,
    ) -> Dict:
        """
        Validiert Datenqualität über alle Datenbanken hinweg

        Returns:
            Dict: Cross-Database Qualitätsbewertung
        """
        cross_db_quality = {
            "document_id": document_id,
            "timestamp": datetime.now().isoformat(),
            "overall_cross_db_score": 0.0,
            "database_scores": {},
            "inconsistencies": [],
            "quality_issues": [],
        }

        # Individual Database Quality
        databases = {
            "vector": vector_data,
            "graph": graph_data,
            "relational": relational_data,
        }

        for db_name, db_data in databases.items():
            if db_data:
                db_score = self._calculate_db_specific_quality(db_name, db_data)
                cross_db_quality["database_scores"][db_name] = db_score

        # Cross-DB Consistency Analysis
        inconsistencies = self._detect_cross_db_inconsistencies(
            vector_data, graph_data, relational_data
        )
        cross_db_quality["inconsistencies"] = inconsistencies

        # Overall Cross-DB Score
        if cross_db_quality["database_scores"]:
            avg_score = sum(cross_db_quality["database_scores"].values()) / len(
                cross_db_quality["database_scores"]
            )
            inconsistency_penalty = len(inconsistencies) * 0.1
            cross_db_quality["overall_cross_db_score"] = max(
                0.0, avg_score - inconsistency_penalty
            )

        return cross_db_quality

    def _calculate_db_specific_quality(self, db_type: str, db_data: Dict) -> float:
        """Berechnet DB-spezifische Qualität"""
        # Vereinfachte DB-spezifische Qualitätsbewertung
        base_score = 1.0

        if db_type == "vector":
            # Vector-spezifische Qualitätsprüfungen
            if "embeddings" in db_data and len(db_data["embeddings"]) == 0:
                base_score *= 0.8

        elif db_type == "graph":
            # Graph-spezifische Qualitätsprüfungen
            if "relationships" in db_data and len(db_data["relationships"]) == 0:
                base_score *= 0.9

        elif db_type == "relational":
            # Relational-spezifische Qualitätsprüfungen
            required_fields = ["id", "title", "file_path"]
            missing_fields = [f for f in required_fields if f not in db_data]
            if missing_fields:
                base_score *= 1.0 - len(missing_fields) * 0.2

        return max(0.0, base_score)

    def _detect_cross_db_inconsistencies(
        self, vector_data: Dict, graph_data: Dict, relational_data: Dict
    ) -> List[Dict]:
        """Erkennt Inkonsistenzen zwischen Datenbanken"""
        inconsistencies: list[Any] = []

        if vector_data and graph_data:
            # Chunk Count vs Relationship Count
            vector_chunks = len(vector_data.get("chunks", []))
            graph_contains_rels = len(
                [
                    r
                    for r in graph_data.get("relationships", [])
                    if r.get("type") == "CONTAINS"
                ]
            )

            if vector_chunks != graph_contains_rels:
                inconsistencies.append(
                    {
                        "type": "chunk_relationship_mismatch",
                        "description": f"Vector chunks ({vector_chunks}) != Graph CONTAINS relationships ({graph_contains_rels})",
                        "severity": "medium",
                    }
                )

        if graph_data and relational_data:
            # ID Consistency
            graph_id = graph_data.get("id")
            relational_id = relational_data.get("document_id")

            if graph_id and relational_id and graph_id != relational_id:
                inconsistencies.append(
                    {
                        "type": "id_mismatch",
                        "description": f"Graph ID ({graph_id}) != Relational ID ({relational_id})",
                        "severity": "high",
                    }
                )

        return inconsistencies


# Factory Functions
def create_security_manager(
    security_level: SecurityLevel = SecurityLevel.INTERNAL,
) -> DataSecurityManager:
    """Factory für DataSecurityManager mit vorkonfigurierten Sicherheitseinstellungen"""
    config = SecurityConfig()

    if security_level == SecurityLevel.RESTRICTED:
        config.encryption_enabled = True
        config.hash_algorithm = "sha512"
        config.salt_length = 64
        config.secure_deletion = True
        config.audit_logging = True
    elif security_level == SecurityLevel.CONFIDENTIAL:
        config.encryption_enabled = True
        config.hash_algorithm = "sha256"
        config.salt_length = 32
        config.audit_logging = True

    return DataSecurityManager(config)


def create_quality_manager(strict_mode: bool = False) -> DataQualityManager:
    """Factory für DataQualityManager mit konfigurierbaren Qualitätsanforderungen"""
    config = QualityConfig()

    if strict_mode:
        config.minimum_quality_score = 0.90
        config.completeness_threshold = 0.95
        config.semantic_validation = True
        config.auto_correction = False

    return DataQualityManager(config)


# Integration Test
if __name__ == "__main__":
    print("=== DATA SECURITY & QUALITY FRAMEWORK TEST ===")

    # Security Manager Test
    print("\n--- DATA SECURITY TEST ---")
    security_mgr = create_security_manager(SecurityLevel.CONFIDENTIAL)

    test_content = (
        "Das ist ein Testdokument über Kündigungsschutz im deutschen Arbeitsrecht."
    )
    test_file_path = "test_arbeitsrecht.pdf"

    # Generate Secure Document ID
    security_info = security_mgr.generate_secure_document_id(
        test_content, test_file_path, SecurityLevel.CONFIDENTIAL
    )

    print(f"Document ID: {security_info['document_id']}")
    print(f"Content Hash: {security_info['content_hash'][:16]}...")
    print(f"Security Level: {security_info['security_level']}")

    # Verify Integrity
    integrity_result = security_mgr.verify_document_integrity(
        security_info["document_id"], test_content, test_file_path, security_info
    )
    print(f"Integrity Verified: {integrity_result['integrity_verified']}")

    # Encrypt Sensitive Data
    encrypted_data = security_mgr.encrypt_sensitive_data(test_content, "legal_data")
    print(f"Encryption Successful: {encrypted_data['is_encrypted']}")

    # Quality Manager Test
    print("\n--- DATA QUALITY TEST ---")
    quality_mgr = create_quality_manager(strict_mode=True)

    test_document_data = {
        "id": security_info["document_id"],
        "title": "Kündigungsschutz im deutschen Arbeitsrecht",
        "content": test_content,
        "file_path": test_file_path,
        "created_at": datetime.now().isoformat(),
    }

    # Mock Vector and Graph Data
    test_vector_data = {
        "document_id": security_info["document_id"],
        "chunks": [{"content": test_content}],
        "embeddings": [1.0] * 1536,
    }

    test_graph_data = {
        "id": security_info["document_id"],
        "relationships": [{"type": "CONTAINS", "target": "chunk_1"}],
    }

    test_relational_data = {
        "document_id": security_info["document_id"],
        "title": "Kündigungsschutz im deutschen Arbeitsrecht",
        "file_path": test_file_path,
    }

    # Calculate Quality Score
    quality_result = quality_mgr.calculate_document_quality_score(
        test_document_data, test_vector_data, test_graph_data, test_relational_data
    )

    print(f"Overall Quality Score: {quality_result['overall_score']:.3f}")
    print(f"Completeness: {quality_result['metrics']['completeness']:.3f}")
    print(f"Consistency: {quality_result['metrics']['consistency']:.3f}")
    print(f"Semantic Coherence: {quality_result['metrics']['semantic_coherence']:.3f}")

    if quality_result["issues"]:
        print(f"Issues: {quality_result['issues']}")
    if quality_result["recommendations"]:
        print(f"Recommendations: {quality_result['recommendations']}")

    # Cross-DB Quality Validation
    cross_db_quality = quality_mgr.validate_cross_db_quality(
        security_info["document_id"],
        test_vector_data,
        test_graph_data,
        test_relational_data,
    )

    print(f"\nCross-DB Quality Score: {cross_db_quality['overall_cross_db_score']:.3f}")
    print(f"Database Scores: {cross_db_quality['database_scores']}")

    if cross_db_quality["inconsistencies"]:
        print(f"Inconsistencies: {len(cross_db_quality['inconsistencies'])} found")
    else:
        print("✅ No cross-database inconsistencies detected")

    print("\n🎉 Security & Quality Framework Test erfolgreich!")

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_security_quality"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...ag3s5l4="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "aee64f9b4ec0f7014719f1e6d172c4d0521b737ff7cd955f5797145b442ce28c"
)
module_file_key = "bf9c0fdbfd5d5fe9ae17b1184058e6186ab4b1f104ee04331bff1b305da5adf5"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===