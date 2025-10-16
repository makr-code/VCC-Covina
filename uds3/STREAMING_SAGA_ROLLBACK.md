# Streaming Saga Rollback Strategy

**Datum:** 2. Oktober 2025  
**Status:** Critical Design Extension  
**Priority:** HIGH

---

## 🎯 Problem: Resume kann fehlschlagen

### Szenarien, wo Resume NICHT funktioniert:

1. **Datei wurde zwischenzeitlich gelöscht/verschoben**
   - Resume versucht fortzusetzen, aber Datei existiert nicht mehr
   - → Saga muss Rollback durchführen

2. **Chunk-Metadaten korrupt/verloren**
   - Resume kann nicht ermitteln, welche Chunks schon hochgeladen sind
   - → Saga muss Rollback durchführen

3. **Storage Backend nicht erreichbar**
   - Persistent Fehler, Resume macht keinen Sinn
   - → Saga muss nach N Retries aufgeben und Rollback

4. **Hash-Mismatch nach Resume**
   - Datei wurde während Pause modifiziert
   - → Integrity Check schlägt fehl, Rollback erforderlich

5. **Timeout/Resource Exhaustion**
   - Resume versucht, aber System-Ressourcen erschöpft
   - → Graceful Rollback statt hängender Operation

6. **Maximale Retry-Versuche erreicht**
   - Mehrere Resume-Versuche fehlgeschlagen
   - → Saga gibt auf, führt vollständigen Rollback durch

---

## 🔄 Enhanced Streaming Saga mit Rollback-Strategie

### 1. **Saga State Machine**

```python
class StreamingSagaState(Enum):
    """States für Streaming Saga mit Resume & Rollback"""
    INITIALIZED = "initialized"
    UPLOADING = "uploading"
    UPLOAD_PAUSED = "upload_paused"
    UPLOAD_FAILED = "upload_failed"
    RESUMING = "resuming"
    RESUME_FAILED = "resume_failed"
    VERIFYING = "verifying"
    VERIFY_FAILED = "verify_failed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"  # Critical!

# State Transitions
ALLOWED_TRANSITIONS = {
    INITIALIZED: [UPLOADING, ROLLING_BACK],
    UPLOADING: [UPLOAD_PAUSED, UPLOAD_FAILED, VERIFYING, ROLLING_BACK],
    UPLOAD_PAUSED: [RESUMING, ROLLING_BACK],
    UPLOAD_FAILED: [RESUMING, ROLLING_BACK],
    RESUMING: [UPLOADING, RESUME_FAILED, ROLLING_BACK],
    RESUME_FAILED: [RESUMING, ROLLING_BACK],  # Retry oder Aufgeben
    VERIFYING: [VERIFY_FAILED, PROCESSING, ROLLING_BACK],
    VERIFY_FAILED: [ROLLING_BACK],
    PROCESSING: [COMPLETED, ROLLING_BACK],
    ROLLING_BACK: [ROLLED_BACK, ROLLBACK_FAILED],
    ROLLED_BACK: [],  # Terminal State
    ROLLBACK_FAILED: []  # Terminal State (Critical!)
}
```

---

### 2. **Resume mit Retry-Limit**

