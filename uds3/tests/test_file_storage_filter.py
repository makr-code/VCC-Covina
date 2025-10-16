#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite for UDS3 File Storage Filter Module
==============================================

Comprehensive tests for file filtering and search capabilities.

Author: UDS3 Development Team
Date: 2. Oktober 2025
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from uds3_file_storage_filter import (
    # Models
    FileMetadata,
    FileSearchQuery,
    FileFilterResult,
    # Enums
    FileType,
    SizeUnit,
    SortOrder,
    FilterOperator,
    # Backend
    FileStorageBackend,
    LocalFileSystemBackend,
    # Filter
    FileStorageFilter,
    # Factory functions
    create_file_storage_filter,
    create_local_backend,
    create_search_query,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample file structure for testing"""
    # Create directories
    Path(temp_dir, "docs").mkdir()
    Path(temp_dir, "images").mkdir()
    Path(temp_dir, "code").mkdir()
    
    # Create sample files
    files = {
        "readme.txt": "This is a readme file." * 10,
        "docs/report.pdf": b"PDF content" * 100,
        "docs/data.csv": "col1,col2\n1,2\n" * 50,
        "images/photo.jpg": b"\xFF\xD8\xFF" * 50,  # JPEG marker
        "code/script.py": "print('Hello')\n" * 20,
        "code/main.js": "console.log('test');\n" * 15,
        ".hidden": "hidden file content",
    }
    
    created_files = {}
    for filename, content in files.items():
        filepath = Path(temp_dir, filename)
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(filepath, mode) as f:
            f.write(content)
        created_files[filename] = str(filepath)
    
    return created_files


@pytest.fixture
def local_backend():
    """Create LocalFileSystemBackend instance"""
    return create_local_backend()


@pytest.fixture
def file_filter(local_backend):
    """Create FileStorageFilter instance"""
    return FileStorageFilter(local_backend)


# ============================================================================
# Test FileMetadata
# ============================================================================

class TestFileMetadata:
    """Test FileMetadata dataclass"""
    
    def test_file_metadata_creation(self):
        """Test FileMetadata creation with required fields"""
        metadata = FileMetadata(
            file_id="file-123",
            path="/path/to/file.txt",
            name="file.txt",
            extension="txt",
            size_bytes=1024,
            file_type=FileType.DOCUMENT,
            mime_type="text/plain",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            accessed_at=datetime.now()
        )
        
        assert metadata.file_id == "file-123"
        assert metadata.name == "file.txt"
        assert metadata.extension == "txt"
        assert metadata.size_bytes == 1024
        assert metadata.file_type == FileType.DOCUMENT
    
    def test_file_metadata_auto_id(self):
        """Test automatic file_id generation"""
        metadata = FileMetadata(
            file_id="",  # Empty ID
            path="/path/to/file.txt",
            name="file.txt",
            extension="txt",
            size_bytes=1024,
            file_type=FileType.DOCUMENT,
            mime_type="text/plain",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            accessed_at=datetime.now()
        )
        
        assert metadata.file_id != ""
        assert metadata.file_id.startswith("file-")
        assert len(metadata.file_id) == 17  # "file-" + 12 chars
    
    def test_size_in_unit_conversion(self):
        """Test size unit conversion"""
        metadata = FileMetadata(
            file_id="file-123",
            path="/path/to/file.txt",
            name="file.txt",
            extension="txt",
            size_bytes=1024 * 1024,  # 1 MB
            file_type=FileType.DOCUMENT,
            mime_type="text/plain",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            accessed_at=datetime.now()
        )
        
        assert metadata.size_in_unit(SizeUnit.BYTES) == 1024 * 1024
        assert metadata.size_in_unit(SizeUnit.KB) == 1024
        assert metadata.size_in_unit(SizeUnit.MB) == 1
        assert metadata.size_in_unit(SizeUnit.GB) == pytest.approx(0.0009765625, rel=1e-5)
    
    def test_file_metadata_to_dict(self):
        """Test FileMetadata serialization"""
        now = datetime.now()
        metadata = FileMetadata(
            file_id="file-123",
            path="/path/to/file.txt",
            name="file.txt",
            extension="txt",
            size_bytes=2048,
            file_type=FileType.DOCUMENT,
            mime_type="text/plain",
            created_at=now,
            modified_at=now,
            accessed_at=now,
            content_hash="abc123",
            is_hidden=False,
            is_symlink=False
        )
        
        data = metadata.to_dict()
        
        assert data["file_id"] == "file-123"
        assert data["name"] == "file.txt"
        assert data["size_bytes"] == 2048
        assert data["size_mb"] == 0.0
        assert data["file_type"] == "document"
        assert data["content_hash"] == "abc123"


# ============================================================================
# Test LocalFileSystemBackend
# ============================================================================

class TestLocalFileSystemBackend:
    """Test LocalFileSystemBackend"""
    
    def test_scan_directory_non_recursive(self, local_backend, temp_dir, sample_files):
        """Test non-recursive directory scan"""
        files = local_backend.scan_directory(temp_dir, recursive=False, include_hidden=False)
        
        # Should only find files in root directory (readme.txt)
        assert len(files) >= 1
        assert any(f.name == "readme.txt" for f in files)
        assert not any(f.name == "report.pdf" for f in files)  # In subdirectory
    
    def test_scan_directory_recursive(self, local_backend, temp_dir, sample_files):
        """Test recursive directory scan"""
        files = local_backend.scan_directory(temp_dir, recursive=True, include_hidden=False)
        
        # Should find files in all subdirectories
        assert len(files) >= 6
        assert any(f.name == "readme.txt" for f in files)
        assert any(f.name == "script.py" for f in files)
        assert any(f.name == "photo.jpg" for f in files)
    
    def test_scan_directory_include_hidden(self, local_backend, temp_dir, sample_files):
        """Test scanning with hidden files"""
        files_without_hidden = local_backend.scan_directory(temp_dir, recursive=False, include_hidden=False)
        files_with_hidden = local_backend.scan_directory(temp_dir, recursive=False, include_hidden=True)
        
        # Should find more files when including hidden
        assert len(files_with_hidden) >= len(files_without_hidden)
        assert any(f.name == ".hidden" for f in files_with_hidden)
        assert not any(f.name == ".hidden" for f in files_without_hidden)
    
    def test_get_file_metadata(self, local_backend, temp_dir, sample_files):
        """Test getting metadata for single file"""
        file_path = sample_files["readme.txt"]
        metadata = local_backend.get_file_metadata(file_path)
        
        assert metadata is not None
        assert metadata.name == "readme.txt"
        assert metadata.extension == "txt"
        assert metadata.size_bytes > 0
        assert metadata.file_type == FileType.DOCUMENT
        assert metadata.path == file_path
    
    def test_get_file_metadata_nonexistent(self, local_backend, temp_dir):
        """Test getting metadata for nonexistent file"""
        metadata = local_backend.get_file_metadata(os.path.join(temp_dir, "nonexistent.txt"))
        assert metadata is None
    
    def test_file_exists(self, local_backend, temp_dir, sample_files):
        """Test file existence check"""
        assert local_backend.file_exists(sample_files["readme.txt"])
        assert not local_backend.file_exists(os.path.join(temp_dir, "nonexistent.txt"))
    
    def test_calculate_hash(self, local_backend, temp_dir, sample_files):
        """Test file hash calculation"""
        file_path = sample_files["readme.txt"]
        hash1 = local_backend.calculate_hash(file_path)
        hash2 = local_backend.calculate_hash(file_path)
        
        assert hash1 == hash2  # Same file should have same hash
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters
    
    def test_classify_file_types(self, local_backend):
        """Test file type classification"""
        assert local_backend._classify_file_type("pdf") == FileType.DOCUMENT
        assert local_backend._classify_file_type("jpg") == FileType.IMAGE
        assert local_backend._classify_file_type("py") == FileType.CODE
        assert local_backend._classify_file_type("zip") == FileType.ARCHIVE
        assert local_backend._classify_file_type("mp4") == FileType.VIDEO
        assert local_backend._classify_file_type("mp3") == FileType.AUDIO
        assert local_backend._classify_file_type("json") == FileType.DATA
        assert local_backend._classify_file_type("unknown") == FileType.OTHER
    
    def test_get_statistics(self, local_backend, temp_dir, sample_files):
        """Test directory statistics"""
        stats = local_backend.get_statistics(temp_dir)
        
        assert stats["total_files"] >= 6
        assert stats["total_size_bytes"] > 0
        assert stats["total_size_mb"] >= 0  # Can be 0 for very small files
        assert "file_types" in stats
        assert "extensions" in stats
        assert stats["directory"] == temp_dir


# ============================================================================
# Test FileSearchQuery
# ============================================================================

class TestFileSearchQuery:
    """Test FileSearchQuery"""
    
    def test_search_query_creation(self):
        """Test FileSearchQuery creation with defaults"""
        query = FileSearchQuery()
        
        assert query.path_pattern is None
        assert query.use_regex is False
        assert query.extensions == []
        assert query.include_hidden is False
        assert query.sort_by == "modified_at"
        assert query.limit is None
        assert query.offset == 0
    
    def test_search_query_with_filters(self):
        """Test FileSearchQuery with multiple filters"""
        query = FileSearchQuery(
            extensions=["py", "txt"],
            min_size_bytes=1024,
            max_size_bytes=1024 * 1024,
            file_types=[FileType.CODE, FileType.DOCUMENT],
            sort_by="size_bytes",
            sort_order=SortOrder.DESC,
            limit=10
        )
        
        assert query.extensions == ["py", "txt"]
        assert query.min_size_bytes == 1024
        assert query.max_size_bytes == 1024 * 1024
        assert FileType.CODE in query.file_types
        assert query.limit == 10
    
    def test_search_query_to_dict(self):
        """Test FileSearchQuery serialization"""
        now = datetime.now()
        query = FileSearchQuery(
            extensions=["py"],
            min_size_bytes=1024,
            modified_after=now,
            file_types=[FileType.CODE],
            sort_by="name",
            limit=5
        )
        
        data = query.to_dict()
        
        assert data["extensions"] == ["py"]
        assert data["min_size_bytes"] == 1024
        assert data["file_types"] == ["code"]
        assert data["sort_by"] == "name"
        assert data["limit"] == 5


# ============================================================================
# Test FileStorageFilter
# ============================================================================

class TestFileStorageFilter:
    """Test FileStorageFilter"""
    
    def test_search_all_files(self, file_filter, temp_dir, sample_files):
        """Test searching for all files"""
        query = FileSearchQuery()
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert len(result.files) >= 6
        assert result.total_count >= 6
        assert result.execution_time_ms > 0
    
    def test_search_by_extension(self, file_filter, temp_dir, sample_files):
        """Test filtering by extension"""
        query = FileSearchQuery(extensions=["py"])
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert all(f.extension == "py" for f in result.files)
        assert len(result.files) >= 1
    
    def test_search_multiple_extensions(self, file_filter, temp_dir, sample_files):
        """Test filtering by multiple extensions"""
        query = FileSearchQuery(extensions=["py", "txt"])
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert all(f.extension in ["py", "txt"] for f in result.files)
        assert len(result.files) >= 2
    
    def test_search_exclude_extensions(self, file_filter, temp_dir, sample_files):
        """Test excluding extensions"""
        query = FileSearchQuery(exclude_extensions=["jpg", "pdf"])
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert all(f.extension not in ["jpg", "pdf"] for f in result.files)
    
    def test_search_by_size_range(self, file_filter, temp_dir, sample_files):
        """Test filtering by size range"""
        query = FileSearchQuery(
            min_size_bytes=100,
            max_size_bytes=10000
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        for f in result.files:
            assert 100 <= f.size_bytes <= 10000
    
    def test_search_by_file_type(self, file_filter, temp_dir, sample_files):
        """Test filtering by file type"""
        query = FileSearchQuery(file_types=[FileType.CODE])
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert all(f.file_type == FileType.CODE for f in result.files)
        assert len(result.files) >= 2  # script.py and main.js
    
    def test_search_with_path_pattern_glob(self, file_filter, temp_dir, sample_files):
        """Test searching with glob pattern"""
        query = FileSearchQuery(
            path_pattern="*/code/*",
            use_regex=False
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert all("code" in f.path for f in result.files)
    
    def test_search_with_path_pattern_regex(self, file_filter, temp_dir, sample_files):
        """Test searching with regex pattern"""
        query = FileSearchQuery(
            path_pattern=r".*\.(py|js)$",
            use_regex=True
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert all(f.extension in ["py", "js"] for f in result.files)
    
    def test_search_sort_by_name_asc(self, file_filter, temp_dir, sample_files):
        """Test sorting by name ascending"""
        query = FileSearchQuery(
            sort_by="name",
            sort_order=SortOrder.ASC
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        names = [f.name for f in result.files]
        assert names == sorted(names, key=str.lower)
    
    def test_search_sort_by_size_desc(self, file_filter, temp_dir, sample_files):
        """Test sorting by size descending"""
        query = FileSearchQuery(
            sort_by="size_bytes",
            sort_order=SortOrder.DESC
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        sizes = [f.size_bytes for f in result.files]
        assert sizes == sorted(sizes, reverse=True)
    
    def test_search_with_limit(self, file_filter, temp_dir, sample_files):
        """Test search with result limit"""
        query = FileSearchQuery(limit=3)
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert len(result.files) <= 3
        assert result.total_count >= len(result.files)
    
    def test_search_with_offset(self, file_filter, temp_dir, sample_files):
        """Test search with pagination offset"""
        query1 = FileSearchQuery(limit=2, offset=0)
        result1 = file_filter.search(query1, temp_dir)
        
        query2 = FileSearchQuery(limit=2, offset=2)
        result2 = file_filter.search(query2, temp_dir)
        
        assert result1.success and result2.success
        # Different results due to offset
        if result1.files and result2.files:
            assert result1.files[0].file_id != result2.files[0].file_id
    
    def test_search_include_hidden(self, file_filter, temp_dir, sample_files):
        """Test including hidden files in search"""
        query = FileSearchQuery(include_hidden=True)
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        hidden_files = [f for f in result.files if f.is_hidden]
        assert len(hidden_files) >= 1
    
    def test_filter_by_extension_shortcut(self, file_filter, temp_dir, sample_files):
        """Test quick filter_by_extension method"""
        files = file_filter.filter_by_extension(["py"], temp_dir)
        
        assert len(files) >= 1
        assert all(f.extension == "py" for f in files)
    
    def test_filter_by_size_range_shortcut(self, file_filter, temp_dir, sample_files):
        """Test quick filter_by_size_range method"""
        files = file_filter.filter_by_size_range(min_mb=0.0001, max_mb=0.1, base_directory=temp_dir)
        
        assert len(files) >= 1
        for f in files:
            assert f.size_bytes >= 100  # ~0.0001 MB
            assert f.size_bytes <= 100000  # ~0.1 MB
    
    def test_filter_by_type_shortcut(self, file_filter, temp_dir, sample_files):
        """Test quick filter_by_type method"""
        files = file_filter.filter_by_type([FileType.IMAGE], temp_dir)
        
        assert all(f.file_type == FileType.IMAGE for f in files)
    
    def test_get_statistics(self, file_filter, temp_dir, sample_files):
        """Test statistics generation"""
        stats = file_filter.get_statistics(temp_dir)
        
        assert stats["total_files"] >= 6
        assert stats["total_size_bytes"] > 0
        assert "file_types" in stats
        assert "extensions" in stats


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_scan_nonexistent_directory(self, local_backend):
        """Test scanning nonexistent directory"""
        files = local_backend.scan_directory("/nonexistent/path")
        assert files == []
    
    def test_metadata_for_directory(self, local_backend, temp_dir):
        """Test getting metadata for directory (should return None)"""
        metadata = local_backend.get_file_metadata(temp_dir)
        assert metadata is None
    
    def test_search_empty_directory(self, file_filter, temp_dir):
        """Test searching empty directory"""
        empty_dir = os.path.join(temp_dir, "empty")
        os.makedirs(empty_dir)
        
        query = FileSearchQuery()
        result = file_filter.search(query, empty_dir)
        
        assert result.success
        assert len(result.files) == 0
    
    def test_search_with_invalid_sort_field(self, file_filter, temp_dir, sample_files):
        """Test search with invalid sort field (should not crash)"""
        query = FileSearchQuery(sort_by="invalid_field")
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        # Should return unsorted results without error
    
    def test_hash_calculation_for_large_file(self, local_backend, temp_dir):
        """Test hash calculation for larger file"""
        large_file = os.path.join(temp_dir, "large.dat")
        with open(large_file, 'wb') as f:
            f.write(b"x" * (1024 * 1024))  # 1 MB
        
        hash_value = local_backend.calculate_hash(large_file)
        assert len(hash_value) == 64
        assert hash_value != ""
    
    def test_hash_calculation_for_nonexistent_file(self, local_backend):
        """Test hash calculation for nonexistent file"""
        hash_value = local_backend.calculate_hash("/nonexistent/file.txt")
        assert hash_value == ""


# ============================================================================
# Test Factory Functions
# ============================================================================

class TestFactoryFunctions:
    """Test factory functions"""
    
    def test_create_file_storage_filter_default(self):
        """Test creating filter with default backend"""
        file_filter = create_file_storage_filter()
        
        assert isinstance(file_filter, FileStorageFilter)
        assert isinstance(file_filter.backend, LocalFileSystemBackend)
    
    def test_create_file_storage_filter_custom_backend(self):
        """Test creating filter with custom backend"""
        backend = create_local_backend()
        file_filter = create_file_storage_filter(backend)
        
        assert isinstance(file_filter, FileStorageFilter)
        assert file_filter.backend is backend
    
    def test_create_local_backend(self):
        """Test creating local backend"""
        backend = create_local_backend()
        
        assert isinstance(backend, LocalFileSystemBackend)
        assert hasattr(backend, 'scan_directory')
        assert hasattr(backend, 'get_file_metadata')
    
    def test_create_search_query(self):
        """Test creating search query"""
        query = create_search_query(
            extensions=["py"],
            min_size_bytes=1024,
            limit=10
        )
        
        assert isinstance(query, FileSearchQuery)
        assert query.extensions == ["py"]
        assert query.min_size_bytes == 1024
        assert query.limit == 10


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    def test_find_large_python_files(self, file_filter, temp_dir, sample_files):
        """Test finding large Python files"""
        query = FileSearchQuery(
            extensions=["py"],
            min_size_bytes=100,
            sort_by="size_bytes",
            sort_order=SortOrder.DESC
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        if result.files:
            assert result.files[0].extension == "py"
            # Largest file should be first
            if len(result.files) > 1:
                assert result.files[0].size_bytes >= result.files[1].size_bytes
    
    def test_find_recently_modified_files(self, file_filter, temp_dir, sample_files):
        """Test finding recently modified files"""
        # Files just created should be recent
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        query = FileSearchQuery(
            modified_after=one_hour_ago,
            sort_by="modified_at",
            sort_order=SortOrder.DESC
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        assert len(result.files) >= 6  # All sample files should be recent
    
    def test_complex_multi_criteria_search(self, file_filter, temp_dir, sample_files):
        """Test complex search with multiple criteria"""
        query = FileSearchQuery(
            extensions=["py", "txt", "csv"],
            min_size_bytes=50,
            file_types=[FileType.CODE, FileType.DOCUMENT, FileType.DATA],
            include_hidden=False,
            sort_by="name",
            limit=5
        )
        result = file_filter.search(query, temp_dir)
        
        assert result.success
        for f in result.files:
            assert f.extension in ["py", "txt", "csv"]
            assert f.size_bytes >= 50
            assert f.file_type in [FileType.CODE, FileType.DOCUMENT, FileType.DATA]
            assert not f.is_hidden


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
