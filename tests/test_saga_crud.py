from __future__ import annotations

import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import pytest

from database.adapter_governance import AdapterGovernance, AdapterGovernanceError
from database.saga_crud import SagaDatabaseCRUD
from uds3.database.database_api_file_storage import FileSystemStorageBackend
from uds3.database.database_api_postgresql import PostgreSQLRelationalBackend


class FakeVectorCollection:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}

    def add(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        for chunk_id, document, metadata in zip(ids, documents, metadatas):
            self.records[chunk_id] = {
                "document": document,
                "metadata": metadata,
            }

    def delete(self, *, ids: Optional[Iterable[str]] = None, where: Optional[Dict[str, Any]] = None) -> None:
        if ids:
            for chunk_id in ids:
                self.records.pop(chunk_id, None)
            return
        if where and "document_id" in where:
            doc_id = where["document_id"]
            for chunk_id in list(self.records.keys()):
                if self.records[chunk_id]["metadata"].get("document_id") == doc_id:
                    del self.records[chunk_id]

    def get(self, *, ids: Optional[Iterable[str]] = None, where: Optional[Dict[str, Any]] = None) -> Dict:
        ids = list(ids) if ids else None
        matched = []
        for chunk_id, entry in self.records.items():
            if ids and chunk_id not in ids:
                continue
            if where and entry["metadata"].get("document_id") != where.get("document_id"):
                continue
            matched.append((chunk_id, entry))
        return {
            "ids": [[chunk_id for chunk_id, _ in matched]],
            "documents": [[entry["document"] for _, entry in matched]],
            "metadatas": [[entry["metadata"] for _, entry in matched]],
        }


class FakeVectorBackend:
    def __init__(self) -> None:
        self.collections: Dict[str, FakeVectorCollection] = {}

    def is_available(self) -> bool:
        return True

    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> bool:
        self.collections.setdefault(name, FakeVectorCollection())
        return True

    def get_collection(self, name: str) -> Optional[FakeVectorCollection]:
        return self.collections.get(name)

    def add_documents(self, collection_name: str, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> bool:
        collection = self.collections.setdefault(collection_name, FakeVectorCollection())
        collection.add(documents, metadatas, ids)
        return True


@dataclass
class FakeGraphBackend:
    nodes: Dict[str, Dict[str, Any]]

    def __init__(self) -> None:
        self.nodes = {}

    def is_available(self) -> bool:
        return True

    def create_node(self, node_type: str, properties: Dict[str, Any], merge_key: str = "id") -> str:
        identifier = properties.get(merge_key)
        if not identifier:
            raise ValueError("merge_key missing")
        node_id = f"{node_type}::{identifier}"
        self.nodes[node_id] = dict(properties)
        return node_id

    def get_node(self, identifier: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(identifier)

    def delete_node(self, identifier: str) -> bool:
        self.nodes.pop(identifier, None)
        return True


class FakeManager:
    def __init__(self, tmp_path: Path) -> None:
        self._vector = FakeVectorBackend()
        self._graph = FakeGraphBackend()
        
        # PostgreSQL Backend für Tests (Test-Datenbank verwenden)
        postgres_config = {
            'host': 'localhost',  # Lokale Testumgebung
            'port': 5432,
            'user': 'postgres',
            'password': 'postgres',
            'database': 'test_covina',  # Separate Test-Datenbank
            'schema': 'public'
        }
        self._relational = PostgreSQLRelationalBackend(postgres_config)
        assert self._relational.connect()
        
        assets_root = tmp_path / "assets"
        self._file = FileSystemStorageBackend({"root_path": str(assets_root)})
        assert self._file.connect()
        self._governance = AdapterGovernance()

    def get_vector_backend(self) -> FakeVectorBackend:
        return self._vector

    def get_graph_backend(self) -> FakeGraphBackend:
        return self._graph

    def get_relational_backend(self) -> PostgreSQLRelationalBackend:
        return self._relational

    def get_file_backend(self) -> FileSystemStorageBackend:
        return self._file

    def ensure_operation_allowed(self, backend_key: str, operation: str) -> None:
        self._governance.ensure_operation_allowed(backend_key, operation)

    def enforce_payload_policy(self, backend_key: str, operation: str, payload: Any) -> None:
        self._governance.enforce_payload(backend_key, operation, payload)

    def close(self) -> None:
        self._relational.disconnect()
        self._file.disconnect()


@pytest.fixture()
def saga_crud(tmp_path: Path) -> Iterable[SagaDatabaseCRUD]:
    manager = FakeManager(tmp_path)
    crud = SagaDatabaseCRUD(manager=manager)
    try:
        yield crud
    finally:
        manager.close()


def collect_observability(crud: SagaDatabaseCRUD, aktenzeichen: str) -> Dict[str, Set[str]]:
    backend = crud._manager.get_relational_backend()  # type: ignore[attr-defined]
    traces = backend.execute_query(  # type: ignore[call-arg]
        """
        SELECT stage, status
          FROM administrative_identity_traces
         WHERE aktenzeichen = ?
        """,
        (aktenzeichen,),
    )
    metrics = backend.execute_query(  # type: ignore[call-arg]
        """
        SELECT metric_name
          FROM administrative_identity_metrics
         WHERE aktenzeichen = ?
        """,
        (aktenzeichen,),
    )
    return {
        "stages": {row.get("stage") for row in traces if row.get("stage")},
        "statuses": {row.get("status") for row in traces if row.get("status")},
        "metric_names": {row.get("metric_name") for row in metrics if row.get("metric_name")},
    }


def test_vector_crud_lifecycle(saga_crud: SagaDatabaseCRUD) -> None:
    aktenzeichen = "AKT-VECTOR"
    chunks = ["eins", "zwei"]
    create = saga_crud.vector_create("doc-vec", chunks, {"aktenzeichen": aktenzeichen})
    assert create.success
    assert create.data["chunk_count"] == 2

    read = saga_crud.vector_read("doc-vec")
    assert read.success
    assert len(read.data["documents"]) == 2

    update = saga_crud.vector_update("doc-vec", ["neu"], {"aktenzeichen": aktenzeichen})
    assert update.success

    read_updated = saga_crud.vector_read("doc-vec")
    assert read_updated.success
    assert len(read_updated.data["documents"]) == 1

    delete = saga_crud.vector_delete("doc-vec")
    assert delete.success
    read_after_delete = saga_crud.vector_read("doc-vec")
    assert not read_after_delete.success

    observability = collect_observability(saga_crud, aktenzeichen)
    assert {"vector.create", "vector.read", "vector.update"}.issubset(observability["stages"])
    assert "success" in observability["statuses"]
    assert {
        "vector.create.attempt",
        "vector.create.success",
        "vector.create.duration_ms",
        "vector.create.chunk_count",
        "vector.update.attempt",
        "vector.update.success",
        "vector.update.duration_ms",
    }.issubset(observability["metric_names"])


def test_governance_block_records_observability(saga_crud: SagaDatabaseCRUD) -> None:
    aktenzeichen = "AKT-GOV"

    def deny(*_: Any, **__: Any) -> None:
        raise AdapterGovernanceError("Policy block")

    saga_crud._manager.ensure_operation_allowed = deny  # type: ignore[attr-defined]

    result = saga_crud.relational_create({"aktenzeichen": aktenzeichen, "title": "Gov Block"})

    assert not result.success
    assert result.data.get("governance_blocked") is True

    observability = collect_observability(saga_crud, aktenzeichen)

    assert "relational.create" in observability["stages"]
    assert "governance_blocked" in observability["statuses"]
    assert {
        "relational.create.attempt",
        "relational.create.success",
        "relational.create.error",
        "relational.create.governance_blocked",
    }.issubset(observability["metric_names"])


def test_relational_governance_forbidden_field(saga_crud: SagaDatabaseCRUD) -> None:
    aktenzeichen = "AKT-GOV-FIELD"
    payload = {
        "aktenzeichen": aktenzeichen,
        "title": "Forbidden Field",
        "raw_content": "vertraulich",
    }

    result = saga_crud.relational_create(payload)

    assert not result.success
    assert result.data.get("governance_blocked") is True
    assert "raw_content" in (result.error or "")

    observability = collect_observability(saga_crud, aktenzeichen)

    assert "relational.create" in observability["stages"]
    assert "governance_blocked" in observability["statuses"]
    assert {
        "relational.create.attempt",
        "relational.create.success",
        "relational.create.error",
        "relational.create.governance_blocked",
    }.issubset(observability["metric_names"])


def test_graph_crud_lifecycle(saga_crud: SagaDatabaseCRUD) -> None:
    aktenzeichen = "AKT-GRAPH"
    create = saga_crud.graph_create("doc-graph", {"title": "Graph Document", "aktenzeichen": aktenzeichen})
    assert create.success
    graph_id = create.data["graph_id"]

    read = saga_crud.graph_read(graph_id)
    assert read.success
    assert read.data["node"]["title"] == "Graph Document"

    update = saga_crud.graph_update(graph_id, {"title": "Updated", "aktenzeichen": aktenzeichen})
    assert update.success

    delete = saga_crud.graph_delete(graph_id)
    assert delete.success

    observability = collect_observability(saga_crud, aktenzeichen)
    assert {"graph.create", "graph.update", "graph.read"}.issubset(observability["stages"])
    assert {
        "graph.create.success",
        "graph.create.duration_ms",
        "graph.update.success",
    }.issubset(observability["metric_names"])


def test_relational_crud_lifecycle(saga_crud: SagaDatabaseCRUD) -> None:
    aktenzeichen = "AKT-REL"
    record = {
        "document_id": "doc-rel",
        "file_path": "/tmp/doc-rel.txt",
        "file_hash": "hash-rel",
        "title": "Rel Dokument",
        "language": "de",
        "aktenzeichen": aktenzeichen,
    }
    create = saga_crud.relational_create(record)
    assert create.success

    read = saga_crud.relational_read("doc-rel")
    assert read.success
    assert read.data["records"][0]["title"] == "Rel Dokument"

    update = saga_crud.relational_update("doc-rel", {"title": "Neu"})
    assert update.success

    delete = saga_crud.relational_delete("doc-rel")
    assert delete.success

    observability = collect_observability(saga_crud, aktenzeichen)
    assert "relational.create" in observability["stages"]
    assert {
        "relational.create.success",
        "relational.create.duration_ms",
    }.issubset(observability["metric_names"])


def test_file_crud_lifecycle(saga_crud: SagaDatabaseCRUD, tmp_path: Path) -> None:
    aktenzeichen = "AKT-FILE"
    file_path = tmp_path / "example.txt"
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write("Hallo Welt")

    create = saga_crud.file_create(
        "doc-file",
        source_path=str(file_path),
        metadata={"category": "test", "aktenzeichen": aktenzeichen},
    )
    assert create.success
    asset_id = create.data["asset_id"]

    read = saga_crud.file_read(asset_id)
    assert read.success
    assert os.path.exists(read.data["path"])

    delete = saga_crud.file_delete(asset_id)
    assert delete.success

    observability = collect_observability(saga_crud, aktenzeichen)
    assert "file.create" in observability["stages"]
    assert {
        "file.create.success",
        "file.create.duration_ms",
    }.issubset(observability["metric_names"])
