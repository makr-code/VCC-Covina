"""Filesystem management layer for UDS3 administrative services."""

from __future__ import annotations

import sitecustomize  # noqa: F401  # stellt Imports für uds3/database sicher
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple

from uds3.database.database_api_file_storage import FileSystemStorageBackend

try:  # pragma: no cover - optional dependency
	from uds3 import UnifiedDatabaseStrategy as _UnifiedDatabaseStrategyType  # type: ignore
	UDS3_AVAILABLE = _UnifiedDatabaseStrategyType is not None
except Exception:  # pragma: no cover
	_UnifiedDatabaseStrategyType = None  # type: ignore
	UDS3_AVAILABLE = False

if TYPE_CHECKING:  # pragma: no cover - typing helper
	from uds3 import UnifiedDatabaseStrategy as UnifiedDatabaseStrategyType  # type: ignore
else:  # Runtime fallback avoiding hard dependency
	UnifiedDatabaseStrategyType = Any


logger = logging.getLogger(__name__)


class FileSystemManagementError(RuntimeError):
	"""Raised when filesystem management operations fail."""


@dataclass(frozen=True)
class FileSystemManagementConfig:
	"""Configuration knobs for filesystem management."""

	auto_connect: bool = True
	skip_duplicates: bool = True
	default_subdir: Optional[str] = None
	metadata_overrides: Dict[str, Any] = field(default_factory=dict)
	use_strategy_metadata: bool = True


@dataclass
class FileAssetPayload:
	"""Payload describing an asset that should be stored in the filesystem."""

	source_path: Optional[str] = None
	data: Optional[bytes] = None
	filename: Optional[str] = None
	mime: Optional[str] = None
	content_hash: Optional[str] = None
	subdir: Optional[str] = None
	metadata: Dict[str, Any] = field(default_factory=dict)

	def build_store_kwargs(self) -> Dict[str, Any]:
		if self.data is None and not self.source_path:
			raise FileSystemManagementError("FileAssetPayload requires either 'data' or 'source_path'")

		return {
			"source_path": self.source_path,
			"data": self.data,
			"filename": self.filename,
			"mime": self.mime,
			"content_hash": self.content_hash,
			"subdir": self.subdir,
			"metadata": dict(self.metadata),
		}


@dataclass
class FileDerivativePayload:
	"""Payload describing a derivative for an existing asset."""

	asset_id: str
	derivative_type: str
	source_path: Optional[str] = None
	data: Optional[bytes] = None
	filename: Optional[str] = None
	mime: Optional[str] = None
	content_hash: Optional[str] = None
	metadata: Dict[str, Any] = field(default_factory=dict)

	def build_store_kwargs(self) -> Dict[str, Any]:
		if self.data is None and not self.source_path:
			raise FileSystemManagementError("FileDerivativePayload requires either 'data' or 'source_path'")

		return {
			"asset_id": self.asset_id,
			"derivative_type": self.derivative_type,
			"source_path": self.source_path,
			"data": self.data,
			"filename": self.filename,
			"mime": self.mime,
			"content_hash": self.content_hash,
			"metadata": dict(self.metadata),
		}


@dataclass
class StoredFileAsset:
	"""Represents a successfully persisted file asset."""

	asset_id: str
	content_hash: Optional[str]
	uri: str
	path: str
	metadata: Dict[str, Any]


@dataclass
class StoredFileDerivative:
	"""Represents a successfully persisted derivative asset."""

	asset_id: str
	derivative_type: str
	content_hash: Optional[str]
	uri: str
	path: str
	metadata: Dict[str, Any]


@dataclass
class FileAssetIngestResult:
	"""Result bundle for asset ingest operations."""

	stored: List[StoredFileAsset] = field(default_factory=list)
	skipped: List[Tuple[FileAssetPayload, str]] = field(default_factory=list)
	failed: List[Tuple[FileAssetPayload, str]] = field(default_factory=list)
	duration_seconds: float = 0.0

	@property
	def success(self) -> bool:
		return not self.failed


@dataclass
class FileDerivativeIngestResult:
	"""Result bundle for derivative ingest operations."""

	stored: List[StoredFileDerivative] = field(default_factory=list)
	failed: List[Tuple[FileDerivativePayload, str]] = field(default_factory=list)
	duration_seconds: float = 0.0

	@property
	def success(self) -> bool:
		return not self.failed


BeforeAssetHook = Callable[[FileAssetPayload, Dict[str, Any]], Dict[str, Any]]
AfterAssetHook = Callable[[FileAssetPayload, StoredFileAsset], None]
AssetFailureHook = Callable[[FileAssetPayload, str], None]

