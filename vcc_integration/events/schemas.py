"""
VCC Event Schemas
Phase 2: Event-Driven Architecture

Pydantic models for VCC ecosystem events.
Uses Avro-compatible schemas for Kafka Schema Registry.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    """VCC Event Types"""
    DOCUMENT_INGESTED = "document.ingested"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_CLASSIFIED = "document.classified"
    DOCUMENT_INDEXED = "document.indexed"
    COMPLIANCE_CHECK = "compliance.check"
    COMPLIANCE_RESULT = "compliance.result"
    AUDIT_LOG = "audit.log"
    VERITAS_REQUEST = "veritas.request"
    VERITAS_RESPONSE = "veritas.response"
    THEMIS_SYNC = "themis.sync"
    CLARA_CLASSIFICATION = "clara.classification"
    ARGUS_MEDIA = "argus.media"


class VCCEventBase(BaseModel):
    """Base class for all VCC events"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    source_service: str = "covina"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    version: str = "1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            "key": self.event_id,
            "value": self.model_dump_json(),
            "headers": {
                "event_type": self.event_type.value,
                "source": self.source_service,
                "correlation_id": self.correlation_id or "",
                "version": self.version
            }
        }


class DocumentMetadata(BaseModel):
    """Document metadata for events"""
    document_id: str
    filename: str
    file_type: str
    file_size: int
    checksum: str
    language: Optional[str] = None
    classification: Optional[str] = None
    confidence_score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentIngestedEvent(VCCEventBase):
    """Event emitted when a document is ingested into Covina"""
    event_type: EventType = EventType.DOCUMENT_INGESTED
    job_id: str
    document: DocumentMetadata
    storage_location: str
    processing_status: str = "pending"
    
    def get_topic(self) -> str:
        return "vcc.documents.ingested"


class ProcessingResult(BaseModel):
    """Processing result details"""
    stage: str
    success: bool
    duration_ms: int
    output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class DocumentProcessedEvent(VCCEventBase):
    """Event emitted when document processing is complete"""
    event_type: EventType = EventType.DOCUMENT_PROCESSED
    job_id: str
    document_id: str
    processing_results: List[ProcessingResult]
    final_status: str
    total_duration_ms: int
    embeddings_generated: bool = False
    graph_updated: bool = False
    
    def get_topic(self) -> str:
        return "vcc.documents.processed"


class ComplianceCheckType(str, Enum):
    """Types of compliance checks"""
    DSGVO = "dsgvo"
    PII_DETECTION = "pii_detection"
    RETENTION_POLICY = "retention_policy"
    ACCESS_CONTROL = "access_control"
    LEGAL_REFERENCE = "legal_reference"


class ComplianceEvent(VCCEventBase):
    """Event for compliance-related actions"""
    event_type: EventType = EventType.COMPLIANCE_CHECK
    check_type: ComplianceCheckType
    document_id: str
    user_id: str
    action: str
    result: str
    severity: str = "info"  # info, warning, critical
    details: Dict[str, Any] = Field(default_factory=dict)
    remediation_required: bool = False
    
    def get_topic(self) -> str:
        return "vcc.compliance.events"


class AuditAction(str, Enum):
    """Audit log action types"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    PERMISSION_CHANGE = "permission_change"


class AuditLogEvent(VCCEventBase):
    """Event for audit logging"""
    event_type: EventType = EventType.AUDIT_LOG
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def get_topic(self) -> str:
        return "vcc.audit.log"


class VeritasRequestEvent(VCCEventBase):
    """Event for requesting VERITAS legal intelligence"""
    event_type: EventType = EventType.VERITAS_REQUEST
    document_id: str
    request_type: str  # legal_reference, entity_extraction, compliance_check
    content_hash: str
    priority: str = "normal"
    
    def get_topic(self) -> str:
        return "vcc.veritas.requests"


class VeritasResponseEvent(VCCEventBase):
    """Event with VERITAS processing results"""
    event_type: EventType = EventType.VERITAS_RESPONSE
    request_id: str
    document_id: str
    legal_references: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_findings: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: int
    
    def get_topic(self) -> str:
        return "vcc.veritas.responses"


class ThemisSyncEvent(VCCEventBase):
    """Event for Themis database synchronization"""
    event_type: EventType = EventType.THEMIS_SYNC
    operation: str  # insert, update, delete, sync_all
    table_name: str
    record_id: str
    data: Dict[str, Any]
    sync_direction: str = "covina_to_themis"  # or themis_to_covina
    
    def get_topic(self) -> str:
        return "vcc.themis.sync"
