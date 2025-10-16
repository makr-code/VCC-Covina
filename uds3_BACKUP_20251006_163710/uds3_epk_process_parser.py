"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_epk_process_parser"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...M7KaCg=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "d2e5ffee703ac084f9c2788182eba6c45199f9f701568b5a94e9e18622990dfb"
)
module_file_key = "a462fe3713c0fe30bafaddc518dcc6ec3fb4e2ed9bfb9753785eef54a8dd8f59"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
EPK PROZESS-PARSER ENGINE
=========================
Parser für Ereignisgesteuerte Prozessketten (EPK)
Konvertiert EPK XML zu UDS3-Prozessdokumenten

Unterstützt:
- Klassische EPK mit Ereignis-Funktion-Ketten
- Erweiterte EPK (eEPK) mit Organisationseinheiten und IT-Systemen
- Funktionszuordnungsdiagramm (FZD) Integration
- Satellitenobjekte-Verknüpfung (Organisation, Anwendungssysteme, Daten)
- Mehrsäulen-Modellierung
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Any
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EPKElement:
    """Repräsentation eines EPK-Elements"""

    element_id: str
    element_type: str
    name: str
    attributes: Dict[str, Any]
    connections: List[str]
    satellite_objects: Dict[str, List[str]] = None  # Organisation, IT, Daten etc.


@dataclass
class EPKSatelliteObject:
    """Satellitenobjekte in erweiterten EPKs"""

    object_id: str
    object_type: str  # organisation, anwendungssystem, dokument, risiko, etc.
    name: str
    attributes: Dict[str, Any]
    connected_functions: List[str]


