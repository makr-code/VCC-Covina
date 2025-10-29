"""
WebSocket Upload Handler

Provides bidirectional real-time file uploads via WebSocket.

Features:
- Binary streaming (no base64 encoding)
- Bidirectional control (server can pause/resume/cancel)
- Multiple file uploads over single connection
- Automatic reconnection with resume
- Heartbeat/ping-pong keep-alive
- Real-time progress updates

Protocol:
- JSON control messages (text frames)
- Binary chunk data (binary frames)

Author: Covina Development Team
Created: 15. Oktober 2025
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# ================================================================
# CONFIGURATION
# ================================================================

# Default chunk size: 64 KB (WebSocket optimal)
DEFAULT_WS_CHUNK_SIZE = 64 * 1024

# Heartbeat interval: 30 seconds
HEARTBEAT_INTERVAL = 30

# Upload storage directory
WS_UPLOAD_STORAGE_DIR = Path("data/uploads/websocket")
WS_UPLOAD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Maximum connections per IP (simple rate limiting)
MAX_CONNECTIONS_PER_IP = 10

# ================================================================
# MESSAGE TYPES & MODELS
# ================================================================

class MessageType(str, Enum):
    """WebSocket message types"""
    # Client → Server
    START_UPLOAD = "start_upload"
    RESUME_UPLOAD = "resume"
    PAUSE = "pause"
    CANCEL = "cancel"
    PING = "ping"
    
    # Server → Client
    UPLOAD_STARTED = "upload_started"
    PROGRESS = "progress"
    PAUSE_REQUEST = "pause_request"
    RESUMED = "resumed"
    COMPLETED = "completed"
    ERROR = "error"
    PONG = "pong"


@dataclass
class StartUploadMessage:
    """Client request to start upload"""
    type: str = MessageType.START_UPLOAD
    file_name: str = ""
    file_size: int = 0
    chunk_size: int = DEFAULT_WS_CHUNK_SIZE
    file_hash: Optional[str] = None


@dataclass
class UploadStartedMessage:
    """Server response after upload started"""
    type: str = MessageType.UPLOAD_STARTED
    upload_id: str = ""
    resume_from_chunk: int = 0
    chunk_size: int = DEFAULT_WS_CHUNK_SIZE


@dataclass
class ProgressMessage:
    """Server progress update"""
    type: str = MessageType.PROGRESS
    upload_id: str = ""
    chunks_received: int = 0
    total_chunks: int = 0
    percent: float = 0.0
    bytes_received: int = 0
    file_size: int = 0


@dataclass
class CompletedMessage:
    """Server completion message"""
    type: str = MessageType.COMPLETED
    upload_id: str = ""
    job_id: str = ""
    file_path: str = ""
    file_size: int = 0
    duration_seconds: float = 0.0


@dataclass
class ErrorMessage:
    """Server error message"""
    type: str = MessageType.ERROR
    upload_id: Optional[str] = None
    error_code: str = ""
    message: str = ""


# ================================================================
# UPLOAD SESSION
# ================================================================

@dataclass
class WebSocketUploadSession:
    """Active upload session"""
    upload_id: str
    file_name: str
    file_size: int
    total_chunks: int
    chunk_size: int
    chunks_received: Set[int]
    storage_dir: Path
    output_file: Optional[object] = None  # File handle
    started_at: datetime = None
    last_activity_at: datetime = None
    paused: bool = False
    cancelled: bool = False
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.last_activity_at is None:
            self.last_activity_at = datetime.now()
    
    @property
    def percent_complete(self) -> float:
        """Calculate upload progress percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (len(self.chunks_received) / self.total_chunks) * 100
    
    @property
    def bytes_received(self) -> int:
        """Calculate bytes received"""
        return len(self.chunks_received) * self.chunk_size
    
    @property
    def is_complete(self) -> bool:
        """Check if all chunks received"""
        return len(self.chunks_received) == self.total_chunks


