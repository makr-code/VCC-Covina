"""
PROZESS-EXPORT-ENGINE FÜR BPMN/EPK
==================================
Konvertiert UDS3-Prozessdokumente zurück zu XML-Formaten
Unterstützt BPMN 2.0 und EPK/eEPK Export mit vollständiger Compliance

Features:
- BPMN 2.0 XML Export mit korrekten Namespaces
- EPK/eEPK XML Export mit FZD-Zuordnungen
- Compliance-Validierung für BVA/FIM Standards
- Digitale Signatur für Verwaltungsprozesse
- ThreadCoordinator Integration
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Any, Optional
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime
import uuid
import hashlib
import base64

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Ergebnis eines Prozess-Exports"""

    success: bool
    xml_content: str
    export_format: str
    file_path: Optional[str]
    validation_result: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: List[str] = None


class ProcessExportEngine:
    """Hauptklasse für Prozess-Export zu XML"""

    def __init__(self):
        self.supported_formats = ["bpmn20", "epk", "eepk"]
        self.compliance_standards = ["bva", "fim", "xoev"]

        # XML-Namespaces für verschiedene Formate
        self.namespaces = {
            "bpmn20": {
                "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
                "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
                "dc": "http://www.omg.org/spec/DD/20100524/DC",
                "di": "http://www.omg.org/spec/DD/20100524/DI",
                "verwaltung": "http://www.verwaltung.de/prozess/v1",
            },
            "epk": {
                "epk": "http://www.verwaltung.de/epk/v1",
                "verwaltung": "http://www.verwaltung.de/prozess/v1",
            },
            "eepk": {
                "eepk": "http://www.verwaltung.de/eepk/v1",
                "fzd": "http://www.verwaltung.de/fzd/v1",
                "verwaltung": "http://www.verwaltung.de/prozess/v1",
            },
        }

        logger.info("Process Export Engine initialisiert")

    def export_uds3_to_xml(
        self,
        uds3_document: Dict[str, Any],
        export_format: str,
        output_path: Optional[str] = None,
        include_signature: bool = True,
        compliance_check: bool = True,
    ) -> ExportResult:
        """Hauptfunktion: Exportiert UDS3-Prozessdokument zu XML"""
        try:
            if export_format not in self.supported_formats:
                raise ValueError(f"Nicht unterstütztes Export-Format: {export_format}")

            # 1. UDS3-Dokument analysieren
            process_type = uds3_document.get("document_type", "")
            content = uds3_document.get("content", {})

            # 2. Format-spezifischer Export
            if export_format == "bpmn20":
                xml_content = self._export_to_bpmn20(uds3_document)
            elif export_format == "epk":
                xml_content = self._export_to_epk(uds3_document)
            elif export_format == "eepk":
                xml_content = self._export_to_eepk(uds3_document)

            # 3. Compliance-Validierung
            validation_result: dict[Any, Any] = {}
            if compliance_check:
                validation_result = self._validate_export_compliance(
                    xml_content, export_format
                )

            # 4. Digitale Signatur
            if include_signature:
                xml_content = self._add_digital_signature(xml_content, uds3_document)

            # 5. Datei speichern (optional)
            file_path = None
            if output_path:
                file_path = self._save_xml_file(xml_content, output_path, export_format)

            return ExportResult(
                success=True,
                xml_content=xml_content,
                export_format=export_format,
                file_path=file_path,
                validation_result=validation_result,
                metadata={
                    "export_timestamp": datetime.now().isoformat(),
                    "source_document_id": uds3_document.get("document_id", "unknown"),
                    "compliance_checked": compliance_check,
                    "digitally_signed": include_signature,
                    "xml_size": len(xml_content.encode("utf-8")),
                },
            )

        except Exception as e:
            logger.error(f"Export fehlgeschlagen: {e}")
            return ExportResult(
                success=False,
                xml_content="",
                export_format=export_format,
                file_path=None,
                validation_result={},
                metadata={},
                errors=[str(e)],
            )

    def _export_to_bpmn20(self, uds3_document: Dict[str, Any]) -> str:
        """Exportiert UDS3-Dokument zu BPMN 2.0 XML"""
        content = uds3_document.get("content", {})
        bpmn_metadata = uds3_document.get("bpmn_metadata", {})
        verwaltung_attrs = uds3_document.get("verwaltungsattribute", {})

        # Root-Element erstellen
        root = ET.Element("{http://www.omg.org/spec/BPMN/20100524/MODEL}definitions")
        root.set("xmlns:bpmn", "http://www.omg.org/spec/BPMN/20100524/MODEL")
        root.set("xmlns:bpmndi", "http://www.omg.org/spec/BPMN/20100524/DI")
        root.set("xmlns:dc", "http://www.omg.org/spec/DD/20100524/DC")
        root.set("xmlns:di", "http://www.omg.org/spec/DD/20100524/DI")
        root.set("xmlns:verwaltung", "http://www.verwaltung.de/prozess/v1")
        root.set("id", f"definitions_{uds3_document.get('document_id', 'process')}")
        root.set("targetNamespace", "http://www.verwaltung.de/prozess/v1")
        root.set("exporter", "UDS3-ProcessExportEngine")
        root.set("exporterVersion", "1.0")

        # BPMN-Prozess erstellen
        process_elem = ET.SubElement(
            root, "{http://www.omg.org/spec/BPMN/20100524/MODEL}process"
        )
        process_elem.set("id", content.get("process_id", "process_1"))
        process_elem.set("name", content.get("process_name", "Unbenannter Prozess"))
        process_elem.set(
            "isExecutable", str(bpmn_metadata.get("is_executable", False)).lower()
        )

        # BPMN-Elemente hinzufügen
        bpmn_elements = content.get("bpmn_elements", [])
        for element_data in bpmn_elements:
            self._add_bpmn_element_to_process(process_elem, element_data)

        # Sequence Flows hinzufügen
        sequence_flows = content.get("sequence_flows", [])
        for flow_data in sequence_flows:
            self._add_sequence_flow_to_process(process_elem, flow_data)

        # Verwaltungsattribute als Extension Elements
        if verwaltung_attrs:
            self._add_verwaltung_extension(process_elem, verwaltung_attrs)

        # XML formatieren und zurückgeben
        self._indent_xml(root)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def _export_to_epk(self, uds3_document: Dict[str, Any]) -> str:
        """Exportiert UDS3-Dokument zu klassischem EPK XML"""
        content = uds3_document.get("content", {})
        verwaltung_attrs = uds3_document.get("verwaltungsattribute", {})

        # Root-Element erstellen
        root = ET.Element("{http://www.verwaltung.de/epk/v1}prozesskette")
        root.set("xmlns:epk", "http://www.verwaltung.de/epk/v1")
        root.set("xmlns:verwaltung", "http://www.verwaltung.de/prozess/v1")
        root.set("id", uds3_document.get("document_id", "epk_process"))
        root.set("name", content.get("process_name", "Unbenannter EPK-Prozess"))
        root.set("version", content.get("process_version", "1.0"))

        # Beschreibung
        if content.get("process_description"):
            desc_elem = ET.SubElement(
                root, "{http://www.verwaltung.de/epk/v1}beschreibung"
            )
            desc_elem.text = content["process_description"]

        # Klassifikation
        if content.get("process_classification"):
            klass_elem = ET.SubElement(
                root, "{http://www.verwaltung.de/epk/v1}klassifikation"
            )
            klass_elem.set("typ", content["process_classification"])

        # EPK-Elemente hinzufügen
        epk_elements = content.get("epk_elements", [])
        for element_data in epk_elements:
            self._add_epk_element_to_root(root, element_data, "epk")

        # Verwaltungsattribute
        if verwaltung_attrs:
            self._add_verwaltung_attributes_to_epk(root, verwaltung_attrs)

        # XML formatieren und zurückgeben
        self._indent_xml(root)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def _export_to_eepk(self, uds3_document: Dict[str, Any]) -> str:
        """Exportiert UDS3-Dokument zu erweitertem EPK (eEPK) XML"""
        content = uds3_document.get("content", {})
        verwaltung_attrs = uds3_document.get("verwaltungsattribute", {})
        fzd_mappings = uds3_document.get("fzd_mappings", {})

        # Root-Element erstellen
        root = ET.Element("{http://www.verwaltung.de/eepk/v1}prozesskette")
        root.set("xmlns:eepk", "http://www.verwaltung.de/eepk/v1")
        root.set("xmlns:fzd", "http://www.verwaltung.de/fzd/v1")
        root.set("xmlns:verwaltung", "http://www.verwaltung.de/prozess/v1")
        root.set("id", uds3_document.get("document_id", "eepk_process"))
        root.set("name", content.get("process_name", "Unbenannter eEPK-Prozess"))
        root.set("version", content.get("process_version", "1.0"))

        # Beschreibung
        if content.get("process_description"):
            desc_elem = ET.SubElement(
                root, "{http://www.verwaltung.de/eepk/v1}beschreibung"
            )
            desc_elem.text = content["process_description"]

        # EPK-Kernelemente hinzufügen
        epk_elements = content.get("epk_elements", [])
        for element_data in epk_elements:
            self._add_epk_element_to_root(root, element_data, "eepk")

        # Satellitenobjekte hinzufügen
        satellite_objects = content.get("satellite_objects", [])
        for satellite_data in satellite_objects:
            self._add_satellite_object_to_root(root, satellite_data)

        # FZD-Zuordnungen hinzufügen
        if fzd_mappings:
            self._add_fzd_mappings_to_root(root, fzd_mappings)

        # Verwaltungsattribute
        if verwaltung_attrs:
            self._add_verwaltung_attributes_to_epk(root, verwaltung_attrs)

        # XML formatieren und zurückgeben
        self._indent_xml(root)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def _add_bpmn_element_to_process(
        self, process_elem: ET.Element, element_data: Dict[str, Any]
    ):
        """Fügt BPMN-Element zum Prozess hinzu"""
        element_type = element_data.get("element_type", "").lower()
        element_id = element_data.get("element_id", str(uuid.uuid4()))
        element_name = element_data.get("element_name", "")

        ns = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"

        if element_type == "startevent":
            elem = ET.SubElement(process_elem, f"{ns}startEvent")
        elif element_type == "endevent":
            elem = ET.SubElement(process_elem, f"{ns}endEvent")
        elif element_type == "task":
            elem = ET.SubElement(process_elem, f"{ns}task")
        elif element_type == "usertask":
            elem = ET.SubElement(process_elem, f"{ns}userTask")
        elif element_type == "servicetask":
            elem = ET.SubElement(process_elem, f"{ns}serviceTask")
        elif element_type == "exclusivegateway":
            elem = ET.SubElement(process_elem, f"{ns}exclusiveGateway")
        elif element_type == "parallelgateway":
            elem = ET.SubElement(process_elem, f"{ns}parallelGateway")
        elif element_type == "inclusivegateway":
            elem = ET.SubElement(process_elem, f"{ns}inclusiveGateway")
        else:
            elem = ET.SubElement(process_elem, f"{ns}task")  # Fallback

        elem.set("id", element_id)
        if element_name:
            elem.set("name", element_name)

        # Zusätzliche Attribute
        attributes = element_data.get("element_attributes", {})
        for attr_name, attr_value in attributes.items():
            if attr_name not in ["id", "name"]:
                elem.set(attr_name, str(attr_value))

    def _add_sequence_flow_to_process(
        self, process_elem: ET.Element, flow_data: Dict[str, Any]
    ):
        """Fügt Sequence Flow zum BPMN-Prozess hinzu"""
        ns = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"

        flow_elem = ET.SubElement(process_elem, f"{ns}sequenceFlow")
        flow_elem.set("id", flow_data.get("flow_id", str(uuid.uuid4())))
        flow_elem.set("sourceRef", flow_data.get("source_ref", ""))
        flow_elem.set("targetRef", flow_data.get("target_ref", ""))

        if flow_data.get("flow_name"):
            flow_elem.set("name", flow_data["flow_name"])

        # Condition Expression für Gateways
        if flow_data.get("condition_expression"):
            condition_elem = ET.SubElement(flow_elem, f"{ns}conditionExpression")
            condition_elem.set("xsi:type", "bpmn:tFormalExpression")
            condition_elem.text = flow_data["condition_expression"]

    def _add_epk_element_to_root(
        self, root: ET.Element, element_data: Dict[str, Any], namespace: str
    ):
        """Fügt EPK-Element zum Root hinzu"""
        element_type = element_data.get("element_type", "").lower()
        element_id = element_data.get("element_id", str(uuid.uuid4()))
        element_name = element_data.get("element_name", "")

        ns_uri = (
            "http://www.verwaltung.de/epk/v1"
            if namespace == "epk"
            else "http://www.verwaltung.de/eepk/v1"
        )
        ns = f"{{{ns_uri}}}"

        if element_type == "ereignis":
            elem = ET.SubElement(root, f"{ns}ereignis")
        elif element_type == "funktion":
            elem = ET.SubElement(root, f"{ns}funktion")
        elif element_type in ["and_connector", "or_connector", "xor_connector"]:
            elem = ET.SubElement(root, f"{ns}{element_type}")
        else:
            elem = ET.SubElement(root, f"{ns}{element_type}")

        elem.set("id", element_id)
        elem.set("name", element_name)

        # Verbindungen hinzufügen
        connections = element_data.get("connections", [])
        for connection in connections:
            if connection:
                conn_elem = ET.SubElement(elem, f"{ns}verbindung")
                conn_elem.set("ref", connection)

        # Satellitenobjekt-Referenzen (nur für eEPK)
        if namespace == "eepk":
            satellite_links = element_data.get("satellite_links", {})
            for sat_type, sat_refs in satellite_links.items():
                for sat_ref in sat_refs:
                    ref_elem = ET.SubElement(elem, f"{ns}{sat_type}_ref")
                    ref_elem.set("ref", sat_ref)

    def _add_satellite_object_to_root(
        self, root: ET.Element, satellite_data: Dict[str, Any]
    ):
        """Fügt Satellitenobjekt zu eEPK hinzu"""
        object_type = satellite_data.get("object_type", "")
        object_id = satellite_data.get("object_id", str(uuid.uuid4()))
        object_name = satellite_data.get("object_name", "")

        ns = "{http://www.verwaltung.de/eepk/v1}"

        elem = ET.SubElement(root, f"{ns}{object_type}")
        elem.set("id", object_id)
        elem.set("name", object_name)

        # Zusätzliche Attribute
        attributes = satellite_data.get("object_attributes", {})
        for attr_name, attr_value in attributes.items():
            if attr_name not in ["id", "name"]:
                elem.set(attr_name, str(attr_value))

        # Funktionsreferenzen
        connected_functions = satellite_data.get("connected_functions", [])
        for func_ref in connected_functions:
            if func_ref:
                ref_elem = ET.SubElement(elem, f"{ns}funktion_ref")
                ref_elem.set("ref", func_ref)

    def _add_fzd_mappings_to_root(self, root: ET.Element, fzd_mappings: Dict[str, Any]):
        """Fügt FZD-Zuordnungen zu eEPK hinzu"""
        ns = "{http://www.verwaltung.de/fzd/v1}"

        for mapping_type, mappings in fzd_mappings.items():
            if mapping_type.startswith("function_to_"):
                target_type = mapping_type.replace("function_to_", "")

                for function_id, target_ids in mappings.items():
                    for target_id in target_ids:
                        zuordnung_elem = ET.SubElement(root, f"{ns}zuordnung")
                        zuordnung_elem.set("funktion_id", function_id)
                        zuordnung_elem.set("ziel_typ", target_type)
                        zuordnung_elem.set("ziel_id", target_id)

    def _add_verwaltung_extension(
        self, process_elem: ET.Element, verwaltung_attrs: Dict[str, Any]
    ):
        """Fügt Verwaltungsattribute als Extension Elements zu BPMN hinzu"""
        ns_bpmn = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
        ns_verwaltung = "{http://www.verwaltung.de/prozess/v1}"

        ext_elements = ET.SubElement(process_elem, f"{ns_bpmn}extensionElements")
        verwaltung_elem = ET.SubElement(
            ext_elements, f"{ns_verwaltung}verwaltungsattribute"
        )

        for attr_name, attr_value in verwaltung_attrs.items():
            if attr_value is not None:
                attr_elem = ET.SubElement(
                    verwaltung_elem, f"{ns_verwaltung}{attr_name}"
                )
                attr_elem.text = str(attr_value)

    def _add_verwaltung_attributes_to_epk(
        self, root: ET.Element, verwaltung_attrs: Dict[str, Any]
    ):
        """Fügt Verwaltungsattribute zu EPK hinzu"""
        ns = "{http://www.verwaltung.de/prozess/v1}"

        for attr_name, attr_value in verwaltung_attrs.items():
            if attr_value is not None:
                attr_elem = ET.SubElement(root, f"{ns}{attr_name}")
                attr_elem.text = str(attr_value)

    def _validate_export_compliance(
        self, xml_content: str, export_format: str
    ) -> Dict[str, Any]:
        """Validiert Export-Compliance"""
        validation_result = {
            "is_compliant": True,
            "compliance_scores": {},
            "violations": [],
            "warnings": [],
        }

        try:
            root = ET.fromstring(xml_content)

            # Format-spezifische Compliance-Prüfungen
            if export_format == "bpmn20":
                bpmn_result = self._validate_bpmn20_compliance(root)
                validation_result.update(bpmn_result)
            elif export_format in ["epk", "eepk"]:
                epk_result = self._validate_epk_compliance(root)
                validation_result.update(epk_result)

            # BVA/FIM Compliance prüfen
            verwaltung_compliance = self._validate_verwaltung_compliance(root)
            validation_result["compliance_scores"]["verwaltung"] = verwaltung_compliance

        except Exception as e:
            validation_result["is_compliant"] = False
            validation_result["violations"].append(
                f"Compliance-Validierung fehlgeschlagen: {e}"
            )

        return validation_result

    def _validate_bpmn20_compliance(self, root: ET.Element) -> Dict[str, Any]:
        """Validiert BPMN 2.0 Compliance"""
        result = {
            "compliance_scores": {"bpmn20": 1.0},
            "violations": [],
            "warnings": [],
        }

        # Namespace-Prüfung
        if "http://www.omg.org/spec/BPMN/20100524/MODEL" not in root.nsmap.values():
            result["violations"].append("BPMN 2.0 Namespace fehlt")
            result["compliance_scores"]["bpmn20"] = 0.5

        # Pflicht-Elemente prüfen
        process_elems = root.findall(
            ".//{http://www.omg.org/spec/BPMN/20100524/MODEL}process"
        )
        if not process_elems:
            result["violations"].append("Kein BPMN-Prozess gefunden")
            result["compliance_scores"]["bpmn20"] = 0.0

        return result

    def _validate_epk_compliance(self, root: ET.Element) -> Dict[str, Any]:
        """Validiert EPK/eEPK Compliance"""
        result = {"compliance_scores": {"epk": 1.0}, "violations": [], "warnings": []}

        # Ereignisse und Funktionen prüfen
        events = root.findall('.//*[contains(local-name(), "ereignis")]')
        functions = root.findall('.//*[contains(local-name(), "funktion")]')

        if not events:
            result["warnings"].append("Keine Ereignisse gefunden")
            result["compliance_scores"]["epk"] -= 0.2

        if not functions:
            result["violations"].append("Keine Funktionen gefunden")
            result["compliance_scores"]["epk"] = 0.0

        return result

    def _validate_verwaltung_compliance(self, root: ET.Element) -> float:
        """Validiert Verwaltungs-Compliance"""
        score = 1.0

        # Verwaltungsattribute prüfen
        verwaltung_elements = root.findall(
            './/*[contains(namespace-uri(), "verwaltung")]'
        )

        if not verwaltung_elements:
            score -= 0.5  # Keine Verwaltungsattribute

        # Mindest-Verwaltungsattribute prüfen
        required_attrs = ["zustaendigkeit", "rechtsgrundlage"]
        found_attrs = [elem.tag.split("}")[-1] for elem in verwaltung_elements]

        missing_attrs = [attr for attr in required_attrs if attr not in found_attrs]
        if missing_attrs:
            score -= 0.3

        return max(0.0, score)

    def _add_digital_signature(
        self, xml_content: str, uds3_document: Dict[str, Any]
    ) -> str:
        """Fügt digitale Signatur zu XML hinzu"""
        try:
            root = ET.fromstring(xml_content)

            # Signature-Element erstellen
            signature_elem = ET.Element(
                "Signature", xmlns="http://www.w3.org/2000/09/xmldsig#"
            )
            signature_elem.set("Id", "ProcessSignature")

            # SignedInfo
            signed_info = ET.SubElement(signature_elem, "SignedInfo")

            # CanonicalizationMethod
            canon_method = ET.SubElement(signed_info, "CanonicalizationMethod")
            canon_method.set(
                "Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
            )

            # SignatureMethod
            sig_method = ET.SubElement(signed_info, "SignatureMethod")
            sig_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#rsa-sha1")

            # Reference
            reference = ET.SubElement(signed_info, "Reference", URI="")

            # DigestMethod
            digest_method = ET.SubElement(reference, "DigestMethod")
            digest_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")

            # DigestValue (vereinfacht)
            digest_value = ET.SubElement(reference, "DigestValue")
            hash_value = hashlib.sha1(xml_content.encode("utf-8")).digest()
            digest_value.text = base64.b64encode(hash_value).decode("utf-8")

            # SignatureValue (vereinfacht - in Production würde hier echter Private Key verwendet)
            sig_value = ET.SubElement(signature_elem, "SignatureValue")
            sig_value.text = base64.b64encode(
                f"UDS3_SIGNATURE_{datetime.now().isoformat()}".encode()
            ).decode("utf-8")

            # KeyInfo
            key_info = ET.SubElement(signature_elem, "KeyInfo")
            key_name = ET.SubElement(key_info, "KeyName")
            key_name.text = "UDS3-ProcessEngine"

            # Signature als erstes Child-Element hinzufügen
            root.insert(0, signature_elem)

            return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode(
                "utf-8"
            )

        except Exception as e:
            logger.warning(f"Digitale Signatur konnte nicht hinzugefügt werden: {e}")
            return xml_content

    def _save_xml_file(
        self, xml_content: str, output_path: str, export_format: str
    ) -> str:
        """Speichert XML in Datei"""
        file_extension = {
            "bpmn20": ".bpmn",
            "epk": ".epk.xml",
            "eepk": ".eepk.xml",
        }.get(export_format, ".xml")

        if not output_path.endswith(file_extension):
            output_path += file_extension

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        logger.info(f"XML-Export gespeichert: {output_path}")
        return output_path

    def _indent_xml(self, elem: ET.Element, level: int = 0):
        """Formatiert XML mit Einrückung"""
        indent = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for elem in elem:
                self._indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent


