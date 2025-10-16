"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_bpmn_process_parser"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...3fj/ww=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "f21a64f845bb7fdba680b39747f9fd10cc4d2dc01073f5bfa115533eaa637952"
)
module_file_key = "428107a1cdcfcf31376ada05854e0aa0278e4dc3d8636b824b9f33abcf3f2141"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
BPMN 2.0 PROZESS-PARSER ENGINE
==============================
Parser für Business Process Model and Notation 2.0 
Konvertiert BPMN 2.0 XML zu UDS3-Prozessdokumenten

Unterstützt:
- BPMN 2.0 Standard (ISO/IEC 19510:2013-07)
- FIM-Konformität (Föderales Informationsmanagement)
- BVA-Konventionen für Verwaltungsprozesse
- Verwaltungsattribute nach PMT-Katalog
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Any
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BPMNElement:
    """Repräsentation eines BPMN-Elements"""

    element_id: str
    element_type: str
    name: str
    attributes: Dict[str, Any]
    connections: List[str]
    verwaltung_attributes: Dict[str, Any] = None


@dataclass
class ProcessValidationResult:
    """Validierungsergebnis für BPMN-Prozess"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    fim_compliant: bool
    bva_conventions_met: bool
    compliance_score: float
    details: Dict[str, Any]


class BPMNProcessParser:
    """Hauptklasse für BPMN 2.0 Parsing"""

    def __init__(self):
        self.namespaces = {
            "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
            "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
            "dc": "http://www.omg.org/spec/DD/20100524/DC",
            "di": "http://www.omg.org/spec/DD/20100524/DI",
            "verwaltung": "http://www.verwaltung.de/prozess/v1",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

        # BPMN-Element-Verarbeiter
        self.element_processors = {
            "startEvent": self._process_start_event,
            "endEvent": self._process_end_event,
            "task": self._process_task,
            "userTask": self._process_user_task,
            "serviceTask": self._process_service_task,
            "scriptTask": self._process_script_task,
            "manualTask": self._process_manual_task,
            "businessRuleTask": self._process_business_rule_task,
            "exclusiveGateway": self._process_exclusive_gateway,
            "inclusiveGateway": self._process_inclusive_gateway,
            "parallelGateway": self._process_parallel_gateway,
            "sequenceFlow": self._process_sequence_flow,
            "messageFlow": self._process_message_flow,
            "dataObject": self._process_data_object,
            "dataStore": self._process_data_store,
        }

        # Verwaltungs-spezifische Attribute
        self.verwaltung_attributes = {
            "rechtsgrundlage": str,
            "zustaendigkeit": str,
            "durchlaufzeit": str,
            "kosten": float,
            "automatisierungsgrad": int,
            "datenschutz_relevant": bool,
            "behoerde": str,
            "fachverfahren": list,
            "kritikalitaet": str,
        }

        logger.info("BPMN 2.0 Parser initialisiert")

    def parse_bpmn_to_uds3(self, bpmn_xml: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Hauptfunktion: Konvertiert BPMN XML zu UDS3-Prozessdokument"""
        try:
            # 1. XML parsen
            root = ET.fromstring(bpmn_xml)

            # 2. Basis-Informationen extrahieren
            process_info = self._extract_process_info(root)

            # 3. BPMN-Elemente verarbeiten
            bpmn_elements = self._extract_bpmn_elements(root)

            # 4. Verwaltungsattribute extrahieren
            verwaltung_attrs = self._extract_verwaltung_attributes(root)

            # 5. Prozessfluss analysieren
            process_flow = self._analyze_process_flow(bpmn_elements)

            # 6. UDS3-Dokument erstellen
            uds3_document = self._create_uds3_process_document(
                process_info, bpmn_elements, verwaltung_attrs, process_flow, filename
            )

            logger.info(
                f"BPMN-Prozess erfolgreich geparst: {process_info.get('id', 'unknown')}"
            )
            return uds3_document

        except Exception as e:
            logger.error(f"BPMN-Parsing fehlgeschlagen: {e}")
            raise

    def _extract_process_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extrahiert Basis-Prozessinformationen"""
        process_info: dict[Any, Any] = {}

        # Definitions-Level Info
        definitions = root
        process_info["definitions_id"] = definitions.get("id", "unknown")
        process_info["target_namespace"] = definitions.get("targetNamespace", "")

        # Process-Element finden
        process_elements = root.findall(".//bpmn:process", self.namespaces)
        if process_elements:
            process = process_elements[0]
            process_info["id"] = process.get("id", "unknown")
            process_info["name"] = process.get("name", process_info["id"])
            process_info["is_executable"] = (
                process.get("isExecutable", "false").lower() == "true"
            )
            process_info["process_type"] = process.get("processType", "None")

        # Documentation extrahieren
        documentation_elements = root.findall(".//bpmn:documentation", self.namespaces)
        if documentation_elements:
            process_info["documentation"] = documentation_elements[0].text or ""

        return process_info

    def _extract_bpmn_elements(self, root: ET.Element) -> List[BPMNElement]:
        """Extrahiert alle BPMN-Elemente"""
        elements: list[Any] = []

        # Alle möglichen BPMN-Elemente durchgehen
        for element_type, processor in self.element_processors.items():
            xpath = f".//bpmn:{element_type}"
            found_elements = root.findall(xpath, self.namespaces)

            for elem in found_elements:
                try:
                    bpmn_element = processor(elem)
                    if bpmn_element:
                        elements.append(bpmn_element)
                except Exception as e:
                    logger.warning(f"Fehler bei Verarbeitung von {element_type}: {e}")

        return elements

    def _extract_verwaltung_attributes(self, root: ET.Element) -> Dict[str, Any]:
        """Extrahiert verwaltungsspezifische Attribute"""
        verwaltung_attrs: dict[Any, Any] = {}

        # Verwaltungs-Namespace-Attribute suchen
        verwaltung_elements = root.findall(".//verwaltung:*", self.namespaces)

        for elem in verwaltung_elements:
            attr_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            attr_value = elem.text or elem.get("value", "")

            # Typ-Konvertierung basierend auf Attribut-Definition
            if attr_name in self.verwaltung_attributes:
                expected_type = self.verwaltung_attributes[attr_name]
                try:
                    if expected_type == int:
                        attr_value = int(attr_value)
                    elif expected_type == float:
                        attr_value = float(attr_value)
                    elif expected_type == bool:
                        attr_value = attr_value.lower() in ("true", "1", "yes")
                    elif expected_type == list:
                        attr_value = [item.strip() for item in attr_value.split(",")]
                except ValueError:
                    logger.warning(
                        f"Typ-Konvertierung fehlgeschlagen für {attr_name}: {attr_value}"
                    )

            verwaltung_attrs[attr_name] = attr_value

        # Auch Standard-Attribute auf Verwaltungsrelevanz prüfen
        self._extract_implicit_verwaltung_attributes(root, verwaltung_attrs)

        return verwaltung_attrs

    def _extract_implicit_verwaltung_attributes(
        self, root: ET.Element, verwaltung_attrs: Dict[str, Any]
    ):
        """Extrahiert implizite Verwaltungsattribute aus Standard-BPMN-Elementen"""
        # Automatisierungsgrad aus Service-Tasks ableiten
        service_tasks = root.findall(".//bpmn:serviceTask", self.namespaces)
        user_tasks = root.findall(".//bpmn:userTask", self.namespaces)
        total_tasks = len(service_tasks) + len(user_tasks)

        if total_tasks > 0:
            automation_level = int((len(service_tasks) / total_tasks) * 100)
            verwaltung_attrs.setdefault("automatisierungsgrad", automation_level)

        # Behörde aus Lane-Namen ableiten
        lanes = root.findall(".//bpmn:lane", self.namespaces)
        behoerden: list[Any] = []
        for lane in lanes:
            lane_name = lane.get("name", "")
            if any(
                keyword in lane_name.lower()
                for keyword in ["amt", "behörde", "verwaltung", "büro"]
            ):
                behoerden.append(lane_name)

        if behoerden:
            verwaltung_attrs.setdefault("behoerde", behoerden[0])
            if len(behoerden) > 1:
                verwaltung_attrs.setdefault("beteiligte_behoerden", behoerden)

    def _analyze_process_flow(self, elements: List[BPMNElement]) -> Dict[str, Any]:
        """Analysiert den Prozessfluss"""
        flow_analysis = {
            "start_events": [],
            "end_events": [],
            "total_elements": len(elements),
            "element_types": {},
            "complexity_indicators": {},
            "parallel_paths": 0,
            "decision_points": 0,
            "estimated_duration": None,
        }

        # Elemente kategorisieren
        for element in elements:
            element_type = element.element_type
            flow_analysis["element_types"][element_type] = (
                flow_analysis["element_types"].get(element_type, 0) + 1
            )

            if element_type in ["startEvent"]:
                flow_analysis["start_events"].append(element.element_id)
            elif element_type in ["endEvent"]:
                flow_analysis["end_events"].append(element.element_id)
            elif "Gateway" in element_type:
                flow_analysis["decision_points"] += 1
                if element_type == "parallelGateway":
                    flow_analysis["parallel_paths"] += 1

        # Komplexitäts-Indikatoren berechnen
        flow_analysis["complexity_indicators"] = {
            "cyclomatic_complexity": self._calculate_cyclomatic_complexity(elements),
            "depth_level": self._calculate_process_depth(elements),
            "branching_factor": flow_analysis["decision_points"]
            / max(1, len(elements)),
        }

        return flow_analysis

    def _calculate_cyclomatic_complexity(self, elements: List[BPMNElement]) -> int:
        """Berechnet zyklomatische Komplexität des Prozesses"""
        # Vereinfachte Berechnung: Anzahl der Entscheidungspunkte + 1
        decision_points = sum(1 for elem in elements if "Gateway" in elem.element_type)
        return decision_points + 1

    def _calculate_process_depth(self, elements: List[BPMNElement]) -> int:
        """Berechnet maximale Verschachtelungstiefe"""
        # Vereinfachte Implementierung - in der Praxis komplexere Analyse nötig
        return len(
            [
                elem
                for elem in elements
                if elem.element_type in ["userTask", "serviceTask"]
            ]
        )

    def _create_uds3_process_document(
        self,
        process_info: Dict,
        elements: List[BPMNElement],
        verwaltung_attrs: Dict,
        flow_analysis: Dict,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Erstellt UDS3-konforme Prozessdokumentation"""
        document_id = f"bpmn_process_{process_info.get('id', 'unknown')}"

        uds3_document = {
            "document_id": document_id,
            "document_type": "verwaltungsprozess_bpmn",
            "collection_name": "prozess_modelle",
            "processing_timestamp": datetime.now().isoformat(),
            # Prozess-Content
            "content": {
                "process_type": "BPMN2.0",
                "process_name": process_info.get("name", "Unbenannter Prozess"),
                "process_description": process_info.get("documentation", ""),
                "process_steps": [
                    self._element_to_step_description(elem) for elem in elements
                ],
                "total_steps": len(elements),
                "is_executable": process_info.get("is_executable", False),
            },
            # BPMN-spezifische Metadaten
            "bpmn_metadata": {
                "definitions_id": process_info.get("definitions_id", ""),
                "target_namespace": process_info.get("target_namespace", ""),
                "process_type": process_info.get("process_type", "None"),
                "bpmn_version": "2.0",
                "elements_count": flow_analysis["total_elements"],
                "element_types_distribution": flow_analysis["element_types"],
            },
            # Verwaltungs-spezifische Metadaten
            "verwaltungsattribute": {
                **verwaltung_attrs,
                "fim_relevant": self._assess_fim_relevance(verwaltung_attrs),
                "digitalisierung_prioritaet": self._assess_digitization_priority(
                    verwaltung_attrs, flow_analysis
                ),
                "stakeholder_count": self._count_stakeholders(elements),
                "system_integration_required": self._assess_system_integration(
                    elements
                ),
            },
            # Prozessfluss-Analyse
            "flow_analysis": flow_analysis,
            # Qualitäts-Metriken
            "quality_metrics": {
                "completeness_score": self._calculate_completeness_score(
                    process_info, verwaltung_attrs
                ),
                "complexity_score": flow_analysis["complexity_indicators"][
                    "cyclomatic_complexity"
                ]
                / 10.0,
                "automation_potential": verwaltung_attrs.get("automatisierungsgrad", 0)
                / 100.0,
                "compliance_readiness": self._assess_compliance_readiness(
                    verwaltung_attrs
                ),
            },
            # Verarbeitungsinfo
            "processing_info": {
                "parser_engine": "BPMNProcessParser",
                "parser_version": "1.0",
                "original_filename": filename,
                "elements_parsed": len(elements),
                "parsing_timestamp": datetime.now().isoformat(),
            },
        }

        return uds3_document

    def _element_to_step_description(self, element: BPMNElement) -> Dict[str, Any]:
        """Konvertiert BPMN-Element zu Schritt-Beschreibung"""
        return {
            "step_id": element.element_id,
            "step_name": element.name,
            "step_type": element.element_type,
            "step_attributes": element.attributes,
            "connections": element.connections,
            "verwaltung_specific": element.verwaltung_attributes or {},
        }

    def _assess_fim_relevance(self, verwaltung_attrs: Dict[str, Any]) -> bool:
        """Bewertet FIM-Relevanz des Prozesses"""
        fim_indicators = [
            verwaltung_attrs.get("behoerde") is not None,
            "bund" in str(verwaltung_attrs.get("zustaendigkeit", "")).lower(),
            verwaltung_attrs.get("fachverfahren") is not None,
            verwaltung_attrs.get("rechtsgrundlage") is not None,
        ]
        return sum(fim_indicators) >= 2

    def _assess_digitization_priority(
        self, verwaltung_attrs: Dict, flow_analysis: Dict
    ) -> str:
        """Bewertet Digitalisierungspriorität"""
        priority_score = 0

        # Häufigkeit
        if verwaltung_attrs.get("haeufigkeit", "").lower() in [
            "täglich",
            "wöchentlich",
            "hoch",
        ]:
            priority_score += 3

        # Automatisierungsgrad
        automation = verwaltung_attrs.get("automatisierungsgrad", 0)
        if automation < 30:
            priority_score += 2

        # Komplexität
        complexity = flow_analysis["complexity_indicators"]["cyclomatic_complexity"]
        if complexity > 5:
            priority_score += 1

        if priority_score >= 4:
            return "hoch"
        elif priority_score >= 2:
            return "mittel"
        else:
            return "niedrig"

    def _count_stakeholders(self, elements: List[BPMNElement]) -> int:
        """Zählt beteiligte Akteure"""
        stakeholders = set()
        for element in elements:
            if element.element_type in ["userTask", "manualTask"]:
                assignee = element.attributes.get("assignee", "Unbekannt")
                stakeholders.add(assignee)
        return len(stakeholders)

    def _assess_system_integration(self, elements: List[BPMNElement]) -> bool:
        """Bewertet ob Systemintegration erforderlich ist"""
        return any(
            elem.element_type in ["serviceTask", "businessRuleTask"]
            for elem in elements
        )

    def _calculate_completeness_score(
        self, process_info: Dict, verwaltung_attrs: Dict
    ) -> float:
        """Berechnet Vollständigkeits-Score"""
        required_fields = ["name", "documentation"]
        optional_fields = ["rechtsgrundlage", "zustaendigkeit", "durchlaufzeit"]

        score = 0.0

        # Pflichtfelder
        for field in required_fields:
            if process_info.get(field):
                score += 0.3

        # Optionale Felder
        for field in optional_fields:
            if verwaltung_attrs.get(field):
                score += 0.1

        return min(1.0, score)

    def _assess_compliance_readiness(self, verwaltung_attrs: Dict) -> float:
        """Bewertet Compliance-Bereitschaft"""
        compliance_indicators = [
            verwaltung_attrs.get("rechtsgrundlage") is not None,
            verwaltung_attrs.get("datenschutz_relevant") is not None,
            verwaltung_attrs.get("zustaendigkeit") is not None,
            verwaltung_attrs.get("durchlaufzeit") is not None,
        ]
        return sum(compliance_indicators) / len(compliance_indicators)

    # Element-Verarbeiter (vereinfachte Implementierungen)
    def _process_start_event(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Start-Event"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="startEvent",
            name=elem.get("name", "Start"),
            attributes=dict(elem.attrib),
            connections=self._extract_outgoing_connections(elem),
        )

    def _process_end_event(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet End-Event"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="endEvent",
            name=elem.get("name", "End"),
            attributes=dict(elem.attrib),
            connections=self._extract_incoming_connections(elem),
        )

    def _process_task(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet generische Task"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="task",
            name=elem.get("name", "Task"),
            attributes=dict(elem.attrib),
            connections=self._extract_all_connections(elem),
        )

    def _process_user_task(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet User-Task"""
        attributes = dict(elem.attrib)

        # Verwaltungsattribute extrahieren
        verwaltung_attrs: dict[Any, Any] = {}
        if elem.get("assignee"):
            verwaltung_attrs["zustaendig"] = elem.get("assignee")
        if elem.get("candidateGroups"):
            verwaltung_attrs["kandidaten_gruppen"] = elem.get("candidateGroups").split(
                ","
            )

        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="userTask",
            name=elem.get("name", "User Task"),
            attributes=attributes,
            connections=self._extract_all_connections(elem),
            verwaltung_attributes=verwaltung_attrs,
        )

    def _process_service_task(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Service-Task"""
        attributes = dict(elem.attrib)

        verwaltung_attrs: dict[Any, Any] = {}
        if elem.get("implementation"):
            verwaltung_attrs["implementierung"] = elem.get("implementation")

        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="serviceTask",
            name=elem.get("name", "Service Task"),
            attributes=attributes,
            connections=self._extract_all_connections(elem),
            verwaltung_attributes=verwaltung_attrs,
        )

    def _process_script_task(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Script-Task"""
        return self._process_task(elem)

    def _process_manual_task(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Manual-Task"""
        return self._process_task(elem)

    def _process_business_rule_task(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Business-Rule-Task"""
        return self._process_task(elem)

    def _process_exclusive_gateway(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Exclusive-Gateway"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="exclusiveGateway",
            name=elem.get("name", "Exclusive Gateway"),
            attributes=dict(elem.attrib),
            connections=self._extract_all_connections(elem),
        )

    def _process_inclusive_gateway(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Inclusive-Gateway"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="inclusiveGateway",
            name=elem.get("name", "Inclusive Gateway"),
            attributes=dict(elem.attrib),
            connections=self._extract_all_connections(elem),
        )

    def _process_parallel_gateway(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Parallel-Gateway"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="parallelGateway",
            name=elem.get("name", "Parallel Gateway"),
            attributes=dict(elem.attrib),
            connections=self._extract_all_connections(elem),
        )

    def _process_sequence_flow(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Sequence-Flow"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="sequenceFlow",
            name=elem.get("name", ""),
            attributes=dict(elem.attrib),
            connections=[elem.get("sourceRef", ""), elem.get("targetRef", "")],
        )

    def _process_message_flow(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Message-Flow"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="messageFlow",
            name=elem.get("name", ""),
            attributes=dict(elem.attrib),
            connections=[elem.get("sourceRef", ""), elem.get("targetRef", "")],
        )

    def _process_data_object(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Data-Object"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="dataObject",
            name=elem.get("name", "Data Object"),
            attributes=dict(elem.attrib),
            connections=[],
        )

    def _process_data_store(self, elem: ET.Element) -> BPMNElement:
        """Verarbeitet Data-Store"""
        return BPMNElement(
            element_id=elem.get("id", "unknown"),
            element_type="dataStore",
            name=elem.get("name", "Data Store"),
            attributes=dict(elem.attrib),
            connections=[],
        )

    def _extract_outgoing_connections(self, elem: ET.Element) -> List[str]:
        """Extrahiert ausgehende Verbindungen"""
        outgoing = elem.findall("bpmn:outgoing", self.namespaces)
        return [out.text for out in outgoing if out.text]

    def _extract_incoming_connections(self, elem: ET.Element) -> List[str]:
        """Extrahiert eingehende Verbindungen"""
        incoming = elem.findall("bpmn:incoming", self.namespaces)
        return [inc.text for inc in incoming if inc.text]

    def _extract_all_connections(self, elem: ET.Element) -> List[str]:
        """Extrahiert alle Verbindungen"""
        return self._extract_incoming_connections(
            elem
        ) + self._extract_outgoing_connections(elem)


class BPMN20Validator:
    """Validiert BPMN 2.0 Konformität und Verwaltungsstandards"""

    def __init__(self):
        self.required_elements = ["startEvent", "endEvent"]
        self.fim_requirements = ["rechtsgrundlage", "zustaendigkeit"]
        self.bva_conventions = {
            "naming_pattern": r"^[A-Za-z][A-Za-z0-9_]*$",
            "max_complexity": 15,
            "required_documentation": True,
        }

    def validate_bpmn_process(self, bpmn_xml: str) -> ProcessValidationResult:
        """Vollständige BPMN-Prozess-Validierung"""
        errors: list[Any] = []
        warnings: list[Any] = []
        details: dict[Any, Any] = {}

        try:
            root = ET.fromstring(bpmn_xml)

            # 1. Schema-Validierung
            schema_result = self._validate_schema(root)
            errors.extend(schema_result.get("errors", []))
            warnings.extend(schema_result.get("warnings", []))
            details["schema_validation"] = schema_result

            # 2. Strukturelle Validierung
            structure_result = self._validate_structure(root)
            errors.extend(structure_result.get("errors", []))
            warnings.extend(structure_result.get("warnings", []))
            details["structure_validation"] = structure_result

            # 3. FIM-Konformität prüfen
            fim_result = self._validate_fim_compliance(root)
            details["fim_compliance"] = fim_result
            if not fim_result["compliant"]:
                warnings.extend(fim_result.get("issues", []))

            # 4. BVA-Konventionen prüfen
            bva_result = self._validate_bva_conventions(root)
            details["bva_conventions"] = bva_result
            if not bva_result["compliant"]:
                warnings.extend(bva_result.get("issues", []))

            # Compliance-Score berechnen
            compliance_score = self._calculate_compliance_score(details)

            return ProcessValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                fim_compliant=fim_result["compliant"],
                bva_conventions_met=bva_result["compliant"],
                compliance_score=compliance_score,
                details=details,
            )

        except Exception as e:
            return ProcessValidationResult(
                is_valid=False,
                errors=[f"Validierung fehlgeschlagen: {e}"],
                warnings=[],
                fim_compliant=False,
                bva_conventions_met=False,
                compliance_score=0.0,
                details={"error": str(e)},
            )

    def _validate_schema(self, root: ET.Element) -> Dict[str, Any]:
        """Validiert gegen BPMN 2.0 Schema"""
        # Vereinfachte Schema-Validierung
        result = {"errors": [], "warnings": [], "valid": True}

        # Namespace prüfen
        if "http://www.omg.org/spec/BPMN/20100524/MODEL" not in str(ET.tostring(root)):
            result["errors"].append("BPMN 2.0 Namespace fehlt")
            result["valid"] = False

        return result

    def _validate_structure(self, root: ET.Element) -> Dict[str, Any]:
        """Validiert Prozessstruktur"""
        result = {"errors": [], "warnings": [], "valid": True}

        namespaces = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}

        # Start-Events prüfen
        start_events = root.findall(".//bpmn:startEvent", namespaces)
        if not start_events:
            result["errors"].append("Kein Start-Event gefunden")
            result["valid"] = False

        # End-Events prüfen
        end_events = root.findall(".//bpmn:endEvent", namespaces)
        if not end_events:
            result["errors"].append("Kein End-Event gefunden")
            result["valid"] = False

        return result

    def _validate_fim_compliance(self, root: ET.Element) -> Dict[str, Any]:
        """Prüft FIM-Konformität"""
        result = {"compliant": True, "issues": [], "score": 100.0}

        # Vereinfachte FIM-Prüfung
        verwaltung_elements = root.findall('.//*[@*[contains(name(), "verwaltung")]]')
        if not verwaltung_elements:
            result["issues"].append("Keine Verwaltungsattribute gefunden")
            result["score"] -= 30.0

        result["compliant"] = result["score"] >= 70.0
        return result

    def _validate_bva_conventions(self, root: ET.Element) -> Dict[str, Any]:
        """Prüft BVA-Konventionen"""
        result = {"compliant": True, "issues": [], "score": 100.0}

        # Vereinfachte BVA-Konventionen-Prüfung
        # In der Praxis: umfassendere Regelprüfung

        result["compliant"] = result["score"] >= 80.0
        return result

    def _calculate_compliance_score(self, details: Dict[str, Any]) -> float:
        """Berechnet Gesamt-Compliance-Score"""
        scores: list[Any] = []

        if "fim_compliance" in details:
            scores.append(details["fim_compliance"]["score"] / 100.0)

        if "bva_conventions" in details:
            scores.append(details["bva_conventions"]["score"] / 100.0)

        return sum(scores) / len(scores) if scores else 0.0


# UDS3 Export für Integration
def get_bpmn_parser():
    """Gibt UDS3 BPMN Parser zurück"""
    return BPMNProcessParser()


def get_bpmn_validator():
    """Gibt UDS3 BPMN Validator zurück"""
    return BPMN20Validator()


# Alternative Namen für Kompatibilität
BPMNValidator = BPMN20Validator


if __name__ == "__main__":
    # Test des BPMN-Parsers
    parser = BPMNProcessParser()
    validator = BPMN20Validator()

    # Test-BPMN (vereinfacht)
    test_bpmn = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:verwaltung="http://www.verwaltung.de/prozess/v1"
                      id="sample_process" targetNamespace="http://sample.org">
        <bpmn:process id="antrag_bearbeitung" name="Antragsbearbeitung" isExecutable="true">
            <bpmn:documentation>Prozess zur Bearbeitung von Anträgen</bpmn:documentation>
            <bpmn:startEvent id="antrag_eingegangen" name="Antrag eingegangen"/>
            <bpmn:userTask id="antrag_pruefen" name="Antrag prüfen" assignee="sachbearbeiter"/>
            <bpmn:exclusiveGateway id="entscheidung" name="Entscheidung"/>
            <bpmn:endEvent id="bescheid_erteilt" name="Bescheid erteilt"/>
            <verwaltung:rechtsgrundlage>§ 15 VwVfG</verwaltung:rechtsgrundlage>
            <verwaltung:zustaendigkeit>Kommunal</verwaltung:zustaendigkeit>
            <verwaltung:automatisierungsgrad>25</verwaltung:automatisierungsgrad>
        </bpmn:process>
    </bpmn:definitions>"""

    # Parsing testen
    try:
        result = parser.parse_bpmn_to_uds3(test_bpmn, "test_antrag.bpmn")
        print("✓ BPMN-Parsing erfolgreich")
        print(f"Prozess-ID: {result['bpmn_metadata']['definitions_id']}")
        print(f"Elemente: {result['bpmn_metadata']['elements_count']}")
        print(
            f"Automatisierungsgrad: {result['verwaltungsattribute'].get('automatisierungsgrad', 'N/A')}%"
        )

        # Validierung testen
        validation_result = validator.validate_bpmn_process(test_bpmn)
        print(
            f"\n✓ Validierung: {'Bestanden' if validation_result.is_valid else 'Fehlgeschlagen'}"
        )
        print(f"Compliance-Score: {validation_result.compliance_score:.2f}")

    except Exception as e:
        print(f"✗ Test fehlgeschlagen: {e}")