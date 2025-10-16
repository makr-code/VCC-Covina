#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_process_mining"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...TTkiew=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "276d903bbf34948647b9c9f1ee5876a13f24c022126e4e4a1252ccd51f540ec4"
)
module_file_key = "b1f686399a557cb9eded6191f957efdb685f13f49f2cd08e7ab88b42f0e52519"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
UDS3 Process Mining & Workflow Analysis
Spezielle Analyse für Betriebsanweisungen und Prozessdokumente

Diese Module sind GOLD für die Graph Database, da sie:
- Explizite Prozessschritte definieren
- Rollen und Zuständigkeiten festlegen
- Entscheidungswege dokumentieren
- Workflows und Abhängigkeiten beschreiben
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import re
from uds3_admin_types import AdminDocumentType


class ProcessElementType(Enum):
    """Typen von Prozesselementen in Betriebsanweisungen"""

    PROCESS_STEP = "step"  # Einzelner Arbeitsschritt
    DECISION_POINT = "decision"  # Entscheidungspunkt
    ROLE_ASSIGNMENT = "role"  # Rollenzuweisung
    TRIGGER_EVENT = "trigger"  # Auslöser/Ereignis
    OUTPUT_ARTIFACT = "output"  # Ergebnis/Dokument
    QUALITY_GATE = "quality_gate"  # Qualitätsprüfung
    ESCALATION = "escalation"  # Eskalation
    PARALLEL_BRANCH = "parallel"  # Parallele Bearbeitung
    MERGE_POINT = "merge"  # Zusammenführung
    WAIT_STATE = "wait"  # Wartezustand


class ProcessRelationType(Enum):
    """Beziehungstypen zwischen Prozesselementen"""

    FOLLOWS = "follows"  # Schritt A folgt auf B
    TRIGGERS = "triggers"  # A löst B aus
    REQUIRES = "requires"  # A benötigt B
    PRODUCES = "produces"  # A erzeugt B
    INVOLVES_ROLE = "involves_role"  # Schritt involviert Rolle
    ESCALATES_TO = "escalates_to"  # Eskaliert zu
    VALIDATES = "validates"  # Prüft/validiert
    DEPENDS_ON = "depends_on"  # Hängt ab von
    PARALLEL_TO = "parallel_to"  # Parallel zu
    ALTERNATIVE_TO = "alternative_to"  # Alternative zu


@dataclass
class ProcessElement:
    """Ein Element in einem Verwaltungsprozess"""

    id: str
    element_type: ProcessElementType
    title: str
    description: str
    assigned_role: Optional[str] = None
    duration_estimate: Optional[str] = None
    legal_basis: Optional[str] = None
    quality_criteria: Optional[str] = None
    automation_potential: Optional[str] = None


@dataclass
class ProcessRelationship:
    """Beziehung zwischen Prozesselementen"""

    source_id: str
    target_id: str
    relationship_type: ProcessRelationType
    condition: Optional[str] = None
    probability: Optional[float] = None


