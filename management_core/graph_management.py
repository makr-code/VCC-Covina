"""Graph management architecture for UDS3 administrative services.

This module introduces a management layer around :class:`GraphDatabaseBackend`
implementations. It mirrors the intent of :mod:`vector_management` by offering
configuration, lifecycle hooks and high-level helpers for node and relationship
operations while remaining backend-agnostic.
"""

from __future__ import annotations

import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from uds3.database.database_api_base import GraphDatabaseBackend

try:  # pragma: no cover - optional dependency
	from uds3 import UnifiedDatabaseStrategy as _UnifiedDatabaseStrategyType  # type: ignore
	UDS3_AVAILABLE = _UnifiedDatabaseStrategyType is not None
except Exception:  # pragma: no cover
	_UnifiedDatabaseStrategyType = None  # type: ignore
	UDS3_AVAILABLE = False

if UDS3_AVAILABLE:  # pragma: no cover - typing helper
	from uds3 import UnifiedDatabaseStrategy as UnifiedDatabaseStrategyType  # type: ignore
else:  # pragma: no cover
	UnifiedDatabaseStrategyType = Any


logger = logging.getLogger(__name__)


class GraphManagementError(RuntimeError):
	"""Domain-specific error raised by the graph management layer."""


@dataclass(frozen=True)
class GraphManagementConfig:
	"""Configuration knobs for the graph management layer."""

	default_node_type: str = "Document"
	allow_dynamic_node_types: bool = True
	allow_dynamic_relationships: bool = True
	enforce_relationship_direction: bool = True
	default_relationship_type: str = "RELATED_TO"
	use_strategy_metadata: bool = True


@dataclass
class GraphNodeTypeDefinition:
	"""Definition describing a managed node type."""

	name: str
	description: str = ""
	required_properties: Dict[str, Any] = field(default_factory=dict)
	optional_properties: Dict[str, Any] = field(default_factory=dict)
	metadata_template: Dict[str, Any] = field(default_factory=dict)

	def apply_defaults(self, properties: Dict[str, Any]) -> Dict[str, Any]:
		merged = {**self.optional_properties, **properties}
		missing = set(self.required_properties) - set(merged)
		if missing:
			raise GraphManagementError(f"Missing required properties {sorted(missing)} for node type '{self.name}'")
		for key, value in self.required_properties.items():
			merged.setdefault(key, value)
		return merged


@dataclass
class GraphRelationshipDefinition:
	"""Definition describing a managed relationship type."""

	name: str
	from_type: str
	to_type: str
	description: str = ""
	required_properties: Dict[str, Any] = field(default_factory=dict)
	optional_properties: Dict[str, Any] = field(default_factory=dict)
	metadata_template: Dict[str, Any] = field(default_factory=dict)

	def apply_defaults(self, properties: Dict[str, Any]) -> Dict[str, Any]:
		merged = {**self.optional_properties, **properties}
		missing = set(self.required_properties) - set(merged)
		if missing:
			raise GraphManagementError(
				f"Missing required properties {sorted(missing)} for relationship type '{self.name}'"
			)
		for key, value in self.required_properties.items():
			merged.setdefault(key, value)
		return merged


@dataclass
class GraphNodePayload:
	"""Payload representing a node that should exist in the graph."""

	node_type: Optional[str] = None
	properties: Dict[str, Any] = field(default_factory=dict)
	metadata: Dict[str, Any] = field(default_factory=dict)
	external_id: Optional[str] = None
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GraphRelationshipPayload:
	"""Payload describing a relationship to create between two nodes."""

	source_id: str
	target_id: str
	relationship_type: Optional[str] = None
	properties: Dict[str, Any] = field(default_factory=dict)
	metadata: Dict[str, Any] = field(default_factory=dict)
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StoredGraphNode:
	"""Represents a successfully persisted node."""

	node_id: str
	node_type: str
	properties: Dict[str, Any]


@dataclass
class StoredGraphRelationship:
	"""Represents a successfully persisted relationship."""

	relationship_id: str
	relationship_type: str
	properties: Dict[str, Any]
	source_id: str
	target_id: str


