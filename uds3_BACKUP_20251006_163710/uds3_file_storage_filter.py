#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 File Storage Filter Module
================================

Provides comprehensive file filtering and search capabilities for the UDS3 system.

Core Features:
- File metadata extraction and indexing
- Multi-criteria filtering (extension, size, date, hash)
- Advanced search patterns (glob, regex)
- Storage backend abstraction (local filesystem, extensible to cloud)
- CRUD operations for file management

Author: UDS3 Development Team
Date: 2. Oktober 2025
"""

import os
import hashlib
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import mimetypes


# ============================================================================
# Enums
# ============================================================================

class FileType(Enum):
    """File type categories"""
    DOCUMENT = "document"  # PDF, DOC, TXT, etc.
    IMAGE = "image"  # JPG, PNG, GIF, etc.
    VIDEO = "video"  # MP4, AVI, etc.
    AUDIO = "audio"  # MP3, WAV, etc.
    ARCHIVE = "archive"  # ZIP, TAR, etc.
    CODE = "code"  # PY, JS, etc.
    DATA = "data"  # JSON, XML, CSV, etc.
    EXECUTABLE = "executable"  # EXE, BIN, etc.
    OTHER = "other"


class SizeUnit(Enum):
    """File size units"""
    BYTES = "bytes"
    KB = "kb"
    MB = "mb"
    GB = "gb"
    TB = "tb"


class SortOrder(Enum):
    """Sort order for file listings"""
    ASC = "ascending"
    DESC = "descending"


class FilterOperator(Enum):
    """Comparison operators for filtering"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES_REGEX = "matches_regex"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class FileMetadata:
    """
    Comprehensive file metadata.
    
    Attributes:
        file_id: Unique identifier
        path: Absolute file path
        name: Filename with extension
        extension: File extension (lowercase, without dot)
        size_bytes: File size in bytes
        file_type: Categorized file type
        mime_type: MIME type
        created_at: Creation timestamp
        modified_at: Last modification timestamp
        accessed_at: Last access timestamp
        content_hash: SHA-256 hash of file content
        is_hidden: Whether file is hidden
        is_symlink: Whether file is a symbolic link
        permissions: File permissions (octal string)
        owner: File owner (if available)
        metadata: Additional custom metadata
    """
    file_id: str
    path: str
    name: str
    extension: str
    size_bytes: int
    file_type: FileType
    mime_type: str
    
    # Timestamps
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    
    # Content
    content_hash: Optional[str] = None
    
    # Properties
    is_hidden: bool = False
    is_symlink: bool = False
    permissions: str = "0644"
    owner: Optional[str] = None
    
    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.file_id:
            self.file_id = f"file-{uuid.uuid4().hex[:12]}"
    
    def size_in_unit(self, unit: SizeUnit) -> float:
        """Convert size to specified unit"""
        conversions = {
            SizeUnit.BYTES: 1,
            SizeUnit.KB: 1024,
            SizeUnit.MB: 1024 ** 2,
            SizeUnit.GB: 1024 ** 3,
            SizeUnit.TB: 1024 ** 4
        }
        return self.size_bytes / conversions[unit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "file_id": self.file_id,
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_in_unit(SizeUnit.MB), 2),
            "file_type": self.file_type.value,
            "mime_type": self.mime_type,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "content_hash": self.content_hash,
            "is_hidden": self.is_hidden,
            "is_symlink": self.is_symlink,
            "permissions": self.permissions,
            "owner": self.owner,
            "metadata": self.metadata
        }


