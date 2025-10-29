"""
File Events Module - Complete Implementation
Compatible with ingestion/scanner.py
Date: 16. Oktober 2025
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
from datetime import datetime


class FileEventType(Enum):
    """Type of file system event"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


class FileCategory(Enum):
    """Category of file based on extension/type"""
    TEXT = "text"
    OFFICE = "office"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    CODE = "code"
    GEO = "geo"
    DATA = "data"
    OTHER = "other"


@dataclass
class FileSnapshot:
    """Snapshot of file state at a point in time"""
    path: Path
    size: int
    modified_at: float
    checksum: Optional[str]
    category: FileCategory
    
    def has_changed(self, other: 'FileSnapshot') -> bool:
        """Check if file has changed compared to other snapshot"""
        if self.size != other.size:
            return True
        if self.modified_at != other.modified_at:
            return True
        if self.checksum and other.checksum:
            return self.checksum != other.checksum
        return False


@dataclass
class FileEvent:
    """Event emitted by the DirectoryScanner"""
    event_type: FileEventType
    snapshot: Optional[FileSnapshot]
    previous_snapshot: Optional[FileSnapshot] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()


__all__ = [
    "FileEventType",
    "FileCategory", 
    "FileSnapshot",
    "FileEvent"
]
