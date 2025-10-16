"""
Event-Bus für Event-Driven Architecture
========================================

Thread-safe EventBus für Observer-Pattern.
Ermöglicht lose Kopplung zwischen Business-Logic und UI.

Version: 4.0.0 (Frontend Modernization)
Date: 14. Oktober 2025

Extracted from: covina_architecture.py (Lines 297-418)
"""

import logging
import queue
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)


# ============================================================================
# Event Types
# ============================================================================

class EventType(Enum):
    """Event-Typen für EventBus"""
    
    # Backend Events
    BACKEND_CONNECTED = "backend_connected"
    BACKEND_DISCONNECTED = "backend_disconnected"
    BACKEND_ERROR = "backend_error"
    
    # Job Events
    JOB_CREATED = "job_created"
    JOB_STATUS_CHANGED = "job_status_changed"
    JOB_PROGRESS_UPDATE = "job_progress_update"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    
    # Upload Events
    UPLOAD_STARTED = "upload_started"
    UPLOAD_PROGRESS = "upload_progress"
    UPLOAD_FILE_COMPLETE = "upload_file_complete"
    UPLOAD_BATCH_COMPLETE = "upload_batch_complete"
    UPLOAD_FINISHED = "upload_finished"
    UPLOAD_ERROR = "upload_error"
    
    # Directory Analysis Events
    DIRECTORY_ANALYSIS_STARTED = "directory_analysis_started"
    DIRECTORY_ANALYSIS_COMPLETE = "directory_analysis_complete"
    DIRECTORY_ANALYSIS_ERROR = "directory_analysis_error"
    
    # UDS3 Events
    UDS3_QUERY_STARTED = "uds3_query_started"
    UDS3_QUERY_COMPLETE = "uds3_query_complete"
    UDS3_QUERY_ERROR = "uds3_query_error"
    
    # Database Events
    DB_HEALTH_CHECK = "db_health_check"
    DB_CONNECTION_LOST = "db_connection_lost"
    DB_CONNECTION_RESTORED = "db_connection_restored"
    
    # SAGA Events
    SAGA_TRANSACTION_STARTED = "saga_transaction_started"
    SAGA_TRANSACTION_COMPLETE = "saga_transaction_complete"
    SAGA_TRANSACTION_FAILED = "saga_transaction_failed"
    SAGA_COMPENSATION_STARTED = "saga_compensation_started"
    
    # Security Events
    SECURITY_AUDIT_LOG = "security_audit_log"
    SECURITY_ALERT = "security_alert"
    
    # Error Events
    ERROR_LOGGED = "error_logged"
    ERROR_CLEARED = "error_cleared"
    
    # Golden Dataset Events
    GOLDEN_DATASET_UPDATED = "golden_dataset_updated"
    GOLDEN_DATASET_VALIDATED = "golden_dataset_validated"
    
    # Recovery Events (NEW v3.4.8)
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETE = "recovery_complete"
    RECOVERY_FAILED = "recovery_failed"
    RECOVERY_FILE_BLOCKED = "recovery_file_blocked"
    RECOVERY_FILE_UNBLOCKED = "recovery_file_unblocked"
    
    # UI Component Events (Phase 2)
    SIDEBAR_LEFT_NAVIGATE = "sidebar_left_navigate"
    SIDEBAR_LEFT_TOGGLED = "sidebar_left_toggled"
    SIDEBAR_RIGHT_TOGGLED = "sidebar_right_toggled"
    QUICK_ACTION_UPLOAD = "quick_action_upload"
    QUICK_ACTION_QUERY = "quick_action_query"
    QUICK_ACTION_LOGS = "quick_action_logs"
    AI_COMMAND_SUBMITTED = "ai_command_submitted"
    AI_RESPONSE = "ai_response"
    AI_TERMINAL_TOGGLED = "ai_terminal_toggled"
    STATUS_BAR_BACKEND_UPDATE = "status_bar_backend_update"
    STATUS_BAR_JOBS_UPDATE = "status_bar_jobs_update"
    STATUS_BAR_RESOURCES_UPDATE = "status_bar_resources_update"
    STATUS_BAR_PROGRESS_UPDATE = "status_bar_progress_update"
    TOOLBAR_HAMBURGER_CLICKED = "toolbar_hamburger_clicked"
    TOOLBAR_SETTINGS_CLICKED = "toolbar_settings_clicked"
    TOOLBAR_PROFILE_CLICKED = "toolbar_profile_clicked"
    
    # View Manager Events (Phase 4)
    VIEW_CHANGED = "view_changed"
    NOTIFICATION = "notification"