@dataclass
class EPKValidationResult:
    """Validierungsergebnis für EPK"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    completeness_score: float
    satellite_coverage: float
    details: Dict[str, Any]


class EPKProcessParser:
    """Hauptklasse für EPK Parsing"""

    def __init__(self):
        self.namespaces = {
            "epk": "http://www.verwaltung.de/epk/v1",
            "eepk": "http://www.verwaltung.de/eepk/v1",  # Erweiterte EPK
            "fzd": "http://www.verwaltung.de/fzd/v1",  # Funktionszuordnungsdiagramm
            "verwaltung": "http://www.verwaltung.de/prozess/v1",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

        # EPK-Element-Verarbeiter
        self.element_processors = {
            "ereignis": self._process_event,
            "funktion": self._process_function,
            "connector": self._process_connector,
            "and_connector": self._process_and_connector,
            "or_connector": self._process_or_connector,
            "xor_connector": self._process_xor_connector,
        }

        # Satellitenobjekt-Verarbeiter
        self.satellite_processors = {
            "organisationseinheit": self._process_organizational_unit,
            "anwendungssystem": self._process_application_system,
            "dokument": self._process_document,
            "datenentitaet": self._process_data_entity,
            "risiko": self._process_risk,
            "ressource": self._process_resource,
        }

        logger.info("EPK Parser initialisiert")

    def parse_epk_to_uds3(self, epk_xml: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Hauptfunktion: Konvertiert EPK XML zu UDS3-Prozessdokument"""
        try:
            # 1. XML parsen
            root = ET.fromstring(epk_xml)

            # 2. Prozess-Grundinformationen
            process_info = self._extract_epk_process_info(root)

            # 3. EPK-Kernelemente (Ereignis-Funktion-Ketten)
            epk_elements = self._extract_epk_core_elements(root)

            # 4. Satellitenobjekte extrahieren (eEPK)
            satellite_objects = self._extract_satellite_objects(root)

            # 5. FZD-Verknüpfungen analysieren
            fzd_mappings = self._extract_fzd_mappings(root)

            # 6. Verwaltungsattribute
            verwaltung_attrs = self._extract_verwaltung_attributes(root)

            # 7. Prozessfluss analysieren
            process_flow = self._analyze_epk_flow(epk_elements, satellite_objects)

            # 8. UDS3-Dokument erstellen
            uds3_document = self._create_uds3_epk_document(
                process_info,
                epk_elements,
                satellite_objects,
                fzd_mappings,
                verwaltung_attrs,
                process_flow,
                filename,
            )

            logger.info(
                f"EPK-Prozess erfolgreich geparst: {process_info.get('id', 'unknown')}"
            )
            return uds3_document

        except Exception as e:
            logger.error(f"EPK-Parsing fehlgeschlagen: {e}")
            raise

    def _extract_epk_process_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extrahiert EPK-Prozessinformationen"""
        process_info: dict[Any, Any] = {}

        # Prozess-Element finden
        epk_process = root.find(".//epk:prozesskette", self.namespaces) or root.find(
            ".//eepk:prozesskette", self.namespaces
        )

        if epk_process is not None:
            process_info["id"] = epk_process.get("id", "unknown_epk")
            process_info["name"] = epk_process.get("name", process_info["id"])
            process_info["type"] = "EPK"
            process_info["version"] = epk_process.get("version", "1.0")

            # EPK-spezifische Attribute
            process_info["modellierungstiefe"] = epk_process.get(
                "modellierungstiefe", "standard"
            )
            process_info["sichtweise"] = epk_process.get(
                "sichtweise", "prozess"
            )  # prozess, daten, organisation

        # Beschreibung
        description_elem = root.find(".//epk:beschreibung", self.namespaces)
        if description_elem is not None:
            process_info["beschreibung"] = description_elem.text or ""

        # Prozess-Klassifikation
        klassifikation_elem = root.find(".//epk:klassifikation", self.namespaces)
        if klassifikation_elem is not None:
            process_info["klassifikation"] = klassifikation_elem.get(
                "typ", "kernprozess"
            )

        return process_info

    def _extract_epk_core_elements(self, root: ET.Element) -> List[EPKElement]:
        """Extrahiert EPK-Kernelemente (Ereignisse, Funktionen, Konnektoren)"""
        elements: list[Any] = []

        # Alle EPK-Kernelemente durchgehen
        for element_type, processor in self.element_processors.items():
            # Sowohl klassische EPK als auch eEPK berücksichtigen
            xpath_classic = f".//epk:{element_type}"
            xpath_extended = f".//eepk:{element_type}"

            found_elements = root.findall(
                xpath_classic, self.namespaces
            ) + root.findall(xpath_extended, self.namespaces)

            for elem in found_elements:
                try:
                    epk_element = processor(elem)
                    if epk_element:
                        elements.append(epk_element)
                except Exception as e:
                    logger.warning(f"Fehler bei EPK-Element {element_type}: {e}")

        return elements

    def _extract_satellite_objects(self, root: ET.Element) -> List[EPKSatelliteObject]:
        """Extrahiert Satellitenobjekte für erweiterte EPK"""
        satellite_objects: list[Any] = []

        for object_type, processor in self.satellite_processors.items():
            xpath = f".//eepk:{object_type}"
            found_objects = root.findall(xpath, self.namespaces)

            for obj in found_objects:
                try:
                    satellite_obj = processor(obj)
                    if satellite_obj:
                        satellite_objects.append(satellite_obj)
                except Exception as e:
                    logger.warning(f"Fehler bei Satellitenobjekt {object_type}: {e}")

        return satellite_objects

    def _extract_fzd_mappings(self, root: ET.Element) -> Dict[str, Any]:
        """Extrahiert Funktionszuordnungsdiagramm-Verknüpfungen"""
        fzd_mappings = {
            "function_to_org": {},  # Funktion -> Organisationseinheit
            "function_to_system": {},  # Funktion -> IT-System
            "function_to_data": {},  # Funktion -> Datenobjekt
            "function_to_resource": {},  # Funktion -> Ressource
        }

        # FZD-Elemente suchen
        fzd_elements = root.findall(".//fzd:zuordnung", self.namespaces)

        for fzd in fzd_elements:
            function_id = fzd.get("funktion_id")
            target_type = fzd.get("ziel_typ")
            target_id = fzd.get("ziel_id")

            if function_id and target_type and target_id:
                mapping_key = f"function_to_{target_type}"
                if mapping_key in fzd_mappings:
                    if function_id not in fzd_mappings[mapping_key]:
                        fzd_mappings[mapping_key][function_id] = []
                    fzd_mappings[mapping_key][function_id].append(target_id)

        return fzd_mappings

    def _extract_verwaltung_attributes(self, root: ET.Element) -> Dict[str, Any]:
        """Extrahiert verwaltungsspezifische Attribute"""
        verwaltung_attrs: dict[Any, Any] = {}

        # Verwaltungsattribute aus verschiedenen Namespaces
        namespaces_to_check = ["verwaltung", "epk", "eepk"]

        for ns in namespaces_to_check:
            if ns in self.namespaces:
                verwaltung_elements = root.findall(
                    f'.//{ns}:*[@*[contains(name(), "verwaltung")] or @verwaltung_relevant="true"]',
                    self.namespaces,
                )

                for elem in verwaltung_elements:
                    # Attribute des Elements extrahieren
                    for attr_name, attr_value in elem.attrib.items():
                        if "verwaltung" in attr_name.lower():
                            verwaltung_attrs[attr_name] = attr_value

                    # Text-Content als potentielles Verwaltungsattribut
                    if elem.text and elem.text.strip():
                        tag_name = (
                            elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        )
                        if tag_name in [
                            "rechtsgrundlage",
                            "zustaendigkeit",
                            "durchlaufzeit",
                            "kosten",
                        ]:
                            verwaltung_attrs[tag_name] = elem.text.strip()

        # Standard-Verwaltungsattribute aus EPK-Struktur ableiten
        self._derive_implicit_verwaltung_attributes(root, verwaltung_attrs)

        return verwaltung_attrs

    def _derive_implicit_verwaltung_attributes(
        self, root: ET.Element, verwaltung_attrs: Dict[str, Any]
    ):
        """Leitet Verwaltungsattribute aus EPK-Struktur ab"""
        # Organisationseinheiten als Zuständigkeit ableiten
        org_units = root.findall(".//eepk:organisationseinheit", self.namespaces)
        if org_units and "zustaendigkeit" not in verwaltung_attrs:
            org_names = [
                org.get("name", org.get("bezeichnung", "")) for org in org_units
            ]
            verwaltung_attrs["beteiligte_organisationen"] = org_names
            if org_names:
                verwaltung_attrs["hauptzustaendigkeit"] = org_names[0]

        # IT-Systeme als Fachverfahren identifizieren
        systems = root.findall(".//eepk:anwendungssystem", self.namespaces)
        if systems:
            system_names = [
                sys.get("name", sys.get("bezeichnung", "")) for sys in systems
            ]
            verwaltung_attrs["fachverfahren"] = system_names

        # Automatisierungsgrad aus Systemverknüpfungen schätzen
        functions = root.findall(".//epk:funktion", self.namespaces) + root.findall(
            ".//eepk:funktion", self.namespaces
        )
        if functions:
            automated_functions = 0
            for func in functions:
                # Prüfen ob Funktion mit IT-System verknüpft ist
                func_id = func.get("id", "")
                system_refs = root.findall(
                    f'.//fzd:zuordnung[@funktion_id="{func_id}"][@ziel_typ="anwendungssystem"]',
                    self.namespaces,
                )
                if system_refs:
                    automated_functions += 1

            if len(functions) > 0:
                automation_level = int((automated_functions / len(functions)) * 100)
                verwaltung_attrs["automatisierungsgrad"] = automation_level

    def _analyze_epk_flow(
        self, elements: List[EPKElement], satellites: List[EPKSatelliteObject]
    ) -> Dict[str, Any]:
        """Analysiert EPK-Prozessfluss"""
        flow_analysis = {
            "start_events": [],
            "end_events": [],
            "total_elements": len(elements),
            "element_distribution": {},
            "satellite_distribution": {},
            "control_flow_complexity": 0,
            "organizational_complexity": 0,
            "data_complexity": 0,
        }

        # Elemente kategorisieren
        for element in elements:
            element_type = element.element_type
            flow_analysis["element_distribution"][element_type] = (
                flow_analysis["element_distribution"].get(element_type, 0) + 1
            )

            # Start/End-Ereignisse identifizieren
            if element_type == "ereignis":
                if (
                    not element.connections
                    or len([c for c in element.connections if c]) == 1
                ):
                    if any(
                        keyword in element.name.lower()
                        for keyword in ["start", "begin", "eingegangen", "eingeleitet"]
                    ):
                        flow_analysis["start_events"].append(element.element_id)
                    elif any(
                        keyword in element.name.lower()
                        for keyword in ["end", "beendet", "abgeschlossen", "erteilt"]
                    ):
                        flow_analysis["end_events"].append(element.element_id)

            # Konnektoren für Komplexitätsanalyse
            if "connector" in element_type:
                flow_analysis["control_flow_complexity"] += 1

        # Satellitenobjekte kategorisieren
        for satellite in satellites:
            sat_type = satellite.object_type
            flow_analysis["satellite_distribution"][sat_type] = (
                flow_analysis["satellite_distribution"].get(sat_type, 0) + 1
            )

        # Komplexitäts-Metriken berechnen
        flow_analysis["organizational_complexity"] = flow_analysis[
            "satellite_distribution"
        ].get("organisationseinheit", 0)
        flow_analysis["data_complexity"] = flow_analysis["satellite_distribution"].get(
            "dokument", 0
        ) + flow_analysis["satellite_distribution"].get("datenentitaet", 0)

        return flow_analysis

    def _create_uds3_epk_document(
        self,
        process_info: Dict,
        elements: List[EPKElement],
        satellites: List[EPKSatelliteObject],
        fzd_mappings: Dict,
        verwaltung_attrs: Dict,
        flow_analysis: Dict,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Erstellt UDS3-konformes EPK-Prozessdokument"""
        document_id = f"epk_process_{process_info.get('id', 'unknown')}"

        uds3_document = {
            "document_id": document_id,
            "document_type": "verwaltungsprozess_epk",
            "collection_name": "prozess_modelle",
            "processing_timestamp": datetime.now().isoformat(),
            # EPK-Content
            "content": {
                "process_type": "EPK",
                "process_subtype": "eEPK" if satellites else "klassische_EPK",
                "process_name": process_info.get("name", "Unbenannter EPK-Prozess"),
                "process_description": process_info.get("beschreibung", ""),
                "process_classification": process_info.get(
                    "klassifikation", "kernprozess"
                ),
                "modeling_depth": process_info.get("modellierungstiefe", "standard"),
                "modeling_perspective": process_info.get("sichtweise", "prozess"),
                # EPK-Elemente
                "epk_elements": [
                    self._element_to_content_description(elem) for elem in elements
                ],
                "total_elements": len(elements),
                # Satellitenobjekte
                "satellite_objects": [
                    self._satellite_to_content_description(sat) for sat in satellites
                ],
                "total_satellites": len(satellites),
            },
            # EPK-spezifische Metadaten
            "epk_metadata": {
                "epk_version": process_info.get("version", "1.0"),
                "is_extended_epk": len(satellites) > 0,
                "has_fzd_mappings": len(fzd_mappings.get("function_to_org", {})) > 0,
                "element_distribution": flow_analysis["element_distribution"],
                "satellite_distribution": flow_analysis["satellite_distribution"],
                "modeling_approach": "mehrsäulig"
                if len(satellites) > 0
                else "einsäulig",
            },
            # FZD-Verknüpfungen
            "fzd_mappings": fzd_mappings,
            # Verwaltungsattribute
            "verwaltungsattribute": {
                **verwaltung_attrs,
                "organisationsweite_relevanz": self._assess_organizational_relevance(
                    satellites
                ),
                "systemintegration_erforderlich": len(
                    fzd_mappings.get("function_to_system", {})
                )
                > 0,
                "datenintegration_erforderlich": len(
                    fzd_mappings.get("function_to_data", {})
                )
                > 0,
                "stakeholder_anzahl": len(
                    set(
                        s.name
                        for s in satellites
                        if s.object_type == "organisationseinheit"
                    )
                ),
            },
            # Prozessfluss-Analyse
            "flow_analysis": flow_analysis,
            # Qualitäts-Metriken
            "quality_metrics": {
                "completeness_score": self._calculate_epk_completeness(
                    elements, satellites
                ),
                "satellite_coverage": len(satellites) / max(1, len(elements))
                if elements
                else 0.0,
                "fzd_coverage": self._calculate_fzd_coverage(elements, fzd_mappings),
                "modeling_consistency": self._assess_modeling_consistency(
                    elements, satellites
                ),
            },
            # Verarbeitungsinfo
            "processing_info": {
                "parser_engine": "EPKProcessParser",
                "parser_version": "1.0",
                "original_filename": filename,
                "elements_parsed": len(elements),
                "satellites_parsed": len(satellites),
                "parsing_timestamp": datetime.now().isoformat(),
            },
        }

        return uds3_document

    def _element_to_content_description(self, element: EPKElement) -> Dict[str, Any]:
        """Konvertiert EPK-Element zu Content-Beschreibung"""
        return {
            "element_id": element.element_id,
            "element_name": element.name,
            "element_type": element.element_type,
            "element_attributes": element.attributes,
            "connections": element.connections,
            "satellite_links": element.satellite_objects or {},
        }

    def _satellite_to_content_description(
        self, satellite: EPKSatelliteObject
    ) -> Dict[str, Any]:
        """Konvertiert Satellitenobjekt zu Content-Beschreibung"""
        return {
            "object_id": satellite.object_id,
            "object_name": satellite.name,
            "object_type": satellite.object_type,
            "object_attributes": satellite.attributes,
            "connected_functions": satellite.connected_functions,
        }

    def _assess_organizational_relevance(
        self, satellites: List[EPKSatelliteObject]
    ) -> str:
        """Bewertet organisationsweite Relevanz"""
        org_units = [s for s in satellites if s.object_type == "organisationseinheit"]

        if len(org_units) > 3:
            return "hoch"
        elif len(org_units) > 1:
            return "mittel"
        else:
            return "niedrig"

    def _calculate_epk_completeness(
        self, elements: List[EPKElement], satellites: List[EPKSatelliteObject]
    ) -> float:
        """Berechnet Vollständigkeit des EPK-Modells"""
        score = 0.0

        # Basis-EPK-Elemente (Events und Functions)
        has_events = any(elem.element_type == "ereignis" for elem in elements)
        has_functions = any(elem.element_type == "funktion" for elem in elements)

        if has_events:
            score += 0.3
        if has_functions:
            score += 0.3

        # Erweiterte EPK-Elemente (Satellitenobjekte)
        if satellites:
            score += 0.2

        # FZD-Vollständigkeit
        functions = [elem for elem in elements if elem.element_type == "funktion"]
        if functions and satellites:
            linked_functions = sum(1 for func in functions if func.satellite_objects)
            if linked_functions > 0:
                score += 0.2 * (linked_functions / len(functions))

        return min(1.0, score)

    def _calculate_fzd_coverage(
        self, elements: List[EPKElement], fzd_mappings: Dict
    ) -> float:
        """Berechnet FZD-Abdeckung"""
        functions = [elem for elem in elements if elem.element_type == "funktion"]
        if not functions:
            return 0.0

        mapped_functions = set()
        for mapping_type, mappings in fzd_mappings.items():
            mapped_functions.update(mappings.keys())

        return len(mapped_functions) / len(functions)

    def _assess_modeling_consistency(
        self, elements: List[EPKElement], satellites: List[EPKSatelliteObject]
    ) -> float:
        """Bewertet Modellierungskonsistenz"""
        # Vereinfachte Konsistenzprüfung
        consistency_score = 1.0

        # Prüfe Event-Function-Alternierung
        events = [elem for elem in elements if elem.element_type == "ereignis"]
        functions = [elem for elem in elements if elem.element_type == "funktion"]

        if len(events) == 0 and len(functions) > 0:
            consistency_score -= 0.3  # Funktionen ohne Events

        if len(functions) == 0 and len(events) > 0:
            consistency_score -= 0.3  # Events ohne Funktionen

        return max(0.0, consistency_score)

    # Element-Verarbeiter
    def _process_event(self, elem: ET.Element) -> EPKElement:
        """Verarbeitet EPK-Ereignis"""
        return EPKElement(
            element_id=elem.get("id", "unknown"),
            element_type="ereignis",
            name=elem.get("name", elem.get("bezeichnung", "Unbenanntes Ereignis")),
            attributes=dict(elem.attrib),
            connections=self._extract_epk_connections(elem),
            satellite_objects=self._extract_element_satellites(elem),
        )

    def _process_function(self, elem: ET.Element) -> EPKElement:
        """Verarbeitet EPK-Funktion"""
        return EPKElement(
            element_id=elem.get("id", "unknown"),
            element_type="funktion",
            name=elem.get("name", elem.get("bezeichnung", "Unbenannte Funktion")),
            attributes=dict(elem.attrib),
            connections=self._extract_epk_connections(elem),
            satellite_objects=self._extract_element_satellites(elem),
        )

    def _process_connector(self, elem: ET.Element) -> EPKElement:
        """Verarbeitet generischen EPK-Konnektor"""
        return EPKElement(
            element_id=elem.get("id", "unknown"),
            element_type="connector",
            name=elem.get("name", "Konnektor"),
            attributes=dict(elem.attrib),
            connections=self._extract_epk_connections(elem),
        )

    def _process_and_connector(self, elem: ET.Element) -> EPKElement:
        """Verarbeitet UND-Konnektor"""
        element = self._process_connector(elem)
        element.element_type = "and_connector"
        element.name = elem.get("name", "UND")
        return element

    def _process_or_connector(self, elem: ET.Element) -> EPKElement:
        """Verarbeitet ODER-Konnektor"""
        element = self._process_connector(elem)
        element.element_type = "or_connector"
        element.name = elem.get("name", "ODER")
        return element

    def _process_xor_connector(self, elem: ET.Element) -> EPKElement:
        """Verarbeitet XOR-Konnektor"""
        element = self._process_connector(elem)
        element.element_type = "xor_connector"
        element.name = elem.get("name", "XOR")
        return element

    # Satellitenobjekt-Verarbeiter
    def _process_organizational_unit(self, elem: ET.Element) -> EPKSatelliteObject:
        """Verarbeitet Organisationseinheit"""
        return EPKSatelliteObject(
            object_id=elem.get("id", "unknown"),
            object_type="organisationseinheit",
            name=elem.get(
                "name", elem.get("bezeichnung", "Unbekannte Organisationseinheit")
            ),
            attributes=dict(elem.attrib),
            connected_functions=self._extract_function_connections(elem),
        )

    def _process_application_system(self, elem: ET.Element) -> EPKSatelliteObject:
        """Verarbeitet Anwendungssystem"""
        return EPKSatelliteObject(
            object_id=elem.get("id", "unknown"),
            object_type="anwendungssystem",
            name=elem.get(
                "name", elem.get("bezeichnung", "Unbekanntes Anwendungssystem")
            ),
            attributes=dict(elem.attrib),
            connected_functions=self._extract_function_connections(elem),
        )

    def _process_document(self, elem: ET.Element) -> EPKSatelliteObject:
        """Verarbeitet Dokument"""
        return EPKSatelliteObject(
            object_id=elem.get("id", "unknown"),
            object_type="dokument",
            name=elem.get("name", elem.get("bezeichnung", "Unbekanntes Dokument")),
            attributes=dict(elem.attrib),
            connected_functions=self._extract_function_connections(elem),
        )

    def _process_data_entity(self, elem: ET.Element) -> EPKSatelliteObject:
        """Verarbeitet Datenentität"""
        return EPKSatelliteObject(
            object_id=elem.get("id", "unknown"),
            object_type="datenentitaet",
            name=elem.get("name", elem.get("bezeichnung", "Unbekannte Datenentität")),
            attributes=dict(elem.attrib),
            connected_functions=self._extract_function_connections(elem),
        )

    def _process_risk(self, elem: ET.Element) -> EPKSatelliteObject:
        """Verarbeitet Risiko"""
        return EPKSatelliteObject(
            object_id=elem.get("id", "unknown"),
            object_type="risiko",
            name=elem.get("name", elem.get("bezeichnung", "Unbekanntes Risiko")),
            attributes=dict(elem.attrib),
            connected_functions=self._extract_function_connections(elem),
        )

    def _process_resource(self, elem: ET.Element) -> EPKSatelliteObject:
        """Verarbeitet Ressource"""
        return EPKSatelliteObject(
            object_id=elem.get("id", "unknown"),
            object_type="ressource",
            name=elem.get("name", elem.get("bezeichnung", "Unbekannte Ressource")),
            attributes=dict(elem.attrib),
            connected_functions=self._extract_function_connections(elem),
        )

    # Hilfsmethoden
    def _extract_epk_connections(self, elem: ET.Element) -> List[str]:
        """Extrahiert EPK-Verbindungen"""
        connections: list[Any] = []

        # Vorgänger
        predecessors = elem.findall("epk:vorgaenger", self.namespaces) + elem.findall(
            "eepk:vorgaenger", self.namespaces
        )
        connections.extend(
            [pred.get("ref", "") for pred in predecessors if pred.get("ref")]
        )

        # Nachfolger
        successors = elem.findall("epk:nachfolger", self.namespaces) + elem.findall(
            "eepk:nachfolger", self.namespaces
        )
        connections.extend(
            [succ.get("ref", "") for succ in successors if succ.get("ref")]
        )

        return connections

    def _extract_element_satellites(self, elem: ET.Element) -> Dict[str, List[str]]:
        """Extrahiert Satellitenobjekt-Verknüpfungen eines Elements"""
        satellites: dict[Any, Any] = {}

        # Verschiedene Satellitenobjekt-Typen durchgehen
        satellite_types = [
            "organisationseinheit",
            "anwendungssystem",
            "dokument",
            "datenentitaet",
            "ressource",
        ]

        for sat_type in satellite_types:
            refs = elem.findall(f"eepk:{sat_type}_ref", self.namespaces)
            if refs:
                satellites[sat_type] = [
                    ref.get("ref", "") for ref in refs if ref.get("ref")
                ]

        return satellites if satellites else None

    def _extract_function_connections(self, elem: ET.Element) -> List[str]:
        """Extrahiert Funktionsverbindungen eines Satellitenobjekts"""
        function_refs = elem.findall(
            ".//eepk:funktion_ref", self.namespaces
        ) + elem.findall(".//fzd:funktion_ref", self.namespaces)
        return [ref.get("ref", "") for ref in function_refs if ref.get("ref")]