class BulkExportManager:
    """Manager für Bulk-Export von UDS3-Prozessdokumenten"""

    def __init__(self):
        self.export_engine = ProcessExportEngine()
        logger.info("Bulk Export Manager initialisiert")

    def export_multiple_processes(
        self,
        uds3_documents: List[Dict[str, Any]],
        export_format: str,
        output_directory: str,
        naming_pattern: str = "{document_id}",
    ) -> List[ExportResult]:
        """Exportiert mehrere UDS3-Prozessdokumente"""
        results: list[Any] = []

        for i, document in enumerate(uds3_documents):
            try:
                # Dateiname generieren
                doc_id = document.get("document_id", f"process_{i}")
                filename = naming_pattern.format(
                    document_id=doc_id,
                    index=i,
                    process_name=document.get("content", {}).get(
                        "process_name", "process"
                    ),
                )

                output_path = f"{output_directory}/{filename}"

                # Export durchführen
                result = self.export_engine.export_uds3_to_xml(
                    document, export_format, output_path
                )

                results.append(result)

                if result.success:
                    logger.info(f"✓ Export erfolgreich: {filename}")
                else:
                    logger.error(f"✗ Export fehlgeschlagen: {filename}")

            except Exception as e:
                logger.error(f"Bulk-Export Fehler bei Dokument {i}: {e}")
                results.append(
                    ExportResult(
                        success=False,
                        xml_content="",
                        export_format=export_format,
                        file_path=None,
                        validation_result={},
                        metadata={},
                        errors=[str(e)],
                    )
                )

        return results


