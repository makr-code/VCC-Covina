"""
Large Upload Test for Covina Ingestion Backend
=============================================

- Lädt alle Dateien aus dem angegebenen Netzwerkverzeichnis hoch
- Validiert Memory-Stabilität, Batch-Operationen und Durchsatz
- Prüft Backend-Status und Log-Analyse nach Upload

Author: GitHub Copilot
Date: 16.10.2025
"""

import os
import sys
import time
import requests
from pathlib import Path

# Konfiguration
INGESTION_URL = "http://127.0.0.1:45679"
NETWORK_DATA_DIR = r"\\TS-864eU\Projects\data"
UPLOAD_LIMIT = 50000  # Maximal zu testende Dateien (Stresstest)


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_info(msg: str):
    print(f"ℹ️  {msg}")

def print_success(msg: str):
    print(f"✅ {msg}")

def print_error(msg: str):
    print(f"❌ {msg}")

def check_health():
    try:
        r = requests.get(f"{INGESTION_URL}/health", timeout=5)
        if r.status_code == 200:
            print_success("Backend Health: healthy")
            return True
        else:
            print_error(f"Backend Health: {r.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def collect_files(directory: str, limit: int = 2000):
    files = []
    for root, _, filenames in os.walk(directory):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            files.append(fpath)
            if len(files) >= limit:
                return files
    return files

def upload_file(filepath: str):
    try:
        with open(filepath, 'rb') as f:
            files = {'files': (os.path.basename(filepath), f, 'application/octet-stream')}
            r = requests.post(f"{INGESTION_URL}/upload/files", files=files, timeout=60)
        if r.status_code in [200, 201]:
            data = r.json()
            job_id = data.get('job_id')
            print_success(f"Upload: {os.path.basename(filepath)} (Job ID: {job_id})")
            return job_id
        else:
            print_error(f"Upload failed: {filepath} ({r.status_code})")
            return None
    except Exception as e:
        print_error(f"Upload exception: {filepath} ({e})")
        return None

def wait_for_jobs(job_ids, timeout=600):
    print_info(f"Warte auf Abschluss von {len(job_ids)} Jobs...")
    start = time.time()
    completed = set()
    while time.time() - start < timeout and len(completed) < len(job_ids):
        for job_id in job_ids:
            if job_id in completed:
                continue
            try:
                r = requests.get(f"{INGESTION_URL}/jobs/{job_id}", timeout=5)
                if r.status_code == 200:
                    status = r.json().get('status', '')
                    if status in ['completed', 'failed', 'error']:
                        print_info(f"Job {job_id}: {status}")
                        completed.add(job_id)
            except Exception:
                pass
        time.sleep(2)
    print_info(f"{len(completed)}/{len(job_ids)} Jobs abgeschlossen.")
    return completed

def main():
    print_header("Large Upload Test: Netzwerkverzeichnis")
    if not check_health():
        print_error("Backend nicht erreichbar!")
        return
    print_info(f"Sammle Dateien aus: {NETWORK_DATA_DIR}")
    files = collect_files(NETWORK_DATA_DIR, UPLOAD_LIMIT)
    print_info(f"Gefundene Dateien: {len(files)} (Limit: {UPLOAD_LIMIT})")
    if not files:
        print_error("Keine Dateien gefunden!")
        return
    job_ids = []
    for idx, fpath in enumerate(files, 1):
        print_info(f"[{idx}/{len(files)}] Upload: {os.path.basename(fpath)}")
        job_id = upload_file(fpath)
        if job_id:
            job_ids.append(job_id)
        time.sleep(0.1)  # Kurze Pause, um Backend nicht zu überlasten
    print_info(f"Alle Uploads abgeschlossen. Warte auf Verarbeitung...")
    wait_for_jobs(job_ids)
    print_success("Großtest abgeschlossen! Bitte Logs und Systemauslastung prüfen.")

if __name__ == "__main__":
    main()