```python
@dataclass
class StreamingSagaConfig:
    """Configuration für Streaming Saga"""
    max_resume_attempts: int = 3
    resume_retry_delay: float = 5.0  # seconds
    hash_verification_enabled: bool = True
    rollback_on_timeout: bool = True
    timeout_seconds: float = 3600.0  # 1 hour
    auto_rollback_on_failure: bool = True


def chunked_upload_action_with_retry(
    context: Dict[str, Any],
    config: StreamingSagaConfig
) -> Dict[str, Any]:
    """
    Chunked Upload mit automatischem Retry und Rollback
    
    Strategy:
    1. Versuche Upload
    2. Bei Fehler: Versuche Resume (max N mal)
    3. Wenn Resume fehlschlägt: Trigger Rollback
    4. Wenn Rollback fehlschlägt: Critical Error
    """
    streaming_manager = context['streaming_manager']
    file_path = context['file_path']
    destination = context['destination']
    
    retry_count = 0
    operation_id = None
    last_error = None
    
    while retry_count < config.max_resume_attempts:
        try:
            if operation_id is None:
                # Initial upload attempt
                logger.info(f"Starting chunked upload (attempt {retry_count + 1})")
                operation_id = streaming_manager.upload_large_file(
                    file_path=file_path,
                    destination=destination,
                    progress_callback=context.get('progress_callback')
                )
            else:
                # Resume attempt
                logger.info(f"Resuming upload (attempt {retry_count + 1})")
                operation_id = streaming_manager.resume_upload(
                    operation_id=operation_id,
                    file_path=file_path,
                    destination=destination,
                    progress_callback=context.get('progress_callback')
                )
            
            # Check if completed
            progress = streaming_manager.get_progress(operation_id)
            
            if progress.is_complete:
                logger.info(f"Upload completed successfully")
                return {
                    'operation_id': operation_id,
                    'uploaded_chunks': progress.chunk_count,
                    'total_bytes': progress.total_bytes,
                    'retry_count': retry_count
                }
            else:
                # Upload incomplete but no exception
                last_error = f"Upload incomplete: {progress.progress_percent}%"
                logger.warning(last_error)
                retry_count += 1
                time.sleep(config.resume_retry_delay)
                
        except FileNotFoundError as e:
            # Critical: File was deleted/moved
            logger.error(f"File not found during upload: {e}")
            raise SagaRollbackRequired(
                reason="FILE_NOT_FOUND",
                message=f"Source file no longer exists: {file_path}",
                operation_id=operation_id,
                retry_count=retry_count
            )
            
        except ChunkMetadataCorruptError as e:
            # Critical: Chunk tracking lost
            logger.error(f"Chunk metadata corrupt: {e}")
            raise SagaRollbackRequired(
                reason="METADATA_CORRUPT",
                message="Cannot resume: chunk metadata corrupted",
                operation_id=operation_id,
                retry_count=retry_count
            )
            
        except StorageBackendError as e:
            # Retry-able error
            logger.warning(f"Storage backend error: {e}")
            last_error = str(e)
            retry_count += 1
            time.sleep(config.resume_retry_delay)
            
        except Exception as e:
            # Unknown error
            logger.error(f"Unexpected error during upload: {e}")
            last_error = str(e)
            retry_count += 1
            time.sleep(config.resume_retry_delay)
    
    # All retry attempts exhausted
    logger.error(f"Upload failed after {retry_count} attempts: {last_error}")
    raise SagaRollbackRequired(
        reason="MAX_RETRIES_EXCEEDED",
        message=f"Upload failed after {retry_count} resume attempts",
        operation_id=operation_id,
        retry_count=retry_count,
        last_error=last_error
    )


class SagaRollbackRequired(Exception):
    """
    Exception signalisiert: Saga muss Rollback durchführen
    
    Raised when:
    - Resume attempts exhausted
    - Critical error (file not found, metadata corrupt)
    - Timeout exceeded
    - Integrity check failed
    """
    def __init__(
        self,
        reason: str,
        message: str,
        operation_id: Optional[str] = None,
        retry_count: int = 0,
        last_error: Optional[str] = None
    ):
        self.reason = reason
        self.message = message
        self.operation_id = operation_id
        self.retry_count = retry_count
        self.last_error = last_error
        super().__init__(message)
```

---

### 3. **Compensation mit Rollback-Garantie**

