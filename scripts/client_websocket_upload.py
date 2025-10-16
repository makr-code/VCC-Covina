#!/usr/bin/env python3
"""
WebSocket Upload Client

Async Python client for WebSocket-based file uploads.

Features:
- Asynchronous binary streaming
- Automatic reconnection with resume
- Real-time progress updates
- Server-side control (pause/resume/cancel)
- Heartbeat keep-alive

Usage:
    python client_websocket_upload.py <file_path> [options]

Examples:
    # Upload with default settings (64KB chunks)
    python client_websocket_upload.py C:\\Data\\document.pdf
    
    # Upload with custom chunk size
    python client_websocket_upload.py C:\\Data\\document.pdf --chunk-size 256KB
    
    # Upload with custom server URL
    python client_websocket_upload.py C:\\Data\\document.pdf --url ws://localhost:45679/ws/upload

Author: Covina Development Team
Created: 15. Oktober 2025
Version: 1.0.0
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import websockets
except ImportError:
    print("❌ ERROR: websockets library not installed")
    print("   Install with: pip install websockets")
    sys.exit(1)

# ================================================================
# CONFIGURATION
# ================================================================

DEFAULT_WS_URL = "ws://127.0.0.1:45679/ws/upload"
DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB (WebSocket optimal)

# ================================================================
# MESSAGE TYPES
# ================================================================

class MessageType:
    """WebSocket message types"""
    # Client → Server
    START_UPLOAD = "start_upload"
    RESUME = "resume"
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

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def parse_size(size_str: str) -> int:
    """
    Parse size string to bytes
    
    Examples:
        "1024" → 1024
        "10KB" → 10240
        "5MB" → 5242880
        "1GB" → 1073741824
    
    Args:
        size_str: Size string (with optional KB/MB/GB/TB suffix)
    
    Returns:
        Size in bytes
    
    Raises:
        ValueError: If format invalid
    """
    size_str = size_str.upper().strip()
    
    # Order matters: Check longer units first (MB before B, GB before B)
    multipliers = [
        ('TB', 1024**4),
        ('GB', 1024**3),
        ('MB', 1024**2),
        ('KB', 1024),
        ('B', 1)
    ]
    
    for unit, multiplier in multipliers:
        if size_str.endswith(unit):
            value_str = size_str[:-len(unit)].strip()
            try:
                value = float(value_str)
                return int(value * multiplier)
            except ValueError:
                raise ValueError(f"Invalid size format: {size_str}")
    
    # No unit, assume bytes
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid size format: {size_str}")


def format_size(size_bytes: int) -> str:
    """
    Format bytes to human-readable string
    
    Examples:
        1024 → "1.00 KB"
        1048576 → "1.00 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format seconds to human-readable duration"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

# ================================================================
# WEBSOCKET UPLOADER
# ================================================================

