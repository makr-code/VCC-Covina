#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UDS3 Saga Orchestrator - Wrapper

OPTIMIZED (1. Okt 2025): Thin wrapper around database/saga_orchestrator.py
BEFORE: 34 KB, 931 LOC | AFTER: 7 KB, 250 LOC | SAVINGS: -27 KB, -681 LOC
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Lazy loading zur Vermeidung zirkulärer Imports
DatabaseSagaOrchestrator = None
DatabaseManager = None
SAGA_BACKEND_AVAILABLE = False

def _lazy_import_saga_backend():
    """Lazy loading der SAGA Backend Klassen zur Vermeidung zirkulärer Imports"""
    global DatabaseSagaOrchestrator, DatabaseManager, SAGA_BACKEND_AVAILABLE
    
    if SAGA_BACKEND_AVAILABLE:
        return True
    
    try:
        import sys
        import os
        
        # Add uds3 directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Lazy import at runtime to avoid circular imports
        import importlib
        
        # Import SagaOrchestrator
        saga_module = importlib.import_module('database.saga_orchestrator')
        DatabaseSagaOrchestrator = getattr(saga_module, 'SagaOrchestrator')
        
        # DatabaseManager optional - nur wenn verfügbar
        try:
            db_module = importlib.import_module('database.database_manager')
            DatabaseManager = getattr(db_module, 'DatabaseManager')
        except (ImportError, AttributeError):
            DatabaseManager = None
        
        SAGA_BACKEND_AVAILABLE = True
        logger.info("✅ Database Saga Orchestrator erfolgreich geladen (lazy import)")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Database Saga Orchestrator konnte nicht geladen werden: {e}")
        DatabaseSagaOrchestrator = None
        DatabaseManager = None
        SAGA_BACKEND_AVAILABLE = False
        return False

logger = logging.getLogger(__name__)

class SagaExecutionError(Exception):
    pass

class SagaCompensationError(Exception):
    pass

class SagaStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"

SagaAction = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
SagaCompensation = Callable[[Dict[str, Any]], None]

@dataclass(slots=True)
class SagaStep:
    name: str
    action: SagaAction
    compensation: Optional[SagaCompensation] = None

@dataclass(slots=True)
class SagaDefinition:
    name: str
    steps: List[SagaStep]

@dataclass(slots=True)
class SagaExecutionResult:
    saga_id: str
    status: SagaStatus
    context: Dict[str, Any]
    errors: List[str]
    compensation_errors: List[str]

class UDS3SagaOrchestrator:
    def __init__(self, relational_backend: Optional[Any] = None):
        self.logger = logging.getLogger("uds3.saga.orchestrator")
        
        # Versuche lazy import der SAGA Backend Klassen
        if not _lazy_import_saga_backend():
            self.logger.warning("⚠️ Database Saga Orchestrator nicht verfügbar - verwende Mock-Implementation")
            self._orchestrator = self._create_mock_orchestrator()
        else:
            try:
                self._orchestrator = DatabaseSagaOrchestrator()
                self.logger.info("✅ UDS3 Saga Orchestrator initialized (wrapper mode)")
            except Exception as exc:
                self.logger.warning(f"⚠️ Saga Orchestrator Fehler: {exc} - verwende Mock-Implementation")
                self._orchestrator = self._create_mock_orchestrator()

    def _create_mock_orchestrator(self):
        """Creates a mock orchestrator for fallback"""
        class MockOrchestrator:
            def create_saga(self, name=None, steps=None, trace_id=None):
                """Mock implementation of create_saga"""
                return f"mock_saga_{hash(str(steps or []))}"
            
            def execute(self, definition, context=None, saga_id=None):
                # Mock implementation that just executes steps sequentially
                ctx = dict(context or {})
                saga_id = saga_id or f"mock_{hash(str(definition))}"
                
                for step in definition.steps:
                    try:
                        if hasattr(step, 'action') and step.action:
                            result = step.action(ctx)
                            if result:
                                ctx.update(result)
                    except Exception as e:
                        return {
                            'saga_id': saga_id,
                            'status': 'FAILED',
                            'context': ctx,
                            'errors': [str(e)],
                            'compensation_errors': []
                        }
                
                return {
                    'saga_id': saga_id,
                    'status': 'COMPLETED',
                    'context': ctx,
                    'errors': [],
                    'compensation_errors': []
                }
        
        return MockOrchestrator()

    def execute(self, definition: SagaDefinition, context: Optional[Dict[str, Any]] = None, *, saga_id: Optional[str] = None) -> SagaExecutionResult:
        ctx = dict(context or {})
        errors = []
        compensation_errors = []
        try:
            steps_data = [{'name': s.name, 'action': s.action, 'compensation': s.compensation} for s in definition.steps]
            trace_id = ctx.get('trace_id')
            db_saga_id = self._orchestrator.create_saga(name=definition.name, steps=steps_data, trace_id=trace_id)
            if saga_id is None:
                saga_id = db_saga_id
            executed_steps = []
            status = SagaStatus.RUNNING
            for step in definition.steps:
                try:
                    self.logger.info(f"Executing saga step: {step.name}")
                    if step.action:
                        result = step.action(ctx)
                        if result is not None:
                            ctx.update(result)
                    executed_steps.append(step)
                except Exception as exc:
                    error_msg = f"Step {step.name} failed: {exc}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    status = SagaStatus.COMPENSATING
                    for comp_step in reversed(executed_steps):
                        if comp_step.compensation:
                            try:
                                self.logger.info(f"Compensating: {comp_step.name}")
                                comp_step.compensation(ctx)
                            except Exception as comp_exc:
                                comp_error = f"Compensation for {comp_step.name} failed: {comp_exc}"
                                compensation_errors.append(comp_error)
                                self.logger.error(comp_error)
                    status = SagaStatus.COMPENSATION_FAILED if compensation_errors else SagaStatus.COMPENSATED
                    break
            else:
                status = SagaStatus.COMPLETED
            return SagaExecutionResult(saga_id=saga_id, status=status, context=ctx, errors=errors, compensation_errors=compensation_errors)
        except Exception as exc:
            self.logger.error(f"Saga execution failed: {exc}")
            return SagaExecutionResult(saga_id=saga_id or "unknown", status=SagaStatus.FAILED, context=ctx, errors=[str(exc)] + errors, compensation_errors=compensation_errors)

    def get_saga_status(self, saga_id: str) -> Dict[str, Any]:
        try:
            return self._orchestrator.get_saga_status(saga_id)
        except AttributeError:
            self.logger.warning("get_saga_status not implemented in backend orchestrator")
            return {"saga_id": saga_id, "status": "unknown", "message": "Backend does not support status queries"}

_saga_orchestrator = None
_orchestrator_lock = None
try:
    import threading
    _orchestrator_lock = threading.Lock()
except ImportError:
    pass

def get_saga_orchestrator(relational_backend: Optional[Any] = None) -> UDS3SagaOrchestrator:
    global _saga_orchestrator
    if _saga_orchestrator is None:
        if _orchestrator_lock:
            with _orchestrator_lock:
                if _saga_orchestrator is None:
                    _saga_orchestrator = UDS3SagaOrchestrator(relational_backend)
        else:
            _saga_orchestrator = UDS3SagaOrchestrator(relational_backend)
    return _saga_orchestrator

__all__ = ['UDS3SagaOrchestrator', 'SagaExecutionResult', 'SagaDefinition', 'SagaStep', 'SagaStatus', 'SagaExecutionError', 'SagaCompensationError', 'get_saga_orchestrator', 'SagaAction', 'SagaCompensation']
