#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_vpb_schema"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...FUVcsA=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "7151ba335a08a2880ccde29a06f6de38e25f01c2ff3fd8fadbd8d31ea06f2fc8"
)
module_file_key = "1a4fb3a34126433a7bd6765330a9ef87f266a8450a1f50be1c28863a0d6ebf2b"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
UDS3 VPB Schema Definition
Datenmodelle für VPB Process Designer Integration mit UDS3 Backend

Autor: UDS3 Development Team
Datum: 22. August 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import uuid


class VPBProcessStatus(Enum):
    """Status eines VPB-Prozesses"""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
    UNDER_REVIEW = "under_review"


class VPBAuthorityLevel(Enum):
    """Behördenebene für Verwaltungsprozesse"""

    BUND = "bund"
    LAND = "land"
    KREIS = "kreis"
    GEMEINDE = "gemeinde"
    SONSTIGE = "sonstige"


class VPBLegalContext(Enum):
    """Rechtlicher Kontext des Prozesses"""

    BAURECHT = "baurecht"
    UMWELTRECHT = "umweltrecht"
    GEWERBERECHT = "gewerberecht"
    SOZIALRECHT = "sozialrecht"
    STEUERRECHT = "steuerrecht"
    VERWALTUNGSRECHT_ALLGEMEIN = "verwaltungsrecht_allgemein"
    SONSTIGES = "sonstiges"


