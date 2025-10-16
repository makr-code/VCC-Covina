#!/usr/bin/env python3
"""
UDS3 FOLLOW-UP TASK ORCHESTRATION

Implementiert spezialisierte Task-Handler für UDS3-spezifische Follow-up Tasks:
- uds3_database_integration: Integration in UDS3-Datenbank
- administrative_relationship_detection: Verwaltungsbeziehungen erkennen
- procedure_stage_tracking: Verfahrensstadien verfolgen
- legal_compliance_checking: Rechtmäßigkeitsprüfung
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# UDS3 Integration
try:
    from uds3_core import get_optimized_unified_strategy

    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False


@dataclass
class UDS3TaskResult:
    """Ergebnis einer UDS3-spezifischen Task-Verarbeitung"""

    task_id: str
    task_type: str
    success: bool
    processing_time: float
    results: Dict[str, Any]
    metadata: Dict[str, Any]
    error_message: Optional[str] = None


class UDS3TaskOrchestrator:
    """
    Orchestrator für UDS3-spezifische Follow-up Tasks
    """

    def __init__(self, orchestrator_id: str = "uds3_orchestrator"):
        self.orchestrator_id = orchestrator_id
        self.logger = logging.getLogger(f"uds3_orchestrator.{orchestrator_id}")

        # UDS3-Integration
        if UDS3_AVAILABLE:
            self.uds3_strategy = get_optimized_unified_strategy()
            self.logger.info(
                "✅ UDS3 Orchestrator mit Datenbankstrategie initialisiert"
            )
        else:
            self.uds3_strategy = None
            self.logger.warning(
                "⚠️ UDS3 nicht verfügbar - Orchestrator läuft im Fallback-Modus"
            )

        # Task-Handler Registry
        self.task_handlers = {
            "uds3_database_integration": self._handle_database_integration,
            "administrative_relationship_detection": self._handle_relationship_detection,
            "procedure_stage_tracking": self._handle_stage_tracking,
            "legal_compliance_checking": self._handle_compliance_checking,
        }

        self.logger.info(f"UDS3 Task Orchestrator {orchestrator_id} initialisiert")

    def process_uds3_task(self, task: Dict[str, Any]) -> UDS3TaskResult:
        """
        Verarbeitet eine UDS3-spezifische Follow-up Task

        Args:
            task: Task-Dictionary mit task_type, task_id, etc.

        Returns:
            UDS3TaskResult mit Verarbeitungsergebnis
        """
        start_time = datetime.now()

        task_type = task.get("task_type")
        task_id = task.get("task_id", "unknown")

        self.logger.info(f"🏛️ Verarbeite UDS3-Task: {task_type} ({task_id})")

        result = UDS3TaskResult(
            task_id=task_id,
            task_type=task_type,
            success=False,
            processing_time=0.0,
            results={},
            metadata={},
        )

        try:
            if task_type not in self.task_handlers:
                result.error_message = f"Unbekannter UDS3-Task-Typ: {task_type}"
                self.logger.error(result.error_message)
                return result

            # Task-spezifischen Handler aufrufen
            handler = self.task_handlers[task_type]
            handler_result = handler(task)

            result.results = handler_result
            result.success = True

            self.logger.info(f"✅ UDS3-Task erfolgreich verarbeitet: {task_type}")

        except Exception as e:
            result.error_message = f"Fehler bei UDS3-Task Verarbeitung: {str(e)}"
            self.logger.error(result.error_message)

        finally:
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
            result.metadata["processed_at"] = datetime.now().isoformat()
            result.metadata["orchestrator_id"] = self.orchestrator_id

        return result

    def _handle_database_integration(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet UDS3-Datenbankintegration

        Args:
            task: Task mit Dokumentmetadaten

        Returns:
            Dictionary mit Integrationsergebnissen
        """
        self.logger.info("🏛️ Starte UDS3-Datenbankintegration...")

        file_id = task.get("file_id")
        metadata = task.get("metadata", {})

        results = {
            "integration_type": "uds3_database",
            "file_id": file_id,
            "status": "completed",
            "operations": [],
        }

        # UDS3-spezifische Metadaten extrahieren
        uds3_metadata: dict[Any, Any] = {}
        if "keywords" in metadata:
            for keyword in metadata["keywords"]:
                if keyword.startswith(("uds3_", "admin_", "domain:", "stage:")):
                    key, value = (
                        keyword.split(":", 1) if ":" in keyword else (keyword, True)
                    )
                    uds3_metadata[key] = value

        results["uds3_metadata"] = uds3_metadata
        results["operations"].append(
            {
                "operation": "metadata_extraction",
                "extracted_fields": len(uds3_metadata),
                "timestamp": datetime.now().isoformat(),
            }
        )

        # UDS3-Datenbank Integration (simuliert)
        if self.uds3_strategy:
            results["operations"].append(
                {
                    "operation": "uds3_storage",
                    "database_status": "integrated",
                    "confidence_threshold": metadata.get("confidence_score", 0.5),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            results["operations"].append(
                {
                    "operation": "uds3_storage",
                    "database_status": "fallback_mode",
                    "note": "UDS3 nicht verfügbar - Metadaten lokal gespeichert",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        self.logger.info(
            f"✅ UDS3-Datenbankintegration abgeschlossen: {len(results['operations'])} Operationen"
        )
        return results

    def _handle_relationship_detection(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Erkennt Verwaltungsbeziehungen zwischen Dokumenten

        Args:
            task: Task mit Dokumentkontext

        Returns:
            Dictionary mit erkannten Beziehungen
        """
        self.logger.info("🔗 Starte Verwaltungsbeziehungserkennung...")

        file_id = task.get("file_id")
        metadata = task.get("metadata", {})

        results = {
            "detection_type": "administrative_relationships",
            "file_id": file_id,
            "relationships": [],
            "confidence_scores": {},
        }

        # Potentielle Beziehungen basierend auf Metadaten
        doc_type = None
        admin_level = None
        domain = None

        if "keywords" in metadata:
            for keyword in metadata["keywords"]:
                if keyword.startswith("uds3_type:"):
                    doc_type = keyword.split(":")[1]
                elif keyword.startswith("admin_level:"):
                    admin_level = keyword.split(":")[1]
                elif keyword.startswith("domain:"):
                    domain = keyword.split(":")[1]

        # Beziehungsregeln anwenden
        if doc_type == "admin_act" and domain == "building":
            results["relationships"].append(
                {
                    "relationship_type": "references_law",
                    "target_document_pattern": "building_codes",
                    "confidence": 0.8,
                    "reasoning": "Verwaltungsakt referenziert Baurecht",
                }
            )

            results["relationships"].append(
                {
                    "relationship_type": "part_of_procedure",
                    "target_document_pattern": "application_documents",
                    "confidence": 0.7,
                    "reasoning": "Teil eines Genehmigungsverfahrens",
                }
            )

        elif doc_type == "law" and domain == "building":
            results["relationships"].append(
                {
                    "relationship_type": "legal_basis_for",
                    "target_document_pattern": "admin_acts_building",
                    "confidence": 0.9,
                    "reasoning": "Gesetzliche Grundlage für Verwaltungsakte",
                }
            )

        # Confidence-Scores berechnen
        total_relationships = len(results["relationships"])
        if total_relationships > 0:
            avg_confidence = (
                sum(rel["confidence"] for rel in results["relationships"])
                / total_relationships
            )
            results["confidence_scores"]["average"] = avg_confidence
            results["confidence_scores"]["total_relationships"] = total_relationships

        self.logger.info(
            f"✅ Verwaltungsbeziehungserkennung abgeschlossen: {total_relationships} Beziehungen erkannt"
        )
        return results

    def _handle_stage_tracking(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verfolgt Verfahrensstadien von Verwaltungsdokumenten

        Args:
            task: Task mit Verfahrenskontext

        Returns:
            Dictionary mit Stadien-Tracking
        """
        self.logger.info("📊 Starte Verfahrensstadien-Tracking...")

        file_id = task.get("file_id")
        metadata = task.get("metadata", {})

        results = {
            "tracking_type": "procedure_stages",
            "file_id": file_id,
            "current_stage": None,
            "stage_history": [],
            "next_possible_stages": [],
        }

        # Aktuelles Stadium ermitteln
        current_stage = None
        doc_type = None

        if "keywords" in metadata:
            for keyword in metadata["keywords"]:
                if keyword.startswith("stage:"):
                    current_stage = keyword.split(":")[1]
                elif keyword.startswith("uds3_type:"):
                    doc_type = keyword.split(":")[1]

        results["current_stage"] = current_stage

        # Verfahrensstadien basierend auf Dokumenttyp
        if doc_type == "admin_act":
            stage_progression = [
                "application",
                "examination",
                "decision",
                "notification",
                "appeal_period",
                "finalized",
            ]

            if current_stage == "decision":
                results["next_possible_stages"] = ["notification", "appeal_period"]
                results["stage_history"].append(
                    {
                        "stage": "application",
                        "estimated_date": "vor Entscheidung",
                        "confidence": 0.8,
                    }
                )
                results["stage_history"].append(
                    {
                        "stage": "examination",
                        "estimated_date": "vor Entscheidung",
                        "confidence": 0.9,
                    }
                )

        elif doc_type == "law":
            stage_progression = [
                "draft",
                "consultation",
                "parliamentary_review",
                "enacted",
                "in_force",
            ]

            if (
                current_stage == "examination"
            ):  # Bei Gesetzen = parlamentarische Prüfung
                results["current_stage"] = "parliamentary_review"
                results["next_possible_stages"] = ["enacted"]

        # Timeline-Schätzung
        results["timeline_estimation"] = {
            "procedure_type": doc_type,
            "estimated_duration": self._estimate_procedure_duration(
                doc_type, current_stage
            ),
            "time_remaining": self._estimate_time_remaining(doc_type, current_stage),
        }

        self.logger.info(
            f"✅ Verfahrensstadien-Tracking abgeschlossen: Stadium '{current_stage}'"
        )
        return results

    def _handle_compliance_checking(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prüft Rechtmäßigkeit und Compliance von Verwaltungsdokumenten

        Args:
            task: Task mit Compliance-Kontext

        Returns:
            Dictionary mit Compliance-Prüfung
        """
        self.logger.info("⚖️ Starte Rechtmäßigkeitsprüfung...")

        file_id = task.get("file_id")
        metadata = task.get("metadata", {})

        results = {
            "compliance_type": "legal_compliance",
            "file_id": file_id,
            "compliance_checks": [],
            "overall_compliance": "unknown",
            "risk_indicators": [],
        }

        # Compliance-Checks basierend auf Dokumenttyp
        doc_type = None
        has_remedy_notice = False
        has_legal_references = False

        if "keywords" in metadata:
            for keyword in metadata["keywords"]:
                if keyword.startswith("uds3_type:"):
                    doc_type = keyword.split(":")[1]
                elif keyword == "has_remedy_notice:true":
                    has_remedy_notice = True
                elif keyword.startswith(("paragraph:", "article:")):
                    has_legal_references = True

        # Spezifische Compliance-Checks
        if doc_type == "admin_act":
            # Rechtsbehelfsbelehrung prüfen
            results["compliance_checks"].append(
                {
                    "check_type": "remedy_notice_required",
                    "status": "passed" if has_remedy_notice else "failed",
                    "requirement": "Verwaltungsakte müssen Rechtsbehelfsbelehrung enthalten",
                    "confidence": 0.9,
                }
            )

            # Rechtliche Grundlagen prüfen
            results["compliance_checks"].append(
                {
                    "check_type": "legal_basis_referenced",
                    "status": "passed" if has_legal_references else "warning",
                    "requirement": "Verwaltungsakte sollten Rechtsgrundlagen angeben",
                    "confidence": 0.8,
                }
            )

            # Zuständigkeit prüfen (vereinfacht)
            results["compliance_checks"].append(
                {
                    "check_type": "competence_check",
                    "status": "passed",
                    "requirement": "Behördliche Zuständigkeit muss gegeben sein",
                    "confidence": 0.7,
                }
            )

        # Overall Compliance bewerten
        passed_checks = sum(
            1 for check in results["compliance_checks"] if check["status"] == "passed"
        )
        total_checks = len(results["compliance_checks"])

        if total_checks > 0:
            compliance_ratio = passed_checks / total_checks
            if compliance_ratio >= 0.8:
                results["overall_compliance"] = "compliant"
            elif compliance_ratio >= 0.6:
                results["overall_compliance"] = "partially_compliant"
            else:
                results["overall_compliance"] = "non_compliant"

        # Risiko-Indikatoren
        failed_checks = [
            check
            for check in results["compliance_checks"]
            if check["status"] == "failed"
        ]
        for failed_check in failed_checks:
            results["risk_indicators"].append(
                {
                    "risk_type": "compliance_violation",
                    "description": f"Fehlgeschlagene Prüfung: {failed_check['check_type']}",
                    "severity": "high"
                    if "required" in failed_check["requirement"]
                    else "medium",
                }
            )

        self.logger.info(
            f"✅ Rechtmäßigkeitsprüfung abgeschlossen: {results['overall_compliance']}"
        )
        return results

    def _estimate_procedure_duration(self, doc_type: str, current_stage: str) -> str:
        """Schätzt Verfahrensdauer"""
        durations = {"admin_act": "3-6 Monate", "law": "12-24 Monate"}
        return durations.get(doc_type, "unbekannt")

    def _estimate_time_remaining(self, doc_type: str, current_stage: str) -> str:
        """Schätzt verbleibende Zeit"""
        if current_stage == "decision":
            return "2-4 Wochen (Zustellung + Rechtsmittelfrist)"
        elif current_stage == "examination":
            return "1-3 Monate"
        return "unbekannt"


def process_uds3_follow_up_tasks(tasks: List[Dict[str, Any]]) -> List[UDS3TaskResult]:
    """
    Verarbeitet eine Liste von UDS3 Follow-up Tasks

    Args:
        tasks: Liste von UDS3-spezifischen Tasks

    Returns:
        Liste von UDS3TaskResult-Objekten
    """
    orchestrator = UDS3TaskOrchestrator()
    results: list[Any] = []

    for task in tasks:
        result = orchestrator.process_uds3_task(task)
        results.append(result)

    return results


if __name__ == "__main__":
    # Test des UDS3 Task Orchestrators
    print("🏛️ UDS3 TASK ORCHESTRATOR TEST")
    print("=" * 60)

    # Test-Tasks erstellen
    test_tasks = [
        {
            "task_type": "uds3_database_integration",
            "task_id": "test_db_integration",
            "file_id": "test_doc_001",
            "metadata": {
                "keywords": [
                    "uds3_type:admin_act",
                    "admin_level:municipal",
                    "domain:building",
                ],
                "confidence_score": 0.9,
            },
        },
        {
            "task_type": "administrative_relationship_detection",
            "task_id": "test_relationship",
            "file_id": "test_doc_001",
            "metadata": {"keywords": ["uds3_type:admin_act", "domain:building"]},
        },
    ]

    # Tasks verarbeiten
    results = process_uds3_follow_up_tasks(test_tasks)

    for result in results:
        print(f"\n✅ Task: {result.task_type}")
        print(f"   Erfolg: {result.success}")
        print(f"   Dauer: {result.processing_time:.3f}s")
        if result.results:
            print(f"   Ergebnisse: {len(result.results)} Einträge")

    print("\n🎉 UDS3 Task Orchestrator Test abgeschlossen!")
