from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
import logging
import time

from ingestion.application.services.extraction_service import ExtractionService
from ingestion.application.services.graph_writer_service import GraphWriterService
from ingestion.observability.legal_nlp_metrics import (
    record_extraction_result,
    record_extraction_status,
    observe_latency,
)
from utils.json_logging import get_correlation_id

@dataclass
class IngestDocument:
    extractor: ExtractionService
    graph_writer: GraphWriterService

    async def execute(self, text: str) -> Any:
        logger = logging.getLogger("ingestion.use_case")

        # Start extraction timing
        t0 = time.perf_counter()
        try:
            result: Dict[str, Any] = await self.extractor.extract(text)
            extract_secs = observe_latency(t0, stage="extract")
            record_extraction_status(True)
        except Exception:
            # Count error and rethrow (no PII in logs)
            record_extraction_status(False)
            logger.exception(
                "legal_nlp_extraction_failed",
                extra={
                    "correlation_id": get_correlation_id(),
                },
            )
            raise

        # Count entities (no content logging)
        summary = record_extraction_result(result or {})

        # Write to graph (if writer is active, NoopWriter just returns)
        t1 = time.perf_counter()
        try:
            await self.graph_writer.write(result)
            write_secs = observe_latency(t1, stage="write")
            write_status = "success"
        except Exception:
            write_secs = observe_latency(t1, stage="write")
            write_status = "error"
            logger.exception(
                "legal_graph_write_failed",
                extra={
                    "correlation_id": get_correlation_id(),
                },
            )
            # Bubble up for caller to handle if needed
            raise

        # Structured summary log (PII-safe: no text excerpt)
        logger.info(
            "legal_nlp_ingest_completed",
            extra={
                "correlation_id": get_correlation_id(),
                "metrics": {
                    "extract_seconds": round(extract_secs, 6),
                    "write_seconds": round(write_secs, 6),
                    "entities": summary,
                    "write_status": write_status,
                },
            },
        )

        return {"status": "ok", "extraction": result, "metrics": {"entities": summary}}
