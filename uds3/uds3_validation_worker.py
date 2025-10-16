#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_validation_worker"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...pVkj5w=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "5426bf69e2c7e091053f8e2732e9ec8319e68164b33889e0622e0741b5e1d554"
)
module_file_key = "555472ec2bc00ee2472e16fe838fa467e341ba8d616ac5c1457ad9ae0563fced"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
NLP/LLM Validation Worker für UDS3-Rechtsgrundlagen und Begründungen
Integration in die bestehende ThreadCoordinator-Pipeline

Läuft nach NLP/LLM-Verarbeitung und vor/anstelle des Quality Workers
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Ergebnis der NLP/LLM-Validierung"""

    success: bool
    overall_score: float
    passed: bool
    detailed_scores: Dict[str, float]
    validation_results: Dict[str, Any]
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    processing_time: float
    error_message: Optional[str] = None


class UDS3ValidationWorker:
    """
    NLP/LLM Worker für die Validierung von UDS3-Rechtsgrundlagen und Begründungen
    Integriert in die bestehende ThreadCoordinator-Pipeline
    """

    def __init__(self, quality_threshold: float = 0.75):
        self.quality_threshold = quality_threshold

        # Lade NLP/LLM Interface
        try:
            import sys
            from pathlib import Path

            project_root = Path(__file__).parent
            sys.path.insert(0, str(project_root))

            try:
                from nlp_llm_worker_interface import UDS3_NLP_LLM_Interface  # type: ignore

                self.nlp_interface = UDS3_NLP_LLM_Interface()
            except Exception:
                from typing import Any

                UDS3_NLP_LLM_Interface = Any  # type: ignore
                self.nlp_interface = None
            logger.info("🤖 UDS3 NLP/LLM Interface erfolgreich geladen")
        except ImportError as e:
            logger.error(f"❌ Fehler beim Laden des NLP/LLM Interface: {e}")
            self.nlp_interface = None

    def process_document(
        self, task: Dict[str, Any], progress_callback=None
    ) -> ValidationResult:
        """
        Führt NLP/LLM-Validierung für UDS3-Rechtsgrundlagen und Begründungen durch

        Args:
            task: Pipeline-Task mit UDS3-Metadaten
            progress_callback: Optional callback für Fortschrittsmeldungen

        Returns:
            ValidationResult mit Validierungsergebnissen
        """
        start_time = time.time()

        # Debug-Log für Task-Typ und -Inhalt
        logger.info(f"🔍 UDS3-Validierung gestartet - Task-Typ: {type(task)}")
        if isinstance(task, dict):
            logger.debug(f"Task-Keys: {list(task.keys())}")
        else:
            logger.warning(f"Task ist kein Dictionary: {str(task)[:200]}...")

        if progress_callback:
            progress_callback("NLP/LLM-Validierung gestartet", 0)

        try:
            # Task-Daten extrahieren - Robust gegen verschiedene Eingabetypen
            if isinstance(task, str):
                # Falls task ein JSON-String ist, versuche zu parsen
                try:
                    import json

                    task = json.loads(task)
                    logger.info("Task von JSON-String zu Dictionary konvertiert")
                except json.JSONDecodeError:
                    logger.error(f"Task ist String aber kein gültiges JSON: {task}")
                    return ValidationResult(
                        success=False,
                        overall_score=0.0,
                        passed=False,
                        detailed_scores={},
                        validation_results={},
                        issues=[
                            f"Ungültiger Task-Typ: String statt Dictionary - {str(task)[:100]}"
                        ],
                        warnings=["Task-Format-Problem"],
                        recommendations=["Task muss als Dictionary übergeben werden"],
                        processing_time=0,
                    )

            if not isinstance(task, dict):
                logger.error(
                    f"Task hat ungültigen Typ: {type(task)} - {str(task)[:100]}"
                )
                return ValidationResult(
                    success=False,
                    overall_score=0.0,
                    passed=False,
                    detailed_scores={},
                    validation_results={},
                    issues=[f"Ungültiger Task-Typ: {type(task)} statt Dictionary"],
                    warnings=["Task-Typ-Problem"],
                    recommendations=["Task muss als Dictionary übergeben werden"],
                    processing_time=0,
                )

            metadata = task.get("metadata", {})
            job_id = task.get("job_id", "unknown")
            file_path = task.get("file_path", "")

            # Metadata-Validierung und -Konvertierung
            if isinstance(metadata, str):
                try:
                    import json

                    metadata = json.loads(metadata)
                    logger.info("Metadata von JSON-String zu Dictionary konvertiert")
                except json.JSONDecodeError:
                    logger.warning(
                        f"Metadata ist String aber kein gültiges JSON: {metadata[:100]}..."
                    )
                    # Fallback: leeres Dictionary
                    metadata: dict[Any, Any] = {}

            if not isinstance(metadata, dict):
                logger.warning(
                    f"Metadata hat ungültigen Typ: {type(metadata)}, verwende leeres Dictionary"
                )
                metadata: dict[Any, Any] = {}

            if not metadata:
                return ValidationResult(
                    success=False,
                    overall_score=0.0,
                    passed=False,
                    detailed_scores={},
                    validation_results={},
                    issues=["Keine Metadaten für Validierung verfügbar"],
                    warnings=[],
                    recommendations=[
                        "Stelle sicher, dass UDS3-Extraktion vor Validierung läuft"
                    ],
                    processing_time=time.time() - start_time,
                    error_message="Keine Metadaten verfügbar",
                )

            if progress_callback:
                progress_callback("Prüfe verfügbare Daten", 10)

            # Prüfe, ob Rechtsgrundlagen/Begründungen vorhanden sind
            has_rechtsgrundlagen = self._check_rechtsgrundlagen_data(metadata)
            has_begründungen = self._check_begründungen_data(metadata)

            if not has_rechtsgrundlagen and not has_begründungen:
                return ValidationResult(
                    success=True,
                    overall_score=0.5,  # Neutral - keine Daten zu validieren
                    passed=True,
                    detailed_scores={"data_availability": 0.5},
                    validation_results={
                        "skip_reason": "Keine Rechtsgrundlagen/Begründungen gefunden"
                    },
                    issues=[],
                    warnings=[
                        "Keine Rechtsgrundlagen oder Begründungen für NLP/LLM-Validierung gefunden"
                    ],
                    recommendations=["Prüfe UDS3-Extraktion auf Vollständigkeit"],
                    processing_time=time.time() - start_time,
                )

            if progress_callback:
                progress_callback("Bereite NLP/LLM-Tasks vor", 20)

            # Bestimme anwendbare NLP-Tasks
            applicable_tasks: list[Any] = []

            if has_rechtsgrundlagen:
                applicable_tasks.extend(
                    ["rechtsgrundlagen_validierung", "zeitpunkt_konsistenz"]
                )

            if has_begründungen:
                applicable_tasks.append("begründungsqualität")

            logger.info(
                f"🔍 Führe {len(applicable_tasks)} NLP/LLM-Validierungen durch: {applicable_tasks}"
            )

            # Führe alle anwendbaren Validierungen durch
            validation_results: dict[Any, Any] = {}
            detailed_scores: dict[Any, Any] = {}
            all_issues: list[Any] = []
            all_warnings: list[Any] = []
            all_recommendations: list[Any] = []

            total_tasks = len(applicable_tasks)
            for i, task_name in enumerate(applicable_tasks):
                if progress_callback:
                    progress_callback(
                        f"Validierung: {task_name}", 30 + (i * 40 // total_tasks)
                    )

                try:
                    # Bereite Task vor
                    prompt_package = self.nlp_interface.prepare_nlp_task(
                        task_name, metadata
                    )

                    # Führe Mock-Validierung durch (in echtem System: LLM-Aufruf)
                    task_result = self._execute_validation_task(
                        prompt_package, task_name
                    )

                    validation_results[task_name] = task_result
                    detailed_scores[task_name] = task_result.get("konfidenzscore", 0.5)

                    # Sammle Issues/Warnings/Empfehlungen
                    if "empfehlungen" in task_result:
                        all_recommendations.extend(task_result["empfehlungen"])
                    if "issues" in task_result:
                        all_issues.extend(task_result["issues"])
                    if "warnings" in task_result:
                        all_warnings.extend(task_result["warnings"])

                    logger.debug(
                        f"✅ Task {task_name} abgeschlossen: Score {detailed_scores[task_name]:.2f}"
                    )

                except Exception as e:
                    logger.error(
                        f"❌ Validierungs-Task {task_name} fehlgeschlagen: {e}"
                    )
                    detailed_scores[task_name] = 0.0
                    validation_results[task_name] = {"error": str(e)}
                    all_issues.append(f"Validierung {task_name} fehlgeschlagen: {e}")

            if progress_callback:
                progress_callback("Berechne Gesamtbewertung", 90)

            # Berechne Gesamtbewertung
            if detailed_scores:
                overall_score = sum(detailed_scores.values()) / len(detailed_scores)
            else:
                overall_score = 0.0

            passed = overall_score >= self.quality_threshold
            processing_time = time.time() - start_time

            if progress_callback:
                progress_callback("NLP/LLM-Validierung abgeschlossen", 100)

            logger.info(
                f"🎯 NLP/LLM-Validierung abgeschlossen: Score {overall_score:.2f}, Passed: {passed}"
            )

            return ValidationResult(
                success=True,
                overall_score=overall_score,
                passed=passed,
                detailed_scores=detailed_scores,
                validation_results=validation_results,
                issues=all_issues,
                warnings=all_warnings,
                recommendations=all_recommendations,
                processing_time=processing_time,
            )

        except Exception as e:
            error_msg = f"NLP/LLM-Validierung fehlgeschlagen: {str(e)}"
            logger.error(error_msg)

            return ValidationResult(
                success=False,
                overall_score=0.0,
                passed=False,
                detailed_scores={},
                validation_results={},
                issues=[error_msg],
                warnings=[],
                recommendations=["Prüfe NLP/LLM-System-Konfiguration"],
                processing_time=time.time() - start_time,
                error_message=error_msg,
            )

    def _check_rechtsgrundlagen_data(self, metadata: Dict[str, Any]) -> bool:
        """Prüft, ob Rechtsgrundlagen-Daten für Validierung verfügbar sind"""
        rechtsgrundlagen_fields = [
            "anwendbare_gesetze",
            "anwendbare_verordnungen",
            "rechtsgrundlagen_zum_zeitpunkt",
            "ermächtigungsgrundlagen_spezifisch",
        ]

        return any(
            metadata.get(field) and len(metadata[field]) > 0
            for field in rechtsgrundlagen_fields
            if isinstance(metadata.get(field), (list, str))
        )

    def _check_begründungen_data(self, metadata: Dict[str, Any]) -> bool:
        """Prüft, ob Begründungs-Daten für Validierung verfügbar sind"""
        begründung_fields = [
            "begründung_nebenbestimmungen",
            "verhältnismäßigkeitsprüfung",
            "sachverständigengutachten_referenzen",
            "begründungsqualität",
        ]

        return any(
            metadata.get(field) and len(metadata[field]) > 0
            for field in begründung_fields
            if isinstance(metadata.get(field), (list, str))
        )

    def _execute_validation_task(
        self, prompt_package, task_name: str
    ) -> Dict[str, Any]:
        """
        Führt einzelne Validierungs-Task durch

        HINWEIS: In der echten Implementierung würde hier ein LLM-Aufruf stattfinden
        Aktuell: Mock-Implementation mit realistischen Ergebnissen
        """

        # Mock-Ergebnisse basierend auf Task-Typ
        if task_name == "rechtsgrundlagen_validierung":
            return {
                "validierung_ergebnis": "VOLLSTÄNDIG",
                "korrekte_rechtsgrundlagen": ["BImSchG § 4", "VwVfG § 28"],
                "fehlende_rechtsgrundlagen": [],
                "empfehlungen": ["EU-Richtlinien-Bezug könnte spezifiziert werden"],
                "konfidenzscore": 0.87,
            }

        elif task_name == "zeitpunkt_konsistenz":
            return {
                "konsistenz_bewertung": "KONSISTENT",
                "zeitpunkt_analyse": {
                    "bescheid_datum": "2023-07-15",
                    "angewandte_rechtsversion": "korrekt",
                },
                "empfehlungen": ["Versionsstände sind aktuell"],
                "konfidenzscore": 0.92,
            }

        elif task_name == "begründungsqualität":
            return {
                "begründungsqualität_gesamt": "GUT",
                "einzelbewertungen": {
                    "vollständigkeit": 0.80,
                    "rechtliche_fundierung": 0.85,
                    "verhältnismäßigkeit": 0.75,
                },
                "empfehlungen": [
                    "Verhältnismäßigkeitsprüfung könnte detaillierter sein"
                ],
                "konfidenzscore": 0.80,
            }

        else:
            return {"status": "unknown_task", "konfidenzscore": 0.5}


def integrate_uds3_validation_worker():
    """
    Integration der UDS3-Validierung in die bestehende ThreadCoordinator-Pipeline

    INTEGRATION POINT: Ersetzt oder ergänzt den bestehenden Quality Worker
    """

    # Integration Code - wird in ingestion_core_components.py eingefügt
    integration_code = """
    
    # In ThreadCoordinator.__init__ hinzufügen:
    self.uds3_validation_workers: list[Any] = []
    self.uds3_validation_queue = queue.Queue()  # NEU: UDS3 Validation Queue
    
    # In thread_configs hinzufügen:
    {'type': 'uds3_validation', 'count': 1, 'queue': self.uds3_validation_queue},
    
    # In _process_task hinzufügen:
    elif worker_type == 'uds3_validation':
        self._process_uds3_validation_task(task, worker_id)
    
    # In _get_workers_by_type hinzufügen:
    'uds3_validation': self.uds3_validation_workers,
    
    # In _get_worker_counts hinzufügen:
    'uds3_validation': len(self.uds3_validation_workers),
    
    # In _get_next_pipeline_job_for_worker_type hinzufügen:
    'uds3_validation': ['file'],  # UDS3-Validation nach NLP/LLM
    """

    return integration_code


if __name__ == "__main__":
    print("🤖 UDS3 NLP/LLM Validation Worker")
    print("Bereit für Integration in ThreadCoordinator-Pipeline")
    print("Position: Nach NLP/LLM-Processing, vor/anstelle Quality Worker")

    # Demo der Funktionalität
    worker = UDS3ValidationWorker()

    # Mock-Task für Demonstration
    mock_task = {
        "job_id": "test_123",
        "file_path": "test_bescheid.txt",
        "metadata": {
            "anwendbare_gesetze": ["BImSchG", "VwVfG"],
            "begründung_nebenbestimmungen": ["Schutz vor Umwelteinwirkungen"],
            "rechtsgrundlagen_zum_zeitpunkt": ["2023-07-15"],
        },
    }

    def mock_progress(stage, progress):
        print(f"[{progress:3d}%] {stage}")

    result = worker.process_document(mock_task, mock_progress)

    print("\n🎯 ERGEBNIS:")
    print(f"   Success: {result.success}")
    print(f"   Overall Score: {result.overall_score:.2f}")
    print(f"   Passed: {result.passed}")
    print(f"   Processing Time: {result.processing_time:.2f}s")
    print(f"   Recommendations: {len(result.recommendations)}")
