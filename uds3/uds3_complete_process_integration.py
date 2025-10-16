"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_complete_process_integration"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...XfSbQA=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "fb07a14f81c952468f6edf18b68ce3578d2c05ff44e84b1cc48d41be6a83b28a"
)
module_file_key = "9482c5df79c2ed33d50c57ca9a538044d4475b1d3e0c66bdf3cecc6c0b2c758a"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
UDS3 COMPLETE PROCESS-INTEGRATION ENGINE
========================================
Kombiniert UDS3 BPMN/EPK Parser mit ThreadCoordinator für vollständige 
Prozessmodellierungs-Integration im UDS3-Ökosystem

FEATURES:
- UDS3 Unified Process Parser für BPMN 2.0 und EPK/eEPK
- Asynchrone Verarbeitung mit UDS3 ThreadCoordinator
- Export zu XML mit UDS3-Compliance-Validierung
- Vollständige UDS3-Integration
- VBP-spezifische Verwaltungsattribute und Workflows
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Union
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from queue import PriorityQueue
from threading import Thread, Lock
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ProcessTask:
    """Prozess-Verarbeitungsaufgabe"""

    task_id: str
    task_type: str  # 'parse_bpmn', 'parse_epk', 'export_xml', 'validate'
    priority: int
    content: Union[str, Dict[str, Any]]  # XML-String für Parse, UDS3-Dict für Export
    config: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __lt__(self, other):
        """Für PriorityQueue-Sortierung"""
        return self.priority < other.priority


@dataclass
class ProcessResult:
    """Ergebnis der Prozess-Verarbeitung"""

    task_id: str
    success: bool
    content: Any  # UDS3-Document oder XML-String
    metadata: Dict[str, Any]
    validation_result: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0.0


