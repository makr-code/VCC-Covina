"""
Intelligent Workers für das Covina Automation Framework
======================================================

Dieses Modul enthält spezialisierte Worker-Implementierungen für:
- Golden Dataset Management (Auto-Expansion, Quality Assessment)
- Gap Detection & Resolution (Self-Healing, Auto-Fix)
- Quality Optimization (Threshold Adjustment, Performance Monitoring)
- Process Mining Integration (Conformance Monitoring, Process Optimization)
- Graph Linking (Post-Ingestion Citation & Topic Linking)

Worker sind autonome Komponenten, die spezielle Aufgaben mit Confidence-basierter
Entscheidungsfindung durchführen und das Human Review System nutzen.
"""

from .golden_dataset_worker import GoldenDatasetWorker
from .gap_detection_worker import GapDetectionWorker
from .quality_optimization_worker import QualityOptimizationWorker
from .process_mining_worker import ProcessMiningWorker
from .graph_linking_worker import GraphLinkingWorker

__all__ = [
    "GoldenDatasetWorker",
    "GapDetectionWorker",
    "QualityOptimizationWorker",
    "ProcessMiningWorker",
    "GraphLinkingWorker"
]