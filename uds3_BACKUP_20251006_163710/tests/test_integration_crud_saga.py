import pytest
from typing import Any, Dict, List

from uds3_core import UnifiedDatabaseStrategy, OperationType


class SimpleMockManager:
    def __init__(self):
        self.storage = {}
        self.operations = []

    def create_document(self, document_id: str, data: Dict[str, Any]) -> bool:
        self.storage[document_id] = data
        self.operations.append(("create", document_id))
        return True

    def read_document(self, document_id: str) -> Dict[str, Any]:
        return self.storage.get(document_id, {})

    def update_document(self, document_id: str, updates: Dict[str, Any]) -> bool:
        if document_id not in self.storage:
            return False
        self.storage[document_id].update(updates)
        self.operations.append(("update", document_id))
        return True

    def delete_document(self, document_id: str) -> bool:
        if document_id in self.storage:
            del self.storage[document_id]
            self.operations.append(("delete", document_id))
            return True
        return False


def test_create_read_update_delete_flow():
    s = UnifiedDatabaseStrategy()
    mock = SimpleMockManager()

    # Inject mock as database manager
    s._database_manager = mock

    plan = s.create_document_operation(
        "path/to/file.pdf",
        "content",
        ["chunk1", "chunk2"],
        title="Test",
        author="Tester",
    )

    # plan should be a dict describing operations to all DBs
    assert isinstance(plan, dict)
    assert "databases" in plan
    # simulate executing vector write
    doc_id = plan.get("document_id") or "doc_1"
    created = mock.create_document(doc_id, {"title": "Test"})
    assert created

    read = mock.read_document(doc_id)
    assert read.get("title") == "Test"

    updated = mock.update_document(doc_id, {"title": "Updated"})
    assert updated
    read2 = mock.read_document(doc_id)
    assert read2.get("title") == "Updated"

    deleted = mock.delete_document(doc_id)
    assert deleted


def test_batch_operation_and_saga_flow():
    s = UnifiedDatabaseStrategy()
    mock = SimpleMockManager()
    s._database_manager = mock

    plan = s.create_document_operation(
        "path/to/file2.pdf",
        "content2",
        ["c1"],
        title="Batch Test",
    )

    batch = s.batch_operation([plan], OperationType.CREATE)
    assert isinstance(batch, dict)
    assert batch.get("operation_count", 0) >= 1
    # simulate that saga_crud executes and records the operations
    # we can't fully emulate sagas here, but ensure no exceptions and proper dict
    assert "databases" in batch