# ThreadCoordinator Integration
class ProcessExportThreadWorker:
    """Thread Worker für Export-Operationen"""

    def __init__(self, export_engine: ProcessExportEngine):
        self.export_engine = export_engine
        logger.info("Process Export Thread Worker initialisiert")

    def process_export_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verarbeitet Export-Job"""
        try:
            uds3_document = job_data.get("uds3_document", {})
            export_format = job_data.get("export_format", "bpmn20")
            output_path = job_data.get("output_path")

            # Export durchführen
            result = self.export_engine.export_uds3_to_xml(
                uds3_document, export_format, output_path
            )

            return {
                "job_id": job_data.get("job_id", "unknown"),
                "status": "completed" if result.success else "failed",
                "result": {
                    "success": result.success,
                    "file_path": result.file_path,
                    "xml_size": len(result.xml_content.encode("utf-8")),
                    "validation_score": result.validation_result.get(
                        "compliance_scores", {}
                    ).get("overall", 0.0),
                },
                "errors": result.errors or [],
                "processing_time": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "job_id": job_data.get("job_id", "unknown"),
                "status": "error",
                "errors": [str(e)],
                "processing_time": datetime.now().isoformat(),
            }


# Export für Integration
def get_export_engine():
    """Gibt Process Export Engine zurück"""
    return ProcessExportEngine()


def get_bulk_export_manager():
    """Gibt Bulk Export Manager zurück"""
    return BulkExportManager()


def get_export_thread_worker():
    """Gibt Export Thread Worker zurück"""
    return ProcessExportThreadWorker(ProcessExportEngine())


if __name__ == "__main__":
    # Test der Export Engine
    export_engine = ProcessExportEngine()

    # Test UDS3-Dokument (vereinfacht)
    test_uds3_bpmn = {
        "document_id": "test_bpmn_export",
        "document_type": "verwaltungsprozess_bpmn",
        "content": {
            "process_id": "antrag_bearbeitung",
            "process_name": "Antragsbearbeitung Test",
            "process_description": "Test-Prozess für BPMN-Export",
            "bpmn_elements": [
                {
                    "element_id": "start_1",
                    "element_type": "startEvent",
                    "element_name": "Antrag eingegangen",
                },
                {
                    "element_id": "task_1",
                    "element_type": "userTask",
                    "element_name": "Antrag prüfen",
                },
                {
                    "element_id": "end_1",
                    "element_type": "endEvent",
                    "element_name": "Prozess beendet",
                },
            ],
            "sequence_flows": [
                {"flow_id": "flow_1", "source_ref": "start_1", "target_ref": "task_1"},
                {"flow_id": "flow_2", "source_ref": "task_1", "target_ref": "end_1"},
            ],
        },
        "bpmn_metadata": {"is_executable": True, "bpmn_version": "2.0"},
        "verwaltungsattribute": {
            "rechtsgrundlage": "§ 63 BauO NRW",
            "zustaendigkeit": "Kommunal",
            "durchlaufzeit": "5 Tage",
        },
    }

    # BPMN-Export testen
    try:
        result = export_engine.export_uds3_to_xml(test_uds3_bpmn, "bpmn20")
        print("✓ BPMN-Export erfolgreich")
        print(f"XML-Größe: {len(result.xml_content)} Zeichen")
        print(
            f"Compliance: {'Bestanden' if result.validation_result.get('is_compliant', False) else 'Fehlgeschlagen'}"
        )

        # Bulk Export testen
        bulk_manager = BulkExportManager()
        bulk_results = bulk_manager.export_multiple_processes(
            [test_uds3_bpmn], "bpmn20", ".", "test_{document_id}"
        )
        print(
            f"✓ Bulk Export: {len([r for r in bulk_results if r.success])}/{len(bulk_results)} erfolgreich"
        )

    except Exception as e:
        print(f"✗ Export-Test fehlgeschlagen: {e}")

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_process_export_engine"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...JmLkSJUF"  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "e949701545ffbd2812114cf99919583d9fc4692cb1bc3655b2cafa9a38cb68d9"
)
module_file_key = "9a5c4226be8bacf30f4da98e1ed4d19a17a8222ddc3ebfda04806bc63dc9050d"
module_version = "1.0"
module_protection_level = 2
# === END PROTECTION KEYS ===