class EPKValidator:
    """Validiert EPK-Konformität"""

    def __init__(self):
        self.required_elements = ["ereignis", "funktion"]
        self.epk_rules = {
            "event_function_alternation": True,
            "single_start_end": True,
            "no_orphaned_elements": True,
        }

    def validate_epk_process(self, epk_xml: str) -> EPKValidationResult:
        """Vollständige EPK-Validierung"""
        errors: list[Any] = []
        warnings: list[Any] = []
        details: dict[Any, Any] = {}

        try:
            root = ET.fromstring(epk_xml)

            # 1. Strukturelle EPK-Regeln
            structure_result = self._validate_epk_structure(root)
            errors.extend(structure_result.get("errors", []))
            warnings.extend(structure_result.get("warnings", []))
            details["structure_validation"] = structure_result

            # 2. Satellitenobjekt-Konsistenz
            satellite_result = self._validate_satellite_consistency(root)
            warnings.extend(satellite_result.get("warnings", []))
            details["satellite_validation"] = satellite_result

            # 3. FZD-Vollständigkeit
            fzd_result = self._validate_fzd_completeness(root)
            details["fzd_validation"] = fzd_result

            # Scores berechnen
            completeness_score = self._calculate_epk_completeness_score(details)
            satellite_coverage = satellite_result.get("coverage_score", 0.0)

            return EPKValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                completeness_score=completeness_score,
                satellite_coverage=satellite_coverage,
                details=details,
            )

        except Exception as e:
            return EPKValidationResult(
                is_valid=False,
                errors=[f"EPK-Validierung fehlgeschlagen: {e}"],
                warnings=[],
                completeness_score=0.0,
                satellite_coverage=0.0,
                details={"error": str(e)},
            )

    def _validate_epk_structure(self, root: ET.Element) -> Dict[str, Any]:
        """Validiert EPK-Struktur"""
        result = {"errors": [], "warnings": [], "valid": True}

        namespaces = {
            "epk": "http://www.verwaltung.de/epk/v1",
            "eepk": "http://www.verwaltung.de/eepk/v1",
        }

        # Ereignisse prüfen
        events = root.findall(".//epk:ereignis", namespaces) + root.findall(
            ".//eepk:ereignis", namespaces
        )

        # Funktionen prüfen
        functions = root.findall(".//epk:funktion", namespaces) + root.findall(
            ".//eepk:funktion", namespaces
        )

        if not events:
            result["errors"].append("Keine Ereignisse gefunden")
            result["valid"] = False

        if not functions:
            result["errors"].append("Keine Funktionen gefunden")
            result["valid"] = False

        # Event-Function-Alternierung prüfen (vereinfacht)
        if len(events) > 0 and len(functions) > 0:
            if abs(len(events) - len(functions)) > len(functions) * 0.5:
                result["warnings"].append("Event-Function-Verhältnis ungewöhnlich")

        return result

    def _validate_satellite_consistency(self, root: ET.Element) -> Dict[str, Any]:
        """Validiert Satellitenobjekt-Konsistenz"""
        result = {"warnings": [], "coverage_score": 0.0}

        # Vereinfachte Satellitenobjekt-Prüfung
        satellites = root.findall(
            ".//eepk:*[@object_type]", {"eepk": "http://www.verwaltung.de/eepk/v1"}
        )
        functions = root.findall(
            ".//eepk:funktion", {"eepk": "http://www.verwaltung.de/eepk/v1"}
        )

        if len(functions) > 0:
            result["coverage_score"] = min(1.0, len(satellites) / len(functions))

        if len(satellites) == 0 and len(functions) > 0:
            result["warnings"].append(
                "Keine Satellitenobjekte für erweiterte EPK gefunden"
            )

        return result

    def _validate_fzd_completeness(self, root: ET.Element) -> Dict[str, Any]:
        """Validiert FZD-Vollständigkeit"""
        result = {"score": 0.0}

        # Vereinfachte FZD-Prüfung
        fzd_mappings = root.findall(
            ".//fzd:zuordnung", {"fzd": "http://www.verwaltung.de/fzd/v1"}
        )
        functions = root.findall(
            ".//eepk:funktion", {"eepk": "http://www.verwaltung.de/eepk/v1"}
        )

        if len(functions) > 0:
            result["score"] = min(1.0, len(fzd_mappings) / len(functions))

        return result

    def _calculate_epk_completeness_score(self, details: Dict[str, Any]) -> float:
        """Berechnet EPK-Vollständigkeits-Score"""
        structure_valid = details.get("structure_validation", {}).get("valid", False)
        satellite_coverage = details.get("satellite_validation", {}).get(
            "coverage_score", 0.0
        )
        fzd_score = details.get("fzd_validation", {}).get("score", 0.0)

        if structure_valid:
            return 0.5 + 0.25 * satellite_coverage + 0.25 * fzd_score
        else:
            return 0.0


