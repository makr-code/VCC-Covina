"""
VCC Event System
Phase 2: Event-Driven Architecture

On-premise Kafka-based event system for VCC ecosystem communication.
No external vendor dependencies - uses self-hosted Apache Kafka.
"""

from .publisher import EventPublisher
from .consumer import EventConsumer
from .schemas import (
    DocumentIngestedEvent,
    DocumentProcessedEvent,
    ComplianceEvent,
    AuditLogEvent,
    VCCEventBase
)

__all__ = [
    "EventPublisher",
    "EventConsumer",
    "DocumentIngestedEvent",
    "DocumentProcessedEvent",
    "ComplianceEvent",
    "AuditLogEvent",
    "VCCEventBase"
]
