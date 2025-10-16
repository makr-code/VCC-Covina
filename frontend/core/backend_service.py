"""
Backend Service - API Abstraction Layer
========================================

Zentrale Business-Logic-Schicht für Covina Frontend.
Trennt Business-Logic von UI-Code. Kommuniziert via EventBus.

Version: 4.0.0 (Frontend Modernization)
Date: 14. Oktober 2025

Simplified extraction from: covina_architecture.py (Lines 1001-1600)
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from .event_bus import Event, EventBus, EventType
from .task_executor import Task, TaskExecutor

logger = logging.getLogger(__name__)


# ============================================================================
# Backend Service Implementation
# ============================================================================

class CovinaBackendService:
    """
    Zentrale Business-Logic-Schicht für Covina Frontend
    
    Trennt Business-Logic von UI-Code. Kommuniziert via EventBus.
    
    Features:
    - Health Check Loop (Backend Status)
    - Job Management (List, Details, Create)
    - Upload Management
    - Recovery Management (NEW v3.4.8)
    - Event-driven Architecture
    
    Example:
        >>> event_bus = EventBus()
        >>> task_executor = TaskExecutor(max_workers=5)
        >>> 
        >>> service = CovinaBackendService(
        >>>     base_url="http://127.0.0.1:45678",
        >>>     ingestion_base_url="http://127.0.0.1:45679",
        >>>     event_bus=event_bus,
        >>>     task_executor=task_executor
        >>> )
        >>> 
        >>> service.start()
        >>> # Subscribe to events...
        >>> service.stop()
    """
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:45678",
        ingestion_base_url: str = "http://127.0.0.1:45679",
        event_bus: Optional[EventBus] = None,
        task_executor: Optional[TaskExecutor] = None
    ):
        self.base_url = base_url
        self.ingestion_base_url = ingestion_base_url
        self.event_bus = event_bus or EventBus()
        self.task_executor = task_executor or TaskExecutor(max_workers=5)
        
        # HTTP Session
        self.session = requests.Session()
        self.session.timeout = 30
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # State
        self.backend_online = False
        self.ingestion_online = False
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_running = False
        
        # Job Cache
        self._job_cache: Dict[str, Dict] = {}
        self._job_cache_lock = threading.RLock()
        
        # Job Refresh Loop
        self._job_refresh_running = False
        self._job_refresh_thread = None
        self._job_refresh_interval = 10  # Sekunden
    
    # ========================================================================
    # Lifecycle
    # ========================================================================
    
    def start(self):
        """Startet Service"""
        self.event_bus.start()
        self.task_executor.start()
        self._start_health_check()
        self._start_job_refresh()
        logger.info("CovinaBackendService gestartet")
    
    def stop(self):
        """Stoppt Service"""
        self._stop_health_check()
        self._stop_job_refresh()
        self.task_executor.stop()
        self.event_bus.stop()
        self.session.close()
        logger.info("CovinaBackendService gestoppt")
    
    # ========================================================================
    # HTTP Helper
    # ========================================================================
    
    def _make_request(
        self,
        method: str,
        url: str,
        timeout: int = 30,
        **kwargs
    ) -> requests.Response:
        """
        HTTP-Request-Wrapper mit Error Handling
        
        Args:
            method: HTTP-Methode (GET, POST, etc.)
            url: URL
            timeout: Timeout in Sekunden
            **kwargs: Zusätzliche Request-Parameter
            
        Returns:
            Response-Objekt
            
        Raises:
            Exception: Bei Fehler
        """
        response = self.session.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    def _start_health_check(self):
        """Startet periodischen Health-Check"""
        self._health_check_running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="BackendHealthCheck"
        )
        self._health_check_thread.start()
    
    def _stop_health_check(self):
        """Stoppt Health-Check"""
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2.0)
    
    def _health_check_loop(self):
        """Health-Check-Loop (alle 10s)"""
        while self._health_check_running:
            try:
                # Main Backend
                main_response = self._make_request(
                    "GET",
                    f"{self.base_url}/health",
                    timeout=5
                )
                main_online = main_response.status_code == 200
                
                # Ingestion Backend
                ingestion_response = self._make_request(
                    "GET",
                    f"{self.ingestion_base_url}/health",
                    timeout=5
                )
                ingestion_online = ingestion_response.status_code == 200
                
                # State-Änderungen emittieren
                if main_online and not self.backend_online:
                    self.backend_online = True
                    self.event_bus.emit(
                        EventType.BACKEND_CONNECTED,
                        {"url": self.base_url, "type": "main"},
                        source="HealthCheck"
                    )
                    logger.info("Main Backend verbunden")
                
                if ingestion_online and not self.ingestion_online:
                    self.ingestion_online = True
                    self.event_bus.emit(
                        EventType.BACKEND_CONNECTED,
                        {"url": self.ingestion_base_url, "type": "ingestion"},
                        source="HealthCheck"
                    )
                    logger.info("Ingestion Backend verbunden")
                
                if not main_online and self.backend_online:
                    self.backend_online = False
                    self.event_bus.emit(
                        EventType.BACKEND_DISCONNECTED,
                        {"url": self.base_url, "type": "main"},
                        source="HealthCheck"
                    )
                    logger.warning("Main Backend nicht erreichbar")
                
                if not ingestion_online and self.ingestion_online:
                    self.ingestion_online = False
                    self.event_bus.emit(
                        EventType.BACKEND_DISCONNECTED,
                        {"url": self.ingestion_base_url, "type": "ingestion"},
                        source="HealthCheck"
                    )
                    logger.warning("Ingestion Backend nicht erreichbar")
                
            except Exception as e:
                if self.backend_online or self.ingestion_online:
                    self.backend_online = False
                    self.ingestion_online = False
                    self.event_bus.emit(
                        EventType.BACKEND_ERROR,
                        {"error": str(e)},
                        source="HealthCheck"
                    )
                    logger.warning(f"Backend Health Check fehlgeschlagen: {e}")
            
            time.sleep(10)
    
    # ========================================================================
    # Job Refresh Loop
    # ========================================================================
    
    def _start_job_refresh(self):
        """Startet periodischen Job-Refresh"""
        self._job_refresh_running = True
        self._job_refresh_thread = threading.Thread(
            target=self._job_refresh_loop,
            daemon=True,
            name="JobRefreshLoop"
        )
        self._job_refresh_thread.start()
    
    def _stop_job_refresh(self):
        """Stoppt Job-Refresh"""
        self._job_refresh_running = False
        if self._job_refresh_thread:
            self._job_refresh_thread.join(timeout=2.0)
    
    def _job_refresh_loop(self):
        """Job-Refresh-Loop (alle 10s)"""
        while self._job_refresh_running:
            try:
                if self.ingestion_online:
                    self.list_jobs(limit=100)
            except Exception as e:
                logger.debug(f"Job-Refresh-Fehler: {e}")
            
            time.sleep(self._job_refresh_interval)
    
    # ========================================================================
    # Job Management API
    # ========================================================================
    
    def list_jobs(self, limit: int = 100):
        """
        Liste alle Jobs (asynchron)
        
        Emits: JOB_STATUS_CHANGED mit allen Jobs
        """
        task = Task(
            task_id=f"list_jobs_{datetime.now().timestamp()}",
            func=self._list_jobs_sync,
            args=(limit,),
            callback=lambda jobs: self.event_bus.emit(
                EventType.JOB_STATUS_CHANGED,
                {"jobs": jobs},
                source="JobService"
            ) if jobs else None,  # Nur emittieren wenn Änderungen
            error_callback=lambda e: self.event_bus.emit(
                EventType.BACKEND_ERROR,
                {"error": str(e), "operation": "list_jobs"},
                source="JobService"
            ),
            priority=7
        )
        self.task_executor.submit(task)
    
    def _list_jobs_sync(self, limit: int) -> List[Dict]:
        """Synchrone Job-List-Implementierung mit Smart Caching"""
        response = self._make_request(
            "GET",
            f"{self.ingestion_base_url}/jobs",
            params={"limit": limit}
        )
        jobs = response.json()
        
        # Smart Polling: Prüfe ob sich Jobs geändert haben
        jobs_changed = False
        
        with self._job_cache_lock:
            # Vergleiche mit Cache
            if len(jobs) != len(self._job_cache):
                jobs_changed = True
            else:
                for job in jobs:
                    job_id = job['job_id']
                    cached_job = self._job_cache.get(job_id)
                    
                    # Neue Job oder Status-Änderung?
                    if not cached_job or cached_job.get('status') != job.get('status'):
                        jobs_changed = True
                        break
                    
                    # Progress-Änderung?
                    if cached_job.get('progress') != job.get('progress'):
                        jobs_changed = True
                        break
            
            # Update Cache nur bei Änderungen
            if jobs_changed:
                for job in jobs:
                    self._job_cache[job['job_id']] = job
                logger.debug(f"Jobs geändert - Cache aktualisiert ({len(jobs)} Jobs)")
            else:
                logger.debug("Keine Job-Änderungen - Cache unverändert")
        
        # Nur bei Änderungen zurückgeben
        return jobs if jobs_changed else []
    
    def get_job_details(self, job_id: str):
        """
        Holt detaillierte Job-Informationen (asynchron)
        
        Emits: JOB_PROGRESS_UPDATE mit Job-Details
        """
        task = Task(
            task_id=f"get_job_details_{job_id}",
            func=self._get_job_details_sync,
            args=(job_id,),
            callback=lambda details: self.event_bus.emit(
                EventType.JOB_PROGRESS_UPDATE,
                {"job_id": job_id, "details": details},
                source="JobService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.BACKEND_ERROR,
                {"error": str(e), "operation": "get_job_details", "job_id": job_id},
                source="JobService"
            ),
            priority=7
        )
        self.task_executor.submit(task)
    
    def _get_job_details_sync(self, job_id: str) -> Dict:
        """Synchrone Job-Details-Implementierung"""
        response = self._make_request(
            "GET",
            f"{self.ingestion_base_url}/jobs/{job_id}/status"
        )
        return response.json()
    
    # ========================================================================
    # Recovery API (NEW v3.4.8)
    # ========================================================================
    
    def get_failed_files(self, job_id: str, max_retries: int = 3):
        """
        Holt fehlgeschlagene Dateien (asynchron)
        
        Emits: RECOVERY_STARTED mit failed files data
        """
        task = Task(
            task_id=f"get_failed_files_{job_id}",
            func=self._get_failed_files_sync,
            args=(job_id, max_retries),
            callback=lambda data: self.event_bus.emit(
                EventType.RECOVERY_STARTED,
                {"job_id": job_id, "failed_files": data},
                source="RecoveryService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.BACKEND_ERROR,
                {"error": str(e), "operation": "get_failed_files", "job_id": job_id},
                source="RecoveryService"
            ),
            priority=8
        )
        self.task_executor.submit(task)
    
    def _get_failed_files_sync(self, job_id: str, max_retries: int) -> Dict:
        """Synchrone Failed-Files-Implementierung"""
        response = self._make_request(
            "GET",
            f"{self.ingestion_base_url}/jobs/{job_id}/failed-files",
            params={"max_retries": max_retries}
        )
        return response.json()
    
    def recover_failed_files(self, job_id: str, max_retries: int = 3, force_retry: bool = False):
        """
        Startet Recovery für fehlgeschlagene Dateien (asynchron)
        
        Emits: RECOVERY_COMPLETE oder RECOVERY_FAILED
        """
        task = Task(
            task_id=f"recover_failed_{job_id}",
            func=self._recover_failed_files_sync,
            args=(job_id, max_retries, force_retry),
            callback=lambda data: self.event_bus.emit(
                EventType.RECOVERY_COMPLETE,
                {"job_id": job_id, "recovery_data": data},
                source="RecoveryService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.RECOVERY_FAILED,
                {"error": str(e), "job_id": job_id},
                source="RecoveryService"
            ),
            priority=9
        )
        self.task_executor.submit(task)
    
    def _recover_failed_files_sync(self, job_id: str, max_retries: int, force_retry: bool) -> Dict:
        """Synchrone Recovery-Implementierung"""
        response = self._make_request(
            "POST",
            f"{self.ingestion_base_url}/jobs/{job_id}/recover-failed-files",
            params={"max_retries": max_retries, "force_retry": force_retry}
        )
        return response.json()
    
    def unblock_file(self, job_id: str, file_path: str, admin_override: bool = True):
        """
        Unblock File (Admin Override)
        
        Emits: RECOVERY_FILE_UNBLOCKED
        """
        task = Task(
            task_id=f"unblock_file_{job_id}_{file_path}",
            func=self._unblock_file_sync,
            args=(job_id, file_path, admin_override),
            callback=lambda data: self.event_bus.emit(
                EventType.RECOVERY_FILE_UNBLOCKED,
                {"job_id": job_id, "file_path": file_path, "data": data},
                source="RecoveryService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.BACKEND_ERROR,
                {"error": str(e), "operation": "unblock_file", "job_id": job_id, "file_path": file_path},
                source="RecoveryService"
            ),
            priority=9
        )
        self.task_executor.submit(task)
    
    def _unblock_file_sync(self, job_id: str, file_path: str, admin_override: bool) -> Dict:
        """Synchrone Unblock-Implementierung"""
        response = self._make_request(
            "POST",
            f"{self.ingestion_base_url}/jobs/{job_id}/files/{file_path}/unblock",
            params={"admin_override": admin_override}
        )
        return response.json()
    
    def get_all_blocked_files(self):
        """
        System-Wide Audit: Alle blockierten Dateien
        
        Emits: RECOVERY_STARTED mit blocked files
        """
        task = Task(
            task_id=f"get_blocked_files_{datetime.now().timestamp()}",
            func=self._get_all_blocked_files_sync,
            callback=lambda data: self.event_bus.emit(
                EventType.RECOVERY_STARTED,
                {"blocked_files": data},
                source="RecoveryService"
            ),
            error_callback=lambda e: self.event_bus.emit(
                EventType.BACKEND_ERROR,
                {"error": str(e), "operation": "get_all_blocked_files"},
                source="RecoveryService"
            ),
            priority=7
        )
        self.task_executor.submit(task)
    
    def _get_all_blocked_files_sync(self) -> Dict:
        """Synchrone Blocked-Files-Implementierung"""
        response = self._make_request(
            "GET",
            f"{self.ingestion_base_url}/recovery/blocked-files"
        )
        return response.json()