@dataclass
class VPBElementData:
    """VPB-Element für Database Storage"""

    element_id: str
    element_type: str
    name: str
    x: float
    y: float
    width: float = 100
    height: float = 60
    description: str = ""
    legal_basis: str = ""
    competent_authority: str = ""
    deadline_days: Optional[int] = None
    swimlane: str = ""
    geo_relevance: bool = False
    admin_level: Optional[int] = None

    # UDS3-spezifische Metadaten
    compliance_tags: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    automation_potential: float = 0.0  # 0-1 Score
    citizen_impact: str = "low"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für JSON-Serialisierung"""
        return {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "name": self.name,
            "position": [self.x, self.y],
            "width": self.width,
            "height": self.height,
            "description": self.description,
            "legal_basis": self.legal_basis,
            "competent_authority": self.competent_authority,
            "deadline_days": self.deadline_days,
            "swimlane": self.swimlane,
            "geo_relevance": self.geo_relevance,
            "admin_level": self.admin_level,
            "compliance_tags": self.compliance_tags,
            "risk_level": self.risk_level,
            "automation_potential": self.automation_potential,
            "citizen_impact": self.citizen_impact,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VPBElementData":
        """Erstellt VPBElementData aus Dictionary"""
        # Position Array zu x,y konvertieren
        if "position" in data:
            data["x"] = data["position"][0]
            data["y"] = data["position"][1]
            del data["position"]

        # Defaults für fehlende UDS3-Felder
        data.setdefault("compliance_tags", [])
        data.setdefault("risk_level", "low")
        data.setdefault("automation_potential", 0.0)
        data.setdefault("citizen_impact", "low")

        return cls(**data)


@dataclass
class VPBConnectionData:
    """VPB-Verbindung für Database Storage"""

    connection_id: str
    source_element_id: str
    target_element_id: str
    source_point: Tuple[float, float] = (0, 0)
    target_point: Tuple[float, float] = (0, 0)
    connection_type: str = "standard"
    condition: str = ""
    label: str = ""
    style: str = "solid"

    # UDS3-spezifische Metadaten
    probability: float = 1.0  # Wahrscheinlichkeit der Verbindung (0-1)
    average_duration_days: Optional[int] = None  # Durchschnittliche Dauer
    bottleneck_indicator: bool = False  # Ist dies ein Engpass?
    compliance_critical: bool = False  # Compliance-kritische Verbindung?

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für JSON-Serialisierung"""
        return {
            "connection_id": self.connection_id,
            "source_element_id": self.source_element_id,
            "target_element_id": self.target_element_id,
            "source_point": list(self.source_point),
            "target_point": list(self.target_point),
            "connection_type": self.connection_type,
            "condition": self.condition,
            "label": self.label,
            "style": self.style,
            "probability": self.probability,
            "average_duration_days": self.average_duration_days,
            "bottleneck_indicator": self.bottleneck_indicator,
            "compliance_critical": self.compliance_critical,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VPBConnectionData":
        """Erstellt VPBConnectionData aus Dictionary"""
        # Defaults für fehlende UDS3-Felder
        data.setdefault("probability", 1.0)
        data.setdefault("average_duration_days", None)
        data.setdefault("bottleneck_indicator", False)
        data.setdefault("compliance_critical", False)

        # Tuple-Konvertierung für Punkte
        if "source_point" in data:
            data["source_point"] = tuple(data["source_point"])
        if "target_point" in data:
            data["target_point"] = tuple(data["target_point"])

        return cls(**data)


@dataclass
class VPBProcessRecord:
    """Kompletter VPB-Prozess für UDS3 Database Storage"""

    process_id: str
    name: str
    description: str
    version: str = "1.0"
    status: VPBProcessStatus = VPBProcessStatus.DRAFT

    # Prozess-Inhalte
    elements: List[VPBElementData] = field(default_factory=list)
    connections: List[VPBConnectionData] = field(default_factory=list)

    # Metadaten
    legal_context: VPBLegalContext = VPBLegalContext.VERWALTUNGSRECHT_ALLGEMEIN
    authority_level: VPBAuthorityLevel = VPBAuthorityLevel.GEMEINDE
    responsible_authority: str = ""
    involved_authorities: List[str] = field(default_factory=list)
    legal_basis: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # UDS3 Intelligence
    complexity_score: float = 0.0  # 0-1 Komplexitätsbewertung
    automation_score: float = 0.0  # 0-1 Automatisierungspotential
    compliance_score: float = 0.0  # 0-1 Compliance-Bewertung
    citizen_satisfaction_score: float = 0.0  # 0-1 Bürgerzufriedenheit

    # Geografische Relevanz
    geo_scope: str = "Deutschland"
    geo_coordinates: Optional[Tuple[float, float]] = None  # Lat/Lon falls relevant

    # Benutzer/Versionierung
    created_by: str = "system"
    last_modified_by: str = "system"
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Nach Initialisierung aufgerufen"""
        if not self.process_id:
            self.process_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert kompletten Prozess zu Dictionary"""
        return {
            "process_metadata": {
                "process_id": self.process_id,
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "status": self.status.value,
                "legal_context": self.legal_context.value,
                "authority_level": self.authority_level.value,
                "responsible_authority": self.responsible_authority,
                "involved_authorities": self.involved_authorities,
                "legal_basis": self.legal_basis,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "created_by": self.created_by,
                "last_modified_by": self.last_modified_by,
                "complexity_score": self.complexity_score,
                "automation_score": self.automation_score,
                "compliance_score": self.compliance_score,
                "citizen_satisfaction_score": self.citizen_satisfaction_score,
                "geo_scope": self.geo_scope,
                "geo_coordinates": self.geo_coordinates,
                "tags": self.tags,
            },
            "elements": [element.to_dict() for element in self.elements],
            "connections": [connection.to_dict() for connection in self.connections],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VPBProcessRecord":
        """Erstellt VPBProcessRecord aus Dictionary"""
        metadata = data.get("process_metadata", {})

        # Enums konvertieren
        status = VPBProcessStatus(metadata.get("status", "draft"))
        legal_context = VPBLegalContext(
            metadata.get("legal_context", "verwaltungsrecht_allgemein")
        )
        authority_level = VPBAuthorityLevel(metadata.get("authority_level", "gemeinde"))

        # Timestamps konvertieren
        created_at = datetime.fromisoformat(
            metadata.get("created_at", datetime.now().isoformat())
        )
        updated_at = datetime.fromisoformat(
            metadata.get("updated_at", datetime.now().isoformat())
        )

        # Elements und Connections konvertieren
        elements = [VPBElementData.from_dict(elem) for elem in data.get("elements", [])]
        connections = [
            VPBConnectionData.from_dict(conn) for conn in data.get("connections", [])
        ]

        return cls(
            process_id=metadata.get("process_id", str(uuid.uuid4())),
            name=metadata.get("name", "Unnamed Process"),
            description=metadata.get("description", ""),
            version=metadata.get("version", "1.0"),
            status=status,
            elements=elements,
            connections=connections,
            legal_context=legal_context,
            authority_level=authority_level,
            responsible_authority=metadata.get("responsible_authority", ""),
            involved_authorities=metadata.get("involved_authorities", []),
            legal_basis=metadata.get("legal_basis", []),
            created_at=created_at,
            updated_at=updated_at,
            complexity_score=metadata.get("complexity_score", 0.0),
            automation_score=metadata.get("automation_score", 0.0),
            compliance_score=metadata.get("compliance_score", 0.0),
            citizen_satisfaction_score=metadata.get("citizen_satisfaction_score", 0.0),
            geo_scope=metadata.get("geo_scope", "Deutschland"),
            geo_coordinates=metadata.get("geo_coordinates"),
            created_by=metadata.get("created_by", "system"),
            last_modified_by=metadata.get("last_modified_by", "system"),
            tags=metadata.get("tags", []),
        )

    def update_scores(self):
        """Berechnet Intelligence-Scores basierend auf Prozess-Inhalten"""
        # Komplexität basierend auf Anzahl Elemente und Verbindungen
        self.complexity_score = min(
            1.0, (len(self.elements) + len(self.connections)) / 50.0
        )

        # Automatisierungspotential basierend auf Element-Typen
        automation_elements = sum(
            1 for elem in self.elements if elem.element_type in ["FUNCTION", "GATEWAY"]
        )
        self.automation_score = automation_elements / max(1, len(self.elements))

        # Compliance basierend auf rechtlichen Grundlagen
        legal_elements = sum(1 for elem in self.elements if elem.legal_basis)
        self.compliance_score = legal_elements / max(1, len(self.elements))

        # Update timestamp
        self.updated_at = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        """Erstellt Zusammenfassung des Prozesses"""
        return {
            "process_id": self.process_id,
            "name": self.name,
            "status": self.status.value,
            "elements_count": len(self.elements),
            "connections_count": len(self.connections),
            "complexity_score": self.complexity_score,
            "automation_score": self.automation_score,
            "compliance_score": self.compliance_score,
            "last_updated": self.updated_at.isoformat(),
            "authority_level": self.authority_level.value,
            "legal_context": self.legal_context.value,
        }


# Hilfsfunktionen für Schema-Validierung


def validate_vpb_process(process_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validiert VPB-Prozessdaten"""
    errors: list[Any] = []

    # Basis-Validierung
    if not process_data.get("process_metadata", {}).get("name"):
        errors.append("Prozessname ist erforderlich")

    if not process_data.get("elements"):
        errors.append("Mindestens ein Element ist erforderlich")

    # Element-Validierung
    element_ids = set()
    for elem in process_data.get("elements", []):
        if not elem.get("element_id"):
            errors.append("Element-ID fehlt")
        elif elem["element_id"] in element_ids:
            errors.append(f"Doppelte Element-ID: {elem['element_id']}")
        else:
            element_ids.add(elem["element_id"])

    # Verbindungs-Validierung
    for conn in process_data.get("connections", []):
        source = conn.get("source_element_id")
        target = conn.get("target_element_id")

        if source not in element_ids:
            errors.append(
                f"Verbindung verweist auf unbekanntes Source-Element: {source}"
            )
        if target not in element_ids:
            errors.append(
                f"Verbindung verweist auf unbekanntes Target-Element: {target}"
            )

    return len(errors) == 0, errors


def migrate_legacy_vpb_data(legacy_data: Dict[str, Any]) -> VPBProcessRecord:
    """Migriert Legacy-VPB-Daten zu neuem Schema"""
    # Legacy-Format von vpb_process_designer.py zu UDS3-Schema

    process_record = VPBProcessRecord(
        process_id=legacy_data.get("process_id", str(uuid.uuid4())),
        name=legacy_data.get("name", "Migrierter Prozess"),
        description=legacy_data.get("description", ""),
    )

    # Elements migrieren
    for elem_data in legacy_data.get("elements", []):
        element = VPBElementData.from_dict(elem_data)
        process_record.elements.append(element)

    # Connections migrieren
    for conn_data in legacy_data.get("connections", []):
        connection = VPBConnectionData.from_dict(conn_data)
        process_record.connections.append(connection)

    # Scores berechnen
    process_record.update_scores()

    return process_record


if __name__ == "__main__":
    # Test der Schema-Funktionalität
    print("UDS3 VPB Schema Test")

    # Test-Prozess erstellen
    test_process = VPBProcessRecord(
        process_id="TEST001",
        name="Test-Bauleitplanungsverfahren",
        description="Test-Prozess für Schema-Validierung",
    )

    # Test-Element hinzufügen
    test_element = VPBElementData(
        element_id="E001",
        element_type="START_EVENT",
        name="Planungsauftrag",
        x=100,
        y=100,
        legal_basis="§ 1 BauGB",
    )
    test_process.elements.append(test_element)

    # Zu Dictionary konvertieren
    process_dict = test_process.to_dict()
    print(f"Prozess serialisiert: {process_dict['process_metadata']['name']}")

    # Validierung testen
    is_valid, errors = validate_vpb_process(process_dict)
    print(f"Validierung: {'✅ Erfolgreich' if is_valid else '❌ Fehler'}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    print("Schema-Test abgeschlossen")
