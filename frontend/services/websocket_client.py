"""
WebSocket Client für Real-Time Job Updates
==========================================

Verbindet sich mit Ingestion Backend WebSocket-Endpoint und empfängt
Real-Time Updates für Job Status-Änderungen.

Features:
- Auto-Reconnect bei Verbindungsabbruch
- Message Handler Callbacks
- Connection State Tracking
- Thread-Safe Design
- Graceful Degradation (Fallback zu Polling)

Author: Covina System
Date: 11. Oktober 2025
"""

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

import websocket

# Logging Setup - ✅ WARNING level for cleaner output
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("websocket_client")


class IngestionWebSocketClient:
    """
    WebSocket Client für Ingestion Backend Job Updates
    
    Usage:
        client = IngestionWebSocketClient("ws://127.0.0.1:45679/ws/jobs")
        client.on_message = lambda msg: print(f"Update: {msg}")
        client.connect()
    """
    
    def __init__(
        self, 
        url: str = "ws://127.0.0.1:45679/ws/jobs",
        auto_reconnect: bool = True,
        reconnect_delay: int = 5
    ):
        """
        Initialize WebSocket Client
        
        Args:
            url: WebSocket endpoint URL
            auto_reconnect: Automatisch neu verbinden bei Disconnect
            reconnect_delay: Wartezeit zwischen Reconnect-Versuchen (Sekunden)
        """
        self.url = url
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        
        # WebSocket Connection
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        
        # Connection State
        self.is_connected = False
        self.is_connecting = False
        self.should_run = True
        
        # Callbacks
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # Thread Lock
        self._lock = threading.Lock()
    
    def connect(self):
        """Stelle WebSocket-Verbindung her"""
        if self.is_connected or self.is_connecting:
            logger.warning("⚠️ Already connected or connecting")
            return
        
        self.is_connecting = True
        self.should_run = True
        
        # Create WebSocket App
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Start WebSocket in separate thread
        self.ws_thread = threading.Thread(
            target=self._run_websocket,
            daemon=True,
            name="websocket_client"
        )
        self.ws_thread.start()
        
        logger.info(f"🔌 Connecting to {self.url}...")
    
    def disconnect(self):
        """Schließe WebSocket-Verbindung"""
        self.should_run = False
        
        if self.ws:
            self.ws.close()
        
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2)
        
        self.is_connected = False
        self.is_connecting = False
        
        logger.info("❌ WebSocket disconnected")
    
    def send_message(self, message: Dict[str, Any]):
        """Sende Nachricht an Server"""
        if not self.is_connected:
            logger.warning("⚠️ Cannot send message - not connected")
            return
        
        try:
            self.ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
    
    def send_ping(self):
        """Sende Ping zur Connection-Health-Überprüfung"""
        if self.is_connected:
            try:
                self.ws.send("ping")
            except Exception as e:
                logger.error(f"❌ Failed to send ping: {e}")
    
    # ================================================================
    # PRIVATE METHODS
    # ================================================================
    
    def _run_websocket(self):
        """WebSocket Run Loop (in separatem Thread)"""
        while self.should_run:
            try:
                self.ws.run_forever()
                
                # Connection closed
                if not self.should_run:
                    break
                
                # Auto-Reconnect
                if self.auto_reconnect:
                    logger.info(f"🔄 Reconnecting in {self.reconnect_delay}s...")
                    time.sleep(self.reconnect_delay)
                    
                    if self.should_run:
                        logger.info(f"🔌 Reconnecting to {self.url}...")
                else:
                    break
                    
            except Exception as e:
                logger.error(f"❌ WebSocket run error: {e}")
                
                if self.auto_reconnect and self.should_run:
                    time.sleep(self.reconnect_delay)
                else:
                    break
    
    def _on_open(self, ws):
        """WebSocket Connection Opened"""
        with self._lock:
            self.is_connected = True
            self.is_connecting = False
        
        logger.info("[OK] WebSocket connected")
        
        if self.on_connected:
            try:
                self.on_connected()
            except Exception as e:
                logger.error(f"[ERROR] on_connected callback error: {e}")
    
    def _on_message(self, ws, message):
        """WebSocket Message Received"""
        try:
            # Parse JSON message
            data = json.loads(message)
            
            # Log message type
            msg_type = data.get("type", "unknown")
            logger.debug(f"[MSG] Received: {msg_type}")
            
            # Call user callback
            if self.on_message:
                try:
                    self.on_message(data)
                except Exception as e:
                    logger.error(f"[ERROR] on_message callback error: {e}")
                    
        except json.JSONDecodeError:
            logger.warning(f"[WARNING] Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"[ERROR] Message handling error: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket Error Occurred"""
        logger.error(f"[ERROR] WebSocket error: {error}")
        
        if self.on_error:
            try:
                self.on_error(error)
            except Exception as e:
                logger.error(f"❌ on_error callback error: {e}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket Connection Closed"""
        with self._lock:
            self.is_connected = False
            self.is_connecting = False
        
        logger.info(f"❌ WebSocket closed: {close_status_code} - {close_msg}")
        
        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception as e:
                logger.error(f"❌ on_disconnected callback error: {e}")
    
    # ================================================================
    # PROPERTIES
    # ================================================================
    
    @property
    def connection_state(self) -> str:
        """Get current connection state"""
        if self.is_connected:
            return "connected"
        elif self.is_connecting:
            return "connecting"
        else:
            return "disconnected"


# ================================================================
# CONVENIENCE FUNCTIONS
# ================================================================

def create_job_monitor_client(
    on_job_update: Callable[[Dict[str, Any]], None],
    on_connected: Optional[Callable[[], None]] = None,
    on_disconnected: Optional[Callable[[], None]] = None
) -> IngestionWebSocketClient:
    """
    Erstelle WebSocket Client für Job Monitoring
    
    Args:
        on_job_update: Callback für Job-Updates
        on_connected: Optional callback bei Verbindung
        on_disconnected: Optional callback bei Trennung
    
    Returns:
        Configured IngestionWebSocketClient
    
    Example:
        def handle_update(data):
            if data.get("type") == "job_update":
                print(f"Job {data['job_id']}: {data['status']}")
        
        client = create_job_monitor_client(handle_update)
        client.connect()
    """
    client = IngestionWebSocketClient()
    
    client.on_message = on_job_update
    
    if on_connected:
        client.on_connected = on_connected
    
    if on_disconnected:
        client.on_disconnected = on_disconnected
    
    return client


# ================================================================
# TESTING
# ================================================================

if __name__ == "__main__":
    """Test WebSocket Client"""
    
    def handle_message(data):
        print(f"📨 Message: {data}")
    
    def handle_connected():
        print("✅ Connected!")
    
    def handle_disconnected():
        print("❌ Disconnected!")
    
    # Create client
    client = create_job_monitor_client(
        on_job_update=handle_message,
        on_connected=handle_connected,
        on_disconnected=handle_disconnected
    )
    
    # Connect
    client.connect()
    
    # Keep alive
    try:
        while True:
            time.sleep(10)
            client.send_ping()  # Ping every 10s
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        client.disconnect()
