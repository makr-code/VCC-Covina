"""
UDS3 Process Parser Base Classes
================================

Gemeinsame Basis-Funktionalität für BPMN und EPK Parser.
Reduziert Code-Duplikation und standardisiert Parser-Architektur.

Author: UDS3 Framework
Date: 1. Oktober 2025
Status: Neu erstellt (Todo #5)
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================================================
# Gemeinsame Dataclasses
# ============================================================================

@dataclass
class ProcessElement:
    """
    Basis-Repräsentation eines Prozess-Elements.
    Abstrakt für BPMN und EPK verwendbar.
    """
    element_id: str
    element_type: str
    name: str
    attributes: Dict[str, Any]
    connections: List[str]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """
    Basis-Validierungsergebnis für Prozess-Parser.
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    compliance_score: float
    details: Dict[str, Any]


# ============================================================================
# Abstract Base Parser
# ============================================================================

class ProcessParserBase(ABC):
    """
    Abstrakte Basis-Klasse für alle Prozess-Parser.
    
    Bietet gemeinsame Funktionalität für:
    - XML-Parsing
    - Namespace-Handling
    - Verwaltungs-Attribute-Extraktion
    - Element-Verarbeitung
    - Validierung
    - UDS3-Konvertierung
    """

    def __init__(self):
        """Initialisiert den Base Parser."""
        self.namespaces: Dict[str, str] = {}
        self.element_processors: Dict[str, Callable] = {}
        self.verwaltung_attributes: Dict[str, type] = {}

    # ========================================================================
    # Abstract Methods (müssen von Subklassen implementiert werden)
    # ========================================================================

    @abstractmethod
    def parse_to_uds3(self, xml_content: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Hauptmethode zum Parsen von Prozess-XML zu UDS3-Format.
        
        Args:
            xml_content: XML-Inhalt als String
            filename: Optionaler Dateiname für Metadaten
            
        Returns:
            UDS3-Prozessdokument als Dictionary
        """
        pass

    @abstractmethod
    def validate_process(self, process_data: Dict[str, Any]) -> ValidationResult:
        """
        Validiert ein gepartes Prozess-Dokument.
        
        Args:
            process_data: Geparste Prozessdaten
            
        Returns:
            Validierungsergebnis
        """
        pass

    # ========================================================================
    # Gemeinsame XML-Parsing Methoden
    # ========================================================================

    def parse_xml(self, xml_content: str) -> ET.Element:
        """
        Parst XML-String zu ElementTree.
        
        Args:
            xml_content: XML-Inhalt als String
            
        Returns:
            Root Element des XML-Baums
            
        Raises:
            ET.ParseError: Bei ungültigem XML
        """
        try:
            return ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"XML-Parsing-Fehler: {e}")
            raise

    def find_elements(
        self, 
        root: ET.Element, 
        xpath: str, 
        namespace: Optional[str] = None
    ) -> List[ET.Element]:
        """
        Findet Elemente via XPath mit Namespace-Unterstützung.
        
        Args:
            root: Root Element
            xpath: XPath-Ausdruck
            namespace: Optionaler Namespace-Key
            
        Returns:
            Liste gefundener Elemente
        """
        if namespace and namespace in self.namespaces:
            return root.findall(xpath, self.namespaces)
        return root.findall(xpath)

    def get_attribute(
        self, 
        elem: ET.Element, 
        attr_name: str, 
        default: Any = None
    ) -> Any:
        """
        Liest Attribut mit Fallback.
        
        Args:
            elem: XML-Element
            attr_name: Attribut-Name
            default: Fallback-Wert
            
        Returns:
            Attribut-Wert oder Default
        """
        return elem.get(attr_name, default)

    def get_text(self, elem: ET.Element, default: str = "") -> str:
        """
        Liest Text-Inhalt eines Elements.
        
        Args:
            elem: XML-Element
            default: Fallback-Text
            
        Returns:
            Text-Inhalt oder Default
        """
        return elem.text.strip() if elem.text else default

    # ========================================================================
    # Gemeinsame Verwaltungs-Attribute Methoden
    # ========================================================================

    def extract_verwaltung_attributes(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extrahiert Verwaltungs-spezifische Attribute aus XML.
        
        Args:
            root: Root Element
            
        Returns:
            Dictionary mit Verwaltungsattributen
        """
        attributes = {}
        
        # Suche nach verwaltung:* Attributen
        verwaltung_ns = self.namespaces.get("verwaltung", "")
        if not verwaltung_ns:
            return attributes
        
        # Alle Elemente mit Verwaltungs-Namespace durchsuchen
        for elem in root.iter():
            for attr_name, attr_value in elem.attrib.items():
                if verwaltung_ns in attr_name:
                    # Entferne Namespace-Prefix
                    clean_name = attr_name.split("}")[-1]
                    attributes[clean_name] = attr_value
        
        return attributes

    def validate_verwaltung_attributes(self, attributes: Dict[str, Any]) -> List[str]:
        """
        Validiert Verwaltungs-Attribute gegen Schema.
        
        Args:
            attributes: Zu validierende Attribute
            
        Returns:
            Liste von Validierungsfehlern (leer = valid)
        """
        errors = []
        
        for attr_name, expected_type in self.verwaltung_attributes.items():
            if attr_name in attributes:
                value = attributes[attr_name]
                if not isinstance(value, expected_type):
                    try:
                        # Versuche Type-Konvertierung
                        attributes[attr_name] = expected_type(value)
                    except (ValueError, TypeError):
                        errors.append(
                            f"Attribut '{attr_name}' hat falschen Typ. "
                            f"Erwartet: {expected_type.__name__}, "
                            f"Erhalten: {type(value).__name__}"
                        )
        
        return errors

    # ========================================================================
    # Gemeinsame Element-Verarbeitung
    # ========================================================================

    def process_element(
        self, 
        elem: ET.Element, 
        element_type: str
    ) -> Optional[ProcessElement]:
        """
        Verarbeitet ein Element mit registriertem Processor.
        
        Args:
            elem: XML-Element
            element_type: Typ des Elements
            
        Returns:
            ProcessElement oder None bei Fehler
        """
        if element_type not in self.element_processors:
            logger.warning(f"Kein Processor für Element-Typ: {element_type}")
            return None
        
        try:
            processor = self.element_processors[element_type]
            return processor(elem)
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von {element_type}: {e}")
            return None

    def extract_connections(self, elem: ET.Element, connection_tag: str) -> List[str]:
        """
        Extrahiert Verbindungen zu anderen Elementen.
        
        Args:
            elem: XML-Element
            connection_tag: Tag-Name für Verbindungen (z.B. "outgoing", "target")
            
        Returns:
            Liste von Element-IDs
        """
        connections = []
        
        for conn_elem in elem.findall(f".//{connection_tag}", self.namespaces):
            conn_id = conn_elem.text or conn_elem.get("id")
            if conn_id:
                connections.append(conn_id.strip())
        
        return connections

    # ========================================================================
    # Gemeinsame UDS3-Konvertierung
    # ========================================================================

    def create_uds3_metadata(
        self, 
        filename: Optional[str] = None,
        process_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Erstellt Standard-UDS3-Metadaten.
        
        Args:
            filename: Optionaler Dateiname
            process_info: Optionale Prozess-Informationen
            
        Returns:
            UDS3-Metadaten Dictionary
        """
        metadata = {
            "document_id": self.generate_document_id(filename),
            "document_type": "prozess",
            "created_at": datetime.now().isoformat(),
            "parser_version": "1.0",
            "source_format": self.__class__.__name__.replace("Parser", "").lower(),
        }
        
        if filename:
            metadata["source_filename"] = filename
        
        if process_info:
            metadata.update(process_info)
        
        return metadata

    def generate_document_id(self, filename: Optional[str] = None) -> str:
        """
        Generiert eine eindeutige Dokument-ID.
        
        Args:
            filename: Optionaler Dateiname
            
        Returns:
            Eindeutige ID
        """
        import hashlib
        
        base = filename or datetime.now().isoformat()
        hash_obj = hashlib.sha256(base.encode())
        return f"proc_{hash_obj.hexdigest()[:16]}"

    # ========================================================================
    # Gemeinsame Validierungs-Hilfsfunktionen
    # ========================================================================

    def check_required_fields(
        self, 
        data: Dict[str, Any], 
        required_fields: List[str]
    ) -> List[str]:
        """
        Prüft ob alle erforderlichen Felder vorhanden sind.
        
        Args:
            data: Zu prüfende Daten
            required_fields: Liste erforderlicher Feld-Namen
            
        Returns:
            Liste fehlender Felder (leer = alle vorhanden)
        """
        missing = []
        
        for field in required_fields:
            if field not in data or data[field] is None:
                missing.append(field)
        
        return missing

    def calculate_completeness_score(
        self, 
        data: Dict[str, Any], 
        optional_fields: List[str]
    ) -> float:
        """
        Berechnet Vollständigkeits-Score (0.0 - 1.0).
        
        Args:
            data: Zu bewertende Daten
            optional_fields: Liste optionaler Felder
            
        Returns:
            Score zwischen 0.0 (leer) und 1.0 (vollständig)
        """
        if not optional_fields:
            return 1.0
        
        present_count = sum(1 for field in optional_fields if field in data and data[field])
        return present_count / len(optional_fields)

    # ========================================================================
    # Logging und Debugging
    # ========================================================================

    def log_parsing_summary(
        self, 
        elements_count: int, 
        validation_result: ValidationResult
    ) -> None:
        """
        Loggt Parsing-Zusammenfassung.
        
        Args:
            elements_count: Anzahl verarbeiteter Elemente
            validation_result: Validierungsergebnis
        """
        logger.info(f"=== {self.__class__.__name__} Zusammenfassung ===")
        logger.info(f"Elemente verarbeitet: {elements_count}")
        logger.info(f"Validierung: {'✅ Erfolgreich' if validation_result.is_valid else '❌ Fehler'}")
        logger.info(f"Compliance Score: {validation_result.compliance_score:.2f}")
        
        if validation_result.errors:
            logger.warning(f"Fehler: {len(validation_result.errors)}")
            for error in validation_result.errors[:5]:  # Nur erste 5
                logger.warning(f"  - {error}")
        
        if validation_result.warnings:
            logger.info(f"Warnungen: {len(validation_result.warnings)}")


# ============================================================================
# Gemeinsame Utility-Funktionen
# ============================================================================

def sanitize_xml_string(xml_content: str) -> str:
    """
    Bereinigt XML-String von problematischen Zeichen.
    
    Args:
        xml_content: Roher XML-String
        
    Returns:
        Bereinigter XML-String
    """
    # Entferne BOM
    if xml_content.startswith('\ufeff'):
        xml_content = xml_content[1:]
    
    # Entferne führende/trailing Whitespaces
    xml_content = xml_content.strip()
    
    return xml_content


def merge_process_metadata(
    base_metadata: Dict[str, Any], 
    additional_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Mergt Prozess-Metadaten mit Konfliktauflösung.
    
    Args:
        base_metadata: Basis-Metadaten
        additional_metadata: Zusätzliche Metadaten
        
    Returns:
        Gemergete Metadaten
    """
    merged = base_metadata.copy()
    
    for key, value in additional_metadata.items():
        if key in merged and merged[key] != value:
            # Bei Konflikt: Erstelle Liste mit beiden Werten
            if not isinstance(merged[key], list):
                merged[key] = [merged[key]]
            if value not in merged[key]:
                merged[key].append(value)
        else:
            merged[key] = value
    
    return merged