class ProcessWorkflowExtractor:
    """
    Extrahiert Workflow-Informationen aus Betriebsanweisungen

    Das ist der GOLDSCHATZ für die Graph Database!
    """

    def __init__(self):
        self.step_patterns = self._create_step_patterns()
        self.role_patterns = self._create_role_patterns()
        self.decision_patterns = self._create_decision_patterns()

    def _create_step_patterns(self) -> List[str]:
        """Regex-Patterns für Prozessschritte"""
        return [
            r"(?:Schritt|Step)\s+(\d+)[:.]?\s*(.+?)(?=(?:Schritt|Step|\n\n|$))",
            r"(\d+)\.\s*(.+?)(?=\d+\.|$)",
            r"(?:Zunächst|Dann|Anschließend|Daraufhin|Abschließend)\s+(.+?)(?=\.|;)",
            r"(?:Der\s+\w+|Die\s+\w+)\s+(prüft|bearbeitet|entscheidet|genehmigt)\s+(.+?)(?=\.|;)",
            r"(?:Es\s+wird|Es\s+ist)\s+(.+?)\s+(?:zu\s+prüfen|durchzuführen|zu\s+beachten)",
        ]

    def _create_role_patterns(self) -> List[str]:
        """Patterns für Rollen und Zuständigkeiten"""
        return [
            r"(?:Der|Die)\s+([A-ZÄÖÜ][a-zäöüß]+(?:leiter|sachbearbeiter|referent|mitarbeiter|beauftragte))\s+(?:ist\s+zuständig|bearbeitet|prüft|entscheidet)",
            r"(?:Zuständig|Verantwortlich):\s*([^.\n]+)",
            r"(?:Unterschriftsberechtigt|Genehmigungsbefugnis):\s*([^.\n]+)",
            r"(?:Bei\s+Problemen|Im\s+Zweifel)\s+(?:wenden\s+Sie\s+sich\s+an|kontaktieren\s+Sie)\s+([^.\n]+)",
        ]

    def _create_decision_patterns(self) -> List[str]:
        """Patterns für Entscheidungspunkte"""
        return [
            r"(?:Falls|Wenn|Sofern)\s+(.+?),?\s+(?:dann|so)\s+(.+?)(?=\.|;|Falls|Wenn)",
            r"(?:Ist|Sind)\s+(.+?)\s+(?:erfüllt|vorhanden|gegeben),?\s+(?:wird|erfolgt|dann)\s+(.+?)(?=\.|;)",
            r"(?:Andernfalls|Sonst|Alternativ)\s+(.+?)(?=\.|;)",
            r"(?:Je\s+nach|Abhängig\s+von)\s+(.+?)\s+(?:wird|erfolgt)\s+(.+?)(?=\.|;)",
        ]

    def extract_process_elements(
        self, content: str, document_title: str
    ) -> List[ProcessElement]:
        """Extrahiert Prozesselemente aus Betriebsanweisungstext"""
        elements: list[Any] = []
        element_counter = 1

        # Schritt-Extraktion
        for pattern in self.step_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                # Wähle die letzte Gruppe oder die gesamte Match
                description = (
                    match.group(len(match.groups()))
                    if match.groups()
                    else match.group(0)
                )

                element = ProcessElement(
                    id=f"element_{element_counter}",
                    element_type=ProcessElementType.PROCESS_STEP,
                    title=f"Schritt {element_counter}",
                    description=description.strip(),
                    automation_potential=self._assess_automation_potential(description),
                )
                elements.append(element)
                element_counter += 1

        # Entscheidungspunkt-Extraktion
        for pattern in self.decision_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                element = ProcessElement(
                    id=f"decision_{element_counter}",
                    element_type=ProcessElementType.DECISION_POINT,
                    title=f"Entscheidung {element_counter}",
                    description=match.group(1).strip()
                    if match.groups()
                    else match.group(0).strip(),
                )
                elements.append(element)
                element_counter += 1

        return elements

    def extract_role_assignments(self, content: str) -> List[ProcessElement]:
        """Extrahiert Rollenzuweisungen"""
        roles: list[Any] = []
        role_counter = 1

        for pattern in self.role_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                role = ProcessElement(
                    id=f"role_{role_counter}",
                    element_type=ProcessElementType.ROLE_ASSIGNMENT,
                    title=match.group(1).strip(),
                    description=f"Rolle: {match.group(1).strip()}",
                    assigned_role=match.group(1).strip(),
                )
                roles.append(role)
                role_counter += 1

        return roles

    def _assess_automation_potential(self, description: str) -> str:
        """Bewertet Automatisierungspotential eines Prozessschritts"""
        description_lower = description.lower()

        # Hohe Automatisierung möglich
        if any(
            word in description_lower
            for word in [
                "prüfen ob",
                "vergleichen",
                "berechnen",
                "erstellen",
                "versenden",
                "benachrichtigen",
                "archivieren",
                "übertragen",
            ]
        ):
            return "HIGH"

        # Mittlere Automatisierung möglich
        if any(
            word in description_lower
            for word in ["dokumentieren", "erfassen", "weiterleiten", "terminieren"]
        ):
            return "MEDIUM"

        # Geringe Automatisierung (menschliche Entscheidung erforderlich)
        if any(
            word in description_lower
            for word in [
                "entscheiden",
                "beurteilen",
                "abwägen",
                "bewerten",
                "genehmigen",
            ]
        ):
            return "LOW"

        return "UNKNOWN"

    def create_workflow_graph(
        self, elements: List[ProcessElement]
    ) -> List[ProcessRelationship]:
        """Erstellt Graph-Beziehungen zwischen Prozesselementen"""
        relationships: list[Any] = []

        # Sequentielle Verknüpfung der Schritte
        steps = [
            e for e in elements if e.element_type == ProcessElementType.PROCESS_STEP
        ]
        for i in range(len(steps) - 1):
            rel = ProcessRelationship(
                source_id=steps[i].id,
                target_id=steps[i + 1].id,
                relationship_type=ProcessRelationType.FOLLOWS,
            )
            relationships.append(rel)

        # Rollenzuweisungen verknüpfen
        roles = [
            e for e in elements if e.element_type == ProcessElementType.ROLE_ASSIGNMENT
        ]
        for role in roles:
            for step in steps:
                if (
                    role.assigned_role
                    and role.assigned_role.lower() in step.description.lower()
                ):
                    rel = ProcessRelationship(
                        source_id=step.id,
                        target_id=role.id,
                        relationship_type=ProcessRelationType.INVOLVES_ROLE,
                    )
                    relationships.append(rel)

        return relationships


