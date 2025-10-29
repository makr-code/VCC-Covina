"""
Hybrid Upload Manager - Automatic method selection

Author: Covina Development Team
Created: 15. Oktober 2025
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict
import requests

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_URL = "http://127.0.0.1:45679"
DEFAULT_WS_URL = "ws://127.0.0.1:45679/ws/upload"
FAST_NETWORK_THRESHOLD = 50 * 1024 * 1024  # 50 Mbps
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB

class NetworkSpeedTester:
    """Test network speed"""
    def __init__(self, upload_url: str = DEFAULT_UPLOAD_URL):
        self.upload_url = upload_url
    
    def test_speed(self) -> float:
        """Test speed (bytes/sec)"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.upload_url}/health", timeout=5)
            duration = time.time() - start_time
            if response.status_code == 200 and duration > 0:
                speed = 1024 * 1024 / duration  # Rough estimate
                return speed
            return 0.0
        except:
            return 0.0

class HybridUploadManager:
    """Hybrid Upload Manager"""
    def __init__(self, upload_url: str = DEFAULT_UPLOAD_URL, ws_url: str = DEFAULT_WS_URL):
        self.upload_url = upload_url
        self.ws_url = ws_url
        self.speed_tester = NetworkSpeedTester(upload_url)
    
    def select_method(self, file_path: str, force_method: Optional[str] = None) -> str:
        """Select upload method"""
        if force_method:
            return force_method
        
        file_size = Path(file_path).stat().st_size
        network_speed = self.speed_tester.test_speed()
        
        # Decision logic
        if network_speed > FAST_NETWORK_THRESHOLD:
            if file_size > LARGE_FILE_THRESHOLD:
                return "websocket"  # Fast network + large file = WebSocket
            else:
                return "websocket"  # Fast network + small file = WebSocket
        else:
            return "chunked_http"  # Slow network = Chunked HTTP (resume capability)
    
    def upload_file(self, file_path: str, method: Optional[str] = None) -> Dict:
        """Upload file with selected method"""
        selected_method = self.select_method(file_path, method)
        
        logger.info(f"Selected method: {selected_method}")
        
        if selected_method == "websocket":
            result = self._upload_websocket(file_path)
        elif selected_method == "chunked_http":
            result = self._upload_chunked(file_path)
        else:
            raise ValueError(f"Unknown method: {selected_method}")
        
        # Log result
        if result.get('stdout'):
            logger.info(f"Output:\n{result['stdout']}")
        if result.get('stderr'):
            logger.error(f"Errors:\n{result['stderr']}")
        
        return result
    
    def _upload_websocket(self, file_path: str) -> Dict:
        """Upload via WebSocket"""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "scripts/client_websocket_upload.py", file_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    def _upload_chunked(self, file_path: str) -> Dict:
        """Upload via Chunked HTTP"""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "scripts/client_chunked_upload.py", file_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr
        }

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(description="Hybrid Upload Manager")
    parser.add_argument("file", help="File to upload")
    parser.add_argument("--method", choices=["websocket", "chunked_http"], help="Force method")
    args = parser.parse_args()
    manager = HybridUploadManager()
    result = manager.upload_file(args.file, args.method)
    print(f"Upload: {result['status']}")
