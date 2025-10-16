from __future__ import annotations

import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import time
from pathlib import Path

import pytest

from uds3.database.database_api_sqlite import SQLiteRelationalBackend
from ingestion_core import CoreIngestHandler, File, Job, JobType
from uds3 import uds3_identity_service as identity_module


@pytest.fixture()
def configured_identity_service(tmp_path):
    db_path = tmp_path / "identity.db"
    backend = SQLiteRelationalBackend({"database_path": str(db_path)})
    assert backend.connect(), "SQLite backend konnte nicht initialisiert werden"

    identity_module._identity_service = None
    service = identity_module.UDS3IdentityService(backend)
    identity_module._identity_service = service

    yield service

    identity_module._identity_service = None
    backend.disconnect()


def _build_job(handler: CoreIngestHandler, file_obj: File) -> Job:
    return Job(
        priority=0,
        enq_ts=time.time(),
        job_id="job-ingest",
        worker_type=handler.worker_type,
        job_type=JobType.FILE_LEVEL,
        target_id=file_obj.file_id,
        pipeline_id="pipeline-1",
        task_id="task-core",
    )


def test_core_ingest_registers_detected_aktenzeichen(tmp_path, configured_identity_service):
    handler = CoreIngestHandler()
    file_path = tmp_path / "aktenzeichen.txt"
    file_path.write_text("Az.: 12 K 1234/2023\nWeitere Inhalte", encoding="utf-8")

    file_obj = File(
        file_id="file-1",
        file_path=str(file_path),
        original_path=str(file_path),
    )
    job = _build_job(handler, file_obj)

    result = handler.process_file(file_obj, job)
    assert result.is_success

    ingestion_data = result.data.get("ingestion")
    assert ingestion_data is not None

    metadata = ingestion_data["metadata"]
    identity_payload = ingestion_data.get("identity")

    expected_aktenzeichen = "K 1234/2023"

    assert metadata["aktenzeichen"] == expected_aktenzeichen
    assert metadata["aktenzeichen_source"] == "analysis"
    assert "aktenzeichen_generated" not in metadata

    assert identity_payload is not None
    assert identity_payload["aktenzeichen"] == expected_aktenzeichen
    assert identity_payload["uuid"] == ingestion_data["document_id"]
    assert Path(file_obj.file_path).name == metadata["file_name"]

    record = configured_identity_service.resolve_by_aktenzeichen(expected_aktenzeichen)
    assert record.uuid == ingestion_data["document_id"]
    assert configured_identity_service.resolve_by_uuid(record.uuid).aktenzeichen == expected_aktenzeichen

    assert file_obj.metadata["aktenzeichen"] == expected_aktenzeichen
    assert file_obj.metadata["identity"]["aktenzeichen_source"] == "analysis"
    assert file_obj.metadata["identity"]["uuid"] == identity_payload["uuid"]


def test_core_ingest_generates_fallback_aktenzeichen(tmp_path, configured_identity_service):
    handler = CoreIngestHandler()
    file_path = tmp_path / "ohne_aktenzeichen.txt"
    file_path.write_text("Dies ist ein Dokument ohne eindeutiges Az.", encoding="utf-8")

    file_obj = File(
        file_id="file-2",
        file_path=str(file_path),
        original_path=str(file_path),
    )
    job = _build_job(handler, file_obj)

    result = handler.process_file(file_obj, job)
    assert result.is_success

    ingestion_data = result.data.get("ingestion")
    metadata = ingestion_data["metadata"]
    identity_payload = ingestion_data.get("identity")

    assert metadata["aktenzeichen_source"] == "generated"
    assert metadata["aktenzeichen_generated"] is True
    assert metadata["aktenzeichen"].startswith("AUTO-")

    assert identity_payload is not None
    assert identity_payload["aktenzeichen"].startswith("AUTO-")
    assert identity_payload["uuid"] == ingestion_data["document_id"]

    record = configured_identity_service.resolve_by_aktenzeichen(metadata["aktenzeichen"])
    assert record.uuid == identity_payload["uuid"]
    assert record.aktenzeichen == metadata["aktenzeichen"]

    identity_meta = file_obj.metadata["identity"]
    assert identity_meta["aktenzeichen_generated"] is True
    assert identity_meta["aktenzeichen_source"] == "generated"
    assert identity_meta["uuid"] == identity_payload["uuid"]