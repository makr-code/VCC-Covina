"""Relational management architecture inspired by the vector management layer."""

from __future__ import annotations

import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from uds3.database.database_api_base import RelationalDatabaseBackend

try:  # pragma: no cover - optional dependency
	from uds3 import UnifiedDatabaseStrategy as _UnifiedDatabaseStrategyType  # type: ignore
	UDS3_AVAILABLE = _UnifiedDatabaseStrategyType is not None
except Exception:  # pragma: no cover
	_UnifiedDatabaseStrategyType = None  # type: ignore
	UDS3_AVAILABLE = False

if TYPE_CHECKING:  # pragma: no cover - typing helper
	from uds3 import UnifiedDatabaseStrategy as UnifiedDatabaseStrategyType  # type: ignore
else:  # Fallback at runtime
	UnifiedDatabaseStrategyType = Any


logger = logging.getLogger(__name__)


class RelationalManagementError(RuntimeError):
	"""Raised when relational management operations fail."""


@dataclass(frozen=True)
class RelationalManagementConfig:
	"""Configuration knobs for relational management."""

	default_schema: Optional[str] = None
	allow_dynamic_tables: bool = True
	enforce_required_columns: bool = True
	use_strategy_metadata: bool = True


@dataclass
class RelationalTableDefinition:
	"""Definition of a managed relational table."""

	name: str
	schema: Dict[str, Any] = field(default_factory=dict)
	required_columns: Iterable[str] = field(default_factory=set)
	default_values: Dict[str, Any] = field(default_factory=dict)
	metadata_template: Dict[str, Any] = field(default_factory=dict)

	def apply_defaults(self, record: Dict[str, Any], *, enforce_required: bool) -> Dict[str, Any]:
		merged = {**self.default_values, **record}
		if enforce_required:
			missing = set(self.required_columns) - set(merged)
			if missing:
				raise RelationalManagementError(
					f"Missing required columns {sorted(missing)} for table '{self.name}'"
				)
		return merged


@dataclass
class RelationalRecordPayload:
	"""Payload representing a record to insert or update."""

	table: Optional[str]
	data: Dict[str, Any] = field(default_factory=dict)
	metadata: Dict[str, Any] = field(default_factory=dict)
	record_id: Optional[Any] = None
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StoredRelationalRecord:
	"""Represents a successfully stored relational record."""

	table: str
	record_id: Any
	data: Dict[str, Any]


@dataclass
class RelationalMutationResult:
	"""Result bundle for relational operations."""

	inserted: List[StoredRelationalRecord] = field(default_factory=list)
	updated: List[StoredRelationalRecord] = field(default_factory=list)
	failed_inserts: List[Tuple[RelationalRecordPayload, str]] = field(default_factory=list)
	failed_updates: List[Tuple[RelationalRecordPayload, str]] = field(default_factory=list)

	@property
	def success(self) -> bool:
		return not self.failed_inserts and not self.failed_updates


BeforeInsertHook = Callable[[RelationalRecordPayload, Dict[str, Any]], Dict[str, Any]]
AfterInsertHook = Callable[[RelationalRecordPayload, StoredRelationalRecord], None]
InsertFailureHook = Callable[[RelationalRecordPayload, str], None]

BeforeUpdateHook = Callable[[RelationalRecordPayload, Dict[str, Any]], Dict[str, Any]]
AfterUpdateHook = Callable[[RelationalRecordPayload, StoredRelationalRecord], None]
UpdateFailureHook = Callable[[RelationalRecordPayload, str], None]


