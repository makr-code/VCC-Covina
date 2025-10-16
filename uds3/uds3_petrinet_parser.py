"""
UDS3 Petri-Netz Parser (PNML Format)
====================================

Parser für Petri-Netze im PNML-Format (Petri Net Markup Language).
Basiert auf ISO/IEC 15909-2:2011 Standard.

Unterstützt:
- Place/Transition Netze (P/T-Netze)
- Colored Petri Nets (CPN)
- Timed Petri Nets
- Workflow-Nets (WF-Nets)

Author: UDS3 Framework
Date: 1. Oktober 2025
Status: Prototyp (Research Feature)
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from uds3_process_parser_base import (
    ProcessParserBase,
    ProcessElement,
    ValidationResult,
    sanitize_xml_string
)

logger = logging.getLogger(__name__)


# ============================================================================
# Petri-Netz spezifische Dataclasses
# ============================================================================

class PetriNetType(Enum):
    """Typen von Petri-Netzen"""
    PT_NET = "place_transition"  # Klassisches P/T-Netz
    COLORED = "colored"           # Colored Petri Net
    TIMED = "timed"              # Timed Petri Net
    WORKFLOW = "workflow"         # Workflow-Net (WF-Net)
    STOCHASTIC = "stochastic"    # Stochastic Petri Net


@dataclass
class Place:
    """
    Stelle (Place) im Petri-Netz.
    Repräsentiert Zustände oder Bedingungen.
    """
    id: str
    name: str
    initial_marking: int = 0  # Anzahl Tokens bei Start
    capacity: Optional[int] = None  # Max. Tokens (None = unbegrenzt)
    position: Optional[Tuple[float, float]] = None  # (x, y) Koordinaten
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transition:
    """
    Transition im Petri-Netz.
    Repräsentiert Aktivitäten oder Ereignisse.
    """
    id: str
    name: str
    guard: Optional[str] = None  # Bedingung für Aktivierung
    priority: int = 0  # Priorität bei Konflikten
    timed: bool = False  # Zeitbehaftet?
    delay: Optional[float] = None  # Verzögerung in Zeiteinheiten
    position: Optional[Tuple[float, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Arc:
    """
    Kante (Arc) im Petri-Netz.
    Verbindet Places mit Transitions.
    """
    id: str
    source: str  # Place-ID oder Transition-ID
    target: str  # Transition-ID oder Place-ID
    weight: int = 1  # Anzahl bewegter Tokens
    inscription: Optional[str] = None  # Colored Petri Nets: Token-Farbe
    arc_type: str = "normal"  # "normal", "inhibitor", "reset"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PetriNet:
    """
    Komplettes Petri-Netz.
    """
    id: str
    name: str
    net_type: PetriNetType
    places: List[Place]
    transitions: List[Transition]
    arcs: List[Arc]
    initial_marking: Dict[str, int] = field(default_factory=dict)  # place_id -> token_count
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_place(self, place_id: str) -> Optional[Place]:
        """Findet Place by ID."""
        return next((p for p in self.places if p.id == place_id), None)

    def get_transition(self, trans_id: str) -> Optional[Transition]:
        """Findet Transition by ID."""
        return next((t for t in self.transitions if t.id == trans_id), None)

    def get_preset(self, node_id: str) -> Set[str]:
        """Gibt Vorbereich (Preset) eines Knotens zurück."""
        return {arc.source for arc in self.arcs if arc.target == node_id}

    def get_postset(self, node_id: str) -> Set[str]:
        """Gibt Nachbereich (Postset) eines Knotens zurück."""
        return {arc.target for arc in self.arcs if arc.source == node_id}

    def is_workflow_net(self) -> bool:
        """
        Prüft ob Netz ein Workflow-Net ist.
        
        Bedingungen:
        - Genau 1 Source-Place (kein Preset)
        - Genau 1 Sink-Place (kein Postset)
        - Alle Knoten auf Pfad von Source zu Sink
        """
        sources = [p.id for p in self.places if not self.get_preset(p.id)]
        sinks = [p.id for p in self.places if not self.get_postset(p.id)]
        
        return len(sources) == 1 and len(sinks) == 1


@dataclass
class PetriNetValidationResult(ValidationResult):
    """Erweiterte Validierung für Petri-Netze."""
    is_workflow_net: bool = False
    is_sound: Optional[bool] = None  # WF-Net Soundness
    is_bounded: Optional[bool] = None  # Beschränktheit
    is_live: Optional[bool] = None  # Lebendigkeit
    structural_properties: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Petri-Netz Parser
# ============================================================================

class PetriNetParser(ProcessParserBase):
    """
    Parser für Petri-Netze im PNML-Format.
    
    PNML (Petri Net Markup Language) ist der ISO-Standard für Petri-Netze.
    Siehe: ISO/IEC 15909-2:2011
    """

    def __init__(self):
        """Initialisiert Petri-Netz Parser."""
        super().__init__()
        
        # PNML Namespaces
        self.namespaces = {
            "pnml": "http://www.pnml.org/version-2009/grammar/pnml",
            "pnmlcoremodel": "http://www.pnml.org/version-2009/grammar/pnmlcoremodel",
            "ptnet": "http://www.pnml.org/version-2009/grammar/ptnet",
            "hlpn": "http://www.pnml.org/version-2009/grammar/highlevelnet",
            "verwaltung": "http://www.verwaltung.de/prozess/v1",
        }

    def parse_to_uds3(
        self, 
        pnml_content: str, 
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parst PNML zu UDS3-Prozessdokument.
        
        Args:
            pnml_content: PNML XML als String
            filename: Optionaler Dateiname
            
        Returns:
            UDS3-Prozessdokument mit Petri-Netz
        """
        logger.info(f"Parse Petri-Netz: {filename or 'unnamed'}")
        
        # XML parsen
        pnml_content = sanitize_xml_string(pnml_content)
        root = self.parse_xml(pnml_content)
        
        # Petri-Netz extrahieren
        petri_net = self._extract_petri_net(root)
        
        # Validierung
        validation = self.validate_process(petri_net)
        
        # UDS3-Format erstellen
        uds3_doc = {
            "metadata": self.create_uds3_metadata(filename, {
                "net_type": petri_net.net_type.value,
                "places_count": len(petri_net.places),
                "transitions_count": len(petri_net.transitions),
                "arcs_count": len(petri_net.arcs),
            }),
            "petri_net": {
                "id": petri_net.id,
                "name": petri_net.name,
                "type": petri_net.net_type.value,
                "places": [self._place_to_dict(p) for p in petri_net.places],
                "transitions": [self._transition_to_dict(t) for t in petri_net.transitions],
                "arcs": [self._arc_to_dict(a) for a in petri_net.arcs],
                "initial_marking": petri_net.initial_marking,
            },
            "validation": {
                "is_valid": validation.is_valid,
                "is_workflow_net": validation.is_workflow_net,
                "errors": validation.errors,
                "warnings": validation.warnings,
                "compliance_score": validation.compliance_score,
            },
            "verwaltung_attributes": self.extract_verwaltung_attributes(root),
        }
        
        self.log_parsing_summary(
            len(petri_net.places) + len(petri_net.transitions),
            validation
        )
        
        return uds3_doc

    def validate_process(self, petri_net: PetriNet) -> PetriNetValidationResult:
        """
        Validiert Petri-Netz Struktur.
        
        Args:
            petri_net: Zu validierendes Petri-Netz
            
        Returns:
            Validierungsergebnis
        """
        errors = []
        warnings = []
        
        # Basis-Validierung
        if not petri_net.places:
            errors.append("Petri-Netz hat keine Places")
        
        if not petri_net.transitions:
            errors.append("Petri-Netz hat keine Transitions")
        
        # Arc-Validierung
        place_ids = {p.id for p in petri_net.places}
        trans_ids = {t.id for t in petri_net.transitions}
        
        for arc in petri_net.arcs:
            # Arc muss Place↔Transition verbinden
            source_is_place = arc.source in place_ids
            target_is_place = arc.target in place_ids
            
            if source_is_place == target_is_place:
                errors.append(
                    f"Arc {arc.id}: Muss Place-Transition oder Transition-Place verbinden"
                )
        
        # Workflow-Net Check
        is_wfnet = petri_net.is_workflow_net()
        
        if is_wfnet:
            logger.info("✅ Struktur ist ein Workflow-Net")
        else:
            warnings.append("Keine Workflow-Net Struktur (nicht kritisch)")
        
        # Compliance Score
        score = 1.0
        if errors:
            score = 0.0
        elif warnings:
            score = 0.8
        
        return PetriNetValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            compliance_score=score,
            is_workflow_net=is_wfnet,
            details={"petri_net": petri_net}
        )

    # ========================================================================
    # Private Extraction Methods
    # ========================================================================

    def _extract_petri_net(self, root: ET.Element) -> PetriNet:
        """Extrahiert Petri-Netz aus PNML Root."""
        
        # Finde <net> Element
        net_elem = root.find(".//pnml:net", self.namespaces)
        if net_elem is None:
            net_elem = root.find(".//net")  # Fallback ohne Namespace
        
        if net_elem is None:
            raise ValueError("Kein <net> Element in PNML gefunden")
        
        net_id = self.get_attribute(net_elem, "id", "net_1")
        net_type_str = self.get_attribute(net_elem, "type", "http://www.pnml.org/version-2009/grammar/ptnet")
        
        # Bestimme Netz-Typ
        net_type = PetriNetType.PT_NET
        if "ptnet" in net_type_str:
            net_type = PetriNetType.PT_NET
        elif "workflow" in net_type_str.lower():
            net_type = PetriNetType.WORKFLOW
        elif "colored" in net_type_str.lower() or "hlpn" in net_type_str:
            net_type = PetriNetType.COLORED
        
        # Name extrahieren
        name_elem = net_elem.find(".//pnml:name/pnml:text", self.namespaces)
        name = self.get_text(name_elem) if name_elem is not None else net_id
        
        # Places extrahieren
        places = self._extract_places(net_elem)
        
        # Transitions extrahieren
        transitions = self._extract_transitions(net_elem)
        
        # Arcs extrahieren
        arcs = self._extract_arcs(net_elem)
        
        # Initial Marking
        initial_marking = {p.id: p.initial_marking for p in places if p.initial_marking > 0}
        
        return PetriNet(
            id=net_id,
            name=name,
            net_type=net_type,
            places=places,
            transitions=transitions,
            arcs=arcs,
            initial_marking=initial_marking
        )

    def _extract_places(self, net_elem: ET.Element) -> List[Place]:
        """Extrahiert alle Places."""
        places = []
        
        for place_elem in net_elem.findall(".//pnml:place", self.namespaces):
            place_id = self.get_attribute(place_elem, "id", f"p{len(places)}")
            
            # Name
            name_elem = place_elem.find(".//pnml:name/pnml:text", self.namespaces)
            name = self.get_text(name_elem) if name_elem is not None else place_id
            
            # Initial Marking
            marking_elem = place_elem.find(".//pnml:initialMarking/pnml:text", self.namespaces)
            initial_marking = int(self.get_text(marking_elem, "0"))
            
            # Position (optional)
            graphics = place_elem.find(".//pnml:graphics/pnml:position", self.namespaces)
            position = None
            if graphics is not None:
                x = float(self.get_attribute(graphics, "x", 0))
                y = float(self.get_attribute(graphics, "y", 0))
                position = (x, y)
            
            places.append(Place(
                id=place_id,
                name=name,
                initial_marking=initial_marking,
                position=position
            ))
        
        return places

    def _extract_transitions(self, net_elem: ET.Element) -> List[Transition]:
        """Extrahiert alle Transitions."""
        transitions = []
        
        for trans_elem in net_elem.findall(".//pnml:transition", self.namespaces):
            trans_id = self.get_attribute(trans_elem, "id", f"t{len(transitions)}")
            
            # Name
            name_elem = trans_elem.find(".//pnml:name/pnml:text", self.namespaces)
            name = self.get_text(name_elem) if name_elem is not None else trans_id
            
            # Position
            graphics = trans_elem.find(".//pnml:graphics/pnml:position", self.namespaces)
            position = None
            if graphics is not None:
                x = float(self.get_attribute(graphics, "x", 0))
                y = float(self.get_attribute(graphics, "y", 0))
                position = (x, y)
            
            transitions.append(Transition(
                id=trans_id,
                name=name,
                position=position
            ))
        
        return transitions

    def _extract_arcs(self, net_elem: ET.Element) -> List[Arc]:
        """Extrahiert alle Arcs."""
        arcs = []
        
        for arc_elem in net_elem.findall(".//pnml:arc", self.namespaces):
            arc_id = self.get_attribute(arc_elem, "id", f"a{len(arcs)}")
            source = self.get_attribute(arc_elem, "source")
            target = self.get_attribute(arc_elem, "target")
            
            if not source or not target:
                logger.warning(f"Arc {arc_id} hat keine Source/Target")
                continue
            
            # Weight (Inscription)
            weight_elem = arc_elem.find(".//pnml:inscription/pnml:text", self.namespaces)
            weight = int(self.get_text(weight_elem, "1"))
            
            arcs.append(Arc(
                id=arc_id,
                source=source,
                target=target,
                weight=weight
            ))
        
        return arcs

    # ========================================================================
    # Conversion Helpers
    # ========================================================================

    def _place_to_dict(self, place: Place) -> Dict[str, Any]:
        """Konvertiert Place zu Dictionary."""
        return {
            "id": place.id,
            "name": place.name,
            "initial_marking": place.initial_marking,
            "capacity": place.capacity,
            "position": place.position,
        }

    def _transition_to_dict(self, transition: Transition) -> Dict[str, Any]:
        """Konvertiert Transition zu Dictionary."""
        return {
            "id": transition.id,
            "name": transition.name,
            "guard": transition.guard,
            "priority": transition.priority,
            "timed": transition.timed,
            "delay": transition.delay,
            "position": transition.position,
        }

    def _arc_to_dict(self, arc: Arc) -> Dict[str, Any]:
        """Konvertiert Arc zu Dictionary."""
        return {
            "id": arc.id,
            "source": arc.source,
            "target": arc.target,
            "weight": arc.weight,
            "inscription": arc.inscription,
            "type": arc.arc_type,
        }


# ============================================================================
# Factory Function
# ============================================================================

def get_petrinet_parser() -> PetriNetParser:
    """Factory für PetriNetParser."""
    return PetriNetParser()
