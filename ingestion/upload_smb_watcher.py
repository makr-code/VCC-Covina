"""
SMB Network Share File Watcher

Monitors a network share for new files and automatically uploads them.

Author: Covina Development Team
Created: 15. Oktober 2025
Version: 1.0.0
"""

import hashlib
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Dict
import mimetypes

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_FILE_PATTERNS = ['*.pdf', '*.docx', '*.txt', '*.csv', '*.json', '*.xml']
MIN_FILE_SIZE = 1
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB
FILE_STABLE_DELAY = 2
SMB_UPLOAD_STORAGE_DIR = Path("data/uploads/smb")
SMB_UPLOAD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_FILES_DB = Path("data/smb_processed_files.txt")

def compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash"""
    hash_func = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def extract_file_metadata(file_path: Path) -> Dict:
    """Extract metadata"""
    stat = file_path.stat()
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return {
        "file_name": file_path.name,
        "file_size": stat.st_size,
        "mime_type": mime_type or "application/octet-stream",
        "file_hash": compute_file_hash(file_path),
        "source_path": str(file_path),
        "discovered_at": datetime.now().isoformat()
    }

def is_file_stable(file_path: Path) -> bool:
    """Check if file is stable"""
    try:
        size_before = file_path.stat().st_size
        time.sleep(FILE_STABLE_DELAY)
        size_after = file_path.stat().st_size
        return size_before == size_after
    except OSError:
        return False

class ProcessedFilesTracker:
    """Track processed files"""
    def __init__(self, db_path: Path = PROCESSED_FILES_DB):
        self.db_path = db_path
        self.processed_hashes: Set[str] = set()
        self._load()
    
    def _load(self):
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                self.processed_hashes = set(line.strip() for line in f if line.strip())
    
    def _save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w') as f:
            for file_hash in sorted(self.processed_hashes):
                f.write(f"{file_hash}\n")
    
    def is_processed(self, file_hash: str) -> bool:
        return file_hash in self.processed_hashes
    
    def mark_processed(self, file_hash: str):
        self.processed_hashes.add(file_hash)
        self._save()

class SMBFileWatcher:
    """SMB File Watcher"""
    def __init__(self, watch_directory: str, file_patterns: List[str] = None, recursive: bool = True):
        self.watch_directory = Path(watch_directory)
        self.file_patterns = file_patterns or DEFAULT_FILE_PATTERNS
        self.recursive = recursive
        self.tracker = ProcessedFilesTracker()
    
    def scan_directory(self) -> List[Path]:
        files = []
        if not self.watch_directory.exists():
            logger.error(f"Directory not found: {self.watch_directory}")
            return files
        for pattern in self.file_patterns:
            if self.recursive:
                files.extend(self.watch_directory.rglob(pattern))
            else:
                files.extend(self.watch_directory.glob(pattern))
        return files
    
    def process_file(self, file_path: Path) -> Optional[Dict]:
        if not file_path.is_file():
            return None
        file_size = file_path.stat().st_size
        if file_size < MIN_FILE_SIZE or file_size > MAX_FILE_SIZE:
            return None
        try:
            metadata = extract_file_metadata(file_path)
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return None
        if self.tracker.is_processed(metadata['file_hash']):
            logger.info(f"Skipping duplicate: {file_path.name}")
            return None
        if not is_file_stable(file_path):
            logger.warning(f"File unstable: {file_path.name}")
            return None
        upload_id = metadata['file_hash'][:16]
        storage_dir = SMB_UPLOAD_STORAGE_DIR / upload_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        dest_path = storage_dir / file_path.name
        shutil.copy2(file_path, dest_path)
        self.tracker.mark_processed(metadata['file_hash'])
        logger.info(f"Processed: {file_path.name} -> {dest_path}")
        return {"status": "success", "upload_id": upload_id, "file_path": str(dest_path), "metadata": metadata}
    
    def scan_and_process(self) -> Dict[str, int]:
        files = self.scan_directory()
        stats = {"scanned": len(files), "processed": 0, "skipped": 0}
        for file_path in files:
            result = self.process_file(file_path)
            if result:
                stats["processed"] += 1
            else:
                stats["skipped"] += 1
        return stats

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(description="SMB File Watcher")
    parser.add_argument("watch_dir", help="Directory to watch")
    parser.add_argument("--patterns", nargs='+', default=DEFAULT_FILE_PATTERNS)
    parser.add_argument("--no-recursive", action='store_true')
    args = parser.parse_args()
    watcher = SMBFileWatcher(args.watch_dir, args.patterns, not args.no_recursive)
    stats = watcher.scan_and_process()
    print(f"\n{'='*60}\nSMB File Watcher - Scan Complete\n{'='*60}")
    print(f"Scanned:   {stats['scanned']}\nProcessed: {stats['processed']}\nSkipped:   {stats['skipped']}\n{'='*60}\n")