```python
def cleanup_chunks_with_verification(context: Dict[str, Any]) -> None:
    """
    Kompensation: Löscht Chunks mit Verifikation
    
    CRITICAL: Muss garantiert durchlaufen, auch bei Fehlern
    
    Strategy:
    1. Liste alle hochgeladenen Chunks
    2. Lösche jeden Chunk einzeln
    3. Verifiziere Löschung
    4. Bei Fehler: Logge, aber fahre fort (Best Effort)
    5. Am Ende: Status-Report
    """
    streaming_manager = context['streaming_manager']
    operation_id = context.get('operation_id')
    
    if not operation_id:
        logger.warning("No operation_id for cleanup - nothing to do")
        return
    
    try:
        # Cancel operation if still running
        if streaming_manager.cancel_operation(operation_id):
            logger.info(f"Cancelled streaming operation: {operation_id}")
        
        # Get all uploaded chunks
        chunks = streaming_manager.get_operation_chunks(operation_id)
        total_chunks = len(chunks)
        deleted_count = 0
        failed_deletions = []
        
        logger.info(f"Starting cleanup: {total_chunks} chunks to delete")
        
        # Delete each chunk with verification
        for chunk in chunks:
            try:
                # Delete chunk from storage
                delete_chunk(chunk.chunk_id)
                
                # Verify deletion
                if not chunk_exists(chunk.chunk_id):
                    deleted_count += 1
                    logger.debug(f"Deleted chunk {chunk.chunk_index}: {chunk.chunk_id}")
                else:
                    failed_deletions.append(chunk.chunk_id)
                    logger.warning(f"Chunk deletion verification failed: {chunk.chunk_id}")
                    
            except Exception as e:
                # Log but continue (Best Effort)
                failed_deletions.append(chunk.chunk_id)
                logger.error(f"Failed to delete chunk {chunk.chunk_id}: {e}")
        
        # Cleanup operation metadata
        streaming_manager.cleanup_completed_operations(max_age_seconds=0)
        
        # Status Report
        success_rate = (deleted_count / total_chunks * 100) if total_chunks > 0 else 100
        logger.info(
            f"Cleanup complete: {deleted_count}/{total_chunks} chunks deleted "
            f"({success_rate:.1f}% success)"
        )
        
        if failed_deletions:
            logger.warning(
                f"Failed to delete {len(failed_deletions)} chunks: {failed_deletions[:5]}..."
            )
            # Store for manual cleanup
            store_failed_deletions(operation_id, failed_deletions)
        
    except Exception as e:
        # Critical: Cleanup itself failed
        logger.critical(f"Cleanup failed catastrophically: {e}")
        # Store for manual intervention
        store_critical_cleanup_failure(operation_id, str(e))
        raise CompensationError(f"Chunk cleanup failed: {e}")


def store_failed_deletions(operation_id: str, failed_chunks: List[str]) -> None:
    """
    Speichert fehlgeschlagene Löschungen für manuelle Bereinigung
    
    Storage: Persistent log oder Database table
    """
    cleanup_log = {
        'timestamp': datetime.utcnow().isoformat(),
        'operation_id': operation_id,
        'failed_chunks': failed_chunks,
        'status': 'PENDING_MANUAL_CLEANUP'
    }
    
    # Persist to database or log file
    with open('failed_cleanups.json', 'a') as f:
        f.write(json.dumps(cleanup_log) + '\n')
    
    logger.info(f"Stored {len(failed_chunks)} failed deletions for manual cleanup")
```

---

### 4. **Integrity Verification mit Rollback**

```python
def verify_integrity_action(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifiziert Datei-Integrität nach Upload/Resume
    
    Checks:
    1. Alle Chunks vorhanden
    2. Chunk-Hashes korrekt
    3. Gesamt-Hash stimmt mit Original überein
    4. Datei-Größe korrekt
    
    Bei Fehler: Trigger Rollback
    """
    operation_id = context['operation_id']
    file_path = context['file_path']
    streaming_manager = context['streaming_manager']
    
    # Get upload metadata
    progress = streaming_manager.get_progress(operation_id)
    chunks = streaming_manager.get_operation_chunks(operation_id)
    
    # Check 1: All chunks present
    expected_chunks = progress.chunk_count
    actual_chunks = len(chunks)
    
    if actual_chunks != expected_chunks:
        logger.error(
            f"Chunk count mismatch: expected {expected_chunks}, got {actual_chunks}"
        )
        raise SagaRollbackRequired(
            reason="CHUNK_COUNT_MISMATCH",
            message=f"Missing chunks: {expected_chunks - actual_chunks}",
            operation_id=operation_id
        )
    
    # Check 2: Calculate original file hash
    original_hash = calculate_file_hash(file_path)
    
    # Check 3: Calculate uploaded chunks hash
    uploaded_hash = calculate_chunks_hash([c.chunk_hash for c in chunks])
    
    if original_hash != uploaded_hash:
        logger.error(
            f"Hash mismatch: original={original_hash}, uploaded={uploaded_hash}"
        )
        raise SagaRollbackRequired(
            reason="HASH_MISMATCH",
            message="File was modified during upload or chunks corrupted",
            operation_id=operation_id
        )
    
    # Check 4: File size
    original_size = os.path.getsize(file_path)
    uploaded_size = sum(c.chunk_size for c in chunks)
    
    if original_size != uploaded_size:
        logger.error(
            f"Size mismatch: original={original_size}, uploaded={uploaded_size}"
        )
        raise SagaRollbackRequired(
            reason="SIZE_MISMATCH",
            message=f"Size difference: {original_size - uploaded_size} bytes",
            operation_id=operation_id
        )
    
    logger.info("✅ Integrity verification passed")
    return {
        'verified': True,
        'hash': original_hash,
        'size': original_size,
        'chunk_count': actual_chunks
    }
```

