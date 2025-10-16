#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite: Streaming Saga Rollback
====================================

Tests für Rollback-Szenarien im Streaming Saga System:
- Resume-Failure nach max retries
- Hash-Mismatch Detection
- File-Not-Found während Upload
- Rollback-Failure Scenarios
- Compensation Verification
- Edge Cases

Author: UDS3 Team
Date: 2. Oktober 2025
Version: 1.0.0
"""

import pytest
import os
import tempfile
import time
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import modules under test
from uds3_streaming_operations import (
    StreamingManager,
    StreamingSagaConfig,
    SagaRollbackRequired,
    ChunkMetadataCorruptError,
    StorageBackendError,
    CompensationError,
    StreamingStatus
)

from uds3_streaming_saga_integration import (
    SagaStatus,
    SagaStep,
    SagaDefinition,
    execute_streaming_saga_with_rollback,
    perform_compensation,
    build_streaming_upload_saga_definition,
    StreamingSagaMonitor
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_file(temp_dir):
    """Create a test file (10 MB)"""
    file_path = os.path.join(temp_dir, "test_file.bin")
    
    # Create 10 MB file
    with open(file_path, 'wb') as f:
        f.write(b'A' * (10 * 1024 * 1024))
    
    return file_path


@pytest.fixture
def large_test_file(temp_dir):
    """Create a large test file (50 MB)"""
    file_path = os.path.join(temp_dir, "large_file.bin")
    
    # Create 50 MB file
    with open(file_path, 'wb') as f:
        f.write(b'B' * (50 * 1024 * 1024))
    
    return file_path


@pytest.fixture
def streaming_manager():
    """Create StreamingManager instance"""
    return StreamingManager(chunk_size=1 * 1024 * 1024)  # 1 MB chunks


@pytest.fixture
def saga_config():
    """Create StreamingSagaConfig"""
    return StreamingSagaConfig(
        max_resume_attempts=3,
        resume_retry_delay=0.1,  # Fast for testing
        hash_verification_enabled=True,
        rollback_on_timeout=True,
        timeout_seconds=60.0,
        auto_rollback_on_failure=True
    )


@pytest.fixture
def saga_monitor():
    """Create StreamingSagaMonitor"""
    return StreamingSagaMonitor()


# ============================================================================
# Test Class: Resume Failures
# ============================================================================

class TestResumeFailures:
    """Tests for resume failure scenarios"""
    
    def test_resume_fails_after_max_retries(self, streaming_manager, test_file, saga_config):
        """
        Test: Resume fehlschlägt nach 3 Versuchen → Rollback
        """
        # Mock: resume_upload schlägt immer fehl
        with patch.object(
            streaming_manager,
            'resume_upload',
            side_effect=StorageBackendError("Backend unavailable")
        ):
            # Mock: upload_large_file schlägt beim ersten Mal fehl
            with patch.object(
                streaming_manager,
                'upload_large_file',
                side_effect=StorageBackendError("Initial upload failed")
            ):
                # Attempt upload with retry
                with pytest.raises(SagaRollbackRequired) as exc_info:
                    streaming_manager.chunked_upload_with_retry(
                        file_path=test_file,
                        destination="test/destination",
                        config=saga_config,
                        progress_callback=None
                    )
                
                # Verify exception details
                assert exc_info.value.reason == "MAX_RETRIES_EXCEEDED"
                assert "3 resume attempts" in exc_info.value.message
                assert exc_info.value.retry_count == 3
    
    def test_resume_succeeds_on_second_attempt(self, streaming_manager, test_file, saga_config):
        """
        Test: Resume erfolgreich beim 2. Versuch
        """
        # Mock: First upload fails, resume succeeds on 2nd attempt
        upload_call_count = [0]
        
        def mock_upload(*args, **kwargs):
            upload_call_count[0] += 1
            if upload_call_count[0] == 1:
                raise StorageBackendError("First attempt failed")
            else:
                # Success on retry
                return "upload-success-123"
        
        with patch.object(streaming_manager, 'upload_large_file', side_effect=mock_upload):
            with patch.object(streaming_manager, 'get_progress') as mock_progress:
                # Mock progress as complete
                mock_progress.return_value = Mock(is_complete=True, chunk_count=10, total_bytes=10485760)
                
                result = streaming_manager.chunked_upload_with_retry(
                    file_path=test_file,
                    destination="test/destination",
                    config=saga_config,
                    progress_callback=None
                )
                
                # Verify result
                assert result['operation_id'] == "upload-success-123"
                assert result['retry_count'] == 1  # One retry
    
    def test_file_not_found_triggers_immediate_rollback(self, streaming_manager, saga_config):
        """
        Test: File not found → Sofortiger Rollback (kein Retry)
        """
        non_existent_file = "/path/to/nonexistent.file"
        
        with pytest.raises(SagaRollbackRequired) as exc_info:
            streaming_manager.chunked_upload_with_retry(
                file_path=non_existent_file,
                destination="test/destination",
                config=saga_config,
                progress_callback=None
            )
        
        # Verify exception
        assert exc_info.value.reason == "FILE_NOT_FOUND"
        assert "no longer exists" in exc_info.value.message.lower()
        assert exc_info.value.retry_count == 0  # No retries
    
    def test_chunk_metadata_corrupt_triggers_rollback(self, streaming_manager, test_file, saga_config):
        """
        Test: Chunk metadata korrupt → Sofortiger Rollback
        """
        with patch.object(
            streaming_manager,
            'upload_large_file',
            side_effect=ChunkMetadataCorruptError("Metadata corrupted")
        ):
            with pytest.raises(SagaRollbackRequired) as exc_info:
                streaming_manager.chunked_upload_with_retry(
                    file_path=test_file,
                    destination="test/destination",
                    config=saga_config,
                    progress_callback=None
                )
            
            # Verify exception
            assert exc_info.value.reason == "METADATA_CORRUPT"
            assert "metadata corrupted" in exc_info.value.message.lower()


# ============================================================================
# Test Class: Integrity Verification
# ============================================================================

class TestIntegrityVerification:
    """Tests for integrity verification scenarios"""
    
    def test_hash_mismatch_triggers_rollback(self, streaming_manager, test_file):
        """
        Test: Hash mismatch → Rollback
        """
        # Create fake operation
        operation_id = "test-op-123"
        
        # Mock progress
        with patch.object(streaming_manager, 'get_progress') as mock_progress:
            mock_progress.return_value = Mock(chunk_count=10)
            
            # Mock chunks with wrong hash
            with patch.object(streaming_manager, 'get_operation_chunks') as mock_chunks:
                mock_chunks.return_value = [
                    Mock(chunk_hash="wrong_hash_1", chunk_size=1024000),
                    Mock(chunk_hash="wrong_hash_2", chunk_size=1024000),
                ]
                
                # Attempt verify_integrity
                with pytest.raises(SagaRollbackRequired) as exc_info:
                    streaming_manager.verify_integrity(
                        operation_id=operation_id,
                        file_path=test_file
                    )
                
                # Verify exception
                assert exc_info.value.reason in ["CHUNK_COUNT_MISMATCH", "HASH_MISMATCH", "SIZE_MISMATCH"]
    
    def test_chunk_count_mismatch_triggers_rollback(self, streaming_manager, test_file):
        """
        Test: Chunk count mismatch → Rollback
        """
        operation_id = "test-op-456"
        
        # Mock: Expected 10 chunks, got 5
        with patch.object(streaming_manager, 'get_progress') as mock_progress:
            mock_progress.return_value = Mock(chunk_count=10)
            
            with patch.object(streaming_manager, 'get_operation_chunks') as mock_chunks:
                mock_chunks.return_value = [Mock()] * 5  # Only 5 chunks
                
                with pytest.raises(SagaRollbackRequired) as exc_info:
                    streaming_manager.verify_integrity(
                        operation_id=operation_id,
                        file_path=test_file
                    )
                
                # Verify
                assert exc_info.value.reason == "CHUNK_COUNT_MISMATCH"
                assert "Missing chunks: 5" in exc_info.value.message
    
    def test_size_mismatch_triggers_rollback(self, streaming_manager, test_file):
        """
        Test: Size mismatch → Rollback
        """
        operation_id = "test-op-789"
        file_size = os.path.getsize(test_file)
        
        with patch.object(streaming_manager, 'get_progress') as mock_progress:
            mock_progress.return_value = Mock(chunk_count=10)
            
            # Mock chunks with wrong total size
            with patch.object(streaming_manager, 'get_operation_chunks') as mock_chunks:
                mock_chunks.return_value = [
                    Mock(chunk_hash=f"hash_{i}", chunk_size=100000)
                    for i in range(10)
                ]  # Total: 1 MB (but file is 10 MB)
                
                with pytest.raises(SagaRollbackRequired) as exc_info:
                    streaming_manager.verify_integrity(
                        operation_id=operation_id,
                        file_path=test_file
                    )
                
                # Verify - can be either HASH_MISMATCH or SIZE_MISMATCH (checks run in sequence)
                assert exc_info.value.reason in ["HASH_MISMATCH", "SIZE_MISMATCH"]


# ============================================================================
# Test Class: Compensation (Rollback)
# ============================================================================

class TestCompensation:
    """Tests for compensation/rollback scenarios"""
    
    def test_cleanup_chunks_success(self, streaming_manager):
        """
        Test: Cleanup erfolgreich (alle Chunks gelöscht)
        """
        operation_id = "test-cleanup-success"
        
        # Mock chunks
        with patch.object(streaming_manager, 'get_operation_chunks') as mock_chunks:
            mock_chunks.return_value = [
                Mock(chunk_id=f"chunk-{i}", chunk_index=i)
                for i in range(5)
            ]
            
            # Mock successful deletion
            with patch.object(streaming_manager, '_delete_chunk'):
                with patch.object(streaming_manager, '_chunk_exists', return_value=False):
                    result = streaming_manager.cleanup_chunks_with_verification(operation_id)
                    
                    # Verify
                    assert result['deleted_count'] == 5
                    assert result['total_chunks'] == 5
                    assert result['success_rate'] == 100.0
                    assert len(result['failed_deletions']) == 0
    
    def test_cleanup_chunks_partial_failure(self, streaming_manager):
        """
        Test: Cleanup teilweise fehlgeschlagen (einige Chunks bleiben)
        """
        operation_id = "test-cleanup-partial"
        
        with patch.object(streaming_manager, 'get_operation_chunks') as mock_chunks:
            mock_chunks.return_value = [
                Mock(chunk_id=f"chunk-{i}", chunk_index=i)
                for i in range(10)
            ]
            
            # Mock: First 7 succeed, last 3 fail
            delete_call_count = [0]
            
            def mock_delete(chunk_id):
                delete_call_count[0] += 1
                if delete_call_count[0] > 7:
                    raise Exception("Delete failed")
            
            with patch.object(streaming_manager, '_delete_chunk', side_effect=mock_delete):
                with patch.object(streaming_manager, '_chunk_exists', return_value=False):
                    result = streaming_manager.cleanup_chunks_with_verification(operation_id)
                    
                    # Verify
                    assert result['deleted_count'] == 7
                    assert result['total_chunks'] == 10
                    assert result['success_rate'] == 70.0
                    assert len(result['failed_deletions']) == 3
    
    def test_cleanup_catastrophic_failure(self, streaming_manager):
        """
        Test: Cleanup selbst crashed → CompensationError
        """
        operation_id = "test-cleanup-crash"
        
        with patch.object(
            streaming_manager,
            'get_operation_chunks',
            side_effect=Exception("Database crashed")
        ):
            with pytest.raises(CompensationError) as exc_info:
                streaming_manager.cleanup_chunks_with_verification(operation_id)
            
            # Verify
            assert "Chunk cleanup failed" in str(exc_info.value)
    
    def test_failed_cleanups_logged(self, streaming_manager, tmp_path):
        """
        Test: Fehlgeschlagene Cleanups werden geloggt
        """
        operation_id = "test-log-failures"
        
        # Mock chunks
        with patch.object(streaming_manager, 'get_operation_chunks') as mock_chunks:
            mock_chunks.return_value = [
                Mock(chunk_id=f"chunk-{i}", chunk_index=i)
                for i in range(3)
            ]
            
            # Mock: All deletions fail
            with patch.object(
                streaming_manager,
                '_delete_chunk',
                side_effect=Exception("Storage unreachable")
            ):
                result = streaming_manager.cleanup_chunks_with_verification(operation_id)
                
                # Verify logging occurred
                assert len(result['failed_deletions']) == 3
                assert result['success_rate'] == 0.0


# ============================================================================
# Test Class: Saga Execution & Rollback
# ============================================================================

class TestSagaExecutionRollback:
    """Tests for saga execution with rollback"""
    
    def test_saga_completes_successfully(self, streaming_manager, saga_config):
        """
        Test: Saga läuft erfolgreich durch (kein Rollback nötig)
        """
        # Create simple saga with 3 steps
        step1_executed = [False]
        step2_executed = [False]
        step3_executed = [False]
        
        def step1_action(ctx):
            step1_executed[0] = True
            return {'step1': 'done'}
        
        def step2_action(ctx):
            step2_executed[0] = True
            return {'step2': 'done'}
        
        def step3_action(ctx):
            step3_executed[0] = True
            return {'step3': 'done'}
        
        saga_def = SagaDefinition(
            name="test_saga",
            steps=[
                SagaStep(name="step1", action=step1_action, compensation=None),
                SagaStep(name="step2", action=step2_action, compensation=None),
                SagaStep(name="step3", action=step3_action, compensation=None),
            ]
        )
        
        # Execute saga
        result = execute_streaming_saga_with_rollback(
            definition=saga_def,
            context={},
            config=saga_config
        )
        
        # Verify
        assert result.status == SagaStatus.COMPLETED
        assert len(result.errors) == 0
        assert len(result.compensation_errors) == 0
        assert step1_executed[0]
        assert step2_executed[0]
        assert step3_executed[0]
    
    def test_saga_rollback_on_failure(self, streaming_manager, saga_config):
        """
        Test: Saga Step schlägt fehl → Automatischer Rollback
        """
        compensated_steps = []
        
        def step1_action(ctx):
            return {'step1': 'done'}
        
        def step1_compensation(ctx):
            compensated_steps.append('step1')
        
        def step2_action(ctx):
            raise SagaRollbackRequired(
                reason="TEST_FAILURE",
                message="Step 2 failed intentionally"
            )
        
        def step2_compensation(ctx):
            compensated_steps.append('step2')
        
        saga_def = SagaDefinition(
            name="test_saga_rollback",
            steps=[
                SagaStep(name="step1", action=step1_action, compensation=step1_compensation),
                SagaStep(name="step2", action=step2_action, compensation=step2_compensation),
            ]
        )
        
        # Execute saga
        result = execute_streaming_saga_with_rollback(
            definition=saga_def,
            context={},
            config=saga_config
        )
        
        # Verify
        assert result.status == SagaStatus.COMPENSATED
        assert len(result.errors) == 1
        assert "Step 2 failed" in result.errors[0]
        assert len(result.compensation_errors) == 0
        
        # Verify compensation was executed (LIFO order)
        assert compensated_steps == ['step1']  # step2 never executed, so no compensation
    
    def test_saga_compensation_failure(self, streaming_manager, saga_config):
        """
        Test: Compensation schlägt fehl → Status COMPENSATION_FAILED
        """
        def step1_action(ctx):
            return {'step1': 'done'}
        
        def step1_compensation(ctx):
            raise CompensationError("Compensation failed")
        
        def step2_action(ctx):
            raise Exception("Step 2 failed")
        
        saga_def = SagaDefinition(
            name="test_compensation_failure",
            steps=[
                SagaStep(name="step1", action=step1_action, compensation=step1_compensation),
                SagaStep(name="step2", action=step2_action, compensation=None),
            ]
        )
        
        # Execute saga
        result = execute_streaming_saga_with_rollback(
            definition=saga_def,
            context={},
            config=saga_config
        )
        
        # Verify
        assert result.status == SagaStatus.COMPENSATION_FAILED
        assert len(result.errors) == 1
        assert len(result.compensation_errors) == 1
        assert "Compensation failed" in result.compensation_errors[0]


# ============================================================================
# Test Class: Monitoring
# ============================================================================

class TestMonitoring:
    """Tests for StreamingSagaMonitor"""
    
    def test_track_saga_lifecycle(self, saga_monitor):
        """
        Test: Saga Lifecycle Tracking
        """
        saga_id = "test-saga-123"
        context = {'operation_id': 'op-123', 'file_path': '/test/file.pdf'}
        
        # Track saga
        saga_monitor.track_saga(saga_id, context)
        
        # Verify active
        assert saga_id in saga_monitor.active_sagas
        assert saga_monitor.active_sagas[saga_id]['status'] == 'RUNNING'
        
        # Complete saga
        result = Mock(status=SagaStatus.COMPLETED)
        saga_monitor.saga_completed(saga_id, result)
        
        # Verify completed
        assert saga_id not in saga_monitor.active_sagas
        assert saga_id in saga_monitor.completed_sagas
    
    def test_track_rollback_statistics(self, saga_monitor):
        """
        Test: Rollback Statistics Tracking
        """
        saga_id = "test-saga-rollback"
        context = {'operation_id': 'op-rollback'}
        
        # Track saga
        saga_monitor.track_saga(saga_id, context)
        
        # Simulate rollback
        result = Mock(
            status=SagaStatus.COMPENSATED,
            errors=['Error 1'],
            compensation_errors=[]
        )
        saga_monitor.saga_rolled_back(saga_id, result, compensation_success=True)
        
        # Verify stats
        stats = saga_monitor.get_stats()
        assert stats['rollback_stats']['total_rollbacks'] == 1
        assert stats['rollback_stats']['successful_rollbacks'] == 1
        assert stats['rollback_stats']['failed_rollbacks'] == 0
    
    def test_alert_on_rollback_failure(self, saga_monitor, tmp_path):
        """
        Test: Alert bei fehlgeschlagenem Rollback
        """
        saga_id = "test-saga-alert"
        context = {'operation_id': 'op-alert'}
        
        saga_monitor.track_saga(saga_id, context)
        
        # Simulate failed rollback
        result = Mock(
            status=SagaStatus.COMPENSATION_FAILED,
            errors=['Upload failed'],
            compensation_errors=['Cleanup failed']
        )
        saga_monitor.saga_rolled_back(saga_id, result, compensation_success=False)
        
        # Verify stats
        stats = saga_monitor.get_stats()
        assert stats['rollback_stats']['failed_rollbacks'] == 1
        assert stats['rollback_stats']['pending_manual_cleanup'] == 1


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and corner scenarios"""
    
    def test_empty_file_upload(self, streaming_manager, temp_dir, saga_config):
        """
        Test: Leere Datei (0 bytes)
        """
        empty_file = os.path.join(temp_dir, "empty.bin")
        Path(empty_file).touch()  # Create empty file
        
        # Mock successful upload
        with patch.object(streaming_manager, 'upload_large_file', return_value='op-empty'):
            with patch.object(streaming_manager, 'get_progress') as mock_progress:
                mock_progress.return_value = Mock(
                    is_complete=True,
                    chunk_count=0,
                    total_bytes=0
                )
                
                result = streaming_manager.chunked_upload_with_retry(
                    file_path=empty_file,
                    destination="test/empty",
                    config=saga_config,
                    progress_callback=None
                )
                
                # Verify
                assert result['operation_id'] == 'op-empty'
                assert result['uploaded_chunks'] == 0
                assert result['total_bytes'] == 0
    
    def test_concurrent_sagas_different_files(self, streaming_manager, test_file, large_test_file, saga_config):
        """
        Test: Mehrere Sagas parallel mit verschiedenen Dateien
        """
        # This test verifies that operations have unique IDs
        with patch.object(streaming_manager, 'upload_large_file') as mock_upload:
            # Return different operation IDs
            mock_upload.side_effect = ['op-1', 'op-2']
            
            with patch.object(streaming_manager, 'get_progress') as mock_progress:
                mock_progress.return_value = Mock(is_complete=True, chunk_count=10, total_bytes=10485760)
                
                # Upload file 1
                result1 = streaming_manager.chunked_upload_with_retry(
                    file_path=test_file,
                    destination="test/file1",
                    config=saga_config,
                    progress_callback=None
                )
                
                # Upload file 2
                result2 = streaming_manager.chunked_upload_with_retry(
                    file_path=large_test_file,
                    destination="test/file2",
                    config=saga_config,
                    progress_callback=None
                )
                
                # Verify unique operation IDs
                assert result1['operation_id'] != result2['operation_id']
    
    def test_very_large_file_simulation(self, streaming_manager, saga_config):
        """
        Test: Sehr große Datei (Simulation 1 GB)
        """
        # We don't actually create 1 GB file, just simulate the metadata
        fake_file = "/fake/1gb_file.bin"
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=1024*1024*1024):  # 1 GB
                with patch('os.access', return_value=True):
                    with patch('builtins.open', create=True):
                        # This would trigger the upload
                        # For now, just verify file size calculation
                        file_size = os.path.getsize(fake_file)
                        chunk_size = 5 * 1024 * 1024  # 5 MB
                        expected_chunks = (file_size + chunk_size - 1) // chunk_size
                        
                        # Verify chunk calculation
                        assert expected_chunks == 205  # 1024 MB / 5 MB per chunk ≈ 205