BeforeDerivativeHook = Callable[[FileDerivativePayload, Dict[str, Any]], Dict[str, Any]]
AfterDerivativeHook = Callable[[FileDerivativePayload, StoredFileDerivative], None]
DerivativeFailureHook = Callable[[FileDerivativePayload, str], None]


class FileSystemLifecycleHooks:
	"""Container for lifecycle hooks during file asset operations."""

	def __init__(self) -> None:
		self._before_asset: List[BeforeAssetHook] = []
		self._after_asset: List[AfterAssetHook] = []
		self._asset_failure: List[AssetFailureHook] = []
		self._before_derivative: List[BeforeDerivativeHook] = []
		self._after_derivative: List[AfterDerivativeHook] = []
		self._derivative_failure: List[DerivativeFailureHook] = []

	def register_before_asset(self, hook: BeforeAssetHook) -> None:
		self._before_asset.append(hook)

	def register_after_asset(self, hook: AfterAssetHook) -> None:
		self._after_asset.append(hook)

	def register_asset_failure(self, hook: AssetFailureHook) -> None:
		self._asset_failure.append(hook)

	def register_before_derivative(self, hook: BeforeDerivativeHook) -> None:
		self._before_derivative.append(hook)

	def register_after_derivative(self, hook: AfterDerivativeHook) -> None:
		self._after_derivative.append(hook)

	def register_derivative_failure(self, hook: DerivativeFailureHook) -> None:
		self._derivative_failure.append(hook)

	def before_asset(self, payload: FileAssetPayload, kwargs: Dict[str, Any]) -> Dict[str, Any]:
		current = kwargs
		for hook in self._before_asset:
			try:
				current = hook(payload, current)
			except Exception as exc:  # pragma: no cover - defensive guard
				logger.warning("Filesystem before_asset hook failed: %s", exc)
		return current

	def after_asset(self, payload: FileAssetPayload, stored: StoredFileAsset) -> None:
		for hook in self._after_asset:
			try:
				hook(payload, stored)
			except Exception as exc:  # pragma: no cover
				logger.warning("Filesystem after_asset hook failed: %s", exc)

	def asset_failure(self, payload: FileAssetPayload, reason: str) -> None:
		for hook in self._asset_failure:
			try:
				hook(payload, reason)
			except Exception as exc:  # pragma: no cover
				logger.warning("Filesystem asset_failure hook failed: %s", exc)

	def before_derivative(self, payload: FileDerivativePayload, kwargs: Dict[str, Any]) -> Dict[str, Any]:
		current = kwargs
		for hook in self._before_derivative:
			try:
				current = hook(payload, current)
			except Exception as exc:  # pragma: no cover
				logger.warning("Filesystem before_derivative hook failed: %s", exc)
		return current

	def after_derivative(self, payload: FileDerivativePayload, stored: StoredFileDerivative) -> None:
		for hook in self._after_derivative:
			try:
				hook(payload, stored)
			except Exception as exc:  # pragma: no cover
				logger.warning("Filesystem after_derivative hook failed: %s", exc)

	def derivative_failure(self, payload: FileDerivativePayload, reason: str) -> None:
		for hook in self._derivative_failure:
			try:
				hook(payload, reason)
			except Exception as exc:  # pragma: no cover
				logger.warning("Filesystem derivative_failure hook failed: %s", exc)