---

### 5. **Complete Saga mit Rollback-Flow**

```python
def _build_streaming_upload_saga_definition(
    context: Dict[str, Any],
    config: StreamingSagaConfig
) -> SagaDefinition:
    """
    Build complete streaming saga with rollback strategy
    
    Rollback Triggers:
    - Any SagaRollbackRequired exception
    - Any unhandled exception after max retries
    - Explicit cancel by user
    - Timeout exceeded
    """
    
    return SagaDefinition(
        name="streaming_upload_with_rollback",
        steps=[
            # Step 1: Validate (no compensation needed)
            SagaStep(
                name="validate_file",
                action=validate_file_action,
                compensation=None
            ),
            
            # Step 2: Start Streaming
            SagaStep(
                name="start_streaming",
                action=start_streaming_action,
                compensation=lambda ctx: cancel_streaming(ctx['operation_id'])
            ),
            
            # Step 3: Chunked Upload mit Retry & Rollback
            SagaStep(
                name="chunked_upload_with_retry",
                action=lambda ctx: chunked_upload_action_with_retry(ctx, config),
                compensation=cleanup_chunks_with_verification
            ),
            
            # Step 4: Verify Integrity (critical check)
            SagaStep(
                name="verify_integrity",
                action=verify_integrity_action,
                compensation=None  # Readonly, but triggers rollback on failure
            ),
            
            # Step 5: Security & Identity
            SagaStep(
                name="process_security",
                action=process_security_action,
                compensation=remove_security_record
            ),
            
            # Step 6: Vector DB Streaming
            SagaStep(
                name="stream_to_vector_db",
                action=lambda ctx: stream_to_vector_db_with_retry(ctx, config),
                compensation=remove_from_vector_db
            ),
            
            # Step 7: Graph DB
            SagaStep(
                name="insert_graph",
                action=insert_graph_action,
                compensation=remove_from_graph
            ),
            
            # Step 8: Relational DB
            SagaStep(
                name="insert_relational",
                action=insert_relational_action,
                compensation=remove_from_relational
            ),
            
            # Step 9: Finalize
            SagaStep(
                name="finalize",
                action=finalize_action,
                compensation=None
            )
        ]
    )


def execute_streaming_saga_with_rollback(
    definition: SagaDefinition,
    context: Dict[str, Any],
    config: StreamingSagaConfig
) -> SagaExecutionResult:
    """
    Execute streaming saga with automatic rollback on failure
    
    Rollback Strategy:
    1. Catch SagaRollbackRequired exception
    2. Execute compensation chain in reverse
    3. Verify each compensation succeeded
    4. Report rollback status
    """
    saga_id = f"saga-{uuid.uuid4().hex[:12]}"
    errors = []
    compensation_errors = []
    status = SagaStatus.RUNNING
    executed_steps = []
    
    try:
        # Execute saga steps
        for step in definition.steps:
            logger.info(f"Executing saga step: {step.name}")
            
            try:
                result = step.action(context)
                if result:
                    context.update(result)
                executed_steps.append(step)
                
            except SagaRollbackRequired as e:
                # Explicit rollback request
                logger.warning(
                    f"Rollback required at step {step.name}: "
                    f"{e.reason} - {e.message}"
                )
                errors.append(f"{step.name}: {e.message}")
                status = SagaStatus.COMPENSATING
                
                # Perform rollback
                compensation_errors = perform_compensation(
                    executed_steps, context, config
                )
                
                if compensation_errors:
                    status = SagaStatus.COMPENSATION_FAILED
                else:
                    status = SagaStatus.COMPENSATED
                
                break
                
            except Exception as e:
                # Unexpected error
                logger.error(f"Step {step.name} failed unexpectedly: {e}")
                errors.append(f"{step.name}: {str(e)}")
                status = SagaStatus.COMPENSATING
                
                # Perform rollback
                compensation_errors = perform_compensation(
                    executed_steps, context, config
                )
                
                if compensation_errors:
                    status = SagaStatus.COMPENSATION_FAILED
                else:
                    status = SagaStatus.COMPENSATED
                
                break
        
        # All steps completed successfully
        if not errors:
            status = SagaStatus.COMPLETED
            logger.info(f"Saga {saga_id} completed successfully")
        
    except Exception as e:
        # Critical saga execution error
        logger.critical(f"Saga execution failed catastrophically: {e}")
        errors.append(f"CRITICAL: {str(e)}")
        status = SagaStatus.FAILED
    
    return SagaExecutionResult(
        saga_id=saga_id,
        status=status,
        context=context,
        errors=errors,
        compensation_errors=compensation_errors
    )


def perform_compensation(
    executed_steps: List[SagaStep],
    context: Dict[str, Any],
    config: StreamingSagaConfig
) -> List[str]:
    """
    Perform compensation (rollback) for executed steps
    
    Strategy:
    1. Reverse order (LIFO)
    2. Execute each compensation
    3. Log success/failure
    4. Continue even if compensation fails (Best Effort)
    5. Return list of compensation errors
    """
    compensation_errors = []
    
    logger.info(f"Starting compensation for {len(executed_steps)} steps")
    
    for step in reversed(executed_steps):
        if step.compensation is None:
            logger.debug(f"Step {step.name}: No compensation needed")
            continue
        
        try:
            logger.info(f"Compensating step: {step.name}")
            step.compensation(context)
            logger.info(f"✅ Compensation successful: {step.name}")
            
        except CompensationError as e:
            error_msg = f"Compensation failed for {step.name}: {e}"
            logger.error(error_msg)
            compensation_errors.append(error_msg)
            # Continue with other compensations (Best Effort)
            
        except Exception as e:
            error_msg = f"Compensation crashed for {step.name}: {e}"
            logger.critical(error_msg)
            compensation_errors.append(error_msg)
            # Continue (Best Effort)
    
    if compensation_errors:
        logger.error(
            f"Compensation completed with {len(compensation_errors)} errors"
        )
    else:
        logger.info("✅ All compensations successful")
    
    return compensation_errors
```