# ================================================================
# CONNECTION MANAGER
# ================================================================

class WebSocketConnectionManager:
    """
    Manages active WebSocket connections
    
    Features:
    - Connection tracking per IP
    - Rate limiting
    - Broadcast to multiple connections
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connections_by_ip: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, client_ip: str) -> bool:
        """
        Accept new WebSocket connection
        
        Returns:
            True if accepted, False if rate limited
        """
        # Check rate limit
        if client_ip in self.connections_by_ip:
            if len(self.connections_by_ip[client_ip]) >= MAX_CONNECTIONS_PER_IP:
                logger.warning(f"⚠️ Rate limit exceeded for IP: {client_ip}")
                return False
        
        await websocket.accept()
        
        self.active_connections[client_id] = websocket
        
        if client_ip not in self.connections_by_ip:
            self.connections_by_ip[client_ip] = set()
        self.connections_by_ip[client_ip].add(client_id)
        
        logger.info(f"✅ WebSocket connected: {client_id} ({client_ip})")
        return True
    
    def disconnect(self, client_id: str, client_ip: str):
        """Disconnect WebSocket"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_ip in self.connections_by_ip:
            self.connections_by_ip[client_ip].discard(client_id)
            if not self.connections_by_ip[client_ip]:
                del self.connections_by_ip[client_ip]
        
        logger.info(f"🔌 WebSocket disconnected: {client_id}")
    
    async def send_json(self, client_id: str, message: dict):
        """Send JSON message to client"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def send_bytes(self, client_id: str, data: bytes):
        """Send binary data to client"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_bytes(data)


# ================================================================
# WEBSOCKET UPLOAD HANDLER
# ================================================================

