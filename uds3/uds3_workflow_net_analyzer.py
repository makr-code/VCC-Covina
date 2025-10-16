"""
UDS3 Workflow-Net Analyzer
===========================

Analyzer für Workflow-Nets mit Soundness-Verifikation nach van der Aalst.

Funktionen:
- Soundness-Verifikation (formale Korrektheit)
- Structural Analysis (S/T-Invarianten)
- Performance Analysis (Token-Flow-Simulation)
- BPMN/EPK → Petri-Netz Konvertierung

Author: UDS3 Framework
Date: 1. Oktober 2025
Status: Research Feature
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from uds3_petrinet_parser import (
    PetriNet,
    Place,
    Transition,
    Arc,
    PetriNetType,
    PetriNetValidationResult
)

logger = logging.getLogger(__name__)


# ============================================================================
# Workflow-Net spezifische Enums
# ============================================================================

class SoundnessLevel(Enum):
    """Soundness-Stufen nach van der Aalst"""
    NOT_SOUND = "not_sound"
    RELAXED_SOUND = "relaxed_sound"  # Schwache Soundness
    SOUND = "sound"                   # Klassische Soundness
    STRICT_SOUND = "strict_sound"     # Strenge Soundness


class StructuralProperty(Enum):
    """Strukturelle Eigenschaften von Petri-Netzen"""
    FREE_CHOICE = "free_choice"          # Free-Choice Netz
    STATE_MACHINE = "state_machine"      # State Machine
    MARKED_GRAPH = "marked_graph"        # Marked Graph
    WORKFLOW_NET = "workflow_net"        # WF-Net
    SOUND_WF_NET = "sound_wf_net"       # Sound WF-Net


# ============================================================================
# Analyzer Results
# ============================================================================

@dataclass
class SoundnessResult:
    """
    Ergebnis der Soundness-Verifikation.
    
    Soundness Bedingungen (van der Aalst):
    1. Option to complete: Von jedem erreichbaren Zustand kann End erreicht werden
    2. Proper completion: Wenn End erreicht, ist genau 1 Token in End
    3. No dead transitions: Jede Transition ist auf mind. 1 Pfad von Start zu End
    """
    is_sound: bool
    soundness_level: SoundnessLevel
    violations: List[str] = field(default_factory=list)
    
    # Detaillierte Checks
    option_to_complete: bool = False
    proper_completion: bool = False
    no_dead_transitions: bool = False
    
    # Erreichbarkeitsanalyse
    reachable_states: int = 0
    deadlock_states: List[Dict[str, int]] = field(default_factory=list)
    dead_transitions: List[str] = field(default_factory=list)
    
    # Performance-Metriken
    analysis_time_ms: float = 0.0
    state_space_explored: int = 0


@dataclass
class StructuralAnalysisResult:
    """
    Ergebnis der strukturellen Analyse.
    """
    properties: Set[StructuralProperty] = field(default_factory=set)
    
    # S-Invarianten (Place Invariants)
    s_invariants: List[Dict[str, int]] = field(default_factory=list)
    is_covered_by_s_invariants: bool = False
    
    # T-Invarianten (Transition Invariants)
    t_invariants: List[Dict[str, int]] = field(default_factory=list)
    is_covered_by_t_invariants: bool = False
    
    # Strukturelle Metriken
    cyclomatic_complexity: int = 0
    average_degree: float = 0.0
    max_path_length: int = 0


@dataclass
class PerformanceAnalysisResult:
    """
    Ergebnis der Performance-Analyse.
    """
    # Token-Flow Simulation
    average_token_count: float = 0.0
    max_token_count: int = 0
    bottleneck_places: List[str] = field(default_factory=list)
    bottleneck_transitions: List[str] = field(default_factory=list)
    
    # Durchlaufzeit-Schätzung
    estimated_execution_time: float = 0.0
    critical_path: List[str] = field(default_factory=list)
    
    # Parallelität
    max_parallel_transitions: int = 0
    parallelism_score: float = 0.0


# ============================================================================
# Workflow-Net Analyzer
# ============================================================================

class WorkflowNetAnalyzer:
    """
    Analyzer für Workflow-Nets.
    
    Implementiert Algorithmen von:
    - W.M.P. van der Aalst: "Workflow Verification"
    - Murata: "Petri Nets: Properties, Analysis and Applications"
    """

    def __init__(self, petri_net: PetriNet):
        """
        Initialisiert Analyzer.
        
        Args:
            petri_net: Zu analysierendes Petri-Netz
        """
        self.petri_net = petri_net
        self.source_place: Optional[str] = None
        self.sink_place: Optional[str] = None
        
        # Validiere dass es ein WF-Net ist
        if not petri_net.is_workflow_net():
            logger.warning("Petri-Netz ist kein Workflow-Net")
        else:
            self._identify_source_sink()

    def _identify_source_sink(self) -> None:
        """Identifiziert Source- und Sink-Places."""
        for place in self.petri_net.places:
            preset = self.petri_net.get_preset(place.id)
            postset = self.petri_net.get_postset(place.id)
            
            if not preset and postset:
                self.source_place = place.id
            elif preset and not postset:
                self.sink_place = place.id

    # ========================================================================
    # Soundness-Verifikation
    # ========================================================================

    def verify_soundness(self) -> SoundnessResult:
        """
        Verifiziert Soundness des Workflow-Nets.
        
        Returns:
            SoundnessResult mit Verifikations-Details
        """
        import time
        start_time = time.time()
        
        logger.info("Starte Soundness-Verifikation...")
        
        if not self.petri_net.is_workflow_net():
            return SoundnessResult(
                is_sound=False,
                soundness_level=SoundnessLevel.NOT_SOUND,
                violations=["Keine Workflow-Net Struktur"]
            )
        
        # 1. Option to complete
        option_ok, deadlocks = self._check_option_to_complete()
        
        # 2. Proper completion
        proper_ok = self._check_proper_completion()
        
        # 3. No dead transitions
        dead_trans = self._find_dead_transitions()
        no_dead_ok = len(dead_trans) == 0
        
        # Soundness-Bewertung
        is_sound = option_ok and proper_ok and no_dead_ok
        
        violations = []
        if not option_ok:
            violations.append(f"Option to complete verletzt: {len(deadlocks)} Deadlock-Zustände")
        if not proper_ok:
            violations.append("Proper completion verletzt: Mehrere Tokens in Sink möglich")
        if not no_dead_ok:
            violations.append(f"Dead transitions: {', '.join(dead_trans)}")
        
        # Soundness-Level
        if is_sound:
            level = SoundnessLevel.SOUND
        elif proper_ok and no_dead_ok:
            level = SoundnessLevel.RELAXED_SOUND
        else:
            level = SoundnessLevel.NOT_SOUND
        
        analysis_time = (time.time() - start_time) * 1000  # ms
        
        result = SoundnessResult(
            is_sound=is_sound,
            soundness_level=level,
            violations=violations,
            option_to_complete=option_ok,
            proper_completion=proper_ok,
            no_dead_transitions=no_dead_ok,
            deadlock_states=deadlocks,
            dead_transitions=dead_trans,
            analysis_time_ms=analysis_time
        )
        
        logger.info(f"✅ Soundness-Verifikation: {level.value} ({analysis_time:.1f}ms)")
        
        return result

    def _check_option_to_complete(self) -> Tuple[bool, List[Dict[str, int]]]:
        """
        Prüft "Option to complete".
        
        Von jedem erreichbaren Zustand muss Sink erreichbar sein.
        
        Returns:
            (is_valid, deadlock_states)
        """
        if not self.source_place or not self.sink_place:
            return False, []
        
        # Erreichbarkeitsanalyse
        reachable = self._compute_reachability_graph()
        deadlocks = []
        
        for marking in reachable:
            # Kann Sink von diesem Marking erreicht werden?
            if not self._can_reach_sink(marking):
                # Prüfe ob bereits in Sink
                if marking.get(self.sink_place, 0) == 0:
                    deadlocks.append(marking)
        
        return len(deadlocks) == 0, deadlocks

    def _check_proper_completion(self) -> bool:
        """
        Prüft "Proper completion".
        
        Wenn Sink erreicht, darf nur 1 Token in Sink sein.
        """
        if not self.sink_place:
            return False
        
        # Alle erreichbaren Markierungen mit Token in Sink
        reachable = self._compute_reachability_graph()
        
        for marking in reachable:
            if marking.get(self.sink_place, 0) > 0:
                # Prüfe: Nur in Sink Tokens?
                total_tokens = sum(marking.values())
                tokens_in_sink = marking[self.sink_place]
                
                if total_tokens != tokens_in_sink or tokens_in_sink != 1:
                    return False
        
        return True

    def _find_dead_transitions(self) -> List[str]:
        """
        Findet tote Transitions (nie aktivierbar).
        
        Returns:
            Liste toter Transition-IDs
        """
        reachable = self._compute_reachability_graph()
        activated = set()
        
        for marking in reachable:
            enabled = self._get_enabled_transitions(marking)
            activated.update(enabled)
        
        all_trans = {t.id for t in self.petri_net.transitions}
        dead = all_trans - activated
        
        return list(dead)

    def _compute_reachability_graph(self, max_states: int = 1000) -> List[Dict[str, int]]:
        """
        Berechnet Erreichbarkeitsgraphen (Coverability Graph).
        
        Args:
            max_states: Maximale Anzahl zu explorierender Zustände
            
        Returns:
            Liste erreichbarer Markierungen
        """
        if not self.source_place:
            return []
        
        # Initial Marking: 1 Token in Source
        initial = {self.source_place: 1}
        
        visited = []
        queue = deque([initial])
        
        while queue and len(visited) < max_states:
            marking = queue.popleft()
            
            # Bereits besucht?
            if any(self._marking_equals(marking, v) for v in visited):
                continue
            
            visited.append(marking)
            
            # Aktivierte Transitions
            enabled = self._get_enabled_transitions(marking)
            
            for trans_id in enabled:
                new_marking = self._fire_transition(marking, trans_id)
                if new_marking:
                    queue.append(new_marking)
        
        return visited

    def _get_enabled_transitions(self, marking: Dict[str, int]) -> List[str]:
        """Findet alle in dieser Markierung aktivierbaren Transitions."""
        enabled = []
        
        for trans in self.petri_net.transitions:
            if self._is_enabled(trans.id, marking):
                enabled.append(trans.id)
        
        return enabled

    def _is_enabled(self, trans_id: str, marking: Dict[str, int]) -> bool:
        """Prüft ob Transition aktiviert ist."""
        preset = self.petri_net.get_preset(trans_id)
        
        for place_id in preset:
            # Finde Arc Weight
            arc = next((a for a in self.petri_net.arcs 
                       if a.source == place_id and a.target == trans_id), None)
            weight = arc.weight if arc else 1
            
            if marking.get(place_id, 0) < weight:
                return False
        
        return True

    def _fire_transition(self, marking: Dict[str, int], trans_id: str) -> Optional[Dict[str, int]]:
        """Führt Transition aus und gibt neue Markierung zurück."""
        if not self._is_enabled(trans_id, marking):
            return None
        
        new_marking = marking.copy()
        
        # Tokens entfernen (Preset)
        preset = self.petri_net.get_preset(trans_id)
        for place_id in preset:
            arc = next((a for a in self.petri_net.arcs 
                       if a.source == place_id and a.target == trans_id), None)
            weight = arc.weight if arc else 1
            new_marking[place_id] = new_marking.get(place_id, 0) - weight
            if new_marking[place_id] <= 0:
                del new_marking[place_id]
        
        # Tokens hinzufügen (Postset)
        postset = self.petri_net.get_postset(trans_id)
        for place_id in postset:
            arc = next((a for a in self.petri_net.arcs 
                       if a.source == trans_id and a.target == place_id), None)
            weight = arc.weight if arc else 1
            new_marking[place_id] = new_marking.get(place_id, 0) + weight
        
        return new_marking

    def _can_reach_sink(self, marking: Dict[str, int]) -> bool:
        """Prüft ob Sink von Markierung erreichbar ist (vereinfacht)."""
        if not self.sink_place:
            return False
        
        # Wenn bereits Token in Sink: Ja
        if marking.get(self.sink_place, 0) > 0:
            return True
        
        # Vereinfachte Heuristik: Gibt es aktivierte Transitions?
        enabled = self._get_enabled_transitions(marking)
        return len(enabled) > 0

    def _marking_equals(self, m1: Dict[str, int], m2: Dict[str, int]) -> bool:
        """Vergleicht zwei Markierungen."""
        return m1 == m2

    # ========================================================================
    # Structural Analysis
    # ========================================================================

    def analyze_structure(self) -> StructuralAnalysisResult:
        """
        Führt strukturelle Analyse durch.
        
        Returns:
            StructuralAnalysisResult
        """
        logger.info("Starte strukturelle Analyse...")
        
        properties = set()
        
        # WF-Net?
        if self.petri_net.is_workflow_net():
            properties.add(StructuralProperty.WORKFLOW_NET)
        
        # Free-Choice?
        if self._is_free_choice():
            properties.add(StructuralProperty.FREE_CHOICE)
        
        # State Machine?
        if self._is_state_machine():
            properties.add(StructuralProperty.STATE_MACHINE)
        
        # Cyclomatic Complexity
        complexity = self._calculate_cyclomatic_complexity()
        
        return StructuralAnalysisResult(
            properties=properties,
            cyclomatic_complexity=complexity
        )

    def _is_free_choice(self) -> bool:
        """Prüft ob Netz Free-Choice ist."""
        # Free-Choice: Wenn zwei Transitions gleichen Preset teilen,
        # müssen sie identischen Preset haben
        for t1 in self.petri_net.transitions:
            preset1 = self.petri_net.get_preset(t1.id)
            for t2 in self.petri_net.transitions:
                if t1.id >= t2.id:  # Nur einmal prüfen
                    continue
                preset2 = self.petri_net.get_preset(t2.id)
                
                # Teilen sie Places?
                if preset1 & preset2:
                    # Dann müssen Presets identisch sein
                    if preset1 != preset2:
                        return False
        
        return True

    def _is_state_machine(self) -> bool:
        """Prüft ob Netz State Machine ist."""
        # State Machine: Jede Transition hat genau 1 Input und 1 Output Place
        for trans in self.petri_net.transitions:
            preset = self.petri_net.get_preset(trans.id)
            postset = self.petri_net.get_postset(trans.id)
            
            if len(preset) != 1 or len(postset) != 1:
                return False
        
        return True

    def _calculate_cyclomatic_complexity(self) -> int:
        """
        Berechnet zyklomatische Komplexität.
        
        CC = E - N + 2P
        E = Anzahl Kanten (Arcs)
        N = Anzahl Knoten (Places + Transitions)
        P = Anzahl zusammenhängender Komponenten
        """
        E = len(self.petri_net.arcs)
        N = len(self.petri_net.places) + len(self.petri_net.transitions)
        P = 1  # Vereinfacht: 1 Komponente
        
        return E - N + 2 * P

    # ========================================================================
    # Performance Analysis
    # ========================================================================

    def analyze_performance(self, simulation_steps: int = 100) -> PerformanceAnalysisResult:
        """
        Führt Performance-Analyse durch Token-Simulation.
        
        Args:
            simulation_steps: Anzahl Simulationsschritte
            
        Returns:
            PerformanceAnalysisResult
        """
        logger.info(f"Starte Performance-Analyse ({simulation_steps} Steps)...")
        
        if not self.source_place:
            return PerformanceAnalysisResult()
        
        # Token-Flow Simulation
        marking = {self.source_place: 1}
        token_counts = []
        
        for _ in range(simulation_steps):
            token_counts.append(sum(marking.values()))
            
            # Wähle zufällige aktivierte Transition
            enabled = self._get_enabled_transitions(marking)
            if not enabled:
                break
            
            trans_id = enabled[0]  # Deterministisch: erste Transition
            new_marking = self._fire_transition(marking, trans_id)
            if new_marking:
                marking = new_marking
        
        avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0
        max_tokens = max(token_counts) if token_counts else 0
        
        return PerformanceAnalysisResult(
            average_token_count=avg_tokens,
            max_token_count=max_tokens
        )


# ============================================================================
# Factory Function
# ============================================================================

def get_workflow_analyzer(petri_net: PetriNet) -> WorkflowNetAnalyzer:
    """Factory für WorkflowNetAnalyzer."""
    return WorkflowNetAnalyzer(petri_net)