@dataclass
class FileSearchQuery:
    """
    File search query builder.
    
    Supports multiple criteria:
    - Path patterns (glob, regex)
    - Extension filters
    - Size range
    - Date range
    - Content hash
    - File type
    """
    # Path patterns
    path_pattern: Optional[str] = None  # Glob or regex pattern
    use_regex: bool = False
    
    # Extension filters
    extensions: List[str] = field(default_factory=list)  # e.g., ['pdf', 'docx']
    exclude_extensions: List[str] = field(default_factory=list)
    
    # Size filters
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    
    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    
    # Content filters
    content_hash: Optional[str] = None
    
    # Type filters
    file_types: List[FileType] = field(default_factory=list)
    
    # Hidden/Symlink filters
    include_hidden: bool = False
    include_symlinks: bool = True
    
    # Sorting
    sort_by: str = "modified_at"  # name, size_bytes, created_at, modified_at
    sort_order: SortOrder = SortOrder.DESC
    
    # Pagination
    limit: Optional[int] = None
    offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "path_pattern": self.path_pattern,
            "use_regex": self.use_regex,
            "extensions": self.extensions,
            "exclude_extensions": self.exclude_extensions,
            "min_size_bytes": self.min_size_bytes,
            "max_size_bytes": self.max_size_bytes,
            "created_after": self.created_after.isoformat() if self.created_after else None,
            "created_before": self.created_before.isoformat() if self.created_before else None,
            "modified_after": self.modified_after.isoformat() if self.modified_after else None,
            "modified_before": self.modified_before.isoformat() if self.modified_before else None,
            "content_hash": self.content_hash,
            "file_types": [ft.value for ft in self.file_types],
            "include_hidden": self.include_hidden,
            "include_symlinks": self.include_symlinks,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order.value,
            "limit": self.limit,
            "offset": self.offset
        }


@dataclass
class FileFilterResult:
    """
    Result of file filter operation.
    """
    success: bool
    files: List[FileMetadata]
    total_count: int
    filtered_count: int
    query: FileSearchQuery
    execution_time_ms: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "files": [f.to_dict() for f in self.files],
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
            "query": self.query.to_dict(),
            "execution_time_ms": self.execution_time_ms,
            "error": self.error
        }


# ============================================================================
# File Storage Backend Interface
# ============================================================================