class FileSystemManagementService:
	"""High-level management layer for filesystem backends."""

	def __init__(
		self,
		backend: FileSystemStorageBackend,
		*,
		config: Optional[FileSystemManagementConfig] = None,
		strategy: Optional["UnifiedDatabaseStrategyType"] = None,
	) -> None:
		self._backend = backend
		self._config = config or FileSystemManagementConfig()
		if strategy is not None:
			self._strategy: Optional[UnifiedDatabaseStrategyType] = strategy
		elif UDS3_AVAILABLE and _UnifiedDatabaseStrategyType is not None:
			self._strategy = _UnifiedDatabaseStrategyType()
		else:
			self._strategy = None

		self.hooks = FileSystemLifecycleHooks()
		self.logger = logging.getLogger(self.__class__.__name__)

		if self._config.auto_connect:
			self._ensure_connection()

	# ------------------------------------------------------------------
	# Public operations

	def store_assets(self, payloads: Sequence[FileAssetPayload]) -> FileAssetIngestResult:
		if not payloads:
			raise FileSystemManagementError("No asset payloads provided")

		self._ensure_connection()
		result = FileAssetIngestResult()
		started = time.perf_counter()

		for payload in payloads:
			try:
				store_kwargs, skip_reason = self._prepare_asset_kwargs(payload)
			except Exception as exc:
				reason = str(exc)
				result.failed.append((payload, reason))
				self.hooks.asset_failure(payload, reason)
				continue

			if skip_reason:
				result.skipped.append((payload, skip_reason))
				continue

			try:
				store_kwargs = self.hooks.before_asset(payload, store_kwargs)
				info = self._backend.store_asset(**store_kwargs)
			except Exception as exc:  # pragma: no cover - backend failure
				reason = f"backend error: {exc}"
				self.logger.error("Failed to store asset: %s", reason)
				result.failed.append((payload, reason))
				self.hooks.asset_failure(payload, reason)
				continue

			stored = StoredFileAsset(
				asset_id=info.get("asset_id") or info.get("hash") or "",
				content_hash=info.get("hash"),
				uri=info.get("uri", ""),
				path=info.get("path", ""),
				metadata={k: v for k, v in info.items() if k not in {"asset_id", "hash", "uri", "path"}},
			)
			result.stored.append(stored)
			self.hooks.after_asset(payload, stored)

		result.duration_seconds = time.perf_counter() - started
		return result

	def store_derivatives(self, payloads: Sequence[FileDerivativePayload]) -> FileDerivativeIngestResult:
		if not payloads:
			raise FileSystemManagementError("No derivative payloads provided")

		self._ensure_connection()
		result = FileDerivativeIngestResult()
		started = time.perf_counter()

		for payload in payloads:
			try:
				store_kwargs = payload.build_store_kwargs()
				store_kwargs["metadata"] = self._prepare_metadata(payload.metadata)
			except Exception as exc:
				reason = str(exc)
				result.failed.append((payload, reason))
				self.hooks.derivative_failure(payload, reason)
				continue

			try:
				store_kwargs = self.hooks.before_derivative(payload, store_kwargs)
				info = self._backend.upsert_derivative(**store_kwargs)
			except Exception as exc:  # pragma: no cover
				reason = f"backend error: {exc}"
				self.logger.error(
					"Failed to store derivative %s for asset %s: %s",
					payload.derivative_type,
					payload.asset_id,
					reason,
				)
				result.failed.append((payload, reason))
				self.hooks.derivative_failure(payload, reason)
				continue

			stored = StoredFileDerivative(
				asset_id=info.get("asset_id", payload.asset_id),
				derivative_type=info.get("type", payload.derivative_type),
				content_hash=info.get("hash"),
				uri=info.get("uri", ""),
				path=info.get("path", ""),
				metadata={k: v for k, v in info.items() if k not in {"asset_id", "type", "uri", "path", "hash"}},
			)
			result.stored.append(stored)
			self.hooks.after_derivative(payload, stored)

		result.duration_seconds = time.perf_counter() - started
		return result

	# ------------------------------------------------------------------
	# Internal helpers

	def _ensure_connection(self) -> None:
		if self._backend.is_available():
			return
		connected = self._backend.connect()
		if not connected or not self._backend.is_available():
			raise FileSystemManagementError("Filesystem backend is not available")

	def _prepare_asset_kwargs(self, payload: FileAssetPayload) -> Tuple[Dict[str, Any], Optional[str]]:
		store_kwargs = payload.build_store_kwargs()
		store_kwargs["metadata"] = self._prepare_metadata(payload.metadata)

		subdir = store_kwargs.get("subdir") or self._config.default_subdir
		if subdir:
			store_kwargs["subdir"] = subdir

		if self._config.skip_duplicates and store_kwargs.get("content_hash"):
			if self._backend.is_duplicate(store_kwargs["content_hash"], subdir):
				return store_kwargs, "duplicate asset detected"

		return store_kwargs, None

	def _prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
		merged: Dict[str, Any] = {}
		merged.update(metadata)

		if self._strategy and self._config.use_strategy_metadata:
			merged.update(self._strategy_metadata(metadata))

		merged.update(self._config.metadata_overrides)
		return merged

	def _strategy_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
		if not self._strategy:
			return {}

		enriched: Dict[str, Any] = {}
		if hasattr(self._strategy, "enhance_file_asset"):
			try:
				enriched = self._strategy.enhance_file_asset(metadata=metadata)  # type: ignore[attr-defined]
			except Exception as exc:  # pragma: no cover
				self.logger.debug("Strategy file asset metadata failed: %s", exc)
		elif hasattr(self._strategy, "enhance_binary_metadata"):
			try:
				enriched = self._strategy.enhance_binary_metadata(metadata=metadata)  # type: ignore[attr-defined]
			except Exception as exc:  # pragma: no cover
				self.logger.debug("Strategy binary metadata failed: %s", exc)
		return enriched or {}

