"""Vector management architecture for UDS3-based administrative services.

This module provides a generic, extensible management layer that sits on top of
`VectorDatabaseBackend` implementations. The goal is to offer a production-ready
baseline that can be extended or swapped without rewriting orchestration logic.
"""

from __future__ import annotations

import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from uds3.database.database_api_base import VectorDatabaseBackend

try:  # pragma: no cover - optional dependency
    from uds3 import UnifiedDatabaseStrategy as _UnifiedDatabaseStrategyType  # type: ignore
    UDS3_AVAILABLE = _UnifiedDatabaseStrategyType is not None
except Exception:  # pragma: no cover
    _UnifiedDatabaseStrategyType = None  # type: ignore
    UDS3_AVAILABLE = False

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from uds3 import UnifiedDatabaseStrategy as UnifiedDatabaseStrategyType  # type: ignore
else:  # Fallback to `Any` to avoid runtime dependency
    UnifiedDatabaseStrategyType = Any


logger = logging.getLogger(__name__)


class VectorManagementError(RuntimeError):
    """Domain-specific error raised by the vector management layer."""


@dataclass(frozen=True)
class VectorManagementConfig:
    """Configuration knobs for the vector management layer."""

    default_collection: str = "uds3_document_chunks"
    auto_create_collections: bool = True
    allow_dynamic_collections: bool = True
    enforce_vector_dimension: Optional[int] = None
    metadata_overrides: Dict[str, Any] = field(default_factory=dict)
    use_strategy_metadata: bool = True


@dataclass
class VectorCollectionDefinition:
    """Describes a managed vector collection and its baseline metadata."""

    name: str
    description: str = ""
    metadata_template: Dict[str, Any] = field(default_factory=dict)
    vector_dimension: Optional[int] = None
    lifecycle_stage: str = "active"
    retain_history: bool = True

    def to_metadata(self) -> Dict[str, Any]:
        metadata = {
            "collection": self.name,
            "description": self.description or f"Collection {self.name}",
            "lifecycle_stage": self.lifecycle_stage,
            "retain_history": self.retain_history,
        }
        metadata.update(self.metadata_template)
        return metadata


@dataclass
class VectorChunkPayload:
    """Payload representing a chunk or summary that should be indexed."""

    document_id: str
    chunk_index: int
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    collection: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StoredVectorRecord:
    """Represents a successfully persisted vector."""

    vector_id: str
    metadata: Dict[str, Any]
    backend_reference: Optional[Any] = None


@dataclass
class VectorIngestResult:
    """Result bundle returned after an ingest operation."""

    collection: str
    stored: List[StoredVectorRecord]
    failed: List[Tuple[VectorChunkPayload, str]]
    duration_seconds: float

    @property
    def success(self) -> bool:
        return not self.failed


BeforeStoreHook = Callable[[VectorChunkPayload, str, Dict[str, Any], List[float]], Tuple[Dict[str, Any], List[float]]]
AfterStoreHook = Callable[[VectorChunkPayload, str, Dict[str, Any]], None]
FailureHook = Callable[[VectorChunkPayload, str, str], None]


