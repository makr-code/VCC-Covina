from typing import Protocol, Any, Dict, Optional
from uuid import UUID


class SagaCrudAdapter(Protocol):
    """Minimal protocol for a saga-style CRUD adapter used by `uds3_core`.

    Methods are intentionally small and synchronous for testability.
    Implementations may be async or use I/O in production.
    """

    def create(self, collection: str, document: Dict[str, Any]) -> Dict[str, Any]: ...

    def read(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]: ...

    def update(
        self, collection: str, document_id: str, patch: Dict[str, Any]
    ) -> Dict[str, Any]: ...

    def delete(self, collection: str, document_id: str) -> bool: ...


class IdentityAdapter(Protocol):
    """Protocol to generate and resolve identity UUIDs/keys."""

    def generate_uuid(self) -> UUID: ...

    def resolve(self, external_id: str) -> Optional[UUID]: ...


class InMemorySagaCrud:
    """A tiny in-memory adapter useful for unit tests and local runs."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def create(self, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        coll = self._store.setdefault(collection, {})
        doc_id = document.get("id") or document.get("_id") or str(len(coll) + 1)
        document = dict(document)
        document["id"] = doc_id
        coll[doc_id] = document
        return document

    def read(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(collection, {}).get(document_id)

    def update(
        self, collection: str, document_id: str, patch: Dict[str, Any]
    ) -> Dict[str, Any]:
        coll = self._store.setdefault(collection, {})
        if document_id not in coll:
            raise KeyError(document_id)
        coll[document_id].update(patch)
        return coll[document_id]

    def delete(self, collection: str, document_id: str) -> bool:
        coll = self._store.setdefault(collection, {})
        return coll.pop(document_id, None) is not None


__all__ = ["SagaCrudAdapter", "IdentityAdapter", "InMemorySagaCrud"]