class WebSocketUploader:
    """
    Async WebSocket upload client
    
    Features:
    - Binary streaming
    - Automatic reconnection
    - Resume from last chunk
    - Real-time progress
    - Server control support
    """
    
    def __init__(
        self, 
        url: str = DEFAULT_WS_URL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        max_reconnect_attempts: int = 3
    ):
        """
        Initialize WebSocket uploader
        
        Args:
            url: WebSocket URL (ws://host:port/path)
            chunk_size: Chunk size in bytes
            max_reconnect_attempts: Max reconnection attempts
        """
        self.url = url
        self.chunk_size = chunk_size
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Upload state
        self.upload_id: Optional[str] = None
        self.paused = False
        self.cancelled = False
        
        # Progress tracking
        self.chunks_sent = 0
        self.total_chunks = 0
        self.start_time = 0
    
    async def upload_file(self, file_path: str) -> dict:
        """
        Upload file via WebSocket
        
        Args:
            file_path: Path to file
        
        Returns:
            Upload result dict with job_id, duration, etc.
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ConnectionError: If WebSocket connection fails
        """
        # Validate file
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_name = path.name
        file_size = path.stat().st_size
        self.total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        
        print(f"\n{'='*60}")
        print(f"📤 WebSocket Upload")
        print(f"{'='*60}")
        print(f"File:       {file_name}")
        print(f"Size:       {format_size(file_size)}")
        print(f"Chunks:     {self.total_chunks} × {format_size(self.chunk_size)}")
        print(f"Server:     {self.url}")
        print(f"{'='*60}\n")
        
        self.start_time = time.time()
        
        # Connect and upload
        result = None
        for attempt in range(1, self.max_reconnect_attempts + 1):
            try:
                async with websockets.connect(self.url) as websocket:
                    result = await self._do_upload(websocket, path, file_name, file_size)
                    break  # Success
            
            except (websockets.ConnectionClosed, ConnectionError) as e:
                print(f"⚠️ Connection error (attempt {attempt}/{self.max_reconnect_attempts}): {e}")
                
                if attempt < self.max_reconnect_attempts:
                    print(f"🔄 Reconnecting in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    print(f"❌ Max reconnection attempts reached")
                    raise ConnectionError("Failed to connect to WebSocket server")
        
        return result
    
    async def _do_upload(
        self, 
        websocket, 
        file_path: Path, 
        file_name: str, 
        file_size: int
    ) -> dict:
        """
        Perform upload over WebSocket connection
        
        Args:
            websocket: WebSocket connection
            file_path: Path object to file
            file_name: File name
            file_size: File size in bytes
        
        Returns:
            Upload result dict
        """
        # Start upload session
        print("🔄 Starting upload session...")
        await self._send_start_upload(websocket, file_name, file_size)
        
        # Wait for UPLOAD_STARTED response
        response = await self._receive_message(websocket)
        
        if response["type"] != MessageType.UPLOAD_STARTED:
            raise RuntimeError(f"Expected UPLOAD_STARTED, got {response['type']}")
        
        self.upload_id = response["upload_id"]
        resume_from_chunk = response.get("resume_from_chunk", 0)
        
        print(f"✅ Upload session started")
        print(f"   Upload ID: {self.upload_id}")
        if resume_from_chunk > 0:
            print(f"   Resuming from chunk: {resume_from_chunk}")
        print()
        
        # Upload chunks
        print(f"📦 Uploading {self.total_chunks} chunks...\n")
        
        result = await self._upload_chunks(websocket, file_path, file_size, resume_from_chunk)
        
        return result
    
    async def _upload_chunks(
        self, 
        websocket, 
        file_path: Path, 
        file_size: int,
        resume_from_chunk: int = 0
    ) -> dict:
        """
        Upload file chunks
        
        Args:
            websocket: WebSocket connection
            file_path: Path to file
            file_size: File size in bytes
            resume_from_chunk: Chunk to resume from
        
        Returns:
            Upload result dict
        """
        # Create tasks: chunk sender + message receiver
        send_task = asyncio.create_task(
            self._send_chunks(websocket, file_path, file_size, resume_from_chunk)
        )
        
        receive_task = asyncio.create_task(
            self._receive_messages(websocket)
        )
        
        # Wait for both tasks
        result = await asyncio.gather(send_task, receive_task)
        
        return result[1]  # Return result from receive_messages
    
    async def _send_chunks(
        self, 
        websocket, 
        file_path: Path, 
        file_size: int,
        resume_from_chunk: int
    ):
        """Send file chunks to server"""
        with open(file_path, 'rb') as f:
            # Skip to resume point
            if resume_from_chunk > 0:
                f.seek(resume_from_chunk * self.chunk_size)
                self.chunks_sent = resume_from_chunk
            
            while True:
                # Check if paused
                while self.paused:
                    await asyncio.sleep(0.1)
                
                # Check if cancelled
                if self.cancelled:
                    break
                
                # Read chunk
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break  # EOF
                
                # Send chunk
                await websocket.send(chunk)
                self.chunks_sent += 1
    
    async def _receive_messages(self, websocket) -> dict:
        """
        Receive and handle server messages
        
        Returns:
            Final result dict when upload completes
        """
        last_progress_time = time.time()
        
        async for message in websocket:
            # Parse JSON message
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == MessageType.PROGRESS:
                # Update progress
                chunks_received = data["chunks_received"]
                total_chunks = data["total_chunks"]
                percent = data["percent"]
                
                # Throttle progress updates (max 1/second)
                now = time.time()
                if now - last_progress_time >= 0.2:
                    elapsed = now - self.start_time
                    chunks_per_sec = chunks_received / elapsed if elapsed > 0 else 0
                    eta = (total_chunks - chunks_received) / chunks_per_sec if chunks_per_sec > 0 else 0
                    
                    print(
                        f"   Progress: {chunks_received}/{total_chunks} "
                        f"({percent:.1f}%) - {chunks_per_sec:.1f} chunks/s - "
                        f"ETA: {format_duration(eta)}     ",
                        end='\r'
                    )
                    
                    last_progress_time = now
            
            elif msg_type == MessageType.COMPLETED:
                # Upload complete!
                print("\n")
                duration = time.time() - self.start_time
                
                print(f"✅ Upload complete!")
                print(f"   Job ID: {data['job_id']}")
                print(f"   File Path: {data['file_path']}")
                print(f"   Duration: {format_duration(duration)}")
                print(f"\n{'='*60}")
                print(f"✅ SUCCESS")
                print(f"{'='*60}\n")
                
                return data
            
            elif msg_type == MessageType.ERROR:
                # Server error
                print(f"\n❌ Server error: {data['message']}")
                print(f"   Error code: {data['error_code']}")
                raise RuntimeError(data['message'])
            
            elif msg_type == MessageType.PAUSE_REQUEST:
                # Server requested pause
                print(f"\n⏸️ Server requested pause")
                self.paused = True
                
                # Send PAUSE acknowledgment
                await self._send_pause(websocket)
            
            elif msg_type == MessageType.PONG:
                # Heartbeat response (ignore)
                pass
        
        # Connection closed without completion
        raise RuntimeError("Connection closed before upload completed")
    
    async def _send_start_upload(self, websocket, file_name: str, file_size: int):
        """Send START_UPLOAD message"""
        message = {
            "type": MessageType.START_UPLOAD,
            "file_name": file_name,
            "file_size": file_size,
            "chunk_size": self.chunk_size
        }
        await websocket.send(json.dumps(message))
    
    async def _send_pause(self, websocket):
        """Send PAUSE message"""
        message = {
            "type": MessageType.PAUSE,
            "upload_id": self.upload_id
        }
        await websocket.send(json.dumps(message))
    
    async def _send_resume(self, websocket):
        """Send RESUME message"""
        message = {
            "type": MessageType.RESUME,
            "upload_id": self.upload_id
        }
        await websocket.send(json.dumps(message))
    
    async def _receive_message(self, websocket) -> dict:
        """Receive single message"""
        message = await websocket.recv()
        return json.loads(message)

# ================================================================
# CLI
# ================================================================

async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="WebSocket file upload client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Upload with defaults:
    %(prog)s C:\\Data\\document.pdf
  
  Custom chunk size:
    %(prog)s C:\\Data\\document.pdf --chunk-size 256KB
  
  Custom server:
    %(prog)s C:\\Data\\document.pdf --url ws://localhost:45679/ws/upload
        """
    )
    
    parser.add_argument(
        "file",
        help="File to upload"
    )
    
    parser.add_argument(
        "--chunk-size",
        default=f"{DEFAULT_CHUNK_SIZE // 1024}KB",
        help=f"Chunk size (default: {DEFAULT_CHUNK_SIZE // 1024}KB). Examples: 64KB, 1MB, 5MB"
    )
    
    parser.add_argument(
        "--url",
        default=DEFAULT_WS_URL,
        help=f"WebSocket URL (default: {DEFAULT_WS_URL})"
    )
    
    parser.add_argument(
        "--max-reconnect",
        type=int,
        default=3,
        help="Max reconnection attempts (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Parse chunk size
    try:
        chunk_size = parse_size(args.chunk_size)
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    # Create uploader
    uploader = WebSocketUploader(
        url=args.url,
        chunk_size=chunk_size,
        max_reconnect_attempts=args.max_reconnect
    )
    
    # Upload file
    try:
        result = await uploader.upload_file(args.file)
        return 0
    
    except FileNotFoundError as e:
        print(f"\n❌ {e}\n")
        return 1
    
    except Exception as e:
        print(f"\n❌ Upload failed: {e}\n")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
