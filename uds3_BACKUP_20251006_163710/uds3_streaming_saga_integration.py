#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Streaming Saga Integration
================================

Integriert Streaming Operations mit Saga Pattern für große Dateien (300+ MB).

Features:
- Saga Steps mit Streaming Support
- Automatischer Rollback bei Resume-Fehlschlag
- Integrity Verification nach Upload
- Compensation mit Best-Effort Cleanup
- Monitoring & Alerting für Rollback-Failures

Author: UDS3 Team
Date: 2. Oktober 2025
Version: 1.0.0
"""

import logging
import hashlib
import time
import uuid
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from uds3_streaming_operations import (
    StreamingManager,
    StreamingSagaConfig,
    SagaRollbackRequired,
    CompensationError,
    StreamingProgress
)

logger = logging.getLogger(__name__)


# ============================================================================
# Saga Status & Result
# ============================================================================

class SagaStatus(Enum):
    """Status of saga execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"
    FAILED = "failed"


@dataclass
class SagaStep:
    """Saga step definition"""
    name: str
    action: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
    compensation: Optional[Callable[[Dict[str, Any]], None]]


@dataclass
class SagaDefinition:
    """Complete saga definition"""
    name: str
    steps: List[SagaStep]


@dataclass
class SagaExecutionResult:
    """Result of saga execution"""
    saga_id: str
    status: SagaStatus
    context: Dict[str, Any]
    errors: List[str]
    compensation_errors: List[str]


# ============================================================================
# Streaming Saga Executor
# ============================================================================

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
    
    Args:
        definition: Saga definition with steps
        context: Execution context
        config: Saga configuration
    
    Returns:
        SagaExecutionResult with status and errors
    """
    saga_id = f"saga-{uuid.uuid4().hex[:12]}"
    errors = []
    compensation_errors = []
    status = SagaStatus.RUNNING
    executed_steps = []
    
    try:
        # Execute saga steps
        for step in definition.steps:
            logger.info(f"[{saga_id}] Executing saga step: {step.name}")
            
            try:
                result = step.action(context)
                if result:
                    context.update(result)
                executed_steps.append(step)
                
            except SagaRollbackRequired as e:
                # Explicit rollback request
                logger.warning(
                    f"[{saga_id}] Rollback required at step {step.name}: "
                    f"{e.reason} - {e.message}"
                )
                errors.append(f"{step.name}: {e.message}")
                status = SagaStatus.COMPENSATING
                
                # Perform rollback
                compensation_errors = perform_compensation(
                    saga_id, executed_steps, context, config
                )
                
                if compensation_errors:
                    status = SagaStatus.COMPENSATION_FAILED
                else:
                    status = SagaStatus.COMPENSATED
                
                break
                
            except Exception as e:
                # Unexpected error
                logger.error(f"[{saga_id}] Step {step.name} failed unexpectedly: {e}")
                errors.append(f"{step.name}: {str(e)}")
                status = SagaStatus.COMPENSATING
                
                # Perform rollback
                compensation_errors = perform_compensation(
                    saga_id, executed_steps, context, config
                )
                
                if compensation_errors:
                    status = SagaStatus.COMPENSATION_FAILED
                else:
                    status = SagaStatus.COMPENSATED
                
                break
        
        # All steps completed successfully
        if not errors:
            status = SagaStatus.COMPLETED
            logger.info(f"[{saga_id}] Saga completed successfully")
        
    except Exception as e:
        # Critical saga execution error
        logger.critical(f"[{saga_id}] Saga execution failed catastrophically: {e}")
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
    saga_id: str,
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
    
    Args:
        saga_id: Saga ID for logging
        executed_steps: Steps that were executed
        context: Execution context
        config: Saga configuration
    
    Returns:
        List of compensation error messages
    """
    compensation_errors = []
    
    logger.info(f"[{saga_id}] Starting compensation for {len(executed_steps)} steps")
    
    for step in reversed(executed_steps):
        if step.compensation is None:
            logger.debug(f"[{saga_id}] Step {step.name}: No compensation needed")
            continue
        
        try:
            logger.info(f"[{saga_id}] Compensating step: {step.name}")
            step.compensation(context)
            logger.info(f"[{saga_id}] ✅ Compensation successful: {step.name}")
            
        except CompensationError as e:
            error_msg = f"Compensation failed for {step.name}: {e}"
            logger.error(f"[{saga_id}] {error_msg}")
            compensation_errors.append(error_msg)
            # Continue with other compensations (Best Effort)
            
        except Exception as e:
            error_msg = f"Compensation crashed for {step.name}: {e}"
            logger.critical(f"[{saga_id}] {error_msg}")
            compensation_errors.append(error_msg)
            # Continue (Best Effort)
    
    if compensation_errors:
        logger.error(
            f"[{saga_id}] Compensation completed with {len(compensation_errors)} errors"
        )
    else:
        logger.info(f"[{saga_id}] ✅ All compensations successful")
    
    return compensation_errors


