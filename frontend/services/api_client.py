"""
Covina Backend API Client
==========================

REST Client für alle Covina Backend-Endpoints mit Error Handling
"""

import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from frontend.config import BACKEND_URL, ENDPOINTS, INGESTION_BACKEND_URL, INGESTION_ENDPOINTS

# Configure logging - ✅ WARNING level for cleaner output
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class APIClient:
    """REST Client für Covina Backend API"""
    
    def __init__(self, base_url: str = BACKEND_URL, timeout: int = 30):  # ✅ Increased timeout for heavy database queries (e.g. /database/stats)
        self.base_url = base_url
        self.timeout = timeout
        # ❌ REMOVED: self.session for thread-safety
        # requests.Session() is NOT thread-safe, use direct requests instead
    
    def _make_request(self, endpoint: str, method: str = 'GET', **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with error handling
        
        Args:
            endpoint: API endpoint (e.g., '/health')
            method: HTTP method ('GET', 'POST', etc.)
            **kwargs: Additional request parameters
        
        Returns:
            Response JSON as dict, or None on error
        """
        url = f"{self.base_url}{endpoint}"
        
        # ✅ Thread-safe: Use direct requests instead of session
        headers = kwargs.pop('headers', {})
        headers['User-Agent'] = 'Covina-LiveView/1.0'
        
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout: {url}")
            return {"error": "timeout", "message": f"Request to {endpoint} timed out"}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection Error: {url}")
            return {"error": "connection", "message": f"Cannot connect to backend at {self.base_url}"}
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {e.response.status_code}: {url}")
            return {"error": "http", "status_code": e.response.status_code, "message": str(e)}
        
        except Exception as e:
            logger.error(f"Unexpected error: {url}: {e}")
            return {"error": "unknown", "message": str(e)}
    
    # ========================================================================
    # HEALTH & STATUS
    # ========================================================================
    
    def is_backend_available(self) -> bool:
        """
        Quick backend availability check.
        
        Returns:
            True if backend is reachable, False otherwise
        """
        try:
            logger.debug(f"🔍 Checking backend availability: {self.base_url}{ENDPOINTS['health']}")
            response = requests.get(  # ✅ Direct request (thread-safe)
                f"{self.base_url}{ENDPOINTS['health']}",
                timeout=1.0,  # Fast timeout for availability check
                headers={'User-Agent': 'Covina-LiveView/1.0'}
            )
            available = response.status_code == 200
            logger.debug(f"✅ Backend check result: {available} (status={response.status_code})")
            return available
        except Exception as e:
            logger.debug(f"❌ Backend check failed: {type(e).__name__}: {e}")
            return False
    
    def get_health(self) -> Optional[Dict[str, Any]]:
        """Get backend health status"""
        return self._make_request(ENDPOINTS["health"])
    
    def get_uds3_status(self) -> Optional[Dict[str, Any]]:
        """Get UDS3 framework status"""
        return self._make_request(ENDPOINTS["uds3_status"])
    
    def get_uds3_strategy_status(self) -> Optional[Dict[str, Any]]:
        """Get UDS3 unified database strategy status"""
        return self._make_request(ENDPOINTS["uds3_strategy"])
    
    # ========================================================================
    # DATABASE STATS
    # ========================================================================
    
    def get_database_stats(self) -> Optional[Dict[str, Any]]:
        """Get PostgreSQL database statistics"""
        return self._make_request(ENDPOINTS["database_stats"])
    
    def get_vector_monitoring(self) -> Optional[Dict[str, Any]]:
        """Get ChromaDB vector database monitoring"""
        return self._make_request(ENDPOINTS["vector_monitoring"])
    
    # ========================================================================
    # SAGA & TRANSACTIONS
    # ========================================================================
    
    def get_saga_status(self) -> Optional[Dict[str, Any]]:
        """Get SAGA transaction status"""
        endpoint = ENDPOINTS.get("saga_status", "/admin/saga/status")
        return self._make_request(endpoint)
    
    # ========================================================================
    # SECURITY & AUDIT
    # ========================================================================
    
    def get_security_audit(self, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get security audit logs"""
        endpoint = ENDPOINTS.get("security_audit", "/admin/security/audit")
        return self._make_request(f"{endpoint}?limit={limit}")
    
    # ========================================================================
    # ERROR TRACKING
    # ========================================================================
    
    def get_recent_errors(self, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get recent errors"""
        endpoint = ENDPOINTS.get("errors_recent", "/errors/recent")
        return self._make_request(f"{endpoint}?limit={limit}")
    
    # ========================================================================
    # INGESTION
    # ========================================================================
    
    def get_ingestion_status(self) -> Optional[Dict[str, Any]]:
        """Get ingestion pipeline status"""
        endpoint = ENDPOINTS.get("ingestion_status", "/admin/ingestion/status")
        return self._make_request(endpoint)
    
    # ========================================================================
    # GOLDEN DATASET
    # ========================================================================
    
    def get_golden_dataset_status(self) -> Optional[Dict[str, Any]]:
        """Get golden dataset and gap detection status"""
        endpoint = ENDPOINTS.get("golden_dataset", "/admin/golden-dataset/status")
        return self._make_request(endpoint)
    
    # ========================================================================
    # CONNECTION TEST
    # ========================================================================
    
    def test_connection(self) -> bool:
        """
        Test if backend is reachable
        
        Returns:
            True if backend is reachable and healthy, False otherwise
        """
        result = self.get_health()
        
        if result and "error" not in result:
            return result.get("status") == "healthy"
        
        return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status
        
        Returns:
            Dict with connection status, latency, and timestamp
        """
        start_time = datetime.now()
        result = self.get_health()
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        if result and "error" not in result:
            return {
                "connected": True,
                "status": result.get("status"),
                "latency_ms": round(latency_ms, 2),
                "active_jobs": result.get("active_jobs", 0),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "connected": False,
                "error": result.get("error") if result else "unknown",
                "message": result.get("message") if result else "No response",
                "timestamp": datetime.now().isoformat()
            }


# ========================================================================
# INGESTION BACKEND CLIENT
# ========================================================================

class IngestionAPIClient:
    """REST Client für Covina Ingestion Backend (Port 45679)"""
    
    def __init__(self, base_url: str = INGESTION_BACKEND_URL, timeout: int = 30):
        """
        Initialize Ingestion API Client
        
        Args:
            base_url: Base URL of Ingestion Backend (default: http://127.0.0.1:45679)
            timeout: Request timeout in seconds (default: 30s for file uploads)
        """
        self.base_url = base_url
        self.timeout = timeout
    
    def _make_request(self, endpoint: str, method: str = 'GET', **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with error handling
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            **kwargs: Additional request parameters
        
        Returns:
            Response JSON or None on error
        """
        url = f"{self.base_url}{endpoint}"
        
        headers = kwargs.pop('headers', {})
        headers['User-Agent'] = 'Covina-Frontend/1.0'
        
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.error(f"Ingestion Backend Timeout: {url}")
            return {"error": "timeout", "message": f"Request to {endpoint} timed out"}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Ingestion Backend Connection Error: {url}")
            return {"error": "connection", "message": f"Cannot connect to Ingestion Backend at {self.base_url}"}
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ingestion Backend HTTP Error {e.response.status_code}: {url}")
            return {"error": "http", "status_code": e.response.status_code, "message": str(e)}
        
        except Exception as e:
            logger.error(f"Ingestion Backend Unexpected error: {url}: {e}")
            return {"error": "unknown", "message": str(e)}
    
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    
    def get_health(self) -> Optional[Dict[str, Any]]:
        """Get Ingestion Backend health status"""
        return self._make_request(INGESTION_ENDPOINTS["health"])
    
    def is_available(self) -> bool:
        """
        Quick availability check
        
        Returns:
            True if Ingestion Backend is reachable
        """
        try:
            response = requests.get(
                f"{self.base_url}{INGESTION_ENDPOINTS['health']}",
                timeout=2.0,
                headers={'User-Agent': 'Covina-Frontend/1.0'}
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ingestion Backend unavailable: {e}")
            return False
    
    # ========================================================================
    # FILE UPLOAD
    # ========================================================================
    
    def upload_files(self, file_paths: List[str]) -> Optional[Dict[str, Any]]:
        """
        Upload multiple files
        
        Args:
            file_paths: List of file paths to upload
        
        Returns:
            Upload response with job_id
        """
        files = []
        try:
            for file_path in file_paths:
                path = Path(file_path)
                if path.exists():
                    files.append((
                        'files',
                        (path.name, open(file_path, 'rb'), 'application/octet-stream')
                    ))
            
            if not files:
                return {"error": "no_files", "message": "No valid files to upload"}
            
            result = self._make_request(
                INGESTION_ENDPOINTS["upload_files"],
                method='POST',
                files=files
            )
            
            return result
        
        except Exception as e:
            logger.error(f"File upload error: {e}")
            return {"error": "upload_failed", "message": str(e)}
        
        finally:
            # Close file handles
            for _, file_tuple in files:
                if hasattr(file_tuple[1], 'close'):
                    file_tuple[1].close()
    
    # ========================================================================
    # DIRECTORY UPLOAD
    # ========================================================================
    
    def upload_directory(
        self,
        directory_path: str,
        chunk_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        Upload all files from a directory (async with instant response)
        
        ВАЖНО: This now returns immediately with scan_job_id!
        - Old behavior: Waited for scan to complete (timeout!)
        - New behavior: Instant response, scan runs in background
        
        Args:
            directory_path: Path to directory
            chunk_size: Number of files per chunk (default: 50)
        
        Returns:
            {
                "scan_job_id": "scan_abc123",
                "status": "scanning",
                "directory_path": "/path/to/dir",
                "message": "Directory scan started in background"
            }
        
        Usage:
            # Start scan (instant!)
            result = client.upload_directory("/path/to/dir")
            scan_job_id = result["scan_job_id"]
            
            # Poll status or listen to WebSocket
            status = client.get_scan_status(scan_job_id)
        """
        data = {
            'directory_path': directory_path,
            'chunk_size': chunk_size
        }
        
        # ✅ Use custom short timeout (response is instant now!)
        try:
            url = f"{self.base_url}{INGESTION_ENDPOINTS['upload_directory']}"
            headers = {'User-Agent': 'Covina-Frontend/1.0'}
            
            response = requests.post(
                url,
                data=data,
                headers=headers,
                timeout=5.0  # 5s timeout (instant response expected!)
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.error(f"Directory upload timeout: {url}")
            return {"error": "timeout", "message": "Request timed out (should be instant!)"}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error: {url}")
            return {"error": "connection", "message": "Cannot connect to Ingestion Backend"}
        
        except Exception as e:
            logger.error(f"Directory upload error: {e}")
            return {"error": "upload_failed", "message": str(e)}
    
    def get_scan_status(self, scan_job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get directory scan status
        
        Args:
            scan_job_id: Scan job ID from upload_directory()
        
        Returns:
            {
                "scan_job_id": "scan_abc123",
                "status": "scanning" | "creating_jobs" | "completed" | "error",
                "files_found": 1234,
                "upload_jobs_created": 25,
                "upload_job_ids": ["job_1", "job_2", ...],
                "error": null | "error message",
                "elapsed_time": 45.2
            }
        """
        return self._make_request(f"/scan/{scan_job_id}")

    
    # ========================================================================
    # JOB MANAGEMENT
    # ========================================================================
    
    def list_jobs(self, limit: int = 50) -> Optional[Dict[str, Any]]:
        """
        List recent jobs
        
        Args:
            limit: Maximum number of jobs to return
        
        Returns:
            List of jobs with status
        """
        return self._make_request(f"{INGESTION_ENDPOINTS['jobs_list']}?limit={limit}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific job
        
        Args:
            job_id: Job ID
        
        Returns:
            Job status
        """
        endpoint = INGESTION_ENDPOINTS["job_status"].format(job_id=job_id)
        return self._make_request(endpoint)
    
    def get_job_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics of a completed job
        
        Args:
            job_id: Job ID
        
        Returns:
            Job metrics (processing time, success rate, etc.)
        """
        endpoint = INGESTION_ENDPOINTS["job_metrics"].format(job_id=job_id)
        return self._make_request(endpoint)


# Global Ingestion API client instance
ingestion_api_client = IngestionAPIClient()


# Global API client instance
api_client = APIClient()


# Convenience functions
def get_health():
    return api_client.get_health()

def get_database_stats():
    return api_client.get_database_stats()

def get_uds3_strategy_status():
    return api_client.get_uds3_strategy_status()

def test_connection():
    return api_client.test_connection()
