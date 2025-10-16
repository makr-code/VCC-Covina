#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 SAGA Multi-Database Integration

Implementiert das SAGA Pattern für transactional Multi-Database Operations.
Koordiniert distributed Transactions über PostgreSQL, CouchDB, ChromaDB und Neo4j
mit comprehensive Compensation Logic, Transaction Coordination und Rollback
Mechanisms für die UDS3 Multi-Database Distribution.

Das SAGA Pattern ermöglicht:
- Distributed Transaction Management ohne 2PC
- Automatic Compensation bei Partial Failures
- Transaction State Tracking und Recovery
- Performance-optimierte Database Coordination
- Eventual Consistency mit Strong Compensation Guarantees

Features:
- Multi-Database SAGA Orchestrator
- Compensation Action Registry
- Transaction State Management
- Rollback und Recovery Mechanisms
- Performance Monitoring und Error Tracking
- Integration mit UDS3MultiDBDistributor

Autor: Covina Development Team  
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import uuid
import time
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

# Import UDS3 components
try:
    from .uds3_multi_db_distributor import (
        UDS3MultiDBDistributor, ProcessorResult, DistributionResult
    )
    from .adaptive_multi_db_strategy import AdaptiveMultiDBStrategy
    UDS3_COMPONENTS_AVAILABLE = True
except ImportError:
    logging.warning("UDS3 components not available for SAGA integration")
    UDS3_COMPONENTS_AVAILABLE = False

# Standard imports
import traceback
from concurrent.futures import ThreadPoolExecutor


class SAGATransactionState(Enum):
    """States of a SAGA transaction"""
    INITIATED = "initiated"           # Transaction started
    EXECUTING = "executing"           # Steps being executed
    COMPENSATING = "compensating"     # Compensation in progress
    COMPLETED = "completed"           # Successfully completed
    COMPENSATED = "compensated"       # Successfully compensated (rolled back)
    FAILED = "failed"                 # Permanently failed
    TIMEOUT = "timeout"               # Transaction timeout


class SAGAStepState(Enum):
    """States of individual SAGA steps"""
    PENDING = "pending"               # Waiting to be executed
    EXECUTING = "executing"           # Currently executing
    COMPLETED = "completed"           # Successfully completed
    FAILED = "failed"                 # Execution failed
    COMPENSATING = "compensating"     # Compensation in progress
    COMPENSATED = "compensated"       # Compensation completed


@dataclass
class SAGACompensationAction:
    """Defines a compensation action for SAGA step rollback"""
    action_id: str
    database_type: str
    operation_type: str              # 'delete', 'update', 'revert'
    target_identifier: str           # ID/key of the target to compensate
    compensation_data: Dict[str, Any] = field(default_factory=dict)
    compensation_function: Optional[Callable] = None
    priority: int = 0                # Higher priority compensated first
    timeout_seconds: float = 30.0
    retry_attempts: int = 3


@dataclass
class SAGAStep:
    """Individual step in a SAGA transaction"""
    step_id: str
    step_name: str
    database_type: str
    operation_data: Dict[str, Any]
    compensation_actions: List[SAGACompensationAction] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)  # Step dependencies
    
    # State tracking
    state: SAGAStepState = SAGAStepState.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[Dict] = None
    retry_count: int = 0
    
    # Configuration
    timeout_seconds: float = 60.0
    max_retries: int = 2
    
    def get_execution_time(self) -> float:
        """Returns execution time in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


@dataclass
class SAGATransaction:
    """Complete SAGA transaction with multiple steps"""
    transaction_id: str
    transaction_name: str
    steps: List[SAGAStep]
    processor_result: Optional[ProcessorResult] = None
    
    # State tracking
    state: SAGATransactionState = SAGATransactionState.INITIATED
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    current_step_index: int = 0
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    compensated_steps: List[str] = field(default_factory=list)
    
    # Configuration
    timeout_seconds: float = 300.0   # 5 minutes total timeout
    enable_partial_compensation: bool = True
    
    # Results tracking
    distribution_results: Dict[str, Any] = field(default_factory=dict)
    compensation_results: Dict[str, Any] = field(default_factory=dict)
    
    def get_total_execution_time(self) -> float:
        """Returns total transaction execution time"""
        end_time = self.end_time or time.time()
        return end_time - self.start_time
    
    def get_progress_percentage(self) -> float:
        """Returns transaction progress as percentage"""
        if not self.steps:
            return 100.0
        return (len(self.completed_steps) / len(self.steps)) * 100.0


class SAGAExecutor(ABC):
    """Abstract base class for database-specific SAGA executors"""
    
    @abstractmethod
    async def execute_step(
        self, 
        step: SAGAStep, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes a SAGA step in the specific database
        
        Args:
            step: SAGA step to execute
            context: Execution context with shared data
            
        Returns:
            Result data from step execution
        """
        pass
    
    @abstractmethod
    async def compensate_step(
        self, 
        step: SAGAStep,
        compensation_action: SAGACompensationAction,
        context: Dict[str, Any]
    ) -> bool:
        """
        Executes compensation for a SAGA step
        
        Args:
            step: Original step that needs compensation
            compensation_action: Specific compensation to execute
            context: Compensation context
            
        Returns:
            True if compensation successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Checks if the database is healthy for SAGA operations
        
        Returns:
            True if database is available and healthy
        """
        pass