class RelationalLifecycleHooks:
	"""Container for relational insert/update hooks."""

	def __init__(self) -> None:
		self._before_insert: List[BeforeInsertHook] = []
		self._after_insert: List[AfterInsertHook] = []
		self._fail_insert: List[InsertFailureHook] = []
		self._before_update: List[BeforeUpdateHook] = []
		self._after_update: List[AfterUpdateHook] = []
		self._fail_update: List[UpdateFailureHook] = []

	def register_before_insert(self, hook: BeforeInsertHook) -> None:
		self._before_insert.append(hook)

	def register_after_insert(self, hook: AfterInsertHook) -> None:
		self._after_insert.append(hook)

	def register_insert_failure(self, hook: InsertFailureHook) -> None:
		self._fail_insert.append(hook)

	def register_before_update(self, hook: BeforeUpdateHook) -> None:
		self._before_update.append(hook)

	def register_after_update(self, hook: AfterUpdateHook) -> None:
		self._after_update.append(hook)

	def register_update_failure(self, hook: UpdateFailureHook) -> None:
		self._fail_update.append(hook)

	def before_insert(self, payload: RelationalRecordPayload, record: Dict[str, Any]) -> Dict[str, Any]:
		current = record
		for hook in self._before_insert:
			try:
				current = hook(payload, current)
			except Exception as exc:  # pragma: no cover
				logger.warning("Relational before_insert hook failed: %s", exc)
		return current

	def after_insert(self, payload: RelationalRecordPayload, record: StoredRelationalRecord) -> None:
		for hook in self._after_insert:
			try:
				hook(payload, record)
			except Exception as exc:  # pragma: no cover
				logger.warning("Relational after_insert hook failed: %s", exc)

	def insert_failure(self, payload: RelationalRecordPayload, reason: str) -> None:
		for hook in self._fail_insert:
			try:
				hook(payload, reason)
			except Exception as exc:  # pragma: no cover
				logger.warning("Relational insert_failure hook failed: %s", exc)

	def before_update(self, payload: RelationalRecordPayload, record: Dict[str, Any]) -> Dict[str, Any]:
		current = record
		for hook in self._before_update:
			try:
				current = hook(payload, current)
			except Exception as exc:  # pragma: no cover
				logger.warning("Relational before_update hook failed: %s", exc)
		return current

	def after_update(self, payload: RelationalRecordPayload, record: StoredRelationalRecord) -> None:
		for hook in self._after_update:
			try:
				hook(payload, record)
			except Exception as exc:  # pragma: no cover
				logger.warning("Relational after_update hook failed: %s", exc)

	def update_failure(self, payload: RelationalRecordPayload, reason: str) -> None:
		for hook in self._fail_update:
			try:
				hook(payload, reason)
			except Exception as exc:  # pragma: no cover
				logger.warning("Relational update_failure hook failed: %s", exc)