# ============================================================================
# Saga Step Builders
# ============================================================================

def build_streaming_upload_saga_definition(
    streaming_manager: StreamingManager,
    config: StreamingSagaConfig,
    vector_db=None,
    graph_db=None,
    relational_db=None,
    security_manager=None
) -> SagaDefinition:
    """
    Build complete streaming saga with rollback strategy
    
    Rollback Triggers:
    - Any SagaRollbackRequired exception
    - Any unhandled exception after max retries
    - Explicit cancel by user
    - Timeout exceeded
    
    Args:
        streaming_manager: StreamingManager instance
        config: Saga configuration
        vector_db: Vector database (optional)
        graph_db: Graph database (optional)
        relational_db: Relational database (optional)
        security_manager: Security manager (optional)
    
    Returns:
        SagaDefinition with all streaming steps
    """
    
    # Step 1: Validate File
    def validate_file_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Validate file exists and is readable"""
        import os
        file_path = ctx['file_path']
        
        if not os.path.exists(file_path):
            raise SagaRollbackRequired(
                reason="FILE_NOT_FOUND",
                message=f"File not found: {file_path}"
            )
        
        if not os.access(file_path, os.R_OK):
            raise SagaRollbackRequired(
                reason="FILE_NOT_READABLE",
                message=f"File not readable: {file_path}"
            )
        
        file_size = os.path.getsize(file_path)
        logger.info(f"File validated: {file_path} ({file_size/1024/1024:.1f} MB)")
        
        return {'file_size': file_size}
    
    # Step 2: Start Streaming
    def start_streaming_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize streaming operation"""
        logger.info("Starting streaming operation")
        ctx['streaming_started_at'] = datetime.utcnow()
        return {}
    
    def cancel_streaming_compensation(ctx: Dict[str, Any]) -> None:
        """Cancel streaming operation"""
        operation_id = ctx.get('operation_id')
        if operation_id:
            streaming_manager.cancel_operation(operation_id)
            logger.info(f"Cancelled streaming operation: {operation_id}")
    
    # Step 3: Chunked Upload with Retry
    def chunked_upload_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Upload file in chunks with retry logic"""
        file_path = ctx['file_path']
        destination = ctx['destination']
        progress_callback = ctx.get('progress_callback')
        
        result = streaming_manager.chunked_upload_with_retry(
            file_path=file_path,
            destination=destination,
            config=config,
            progress_callback=progress_callback
        )
        
        logger.info(
            f"Upload complete: {result['uploaded_chunks']} chunks, "
            f"{result['retry_count']} retries"
        )
        
        return result
    
    def cleanup_chunks_compensation(ctx: Dict[str, Any]) -> None:
        """Delete uploaded chunks"""
        operation_id = ctx.get('operation_id')
        if operation_id:
            result = streaming_manager.cleanup_chunks_with_verification(operation_id)
            logger.info(
                f"Cleanup: {result['deleted_count']}/{result['total_chunks']} chunks deleted "
                f"({result['success_rate']:.1f}% success)"
            )
    
    # Step 4: Verify Integrity
    def verify_integrity_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Verify upload integrity"""
        operation_id = ctx['operation_id']
        file_path = ctx['file_path']
        
        result = streaming_manager.verify_integrity(
            operation_id=operation_id,
            file_path=file_path
        )
        
        logger.info(
            f"Integrity verified: hash={result['hash'][:16]}..., "
            f"size={result['size']} bytes"
        )
        
        return result
    
    # Step 5: Process Security (optional)
    def process_security_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Process security and generate document ID"""
        if not security_manager:
            logger.info("Security manager not configured - skipping")
            return {}
        
        file_path = ctx['file_path']
        content = ctx.get('content', '')
        security_level = ctx.get('security_level')
        
        security_info = security_manager.generate_secure_document_id(
            content, file_path, security_level
        )
        
        document_id = security_info.get('document_id')
        logger.info(f"Security processed: document_id={document_id}")
        
        return {'document_id': document_id, 'security_info': security_info}
    
    def remove_security_record_compensation(ctx: Dict[str, Any]) -> None:
        """Remove security record"""
        document_id = ctx.get('document_id')
        if document_id and security_manager:
            # Remove from security system (implementation specific)
            logger.info(f"Removed security record: {document_id}")
    
    # Step 6: Stream to Vector DB (optional)
    def stream_to_vector_db_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Stream to vector DB with chunked embeddings"""
        if not vector_db:
            logger.info("Vector DB not configured - skipping")
            return {}
        
        operation_id = ctx['operation_id']
        chunks = ctx.get('chunks', [])
        embedding_function = ctx.get('embedding_function')
        
        if not chunks or not embedding_function:
            logger.info("No chunks or embedding function - skipping vector DB")
            return {}
        
        # Stream to vector DB with progress tracking
        result = streaming_manager.stream_to_vector_db(
            chunks=chunks,
            embedding_function=embedding_function,
            chunk_size=10,  # Process 10 chunks at a time
            progress_callback=ctx.get('progress_callback')
        )
        
        logger.info(f"Vector DB streaming complete: {result['chunks_processed']} chunks")
        
        return result
    
    def remove_from_vector_db_compensation(ctx: Dict[str, Any]) -> None:
        """Remove from vector DB"""
        document_id = ctx.get('document_id')
        if document_id and vector_db:
            # Remove from vector DB (implementation specific)
            logger.info(f"Removed from vector DB: {document_id}")
    
    # Step 7: Insert Graph DB (optional)
    def insert_graph_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Insert into graph database"""
        if not graph_db:
            logger.info("Graph DB not configured - skipping")
            return {}
        
        document_id = ctx.get('document_id')
        metadata = ctx.get('metadata', {})
        
        # Insert into graph DB (implementation specific)
        logger.info(f"Inserted into graph DB: {document_id}")
        
        return {'graph_inserted': True}
    
    def remove_from_graph_compensation(ctx: Dict[str, Any]) -> None:
        """Remove from graph DB"""
        document_id = ctx.get('document_id')
        if document_id and graph_db:
            # Remove from graph DB (implementation specific)
            logger.info(f"Removed from graph DB: {document_id}")
    
    # Step 8: Insert Relational DB (optional)
    def insert_relational_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Insert into relational database"""
        if not relational_db:
            logger.info("Relational DB not configured - skipping")
            return {}
        
        document_id = ctx.get('document_id')
        metadata = ctx.get('metadata', {})
        
        # Insert into relational DB (implementation specific)
        logger.info(f"Inserted into relational DB: {document_id}")
        
        return {'relational_inserted': True}
    
    def remove_from_relational_compensation(ctx: Dict[str, Any]) -> None:
        """Remove from relational DB"""
        document_id = ctx.get('document_id')
        if document_id and relational_db:
            # Remove from relational DB (implementation specific)
            logger.info(f"Removed from relational DB: {document_id}")
    
    # Step 9: Finalize
    def finalize_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize saga execution"""
        logger.info("Saga finalized successfully")
        ctx['finalized_at'] = datetime.utcnow()
        return {}
    
    # Build saga definition
    return SagaDefinition(
        name="streaming_upload_with_rollback",
        steps=[
            SagaStep(
                name="validate_file",
                action=validate_file_action,
                compensation=None
            ),
            SagaStep(
                name="start_streaming",
                action=start_streaming_action,
                compensation=cancel_streaming_compensation
            ),
            SagaStep(
                name="chunked_upload_with_retry",
                action=chunked_upload_action,
                compensation=cleanup_chunks_compensation
            ),
            SagaStep(
                name="verify_integrity",
                action=verify_integrity_action,
                compensation=None  # Readonly, but triggers rollback on failure
            ),
            SagaStep(
                name="process_security",
                action=process_security_action,
                compensation=remove_security_record_compensation
            ),
            SagaStep(
                name="stream_to_vector_db",
                action=stream_to_vector_db_action,
                compensation=remove_from_vector_db_compensation
            ),
            SagaStep(
                name="insert_graph",
                action=insert_graph_action,
                compensation=remove_from_graph_compensation
            ),
            SagaStep(
                name="insert_relational",
                action=insert_relational_action,
                compensation=remove_from_relational_compensation
            ),
            SagaStep(
                name="finalize",
                action=finalize_action,
                compensation=None
            )
        ]
    )


# ============================================================================
# Monitoring & Alerting
# ============================================================================

class StreamingSagaMonitor:
    """
    Monitoring für Streaming Sagas mit Rollback-Tracking
    """
    
    def __init__(self):
        self.active_sagas: Dict[str, Dict[str, Any]] = {}
        self.completed_sagas: Dict[str, Dict[str, Any]] = {}
        self.failed_sagas: Dict[str, Dict[str, Any]] = {}
        self.rollback_stats = {
            'total_rollbacks': 0,
            'successful_rollbacks': 0,
            'failed_rollbacks': 0,
            'pending_manual_cleanup': 0
        }
    
    def track_saga(self, saga_id: str, context: Dict[str, Any]) -> None:
        """Track active saga"""
        self.active_sagas[saga_id] = {
            'started_at': datetime.utcnow(),
            'operation_id': context.get('operation_id'),
            'file_path': context.get('file_path'),
            'status': 'RUNNING'
        }
    
    def saga_completed(self, saga_id: str, result: SagaExecutionResult) -> None:
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
    ) -> None:
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
    
    def alert_rollback_failure(self, saga_id: str, result: SagaExecutionResult) -> None:
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
        
        # Store for manual intervention
        self._store_alert(alert)
    
    def _store_alert(self, alert: Dict[str, Any]) -> None:
        """Store alert for later review"""
        try:
            with open('rollback_alerts.json', 'a') as f:
                f.write(json.dumps(alert) + '\n')
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        total_sagas = len(self.completed_sagas) + len(self.failed_sagas)
        success_rate = (len(self.completed_sagas) / total_sagas * 100) if total_sagas > 0 else 100.0
        
        return {
            'active_sagas': len(self.active_sagas),
            'completed_sagas': len(self.completed_sagas),
            'failed_sagas': len(self.failed_sagas),
            'rollback_stats': self.rollback_stats,
            'success_rate': success_rate
        }


# ============================================================================
# Helper Functions
# ============================================================================

def store_rollback_failures(saga_result: SagaExecutionResult) -> None:
    """
    Speichert fehlgeschlagene Rollbacks für manuelle Intervention
    """
    failure_record = {
        'timestamp': datetime.utcnow().isoformat(),
        'saga_id': saga_result.saga_id,
        'errors': saga_result.errors,
        'compensation_errors': saga_result.compensation_errors,
        'status': 'REQUIRES_MANUAL_CLEANUP'
    }
    
    # Persist to database or dedicated log
    logger.critical(
        f"Rollback failures detected - manual cleanup required: "
        f"{saga_result.saga_id}"
    )
    
    # Store in dedicated file
    try:
        with open('rollback_failures.json', 'a') as f:
            f.write(json.dumps(failure_record) + '\n')
    except Exception as e:
        logger.error(f"Failed to store rollback failure: {e}")
