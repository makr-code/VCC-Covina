from __future__ import annotations
import os
from ingestion.application.services.extraction_service import RegexExtractionService
from ingestion.application.services.graph_writer_service import NoopGraphWriter, RealGraphWriter
from ingestion.application.use_cases.ingest_document import IngestDocument

class Container:
    def __init__(self) -> None:
        self.extractor = RegexExtractionService()
        # Choose graph writer via ENV flag (default: Noop for safe dev runs)
        if os.getenv("ENABLE_GRAPH_WRITER", "false").lower() == "true":
            self.graph_writer = RealGraphWriter()
        else:
            self.graph_writer = NoopGraphWriter()
        self.ingest_document = IngestDocument(self.extractor, self.graph_writer)

container = Container()
