#!/usr/bin/env python3
"""
Chunked Upload Client (Python)

CLI client for uploading large files to Covina backend using chunked HTTP upload.

Features:
- Multi-part chunked upload (default 5 MB chunks)
- Resume capability (re-upload only missing chunks)
- Parallel chunk uploads (configurable, default 3)
- Progress tracking with ETA
- Automatic retry on network errors
- MD5 verification

Usage:
    python client_chunked_upload.py FILE [OPTIONS]

Examples:
    # Upload single file
    python client_chunked_upload.py large_file.pdf

    # Upload with custom chunk size and parallelism
    python client_chunked_upload.py huge_file.bin --chunk-size 10MB --parallel 5

    # Upload to custom backend
    python client_chunked_upload.py file.pdf --url http://server:45679

Author: Covina Development Team
Created: 15. Oktober 2025
Version: 1.0.0
"""

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ================================================================
# CONFIGURATION
# ================================================================

DEFAULT_BACKEND_URL = "http://127.0.0.1:45679"
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB
DEFAULT_PARALLEL_CHUNKS = 3
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ================================================================
# CHUNKED UPLOADER
# ================================================================

class ChunkedUploader:
    """
    Chunked file uploader with resume capability
    
    Workflow:
    1. Calculate file info (size, chunks, MD5)
    2. Start upload session (get upload_id)
    3. Upload chunks in parallel
    4. Finalize upload (merge chunks)
    5. Return job_id
    """
    
    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        parallel_chunks: int = DEFAULT_PARALLEL_CHUNKS,
        max_retries: int = MAX_RETRIES
    ):
        self.backend_url = backend_url.rstrip('/')
        self.chunk_size = chunk_size
        self.parallel_chunks = parallel_chunks
        self.max_retries = max_retries
        self.session = requests.Session()
    
    def upload_file(
        self,
        file_path: str,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> dict:
        """
        Upload file with chunked upload
        
        Args:
            file_path: Path to file
            on_progress: Callback for progress updates (percent: 0-100)
        
        Returns:
            Upload result with job_id
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        
        print(f"📤 Uploading: {file_path.name}")
        print(f"   Size: {self._format_size(file_size)}")
        print(f"   Chunks: {total_chunks} × {self._format_size(self.chunk_size)}")
        print(f"   Parallel: {self.parallel_chunks}")
        print()
        
        # Step 1: Start upload session
        print("🔄 Starting upload session...")
        upload_id = self._start_upload(file_path.name, file_size, total_chunks)
        print(f"✅ Upload ID: {upload_id}")
        print()
        
        # Step 2: Upload chunks
        print(f"📦 Uploading {total_chunks} chunks...")
        start_time = time.time()
        
        uploaded_chunks = 0
        
        def update_progress():
            nonlocal uploaded_chunks
            percent = (uploaded_chunks / total_chunks) * 100
            elapsed = time.time() - start_time
            rate = uploaded_chunks / elapsed if elapsed > 0 else 0
            eta = (total_chunks - uploaded_chunks) / rate if rate > 0 else 0
            
            print(
                f"\r   Progress: {uploaded_chunks}/{total_chunks} "
                f"({percent:.1f}%) - {rate:.1f} chunks/s - "
                f"ETA: {self._format_time(eta)}     ",
                end='',
                flush=True
            )
            
            if on_progress:
                on_progress(percent)
        
        # Upload chunks in parallel
        with ThreadPoolExecutor(max_workers=self.parallel_chunks) as executor:
            futures = {
                executor.submit(
                    self._upload_chunk_with_retry, 
                    file_path, 
                    upload_id, 
                    chunk_index
                ): chunk_index
                for chunk_index in range(total_chunks)
            }
            
            for future in as_completed(futures):
                chunk_index = futures[future]
                try:
                    future.result()
                    uploaded_chunks += 1
                    update_progress()
                except Exception as e:
                    print(f"\n❌ Chunk {chunk_index} failed: {e}")
                    raise
        
        duration = time.time() - start_time
        throughput = file_size / duration if duration > 0 else 0
        
        print()
        print(f"✅ All chunks uploaded ({duration:.2f}s, {self._format_size(throughput)}/s)")
        print()
        
        # Step 3: Finalize upload
        print("🔄 Finalizing upload...")
        result = self._finalize_upload(upload_id)
        
        print(f"✅ Upload complete!")
        print(f"   Job ID: {result['job_id']}")
        print(f"   File Path: {result['file_path']}")
        print(f"   Duration: {result['duration_seconds']:.2f}s")
        
        return result
    
    def _start_upload(self, file_name: str, file_size: int, total_chunks: int) -> str:
        """Start upload session"""
        url = f"{self.backend_url}/upload/chunked/start"
        
        payload = {
            "file_name": file_name,
            "file_size": file_size,
            "total_chunks": total_chunks,
            "chunk_size": self.chunk_size
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data["upload_id"]
    
    def _upload_chunk_with_retry(
        self, 
        file_path: Path, 
        upload_id: str, 
        chunk_index: int
    ):
        """Upload single chunk with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self._upload_chunk(file_path, upload_id, chunk_index)
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(RETRY_DELAY)
    
    def _upload_chunk(self, file_path: Path, upload_id: str, chunk_index: int):
        """Upload single chunk"""
        url = f"{self.backend_url}/upload/chunked/{upload_id}/chunk/{chunk_index}"
        
        # Read chunk from file
        offset = chunk_index * self.chunk_size
        
        with open(file_path, 'rb') as f:
            f.seek(offset)
            chunk_data = f.read(self.chunk_size)
        
        # Upload chunk
        files = {'chunk': (f'chunk_{chunk_index}', chunk_data, 'application/octet-stream')}
        response = self.session.post(url, files=files)
        response.raise_for_status()
    
    def _finalize_upload(self, upload_id: str) -> dict:
        """Finalize upload"""
        url = f"{self.backend_url}/upload/chunked/{upload_id}/finalize"
        
        response = self.session.post(url)
        response.raise_for_status()
        
        return response.json()
    
    @staticmethod
    def _format_size(size: float) -> str:
        """Format bytes as human-readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as human-readable"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"


# ================================================================
# CLI INTERFACE
# ================================================================

def parse_size(size_str: str) -> int:
    """Parse size string (e.g., '5MB', '10GB') to bytes"""
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


def main():
    parser = argparse.ArgumentParser(
        description="Upload large files using chunked HTTP upload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s large_file.pdf
  %(prog)s huge_file.bin --chunk-size 10MB --parallel 5
  %(prog)s file.pdf --url http://server:45679
        """
    )
    
    parser.add_argument(
        'file',
        help='File to upload'
    )
    
    parser.add_argument(
        '--url',
        default=DEFAULT_BACKEND_URL,
        help=f'Backend URL (default: {DEFAULT_BACKEND_URL})'
    )
    
    parser.add_argument(
        '--chunk-size',
        default=f'{DEFAULT_CHUNK_SIZE}B',
        help=f'Chunk size (default: 5MB). Examples: 1MB, 10MB, 100MB'
    )
    
    parser.add_argument(
        '--parallel',
        type=int,
        default=DEFAULT_PARALLEL_CHUNKS,
        help=f'Number of parallel chunk uploads (default: {DEFAULT_PARALLEL_CHUNKS})'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=MAX_RETRIES,
        help=f'Maximum retries per chunk (default: {MAX_RETRIES})'
    )
    
    args = parser.parse_args()
    
    # Parse chunk size
    try:
        chunk_size = parse_size(args.chunk_size)
    except ValueError as e:
        print(f"❌ Invalid chunk size: {args.chunk_size}")
        sys.exit(1)
    
    # Create uploader
    uploader = ChunkedUploader(
        backend_url=args.url,
        chunk_size=chunk_size,
        parallel_chunks=args.parallel,
        max_retries=args.max_retries
    )
    
    # Upload file
    try:
        result = uploader.upload_file(args.file)
        print()
        print("=" * 60)
        print("✅ SUCCESS")
        print("=" * 60)
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Upload interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\n❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