class ProcessComplexityAnalyzer:
    """Analysiert die Komplexität von Verwaltungsprozessen"""

    def analyze_process_document(
        self, doc_type: AdminDocumentType, content: str, title: str
    ) -> Dict:
        """Führt vollständige Prozessanalyse durch"""

        if doc_type not in [
            AdminDocumentType.ORG_MANUAL,
            AdminDocumentType.PROCESS_INSTRUCTION,
            AdminDocumentType.WORKFLOW_DEFINITION,
            AdminDocumentType.COMPLETION_GUIDE,
        ]:
            return {"analysis": "Not a process document"}

        extractor = ProcessWorkflowExtractor()

        # Prozesselemente extrahieren
        elements = extractor.extract_process_elements(content, title)
        roles = extractor.extract_role_assignments(content)
        all_elements = elements + roles

        # Workflow-Graph erstellen
        relationships = extractor.create_workflow_graph(all_elements)

        # Komplexitätsmetriken berechnen
        complexity_metrics = {
            "total_elements": len(all_elements),
            "process_steps": len(
                [
                    e
                    for e in all_elements
                    if e.element_type == ProcessElementType.PROCESS_STEP
                ]
            ),
            "decision_points": len(
                [
                    e
                    for e in all_elements
                    if e.element_type == ProcessElementType.DECISION_POINT
                ]
            ),
            "roles_involved": len(
                [
                    e
                    for e in all_elements
                    if e.element_type == ProcessElementType.ROLE_ASSIGNMENT
                ]
            ),
            "relationships": len(relationships),
            "automation_high": len(
                [
                    e
                    for e in all_elements
                    if getattr(e, "automation_potential", "") == "HIGH"
                ]
            ),
            "automation_medium": len(
                [
                    e
                    for e in all_elements
                    if getattr(e, "automation_potential", "") == "MEDIUM"
                ]
            ),
            "automation_low": len(
                [
                    e
                    for e in all_elements
                    if getattr(e, "automation_potential", "") == "LOW"
                ]
            ),
        }

        # Graph-Strukturen für Neo4j
        neo4j_nodes = [
            {
                "id": elem.id,
                "type": elem.element_type.value,
                "title": elem.title,
                "description": elem.description,
                "assigned_role": elem.assigned_role,
                "automation_potential": getattr(elem, "automation_potential", None),
            }
            for elem in all_elements
        ]

        neo4j_relationships = [
            {
                "source": rel.source_id,
                "target": rel.target_id,
                "type": rel.relationship_type.value,
                "condition": rel.condition,
            }
            for rel in relationships
        ]

        return {
            "document_analysis": {
                "document_type": doc_type.value,
                "title": title,
                "complexity_metrics": complexity_metrics,
            },
            "process_elements": [
                {
                    "id": e.id,
                    "type": e.element_type.value,
                    "title": e.title,
                    "description": e.description,
                    "automation_potential": getattr(e, "automation_potential", None),
                }
                for e in all_elements
            ],
            "graph_structure": {
                "nodes": neo4j_nodes,
                "relationships": neo4j_relationships,
            },
            "recommendations": self._generate_recommendations(
                complexity_metrics, all_elements
            ),
        }

    def _generate_recommendations(
        self, metrics: Dict, elements: List[ProcessElement]
    ) -> List[str]:
        """Generiert Empfehlungen basierend auf Prozessanalyse"""
        recommendations: list[Any] = []

        if metrics["automation_high"] > 3:
            recommendations.append(
                "🤖 Hoher Automatisierungsgrad möglich - RPA-Implementierung prüfen"
            )

        if metrics["roles_involved"] > 5:
            recommendations.append(
                "👥 Viele Rollen beteiligt - Koordinationsaufwand beachten"
            )

        if metrics["decision_points"] > 2:
            recommendations.append(
                "🔀 Komplexe Entscheidungsstruktur - Regelwerk digitalisieren"
            )

        if metrics["process_steps"] > 10:
            recommendations.append(
                "📋 Langer Prozess - Zwischenstände/Meilensteine definieren"
            )

        return recommendations