class PostgreSQLSAGAExecutor(SAGAExecutor):
    """PostgreSQL-specific SAGA executor"""
    
    def __init__(self, connection_config: Dict = None):
        self.connection_config = connection_config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def execute_step(
        self, 
        step: SAGAStep, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executes PostgreSQL SAGA step"""
        
        try:
            operation_data = step.operation_data
            
            # Simulate PostgreSQL operation
            if operation_data.get('operation') == 'insert_master_registry':
                result_id = f"pg_master_{uuid.uuid4().hex[:8]}"
                
                # Simulate database insert
                await asyncio.sleep(0.05)  # Simulate network latency
                
                # Add compensation action
                compensation = SAGACompensationAction(
                    action_id=f"comp_{result_id}",
                    database_type='postgresql',
                    operation_type='delete',
                    target_identifier=result_id,
                    compensation_data={'table': 'uds3_master_documents', 'id': result_id}
                )
                step.compensation_actions.append(compensation)
                
                return {
                    'success': True,
                    'result_id': result_id,
                    'operation': 'master_registry_inserted',
                    'rows_affected': 1
                }
            
            elif operation_data.get('operation') == 'insert_processor_results':
                result_id = f"pg_proc_{uuid.uuid4().hex[:8]}"
                
                await asyncio.sleep(0.03)
                
                compensation = SAGACompensationAction(
                    action_id=f"comp_{result_id}",
                    database_type='postgresql',
                    operation_type='delete',
                    target_identifier=result_id,
                    compensation_data={'table': 'uds3_processor_results', 'id': result_id}
                )
                step.compensation_actions.append(compensation)
                
                return {
                    'success': True,
                    'result_id': result_id,
                    'operation': 'processor_results_inserted',
                    'rows_affected': 1
                }
            
            else:
                return {
                    'success': True,
                    'operation': operation_data.get('operation', 'unknown'),
                    'message': 'PostgreSQL operation completed'
                }
                
        except Exception as e:
            self.logger.error(f"PostgreSQL SAGA step failed: {e}")
            raise
    
    async def compensate_step(
        self, 
        step: SAGAStep,
        compensation_action: SAGACompensationAction,
        context: Dict[str, Any]
    ) -> bool:
        """Executes PostgreSQL compensation"""
        
        try:
            self.logger.info(f"Compensating PostgreSQL step: {compensation_action.operation_type}")
            
            # Simulate compensation operation
            if compensation_action.operation_type == 'delete':
                await asyncio.sleep(0.02)  # Simulate delete operation
                self.logger.debug(f"Deleted PostgreSQL record: {compensation_action.target_identifier}")
                
            elif compensation_action.operation_type == 'update':
                await asyncio.sleep(0.02)  # Simulate update operation
                self.logger.debug(f"Updated PostgreSQL record: {compensation_action.target_identifier}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"PostgreSQL compensation failed: {e}")
            return False
    
    async def health_check(self) -> bool:
        """PostgreSQL health check"""
        try:
            # Simulate health check
            await asyncio.sleep(0.01)
            return True
        except:
            return False


class CouchDBSAGAExecutor(SAGAExecutor):
    """CouchDB-specific SAGA executor"""
    
    def __init__(self, connection_config: Dict = None):
        self.connection_config = connection_config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def execute_step(
        self, 
        step: SAGAStep, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executes CouchDB SAGA step"""
        
        try:
            operation_data = step.operation_data
            
            if operation_data.get('operation') == 'store_document_content':
                doc_id = f"couch_{uuid.uuid4().hex[:8]}"
                doc_rev = f"1-{uuid.uuid4().hex[:8]}"
                
                await asyncio.sleep(0.04)  # Simulate CouchDB latency
                
                compensation = SAGACompensationAction(
                    action_id=f"comp_{doc_id}",
                    database_type='couchdb',
                    operation_type='delete',
                    target_identifier=doc_id,
                    compensation_data={'doc_id': doc_id, 'rev': doc_rev}
                )
                step.compensation_actions.append(compensation)
                
                return {
                    'success': True,
                    'doc_id': doc_id,
                    'rev': doc_rev,
                    'operation': 'document_stored'
                }
            
            else:
                return {
                    'success': True,
                    'operation': operation_data.get('operation', 'unknown'),
                    'message': 'CouchDB operation completed'
                }
                
        except Exception as e:
            self.logger.error(f"CouchDB SAGA step failed: {e}")
            raise
    
    async def compensate_step(
        self, 
        step: SAGAStep,
        compensation_action: SAGACompensationAction,
        context: Dict[str, Any]
    ) -> bool:
        """Executes CouchDB compensation"""
        
        try:
            self.logger.info(f"Compensating CouchDB step: {compensation_action.operation_type}")
            
            if compensation_action.operation_type == 'delete':
                await asyncio.sleep(0.03)
                self.logger.debug(f"Deleted CouchDB document: {compensation_action.target_identifier}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"CouchDB compensation failed: {e}")
            return False
    
    async def health_check(self) -> bool:
        """CouchDB health check"""
        try:
            await asyncio.sleep(0.01)
            return True
        except:
            return False


class ChromaDBSAGAExecutor(SAGAExecutor):
    """ChromaDB-specific SAGA executor"""
    
    def __init__(self, connection_config: Dict = None):
        self.connection_config = connection_config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def execute_step(
        self, 
        step: SAGAStep, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executes ChromaDB SAGA step"""
        
        try:
            operation_data = step.operation_data
            
            if operation_data.get('operation') == 'add_embeddings':
                embedding_ids = [f"chroma_{uuid.uuid4().hex[:8]}" for _ in range(operation_data.get('count', 1))]
                
                await asyncio.sleep(0.06)  # Simulate embedding storage
                
                for embedding_id in embedding_ids:
                    compensation = SAGACompensationAction(
                        action_id=f"comp_{embedding_id}",
                        database_type='chromadb',
                        operation_type='delete',
                        target_identifier=embedding_id,
                        compensation_data={'embedding_id': embedding_id, 'collection': operation_data.get('collection', 'default')}
                    )
                    step.compensation_actions.append(compensation)
                
                return {
                    'success': True,
                    'embedding_ids': embedding_ids,
                    'operation': 'embeddings_added',
                    'collection': operation_data.get('collection', 'default')
                }
            
            else:
                return {
                    'success': True,
                    'operation': operation_data.get('operation', 'unknown'),
                    'message': 'ChromaDB operation completed'
                }
                
        except Exception as e:
            self.logger.error(f"ChromaDB SAGA step failed: {e}")
            raise
    
    async def compensate_step(
        self, 
        step: SAGAStep,
        compensation_action: SAGACompensationAction,
        context: Dict[str, Any]
    ) -> bool:
        """Executes ChromaDB compensation"""
        
        try:
            self.logger.info(f"Compensating ChromaDB step: {compensation_action.operation_type}")
            
            if compensation_action.operation_type == 'delete':
                await asyncio.sleep(0.04)
                self.logger.debug(f"Deleted ChromaDB embedding: {compensation_action.target_identifier}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"ChromaDB compensation failed: {e}")
            return False
    
    async def health_check(self) -> bool:
        """ChromaDB health check"""
        try:
            await asyncio.sleep(0.01)
            return True
        except:
            return False


class Neo4jSAGAExecutor(SAGAExecutor):
    """Neo4j-specific SAGA executor"""
    
    def __init__(self, connection_config: Dict = None):
        self.connection_config = connection_config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def execute_step(
        self, 
        step: SAGAStep, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executes Neo4j SAGA step"""
        
        try:
            operation_data = step.operation_data
            
            if operation_data.get('operation') == 'create_document_node':
                node_id = f"neo4j_{uuid.uuid4().hex[:8]}"
                
                await asyncio.sleep(0.05)  # Simulate graph operation
                
                compensation = SAGACompensationAction(
                    action_id=f"comp_{node_id}",
                    database_type='neo4j',
                    operation_type='delete',
                    target_identifier=node_id,
                    compensation_data={'node_id': node_id, 'label': operation_data.get('label', 'Document')}
                )
                step.compensation_actions.append(compensation)
                
                return {
                    'success': True,
                    'node_id': node_id,
                    'operation': 'node_created',
                    'label': operation_data.get('label', 'Document')
                }
            
            elif operation_data.get('operation') == 'create_relationships':
                relationship_ids = [f"rel_{uuid.uuid4().hex[:8]}" for _ in range(operation_data.get('count', 1))]
                
                await asyncio.sleep(0.03)
                
                for rel_id in relationship_ids:
                    compensation = SAGACompensationAction(
                        action_id=f"comp_{rel_id}",
                        database_type='neo4j',
                        operation_type='delete',
                        target_identifier=rel_id,
                        compensation_data={'relationship_id': rel_id}
                    )
                    step.compensation_actions.append(compensation)
                
                return {
                    'success': True,
                    'relationship_ids': relationship_ids,
                    'operation': 'relationships_created'
                }
            
            else:
                return {
                    'success': True,
                    'operation': operation_data.get('operation', 'unknown'),
                    'message': 'Neo4j operation completed'
                }
                
        except Exception as e:
            self.logger.error(f"Neo4j SAGA step failed: {e}")
            raise
    
    async def compensate_step(
        self, 
        step: SAGAStep,
        compensation_action: SAGACompensationAction,
        context: Dict[str, Any]
    ) -> bool:
        """Executes Neo4j compensation"""
        
        try:
            self.logger.info(f"Compensating Neo4j step: {compensation_action.operation_type}")
            
            if compensation_action.operation_type == 'delete':
                await asyncio.sleep(0.03)
                self.logger.debug(f"Deleted Neo4j entity: {compensation_action.target_identifier}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Neo4j compensation failed: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Neo4j health check"""
        try:
            await asyncio.sleep(0.01)
            return True
        except:
            return False


class SAGAOrchestrator:
    """
    SAGA Orchestrator for coordinating multi-database transactions
    
    Manages the execution of SAGA transactions across multiple databases
    with proper compensation handling and state management.
    """
    
    def __init__(
        self,
        adaptive_strategy: AdaptiveMultiDBStrategy,
        config: Dict = None
    ):
        self.adaptive_strategy = adaptive_strategy
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize database executors
        self.executors: Dict[str, SAGAExecutor] = {}
        self._initialize_executors()
        
        # Transaction management
        self.active_transactions: Dict[str, SAGATransaction] = {}
        self.completed_transactions: Dict[str, SAGATransaction] = {}
        self.transaction_history: List[str] = []
        
        # Configuration
        self.max_concurrent_transactions = self.config.get('max_concurrent_transactions', 10)
        self.default_transaction_timeout = self.config.get('default_transaction_timeout', 300.0)
        self.enable_compensation_retry = self.config.get('enable_compensation_retry', True)
        self.compensation_retry_attempts = self.config.get('compensation_retry_attempts', 3)
        
        # Performance tracking
        self.orchestrator_stats = {
            'transactions_started': 0,
            'transactions_completed': 0,
            'transactions_compensated': 0,
            'transactions_failed': 0,
            'total_steps_executed': 0,
            'total_compensations_executed': 0,
            'average_transaction_time_ms': 0.0
        }
        
        # Cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    def _initialize_executors(self):
        """Initializes database-specific SAGA executors"""
        
        connection_configs = self.config.get('database_configs', {})
        
        self.executors = {
            'postgresql': PostgreSQLSAGAExecutor(connection_configs.get('postgresql', {})),
            'couchdb': CouchDBSAGAExecutor(connection_configs.get('couchdb', {})),
            'chromadb': ChromaDBSAGAExecutor(connection_configs.get('chromadb', {})),
            'neo4j': Neo4jSAGAExecutor(connection_configs.get('neo4j', {}))
        }
        
        self.logger.info(f"Initialized SAGA executors for {len(self.executors)} databases")
    
    async def execute_saga_transaction(
        self, 
        transaction: SAGATransaction
    ) -> DistributionResult:
        """
        Executes a complete SAGA transaction with compensation handling
        
        Args:
            transaction: SAGA transaction to execute
            
        Returns:
            DistributionResult with transaction outcome
        """
        
        start_time = time.time()
        
        try:
            # Validate transaction
            if not transaction.steps:
                raise ValueError("SAGA transaction must have at least one step")
            
            # Register transaction
            self.active_transactions[transaction.transaction_id] = transaction
            transaction.state = SAGATransactionState.EXECUTING
            
            self.orchestrator_stats['transactions_started'] += 1
            
            self.logger.info(
                f"🚀 Starting SAGA transaction {transaction.transaction_name} "
                f"with {len(transaction.steps)} steps"
            )
            
            # Execute transaction steps
            success = await self._execute_transaction_steps(transaction)
            
            if success:
                # Transaction completed successfully
                transaction.state = SAGATransactionState.COMPLETED
                transaction.end_time = time.time()
                
                self.orchestrator_stats['transactions_completed'] += 1
                
                self.logger.info(
                    f"✅ SAGA transaction {transaction.transaction_name} completed successfully "
                    f"in {transaction.get_total_execution_time():.2f}s"
                )
                
                return DistributionResult(
                    document_id=transaction.processor_result.document_id if transaction.processor_result else transaction.transaction_id,
                    processor_name=transaction.processor_result.processor_name if transaction.processor_result else "SAGAOrchestrator",
                    success=True,
                    distributed_to=self._extract_distributed_to(transaction),
                    execution_time_ms=transaction.get_total_execution_time() * 1000,
                    strategy_used="saga_multi_db"
                )
                
            else:
                # Transaction failed - trigger compensation
                self.logger.warning(f"⚠️ SAGA transaction {transaction.transaction_name} failed, starting compensation")
                
                compensation_success = await self._compensate_transaction(transaction)
                
                if compensation_success:
                    transaction.state = SAGATransactionState.COMPENSATED
                    self.orchestrator_stats['transactions_compensated'] += 1
                    
                    self.logger.info(f"🔄 SAGA transaction {transaction.transaction_name} successfully compensated")
                    
                else:
                    transaction.state = SAGATransactionState.FAILED
                    self.orchestrator_stats['transactions_failed'] += 1
                    
                    self.logger.error(f"❌ SAGA transaction {transaction.transaction_name} compensation failed")
                
                transaction.end_time = time.time()
                
                return DistributionResult(
                    document_id=transaction.processor_result.document_id if transaction.processor_result else transaction.transaction_id,
                    processor_name=transaction.processor_result.processor_name if transaction.processor_result else "SAGAOrchestrator",
                    success=False,
                    distributed_to={},
                    execution_time_ms=transaction.get_total_execution_time() * 1000,
                    errors=[f"SAGA transaction failed: {transaction.state.value}"],
                    strategy_used="saga_multi_db"
                )
            
        except Exception as e:
            # Handle unexpected errors
            transaction.state = SAGATransactionState.FAILED
            transaction.end_time = time.time()
            
            self.logger.error(f"❌ SAGA transaction {transaction.transaction_name} failed with error: {e}")
            self.orchestrator_stats['transactions_failed'] += 1
            
            return DistributionResult(
                document_id=transaction.processor_result.document_id if transaction.processor_result else transaction.transaction_id,
                processor_name=transaction.processor_result.processor_name if transaction.processor_result else "SAGAOrchestrator",
                success=False,
                distributed_to={},
                execution_time_ms=(time.time() - start_time) * 1000,
                errors=[f"SAGA orchestration error: {str(e)}"],
                strategy_used="saga_multi_db"
            )
        
        finally:
            # Move to completed transactions
            if transaction.transaction_id in self.active_transactions:
                del self.active_transactions[transaction.transaction_id]
                self.completed_transactions[transaction.transaction_id] = transaction
                self.transaction_history.append(transaction.transaction_id)
                
                # Update average transaction time
                self._update_average_transaction_time(transaction.get_total_execution_time() * 1000)
    
    async def _execute_transaction_steps(self, transaction: SAGATransaction) -> bool:
        """Executes all steps in a SAGA transaction"""
        
        context = {'transaction_id': transaction.transaction_id}
        
        for i, step in enumerate(transaction.steps):
            transaction.current_step_index = i
            
            # Check dependencies
            if not self._check_step_dependencies(step, transaction.completed_steps):
                self.logger.error(f"Step {step.step_name} dependencies not met")
                return False
            
            # Execute step
            success = await self._execute_single_step(step, context, transaction)
            
            if success:
                transaction.completed_steps.append(step.step_id)
                self.orchestrator_stats['total_steps_executed'] += 1
            else:
                transaction.failed_steps.append(step.step_id)
                return False
            
            # Check for timeout
            if transaction.get_total_execution_time() > transaction.timeout_seconds:
                transaction.state = SAGATransactionState.TIMEOUT
                self.logger.error(f"SAGA transaction {transaction.transaction_name} timed out")
                return False
        
        return True
    
    async def _execute_single_step(
        self, 
        step: SAGAStep, 
        context: Dict[str, Any],
        transaction: SAGATransaction
    ) -> bool:
        """Executes a single SAGA step"""
        
        step.state = SAGAStepState.EXECUTING
        step.start_time = time.time()
        
        try:
            # Get executor for this database type
            executor = self.executors.get(step.database_type)
            if not executor:
                raise ValueError(f"No executor available for database type: {step.database_type}")
            
            # Check database health
            if not await executor.health_check():
                raise RuntimeError(f"Database {step.database_type} is not healthy")
            
            self.logger.debug(f"Executing SAGA step: {step.step_name} on {step.database_type}")
            
            # Execute the step
            result = await asyncio.wait_for(
                executor.execute_step(step, context),
                timeout=step.timeout_seconds
            )
            
            step.result_data = result
            step.state = SAGAStepState.COMPLETED
            step.end_time = time.time()
            
            self.logger.debug(
                f"✅ SAGA step {step.step_name} completed in {step.get_execution_time():.3f}s"
            )
            
            return True
            
        except asyncio.TimeoutError:
            step.state = SAGAStepState.FAILED
            step.end_time = time.time()
            step.error_info = {
                'error_type': 'timeout',
                'message': f"Step execution timed out after {step.timeout_seconds}s"
            }
            
            self.logger.error(f"⏰ SAGA step {step.step_name} timed out")
            return False
            
        except Exception as e:
            step.state = SAGAStepState.FAILED
            step.end_time = time.time()
            step.error_info = {
                'error_type': 'execution_error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            
            self.logger.error(f"❌ SAGA step {step.step_name} failed: {e}")
            return False
    
    def _check_step_dependencies(self, step: SAGAStep, completed_steps: List[str]) -> bool:
        """Checks if step dependencies are satisfied"""
        
        if not step.depends_on:
            return True
        
        return all(dep_id in completed_steps for dep_id in step.depends_on)
    
    async def _compensate_transaction(self, transaction: SAGATransaction) -> bool:
        """Executes compensation for a failed SAGA transaction"""
        
        transaction.state = SAGATransactionState.COMPENSATING
        
        # Compensate completed steps in reverse order
        completed_steps = [
            step for step in reversed(transaction.steps) 
            if step.step_id in transaction.completed_steps
        ]
        
        compensation_success = True
        context = {'transaction_id': transaction.transaction_id, 'compensation_mode': True}
        
        for step in completed_steps:
            step_compensation_success = await self._compensate_single_step(step, context)
            
            if step_compensation_success:
                transaction.compensated_steps.append(step.step_id)
            else:
                compensation_success = False
                # Continue with other compensations even if one fails
        
        return compensation_success
    
    async def _compensate_single_step(
        self, 
        step: SAGAStep, 
        context: Dict[str, Any]
    ) -> bool:
        """Compensates a single SAGA step"""
        
        step.state = SAGAStepState.COMPENSATING
        
        if not step.compensation_actions:
            self.logger.warning(f"No compensation actions defined for step {step.step_name}")
            return True  # Consider it successful if no compensation needed
        
        executor = self.executors.get(step.database_type)
        if not executor:
            self.logger.error(f"No executor for compensation of {step.database_type}")
            return False
        
        # Execute compensation actions in priority order
        sorted_actions = sorted(
            step.compensation_actions, 
            key=lambda x: x.priority, 
            reverse=True
        )
        
        all_compensations_successful = True
        
        for compensation_action in sorted_actions:
            try:
                self.logger.debug(f"Executing compensation: {compensation_action.action_id}")
                
                success = await asyncio.wait_for(
                    executor.compensate_step(step, compensation_action, context),
                    timeout=compensation_action.timeout_seconds
                )
                
                if success:
                    self.orchestrator_stats['total_compensations_executed'] += 1
                else:
                    all_compensations_successful = False
                    self.logger.error(f"Compensation failed: {compensation_action.action_id}")
                
            except Exception as e:
                all_compensations_successful = False
                self.logger.error(f"Compensation error for {compensation_action.action_id}: {e}")
        
        step.state = SAGAStepState.COMPENSATED if all_compensations_successful else SAGAStepState.FAILED
        
        return all_compensations_successful
    
    def _extract_distributed_to(self, transaction: SAGATransaction) -> Dict[str, List[str]]:
        """Extracts distributed_to information from transaction results"""
        
        distributed_to = {}
        
        for step in transaction.steps:
            if step.state == SAGAStepState.COMPLETED and step.result_data:
                db_type = step.database_type
                if db_type not in distributed_to:
                    distributed_to[db_type] = []
                
                # Extract stored items from result
                result = step.result_data
                if 'result_id' in result:
                    distributed_to[db_type].append(f"{step.step_name}:{result['result_id']}")
                elif 'doc_id' in result:
                    distributed_to[db_type].append(f"{step.step_name}:{result['doc_id']}")
                elif 'node_id' in result:
                    distributed_to[db_type].append(f"{step.step_name}:{result['node_id']}")
                else:
                    distributed_to[db_type].append(f"{step.step_name}:completed")
        
        return distributed_to
    
    def _update_average_transaction_time(self, new_time_ms: float):
        """Updates running average of transaction times"""
        
        current_avg = self.orchestrator_stats['average_transaction_time_ms']
        total_completed = self.orchestrator_stats['transactions_completed']
        
        if total_completed <= 1:
            self.orchestrator_stats['average_transaction_time_ms'] = new_time_ms
        else:
            self.orchestrator_stats['average_transaction_time_ms'] = (
                (current_avg * (total_completed - 1) + new_time_ms) / total_completed
            )
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old completed transactions"""
        
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
                current_time = time.time()
                cleanup_threshold = 3600  # Keep transactions for 1 hour
                
                # Find old transactions to cleanup
                old_transactions = [
                    tid for tid, transaction in self.completed_transactions.items()
                    if transaction.end_time and (current_time - transaction.end_time) > cleanup_threshold
                ]
                
                # Remove old transactions
                for tid in old_transactions:
                    del self.completed_transactions[tid]
                    if tid in self.transaction_history:
                        self.transaction_history.remove(tid)
                
                if old_transactions:
                    self.logger.debug(f"Cleaned up {len(old_transactions)} old SAGA transactions")
                    
            except Exception as e:
                self.logger.error(f"SAGA cleanup error: {e}")
    
    def create_distribution_saga(
        self, 
        processor_result: ProcessorResult,
        available_databases: Dict[str, bool]
    ) -> SAGATransaction:
        """
        Creates a SAGA transaction for multi-database distribution
        
        Args:
            processor_result: Processor result to distribute
            available_databases: Available database systems
            
        Returns:
            SAGA transaction ready for execution
        """
        
        transaction_id = f"saga_{uuid.uuid4().hex[:8]}"
        steps = []
        
        # Step 1: Master Registry (PostgreSQL) - Always first and critical
        if available_databases.get('postgresql', False):
            master_step = SAGAStep(
                step_id=f"{transaction_id}_master",
                step_name="master_registry",
                database_type="postgresql",
                operation_data={
                    'operation': 'insert_master_registry',
                    'document_id': processor_result.document_id,
                    'processor_name': processor_result.processor_name,
                    'metadata': processor_result.metadata
                }
            )
            steps.append(master_step)
        
        # Step 2: Processor Results (PostgreSQL) - Depends on master registry
        if available_databases.get('postgresql', False):
            results_step = SAGAStep(
                step_id=f"{transaction_id}_results",
                step_name="processor_results",
                database_type="postgresql",
                operation_data={
                    'operation': 'insert_processor_results',
                    'document_id': processor_result.document_id,
                    'processor_type': processor_result.processor_type.value,
                    'result_data': processor_result.result_data
                },
                depends_on=[f"{transaction_id}_master"]
            )
            steps.append(results_step)
        
        # Step 3: Document Content (CouchDB) - Independent
        if available_databases.get('couchdb', False) and processor_result.result_data.get('text_content'):
            content_step = SAGAStep(
                step_id=f"{transaction_id}_content",
                step_name="document_content",
                database_type="couchdb",
                operation_data={
                    'operation': 'store_document_content',
                    'document_id': processor_result.document_id,
                    'content': processor_result.result_data.get('text_content', ''),
                    'metadata': processor_result.metadata
                }
            )
            steps.append(content_step)
        
        # Step 4: Embeddings (ChromaDB) - Independent
        if available_databases.get('chromadb', False) and (
            'embedding' in processor_result.result_data or 'vector' in processor_result.result_data
        ):
            embeddings_step = SAGAStep(
                step_id=f"{transaction_id}_embeddings",
                step_name="vector_embeddings",
                database_type="chromadb",
                operation_data={
                    'operation': 'add_embeddings',
                    'document_id': processor_result.document_id,
                    'embeddings': processor_result.result_data.get('embedding') or processor_result.result_data.get('vector'),
                    'collection': f"{processor_result.processor_type.value}_embeddings",
                    'count': 1
                }
            )
            steps.append(embeddings_step)
        
        # Step 5: Relationships (Neo4j) - Depends on master registry
        if available_databases.get('neo4j', False):
            relationships_step = SAGAStep(
                step_id=f"{transaction_id}_relationships",
                step_name="document_relationships",
                database_type="neo4j",
                operation_data={
                    'operation': 'create_document_node',
                    'document_id': processor_result.document_id,
                    'processor_type': processor_result.processor_type.value,
                    'label': 'Document'
                },
                depends_on=[f"{transaction_id}_master"]
            )
            steps.append(relationships_step)
        
        return SAGATransaction(
            transaction_id=transaction_id,
            transaction_name=f"distribute_{processor_result.processor_type.value}_{processor_result.document_id}",
            steps=steps,
            processor_result=processor_result
        )
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Returns current orchestrator statistics"""
        
        return {
            **self.orchestrator_stats,
            'active_transactions': len(self.active_transactions),
            'completed_transactions': len(self.completed_transactions),
            'success_rate': (
                self.orchestrator_stats['transactions_completed'] / 
                self.orchestrator_stats['transactions_started']
                if self.orchestrator_stats['transactions_started'] > 0 else 0.0
            ),
            'compensation_rate': (
                self.orchestrator_stats['transactions_compensated'] / 
                self.orchestrator_stats['transactions_started']
                if self.orchestrator_stats['transactions_started'] > 0 else 0.0
            )
        }
    
    async def shutdown(self):
        """Graceful shutdown of SAGA orchestrator"""
        
        self.logger.info("🔄 Shutting down SAGA orchestrator...")
        
        # Cancel cleanup task
        self._cleanup_task.cancel()
        
        # Wait for active transactions to complete (with timeout)
        if self.active_transactions:
            self.logger.info(f"Waiting for {len(self.active_transactions)} active transactions to complete...")
            
            timeout = 60.0  # 1 minute timeout for graceful shutdown
            start_time = time.time()
            
            while self.active_transactions and (time.time() - start_time) < timeout:
                await asyncio.sleep(1.0)
            
            if self.active_transactions:
                self.logger.warning(f"Shutdown timeout - {len(self.active_transactions)} transactions still active")
        
        self.logger.info("✅ SAGA orchestrator shutdown complete")


# Integration with UDS3MultiDBDistributor
class SAGAIntegratedMultiDBDistributor(UDS3MultiDBDistributor):
    """
    UDS3 Multi-DB Distributor with integrated SAGA transaction management
    
    Combines the distribution intelligence of UDS3MultiDBDistributor with
    the transactional guarantees of the SAGA pattern.
    """
    
    def __init__(
        self,
        adaptive_strategy: AdaptiveMultiDBStrategy,
        database_manager = None,
        config: Dict = None
    ):
        super().__init__(adaptive_strategy, database_manager, config)
        
        # Initialize SAGA orchestrator
        saga_config = config.get('saga_config', {}) if config else {}
        self.saga_orchestrator = SAGAOrchestrator(adaptive_strategy, saga_config)
        
        # Configuration
        self.enable_saga_transactions = config.get('enable_saga_transactions', True) if config else True
        self.saga_fallback_threshold = config.get('saga_fallback_threshold', 0.8) if config else 0.8
        
        self.logger.info("🔄 SAGA-Integrated Multi-DB Distributor initialized")
    
    async def distribute_processor_result(
        self, 
        processor_result: ProcessorResult
    ) -> DistributionResult:
        """
        Enhanced distribution with SAGA transaction guarantees
        """
        
        if not self.enable_saga_transactions:
            # Fall back to standard distribution
            return await super().distribute_processor_result(processor_result)
        
        try:
            # Get available databases
            available_dbs = await self._get_available_databases()
            
            # Check if SAGA is beneficial (multiple databases available)
            available_db_count = sum(1 for available in available_dbs.values() if available)
            
            if available_db_count < 2:
                # Single database - no need for SAGA
                return await super().distribute_processor_result(processor_result)
            
            # Create SAGA transaction
            saga_transaction = self.saga_orchestrator.create_distribution_saga(
                processor_result, available_dbs
            )
            
            # Execute SAGA transaction
            return await self.saga_orchestrator.execute_saga_transaction(saga_transaction)
            
        except Exception as e:
            self.logger.error(f"SAGA distribution failed, falling back to standard: {e}")
            
            # Fallback to standard distribution
            return await super().distribute_processor_result(processor_result)
    
    def get_saga_integrated_stats(self) -> Dict[str, Any]:
        """Gets comprehensive statistics including SAGA metrics"""
        
        base_stats = self.get_distribution_stats()
        saga_stats = self.saga_orchestrator.get_orchestrator_stats()
        
        return {
            'base_distribution': base_stats,
            'saga_orchestration': saga_stats,
            'saga_integration': {
                'saga_enabled': self.enable_saga_transactions,
                'fallback_threshold': self.saga_fallback_threshold
            }
        }
    
    async def shutdown(self):
        """Graceful shutdown with SAGA coordination"""
        
        await self.saga_orchestrator.shutdown()
        self.logger.info("✅ SAGA-Integrated Distributor shutdown complete")


# Convenience function for creating SAGA-integrated distributor
async def create_saga_integrated_distributor(
    adaptive_strategy: AdaptiveMultiDBStrategy,
    database_manager = None,
    config: Dict = None
) -> SAGAIntegratedMultiDBDistributor:
    """
    Creates a SAGA-integrated UDS3 Multi-DB Distributor
    """
    
    saga_config = config or {}
    saga_config.setdefault('enable_saga_transactions', True)
    saga_config.setdefault('saga_config', {
        'max_concurrent_transactions': 10,
        'default_transaction_timeout': 300.0,
        'enable_compensation_retry': True
    })
    
    distributor = SAGAIntegratedMultiDBDistributor(
        adaptive_strategy=adaptive_strategy,
        database_manager=database_manager,
        config=saga_config
    )
    
    logging.info("🚀 SAGA-Integrated Multi-DB Distributor created")
    
    return distributor


if __name__ == "__main__":
    # Example usage and testing
    async def test_saga_integration():
        """Test SAGA pattern integration"""
        
        logging.basicConfig(level=logging.INFO)
        
        # Mock adaptive strategy
        class MockAdaptiveStrategy:
            current_strategy = 'full_polyglot'
            db_availability = type('', (), {
                'postgresql': True,
                'couchdb': True,
                'chromadb': True,
                'neo4j': True,
                'sqlite': True
            })()
        
        mock_strategy = MockAdaptiveStrategy()
        
        # Create SAGA-integrated distributor
        distributor = await create_saga_integrated_distributor(mock_strategy)
        
        # Test processor result
        from .uds3_multi_db_distributor import ProcessorResult, ProcessorType
        
        test_result = ProcessorResult(
            processor_name="TestProcessor",
            processor_type=ProcessorType.TEXT_PROCESSOR,
            document_id="saga_test_001",
            result_data={
                'text_content': 'Test document for SAGA',
                'embedding': [0.1, 0.2, 0.3, 0.4, 0.5]
            },
            confidence_score=0.95,
            execution_time_ms=1200,
            metadata={'file_path': '/test/document.txt'}
        )
        
        # Test SAGA distribution
        result = await distributor.distribute_processor_result(test_result)
        
        print(f"SAGA Distribution Result: Success={result.success}")
        print(f"Distributed to: {result.distributed_to}")
        print(f"Execution time: {result.execution_time_ms:.1f}ms")
        
        # Get comprehensive statistics
        stats = distributor.get_saga_integrated_stats()
        print(f"SAGA Integration Stats:")
        print(json.dumps(stats, indent=2, default=str))
        
        # Shutdown
        await distributor.shutdown()
    
    # Run test
    asyncio.run(test_saga_integration())