---

## 6. **Integration in uds3_core.py**

```python
class UnifiedDatabaseStrategy:
    
    def create_document_streaming(
        self,
        file_path: str,
        content: str,
        chunks: List[str],
        progress_callback: Optional[Callable] = None,
        max_resume_attempts: int = 3,
        **metadata
    ) -> Dict[str, Any]:
        """
        Erstellt Dokument mit Streaming und automatischem Rollback
        
        Rollback wird ausgelöst bei:
        - Resume fehlschlägt nach N Versuchen
        - Integrity Check schlägt fehl
        - Kritische Fehler (File not found, etc.)
        - Timeout überschritten
        
        Args:
            file_path: Pfad zur Datei
            content: Text-Inhalt
            chunks: Text-Chunks
            progress_callback: Progress-Callback
            max_resume_attempts: Maximale Resume-Versuche (default: 3)
            **metadata: Dokument-Metadaten
        
        Returns:
            Dict mit Ergebnis und rollback_info wenn applicable
        """
        # Config
        config = StreamingSagaConfig(
            max_resume_attempts=max_resume_attempts,
            resume_retry_delay=5.0,
            hash_verification_enabled=True,
            rollback_on_timeout=True,
            auto_rollback_on_failure=True
        )
        
        # Context
        context = {
            'file_path': file_path,
            'content': content,
            'chunks': chunks,
            'metadata': metadata,
            'streaming_manager': self.streaming_manager,
            'progress_callback': progress_callback,
            'security_level': metadata.get('security_level'),
            'embedding_function': self._get_embedding_function(),
            'create_result': {
                'success': False,
                'issues': [],
                'rollback_performed': False
            }
        }
        
        # Build saga
        saga_definition = self._build_streaming_upload_saga_definition(
            context, config
        )
        
        # Execute with automatic rollback
        saga_result = execute_streaming_saga_with_rollback(
            definition=saga_definition,
            context=context,
            config=config
        )
        
        # Build result
        result = {
            'success': saga_result.status == SagaStatus.COMPLETED,
            'saga_id': saga_result.saga_id,
            'status': saga_result.status.value,
            'operation_id': context.get('operation_id'),
            'document_id': context.get('document_id'),
            'errors': saga_result.errors,
            'compensation_errors': saga_result.compensation_errors
        }
        
        # Rollback info
        if saga_result.status in [SagaStatus.COMPENSATED, SagaStatus.COMPENSATION_FAILED]:
            result['rollback_performed'] = True
            result['rollback_status'] = (
                'success' if saga_result.status == SagaStatus.COMPENSATED 
                else 'partial_failure'
            )
            
            if saga_result.compensation_errors:
                result['rollback_warnings'] = saga_result.compensation_errors
                # Store for manual cleanup
                self._store_rollback_failures(saga_result)
        
        return result
    
    def _store_rollback_failures(self, saga_result: SagaExecutionResult) -> None:
        """
        Speichert fehlgeschlagene Rollbacks für manuelle Intervention
        """
        failure_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'saga_id': saga_result.saga_id,
            'errors': saga_result.errors,
            'compensation_errors': saga_result.compensation_errors,
            'context_snapshot': self._sanitize_context(saga_result.context),
            'status': 'REQUIRES_MANUAL_CLEANUP'
        }
        
        # Persist to database or dedicated log
        logger.critical(
            f"Rollback failures detected - manual cleanup required: "
            f"{saga_result.saga_id}"
        )
        
        # Store in dedicated table/file
        with open('rollback_failures.json', 'a') as f:
            f.write(json.dumps(failure_record) + '\n')
```

