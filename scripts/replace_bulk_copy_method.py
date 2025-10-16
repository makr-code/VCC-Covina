"""
Auto-Replace Script for _bulk_copy_directory Integration
=========================================================

This script automatically replaces the old _bulk_copy_directory method
with the new streaming version.

Usage:
    python scripts/replace_bulk_copy_method.py

Author: Covina Development Team
Date: 14. Oktober 2025, 16:00 Uhr
"""

import re
from pathlib import Path

# Paths
BACKEND_FILE = Path("ingestion_backend.py")
BACKUP_FILE = Path("ingestion_backend.py.backup")

# New method implementation
NEW_METHOD = '''    async def _bulk_copy_directory(self):
        """
        🆕 Copy entire directory to temp_dir with STREAMING PROGRESS UPDATES.
        
        Benefits:
        - Much faster than Python file-by-file copy
        - Handles Network Drives efficiently
        - Real-time progress updates via WebSocket
        - Robust error handling
        - Uses robocopy (Windows) or rsync (Linux)
        """
        from ingestion.bulk_copy_streaming import BulkCopyStreaming, CopyProgress
        
        logger.info(f"📦 [SCAN {self.scan_job_id}] Bulk copy: {self.directory_path} → {self.temp_dir}")
        
        # 🆕 Initialize progress tracking
        self.bulk_copy_progress = BulkCopyProgress(status="preparing")
        await self._broadcast_bulk_copy_progress()
        
        async def on_progress(progress: CopyProgress):
            """Callback for progress updates from streaming module"""
            # Update our progress object
            self.bulk_copy_progress.percent_complete = progress.percent_complete
            self.bulk_copy_progress.files_copied = progress.files_copied
            self.bulk_copy_progress.total_files = progress.total_files
            self.bulk_copy_progress.bytes_copied = progress.bytes_copied
            self.bulk_copy_progress.total_bytes = progress.total_bytes
            self.bulk_copy_progress.copy_rate_mbps = progress.copy_rate_mbps
            self.bulk_copy_progress.eta_seconds = progress.eta_seconds
            self.bulk_copy_progress.current_file = progress.current_file
            self.bulk_copy_progress.status = progress.status
            
            # Broadcast to WebSocket clients
            await self._broadcast_bulk_copy_progress()
        
        # 🆕 Use streaming bulk copy with progress callbacks
        copier = BulkCopyStreaming(
            source=self.directory_path,
            destination=self.temp_dir,
            progress_callback=on_progress,
            broadcast_interval=5.0  # Update UI every 5 seconds
        )
        
        timeout_seconds = 1800  # 30 minutes for large network transfers (7+ GB)
        
        try:
            final_progress = await copier.execute(timeout=timeout_seconds)
            
            logger.info(
                f"✅ [SCAN {self.scan_job_id}] Bulk copy complete: "
                f"{final_progress.files_copied} files, "
                f"{final_progress.bytes_copied / (1024**3):.2f} GB, "
                f"avg rate: {final_progress.copy_rate_mbps:.1f} MB/s"
            )
            
            # Mark progress as completed
            self.bulk_copy_progress.status = "completed"
            await self._broadcast_bulk_copy_progress()
            
            # Re-initialize scanner to point to LOCAL copy
            logger.info(f"🔄 [SCAN {self.scan_job_id}] Re-initializing scanner for local copy...")
            self.scanner = DirectoryScanner(
                root=self.temp_dir,  # ✅ Now scans local copy!
                classifier=FileClassifier(),
                compute_hashes=False
            )
            logger.info(f"✅ [SCAN {self.scan_job_id}] Scanner ready for local directory")
            
        except asyncio.TimeoutError:
            self.bulk_copy_progress.status = "error"
            await self._broadcast_bulk_copy_progress()
            raise TimeoutError(
                f"Directory copy timeout after {timeout_seconds}s "
                f"(source: {self.directory_path})"
            )
        except Exception as e:
            self.bulk_copy_progress.status = "error"
            await self._broadcast_bulk_copy_progress()
            logger.error(f"❌ [SCAN {self.scan_job_id}] Bulk copy error: {e}")
            raise'''


def main():
    print("=" * 60)
    print("AUTO-REPLACE: _bulk_copy_directory Method")
    print("=" * 60)
    
    # Check if file exists
    if not BACKEND_FILE.exists():
        print(f"❌ ERROR: {BACKEND_FILE} not found!")
        return 1
    
    # Create backup
    print(f"\n📦 Creating backup: {BACKUP_FILE}")
    content = BACKEND_FILE.read_text(encoding='utf-8')
    BACKUP_FILE.write_text(content, encoding='utf-8')
    print(f"✅ Backup created ({len(content)} bytes)")
    
    # Find method boundaries
    print(f"\n🔍 Searching for _bulk_copy_directory method...")
    
    # Pattern to match the entire method
    pattern = r'(    async def _bulk_copy_directory\(self\):.*?)(\n    async def \w+)'
    
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("❌ ERROR: Could not find _bulk_copy_directory method!")
        print("   Pattern used: async def _bulk_copy_directory(self):")
        return 1
    
    old_method = match.group(1)
    next_method = match.group(2)
    
    print(f"✅ Found method (Old: {len(old_method)} chars)")
    print(f"   Next method: {next_method[:40]}...")
    
    # Replace
    print(f"\n🔄 Replacing with new implementation...")
    new_content = content.replace(old_method, NEW_METHOD)
    
    if new_content == content:
        print("⚠️  WARNING: No changes made! Method might already be updated.")
        return 2
    
    # Write back
    print(f"\n💾 Writing updated file...")
    BACKEND_FILE.write_text(new_content, encoding='utf-8')
    print(f"✅ File written ({len(new_content)} bytes)")
    
    # Verify syntax
    print(f"\n🧪 Verifying syntax...")
    import subprocess
    result = subprocess.run(
        ["python", "-m", "py_compile", str(BACKEND_FILE)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Syntax check PASSED!")
    else:
        print(f"❌ Syntax check FAILED:")
        print(result.stderr)
        print(f"\n🔄 Restoring backup...")
        BACKEND_FILE.write_text(content, encoding='utf-8')
        print(f"✅ Backup restored")
        return 3
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ REPLACEMENT COMPLETE!")
    print("=" * 60)
    print(f"\nOld method: {len(old_method)} chars")
    print(f"New method: {len(NEW_METHOD)} chars")
    print(f"Difference: {len(NEW_METHOD) - len(old_method):+d} chars")
    print(f"\n📄 Backup: {BACKUP_FILE}")
    print(f"\n🚀 Next steps:")
    print(f"   1. Restart ingestion backend")
    print(f"   2. Test with small directory upload")
    print(f"   3. Monitor progress modal")
    
    return 0


if __name__ == "__main__":
    exit(main())
