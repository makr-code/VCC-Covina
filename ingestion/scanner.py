"""Directory scanning and file classification services."""
from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .file_events import FileCategory, FileEvent, FileEventType, FileSnapshot

logger = logging.getLogger(__name__)

_TEXT_SUFFIXES: Set[str] = {
    ".txt",
    ".md",
    ".rtf",
    ".json",
    ".csv",
    ".log",
    ".xml",
}
_OFFICE_SUFFIXES: Set[str] = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".odt",
    ".ods",
}
_IMAGE_SUFFIXES: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".gif",
}
_GEO_SUFFIXES: Set[str] = {
    ".geojson",
    ".gml",
    ".kml",
    ".shp",
    ".gpkg",
}
_CODE_SUFFIXES: Set[str] = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cs",
    ".go",
    ".rs",
    ".sql",
    ".yaml",
    ".yml",
    ".ini",
    ".toml",
}
_ARCHIVE_SUFFIXES: Set[str] = {
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
}


class FileClassifier:
    """Simple suffix-based classifier for file categories."""

    def __init__(self, extra_mappings: Optional[Dict[str, FileCategory]] = None):
        self._extra_mappings = {k.lower(): v for k, v in (extra_mappings or {}).items()}

    def classify(self, path: Path) -> FileCategory:
        suffix = path.suffix.lower()
        if suffix in self._extra_mappings:
            return self._extra_mappings[suffix]
        if suffix in _TEXT_SUFFIXES:
            return FileCategory.TEXT
        if suffix in _OFFICE_SUFFIXES:
            return FileCategory.OFFICE
        if suffix in _IMAGE_SUFFIXES:
            return FileCategory.IMAGE
        if suffix in _GEO_SUFFIXES:
            return FileCategory.GEO
        if suffix in _CODE_SUFFIXES:
            return FileCategory.CODE
        if suffix in _ARCHIVE_SUFFIXES:
            return FileCategory.ARCHIVE
        return FileCategory.OTHER


class DirectoryScanner:
    """Scans a directory tree and emits file system events."""

    def __init__(
        self,
        root: Path,
        *,
        classifier: Optional[FileClassifier] = None,
        include_extensions: Optional[Sequence[str]] = None,
        exclude_extensions: Optional[Sequence[str]] = None,
        compute_hashes: bool = False,
    ) -> None:
        self._root = root
        self._classifier = classifier or FileClassifier()
        self._include_exts: Optional[Set[str]] = (
            {ext.lower() for ext in include_extensions} if include_extensions else None
        )
        self._exclude_exts: Set[str] = {ext.lower() for ext in (exclude_extensions or [])}
        self._compute_hashes = compute_hashes
        self._snapshots: Dict[Path, FileSnapshot] = {}
        self._lock = threading.RLock()

    @property
    def root(self) -> Path:
        return self._root

    def get_snapshots(self) -> Dict[Path, FileSnapshot]:
        with self._lock:
            return dict(self._snapshots)

    def scan_once(self) -> List[FileEvent]:
        if not self._root.exists():
            logger.warning("Scan root %s existiert nicht", self._root)
            return []

        with self._lock:
            current: Dict[Path, FileSnapshot] = {}
            events: List[FileEvent] = []

            for path in self._iter_files(self._root):
                try:
                    snapshot = self._build_snapshot(path)
                except OSError as exc:
                    logger.error("Fehler beim Lesen von %s: %s", path, exc)
                    continue

                current[path] = snapshot
                previous = self._snapshots.get(path)
                if previous is None:
                    events.append(FileEvent(FileEventType.CREATED, snapshot))
                elif snapshot.has_changed(previous):
                    events.append(FileEvent(FileEventType.MODIFIED, snapshot, previous))

            # deletions
            for missing_path, previous_snapshot in self._snapshots.items():
                if missing_path not in current:
                    events.append(FileEvent(FileEventType.DELETED, None, previous_snapshot))

            self._snapshots = current
            return events

    def _iter_files(self, root: Path) -> Iterable[Path]:
        for item in root.rglob("*"):
            if not item.is_file():
                continue
            suffix = item.suffix.lower()
            if self._include_exts is not None and suffix not in self._include_exts:
                continue
            if suffix in self._exclude_exts:
                continue
            yield item

    def _build_snapshot(self, path: Path) -> FileSnapshot:
        stat = path.stat()
        checksum = None
        if self._compute_hashes:
            checksum = self._compute_checksum(path)
        category = self._classifier.classify(path)
        return FileSnapshot(
            path=path,
            size=stat.st_size,
            modified_at=stat.st_mtime,
            checksum=checksum,
            category=category,
        )

    @staticmethod
    def _compute_checksum(path: Path, chunk_size: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
