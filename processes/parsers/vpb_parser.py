"""
VPB JSON Parser - Converts VPB process definitions to UPS

Parses VPB JSON format (from docs/VPB_PROCESS_*.json examples) into
Unified Process Schema (UPS) domain models.

Supports:
- Process metadata (name, version, domain, status)
- Steps with types, roles, durations, controls
- Legal references (BauGB, BauNVO, etc.)
- Information objects (inputs/outputs)
- Temporal scheduling (effective dates, deadlines)
"""
from __future__ import annotations
import json
from datetime import datetime, date
from typing import Any
from pathlib import Path

from processes.domain.models import (
    Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject
)


class VPBParser:
    """
    Parse VPB JSON to UPS domain models.
    
    Expected VPB JSON structure:
    {
      "process": {
        "key": "bauleitplanung",
        "name": "Bauleitplanung",
        "version": "1.0",
        "domain": "Stadtplanung",
        "owner": "Planungsamt",
        "status": "active",
        "description": "...",
        "legal_refs": [...],
        "steps": [...]
      }
    }
    """
    
    def __init__(self):
        """Initialize parser."""
        self.roles: dict[str, Role] = {}
        self.org_units: dict[str, OrgUnit] = {}
        self.systems: dict[str, System] = {}
        self.controls: dict[str, Control] = {}
        self.legal_refs: dict[str, LegalRef] = {}
        self.info_objects: dict[str, InfoObject] = {}
    
    def parse_file(self, file_path: str | Path) -> Process:
        """
        Parse VPB JSON file to Process.
        
        Args:
            file_path: Path to VPB JSON file
            
        Returns:
            Process domain model with all entities
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return self.parse_dict(data)
    
    def parse_json(self, json_str: str) -> Process:
        """
        Parse VPB JSON string to Process.
        
        Args:
            json_str: VPB JSON string
            
        Returns:
            Process domain model with all entities
        """
        data = json.loads(json_str)
        return self.parse_dict(data)
    
    def parse_dict(self, data: dict[str, Any]) -> Process:
        """
        Parse VPB dict to Process.
        
        Args:
            data: VPB dict (expects "process" key)
            
        Returns:
            Process domain model with all entities
        """
        # Reset entity registries
        self.roles = {}
        self.org_units = {}
        self.systems = {}
        self.controls = {}
        self.legal_refs = {}
        self.info_objects = {}
        
        # Get process data
        proc_data = data.get("process", data)  # Allow both {"process": ...} and direct {...}
        
        # Parse metadata
        process = Process(
            key=proc_data.get("key", "unknown"),
            name=proc_data.get("name", "Unknown Process"),
            version=proc_data.get("version", "1.0"),
            description=proc_data.get("description"),
            source=proc_data.get("source", "VPB"),
            source_format="json",
            domain=proc_data.get("domain"),
            owner=proc_data.get("owner"),
            status=proc_data.get("status", "draft"),
            metadata=proc_data.get("metadata", {}),
        )
        
        # Parse legal references (process-level)
        for ref_data in proc_data.get("legal_refs", []):
            legal_ref = self._parse_legal_ref(ref_data)
            self.legal_refs[legal_ref.id] = legal_ref
        
        # Parse steps
        steps_data = proc_data.get("steps", [])
        for step_data in steps_data:
            step = self._parse_step(step_data)
            # Steps are not directly attached to Process in UPS (graph relation instead)
        
        return process
    
    def _parse_step(self, data: dict[str, Any]) -> Step:
        """Parse step data to Step model."""
        step = Step(
            key=data.get("key", "unknown_step"),
            name=data.get("name", "Unknown Step"),
            type=data.get("type", "task"),
            description=data.get("description"),
            instructions=data.get("instructions"),
            duration_days=data.get("duration_days"),
            mandatory=data.get("mandatory", True),
            automated=data.get("automated", False),
            metadata=data.get("metadata", {}),
        )
        
        # Parse role (if present)
        if "role" in data:
            role = self._parse_role(data["role"])
            self.roles[role.id] = role
            step.metadata["role_id"] = role.id
        
        # Parse org_unit (if present)
        if "org_unit" in data:
            org_unit = self._parse_org_unit(data["org_unit"])
            self.org_units[org_unit.id] = org_unit
            step.metadata["org_unit_id"] = org_unit.id
        
        # Parse systems (if present)
        for sys_data in data.get("systems", []):
            system = self._parse_system(sys_data)
            self.systems[system.id] = system
            step.metadata.setdefault("system_ids", []).append(system.id)
        
        # Parse controls (if present)
        for ctrl_data in data.get("controls", []):
            control = self._parse_control(ctrl_data)
            self.controls[control.id] = control
            step.metadata.setdefault("control_ids", []).append(control.id)
        
        # Parse legal refs (if present)
        for ref_data in data.get("legal_refs", []):
            legal_ref = self._parse_legal_ref(ref_data)
            self.legal_refs[legal_ref.id] = legal_ref
            step.metadata.setdefault("legal_ref_ids", []).append(legal_ref.id)
        
        # Parse info objects (inputs/outputs)
        for input_data in data.get("inputs", []):
            info_obj = self._parse_info_object(input_data, is_input=True)
            self.info_objects[info_obj.id] = info_obj
            step.metadata.setdefault("input_ids", []).append(info_obj.id)
        
        for output_data in data.get("outputs", []):
            info_obj = self._parse_info_object(output_data, is_input=False)
            self.info_objects[info_obj.id] = info_obj
            step.metadata.setdefault("output_ids", []).append(info_obj.id)
        
        return step
    
    def _parse_role(self, data: dict[str, Any] | str) -> Role:
        """Parse role data to Role model."""
        if isinstance(data, str):
            # Simple string role (just name)
            role_key = data.lower().replace(" ", "_")
            if role_key in self.roles:
                return list(self.roles.values())[0]  # Return first match by key
            return Role(name=data, level="unknown")
        
        # Dict role (full data)
        role_key = data.get("name", "unknown").lower().replace(" ", "_")
        
        return Role(
            name=data.get("name", "Unknown Role"),
            level=data.get("level", "unknown"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )
    
    def _parse_org_unit(self, data: dict[str, Any] | str) -> OrgUnit:
        """Parse org_unit data to OrgUnit model."""
        if isinstance(data, str):
            return OrgUnit(name=data, level="unknown")
        
        return OrgUnit(
            name=data.get("name", "Unknown OrgUnit"),
            level=data.get("level", "unknown"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )
    
    def _parse_system(self, data: dict[str, Any] | str) -> System:
        """Parse system data to System model."""
        if isinstance(data, str):
            return System(name=data, type="unknown")
        
        return System(
            name=data.get("name", "Unknown System"),
            type=data.get("type", "application"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )
    
    def _parse_control(self, data: dict[str, Any] | str) -> Control:
        """Parse control data to Control model."""
        if isinstance(data, str):
            return Control(name=data, type="manual", criticality="medium")
        
        return Control(
            name=data.get("name", "Unknown Control"),
            type=data.get("type", "manual"),
            criticality=data.get("criticality", "medium"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )
    
    def _parse_legal_ref(self, data: dict[str, Any] | str) -> LegalRef:
        """Parse legal_ref data to LegalRef model."""
        if isinstance(data, str):
            # Simple string like "BauGB §1" or "BauNVO §17"
            parts = data.split()
            source = parts[0] if parts else "Unknown"
            article = parts[1] if len(parts) > 1 else None
            return LegalRef(source=source, article=article)
        
        return LegalRef(
            source=data.get("source", "Unknown"),
            article=data.get("article"),
            paragraph=data.get("paragraph"),
            description=data.get("description"),
            url=data.get("url"),
            metadata=data.get("metadata", {}),
        )
    
    def _parse_info_object(self, data: dict[str, Any] | str, is_input: bool) -> InfoObject:
        """Parse info_object data to InfoObject model."""
        if isinstance(data, str):
            return InfoObject(
                key=data.lower().replace(" ", "_"),
                name=data,
                type="document" if is_input else "output",
                required=True,
            )
        
        return InfoObject(
            key=data.get("key", data.get("name", "unknown").lower().replace(" ", "_")),
            name=data.get("name", "Unknown InfoObject"),
            type=data.get("type", "document"),
            description=data.get("description"),
            required=data.get("required", True),
            retention_days=data.get("retention_days"),
            metadata=data.get("metadata", {}),
        )
    
    def get_all_entities(self) -> dict[str, list[Any]]:
        """
        Get all parsed entities from last parse operation.
        
        Returns:
            Dict with entity types as keys and lists of entities as values
        """
        return {
            "roles": list(self.roles.values()),
            "org_units": list(self.org_units.values()),
            "systems": list(self.systems.values()),
            "controls": list(self.controls.values()),
            "legal_refs": list(self.legal_refs.values()),
            "info_objects": list(self.info_objects.values()),
        }