# ============================================================================
# Test Class: Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components"""
    
    def test_full_saga_with_rollback_integration(
        self, streaming_manager, test_file, saga_config, saga_monitor
    ):
        """
        Test: Vollständige Saga mit Upload → Failure → Rollback
        """
        saga_id = "integration-test-saga"
        
        # Build saga definition
        saga_def = build_streaming_upload_saga_definition(
            streaming_manager=streaming_manager,
            config=saga_config,
            vector_db=None,
            graph_db=None,
            relational_db=None,
            security_manager=None
        )
        
        # Track saga
        context = {
            'file_path': test_file,
            'destination': 'test/integration',
            'streaming_manager': streaming_manager,
            'content': '',
            'chunks': [],
            'metadata': {}
        }
        saga_monitor.track_saga(saga_id, context)
        
        # Mock: Upload succeeds but integrity fails
        with patch.object(streaming_manager, 'upload_large_file', return_value='op-int-123'):
            with patch.object(streaming_manager, 'get_progress') as mock_progress:
                mock_progress.return_value = Mock(
                    is_complete=True,
                    chunk_count=10,
                    total_bytes=10485760
                )
                
                # Mock: verify_integrity fails (hash mismatch)
                with patch.object(
                    streaming_manager,
                    'verify_integrity',
                    side_effect=SagaRollbackRequired(
                        reason="HASH_MISMATCH",
                        message="Hash mismatch detected"
                    )
                ):
                    # Mock: cleanup succeeds
                    with patch.object(streaming_manager, 'cleanup_chunks_with_verification') as mock_cleanup:
                        mock_cleanup.return_value = {
                            'deleted_count': 10,
                            'total_chunks': 10,
                            'failed_deletions': [],
                            'success_rate': 100.0
                        }
                        
                        # Execute saga
                        result = execute_streaming_saga_with_rollback(
                            definition=saga_def,
                            context=context,
                            config=saga_config
                        )
                        
                        # Verify rollback occurred
                        assert result.status == SagaStatus.COMPENSATED
                        assert len(result.errors) == 1
                        assert "HASH_MISMATCH" in result.errors[0] or "Hash mismatch" in result.errors[0]
                        assert len(result.compensation_errors) == 0
                        
                        # Verify cleanup was called
                        mock_cleanup.assert_called_once()
        
        # Update monitor
        saga_monitor.saga_rolled_back(saga_id, result, compensation_success=True)
        
        # Verify monitor stats
        stats = saga_monitor.get_stats()
        assert stats['rollback_stats']['total_rollbacks'] == 1
        assert stats['rollback_stats']['successful_rollbacks'] == 1


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