---

## 7. **Monitoring & Alerting**

```python
class StreamingSagaMonitor:
    """
    Monitoring für Streaming Sagas mit Rollback-Tracking
    """
    
    def __init__(self):
        self.active_sagas = {}
        self.completed_sagas = {}
        self.failed_sagas = {}
        self.rollback_stats = {
            'total_rollbacks': 0,
            'successful_rollbacks': 0,
            'failed_rollbacks': 0,
            'pending_manual_cleanup': 0
        }
    
    def track_saga(self, saga_id: str, context: Dict[str, Any]):
        """Track active saga"""
        self.active_sagas[saga_id] = {
            'started_at': datetime.utcnow(),
            'operation_id': context.get('operation_id'),
            'file_path': context.get('file_path'),
            'status': 'RUNNING'
        }
    
    def saga_completed(self, saga_id: str, result: SagaExecutionResult):
        """Saga completed successfully"""
        if saga_id in self.active_sagas:
            self.completed_sagas[saga_id] = {
                **self.active_sagas[saga_id],
                'completed_at': datetime.utcnow(),
                'status': result.status.value
            }
            del self.active_sagas[saga_id]
    
    def saga_rolled_back(
        self,
        saga_id: str,
        result: SagaExecutionResult,
        compensation_success: bool
    ):
        """Saga was rolled back"""
        self.rollback_stats['total_rollbacks'] += 1
        
        if compensation_success:
            self.rollback_stats['successful_rollbacks'] += 1
        else:
            self.rollback_stats['failed_rollbacks'] += 1
            self.rollback_stats['pending_manual_cleanup'] += 1
            
            # Alert for failed rollback
            self.alert_rollback_failure(saga_id, result)
        
        if saga_id in self.active_sagas:
            self.failed_sagas[saga_id] = {
                **self.active_sagas[saga_id],
                'failed_at': datetime.utcnow(),
                'rollback_status': 'success' if compensation_success else 'failed',
                'errors': result.errors,
                'compensation_errors': result.compensation_errors
            }
            del self.active_sagas[saga_id]
    
    def alert_rollback_failure(self, saga_id: str, result: SagaExecutionResult):
        """Send alert for critical rollback failure"""
        alert = {
            'severity': 'CRITICAL',
            'type': 'ROLLBACK_FAILURE',
            'saga_id': saga_id,
            'message': f"Saga {saga_id} rollback failed - manual cleanup required",
            'errors': result.errors,
            'compensation_errors': result.compensation_errors,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to monitoring system (Prometheus, Grafana, etc.)
        logger.critical(json.dumps(alert))
        
        # Could also: Send email, SMS, PagerDuty, etc.
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return {
            'active_sagas': len(self.active_sagas),
            'completed_sagas': len(self.completed_sagas),
            'failed_sagas': len(self.failed_sagas),
            'rollback_stats': self.rollback_stats,
            'success_rate': self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate saga success rate"""
        total = len(self.completed_sagas) + len(self.failed_sagas)
        if total == 0:
            return 100.0
        return (len(self.completed_sagas) / total) * 100.0
```

---

## 8. **Testing Rollback Scenarios**

