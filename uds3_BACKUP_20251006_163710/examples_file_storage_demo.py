"""
File Storage Filter Demo Script

This script demonstrates comprehensive file storage filtering capabilities
provided by the File Storage Filter module.

Features demonstrated:
1. Basic file scanning (recursive/non-recursive)
2. Extension filtering (single, multiple, exclude)
3. Size filtering (range queries with unit conversions)
4. Date filtering (created, modified ranges)
5. Type filtering (FileType enum)
6. Pattern matching (glob and regex)
7. Sorting and pagination
8. Advanced multi-criteria search
9. Duplicate detection (by hash and size)
10. Statistics generation
11. UDS3 Core integration

Author: UDS3 Development Team
Date: October 2025
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from uds3_file_storage_filter import (
        FileMetadata, FileSearchQuery, FileFilterResult,
        FileType, SizeUnit, SortOrder,
        create_file_storage_filter, create_local_backend, create_search_query,
    )
    from uds3_core import UnifiedDatabaseStrategy
    
    FILE_STORAGE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Error importing File Storage Filter: {e}")
    FILE_STORAGE_AVAILABLE = False
    sys.exit(1)


def print_section_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_file_details(files: List[FileMetadata], max_display: int = 5):
    """Print file details in formatted table."""
    if not files:
        print("  (No files found)")
        return
    
    print(f"\n  Found {len(files)} file(s):\n")
    
    for i, file in enumerate(files[:max_display], 1):
        size_kb = file.size_in_unit(SizeUnit.KB)
        print(f"  {i:2d}. {file.name:40s} | {size_kb:10.2f} KB | {file.file_type.value:12s}")
    
    if len(files) > max_display:
        print(f"  ... and {len(files) - max_display} more")


def print_statistics(stats: Dict[str, Any]):
    """Print directory statistics."""
    print(f"\n  Total Files:     {stats['total_files']}")
    print(f"  Total Size:      {stats['total_size_mb']:.2f} MB ({stats['total_size_gb']:.4f} GB)")
    print(f"\n  File Types:")
    for file_type, count in stats['file_types'].items():
        print(f"    - {file_type:12s}: {count:4d} files")
    print(f"\n  Top 5 Extensions:")
    sorted_exts = sorted(stats['extensions'].items(), key=lambda x: x[1], reverse=True)[:5]
    for ext, count in sorted_exts:
        ext_display = ext if ext else "(no extension)"
        print(f"    - {ext_display:12s}: {count:4d} files")


# ==================================================================
# Demo 1: Basic File Scanning
# ==================================================================

def demo_basic_scanning():
    """Demonstrate basic directory scanning."""
    print_section_header("Demo 1: Basic File Scanning")
    
    backend = create_local_backend()
    
    # Scan current directory (non-recursive)
    print("\n[1.1] Non-recursive scan of current directory:")
    files = backend.scan_directory(".", recursive=False, include_hidden=False)
    print(f"  Found {len(files)} files in current directory")
    print_file_details(files, max_display=3)
    
    # Scan recursively
    print("\n[1.2] Recursive scan (including subdirectories):")
    files_recursive = backend.scan_directory(".", recursive=True, include_hidden=False)
    print(f"  Found {len(files_recursive)} files total (recursive)")
    
    # Scan with hidden files
    print("\n[1.3] Scan including hidden files:")
    files_with_hidden = backend.scan_directory(".", recursive=False, include_hidden=True)
    hidden_count = len(files_with_hidden) - len(files)
    print(f"  Found {hidden_count} hidden files")


# ==================================================================
# Demo 2: Extension Filtering
# ==================================================================

def demo_extension_filtering():
    """Demonstrate extension-based filtering."""
    print_section_header("Demo 2: Extension Filtering")
    
    file_filter = create_file_storage_filter()
    
    # Single extension
    print("\n[2.1] Filter Python files only:")
    py_files = file_filter.filter_by_extension(["py"], ".", limit=10)
    print_file_details(py_files)
    
    # Multiple extensions
    print("\n[2.2] Filter Python and Markdown files:")
    code_files = file_filter.filter_by_extension(["py", "md"], ".", limit=10)
    print_file_details(code_files)
    
    # Exclude extensions
    print("\n[2.3] All files EXCEPT Python files:")
    query = create_search_query(
        exclude_extensions=["py", "pyc"],
        limit=10
    )
    result = file_filter.search(query, ".")
    print(f"  Found {result.filtered_count} non-Python files")
    print_file_details(result.files)


# ==================================================================
# Demo 3: Size Filtering
# ==================================================================

def demo_size_filtering():
    """Demonstrate size-based filtering."""
    print_section_header("Demo 3: Size Filtering")
    
    file_filter = create_file_storage_filter()
    
    # Files larger than 10KB
    print("\n[3.1] Files larger than 10 KB:")
    large_files = file_filter.filter_by_size_range(min_mb=0.01, max_mb=None, base_directory=".", limit=10)
    print_file_details(large_files)
    
    # Files in specific size range (100KB - 500KB)
    print("\n[3.2] Files between 100 KB and 500 KB:")
    medium_files = file_filter.filter_by_size_range(min_mb=0.1, max_mb=0.5, base_directory=".", limit=10)
    print_file_details(medium_files)
    
    # Very small files (< 1KB)
    print("\n[3.3] Very small files (< 1 KB):")
    query = create_search_query(
        max_size_bytes=1024,
        sort_by="size_bytes",
        sort_order=SortOrder.ASC,
        limit=5
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)


# ==================================================================
# Demo 4: Date Filtering
# ==================================================================

def demo_date_filtering():
    """Demonstrate date-based filtering."""
    print_section_header("Demo 4: Date Filtering")
    
    file_filter = create_file_storage_filter()
    
    # Files modified in last 7 days
    print("\n[4.1] Files modified in last 7 days:")
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_files = file_filter.filter_by_date_range(
        modified_after=seven_days_ago,
        modified_before=None,
        base_directory=".",
        limit=10
    )
    print_file_details(recent_files)
    
    # Files modified in last 24 hours
    print("\n[4.2] Files modified in last 24 hours:")
    yesterday = datetime.now() - timedelta(hours=24)
    very_recent = file_filter.filter_by_date_range(
        modified_after=yesterday,
        modified_before=None,
        base_directory=".",
        limit=10
    )
    print_file_details(very_recent)
    
    # Files older than 30 days
    print("\n[4.3] Files older than 30 days:")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    old_files = file_filter.filter_by_date_range(
        modified_after=None,
        modified_before=thirty_days_ago,
        base_directory=".",
        limit=10
    )
    print_file_details(old_files)


# ==================================================================
# Demo 5: Type Filtering
# ==================================================================

def demo_type_filtering():
    """Demonstrate file type filtering."""
    print_section_header("Demo 5: Type Filtering")
    
    file_filter = create_file_storage_filter()
    
    # Code files
    print("\n[5.1] Code files (Python, JavaScript, etc.):")
    code_files = file_filter.filter_by_type([FileType.CODE], ".", limit=10)
    print_file_details(code_files)
    
    # Document files
    print("\n[5.2] Document files (PDF, TXT, MD, etc.):")
    doc_files = file_filter.filter_by_type([FileType.DOCUMENT], ".", limit=10)
    print_file_details(doc_files)
    
    # Data files
    print("\n[5.3] Data files (JSON, XML, CSV, etc.):")
    data_files = file_filter.filter_by_type([FileType.DATA], ".", limit=10)
    print_file_details(data_files)
    
    # Multiple types
    print("\n[5.4] Code AND Data files:")
    combined = file_filter.filter_by_type([FileType.CODE, FileType.DATA], ".", limit=10)
    print_file_details(combined)


# ==================================================================
# Demo 6: Pattern Matching
# ==================================================================

def demo_pattern_matching():
    """Demonstrate glob and regex pattern matching."""
    print_section_header("Demo 6: Pattern Matching")
    
    file_filter = create_file_storage_filter()
    
    # Glob pattern
    print("\n[6.1] Glob pattern: '*.py' (Python files):")
    query = create_search_query(
        path_pattern="*.py",
        use_regex=False,
        limit=10
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)
    
    # Glob pattern with wildcards
    print("\n[6.2] Glob pattern: 'test_*.py' (test files):")
    query = create_search_query(
        path_pattern="test_*.py",
        use_regex=False,
        limit=10
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)
    
    # Regex pattern
    print("\n[6.3] Regex pattern: r'.*\\.py$' (Python files):")
    query = create_search_query(
        path_pattern=r".*\.py$",
        use_regex=True,
        limit=10
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)
    
    # Complex regex
    print("\n[6.4] Regex pattern: r'^(uds3|examples)_.*\\.py$' (UDS3/examples modules):")
    query = create_search_query(
        path_pattern=r"^(uds3|examples)_.*\.py$",
        use_regex=True,
        limit=10
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)


# ==================================================================
# Demo 7: Sorting and Pagination
# ==================================================================

def demo_sorting_pagination():
    """Demonstrate sorting and pagination."""
    print_section_header("Demo 7: Sorting and Pagination")
    
    file_filter = create_file_storage_filter()
    
    # Sort by name (ascending)
    print("\n[7.1] Sort by name (A-Z):")
    query = create_search_query(
        extensions=["py"],
        sort_by="name",
        sort_order=SortOrder.ASC,
        limit=5
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)
    
    # Sort by size (descending)
    print("\n[7.2] Sort by size (largest first):")
    query = create_search_query(
        extensions=["py"],
        sort_by="size_bytes",
        sort_order=SortOrder.DESC,
        limit=5
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)
    
    # Sort by modified date (most recent first)
    print("\n[7.3] Sort by modified date (most recent first):")
    query = create_search_query(
        extensions=["py"],
        sort_by="modified_at",
        sort_order=SortOrder.DESC,
        limit=5
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)
    
    # Pagination: Page 1
    print("\n[7.4] Pagination - Page 1 (items 1-5):")
    query = create_search_query(
        extensions=["py"],
        sort_by="name",
        sort_order=SortOrder.ASC,
        limit=5,
        offset=0
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)
    
    # Pagination: Page 2
    print("\n[7.5] Pagination - Page 2 (items 6-10):")
    query = create_search_query(
        extensions=["py"],
        sort_by="name",
        sort_order=SortOrder.ASC,
        limit=5,
        offset=5
    )
    result = file_filter.search(query, ".")
    print_file_details(result.files)


# ==================================================================
# Demo 8: Advanced Multi-Criteria Search
# ==================================================================

def demo_advanced_search():
    """Demonstrate complex multi-criteria search."""
    print_section_header("Demo 8: Advanced Multi-Criteria Search")
    
    file_filter = create_file_storage_filter()
    
    # Complex search: Large Python files modified recently
    print("\n[8.1] Complex search: Python files > 50KB modified in last 30 days:")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    query = create_search_query(
        extensions=["py"],
        min_size_bytes=50 * 1024,  # 50 KB
        modified_after=thirty_days_ago,
        sort_by="size_bytes",
        sort_order=SortOrder.DESC,
        limit=10
    )
    result = file_filter.search(query, ".")
    print(f"  Execution time: {result.execution_time_ms:.2f} ms")
    print_file_details(result.files)
    
    # Multi-type search with size constraint
    print("\n[8.2] Code OR Data files between 10-100 KB:")
    query = create_search_query(
        file_types=[FileType.CODE, FileType.DATA],
        min_size_bytes=10 * 1024,
        max_size_bytes=100 * 1024,
        sort_by="size_bytes",
        sort_order=SortOrder.DESC,
        limit=10
    )
    result = file_filter.search(query, ".")
    print(f"  Execution time: {result.execution_time_ms:.2f} ms")
    print_file_details(result.files)
    
    # Pattern + size + date combination
    print("\n[8.3] 'test_*.py' files > 5KB modified in last 7 days:")
    seven_days_ago = datetime.now() - timedelta(days=7)
    query = create_search_query(
        path_pattern="test_*.py",
        use_regex=False,
        min_size_bytes=5 * 1024,
        modified_after=seven_days_ago,
        sort_by="modified_at",
        sort_order=SortOrder.DESC,
        limit=10
    )
    result = file_filter.search(query, ".")
    print(f"  Execution time: {result.execution_time_ms:.2f} ms")
    print_file_details(result.files)


# ==================================================================
# Demo 9: Duplicate Detection
# ==================================================================

def demo_duplicate_detection():
    """Demonstrate duplicate file detection."""
    print_section_header("Demo 9: Duplicate Detection")
    
    file_filter = create_file_storage_filter()
    
    # Find duplicates by hash
    print("\n[9.1] Find duplicate files by content hash:")
    duplicates_by_hash = file_filter.find_duplicates(".", by_hash=True)
    
    if duplicates_by_hash:
        print(f"  Found {len(duplicates_by_hash)} groups of duplicate files:")
        for hash_value, files in list(duplicates_by_hash.items())[:3]:
            print(f"\n  Hash: {hash_value[:16]}...")
            print_file_details(files)
    else:
        print("  No duplicate files found (by content hash)")
    
    # Find duplicates by size
    print("\n[9.2] Find potential duplicates by size:")
    duplicates_by_size = file_filter.find_duplicates(".", by_hash=False)
    
    if duplicates_by_size:
        print(f"  Found {len(duplicates_by_size)} groups of files with same size:")
        # Show only files with multiple entries
        groups_shown = 0
        for size, files in duplicates_by_size.items():
            if len(files) > 1 and groups_shown < 3:
                print(f"\n  Size: {int(size) / 1024:.2f} KB")
                print_file_details(files)
                groups_shown += 1
        
        if groups_shown == 0:
            print("  (All size groups have only 1 file)")
    else:
        print("  No files with duplicate sizes found")


# ==================================================================
# Demo 10: Statistics Generation
# ==================================================================

def demo_statistics():
    """Demonstrate directory statistics."""
    print_section_header("Demo 10: Statistics Generation")
    
    file_filter = create_file_storage_filter()
    
    # Current directory stats
    print("\n[10.1] Statistics for current directory:")
    stats = file_filter.get_statistics(".")
    print_statistics(stats)
    
    # Subdirectory stats (if tests/ exists)
    if os.path.exists("tests"):
        print("\n[10.2] Statistics for tests/ directory:")
        test_stats = file_filter.get_statistics("tests")
        print_statistics(test_stats)


# ==================================================================
# Demo 11: UDS3 Core Integration
# ==================================================================

def demo_uds3_integration():
    """Demonstrate UDS3 Core integration methods."""
    print_section_header("Demo 11: UDS3 Core Integration")
    
    # Initialize UDS3 Core
    print("\n[11.1] Initialize UDS3 Core with File Storage Filter:")
    core = UnifiedDatabaseStrategy()
    print("  ✓ UDS3 Core initialized")
    
    # Create filter via UDS3 Core
    print("\n[11.2] Create file filter via UDS3 Core:")
    file_filter = core.create_file_storage_filter()
    if file_filter:
        print("  ✓ File filter created successfully")
    
    # Use convenience method: filter by extension
    print("\n[11.3] Use UDS3 convenience method - filter Python files:")
    py_files = core.filter_files_by_extension(["py"], ".", limit=5)
    print_file_details(py_files)
    
    # Use convenience method: get statistics
    print("\n[11.4] Use UDS3 convenience method - get statistics:")
    stats = core.get_file_statistics(".")
    if stats:
        print(f"  Total files: {stats['total_files']}")
        print(f"  Total size:  {stats['total_size_mb']:.2f} MB")
    
    # Use convenience method: get file metadata
    print("\n[11.5] Use UDS3 convenience method - get file metadata:")
    if py_files:
        first_file = py_files[0]
        metadata = core.get_file_metadata(first_file.path)
        if metadata:
            print(f"  File:        {metadata.name}")
            print(f"  Size:        {metadata.size_in_unit(SizeUnit.KB):.2f} KB")
            print(f"  Type:        {metadata.file_type.value}")
            print(f"  Modified:    {metadata.modified_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Use search method with query
    print("\n[11.6] Use UDS3 search method with query:")
    result = core.search_files(
        base_directory=".",
        extensions=["py", "md"],
        min_size_bytes=10 * 1024,
        sort_by="size_bytes",
        sort_order=SortOrder.DESC,
        limit=5
    )
    if result:
        print(f"  Found {result.filtered_count} files in {result.execution_time_ms:.2f} ms")
        print_file_details(result.files)


# ==================================================================
# Main Execution
# ==================================================================

def main():
    """Execute all demo sections."""
    print("\n" + "=" * 80)
    print("  FILE STORAGE FILTER - COMPREHENSIVE DEMO")
    print("  UDS3 Module: uds3_file_storage_filter.py")
    print("=" * 80)
    
    if not FILE_STORAGE_AVAILABLE:
        print("\n❌ File Storage Filter module not available!")
        return
    
    print("\n✓ File Storage Filter module loaded successfully")
    print(f"✓ Working directory: {os.getcwd()}")
    
    try:
        # Run all demos
        demo_basic_scanning()
        demo_extension_filtering()
        demo_size_filtering()
        demo_date_filtering()
        demo_type_filtering()
        demo_pattern_matching()
        demo_sorting_pagination()
        demo_advanced_search()
        demo_duplicate_detection()
        demo_statistics()
        demo_uds3_integration()
        
        # Final summary
        print("\n" + "=" * 80)
        print("  DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\n✓ All 11 demo sections executed")
        print("✓ File Storage Filter fully operational")
        print("\nFeatures demonstrated:")
        print("  • Basic file scanning (recursive/non-recursive)")
        print("  • Extension filtering (include/exclude)")
        print("  • Size filtering (range queries)")
        print("  • Date filtering (created/modified ranges)")
        print("  • Type filtering (FileType enum)")
        print("  • Pattern matching (glob and regex)")
        print("  • Sorting (name/size/date)")
        print("  • Pagination (limit/offset)")
        print("  • Advanced multi-criteria search")
        print("  • Duplicate detection (hash/size)")
        print("  • Statistics generation")
        print("  • UDS3 Core integration")
        print("\n" + "=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during demo execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
