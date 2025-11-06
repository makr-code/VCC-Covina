"""Domain Models - Unified Process Schema (UPS).

Core entities for process modeling aligned with VPB strategy.

Entities:
- Process: Top-level process definition
- Step: Individual process step/activity
- Role: Organizational role
- OrgUnit: Organizational unit/department
- System: IT system/application
- Control: Governance control
- LegalRef: Legal reference/citation
- InfoObject: Information artifact with classification

All entities use:
- UUIDv7 for IDs
- Stable keys from domain
- created_at/updated_at timestamps
- Version tracking where applicable
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Process:
    """Top-level process definition.
    
    Attributes:
        id: UUIDv7 identifier
        key: Stable domain key (e.g., "bauleitplanung_brandenburg")
        title: Human-readable title
        version: Version string (e.g., "1.0", "2023-10")
        domain: Domain/category (e.g., "verwaltung", "bau")
        owner_org: Owning organizational unit
        status: Status (active, draft, deprecated)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        extra: Additional metadata
    """
    id: str
    key: str
    title: str
    version: str
    domain: Optional[str] = None
    owner_org: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    """Individual process step/activity.
    
    Attributes:
        id: UUIDv7 identifier
        process_id: Parent process ID
        order: Sequence order in process
        key: Stable step key (remains constant across versions)
        title: Step title
        description: Detailed description
        required: Whether step is mandatory
        duration_est: Estimated duration in days (optional)
        inputs: List of required input artifacts
        outputs: List of produced output artifacts
        control_points: List of control checkpoints
        extra: Additional metadata
    """
    id: str
    process_id: str
    order: int
    key: str
    title: str
    description: Optional[str] = None
    required: bool = True
    duration_est: Optional[int] = None
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Role:
    """Organizational role.
    
    Attributes:
        id: UUIDv7 identifier
        key: Stable role key
        name: Role name
        level: Hierarchical level (e.g., "operational", "tactical", "strategic")
        permissions: List of permission identifiers
        extra: Additional metadata
    """
    id: str
    key: str
    name: str
    level: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrgUnit:
    """Organizational unit/department.
    
    Attributes:
        id: UUIDv7 identifier
        key: Stable unit key
        name: Unit name
        parent_id: Parent unit ID (for hierarchy)
        type: Unit type (e.g., "department", "team", "office")
        extra: Additional metadata
    """
    id: str
    key: str
    name: str
    parent_id: Optional[str] = None
    type: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class System:
    """IT system/application.
    
    Attributes:
        id: UUIDv7 identifier
        key: Stable system key
        name: System name
        type: System type (e.g., "erp", "cms", "db")
        criticality: Criticality level (e.g., "high", "medium", "low")
        extra: Additional metadata
    """
    id: str
    key: str
    name: str
    type: Optional[str] = None
    criticality: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Control:
    """Governance control.
    
    Attributes:
        id: UUIDv7 identifier
        key: Stable control key
        name: Control name
        type: Control type (e.g., "approval", "review", "audit")
        objective: Control objective/purpose
        evidence: Required evidence/artifacts
        extra: Additional metadata
    """
    id: str
    key: str
    name: str
    type: Optional[str] = None
    objective: Optional[str] = None
    evidence: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LegalRef:
    """Legal reference/citation.
    
    Attributes:
        id: UUIDv7 identifier
        citation: Citation string (e.g., "§ 3 BauGB")
        type: Reference type (e.g., "gesetz", "verordnung", "richtlinie")
        uri: Optional URI to legal text
        extra: Additional metadata
    """
    id: str
    citation: str
    type: Optional[str] = None
    uri: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InfoObject:
    """Information artifact with classification.
    
    Attributes:
        id: UUIDv7 identifier
        key: Stable object key
        name: Object name/title
        classification: Security classification (e.g., "public", "internal", "confidential")
        pii: Whether contains personal data
        retention: Retention period in months (optional)
        extra: Additional metadata
    """
    id: str
    key: str
    name: str
    classification: Optional[str] = None
    pii: bool = False
    retention: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
