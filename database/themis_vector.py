"""
Themis Vector Backend

Implements ChromaDB-like vector operations on top of Themis HTTP API.

Author: VCC Covina Team
Created: 2025-11-07
Version: 0.1.0
"""
from __future__ import annotations

import json
from typing import Optional, List, Dict, Any

from .themis_adapter import ThemisAdapter
from .themis_exceptions import (
    create_vector_error,
    ThemisNotFoundError,
)


class ThemisVectorBackend:
    """Vector Backend for Themis (ChromaDB → Themis Vector Index)

    Provides UDS3/ChromaDB compatible methods:
    - add(ids, embeddings, metadatas=None, documents=None)
    - query(query_embeddings, n_results=10, where=None, include_metadata=True, include_documents=True)
    - delete(ids)
    """

    def __init__(self, adapter: ThemisAdapter):
        self.adapter = adapter
        self.client = adapter  # use adapter's retry-enabled methods
        self.logger = adapter.logger
        self._expected_dim: Optional[int] = None

    # ---------------------------------------------------------------------
    # Public API (ChromaDB compatible)
    # ---------------------------------------------------------------------
    async def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        validate_dimensions: bool = True,
    ) -> Dict[str, Any]:
        """
        Add vectors to Themis index.

        Args:
            ids: Unique document/vector IDs
            embeddings: List of vector embeddings (uniform dimension)
            metadatas: Optional metadata dicts per item
            documents: Optional raw text document contents
            validate_dimensions: Enforce consistent dimension across batch

        Returns:
            Result dictionary from Themis response.
        """
        if len(ids) != len(embeddings):
            raise create_vector_error(
                "Length mismatch: ids vs embeddings",
                expected_dim=len(ids),
                actual_dim=len(embeddings),
            )
        if metadatas and len(metadatas) != len(ids):
            raise create_vector_error("Length mismatch: metadatas vs ids")
        if documents and len(documents) != len(ids):
            raise create_vector_error("Length mismatch: documents vs ids")

        if validate_dimensions:
            self._validate_and_set_dimension(embeddings)

        metadatas = metadatas or [{} for _ in ids]
        documents = documents or ["" for _ in ids]

        items = []
        for pk, vector, metadata, doc in zip(ids, embeddings, metadatas, documents):
            combined_fields = dict(metadata)
            if doc:
                combined_fields["text"] = doc
            items.append({
                "pk": pk,
                "vector": vector,
                "fields": combined_fields,
            })

        response = await self.client.post(
            "/vector/batch_insert",
            json={
                "vector_field": "embedding",
                "items": items,
            },
        )
        data = response.json()
        return data

    async def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_documents: bool = True,
        validate_dimensions: bool = True,
    ) -> Dict[str, Any]:
        """
        Query similar vectors.

        Returns a ChromaDB-compatible structure:
        {
            "ids": [[... per query]],
            "distances": [[... per query]],
            "metadatas": [[{...} per hit] per query],
            "documents": [["text" per hit] per query]
        }
        """
        if validate_dimensions and self._expected_dim is not None:
            for qv in query_embeddings:
                if len(qv) != self._expected_dim:
                    raise create_vector_error(
                        "Query vector dimension mismatch",
                        expected_dim=self._expected_dim,
                        actual_dim=len(qv),
                    )

        results: Dict[str, List] = {
            "ids": [],
            "distances": [],
            "metadatas": [],
            "documents": [],
        }

        for qv in query_embeddings:
            payload = {
                "vector": qv,
                "k": n_results,
            }
            # Optional filter support (if Themis adds it later)
            if where:
                payload["filter"] = where

            response = await self.client.post("/vector/search", json=payload)
            data = response.json()
            hits = data.get("results", [])

            ids_batch = [hit.get("pk") for hit in hits]
            dist_batch = [hit.get("distance") for hit in hits]
            metadata_batch: List[Dict[str, Any]] = []
            doc_batch: List[str] = []

            if include_metadata or include_documents:
                for pk in ids_batch:
                    entity = await self._fetch_entity(pk)
                    if entity is None:
                        metadata_batch.append({})
                        doc_batch.append("")
                        continue
                    metadata_batch.append(entity if include_metadata else {})
                    doc_batch.append(entity.get("text", "") if include_documents else "")

            results["ids"].append(ids_batch)
            results["distances"].append(dist_batch)
            results["metadatas"].append(metadata_batch)
            results["documents"].append(doc_batch)

        return results

    async def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        if not ids:
            return True
        response = await self.client.delete(
            "/vector/by-filter",
            json={"pks": ids},
        )
        return response.status_code == 200

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _validate_and_set_dimension(self, embeddings: List[List[float]]) -> None:
        if not embeddings:
            return
        dim = len(embeddings[0])
        if self._expected_dim is None:
            self._expected_dim = dim
        for vec in embeddings:
            if len(vec) != dim:
                raise create_vector_error(
                    "Inconsistent embedding dimensions in batch",
                    expected_dim=dim,
                    actual_dim=len(vec),
                )

    async def _fetch_entity(self, pk: str) -> Optional[Dict[str, Any]]:
        response = await self.client.get(f"/entities/{pk}")
        if response.status_code == 404:
            return None
        data = response.json()
        blob = data.get("blob")
        try:
            return json.loads(blob) if blob else {}
        except json.JSONDecodeError:
            return {}

    # ---------------------------------------------------------------------
    # Diagnostics
    # ---------------------------------------------------------------------
    @property
    def expected_dimension(self) -> Optional[int]:
        return self._expected_dim

    def reset_dimension(self) -> None:
        self._expected_dim = None

__all__ = ["ThemisVectorBackend"]