class VectorLifecycleHooks:
    """Container for lifecycle hooks around vector persistence."""

    def __init__(self) -> None:
        self._before_store: List[BeforeStoreHook] = []
        self._after_store: List[AfterStoreHook] = []
        self._on_failure: List[FailureHook] = []

    def register_before_store(self, hook: BeforeStoreHook) -> None:
        self._before_store.append(hook)

    def register_after_store(self, hook: AfterStoreHook) -> None:
        self._after_store.append(hook)

    def register_failure_hook(self, hook: FailureHook) -> None:
        self._on_failure.append(hook)

    def run_before_store(
        self,
        payload: VectorChunkPayload,
        vector_id: str,
        metadata: Dict[str, Any],
        embedding: List[float],
    ) -> Tuple[Dict[str, Any], List[float]]:
        current_metadata, current_embedding = metadata, embedding
        for hook in self._before_store:
            try:
                current_metadata, current_embedding = hook(payload, vector_id, current_metadata, current_embedding)
            except Exception as exc:  # pragma: no cover - hook failures should not crash core logic
                logger.warning("Before-store hook failed for %s: %s", vector_id, exc)
        return current_metadata, current_embedding

    def run_after_store(
        self,
        payload: VectorChunkPayload,
        vector_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        for hook in self._after_store:
            try:
                hook(payload, vector_id, metadata)
            except Exception as exc:  # pragma: no cover
                logger.warning("After-store hook failed for %s: %s", vector_id, exc)

    def run_failure_hooks(self, payload: VectorChunkPayload, vector_id: str, reason: str) -> None:
        for hook in self._on_failure:
            try:
                hook(payload, vector_id, reason)
            except Exception as exc:  # pragma: no cover
                logger.warning("Failure hook failed for %s: %s", vector_id, exc)


class VectorManagementService:
    """High-level management layer for vector backends.

    Responsibilities:
        * Maintain collection metadata & lifecycle policies.
        * Provide a stable entry point for ingest/search operations.
        * Decorate metadata with UDS3 strategy insights when available.
        * Offer lifecycle hooks so future phases can customise behaviour.
    """

    def __init__(
        self,
        backend: VectorDatabaseBackend,
        *,
        config: Optional[VectorManagementConfig] = None,
    strategy: Optional["UnifiedDatabaseStrategyType"] = None,
        embedding_provider: Optional[Callable[[str], List[float]]] = None,
    ) -> None:
        self._backend = backend
        self._config = config or VectorManagementConfig()
        if strategy is not None:
            self._strategy: Optional[UnifiedDatabaseStrategyType] = strategy
        elif UDS3_AVAILABLE and _UnifiedDatabaseStrategyType is not None:
            self._strategy = _UnifiedDatabaseStrategyType()
        else:
            self._strategy = None
        self._embedding_provider = embedding_provider
        self._collections: Dict[str, VectorCollectionDefinition] = {}
        self.hooks = VectorLifecycleHooks()

        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Collection Management

    def register_collection(self, definition: VectorCollectionDefinition) -> None:
        """Register a collection definition and ensure it exists if configured."""
        self._collections[definition.name] = definition
        self.logger.debug("Registered collection definition %s", definition.name)
        if self._config.auto_create_collections:
            created = self._backend.create_collection(definition.name, metadata=definition.to_metadata())
            if not created:
                raise VectorManagementError(f"Collection '{definition.name}' could not be created")

    def ensure_collection(self, collection_name: str) -> VectorCollectionDefinition:
        """Return a collection definition, creating a default one if permitted."""
        definition = self._collections.get(collection_name)
        if definition is None:
            if not self._config.allow_dynamic_collections:
                raise VectorManagementError(f"Collection '{collection_name}' is not registered and dynamic creation is disabled")
            definition = VectorCollectionDefinition(
                name=collection_name,
                description=f"Dynamic collection {collection_name}",
                metadata_template={"created_dynamic": True},
            )
            self.register_collection(definition)
        return definition

    def list_registered_collections(self) -> List[str]:
        return list(self._collections.keys())

    # ------------------------------------------------------------------
    # Ingest Pipeline

    def ingest_chunks(
        self,
        chunks: Sequence[VectorChunkPayload],
        *,
        collection: Optional[str] = None,
    ) -> VectorIngestResult:
        if not chunks:
            raise VectorManagementError("No chunks provided for ingest")

        target_collection = collection or chunks[0].collection or self._config.default_collection
        definition = self.ensure_collection(target_collection)

        stored: List[StoredVectorRecord] = []
        failed: List[Tuple[VectorChunkPayload, str]] = []
        start = time.perf_counter()

        for chunk in chunks:
            vector_id, metadata, embedding = self._prepare_chunk(chunk, definition, target_collection)
            metadata, embedding = self.hooks.run_before_store(chunk, vector_id, metadata, embedding)

            try:
                success = self._backend.add_vector(vector_id, embedding, metadata)
            except Exception as exc:  # pragma: no cover - backend level failure
                reason = f"backend raised exception: {exc}"
                self.logger.error("Failed to persist vector %s: %s", vector_id, reason)
                failed.append((chunk, reason))
                self.hooks.run_failure_hooks(chunk, vector_id, reason)
                continue

            if not success:
                reason = "backend returned False"
                self.logger.warning("Vector backend rejected %s", vector_id)
                failed.append((chunk, reason))
                self.hooks.run_failure_hooks(chunk, vector_id, reason)
                continue

            record = StoredVectorRecord(vector_id=vector_id, metadata=metadata)
            stored.append(record)
            self.hooks.run_after_store(chunk, vector_id, metadata)

        duration = time.perf_counter() - start
        return VectorIngestResult(collection=target_collection, stored=stored, failed=failed, duration_seconds=duration)

    # ------------------------------------------------------------------
    # Search & Utility

    def search(self, query: str, *, collection: Optional[str] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        target_collection = collection or self._config.default_collection
        return self._backend.search_similar(target_collection, query, n_results=top_k)

    def describe_collections(self) -> List[Dict[str, Any]]:
        descriptions = []
        for name in self._backend.list_collections():
            definition = self._collections.get(name)
            descriptions.append(
                {
                    "name": name,
                    "registered": definition is not None,
                    "metadata": definition.to_metadata() if definition else None,
                }
            )
        return descriptions

    # ------------------------------------------------------------------
    # Internal helpers

    def _prepare_chunk(
        self,
        payload: VectorChunkPayload,
        definition: VectorCollectionDefinition,
        collection_name: str,
    ) -> Tuple[str, Dict[str, Any], List[float]]:
        metadata = self._build_metadata(payload, definition, collection_name)
        embedding = self._resolve_embedding(payload)
        self._validate_embedding(embedding, definition)
        vector_id = self._build_vector_id(payload, metadata)
        metadata["vector_id"] = vector_id
        metadata.setdefault("collection", collection_name)
        metadata.setdefault("document_id", payload.document_id)
        metadata.setdefault("chunk_index", payload.chunk_index)
        metadata.setdefault("created_at", payload.created_at.isoformat())
        metadata.update(self._config.metadata_overrides)
        return vector_id, metadata, embedding

    def _build_metadata(
        self,
        payload: VectorChunkPayload,
        definition: VectorCollectionDefinition,
        collection_name: str,
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        metadata.update(definition.metadata_template)
        metadata.update(payload.metadata)
        metadata.setdefault("content_preview", payload.content[:280])
        metadata.setdefault("lifecycle_stage", definition.lifecycle_stage)
        metadata.setdefault("collection", collection_name)

        if self._strategy and self._config.use_strategy_metadata:
            strategy_metadata = self._call_strategy_metadata(payload)
            metadata.update({k: v for k, v in strategy_metadata.items() if k not in metadata})

        return metadata

    def _call_strategy_metadata(self, payload: VectorChunkPayload) -> Dict[str, Any]:
        if not self._strategy:
            return {}

        strategy_metadata: Dict[str, Any] = {}
        if hasattr(self._strategy, "create_chunk_properties"):
            try:
                strategy_metadata = self._strategy.create_chunk_properties(  # type: ignore[arg-type]
                    document_id=payload.document_id,
                    chunk_index=payload.chunk_index,
                    content=payload.content,
                    **payload.metadata,
                )
            except Exception as exc:  # pragma: no cover - defensive fall-back
                self.logger.debug("Strategy chunk metadata failed: %s", exc)
        return strategy_metadata or {}

    def _resolve_embedding(self, payload: VectorChunkPayload) -> List[float]:
        if payload.embedding is not None:
            return list(payload.embedding)
        if not self._embedding_provider:
            raise VectorManagementError(
                "No embedding provided and no embedding_provider configured; cannot continue"
            )
        embedding = self._embedding_provider(payload.content)
        if embedding is None:
            raise VectorManagementError("Embedding provider returned None")
        return list(embedding)

    def _validate_embedding(
        self,
        embedding: Sequence[float],
        definition: VectorCollectionDefinition,
    ) -> None:
        if not embedding:
            raise VectorManagementError("Embedding is empty")
        if not all(isinstance(value, (int, float)) for value in embedding):
            raise VectorManagementError("Embedding must contain numeric values")

        expected = self._config.enforce_vector_dimension or definition.vector_dimension
        if expected is not None and len(embedding) != expected:
            raise VectorManagementError(
                f"Embedding dimension mismatch: expected {expected}, got {len(embedding)}"
            )

    def _build_vector_id(self, payload: VectorChunkPayload, metadata: Dict[str, Any]) -> str:
        if "vector_id" in metadata and metadata["vector_id"]:
            return str(metadata["vector_id"])

        # Try to leverage UDS3 strategy id generation
        if self._strategy:
            if hasattr(self._strategy, "create_chunk_properties"):
                try:
                    strategy_props = self._strategy.create_chunk_properties(  # type: ignore[arg-type]
                        document_id=payload.document_id,
                        chunk_index=payload.chunk_index,
                        content=payload.content,
                        **payload.metadata,
                    )
                    for key in ("id", "chunk_id", "vector_id"):
                        if strategy_props.get(key):
                            return str(strategy_props[key])
                except Exception as exc:  # pragma: no cover
                    self.logger.debug("Strategy id generation failed: %s", exc)

        return f"{payload.document_id}::{payload.chunk_index}::{uuid.uuid4()}"

    # ------------------------------------------------------------------
    # Hook registration convenience wrappers

    def on_before_store(self, hook: BeforeStoreHook) -> None:
        self.hooks.register_before_store(hook)

    def on_after_store(self, hook: AfterStoreHook) -> None:
        self.hooks.register_after_store(hook)

    def on_failure(self, hook: FailureHook) -> None:
        self.hooks.register_failure_hook(hook)


__all__ = [
    "VectorManagementService",
    "VectorManagementConfig",
    "VectorCollectionDefinition",
    "VectorChunkPayload",
    "VectorIngestResult",
    "StoredVectorRecord",
    "VectorManagementError",
    "VectorLifecycleHooks",
]