class FileStorageBackend:
    """
    Abstract interface for file storage backends.
    
    Implementations can support:
    - Local filesystem
    - Cloud storage (S3, Azure Blob, GCS)
    - Network file systems (NFS, SMB)
    """
    
    def scan_directory(
        self,
        directory: str,
        recursive: bool = True,
        include_hidden: bool = False
    ) -> List[FileMetadata]:
        """
        Scan directory and return file metadata.
        
        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories
            include_hidden: Whether to include hidden files
        
        Returns:
            List of FileMetadata objects
        """
        raise NotImplementedError
    
    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """
        Get metadata for a single file.
        
        Args:
            file_path: Path to file
        
        Returns:
            FileMetadata object or None if file not found
        """
        raise NotImplementedError
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        raise NotImplementedError
    
    def calculate_hash(self, file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file content hash"""
        raise NotImplementedError
    
    def get_statistics(self, directory: str) -> Dict[str, Any]:
        """Get directory statistics"""
        raise NotImplementedError


# ============================================================================
# Local Filesystem Backend
# ============================================================================

class LocalFileSystemBackend(FileStorageBackend):
    """
    Local filesystem implementation of FileStorageBackend.
    """
    
    def __init__(self):
        self.file_type_mappings = self._build_file_type_mappings()
    
    def _build_file_type_mappings(self) -> Dict[str, FileType]:
        """Build extension to file type mappings"""
        return {
            # Documents
            "pdf": FileType.DOCUMENT,
            "doc": FileType.DOCUMENT,
            "docx": FileType.DOCUMENT,
            "txt": FileType.DOCUMENT,
            "rtf": FileType.DOCUMENT,
            "odt": FileType.DOCUMENT,
            "md": FileType.DOCUMENT,
            
            # Images
            "jpg": FileType.IMAGE,
            "jpeg": FileType.IMAGE,
            "png": FileType.IMAGE,
            "gif": FileType.IMAGE,
            "bmp": FileType.IMAGE,
            "svg": FileType.IMAGE,
            "webp": FileType.IMAGE,
            "tiff": FileType.IMAGE,
            
            # Video
            "mp4": FileType.VIDEO,
            "avi": FileType.VIDEO,
            "mkv": FileType.VIDEO,
            "mov": FileType.VIDEO,
            "wmv": FileType.VIDEO,
            "flv": FileType.VIDEO,
            "webm": FileType.VIDEO,
            
            # Audio
            "mp3": FileType.AUDIO,
            "wav": FileType.AUDIO,
            "flac": FileType.AUDIO,
            "aac": FileType.AUDIO,
            "ogg": FileType.AUDIO,
            "wma": FileType.AUDIO,
            
            # Archive
            "zip": FileType.ARCHIVE,
            "tar": FileType.ARCHIVE,
            "gz": FileType.ARCHIVE,
            "bz2": FileType.ARCHIVE,
            "7z": FileType.ARCHIVE,
            "rar": FileType.ARCHIVE,
            
            # Code
            "py": FileType.CODE,
            "js": FileType.CODE,
            "java": FileType.CODE,
            "cpp": FileType.CODE,
            "c": FileType.CODE,
            "h": FileType.CODE,
            "cs": FileType.CODE,
            "php": FileType.CODE,
            "rb": FileType.CODE,
            "go": FileType.CODE,
            "rs": FileType.CODE,
            "ts": FileType.CODE,
            
            # Data
            "json": FileType.DATA,
            "xml": FileType.DATA,
            "yaml": FileType.DATA,
            "yml": FileType.DATA,
            "csv": FileType.DATA,
            "sql": FileType.DATA,
            
            # Executable
            "exe": FileType.EXECUTABLE,
            "bin": FileType.EXECUTABLE,
            "dll": FileType.EXECUTABLE,
            "so": FileType.EXECUTABLE,
        }
    
    def _classify_file_type(self, extension: str) -> FileType:
        """Classify file by extension"""
        return self.file_type_mappings.get(extension.lower(), FileType.OTHER)
    
    def scan_directory(
        self,
        directory: str,
        recursive: bool = True,
        include_hidden: bool = False
    ) -> List[FileMetadata]:
        """Scan directory and return file metadata"""
        files = []
        path = Path(directory)
        
        if not path.exists():
            return files
        
        # Use glob pattern based on recursive flag
        pattern = "**/*" if recursive else "*"
        
        for file_path in path.glob(pattern):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip hidden files if requested
            if not include_hidden and file_path.name.startswith('.'):
                continue
            
            # Get metadata
            metadata = self.get_file_metadata(str(file_path))
            if metadata:
                files.append(metadata)
        
        return files
    
    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """Get metadata for a single file"""
        path = Path(file_path)
        
        if not path.exists() or not path.is_file():
            return None
        
        try:
            stat = path.stat()
            extension = path.suffix[1:].lower() if path.suffix else ""
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = "application/octet-stream"
            
            # Create metadata
            metadata = FileMetadata(
                file_id="",  # Will be auto-generated
                path=str(path.absolute()),
                name=path.name,
                extension=extension,
                size_bytes=stat.st_size,
                file_type=self._classify_file_type(extension),
                mime_type=mime_type,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                accessed_at=datetime.fromtimestamp(stat.st_atime),
                is_hidden=path.name.startswith('.'),
                is_symlink=path.is_symlink(),
                permissions=oct(stat.st_mode)[-3:]
            )
            
            return metadata
            
        except Exception:
            return None
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        return Path(file_path).is_file()
    
    def calculate_hash(self, file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file content hash"""
        hash_func = hashlib.new(algorithm)
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception:
            return ""
    
    def get_statistics(self, directory: str) -> Dict[str, Any]:
        """Get directory statistics"""
        files = self.scan_directory(directory, recursive=True, include_hidden=True)
        
        total_size = sum(f.size_bytes for f in files)
        file_types = {}
        extensions = {}
        
        for f in files:
            # Count by file type
            file_types[f.file_type.value] = file_types.get(f.file_type.value, 0) + 1
            
            # Count by extension
            if f.extension:
                extensions[f.extension] = extensions.get(f.extension, 0) + 1
        
        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 ** 2), 2),
            "total_size_gb": round(total_size / (1024 ** 3), 2),
            "file_types": file_types,
            "extensions": extensions,
            "directory": directory
        }


# ============================================================================
# File Storage Filter
# ============================================================================