class UDS3UnifiedProcessParser:
    """UDS3 Vereinigter Parser für BPMN und EPK Prozesse"""

    def __init__(self):
        self.parsers: dict[Any, Any] = {}
        self.validators: dict[Any, Any] = {}

        # Lade UDS3 Parser dynamisch (verhindert Import-Fehler)
        self._initialize_uds3_parsers()

        logger.info("UDS3 Unified Process Parser initialisiert")

    def _initialize_uds3_parsers(self):
        """Initialisiert UDS3 Parser-Module"""
        try:
            # UDS3 BPMN Parser
            from uds3_bpmn_process_parser import BPMNProcessParser, BPMNValidator

            self.parsers["bpmn"] = BPMNProcessParser()
            self.validators["bpmn"] = BPMNValidator()
            logger.info("✓ UDS3-BPMN-Parser geladen")

        except ImportError as e:
            logger.warning(f"UDS3-BPMN-Parser nicht verfügbar: {e}")
            self.parsers["bpmn"] = None

        try:
            # UDS3 EPK Parser
            from uds3_epk_process_parser import EPKProcessParser, EPKValidator

            self.parsers["epk"] = EPKProcessParser()
            self.validators["epk"] = EPKValidator()
            logger.info("✓ UDS3-EPK-Parser geladen")

        except ImportError as e:
            logger.warning(f"UDS3-EPK-Parser nicht verfügbar: {e}")
            self.parsers["epk"] = None

    def detect_process_format(self, xml_content: str) -> str:
        """Erkennt Prozessformat automatisch"""
        xml_lower = xml_content.lower()

        # BPMN 2.0 erkennen
        if "bpmn/20100524/model" in xml_content or "definitions" in xml_lower:
            return "bpmn"

        # EPK erkennen
        if any(
            keyword in xml_lower for keyword in ["prozesskette", "ereignis", "funktion"]
        ):
            if "eepk" in xml_lower or "erweiterte" in xml_lower:
                return "eepk"
            else:
                return "epk"

        # Fallback
        return "unknown"

    def parse_process_xml(
        self, xml_content: str, format_hint: Optional[str] = None, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parst Prozess-XML zu UDS3-Dokument"""
        try:
            # Format ermitteln
            process_format = format_hint or self.detect_process_format(xml_content)

            if process_format == "unknown":
                raise ValueError("Prozessformat konnte nicht erkannt werden")

            # Format-Mapping für Parser
            parser_format = "bpmn" if process_format == "bpmn" else "epk"

            if parser_format not in self.parsers or self.parsers[parser_format] is None:
                raise ValueError(f"Parser für Format '{parser_format}' nicht verfügbar")

            parser = self.parsers[parser_format]

            # Parsing durchführen
            if parser_format == "bpmn":
                uds3_document = parser.parse_bpmn_to_uds3(xml_content, filename)
            else:  # EPK/eEPK
                uds3_document = parser.parse_epk_to_uds3(xml_content, filename)

            # Process-Format in Metadaten setzen
            uds3_document.setdefault("metadata", {})["detected_format"] = process_format

            return uds3_document

        except Exception as e:
            logger.error(f"Process Parsing fehlgeschlagen: {e}")
            raise

    def validate_process(self, xml_content: str, process_format: Optional[str] = None):
        """Validiert Prozess-XML"""
        try:
            format_to_validate = process_format or self.detect_process_format(
                xml_content
            )

            validator_format = "bpmn" if format_to_validate == "bpmn" else "epk"

            if (
                validator_format not in self.validators
                or self.validators[validator_format] is None
            ):
                raise ValueError(
                    f"Validator für Format '{validator_format}' nicht verfügbar"
                )

            validator = self.validators[validator_format]

            # Validierung durchführen
            if validator_format == "bpmn":
                return validator.validate_bpmn_process(xml_content)
            else:  # EPK
                return validator.validate_epk_process(xml_content)

        except Exception as e:
            logger.error(f"Process Validation fehlgeschlagen: {e}")
            raise


class UDS3UnifiedProcessExporter:
    """UDS3 Vereinigter Exporter für Prozess-XML"""

    def __init__(self):
        self.export_engine = None
        self._initialize_uds3_exporter()

    def _initialize_uds3_exporter(self):
        """Initialisiert UDS3 Export-Engine"""
        try:
            from uds3_process_export_engine import ProcessExportEngine

            self.export_engine = ProcessExportEngine()
            logger.info("✓ UDS3 Process Export Engine geladen")

        except ImportError as e:
            logger.warning(f"UDS3 Process Export Engine nicht verfügbar: {e}")
            self.export_engine = None

    def export_to_xml(
        self,
        uds3_document: Dict[str, Any],
        export_format: str,
        output_path: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Exportiert UDS3-Dokument zu XML"""
        if self.export_engine is None:
            raise ValueError("Export Engine nicht verfügbar")

        result = self.export_engine.export_uds3_to_xml(
            uds3_document, export_format, output_path, **kwargs
        )

        if not result.success:
            raise ValueError(f"Export fehlgeschlagen: {result.errors}")

        return result.xml_content


class UDS3ProcessWorker:
    """UDS3 Worker für asynchrone Prozess-Verarbeitung"""

    def __init__(
        self, worker_id: str, task_queue: PriorityQueue, result_callback: Callable
    ):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_callback = result_callback

        # UDS3 Components
        self.parser = UDS3UnifiedProcessParser()
        self.exporter = UDS3UnifiedProcessExporter()

        # State
        self.running = False
        self.thread = None
        self.processed_count = 0
        self.lock = Lock()

        logger.info(f"UDS3 Process Worker {worker_id} initialisiert")

    def start(self):
        """Startet den Worker"""
        with self.lock:
            if self.running:
                return

            self.running = True
            self.thread = Thread(target=self._worker_loop, daemon=True)
            self.thread.start()
            logger.info(f"Process Worker {self.worker_id} gestartet")

    def stop(self):
        """Stoppt den Worker"""
        with self.lock:
            self.running = False

        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info(f"Process Worker {self.worker_id} gestoppt")

    def _worker_loop(self):
        """Hauptschleife des Workers"""
        while self.running:
            try:
                # Task aus Queue holen
                try:
                    task = self.task_queue.get(timeout=1.0)
                except:
                    continue

                logger.info(
                    f"Worker {self.worker_id} verarbeitet Task {task.task_id} (Typ: {task.task_type})"
                )

                start_time = datetime.now()

                # Task verarbeiten
                try:
                    result = self._process_task(task)
                    result.processing_time = (
                        datetime.now() - start_time
                    ).total_seconds()

                    logger.info(
                        f"Task {task.task_id} erfolgreich verarbeitet in {result.processing_time:.2f}s"
                    )

                except Exception as e:
                    result = ProcessResult(
                        task_id=task.task_id,
                        success=False,
                        content=None,
                        metadata={"worker_id": self.worker_id},
                        errors=[str(e)],
                        processing_time=(datetime.now() - start_time).total_seconds(),
                    )

                    logger.error(f"Task {task.task_id} fehlgeschlagen: {e}")

                # Ergebnis zurückgeben
                if self.result_callback:
                    try:
                        self.result_callback(task, result)
                    except Exception as e:
                        logger.error(f"Result Callback Fehler: {e}")

                # Callback aus Task ausführen
                if task.callback:
                    try:
                        task.callback(result)
                    except Exception as e:
                        logger.error(f"Task Callback Fehler: {e}")

                self.processed_count += 1
                self.task_queue.task_done()

            except Exception as e:
                logger.error(f"Worker {self.worker_id} Loop-Fehler: {e}")

    def _process_task(self, task: ProcessTask) -> ProcessResult:
        """Verarbeitet einzelne Tasks"""
        if task.task_type == "parse_bpmn" or task.task_type == "parse_epk":
            return self._parse_process(task)
        elif task.task_type == "export_xml":
            return self._export_process(task)
        elif task.task_type == "validate":
            return self._validate_process(task)
        else:
            raise ValueError(f"Unbekannter Task-Typ: {task.task_type}")

    def _parse_process(self, task: ProcessTask) -> ProcessResult:
        """Verarbeitet Parse-Task"""
        xml_content = task.content
        filename = task.config.get("filename")
        format_hint = task.config.get("format_hint")

        # Parsing durchführen
        uds3_document = self.parser.parse_process_xml(
            xml_content, format_hint, filename
        )

        # Validation (optional)
        validation_result: dict[Any, Any] = {}
        if task.config.get("validate", True):
            try:
                validation_result = self.parser.validate_process(
                    xml_content, format_hint
                )
            except Exception as e:
                validation_result = {"validation_error": str(e)}

        return ProcessResult(
            task_id=task.task_id,
            success=True,
            content=uds3_document,
            metadata={
                "worker_id": self.worker_id,
                "parser_engine": "UDS3UnifiedProcessParser",
                "original_size": len(xml_content.encode("utf-8")),
                "elements_parsed": len(
                    uds3_document.get("content", {}).get("bpmn_elements", [])
                )
                + len(uds3_document.get("content", {}).get("epk_elements", [])),
            },
            validation_result=validation_result,
        )

    def _export_process(self, task: ProcessTask) -> ProcessResult:
        """Verarbeitet Export-Task"""
        uds3_document = task.content
        export_format = task.config.get("export_format", "bpmn20")
        output_path = task.config.get("output_path")

        # Export durchführen
        xml_content = self.exporter.export_to_xml(
            uds3_document,
            export_format,
            output_path,
            **task.config.get("export_options", {}),
        )

        return ProcessResult(
            task_id=task.task_id,
            success=True,
            content=xml_content,
            metadata={
                "worker_id": self.worker_id,
                "export_engine": "UDS3UnifiedProcessExporter",
                "export_format": export_format,
                "output_size": len(xml_content.encode("utf-8")),
                "output_path": output_path,
            },
        )

    def _validate_process(self, task: ProcessTask) -> ProcessResult:
        """Verarbeitet Validation-Task"""
        xml_content = task.content
        format_hint = task.config.get("format_hint")

        # Validierung durchführen
        validation_result = self.parser.validate_process(xml_content, format_hint)

        return ProcessResult(
            task_id=task.task_id,
            success=True,
            content=validation_result,
            metadata={
                "worker_id": self.worker_id,
                "validation_engine": "UDS3UnifiedProcessValidator",
            },
            validation_result=validation_result,
        )


class UDS3ProcessIntegrationCoordinator:
    """Haupt-Koordinator für UDS3 Prozess-Integration"""

    def __init__(self, num_workers: int = 3):
        self.num_workers = num_workers
        self.task_queue: PriorityQueue[Any] = PriorityQueue()
        self.workers: list[Any] = []
        self.results: dict[Any, Any] = {}
        self.callbacks: dict[Any, Any] = {}
        self.stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_processing_time": 0.0,
        }
        self.running = False
        self.lock = Lock()

        logger.info(
            f"UDS3 Process Integration Coordinator mit {num_workers} Workern initialisiert"
        )

    def start(self):
        """Startet den Coordinator"""
        with self.lock:
            if self.running:
                return

            self.running = True

            # UDS3 Worker erstellen und starten
            for i in range(self.num_workers):
                worker = UDS3ProcessWorker(
                    worker_id=f"uds3_process_worker_{i}",
                    task_queue=self.task_queue,
                    result_callback=self._handle_result,
                )
                worker.start()
                self.workers.append(worker)

            logger.info(
                f"UDS3 Process Integration Coordinator mit {len(self.workers)} Workern gestartet"
            )

    def stop(self):
        """Stoppt den Coordinator"""
        with self.lock:
            self.running = False

        # Alle Worker stoppen
        for worker in self.workers:
            worker.stop()

        self.workers.clear()
        logger.info("UDS3 Process Integration Coordinator gestoppt")

    def submit_parse_task(
        self,
        xml_content: str,
        format_hint: Optional[str] = None,
        filename: Optional[str] = None,
        priority: int = 5,
        callback: Callable = None,
    ) -> str:
        """Submittet Parse-Task"""
        task_id = str(uuid.uuid4())

        task = ProcessTask(
            task_id=task_id,
            task_type=f"parse_{format_hint}" if format_hint else "parse_bpmn",
            priority=priority,
            content=xml_content,
            config={"format_hint": format_hint, "filename": filename, "validate": True},
            callback=callback,
        )

        self.task_queue.put(task)
        self.stats["tasks_submitted"] += 1

        logger.info(
            f"Parse-Task {task_id} submitted (Format: {format_hint}, Priorität: {priority})"
        )
        return task_id

    def submit_export_task(
        self,
        uds3_document: Dict[str, Any],
        export_format: str = "bpmn20",
        output_path: Optional[str] = None,
        priority: int = 5,
        callback: Callable = None,
        **export_options,
    ) -> str:
        """Submittet Export-Task"""
        task_id = str(uuid.uuid4())

        task = ProcessTask(
            task_id=task_id,
            task_type="export_xml",
            priority=priority,
            content=uds3_document,
            config={
                "export_format": export_format,
                "output_path": output_path,
                "export_options": export_options,
            },
            callback=callback,
        )

        self.task_queue.put(task)
        self.stats["tasks_submitted"] += 1

        logger.info(
            f"Export-Task {task_id} submitted (Format: {export_format}, Priorität: {priority})"
        )
        return task_id

    def submit_validation_task(
        self,
        xml_content: str,
        format_hint: Optional[str] = None,
        priority: int = 5,
        callback: Callable = None,
    ) -> str:
        """Submittet Validation-Task"""
        task_id = str(uuid.uuid4())

        task = ProcessTask(
            task_id=task_id,
            task_type="validate",
            priority=priority,
            content=xml_content,
            config={"format_hint": format_hint},
            callback=callback,
        )

        self.task_queue.put(task)
        self.stats["tasks_submitted"] += 1

        logger.info(f"Validation-Task {task_id} submitted (Format: {format_hint})")
        return task_id

    def get_result(
        self, task_id: str, timeout: float = 30.0
    ) -> Optional[ProcessResult]:
        """Holt Ergebnis für Task (blockierend)"""
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            if task_id in self.results:
                return self.results.pop(task_id)
            time.sleep(0.1)

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück"""
        worker_stats: list[Any] = []
        for worker in self.workers:
            worker_stats.append(
                {
                    "worker_id": worker.worker_id,
                    "processed_count": worker.processed_count,
                    "running": worker.running,
                }
            )

        return {
            **self.stats,
            "queue_size": self.task_queue.qsize(),
            "num_workers": len(self.workers),
            "worker_stats": worker_stats,
            "avg_processing_time": (
                self.stats["total_processing_time"]
                / max(1, self.stats["tasks_completed"])
            ),
        }

    def _handle_result(self, task: ProcessTask, result: ProcessResult):
        """Behandelt Worker-Ergebnisse"""
        # Ergebnis speichern
        self.results[task.task_id] = result

        # Statistiken updaten
        if result.success:
            self.stats["tasks_completed"] += 1
        else:
            self.stats["tasks_failed"] += 1

        self.stats["total_processing_time"] += result.processing_time

        # Task-spezifische Callbacks ausführen
        if task.task_id in self.callbacks:
            try:
                self.callbacks[task.task_id](result)
                del self.callbacks[task.task_id]
            except Exception as e:
                logger.error(f"Callback Fehler für Task {task.task_id}: {e}")


# UDS3 Convenience Functions
def create_uds3_process_coordinator(
    num_workers: int = 3,
) -> UDS3ProcessIntegrationCoordinator:
    """Erstellt und startet UDS3 Process Integration Coordinator"""
    coordinator = UDS3ProcessIntegrationCoordinator(num_workers)
    coordinator.start()
    return coordinator


# Export für UDS3-Integration
def get_uds3_process_coordinator():
    """Gibt UDS3 Process Integration Coordinator zurück"""
    return UDS3ProcessIntegrationCoordinator()


def get_uds3_unified_parser():
    """Gibt UDS3 Unified Process Parser zurück"""
    return UDS3UnifiedProcessParser()


def get_uds3_unified_exporter():
    """Gibt UDS3 Unified Process Exporter zurück"""
    return UDS3UnifiedProcessExporter()


if __name__ == "__main__":
    # Test der UDS3 Process Integration
    coordinator = create_uds3_process_coordinator(num_workers=2)

    # Test BPMN-Parsing
    test_bpmn = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:verwaltung="http://www.verwaltung.de/prozess/v1"
                      id="test_antrag" targetNamespace="http://verwaltung.de">
        <bpmn:process id="antrag_bearbeitung" name="Antragsbearbeitung">
            <bpmn:startEvent id="start_antrag" name="Antrag eingegangen"/>
            <bpmn:userTask id="antrag_pruefen" name="Antrag prüfen"/>
            <bpmn:endEvent id="end_prozess" name="Prozess beendet"/>
            <bpmn:sequenceFlow id="flow1" sourceRef="start_antrag" targetRef="antrag_pruefen"/>
            <bpmn:sequenceFlow id="flow2" sourceRef="antrag_pruefen" targetRef="end_prozess"/>
        </bpmn:process>
    </bpmn:definitions>"""

    # Parse-Task submitten
    def parse_callback(result):
        print(f"✓ UDS3 Parse-Ergebnis erhalten: {result.success}")
        if result.success:
            print(
                f"  Prozess: {result.content.get('content', {}).get('process_name', 'Unknown')}"
            )
        else:
            print(f"  Fehler: {result.errors}")

    parse_task_id = coordinator.submit_parse_task(
        test_bpmn,
        format_hint="bpmn",
        filename="test_antrag.bpmn",
        callback=parse_callback,
    )

    # Kurz warten für Verarbeitung
    import time

    time.sleep(2)

    # Statistiken anzeigen
    stats = coordinator.get_stats()
    print("\nUDS3 Statistiken:")
    print(f"  Submitted: {stats['tasks_submitted']}")
    print(f"  Completed: {stats['tasks_completed']}")
    print(f"  Failed: {stats['tasks_failed']}")
    print(f"  Queue Size: {stats['queue_size']}")
    print(f"  Avg Processing Time: {stats['avg_processing_time']:.2f}s")

    # Coordinator stoppen
    coordinator.stop()
    print("\n✓ UDS3 Process Integration Test abgeschlossen")