# UDS3 Export für Integration
def get_epk_parser():
    """Gibt UDS3 EPK Parser zurück"""
    return EPKProcessParser()


def get_epk_validator():
    """Gibt UDS3 EPK Validator zurück"""
    return EPKValidator()


# Alternative Namen für Kompatibilität
EPKValidator = EPKValidator


if __name__ == "__main__":
    # Test des EPK-Parsers
    parser = EPKProcessParser()
    validator = EPKValidator()

    # Test-EPK (erweiterte EPK)
    test_epk = """<?xml version="1.0" encoding="UTF-8"?>
    <eepk:prozesskette xmlns:eepk="http://www.verwaltung.de/eepk/v1"
                       xmlns:fzd="http://www.verwaltung.de/fzd/v1"
                       xmlns:verwaltung="http://www.verwaltung.de/prozess/v1"
                       id="antrag_bearbeitung_epk" name="Antragsbearbeitung EPK">
        
        <eepk:beschreibung>Erweiterte EPK für Antragsbearbeitung mit Organisationseinheiten</eepk:beschreibung>
        
        <eepk:ereignis id="antrag_eingegangen" name="Antrag ist eingegangen"/>
        <eepk:funktion id="antrag_pruefen" name="Antrag prüfen">
            <eepk:organisationseinheit_ref ref="sachbearbeitung"/>
            <eepk:anwendungssystem_ref ref="fachverfahren_xy"/>
        </eepk:funktion>
        <eepk:ereignis id="pruefung_abgeschlossen" name="Prüfung ist abgeschlossen"/>
        
        <eepk:organisationseinheit id="sachbearbeitung" name="Sachbearbeitung Bauamt"/>
        <eepk:anwendungssystem id="fachverfahren_xy" name="Fachverfahren XY"/>
        
        <fzd:zuordnung funktion_id="antrag_pruefen" ziel_typ="organisationseinheit" ziel_id="sachbearbeitung"/>
        <fzd:zuordnung funktion_id="antrag_pruefen" ziel_typ="anwendungssystem" ziel_id="fachverfahren_xy"/>
        
        <verwaltung:rechtsgrundlage>§ 63 BauO NRW</verwaltung:rechtsgrundlage>
        <verwaltung:zustaendigkeit>Kommunal</verwaltung:zustaendigkeit>
    </eepk:prozesskette>"""

    # Parsing testen
    try:
        result = parser.parse_epk_to_uds3(test_epk, "test_antrag.epk")
        print("✓ EPK-Parsing erfolgreich")
        print(f"Prozess-Typ: {result['content']['process_subtype']}")
        print(f"Elemente: {result['epk_metadata']['element_distribution']}")
        print(f"Satelliten: {result['epk_metadata']['satellite_distribution']}")

        # Validierung testen
        validation_result = validator.validate_epk_process(test_epk)
        print(
            f"\n✓ Validierung: {'Bestanden' if validation_result.is_valid else 'Fehlgeschlagen'}"
        )
        print(f"Vollständigkeits-Score: {validation_result.completeness_score:.2f}")
        print(f"Satelliten-Abdeckung: {validation_result.satellite_coverage:.2f}")

    except Exception as e:
        print(f"✗ Test fehlgeschlagen: {e}")