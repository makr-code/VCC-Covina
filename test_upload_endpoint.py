#!/usr/bin/env python3
"""
Quick test for the new /ingestion/upload/files endpoint.
Creates a small test file and uploads it via multipart.
"""
import tempfile
import requests
from pathlib import Path

# Create test file
test_file = Path(tempfile.gettempdir()) / "test_upload.txt"
test_file.write_text("Dies ist ein Test-Dokument für den Upload-Endpoint.\n\nSpaCy sollte dies extrahieren können.")

print(f"[TEST] Created test file: {test_file} ({test_file.stat().st_size} bytes)")

# Upload to endpoint
url = "http://127.0.0.1:45692/ingestion/upload/files"
with test_file.open("rb") as f:
    files = {"files": (test_file.name, f, "text/plain")}
    response = requests.post(url, files=files, timeout=30)

print(f"\n[RESULT] Status: {response.status_code}")
print(f"[RESULT] Response: {response.json()}")

# Cleanup
test_file.unlink()
print(f"\n[CLEANUP] Test file deleted")