class FileStorageFilter:
    """
    Main file storage filter with comprehensive query capabilities.
    """
    
    def __init__(self, backend: FileStorageBackend):
        self.backend = backend
    
    def search(self, query: FileSearchQuery, base_directory: str = ".") -> FileFilterResult:
        """
        Execute file search query.
        
        Args:
            query: FileSearchQuery object
            base_directory: Base directory to search from
        
        Returns:
            FileFilterResult with matching files
        """
        start_time = datetime.now()
        
        try:
            # Scan directory
            all_files = self.backend.scan_directory(
                base_directory,
                recursive=True,
                include_hidden=query.include_hidden
            )
            
            # Apply filters
            filtered_files = self._apply_filters(all_files, query)
            
            # Sort results
            filtered_files = self._sort_files(filtered_files, query.sort_by, query.sort_order)
            
            # Apply pagination
            total_filtered = len(filtered_files)
            filtered_files = filtered_files[query.offset:]
            if query.limit:
                filtered_files = filtered_files[:query.limit]
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return FileFilterResult(
                success=True,
                files=filtered_files,
                total_count=len(all_files),
                filtered_count=total_filtered,
                query=query,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return FileFilterResult(
                success=False,
                files=[],
                total_count=0,
                filtered_count=0,
                query=query,
                execution_time_ms=execution_time,
                error=str(e)
            )
    
    def _apply_filters(self, files: List[FileMetadata], query: FileSearchQuery) -> List[FileMetadata]:
        """Apply all query filters to file list"""
        filtered = files
        
        # Path pattern filter
        if query.path_pattern:
            if query.use_regex:
                pattern = re.compile(query.path_pattern)
                filtered = [f for f in filtered if pattern.search(f.path)]
            else:
                # Convert glob to regex
                import fnmatch
                filtered = [f for f in filtered if fnmatch.fnmatch(f.path, query.path_pattern)]
        
        # Extension filters
        if query.extensions:
            filtered = [f for f in filtered if f.extension in query.extensions]
        
        if query.exclude_extensions:
            filtered = [f for f in filtered if f.extension not in query.exclude_extensions]
        
        # Size filters
        if query.min_size_bytes is not None:
            filtered = [f for f in filtered if f.size_bytes >= query.min_size_bytes]
        
        if query.max_size_bytes is not None:
            filtered = [f for f in filtered if f.size_bytes <= query.max_size_bytes]
        
        # Date filters
        if query.created_after:
            filtered = [f for f in filtered if f.created_at >= query.created_after]
        
        if query.created_before:
            filtered = [f for f in filtered if f.created_at <= query.created_before]
        
        if query.modified_after:
            filtered = [f for f in filtered if f.modified_at >= query.modified_after]
        
        if query.modified_before:
            filtered = [f for f in filtered if f.modified_at <= query.modified_before]
        
        # Content hash filter
        if query.content_hash:
            filtered = [f for f in filtered if f.content_hash == query.content_hash]
        
        # File type filter
        if query.file_types:
            filtered = [f for f in filtered if f.file_type in query.file_types]
        
        # Symlink filter
        if not query.include_symlinks:
            filtered = [f for f in filtered if not f.is_symlink]
        
        return filtered
    
    def _sort_files(
        self,
        files: List[FileMetadata],
        sort_by: str,
        sort_order: SortOrder
    ) -> List[FileMetadata]:
        """Sort files by specified field"""
        reverse = (sort_order == SortOrder.DESC)
        
        if sort_by == "name":
            return sorted(files, key=lambda f: f.name.lower(), reverse=reverse)
        elif sort_by == "size_bytes":
            return sorted(files, key=lambda f: f.size_bytes, reverse=reverse)
        elif sort_by == "created_at":
            return sorted(files, key=lambda f: f.created_at, reverse=reverse)
        elif sort_by == "modified_at":
            return sorted(files, key=lambda f: f.modified_at, reverse=reverse)
        else:
            return files
    
    def filter_by_extension(
        self,
        extensions: List[str],
        base_directory: str = ".",
        limit: Optional[int] = None
    ) -> List[FileMetadata]:
        """Quick filter by file extensions"""
        query = FileSearchQuery(
            extensions=extensions,
            limit=limit
        )
        result = self.search(query, base_directory)
        return result.files
    
    def filter_by_size_range(
        self,
        min_mb: float = 0,
        max_mb: Optional[float] = None,
        base_directory: str = ".",
        limit: Optional[int] = None
    ) -> List[FileMetadata]:
        """Quick filter by size range (in MB)"""
        query = FileSearchQuery(
            min_size_bytes=int(min_mb * 1024 * 1024),
            max_size_bytes=int(max_mb * 1024 * 1024) if max_mb else None,
            limit=limit
        )
        result = self.search(query, base_directory)
        return result.files
    
    def filter_by_date_range(
        self,
        modified_after: Optional[datetime] = None,
        modified_before: Optional[datetime] = None,
        base_directory: str = ".",
        limit: Optional[int] = None
    ) -> List[FileMetadata]:
        """Quick filter by modification date range"""
        query = FileSearchQuery(
            modified_after=modified_after,
            modified_before=modified_before,
            limit=limit
        )
        result = self.search(query, base_directory)
        return result.files
    
    def filter_by_type(
        self,
        file_types: List[FileType],
        base_directory: str = ".",
        limit: Optional[int] = None
    ) -> List[FileMetadata]:
        """Quick filter by file types"""
        query = FileSearchQuery(
            file_types=file_types,
            limit=limit
        )
        result = self.search(query, base_directory)
        return result.files
    
    def find_duplicates(
        self,
        base_directory: str = ".",
        by_hash: bool = True
    ) -> Dict[str, List[FileMetadata]]:
        """
        Find duplicate files.
        
        Args:
            base_directory: Directory to search
            by_hash: Use content hash (True) or size only (False)
        
        Returns:
            Dict mapping hash/size to list of duplicate files
        """
        all_files = self.backend.scan_directory(base_directory, recursive=True)
        
        duplicates: Dict[str, List[FileMetadata]] = {}
        
        for file in all_files:
            if by_hash:
                # Calculate hash for comparison
                file.content_hash = self.backend.calculate_hash(file.path)
                key = file.content_hash
            else:
                key = str(file.size_bytes)
            
            if key not in duplicates:
                duplicates[key] = []
            duplicates[key].append(file)
        
        # Keep only actual duplicates (more than 1 file)
        return {k: v for k, v in duplicates.items() if len(v) > 1}
    
    def get_statistics(self, base_directory: str = ".") -> Dict[str, Any]:
        """Get comprehensive file statistics"""
        return self.backend.get_statistics(base_directory)


# ============================================================================
# Factory Functions
# ============================================================================

def create_file_storage_filter(backend: Optional[FileStorageBackend] = None) -> FileStorageFilter:
    """
    Create FileStorageFilter instance.
    
    Args:
        backend: Optional FileStorageBackend (defaults to LocalFileSystemBackend)
    
    Returns:
        FileStorageFilter instance
    """
    if backend is None:
        backend = LocalFileSystemBackend()
    return FileStorageFilter(backend)


def create_local_backend() -> LocalFileSystemBackend:
    """Create LocalFileSystemBackend instance"""
    return LocalFileSystemBackend()


def create_search_query(**kwargs) -> FileSearchQuery:
    """Create FileSearchQuery with given parameters"""
    return FileSearchQuery(**kwargs)


# ============================================================================
# Built-in Test
# ============================================================================

if __name__ == "__main__":
    print("FileStorageFilter Module - Quick Test")
    print("=" * 60)
    
    # Create filter with local backend
    file_filter = create_file_storage_filter()
    backend = create_local_backend()
    
    # Test 1: Scan current directory
    print("\n[1/4] Scanning current directory...")
    files = backend.scan_directory(".", recursive=False, include_hidden=False)
    print(f"✅ Found {len(files)} files")
    if files:
        print(f"   Example: {files[0].name} ({files[0].size_in_unit(SizeUnit.KB):.2f} KB)")
    
    # Test 2: Filter by extension
    print("\n[2/4] Filter Python files...")
    python_files = file_filter.filter_by_extension(["py"], ".")
    print(f"✅ Found {len(python_files)} Python files")
    if python_files:
        total_size_mb = sum(f.size_bytes for f in python_files) / (1024 ** 2)
        print(f"   Total size: {total_size_mb:.2f} MB")
    
    # Test 3: Statistics
    print("\n[3/4] Directory statistics...")
    stats = file_filter.get_statistics(".")
    print(f"✅ Statistics:")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']:.2f} MB")
    print(f"   File types: {len(stats['file_types'])}")
    
    # Test 4: Advanced search
    print("\n[4/4] Advanced search (Python files > 10KB)...")
    query = create_search_query(
        extensions=["py"],
        min_size_bytes=10 * 1024,
        sort_by="size_bytes",
        sort_order=SortOrder.DESC,
        limit=5
    )
    result = file_filter.search(query, ".")
    print(f"✅ Search completed in {result.execution_time_ms:.2f}ms")
    print(f"   Found: {result.filtered_count} files")
    for i, f in enumerate(result.files, 1):
        print(f"   {i}. {f.name} - {f.size_in_unit(SizeUnit.KB):.2f} KB")
    
    print("\n✅ FileStorageFilter Module Test Complete!")
