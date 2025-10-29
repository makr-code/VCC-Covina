"""
Document Migration Job Tests
=============================

Tests for DocumentMigrationJob batching logic, state management, and resumability.

Coverage:
- State save/load
- Batch processing logic
- Resume from checkpoint
- Reset functionality
- Dry-run mode
- Error handling
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from ingestion.graph.document_migration import (
    DocumentMigrationJob,
    MigrationState,
)


@pytest.fixture
def temp_state_file(tmp_path):
    """Provide a temporary state file for testing."""
    return tmp_path / "test_migration_state.json"


@pytest.fixture
def mock_documents():
    """Sample document records from PostgreSQL."""
    return [
        {"id": "doc_001", "file_path": "/data/doc1.pdf", "classification": "LEGAL", "content_length": 1000},
        {"id": "doc_002", "file_path": "/data/doc2.pdf", "classification": "LEGAL", "content_length": 2000},
        {"id": "doc_003", "file_path": "/data/doc3.pdf", "classification": "LEGAL", "content_length": 1500},
    ]


@pytest.fixture
def mock_content():
    """Sample legal document content."""
    return """
    Az. 4 K 123/20
    Beschluss vom 15.03.2023 (ECLI:DE:BVerwG:2023:150323U4C123.20)
    Nach § 3 Abs. 1 BauGB ist die Öffentlichkeit zu beteiligen.
    """


def test_migration_state_save_load(temp_state_file):
    """Test MigrationState persistence."""
    # Create state
    state = MigrationState(
        last_processed_id="doc_123",
        total_processed=50,
        total_entities_extracted=200,
        total_errors=5,
        batches_completed=10,
    )

    # Save
    state.save(temp_state_file)
    assert temp_state_file.exists()

    # Load
    loaded_state = MigrationState.load(temp_state_file)
    assert loaded_state.last_processed_id == "doc_123"
    assert loaded_state.total_processed == 50
    assert loaded_state.total_entities_extracted == 200
    assert loaded_state.total_errors == 5
    assert loaded_state.batches_completed == 10


def test_migration_state_load_nonexistent(temp_state_file):
    """Test loading state from non-existent file creates new state."""
    state = MigrationState.load(temp_state_file)
    assert state.last_processed_id is None
    assert state.total_processed == 0
    assert state.started_at is not None  # Should be set to current time


def test_migration_job_init_dry_run(temp_state_file):
    """Test job initialization in dry-run mode."""
    job = DocumentMigrationJob(
        batch_size=50,
        delay=0.1,
        dry_run=True,
        state_file=temp_state_file,
    )

    assert job.batch_size == 50
    assert job.delay == 0.1
    assert job.dry_run is True
    assert job.writer is None  # No writer in dry-run mode
    assert job.extractor is not None


def test_migration_job_init_production(temp_state_file):
    """Test job initialization in production mode."""
    with patch("ingestion.graph.document_migration.EntityGraphWriter"):
        job = DocumentMigrationJob(
            batch_size=100,
            delay=0.5,
            dry_run=False,
            state_file=temp_state_file,
        )

        assert job.batch_size == 100
        assert job.delay == 0.5
        assert job.dry_run is False
        # Writer would be initialized (mocked)


@pytest.mark.asyncio
async def test_fetch_documents_batch_mock(temp_state_file, mock_documents):
    """Test document batch fetching with mocked PostgreSQL."""
    job = DocumentMigrationJob(
        batch_size=3,
        dry_run=True,
        state_file=temp_state_file,
    )

    # Mock PostgreSQL backend
    with patch.object(job, "get_postgres_connection") as mock_conn:
        mock_backend = Mock()
        mock_backend.execute_query.return_value = mock_documents
        mock_conn.return_value = mock_backend

        # Fetch batch
        documents = await job.fetch_documents_batch(limit=3)

        assert len(documents) == 3
        assert documents[0]["id"] == "doc_001"
        assert documents[1]["id"] == "doc_002"
        assert documents[2]["id"] == "doc_003"


@pytest.mark.asyncio
async def test_fetch_documents_batch_with_resume(temp_state_file, mock_documents):
    """Test batch fetching resumes from last processed ID."""
    # Create state with last processed ID
    state = MigrationState(last_processed_id="doc_001")
    state.save(temp_state_file)

    job = DocumentMigrationJob(
        batch_size=3,
        dry_run=True,
        state_file=temp_state_file,
    )

    # Verify state loaded
    assert job.state.last_processed_id == "doc_001"

    # Mock PostgreSQL backend
    with patch.object(job, "get_postgres_connection") as mock_conn:
        mock_backend = Mock()
        # Simulate query with WHERE id > 'doc_001'
        filtered_docs = [d for d in mock_documents if d["id"] > "doc_001"]
        mock_backend.execute_query.return_value = filtered_docs
        mock_conn.return_value = mock_backend

        # Fetch batch
        documents = await job.fetch_documents_batch(limit=3)

        # Should only get doc_002 and doc_003
        assert len(documents) == 2
        assert documents[0]["id"] == "doc_002"


@pytest.mark.asyncio
async def test_process_document_dry_run(temp_state_file, mock_content):
    """Test document processing in dry-run mode."""
    job = DocumentMigrationJob(
        batch_size=1,
        dry_run=True,
        state_file=temp_state_file,
    )

    doc_record = {"id": "doc_test", "file_path": "/test.pdf"}

    # Mock content fetch
    with patch.object(job, "fetch_document_content", return_value=mock_content):
        stats = await job.process_document(doc_record)

        assert stats["document_id"] == "doc_test"
        assert stats["entities_extracted"] > 0  # Should extract entities
        assert stats["entities_persisted"] > 0  # Should "persist" in dry-run
        assert stats["skipped"] is False
        assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_process_document_no_content(temp_state_file):
    """Test document processing with no content (skip)."""
    job = DocumentMigrationJob(
        batch_size=1,
        dry_run=True,
        state_file=temp_state_file,
    )

    doc_record = {"id": "doc_empty", "file_path": "/empty.pdf"}

    # Mock content fetch returning None
    with patch.object(job, "fetch_document_content", return_value=None):
        stats = await job.process_document(doc_record)

        assert stats["document_id"] == "doc_empty"
        assert stats["entities_extracted"] == 0
        assert stats["skipped"] is True


@pytest.mark.asyncio
async def test_process_document_no_entities(temp_state_file):
    """Test document processing with no legal entities."""
    job = DocumentMigrationJob(
        batch_size=1,
        dry_run=True,
        state_file=temp_state_file,
    )

    doc_record = {"id": "doc_plain", "file_path": "/plain.pdf"}
    plain_content = "This is a plain business document with no legal references."

    # Mock content fetch
    with patch.object(job, "fetch_document_content", return_value=plain_content):
        stats = await job.process_document(doc_record)

        assert stats["document_id"] == "doc_plain"
        assert stats["entities_extracted"] == 0  # No legal entities
        assert stats["entities_persisted"] == 0
        assert stats["skipped"] is False  # Not skipped, just no entities


@pytest.mark.asyncio
async def test_run_with_limit(temp_state_file, mock_documents, mock_content):
    """Test migration run with document limit."""
    job = DocumentMigrationJob(
        batch_size=10,
        delay=0.0,  # No delay for test speed
        dry_run=True,
        state_file=temp_state_file,
    )

    # Mock methods
    with patch.object(job, "fetch_documents_batch", return_value=mock_documents[:2]), \
         patch.object(job, "fetch_document_content", return_value=mock_content):

        summary = await job.run(limit=2)

        assert summary["total_documents_processed"] == 2
        assert summary["total_entities_extracted"] > 0
        assert summary["batches_completed"] == 1
        assert summary["dry_run"] is True


@pytest.mark.asyncio
async def test_run_saves_state(temp_state_file, mock_documents, mock_content):
    """Test that migration run saves state after each batch."""
    job = DocumentMigrationJob(
        batch_size=2,
        delay=0.0,
        dry_run=True,
        state_file=temp_state_file,
    )

    # Mock methods to return one batch
    async def mock_fetch(limit=None):
        if job.state.batches_completed == 0:
            return mock_documents[:2]
        return []  # No more batches

    with patch.object(job, "fetch_documents_batch", side_effect=mock_fetch), \
         patch.object(job, "fetch_document_content", return_value=mock_content):

        await job.run()

        # Verify state file was created
        assert temp_state_file.exists()

        # Load and verify state
        saved_state = MigrationState.load(temp_state_file)
        assert saved_state.total_processed == 2
        assert saved_state.batches_completed == 1
        assert saved_state.last_processed_id == "doc_002"  # Last in batch


def test_reset_clears_state(temp_state_file):
    """Test reset functionality clears state file."""
    # Create state file
    state = MigrationState(total_processed=100)
    state.save(temp_state_file)
    assert temp_state_file.exists()

    # Reset
    job = DocumentMigrationJob(state_file=temp_state_file, dry_run=True)
    job.reset()

    # Verify file deleted
    assert not temp_state_file.exists()


def test_reset_nonexistent_state(temp_state_file):
    """Test reset with no state file doesn't error."""
    job = DocumentMigrationJob(state_file=temp_state_file, dry_run=True)
    job.reset()  # Should not raise exception
    assert not temp_state_file.exists()