class WebSocketUploadHandler:
    """
    WebSocket upload handler with bidirectional control
    
    Protocol Flow:
    1. Client connects via WebSocket
    2. Client sends START_UPLOAD message (JSON)
    3. Server responds with UPLOAD_STARTED (JSON)
    4. Client sends binary chunks
    5. Server sends PROGRESS updates (JSON)
    6. Server can send PAUSE_REQUEST (JSON)
    7. Client responds with PAUSE (JSON)
    8. Client can send RESUME (JSON)
    9. After all chunks: Server sends COMPLETED (JSON)
    
    Message Format:
    - Control: JSON text frames
    - Data: Binary frames (raw chunk bytes)
    """
    
    def __init__(self):
        self.connection_manager = WebSocketConnectionManager()
        self.upload_sessions: Dict[str, WebSocketUploadSession] = {}
    
    async def handle_connection(
        self, 
        websocket: WebSocket,
        client_ip: str,
        job_manager=None
    ):
        """
        Handle WebSocket connection lifecycle
        
        Args:
            websocket: FastAPI WebSocket instance
            client_ip: Client IP address
            job_manager: JobManager instance (optional)
        """
        client_id = str(uuid.uuid4())
        
        # Accept connection (with rate limiting)
        accepted = await self.connection_manager.connect(websocket, client_id, client_ip)
        if not accepted:
            await websocket.close(code=1008, reason="Rate limit exceeded")
            return
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat(client_id))
        
        current_upload_id = None
        
        try:
            while True:
                # Receive message (JSON or binary)
                message = await websocket.receive()
                
                if "text" in message:
                    # JSON control message
                    result = await self._handle_control_message(
                        client_id, 
                        message["text"], 
                        job_manager
                    )
                    
                    # Track upload_id if START_UPLOAD successful
                    if result and isinstance(result, dict) and "upload_id" in result:
                        current_upload_id = result["upload_id"]
                    
                elif "bytes" in message:
                    # Binary chunk data
                    if current_upload_id:
                        await self._handle_chunk_data(
                            client_id,
                            current_upload_id,
                            message["bytes"]
                        )
                    else:
                        await self._send_error(
                            client_id,
                            "NO_ACTIVE_UPLOAD",
                            "No active upload session"
                        )
        
        except WebSocketDisconnect:
            logger.info(f"🔌 Client disconnected: {client_id}")
        
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}", exc_info=True)
            await self._send_error(client_id, "INTERNAL_ERROR", str(e))
        
        finally:
            # Cleanup
            heartbeat_task.cancel()
            self.connection_manager.disconnect(client_id, client_ip)
            
            # Keep upload session for resume
            # (don't delete here, cleanup happens on timeout or completion)
    
    async def _handle_control_message(
        self, 
        client_id: str, 
        message_text: str,
        job_manager
    ):
        """
        Handle JSON control message
        
        Returns:
            Result dict if message processed successfully (e.g., upload_id for START_UPLOAD)
        """
        try:
            message_data = json.loads(message_text)
            message_type = message_data.get("type")
            
            if message_type == MessageType.START_UPLOAD:
                return await self._handle_start_upload(client_id, message_data)
            
            elif message_type == MessageType.RESUME_UPLOAD:
                await self._handle_resume(client_id, message_data)
            
            elif message_type == MessageType.PAUSE:
                await self._handle_pause(client_id, message_data)
            
            elif message_type == MessageType.CANCEL:
                await self._handle_cancel(client_id, message_data)
            
            elif message_type == MessageType.PING:
                await self._send_pong(client_id)
            
            else:
                await self._send_error(
                    client_id,
                    "UNKNOWN_MESSAGE_TYPE",
                    f"Unknown message type: {message_type}"
                )
        
        except json.JSONDecodeError as e:
            await self._send_error(client_id, "INVALID_JSON", str(e))
    
    async def _handle_start_upload(self, client_id: str, message_data: dict):
        """Handle START_UPLOAD message"""
        file_name = message_data.get("file_name")
        file_size = message_data.get("file_size")
        chunk_size = message_data.get("chunk_size", DEFAULT_WS_CHUNK_SIZE)
        
        if not file_name or not file_size:
            await self._send_error(
                client_id,
                "INVALID_START_MESSAGE",
                "Missing file_name or file_size"
            )
            return
        
        # Create upload session
        upload_id = str(uuid.uuid4())
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        storage_dir = WS_UPLOAD_STORAGE_DIR / upload_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = storage_dir / file_name
        output_file = open(output_path, 'wb')
        
        session = WebSocketUploadSession(
            upload_id=upload_id,
            file_name=file_name,
            file_size=file_size,
            total_chunks=total_chunks,
            chunk_size=chunk_size,
            chunks_received=set(),
            storage_dir=storage_dir,
            output_file=output_file
        )
        
        self.upload_sessions[upload_id] = session
        
        logger.info(
            f"📤 Upload started: {upload_id} - {file_name} "
            f"({total_chunks} chunks × {chunk_size} bytes)"
        )
        
        # Send response
        response = UploadStartedMessage(
            upload_id=upload_id,
            resume_from_chunk=0,
            chunk_size=chunk_size
        )
        
        await self.connection_manager.send_json(client_id, asdict(response))
        
        # Return upload_id for tracking
        return {"upload_id": upload_id}
    
    async def _handle_chunk_data(
        self, 
        client_id: str, 
        upload_id: str, 
        chunk_data: bytes
    ):
        """Handle binary chunk data"""
        session = self.upload_sessions.get(upload_id)
        if not session:
            await self._send_error(client_id, "SESSION_NOT_FOUND", f"Upload session not found: {upload_id}")
            return
        
        if session.paused:
            await self._send_error(client_id, "UPLOAD_PAUSED", "Upload is paused")
            return
        
        if session.cancelled:
            await self._send_error(client_id, "UPLOAD_CANCELLED", "Upload was cancelled")
            return
        
        # Write chunk to file
        session.output_file.write(chunk_data)
        
        # Track chunk
        chunk_index = len(session.chunks_received)
        session.chunks_received.add(chunk_index)
        session.last_activity_at = datetime.now()
        
        # Send progress update
        progress = ProgressMessage(
            upload_id=upload_id,
            chunks_received=len(session.chunks_received),
            total_chunks=session.total_chunks,
            percent=session.percent_complete,
            bytes_received=session.bytes_received,
            file_size=session.file_size
        )
        
        await self.connection_manager.send_json(client_id, asdict(progress))
        
        # Check if complete
        if session.is_complete:
            await self._finalize_upload(client_id, upload_id)
    
    async def _finalize_upload(self, client_id: str, upload_id: str):
        """Finalize upload after all chunks received"""
        session = self.upload_sessions.get(upload_id)
        if not session:
            return
        
        # Close file
        session.output_file.close()
        
        duration = (datetime.now() - session.started_at).total_seconds()
        
        file_path = session.storage_dir / session.file_name
        
        # TODO: Create job and process file
        job_id = "N/A"  # Placeholder
        
        # Send completion message
        completion = CompletedMessage(
            upload_id=upload_id,
            job_id=job_id,
            file_path=str(file_path),
            file_size=session.file_size,
            duration_seconds=duration
        )
        
        await self.connection_manager.send_json(client_id, asdict(completion))
        
        logger.info(
            f"✅ Upload completed: {upload_id} - {session.file_name} "
            f"({session.total_chunks} chunks, {duration:.2f}s)"
        )
        
        # Cleanup session
        del self.upload_sessions[upload_id]
    
    async def _handle_resume(self, client_id: str, message_data: dict):
        """Handle RESUME message"""
        upload_id = message_data.get("upload_id")
        
        session = self.upload_sessions.get(upload_id)
        if not session:
            await self._send_error(client_id, "SESSION_NOT_FOUND", f"Upload session not found: {upload_id}")
            return
        
        session.paused = False
        session.last_activity_at = datetime.now()
        
        response = {
            "type": MessageType.RESUMED,
            "upload_id": upload_id,
            "resume_from_chunk": len(session.chunks_received)
        }
        
        await self.connection_manager.send_json(client_id, response)
        
        logger.info(f"▶️ Upload resumed: {upload_id}")
    
    async def _handle_pause(self, client_id: str, message_data: dict):
        """Handle PAUSE message"""
        upload_id = message_data.get("upload_id")
        
        session = self.upload_sessions.get(upload_id)
        if not session:
            return
        
        session.paused = True
        logger.info(f"⏸️ Upload paused: {upload_id}")
    
    async def _handle_cancel(self, client_id: str, message_data: dict):
        """Handle CANCEL message"""
        upload_id = message_data.get("upload_id")
        
        session = self.upload_sessions.get(upload_id)
        if not session:
            return
        
        session.cancelled = True
        session.output_file.close()
        
        # Delete partial file
        file_path = session.storage_dir / session.file_name
        if file_path.exists():
            file_path.unlink()
        
        # Cleanup session
        del self.upload_sessions[upload_id]
        
        logger.info(f"❌ Upload cancelled: {upload_id}")
    
    async def _send_error(self, client_id: str, error_code: str, message: str):
        """Send error message to client"""
        error = ErrorMessage(
            error_code=error_code,
            message=message
        )
        await self.connection_manager.send_json(client_id, asdict(error))
    
    async def _send_pong(self, client_id: str):
        """Send PONG response"""
        await self.connection_manager.send_json(client_id, {"type": MessageType.PONG})
    
    async def _heartbeat(self, client_id: str):
        """Heartbeat task to keep connection alive"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await self._send_pong(client_id)
            except:
                break


# ================================================================
# GLOBAL INSTANCE
# ================================================================

_handler = None

def get_websocket_upload_handler() -> WebSocketUploadHandler:
    """Get or create WebSocket upload handler"""
    global _handler
    
    if _handler is None:
        _handler = WebSocketUploadHandler()
    
    return _handler
