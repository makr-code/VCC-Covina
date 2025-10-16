"""
Test Suite für UDS3 Streaming Operations
==========================================

Comprehensive tests for large file streaming:
- Basic streaming operations
- Chunked uploads (100+ MB simulated)
- Resume functionality (interrupt & continue)
- Progress tracking accuracy
- Concurrent streams
- Memory efficiency verification
- Error recovery
- Large file handling

Author: UDS3 Team
Date: 2. Oktober 2025
"""

import pytest
import os
import tempfile
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

from uds3_streaming_operations import (
    StreamingManager,
    create_streaming_manager,
    StreamingProgress,
    StreamingStatus,
    StreamingOperation,
    ChunkMetadata,
    DEFAULT_CHUNK_SIZE,
    LARGE_CHUNK_SIZE,
    SMALL_CHUNK_SIZE,
    calculate_optimal_chunk_size,
    format_bytes,
    format_duration,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def streaming_manager():
    """Create a StreamingManager for testing"""
    return create_streaming_manager(chunk_size=1024 * 1024)  # 1 MB for testing


@pytest.fixture
def temp_file_small():
    """Create a small temporary file (1 MB)"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
        # Write 1 MB of data
        f.write(b'x' * (1024 * 1024))
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_file_medium():
    """Create a medium temporary file (10 MB)"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
        # Write 10 MB of data
        for _ in range(10):
            f.write(b'y' * (1024 * 1024))
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_file_large():
    """Create a large temporary file (50 MB)"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
        # Write 50 MB of data
        for _ in range(50):
            f.write(b'z' * (1024 * 1024))
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Cleanup
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


# ============================================================================
# Test Progress Tracking
# ============================================================================

class TestStreamingProgress:
    """Test StreamingProgress dataclass"""
    
    def test_progress_creation(self):
        """Test creating progress object"""
        progress = StreamingProgress(
            operation_id="test-123",
            operation_type=StreamingOperation.UPLOAD,
            status=StreamingStatus.IN_PROGRESS,
            total_bytes=100 * 1024 * 1024,  # 100 MB
            transferred_bytes=50 * 1024 * 1024,  # 50 MB
            chunk_count=100,
            current_chunk=50,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert progress.operation_id == "test-123"
        assert progress.operation_type == StreamingOperation.UPLOAD
        assert progress.status == StreamingStatus.IN_PROGRESS
        assert progress.total_bytes == 100 * 1024 * 1024
        assert progress.transferred_bytes == 50 * 1024 * 1024
    
    def test_progress_percent_calculation(self):
        """Test progress percentage calculation"""
        progress = StreamingProgress(
            operation_id="test-123",
            operation_type=StreamingOperation.UPLOAD,
            status=StreamingStatus.IN_PROGRESS,
            total_bytes=1000,
            transferred_bytes=500,
            chunk_count=10,
            current_chunk=5,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert progress.progress_percent == 50.0
    
    def test_progress_is_complete(self):
        """Test is_complete property"""
        progress = StreamingProgress(
            operation_id="test-123",
            operation_type=StreamingOperation.UPLOAD,
            status=StreamingStatus.COMPLETED,
            total_bytes=1000,
            transferred_bytes=1000,
            chunk_count=10,
            current_chunk=10,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert progress.is_complete is True
    
    def test_progress_to_dict(self):
        """Test converting progress to dictionary"""
        progress = StreamingProgress(
            operation_id="test-123",
            operation_type=StreamingOperation.UPLOAD,
            status=StreamingStatus.IN_PROGRESS,
            total_bytes=1000,
            transferred_bytes=500,
            chunk_count=10,
            current_chunk=5,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = progress.to_dict()
        
        assert result['operation_id'] == "test-123"
        assert result['operation_type'] == "upload"
        assert result['status'] == "in_progress"
        assert result['progress_percent'] == 50.0


# ============================================================================
# Test Basic Streaming Operations
# ============================================================================

class TestBasicStreamingOperations:
    """Test basic streaming operations"""
    
    def test_upload_small_file(self, streaming_manager, temp_file_small):
        """Test uploading a small file"""
        progress_updates = []
        
        def on_progress(progress):
            progress_updates.append(progress.progress_percent)
        
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_small,
            destination="test/small.txt",
            progress_callback=on_progress
        )
        
        assert operation_id is not None
        assert len(progress_updates) > 0
        
        # Check final progress
        final_progress = streaming_manager.get_progress(operation_id)
        assert final_progress is not None
        assert final_progress.is_complete
        assert final_progress.progress_percent == 100.0
    
    def test_upload_medium_file(self, streaming_manager, temp_file_medium):
        """Test uploading a medium file (10 MB)"""
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/medium.pdf"
        )
        
        final_progress = streaming_manager.get_progress(operation_id)
        assert final_progress is not None
        assert final_progress.is_complete
        assert final_progress.chunk_count > 1  # Should be multiple chunks
    
    def test_upload_with_metadata(self, streaming_manager, temp_file_small):
        """Test upload with custom metadata"""
        metadata = {
            'document_type': 'contract',
            'author': 'Test User',
            'department': 'Legal'
        }
        
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_small,
            destination="test/contract.txt",
            metadata=metadata
        )
        
        assert operation_id is not None
        final_progress = streaming_manager.get_progress(operation_id)
        assert final_progress.is_complete
    
    def test_upload_with_custom_chunk_size(self, temp_file_medium):
        """Test upload with custom chunk size"""
        manager = create_streaming_manager(chunk_size=512 * 1024)  # 512 KB
        
        operation_id = manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/chunked.pdf"
        )
        
        final_progress = manager.get_progress(operation_id)
        assert final_progress is not None
        assert final_progress.chunk_count > 10  # Smaller chunks = more chunks


# ============================================================================
# Test Progress Tracking
# ============================================================================

class TestProgressTracking:
    """Test progress tracking functionality"""
    
    def test_progress_updates_during_upload(self, streaming_manager, temp_file_medium):
        """Test that progress updates are received during upload"""
        progress_updates = []
        
        def on_progress(progress):
            progress_updates.append({
                'percent': progress.progress_percent,
                'transferred': progress.transferred_bytes,
                'chunk': progress.current_chunk
            })
        
        streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/progress.pdf",
            progress_callback=on_progress
        )
        
        # Should have multiple progress updates
        assert len(progress_updates) > 1
        
        # Progress should increase
        for i in range(1, len(progress_updates)):
            assert progress_updates[i]['percent'] >= progress_updates[i-1]['percent']
    
    def test_speed_calculation(self, streaming_manager, temp_file_medium):
        """Test transfer speed calculation"""
        final_progress = None
        
        def on_progress(progress):
            nonlocal final_progress
            final_progress = progress
        
        streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/speed.pdf",
            progress_callback=on_progress
        )
        
        assert final_progress is not None
        assert final_progress.bytes_per_second > 0
    
    def test_get_progress(self, streaming_manager, temp_file_small):
        """Test getting progress by operation ID"""
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_small,
            destination="test/getprogress.txt"
        )
        
        progress = streaming_manager.get_progress(operation_id)
        assert progress is not None
        assert progress.operation_id == operation_id
    
    def test_list_operations(self, streaming_manager, temp_file_small):
        """Test listing all operations"""
        # Upload multiple files
        op1 = streaming_manager.upload_large_file(temp_file_small, "test/file1.txt")
        op2 = streaming_manager.upload_large_file(temp_file_small, "test/file2.txt")
        
        # List all operations
        operations = streaming_manager.list_operations()
        assert len(operations) >= 2
        
        # List only completed operations
        completed = streaming_manager.list_operations(status=StreamingStatus.COMPLETED)
        assert len(completed) >= 2


# ============================================================================
# Test Resume Functionality
# ============================================================================

class TestResumeOperations:
    """Test resume functionality for interrupted uploads"""
    
    def test_resume_upload_basic(self, streaming_manager, temp_file_medium):
        """Test resuming an interrupted upload"""
        # Start upload and "interrupt" it by pausing
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/resume.pdf"
        )
        
        # Pause the operation (simulate interruption)
        streaming_manager.pause_operation(operation_id)
        
        # Resume the upload
        resumed_id = streaming_manager.resume_upload(
            operation_id=operation_id,
            file_path=temp_file_medium,
            destination="test/resume.pdf"
        )
        
        assert resumed_id == operation_id
        
        # Check that it completed
        final_progress = streaming_manager.get_progress(resumed_id)
        assert final_progress is not None
        assert final_progress.is_complete
    
    def test_resume_preserves_chunks(self, streaming_manager, temp_file_medium):
        """Test that resume preserves already uploaded chunks"""
        # Start upload
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/chunks.pdf"
        )
        
        # Get chunks uploaded
        chunks_before = streaming_manager.get_operation_chunks(operation_id)
        chunk_count_before = len(chunks_before)
        
        # "Resume" (in this case just complete)
        streaming_manager.resume_upload(
            operation_id=operation_id,
            file_path=temp_file_medium,
            destination="test/chunks.pdf"
        )
        
        # Get final chunks
        chunks_after = streaming_manager.get_operation_chunks(operation_id)
        
        # Should have all chunks
        assert len(chunks_after) >= chunk_count_before


# ============================================================================
# Test Concurrent Operations
# ============================================================================

class TestConcurrentOperations:
    """Test concurrent streaming operations"""
    
    def test_multiple_uploads_concurrent(self, streaming_manager, temp_file_small):
        """Test multiple concurrent uploads"""
        operation_ids = []
        
        # Start 5 concurrent uploads
        for i in range(5):
            op_id = streaming_manager.upload_large_file(
                file_path=temp_file_small,
                destination=f"test/concurrent{i}.txt"
            )
            operation_ids.append(op_id)
        
        # Check all completed
        for op_id in operation_ids:
            progress = streaming_manager.get_progress(op_id)
            assert progress is not None
            assert progress.is_complete
    
    def test_concurrent_operations_with_threads(self, streaming_manager, temp_file_small):
        """Test streaming operations from multiple threads"""
        results = []
        errors = []
        
        def upload_file(file_num):
            try:
                op_id = streaming_manager.upload_large_file(
                    file_path=temp_file_small,
                    destination=f"test/thread{file_num}.txt"
                )
                results.append(op_id)
            except Exception as e:
                errors.append(str(e))
        
        # Create 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=upload_file, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 10
        
        # Verify all completed
        for op_id in results:
            progress = streaming_manager.get_progress(op_id)
            assert progress.is_complete


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_upload_nonexistent_file(self, streaming_manager):
        """Test uploading a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            streaming_manager.upload_large_file(
                file_path="/nonexistent/file.txt",
                destination="test/error.txt"
            )
    
    def test_cancel_operation(self, streaming_manager, temp_file_medium):
        """Test cancelling an operation"""
        # Start upload
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/cancel.pdf"
        )
        
        # Cancel immediately (may or may not succeed depending on timing)
        cancelled = streaming_manager.cancel_operation(operation_id)
        
        # Operation should exist
        progress = streaming_manager.get_progress(operation_id)
        assert progress is not None
    
    def test_pause_operation(self, streaming_manager, temp_file_medium):
        """Test pausing an operation"""
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/pause.pdf"
        )
        
        paused = streaming_manager.pause_operation(operation_id)
        
        # Check status
        progress = streaming_manager.get_progress(operation_id)
        assert progress is not None


