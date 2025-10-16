"""Factories for translating file events into pipeline jobs."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .file_events import FileCategory, FileEvent, FileEventType

logger = logging.getLogger(__name__)


@dataclass
class PipelineMapping:
    """Describes how a file category maps to an ingestion pipeline."""

    force_pipeline: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class FileIngestionJobFactory:
    """Creates pipeline submissions based on file events."""

    def __init__(
        self,
        orchestrator,
        *,
        pipeline_mappings: Optional[Dict[FileCategory, PipelineMapping]] = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._pipeline_mappings = pipeline_mappings or {}

    def submit(self, event: FileEvent) -> Optional[str]:
        """Submit a pipeline for the given event.

        Returns the created pipeline id or ``None`` if no submission was made.
        """

        if event.event_type == FileEventType.DELETED:
            logger.info("Ignoriere Delete-Event für %s", event.path)
            return None

        snapshot = event.snapshot
        if snapshot is None:
            logger.warning("Kein Snapshot für Event %s vorhanden", event)
            return None

        mapping = self._pipeline_mappings.get(snapshot.category)
        force_pipeline = mapping.force_pipeline if mapping else None
        meta_payload = mapping.metadata if mapping else None

        file_path = str(snapshot.path)
        pipeline_id = self._create_pipeline(file_path, force_pipeline, meta_payload)
        if pipeline_id:
            logger.info("Pipeline %s für %s eingereiht (%s)", pipeline_id, file_path, snapshot.category.value)
        else:
            logger.warning("Keine Pipeline für %s erstellt", file_path)
        return pipeline_id

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _create_pipeline(
        self, file_path: str, force_pipeline: Optional[str], metadata: Optional[Dict[str, str]]
    ) -> Optional[str]:
        orchestrator = self._orchestrator

        if metadata and hasattr(orchestrator, "create_pipeline_from_dict"):
            # Option für zukünftige Nutzung
            pass

        # bevorzugt: create_pipeline_from_file wenn verfügbar
        if hasattr(orchestrator, "create_pipeline_from_file"):
            try:
                pipeline_id = orchestrator.create_pipeline_from_file(
                    file_path=file_path,
                    force_pipeline=force_pipeline,
                    metadata=metadata,
                )
            except TypeError:
                try:
                    pipeline_id = orchestrator.create_pipeline_from_file(
                        file_path=file_path, force_pipeline=force_pipeline
                    )
                except TypeError:
                    pipeline_id = orchestrator.create_pipeline_from_file(file_path=file_path)
        else:
            pipeline_id = None

        if not pipeline_id and hasattr(orchestrator, "create_simple_pipeline"):
            pipeline_id = orchestrator.create_simple_pipeline(file_path)

        return pipeline_id


class JobFactoryBuilder:
    """Factory-of-factories adhering to the requested OOP style."""

    def __init__(self, orchestrator):
        self._orchestrator = orchestrator
        self._mappings: Dict[FileCategory, PipelineMapping] = {}

    def register_mapping(self, category: FileCategory, mapping: PipelineMapping) -> "JobFactoryBuilder":
        self._mappings[category] = mapping
        return self

    def build(self) -> FileIngestionJobFactory:
        return FileIngestionJobFactory(self._orchestrator, pipeline_mappings=dict(self._mappings))
