"""Domain Module - Unified Process Schema (UPS).

Core domain models for process representation.

Models:
- Process: Top-level process definition
- Step: Individual process step
- Role: Organizational role
- OrgUnit: Organizational unit
- System: IT system
- Control: Governance control
- LegalRef: Legal reference
- InfoObject: Information artifact

Usage:
    from processes.domain import Process, Step, Role
    
    process = Process(
        id="uuid-here",
        key="bauleitplanung_brandenburg",
        title="Bauleitplanung Brandenburg",
        version="2023-10"
    )
"""

from .models import (
    Process,
    Step,
    Role,
    OrgUnit,
    System,
    Control,
    LegalRef,
    InfoObject,
)

__all__ = [
    "Process",
    "Step",
    "Role",
    "OrgUnit",
    "System",
    "Control",
    "LegalRef",
    "InfoObject",
]