@dataclass
class GraphMutationResult:
	"""Result bundle capturing node and relationship mutations."""

	nodes: List[StoredGraphNode] = field(default_factory=list)
	relationships: List[StoredGraphRelationship] = field(default_factory=list)
	failed_nodes: List[Tuple[GraphNodePayload, str]] = field(default_factory=list)
	failed_relationships: List[Tuple[GraphRelationshipPayload, str]] = field(default_factory=list)

	@property
	def success(self) -> bool:
		return not self.failed_nodes and not self.failed_relationships


NodeBeforeHook = Callable[[GraphNodePayload, Dict[str, Any]], Dict[str, Any]]
NodeAfterHook = Callable[[GraphNodePayload, StoredGraphNode], None]
NodeFailureHook = Callable[[GraphNodePayload, str], None]

RelationshipBeforeHook = Callable[[GraphRelationshipPayload, Dict[str, Any]], Dict[str, Any]]
RelationshipAfterHook = Callable[[GraphRelationshipPayload, StoredGraphRelationship], None]
RelationshipFailureHook = Callable[[GraphRelationshipPayload, str], None]


class GraphLifecycleHooks:
	"""Container for lifecycle hooks executed during graph mutations."""

	def __init__(self) -> None:
		self._before_node: List[NodeBeforeHook] = []
		self._after_node: List[NodeAfterHook] = []
		self._on_node_failure: List[NodeFailureHook] = []
		self._before_relationship: List[RelationshipBeforeHook] = []
		self._after_relationship: List[RelationshipAfterHook] = []
		self._on_relationship_failure: List[RelationshipFailureHook] = []

	def register_before_node(self, hook: NodeBeforeHook) -> None:
		self._before_node.append(hook)

	def register_after_node(self, hook: NodeAfterHook) -> None:
		self._after_node.append(hook)

	def register_node_failure(self, hook: NodeFailureHook) -> None:
		self._on_node_failure.append(hook)

	def register_before_relationship(self, hook: RelationshipBeforeHook) -> None:
		self._before_relationship.append(hook)

	def register_after_relationship(self, hook: RelationshipAfterHook) -> None:
		self._after_relationship.append(hook)

	def register_relationship_failure(self, hook: RelationshipFailureHook) -> None:
		self._on_relationship_failure.append(hook)

	def before_node(self, payload: GraphNodePayload, properties: Dict[str, Any]) -> Dict[str, Any]:
		current = properties
		for hook in self._before_node:
			try:
				current = hook(payload, current)
			except Exception as exc:  # pragma: no cover - hook errors should not abort flow
				logger.warning("Graph before_node hook failed: %s", exc)
		return current

	def after_node(self, payload: GraphNodePayload, node: StoredGraphNode) -> None:
		for hook in self._after_node:
			try:
				hook(payload, node)
			except Exception as exc:  # pragma: no cover
				logger.warning("Graph after_node hook failed: %s", exc)

	def node_failure(self, payload: GraphNodePayload, reason: str) -> None:
		for hook in self._on_node_failure:
			try:
				hook(payload, reason)
			except Exception as exc:  # pragma: no cover
				logger.warning("Graph node_failure hook failed: %s", exc)

	def before_relationship(self, payload: GraphRelationshipPayload, properties: Dict[str, Any]) -> Dict[str, Any]:
		current = properties
		for hook in self._before_relationship:
			try:
				current = hook(payload, current)
			except Exception as exc:  # pragma: no cover
				logger.warning("Graph before_relationship hook failed: %s", exc)
		return current

	def after_relationship(self, payload: GraphRelationshipPayload, relationship: StoredGraphRelationship) -> None:
		for hook in self._after_relationship:
			try:
				hook(payload, relationship)
			except Exception as exc:  # pragma: no cover
				logger.warning("Graph after_relationship hook failed: %s", exc)

	def relationship_failure(self, payload: GraphRelationshipPayload, reason: str) -> None:
		for hook in self._on_relationship_failure:
			try:
				hook(payload, reason)
			except Exception as exc:  # pragma: no cover
				logger.warning("Graph relationship_failure hook failed: %s", exc)


