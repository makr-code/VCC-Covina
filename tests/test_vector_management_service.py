import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import pytest

from management_core.vector_management import (
    VectorChunkPayload,
    VectorCollectionDefinition,
    VectorManagementConfig,
    VectorManagementError,
    VectorManagementService,
)
from uds3.database.database_api_base import VectorDatabaseBackend


class FakeVectorBackend(VectorDatabaseBackend):
    def __init__(self):
        super().__init__({})
        self._collections = {}
        self._connected = True

    # Connection lifecycle -------------------------------------------------

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_available(self) -> bool:
        return self._connected

    def get_backend_type(self) -> str:
        return "fake-vector"

    # Collection management ------------------------------------------------

    def create_collection(self, name: str, metadata: dict | None = None) -> bool:
        self._collections.setdefault(name, {"metadata": metadata or {}, "vectors": {}})
        return True

    def get_collection(self, name: str):  # pragma: no cover - unused in tests
        return self._collections.get(name)

    def list_collections(self) -> list[str]:
        return list(self._collections.keys())

    # Vector operations ----------------------------------------------------

    def add_documents(self, collection_name: str, documents, metadatas, ids) -> bool:  # pragma: no cover - not used
        for idx, doc_id in enumerate(ids):
            self.create_collection(collection_name)
            self._collections[collection_name]["vectors"][doc_id] = {
                "document": documents[idx],
                "metadata": metadatas[idx],
            }
        return True

    def add_vector(self, vector_id: str, vector, metadata: dict | None = None) -> bool:
        metadata = metadata or {}
        collection = metadata.get("collection", "default")
        self.create_collection(collection)
        self._collections[collection]["vectors"][vector_id] = {
            "vector": list(vector),
            "metadata": metadata,
        }
        return True

    def search_similar(self, collection_name: str, query: str, n_results: int = 5):  # pragma: no cover - not used
        vectors = self._collections.get(collection_name, {}).get("vectors", {})
        return [
            {
                "id": vector_id,
                "metadata": entry["metadata"],
            }
            for vector_id, entry in list(vectors.items())[:n_results]
        ]

    def search_vectors(self, query_vector, top_k: int = 10, collection_name: str | None = None):  # pragma: no cover - not used
        collection = collection_name or next(iter(self._collections.keys()), None)
        if collection is None:
            return []
        vectors = self._collections.get(collection, {}).get("vectors", {})
        return [
            {
                "id": vector_id,
                "metadata": entry["metadata"],
            }
            for vector_id, entry in list(vectors.items())[:top_k]
        ]


@pytest.fixture()
def backend():
    return FakeVectorBackend()


def test_ingest_chunk_with_embedding_provider(backend):
    service = VectorManagementService(
        backend,
        config=VectorManagementConfig(enforce_vector_dimension=3),
        embedding_provider=lambda text: [1.0, float(len(text)), 3.0],
    )

    payload = VectorChunkPayload(
        document_id="doc-001",
        chunk_index=0,
        content="Hallo Verwaltung",
    )

    result = service.ingest_chunks([payload], collection="uds3_document_chunks")

    assert result.success
    assert "uds3_document_chunks" in backend._collections
    stored_vectors = backend._collections["uds3_document_chunks"]["vectors"]
    assert len(stored_vectors) == 1

    stored_metadata = next(iter(stored_vectors.values()))["metadata"]
    assert stored_metadata["document_id"] == "doc-001"
    assert stored_metadata["chunk_index"] == 0


def test_dynamic_collection_disabled_raises(backend):
    service = VectorManagementService(
        backend,
        config=VectorManagementConfig(allow_dynamic_collections=False, enforce_vector_dimension=1),
        embedding_provider=lambda text: [0.0],
    )

    payload = VectorChunkPayload(document_id="doc-002", chunk_index=0, content="Test")

    with pytest.raises(VectorManagementError):
        service.ingest_chunks([payload], collection="unregistered")


def test_hooks_modify_metadata(backend):
    service = VectorManagementService(
        backend,
        config=VectorManagementConfig(enforce_vector_dimension=1),
        embedding_provider=lambda text: [0.5],
    )

    service.register_collection(
        VectorCollectionDefinition(
            name="managed",
            metadata_template={"base": True},
        )
    )

    service.on_before_store(
        lambda payload, vector_id, metadata, embedding: (
            {**metadata, "custom_flag": "ok"},
            embedding,
        )
    )

    captured = {}

    def after_store(payload, vector_id, metadata):
        captured[vector_id] = metadata["custom_flag"]

    service.on_after_store(after_store)

    payload = VectorChunkPayload(document_id="doc-003", chunk_index=1, content="Test")
    result = service.ingest_chunks([payload], collection="managed")

    assert result.success
    assert len(captured) == 1
    assert next(iter(captured.values())) == "ok"