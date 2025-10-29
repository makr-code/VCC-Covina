"""
Bulk Copy mit Streaming Progress
==================================

Modul für OS-Level Directory Copy mit Echtzeit-Progress-Updates.

Features:
- Windows: robocopy mit vollständigem Output-Streaming
- Linux/Mac: rsync mit Progress-Parsing
- Real-time Progress-Callbacks
- Robuste Error-Handling

Author: Covina System
Date: 14. Oktober 2025
"""

import asyncio
import logging
import platform
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class CopyProgress:
    """Progress information for bulk copy operation"""
    percent_complete: float = 0.0
    files_copied: int = 0
    total_files: int = 0
    bytes_copied: int = 0
    total_bytes: int = 0
    copy_rate_mbps: float = 0.0
    eta_seconds: int = 0
    current_file: str = ""
    status: str = "preparing"  # preparing, copying, completed, error


class BulkCopyStreaming:
    """
    Streaming Bulk Copy mit Real-Time Progress Updates
    
    Example:
        async def on_progress(progress: CopyProgress):
            print(f"Progress: {progress.percent_complete:.1f}%")
        
        copier = BulkCopyStreaming(
            source="/path/to/source",
            destination="/path/to/dest",
            progress_callback=on_progress
        )
        
        await copier.execute()
    """
    
    def __init__(
        self,
        source: Path,
        destination: Path,
        progress_callback: Optional[Callable[[CopyProgress], any]] = None,
        broadcast_interval: float = 5.0
    ):
        self.source = Path(source)
        self.destination = Path(destination)
        self.progress_callback = progress_callback
        self.broadcast_interval = broadcast_interval
        self.progress = CopyProgress()
        
    async def execute(self, timeout: int = 1800) -> CopyProgress:
        """
        Execute bulk copy with progress streaming
        
        Args:
            timeout: Maximum time in seconds (default: 30 minutes)
            
        Returns:
            Final CopyProgress object
            
        Raises:
            RuntimeError: If copy fails
            asyncio.TimeoutError: If copy exceeds timeout
        """
        logger.info(f"📦 Bulk copy: {self.source} → {self.destination}")
        
        try:
            if platform.system() == "Windows":
                await asyncio.wait_for(
                    self._execute_robocopy(),
                    timeout=timeout
                )
            else:
                await asyncio.wait_for(
                    self._execute_rsync(),
                    timeout=timeout
                )
            
            self.progress.status = "completed"
            self.progress.percent_complete = 100.0
            
            if self.progress_callback:
                await self.progress_callback(self.progress)
            
            logger.info(
                f"✅ Bulk copy complete: {self.progress.files_copied} files, "
                f"{self.progress.bytes_copied / (1024**3):.2f} GB"
            )
            
            return self.progress
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Bulk copy timeout after {timeout}s")
            self.progress.status = "error"
            if self.progress_callback:
                await self.progress_callback(self.progress)
            raise
            
        except Exception as e:
            logger.error(f"❌ Bulk copy error: {e}")
            self.progress.status = "error"
            if self.progress_callback:
                await self.progress_callback(self.progress)
            raise
    
    async def _execute_robocopy(self):
        """Execute robocopy with streaming output (Windows)"""
        cmd = [
            "robocopy",
            str(self.source),
            str(self.destination),
            "/E",          # Copy subdirectories including empty
            "/MT:16",      # Multi-threaded (16 threads)
            "/R:2",        # Retry 2 times on error
            "/W:5",        # Wait 5 seconds between retries
            "/BYTES"       # Show sizes in bytes
            # 🆕 NO /NP, /NFL for FULL output streaming
        ]
        
        logger.info(f"🔧 Running: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='cp850',  # 🆕 Windows OEM encoding for robocopy
            errors='replace',  # Replace invalid chars instead of crashing
            bufsize=1  # Line-buffered
        )
        
        self.progress.status = "copying"
        start_time = time.time()
        last_broadcast = 0
        
        # Stream and parse output
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break  # EOF
                
                # Parse file count
                if "Files :" in line:
                    match = re.search(r'Files\s+:\s+(\d+)', line)
                    if match:
                        self.progress.files_copied = int(match.group(1))
                
                # Parse bytes copied
                if "Bytes :" in line:
                    match = re.search(r'Bytes\s+:\s+([\d.]+)\s+([kmgt])', line, re.IGNORECASE)
                    if match:
                        value = float(match.group(1))
                        unit = match.group(2).lower()
                        multipliers = {'k': 1024, 'm': 1024**2, 'g': 1024**3, 't': 1024**4}
                        self.progress.bytes_copied = int(value * multipliers.get(unit, 1))
                
                # Parse speed
                if "Speed :" in line or "Bytes/sec :" in line:
                    match = re.search(r'([\d.]+)\s+([kmgt])Bytes/sec', line, re.IGNORECASE)
                    if match:
                        value = float(match.group(1))
                        unit = match.group(2).lower()
                        # Convert to MB/s
                        multipliers = {'k': 1/1024, 'm': 1, 'g': 1024, 't': 1024**2}
                        self.progress.copy_rate_mbps = value * multipliers.get(unit, 1)
                
                # Calculate progress percentage (estimate based on elapsed time)
                elapsed = time.time() - start_time
                if self.progress.bytes_copied > 0 and self.progress.copy_rate_mbps > 0:
                    # Rough estimate: assume linear progress over timeout period
                    self.progress.percent_complete = min(99.0, (elapsed / 1800.0) * 100)
                
                # Broadcast progress every N seconds
                if time.time() - last_broadcast >= self.broadcast_interval:
                    if self.progress_callback:
                        await self.progress_callback(self.progress)
                    last_broadcast = time.time()
            
            # Wait for completion
            return_code = process.wait()
            
            # robocopy exit codes: 0-7 are success (8+ is error)
            if return_code >= 8:
                stderr = process.stderr.read()
                raise RuntimeError(f"robocopy failed (code {return_code}): {stderr}")
                
        finally:
            process.stdout.close()
            process.stderr.close()
    
    async def _execute_rsync(self):
        """Execute rsync with streaming output (Linux/Mac)"""
        cmd = [
            "rsync",
            "-av",         # Archive mode + verbose
            "--progress",  # Show progress
            "--stats",     # Show transfer stats
            f"{self.source}/",  # Source with trailing slash
            str(self.destination)
        ]
        
        logger.info(f"🔧 Running: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',  # rsync uses UTF-8
            errors='replace',  # Replace invalid chars
            bufsize=1
        )
        
        self.progress.status = "copying"
        last_broadcast = 0
        
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Parse rsync progress (example: "1.23MB  45%  1.2MB/s")
                if '%' in line:
                    match = re.search(r'(\d+)%', line)
                    if match:
                        self.progress.percent_complete = float(match.group(1))
                
                # Parse speed
                match = re.search(r'([\d.]+)([KMG])B/s', line)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2)
                    multipliers = {'K': 1/1024, 'M': 1, 'G': 1024}
                    self.progress.copy_rate_mbps = value * multipliers.get(unit, 1)
                
                # Broadcast progress
                if time.time() - last_broadcast >= self.broadcast_interval:
                    if self.progress_callback:
                        await self.progress_callback(self.progress)
                    last_broadcast = time.time()
            
            return_code = process.wait()
            if return_code != 0:
                stderr = process.stderr.read()
                raise RuntimeError(f"rsync failed: {stderr}")
                
        finally:
            process.stdout.close()
            process.stderr.close()


# 🆕 Convenience function for simple usage
async def bulk_copy_with_progress(
    source: Path,
    destination: Path,
    progress_callback: Optional[Callable[[CopyProgress], any]] = None,
    timeout: int = 1800
) -> CopyProgress:
    """
    Convenience function for bulk copy with progress
    
    Example:
        async def show_progress(progress):
            print(f"{progress.percent_complete:.1f}% - {progress.copy_rate_mbps:.1f} MB/s")
        
        result = await bulk_copy_with_progress(
            source=Path("/source"),
            destination=Path("/dest"),
            progress_callback=show_progress
        )
    """
    copier = BulkCopyStreaming(source, destination, progress_callback)
    return await copier.execute(timeout=timeout)