class GraphManagementService:
	"""High-level management layer for graph backends."""

	def __init__(
		self,
		backend: GraphDatabaseBackend,
		*,
		config: Optional[GraphManagementConfig] = None,
		strategy: Optional["UnifiedDatabaseStrategyType"] = None,
	) -> None:
		self._backend = backend
		self._config = config or GraphManagementConfig()
		if strategy is not None:
			self._strategy: Optional[UnifiedDatabaseStrategyType] = strategy
		elif UDS3_AVAILABLE and _UnifiedDatabaseStrategyType is not None:
			self._strategy = _UnifiedDatabaseStrategyType()
		else:
			self._strategy = None

		self._node_types: Dict[str, GraphNodeTypeDefinition] = {}
		self._relationship_types: Dict[str, GraphRelationshipDefinition] = {}
		self.hooks = GraphLifecycleHooks()
		self.logger = logging.getLogger(self.__class__.__name__)

	# ------------------------------------------------------------------
	# Node definition management

	def register_node_type(self, definition: GraphNodeTypeDefinition) -> None:
		self._node_types[definition.name] = definition
		ensure_method = getattr(self._backend, "ensure_node_schema", None)
		if callable(ensure_method):  # pragma: no cover - depends on backend implementation
			ensure_method(definition.name, definition.required_properties, definition.optional_properties)

	def ensure_node_type(self, node_type: Optional[str]) -> GraphNodeTypeDefinition:
		effective_type = node_type or self._config.default_node_type
		definition = self._node_types.get(effective_type)
		if definition is None:
			if not self._config.allow_dynamic_node_types:
				raise GraphManagementError(f"Node type '{effective_type}' is not registered and dynamic creation is disabled")
			definition = GraphNodeTypeDefinition(name=effective_type, metadata_template={"created_dynamic": True})
			self.register_node_type(definition)
		return definition

	def list_registered_node_types(self) -> List[str]:
		return list(self._node_types.keys())

	# ------------------------------------------------------------------
	# Relationship definition management

	def register_relationship_type(self, definition: GraphRelationshipDefinition) -> None:
		self._relationship_types[definition.name] = definition
		ensure_method = getattr(self._backend, "ensure_relationship_schema", None)
		if callable(ensure_method):  # pragma: no cover - backend dependent
			ensure_method(
				definition.name,
				definition.from_type,
				definition.to_type,
				definition.required_properties,
				definition.optional_properties,
			)

	def ensure_relationship_type(self, relationship_type: Optional[str]) -> GraphRelationshipDefinition:
		effective_type = relationship_type or self._config.default_relationship_type
		definition = self._relationship_types.get(effective_type)
		if definition is None:
			if not self._config.allow_dynamic_relationships:
				raise GraphManagementError(
					f"Relationship type '{effective_type}' is not registered and dynamic creation is disabled"
				)
			definition = GraphRelationshipDefinition(
				name=effective_type,
				from_type=self._config.default_node_type,
				to_type=self._config.default_node_type,
				metadata_template={"created_dynamic": True},
			)
			self.register_relationship_type(definition)
		return definition

	def list_registered_relationship_types(self) -> List[str]:
		return list(self._relationship_types.keys())

	# ------------------------------------------------------------------
	# Mutation operations

	def upsert_nodes(self, payloads: Sequence[GraphNodePayload]) -> GraphMutationResult:
		if not payloads:
			raise GraphManagementError("No node payloads provided")

		result = GraphMutationResult()
		for payload in payloads:
			definition = self.ensure_node_type(payload.node_type)
			properties = self._build_node_properties(payload, definition)
			try:
				properties = self.hooks.before_node(payload, properties)
				node_id = self._backend.create_node(definition.name, properties)
			except Exception as exc:  # pragma: no cover - backend failure
				reason = f"backend error: {exc}"
				self.logger.error("Failed to persist node (%s): %s", definition.name, reason)
				result.failed_nodes.append((payload, reason))
				self.hooks.node_failure(payload, reason)
				continue

			stored = StoredGraphNode(node_id=node_id, node_type=definition.name, properties=properties)
			result.nodes.append(stored)
			self.hooks.after_node(payload, stored)

		return result

	def upsert_relationships(self, payloads: Sequence[GraphRelationshipPayload]) -> GraphMutationResult:
		if not payloads:
			raise GraphManagementError("No relationship payloads provided")

		result = GraphMutationResult()
		for payload in payloads:
			definition = self.ensure_relationship_type(payload.relationship_type)
			if self._config.enforce_relationship_direction:
				self._validate_relationship_direction(payload, definition)
			properties = self._build_relationship_properties(payload, definition)
			try:
				properties = self.hooks.before_relationship(payload, properties)
				rel_id = self._backend.create_edge(payload.source_id, payload.target_id, definition.name, properties)
			except Exception as exc:  # pragma: no cover
				reason = f"backend error: {exc}"
				self.logger.error(
					"Failed to persist relationship (%s -> %s %s): %s",
					payload.source_id,
					definition.name,
					payload.target_id,
					reason,
				)
				result.failed_relationships.append((payload, reason))
				self.hooks.relationship_failure(payload, reason)
				continue

			stored = StoredGraphRelationship(
				relationship_id=rel_id,
				relationship_type=definition.name,
				properties=properties,
				source_id=payload.source_id,
				target_id=payload.target_id,
			)
			result.relationships.append(stored)
			self.hooks.after_relationship(payload, stored)

		return result

	# ------------------------------------------------------------------
	# Internal helpers

	def _build_node_properties(
		self,
		payload: GraphNodePayload,
		definition: GraphNodeTypeDefinition,
	) -> Dict[str, Any]:
		properties = dict(payload.properties)
		properties.update(definition.metadata_template)
		properties.update(payload.metadata)
		properties.setdefault("created_at", payload.created_at.isoformat())
		if payload.external_id:
			properties.setdefault("external_id", payload.external_id)

		if self._strategy and self._config.use_strategy_metadata:
			properties.update(self._strategy_metadata(payload, definition))

		properties = definition.apply_defaults(properties)
		if "node_id" not in properties:
			properties.setdefault("node_id", str(uuid.uuid4()))
		return properties

	def _build_relationship_properties(
		self,
		payload: GraphRelationshipPayload,
		definition: GraphRelationshipDefinition,
	) -> Dict[str, Any]:
		properties = dict(payload.properties)
		properties.update(definition.metadata_template)
		properties.update(payload.metadata)
		properties.setdefault("created_at", payload.created_at.isoformat())
		properties = definition.apply_defaults(properties)
		properties.setdefault("relationship_id", str(uuid.uuid4()))
		return properties

	def _strategy_metadata(
		self,
		payload: GraphNodePayload,
		definition: GraphNodeTypeDefinition,
	) -> Dict[str, Any]:
		if not self._strategy:
			return {}

		metadata: Dict[str, Any] = {}
		if hasattr(self._strategy, "enhance_graph_node"):
			try:
				metadata = self._strategy.enhance_graph_node(  # type: ignore[attr-defined]
					node_type=definition.name,
					properties=payload.properties,
					metadata=payload.metadata,
				)
			except Exception as exc:  # pragma: no cover
				self.logger.debug("Strategy graph node metadata failed: %s", exc)
		return metadata or {}

	def _validate_relationship_direction(
		self,
		payload: GraphRelationshipPayload,
		definition: GraphRelationshipDefinition,
	) -> None:
		# Some backends may not expose node inspection APIs; we only validate availability of IDs.
		if not payload.source_id or not payload.target_id:
			raise GraphManagementError("Relationship payload requires both source_id and target_id")

	# ------------------------------------------------------------------
	# Discovery helpers

	def describe_topology(self) -> Dict[str, Iterable[str]]:
		return {
			"node_types": self.list_registered_node_types(),
			"relationship_types": self.list_registered_relationship_types(),
		}