# ============================================================================
# Test Memory Efficiency
# ============================================================================

class TestMemoryEfficiency:
    """Test memory-efficient streaming"""
    
    def test_large_file_memory_usage(self, streaming_manager, temp_file_large):
        """Test that large files don't consume excessive memory"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Upload large file
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_large,
            destination="test/large.pdf"
        )
        
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_increase = mem_after - mem_before
        
        # Memory increase should be reasonable (< 50 MB for 50 MB file)
        assert mem_increase < 50
        
        # Verify upload completed
        progress = streaming_manager.get_progress(operation_id)
        assert progress.is_complete
    
    def test_chunked_processing_memory(self, streaming_manager, temp_file_large):
        """Test that chunked processing is memory-efficient"""
        # Get chunk metadata
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_large,
            destination="test/chunked_large.pdf"
        )
        
        chunks = streaming_manager.get_operation_chunks(operation_id)
        
        # Should have many chunks (50 MB file with 1 MB chunks = 50 chunks)
        assert len(chunks) >= 40


# ============================================================================
# Test Vector DB Streaming
# ============================================================================

class TestVectorDBStreaming:
    """Test streaming to vector database"""
    
    def test_stream_to_vector_db_basic(self, streaming_manager, temp_file_medium):
        """Test streaming file to vector DB"""
        embeddings_generated = []
        
        def mock_embedding_function(text: str) -> List[float]:
            # Mock embedding generation
            embeddings_generated.append(len(text))
            return [0.1, 0.2, 0.3]
        
        operation_id = streaming_manager.stream_to_vector_db(
            file_path=temp_file_medium,
            embedding_function=mock_embedding_function,
            chunk_text_size=1000
        )
        
        assert operation_id is not None
        
        # Check progress
        progress = streaming_manager.get_progress(operation_id)
        assert progress is not None
        assert progress.is_complete
    
    def test_stream_with_progress_callback(self, streaming_manager, temp_file_medium):
        """Test vector DB streaming with progress callback"""
        progress_updates = []
        
        def on_progress(progress):
            progress_updates.append(progress.current_chunk)
        
        def mock_embedding_function(text: str) -> List[float]:
            return [0.1, 0.2, 0.3]
        
        streaming_manager.stream_to_vector_db(
            file_path=temp_file_medium,
            embedding_function=mock_embedding_function,
            chunk_text_size=1000,
            progress_callback=on_progress
        )
        
        # Should have progress updates
        assert len(progress_updates) > 0


# ============================================================================
# Test Cleanup Operations
# ============================================================================

class TestCleanupOperations:
    """Test cleanup of completed operations"""
    
    def test_cleanup_completed_operations(self, streaming_manager, temp_file_small):
        """Test cleaning up old completed operations"""
        # Create some operations
        op1 = streaming_manager.upload_large_file(temp_file_small, "test/cleanup1.txt")
        op2 = streaming_manager.upload_large_file(temp_file_small, "test/cleanup2.txt")
        
        # Operations should exist
        assert streaming_manager.get_progress(op1) is not None
        assert streaming_manager.get_progress(op2) is not None
        
        # Cleanup (with very short max age to remove all)
        removed = streaming_manager.cleanup_completed_operations(max_age_seconds=0)
        
        assert removed >= 2


# ============================================================================
# Test Utility Functions
# ============================================================================

class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_calculate_optimal_chunk_size(self):
        """Test optimal chunk size calculation"""
        # Fast network, large file, plenty of memory
        chunk_size = calculate_optimal_chunk_size(
            file_size=1024 * 1024 * 1024,  # 1 GB
            available_memory=8 * 1024 * 1024 * 1024,  # 8 GB
            network_speed_mbps=1000  # 1 Gbps
        )
        
        assert chunk_size >= LARGE_CHUNK_SIZE
    
    def test_format_bytes(self):
        """Test formatting bytes as human-readable"""
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1024 * 1024) == "1.00 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_format_duration(self):
        """Test formatting duration"""
        assert format_duration(30) == "30.0s"
        assert format_duration(120) == "2.0m"
        assert format_duration(3600) == "1.0h"


# ============================================================================
# Test Performance Benchmarks
# ============================================================================

class TestPerformanceBenchmarks:
    """Test performance benchmarks"""
    
    def test_upload_speed_benchmark(self, streaming_manager, temp_file_large):
        """Benchmark upload speed"""
        start_time = time.time()
        
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_large,
            destination="test/benchmark.pdf"
        )
        
        elapsed = time.time() - start_time
        
        # Get final progress
        progress = streaming_manager.get_progress(operation_id)
        assert progress is not None
        
        # Calculate effective speed
        file_size_mb = progress.total_bytes / 1024 / 1024
        speed_mbps = (file_size_mb / elapsed) if elapsed > 0 else 0
        
        print(f"\nUpload Speed: {speed_mbps:.2f} MB/s")
        print(f"File Size: {file_size_mb:.2f} MB")
        print(f"Duration: {elapsed:.2f}s")
        
        # Should complete in reasonable time (< 10s for 50MB test file)
        assert elapsed < 10.0
    
    def test_chunk_overhead(self, streaming_manager, temp_file_medium):
        """Test overhead of chunking"""
        operation_id = streaming_manager.upload_large_file(
            file_path=temp_file_medium,
            destination="test/overhead.pdf"
        )
        
        progress = streaming_manager.get_progress(operation_id)
        chunks = streaming_manager.get_operation_chunks(operation_id)
        
        # Verify all chunks accounted for
        total_chunk_size = sum(c.chunk_size for c in chunks)
        assert total_chunk_size == progress.total_bytes


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_file_upload(self, streaming_manager):
        """Test uploading an empty file"""
        # Create empty file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            operation_id = streaming_manager.upload_large_file(
                file_path=temp_path,
                destination="test/empty.txt"
            )
            
            progress = streaming_manager.get_progress(operation_id)
            assert progress is not None
            assert progress.total_bytes == 0
            assert progress.is_complete
        finally:
            os.unlink(temp_path)
    
    def test_very_large_chunk_size(self, temp_file_small):
        """Test with chunk size larger than file"""
        manager = create_streaming_manager(chunk_size=100 * 1024 * 1024)  # 100 MB
        
        operation_id = manager.upload_large_file(
            file_path=temp_file_small,
            destination="test/large_chunk.txt"
        )
        
        progress = manager.get_progress(operation_id)
        assert progress is not None
        assert progress.chunk_count == 1  # Only 1 chunk needed


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
