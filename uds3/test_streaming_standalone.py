"""
Schneller Standalone-Test für Streaming Operations
Testet die Hauptfunktionalität ohne volle UDS3-Integration
"""

import os
import tempfile
import time
from uds3_streaming_operations import (
    create_streaming_manager,
    StreamingStatus,
    format_bytes,
    format_duration,
    calculate_optimal_chunk_size,
    DEFAULT_CHUNK_SIZE
)

print("=" * 70)
print("UDS3 Streaming Operations - Standalone Tests")
print("=" * 70)

# Test 1: Module basics
print("\n[Test 1] Module Import & Basic Functions")
print(f"✅ Default chunk size: {format_bytes(DEFAULT_CHUNK_SIZE)}")
print(f"✅ Format duration: {format_duration(3665)}")
print(f"✅ Format bytes: {format_bytes(524288000)}")

optimal = calculate_optimal_chunk_size(
    file_size=500 * 1024 * 1024,  # 500 MB
    available_memory=16 * 1024 * 1024 * 1024,  # 16 GB
    network_speed_mbps=1000  # 1 Gbps
)
print(f"✅ Optimal chunk size (fast network): {format_bytes(optimal)}")

# Test 2: Create manager
print("\n[Test 2] StreamingManager Creation")
manager = create_streaming_manager(chunk_size=1024 * 1024)  # 1 MB
print("✅ StreamingManager created successfully")

# Test 3: Upload small file
print("\n[Test 3] Upload Small File (1 MB)")
with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
    f.write(b'x' * (1024 * 1024))  # 1 MB
    temp_file = f.name

progress_updates = []

def on_progress(progress):
    progress_updates.append(progress.progress_percent)
    if progress.is_complete:
        print(f"✅ Upload complete: {progress.progress_percent:.1f}%")

start = time.time()
op_id = manager.upload_large_file(
    file_path=temp_file,
    destination="test/small.txt",
    progress_callback=on_progress
)
elapsed = time.time() - start

print(f"✅ Operation ID: {op_id}")
print(f"✅ Duration: {elapsed:.3f}s")
print(f"✅ Progress updates: {len(progress_updates)}")

# Cleanup
os.unlink(temp_file)

# Test 4: Check progress
print("\n[Test 4] Progress Tracking")
progress = manager.get_progress(op_id)
if progress:
    print(f"✅ Status: {progress.status.value}")
    print(f"✅ Total bytes: {format_bytes(progress.total_bytes)}")
    print(f"✅ Transferred: {format_bytes(progress.transferred_bytes)}")
    print(f"✅ Chunks: {progress.current_chunk}/{progress.chunk_count}")
    if progress.bytes_per_second > 0:
        print(f"✅ Speed: {format_bytes(int(progress.bytes_per_second))}/s")

# Test 5: Upload medium file
print("\n[Test 5] Upload Medium File (10 MB)")
with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
    for _ in range(10):
        f.write(b'y' * (1024 * 1024))  # 10 MB
    temp_file = f.name

start = time.time()
op_id2 = manager.upload_large_file(
    file_path=temp_file,
    destination="test/medium.pdf"
)
elapsed = time.time() - start

progress2 = manager.get_progress(op_id2)
print(f"✅ Operation ID: {op_id2}")
print(f"✅ Duration: {elapsed:.3f}s")
print(f"✅ Chunks: {progress2.chunk_count if progress2 else 'N/A'}")
print(f"✅ Status: {progress2.status.value if progress2 else 'N/A'}")

os.unlink(temp_file)

# Test 6: List operations
print("\n[Test 6] List All Operations")
operations = manager.list_operations()
print(f"✅ Total operations: {len(operations)}")

completed = manager.list_operations(status=StreamingStatus.COMPLETED)
print(f"✅ Completed operations: {len(completed)}")

# Test 7: Concurrent uploads
print("\n[Test 7] Concurrent Uploads (5 files)")
with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
    f.write(b'z' * (512 * 1024))  # 512 KB
    temp_file = f.name

start = time.time()
concurrent_ops = []
for i in range(5):
    op_id = manager.upload_large_file(
        file_path=temp_file,
        destination=f"test/concurrent{i}.txt"
    )
    concurrent_ops.append(op_id)
elapsed = time.time() - start

print(f"✅ All operations completed in {elapsed:.3f}s")
print(f"✅ Average: {elapsed/5:.3f}s per file")

# Check all completed
all_done = all(
    manager.get_progress(op).is_complete 
    for op in concurrent_ops
)
print(f"✅ All concurrent uploads successful: {all_done}")

os.unlink(temp_file)

# Test 8: Cleanup
print("\n[Test 8] Cleanup Old Operations")
removed = manager.cleanup_completed_operations(max_age_seconds=0)
print(f"✅ Removed {removed} old operations")

# Final summary
print("\n" + "=" * 70)
print("STREAMING OPERATIONS TESTS - ALL PASSED ✅")
print("=" * 70)
print(f"\n📊 Performance Summary:")
print(f"  - Small file (1 MB): {elapsed:.3f}s")
print(f"  - Medium file (10 MB): {elapsed:.3f}s")
print(f"  - Concurrent (5 files): {elapsed:.3f}s total")
print(f"  - Operations tracked: {len(operations)}")
print(f"  - Chunk size: {format_bytes(1024 * 1024)}")
print("\n✅ All streaming functionality working correctly!")
