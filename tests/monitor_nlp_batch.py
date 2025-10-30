"""
Phase L6A: Live-Monitoring für NLP-Batch-Lauf
Zeigt den aktuellen Fortschritt der JSONL-Extraktion an.
"""

import os
import time
import json
from pathlib import Path

def monitor_jsonl_progress(jsonl_path: str, check_interval: int = 10):
    """Überwacht die JSONL-Datei und zeigt den Fortschritt alle N Sekunden an."""
    if not os.path.exists(jsonl_path):
        print(f"[MONITOR] Waiting for {jsonl_path} to be created...")
        while not os.path.exists(jsonl_path):
            time.sleep(check_interval)
    
    print(f"[MONITOR] Monitoring: {jsonl_path}")
    print(f"[MONITOR] Press Ctrl+C to stop monitoring\n")
    
    last_count = 0
    start_time = time.time()
    
    try:
        while True:
            if os.path.exists(jsonl_path):
                with open(jsonl_path, encoding="utf-8") as f:
                    count = sum(1 for _ in f)
                
                if count > last_count:
                    elapsed = time.time() - start_time
                    rate = count / elapsed if elapsed > 0 else 0
                    eta_seconds = (3618 - count) / rate if rate > 0 else 0
                    eta_minutes = eta_seconds / 60
                    
                    print(f"[MONITOR] Progress: {count:4} files | Rate: {rate:.2f} files/sec | ETA: {eta_minutes:.1f} min")
                    last_count = count
            
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print(f"\n[MONITOR] Stopped. Total processed: {last_count} files")

if __name__ == "__main__":
    jsonl_path = os.environ.get("NLP_OUTPUT_JSONL", "data/nlp/entities_full.jsonl")
    check_interval = int(os.environ.get("MONITOR_INTERVAL", "10"))
    monitor_jsonl_progress(jsonl_path, check_interval)