```python
# Test: Resume fehlschlägt nach 3 Versuchen
def test_resume_fails_triggers_rollback():
    """
    Test: Resume schlägt fehl → Automatischer Rollback
    """
    manager = create_streaming_manager()
    
    # Create test file
    test_file = create_test_file(100)  # 100 MB
    
    # Mock: Resume schlägt immer fehl
    with mock.patch.object(
        manager, 
        'resume_upload', 
        side_effect=StorageBackendError("Backend unavailable")
    ):
        # Attempt create_document_streaming
        result = uds.create_document_streaming(
            file_path=test_file,
            content="",
            chunks=[],
            max_resume_attempts=3
        )
        
        # Verify rollback was performed
        assert result['success'] is False
        assert result['rollback_performed'] is True
        assert result['rollback_status'] == 'success'
        assert 'MAX_RETRIES_EXCEEDED' in str(result['errors'])
        
        # Verify chunks were deleted
        chunks = manager.get_operation_chunks(result['operation_id'])
        assert len(chunks) == 0


# Test: Hash Mismatch triggert Rollback
def test_hash_mismatch_triggers_rollback():
    """
    Test: Datei wurde während Upload modifiziert → Rollback
    """
    # Create test file
    test_file = create_test_file(50)  # 50 MB
    
    # Mock: Modify file during upload
    def modify_file_during_upload(progress):
        if progress.progress_percent > 50:
            # Modify file
            with open(test_file, 'a') as f:
                f.write(b'MODIFIED')
    
    result = uds.create_document_streaming(
        file_path=test_file,
        content="",
        chunks=[],
        progress_callback=modify_file_during_upload
    )
    
    # Verify rollback
    assert result['success'] is False
    assert result['rollback_performed'] is True
    assert 'HASH_MISMATCH' in str(result['errors'])


# Test: Rollback selbst schlägt fehl
def test_rollback_failure_is_logged():
    """
    Test: Rollback schlägt fehl → Critical Log Entry
    """
    # Mock: Compensation schlägt fehl
    with mock.patch(
        'cleanup_chunks_with_verification',
        side_effect=CompensationError("Storage unreachable")
    ):
        result = uds.create_document_streaming(
            file_path=test_file,
            content="",
            chunks=[]
        )
        
        assert result['rollback_performed'] is True
        assert result['rollback_status'] == 'partial_failure'
        assert len(result['compensation_errors']) > 0
        
        # Verify critical log entry
        assert os.path.exists('rollback_failures.json')
```

---

## ✅ Zusammenfassung: Rollback-Strategie

### Wann wird Rollback ausgelöst?

1. ✅ **Resume fehlschlägt** nach N Versuchen (default: 3)
2. ✅ **Integrity Check schlägt fehl** (Hash/Size Mismatch)
3. ✅ **Datei nicht gefunden** (wurde gelöscht/verschoben)
4. ✅ **Chunk-Metadaten korrupt** (kann nicht resume)
5. ✅ **Timeout** überschritten
6. ✅ **Kritische Fehler** in beliebigem Saga Step

### Was passiert beim Rollback?

1. ✅ **Cancel** laufende Streaming-Operation
2. ✅ **Delete** alle hochgeladenen Chunks (verifiziert)
3. ✅ **Remove** Security Records
4. ✅ **Delete** Vector DB Embeddings
5. ✅ **Remove** Graph DB Entries
6. ✅ **Delete** Relational DB Metadata
7. ✅ **Log** Rollback-Status für Monitoring

### Was wenn Rollback fehlschlägt?

1. ✅ **Best Effort:** Fahre mit anderen Compensations fort
2. ✅ **Log Critical Error** für manuelle Intervention
3. ✅ **Store Failed Deletions** in `rollback_failures.json`
4. ✅ **Alert Monitoring System** (Prometheus, etc.)
5. ✅ **Return Partial Success** mit Warnings

### Monitoring

1. ✅ **Active Sagas** - Laufende Operationen
2. ✅ **Rollback Rate** - Erfolgsquote
3. ✅ **Failed Rollbacks** - Manuelle Cleanup nötig
4. ✅ **Success Rate** - Gesamtübersicht
5. ✅ **Alerts** - Critical Failures

---

**Status:** Design Complete ✅  
**Implementation Priority:** CRITICAL  
**Next Step:** Implement in uds3_saga_step_builders.py