class RelationalManagementService:
	"""High-level management layer for relational backends."""

	def __init__(
		self,
		backend: RelationalDatabaseBackend,
		*,
		config: Optional[RelationalManagementConfig] = None,
		strategy: Optional["UnifiedDatabaseStrategyType"] = None,
	) -> None:
		self._backend = backend
		self._config = config or RelationalManagementConfig()
		if strategy is not None:
			self._strategy: Optional[UnifiedDatabaseStrategyType] = strategy
		elif UDS3_AVAILABLE and _UnifiedDatabaseStrategyType is not None:
			self._strategy = _UnifiedDatabaseStrategyType()
		else:
			self._strategy = None

		self._tables: Dict[str, RelationalTableDefinition] = {}
		self.hooks = RelationalLifecycleHooks()
		self.logger = logging.getLogger(self.__class__.__name__)

	# ------------------------------------------------------------------
	# Table definition management

	def register_table(self, definition: RelationalTableDefinition) -> None:
		table_name = self._qualify_table(definition.name)
		self._tables[table_name] = definition
		created = self._backend.create_table(table_name, definition.schema)
		if not created:
			raise RelationalManagementError(f"Failed to create table '{table_name}'")

	def ensure_table(self, table_name: Optional[str]) -> Tuple[str, RelationalTableDefinition]:
		qualified_name = self._qualify_table(table_name or "") or self._qualify_table("records")
		definition = self._tables.get(qualified_name)
		if definition is None:
			if not self._config.allow_dynamic_tables:
				raise RelationalManagementError(
					f"Table '{qualified_name}' is not registered and dynamic creation is disabled"
				)
			definition = RelationalTableDefinition(name=qualified_name, metadata_template={"created_dynamic": True})
			self.register_table(definition)
		return qualified_name, definition

	def list_registered_tables(self) -> List[str]:
		return list(self._tables.keys())

	# ------------------------------------------------------------------
	# Mutation helpers

	def insert_records(self, payloads: Sequence[RelationalRecordPayload]) -> RelationalMutationResult:
		if not payloads:
			raise RelationalManagementError("No insert payloads provided")

		result = RelationalMutationResult()
		for payload in payloads:
			table_name, definition = self.ensure_table(payload.table)
			record = self._build_record(payload, definition)
			try:
				record = self.hooks.before_insert(payload, record)
				record_id = self._backend.insert_record(table_name, record)
			except Exception as exc:  # pragma: no cover
				reason = f"backend error: {exc}"
				self.logger.error("Failed to insert record into %s: %s", table_name, reason)
				result.failed_inserts.append((payload, reason))
				self.hooks.insert_failure(payload, reason)
				continue

			stored = StoredRelationalRecord(table=table_name, record_id=record_id, data=record)
			result.inserted.append(stored)
			self.hooks.after_insert(payload, stored)

		return result

	def update_records(self, payloads: Sequence[RelationalRecordPayload]) -> RelationalMutationResult:
		if not payloads:
			raise RelationalManagementError("No update payloads provided")

		result = RelationalMutationResult()
		for payload in payloads:
			if payload.record_id is None:
				raise RelationalManagementError("Update payload requires record_id")

			table_name, definition = self.ensure_table(payload.table)
			record = self._build_record(payload, definition)
			try:
				record = self.hooks.before_update(payload, record)
				success = self._backend.update_record(table_name, payload.record_id, record)
			except Exception as exc:  # pragma: no cover
				reason = f"backend error: {exc}"
				self.logger.error("Failed to update record %s in %s: %s", payload.record_id, table_name, reason)
				result.failed_updates.append((payload, reason))
				self.hooks.update_failure(payload, reason)
				continue

			if not success:
				reason = "backend returned False"
				self.logger.warning("Update rejected for record %s in %s", payload.record_id, table_name)
				result.failed_updates.append((payload, reason))
				self.hooks.update_failure(payload, reason)
				continue

			stored = StoredRelationalRecord(table=table_name, record_id=payload.record_id, data=record)
			result.updated.append(stored)
			self.hooks.after_update(payload, stored)

		return result

	# ------------------------------------------------------------------
	# Internal helpers

	def _qualify_table(self, name: Optional[str]) -> str:
		if not name:
			return self._config.default_schema + ".records" if self._config.default_schema else "records"
		if self._config.default_schema and "." not in name:
			return f"{self._config.default_schema}.{name}"
		return name

	def _build_record(
		self,
		payload: RelationalRecordPayload,
		definition: RelationalTableDefinition,
	) -> Dict[str, Any]:
		record = dict(payload.data)
		record.update(definition.metadata_template)
		record.update(payload.metadata)
		record.setdefault("created_at", payload.created_at.isoformat())

		if self._strategy and self._config.use_strategy_metadata:
			record.update(self._strategy_metadata(payload, definition))

		return definition.apply_defaults(record, enforce_required=self._config.enforce_required_columns)

	def _strategy_metadata(
		self,
		payload: RelationalRecordPayload,
		definition: RelationalTableDefinition,
	) -> Dict[str, Any]:
		if not self._strategy:
			return {}

		metadata: Dict[str, Any] = {}
		if hasattr(self._strategy, "enhance_relational_record"):
			try:
				metadata = self._strategy.enhance_relational_record(  # type: ignore[attr-defined]
					table=definition.name,
					record=payload.data,
					metadata=payload.metadata,
				)
			except Exception as exc:  # pragma: no cover
				self.logger.debug("Strategy relational metadata failed: %s", exc)
		return metadata or {}

