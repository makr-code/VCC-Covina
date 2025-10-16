"""Registry and factory for ingestion handlers."""
from __future__ import annotations

import threading
from typing import Dict, Optional, Type

from ..file_events import FileCategory
from .base import BaseIngestionHandler


class HandlerRegistry:
    """Thread-safe registry mapping file categories to handler classes."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: Dict[FileCategory, Type[BaseIngestionHandler]] = {}

    def register(self, category: FileCategory, handler_cls: Type[BaseIngestionHandler]) -> "HandlerRegistry":
        with self._lock:
            setattr(handler_cls, "category", category)
            self._handlers[category] = handler_cls
        return self

    def get(self, category: FileCategory) -> Optional[Type[BaseIngestionHandler]]:
        with self._lock:
            return self._handlers.get(category)

    def snapshot(self) -> Dict[FileCategory, Type[BaseIngestionHandler]]:
        with self._lock:
            return dict(self._handlers)


class HandlerFactory:
    """Instantiates handlers on demand using the provided registry."""

    def __init__(self, registry: Optional[HandlerRegistry] = None) -> None:
        self._registry = registry or HandlerRegistry()

    @property
    def registry(self) -> HandlerRegistry:
        return self._registry

    def create(self, category: FileCategory) -> BaseIngestionHandler:
        handler_cls = self._registry.get(category)
        if handler_cls is None:
            handler_cls = self._registry.get(FileCategory.OTHER)
        if handler_cls is None:
            raise ValueError(f"Kein Handler für Kategorie {category.value} registriert")
        return handler_cls()


def create_default_factory() -> HandlerFactory:
    """Create a factory pre-populated with standard handlers."""

    from .archive import ArchiveIngestionHandler
    from .code import CodeIngestionHandler
    from .geo import GeoIngestionHandler
    from .image import ImageIngestionHandler
    from .office import OfficeIngestionHandler
    from .text import TextIngestionHandler

    registry = HandlerRegistry()
    registry.register(FileCategory.TEXT, TextIngestionHandler)
    registry.register(FileCategory.OFFICE, OfficeIngestionHandler)
    registry.register(FileCategory.IMAGE, ImageIngestionHandler)
    registry.register(FileCategory.GEO, GeoIngestionHandler)
    registry.register(FileCategory.CODE, CodeIngestionHandler)
    registry.register(FileCategory.ARCHIVE, ArchiveIngestionHandler)  # ✅ NEW
    registry.register(FileCategory.OTHER, TextIngestionHandler)
    return HandlerFactory(registry)