# ============================================================================
# Event Data Class
# ============================================================================

@dataclass
class Event:
    """Event-Datenklasse"""
    event_type: EventType
    data: Dict[str, Any]
    source: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __repr__(self) -> str:
        return f"Event({self.event_type.value}, source={self.source}, time={self.timestamp.strftime('%H:%M:%S')})"


# ============================================================================
# EventBus Implementation
# ============================================================================

class EventBus:
    """
    Thread-safe Event-Bus für Observer-Pattern
    
    Ermöglicht lose Kopplung zwischen Business-Logic und UI.
    
    Features:
    - Asynchrone Event-Verarbeitung via Queue
    - Thread-safe Subscription Management
    - Synchrone und asynchrone Event-Emission
    - Graceful Shutdown
    
    Example:
        >>> bus = EventBus()
        >>> bus.start()
        >>> 
        >>> def on_job_created(event: Event):
        >>>     print(f"Job created: {event.data['job_id']}")
        >>> 
        >>> bus.subscribe(EventType.JOB_CREATED, on_job_created)
        >>> bus.emit(EventType.JOB_CREATED, {"job_id": "123"})
        >>> bus.stop()
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, Set[Callable]] = defaultdict(set)
        self._event_queue: queue.Queue = queue.Queue()
        self._running = False
        self._dispatch_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
    
    def start(self):
        """Startet Event-Dispatcher-Thread"""
        if not self._running:
            self._running = True
            self._dispatch_thread = threading.Thread(
                target=self._dispatch_loop, 
                daemon=True,
                name="EventBus-Dispatcher"
            )
            self._dispatch_thread.start()
            logger.info("EventBus gestartet")
    
    def stop(self):
        """Stoppt Event-Dispatcher"""
        self._running = False
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=2.0)
        logger.info("EventBus gestoppt")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        Abonniert Event-Typ
        
        Args:
            event_type: Typ des Events
            callback: Callback-Funktion (Event -> None)
        """
        with self._lock:
            self._subscribers[event_type].add(callback)
            logger.debug(f"Subscriber registriert für {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Entfernt Subscription"""
        with self._lock:
            self._subscribers[event_type].discard(callback)
    
    def emit(self, event_type: EventType, data: Dict[str, Any], source: Optional[str] = None):
        """
        Sendet Event (asynchron via Queue)
        
        Args:
            event_type: Event-Typ
            data: Event-Daten
            source: Quelle des Events (optional)
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source
        )
        self._event_queue.put(event)
    
    def emit_sync(self, event_type: EventType, data: Dict[str, Any], source: Optional[str] = None):
        """
        Sendet Event synchron (blockierend)
        
        Vorsicht: Kann zu Deadlocks führen wenn Callbacks blockieren!
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source
        )
        self._dispatch_event(event)
    
    def _dispatch_loop(self):
        """Event-Dispatch-Loop (läuft in eigenem Thread)"""
        while self._running:
            try:
                # Performance-Optimierung: Kürzerer Timeout für bessere Responsiveness
                # Trade-off: CPU-Last vs. Shutdown-Latenz (100ms ist guter Kompromiss)
                event = self._event_queue.get(timeout=0.1)
                self._dispatch_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Fehler in Event-Dispatch-Loop: {e}")
    
    def _dispatch_event(self, event: Event):
        """Dispatched Event an alle Subscriber"""
        with self._lock:
            subscribers = self._subscribers.get(event.event_type, set()).copy()
        
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Fehler in Event-Callback für {event.event_type.value}: {e}")
