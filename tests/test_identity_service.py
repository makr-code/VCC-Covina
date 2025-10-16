from __future__ import annotations

import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import uuid

import pytest

from uds3.uds3_identity_service import IdentityNotFoundError, UDS3IdentityService
from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend


@pytest.fixture()
def identity_service(tmp_path):
    # PostgreSQL Test-Config (separate Test-Datenbank)
    postgres_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'test_covina',  # Separate Test-DB
        'schema': 'public'
    }
    backend = PostgreSQLRelationalBackend(postgres_config)
    assert backend.connect(), "PostgreSQL backend konnte nicht initialisiert werden"
    service = UDS3IdentityService(backend)
    yield service
    backend.disconnect()


def test_generate_uuid_creates_identity(identity_service):
    record = identity_service.generate_uuid(
        source_system="pytest",
        aktenzeichen="AZ-123/2025",
        actor="tester",
    )

    assert record.uuid
    assert record.aktenzeichen == "AZ-123/2025"
    assert record.status == "registered"

    loaded = identity_service.resolve_by_uuid(record.uuid)
    assert loaded.uuid == record.uuid
    assert loaded.aktenzeichen == "AZ-123/2025"


def test_register_aktenzeichen_allows_duplicates(identity_service):
    first = identity_service.generate_uuid(aktenzeichen="AZ-ABC", actor="tester1")
    second = identity_service.generate_uuid(actor="tester2")

    identity_service.register_aktenzeichen(second.uuid, "AZ-ABC", actor="tester2")

    first_reloaded = identity_service.resolve_by_uuid(first.uuid)
    second_reloaded = identity_service.resolve_by_uuid(second.uuid)

    assert first_reloaded.aktenzeichen == "AZ-ABC"
    assert second_reloaded.aktenzeichen == "AZ-ABC"


def test_bind_backend_ids_upserts(identity_service):
    record = identity_service.generate_uuid(actor="tester")

    updated = identity_service.bind_backend_ids(
        record.uuid,
        relational_id="rel-1",
        metadata={"source": "pytest"},
        actor="tester",
    )
    assert updated.mappings["relational_id"] == "rel-1"
    assert updated.mappings["graph_id"] is None

    # Update partial mapping and ensure previous values remain
    updated = identity_service.bind_backend_ids(
        record.uuid,
        graph_id="graph-9",
        vector_id="vec-77",
        actor="tester",
    )
    assert updated.mappings["relational_id"] == "rel-1"
    assert updated.mappings["graph_id"] == "graph-9"
    assert updated.mappings["vector_id"] == "vec-77"


def test_ensure_identity_creates_or_updates(identity_service):
    explicit_uuid = str(uuid.uuid4())
    ensured = identity_service.ensure_identity(
        explicit_uuid,
        aktenzeichen="AZ-999",
        source_system="pytest",
        actor="tester",
    )
    assert ensured.uuid == explicit_uuid.lower()
    assert ensured.aktenzeichen == "AZ-999"

    other_uuid = str(uuid.uuid4())
    other_identity = identity_service.ensure_identity(
        other_uuid,
        aktenzeichen="AZ-999",
        source_system="pytest",
        actor="tester",
    )
    assert other_identity.uuid == other_uuid.lower()
    assert other_identity.aktenzeichen == "AZ-999"

    # resolve_by_aktenzeichen liefert den zuletzt aktualisierten Datensatz
    resolved = identity_service.resolve_by_aktenzeichen("AZ-999")
    assert resolved.uuid == other_identity.uuid

    # Non-existing aktenzeichen raises
    with pytest.raises(IdentityNotFoundError):
        identity_service.resolve_by_aktenzeichen("AZ-NOPE")