# Export
__all__ = [
    "ProcessElementType",
    "ProcessRelationType",
    "ProcessElement",
    "ProcessRelationship",
    "ProcessWorkflowExtractor",
    "ProcessComplexityAnalyzer",
]

if __name__ == "__main__":
    print("⚙️  UDS3 Process Mining & Workflow Analysis Demo")
    print("=" * 60)

    # Test mit typischer Betriebsanweisung
    sample_process_text = """
    Arbeitsanweisung: Baugenehmigungsverfahren
    
    Schritt 1: Der Sachbearbeiter prüft die Vollständigkeit der Antragsunterlagen.
    Falls Unterlagen fehlen, dann wird eine Nachforderung erstellt.
    
    Schritt 2: Die Fachbereichsleiterin prüft die rechtliche Zulässigkeit des Vorhabens.
    Bei Zweifeln wenden Sie sich an den Rechtsreferenten.
    
    Schritt 3: Der Bauprüfer führt eine technische Prüfung durch.
    Anschließend wird das Gutachten erstellt und archiviert.
    
    Zuständig: Fachbereichsleiter Bauen und Wohnen
    Unterschriftsberechtigt: Amtsleiter (bei Genehmigungswert > 100.000 €)
    """

    analyzer = ProcessComplexityAnalyzer()
    result = analyzer.analyze_process_document(
        AdminDocumentType.PROCESS_INSTRUCTION,
        sample_process_text,
        "Arbeitsanweisung Baugenehmigungsverfahren",
    )

    print("\n📊 Analyse-Ergebnis:")
    print(f"   Dokumenttyp: {result['document_analysis']['document_type']}")
    print(
        f"   Prozessschritte: {result['document_analysis']['complexity_metrics']['process_steps']}"
    )
    print(
        f"   Beteiligte Rollen: {result['document_analysis']['complexity_metrics']['roles_involved']}"
    )
    print(
        f"   Entscheidungspunkte: {result['document_analysis']['complexity_metrics']['decision_points']}"
    )
    print(
        f"   Beziehungen: {result['document_analysis']['complexity_metrics']['relationships']}"
    )

    print("\n🎯 Graph-Struktur für Neo4j:")
    print(f"   Knoten: {len(result['graph_structure']['nodes'])}")
    print(f"   Beziehungen: {len(result['graph_structure']['relationships'])}")

    print("\n💡 Empfehlungen:")
    for rec in result["recommendations"]:
        print(f"   {rec}")

    print("\n🔗 Beispiel-Beziehungen:")
    for rel in result["graph_structure"]["relationships"][:3]:
        print(f"   {rel['source']} --[{rel['type']}]--> {rel['target']}")

    print("\n🎉 Process Mining Demo abgeschlossen!")
    print("Diese Analyse würde GOLDWERTE Insights für die Graph Database liefern!")
