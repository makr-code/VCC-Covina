"""
Monitor CouchDB document count during sync.
Refreshes every 10 seconds to show progress.
"""

import requests
import time
from datetime import datetime

COUCH_URL = "http://192.168.178.94:32770/covina"
TARGET_DOCS = 168454
REFRESH_INTERVAL = 10  # seconds

print("=" * 70)
print("COUCHDB SYNC MONITOR")
print("=" * 70)
print(f"Target: {TARGET_DOCS:,} documents")
print(f"Refresh: Every {REFRESH_INTERVAL} seconds")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)
print("\nPress Ctrl+C to stop monitoring\n")

start_time = time.time()
last_count = 0
last_time = start_time

try:
    while True:
        try:
            response = requests.get(COUCH_URL, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                doc_count = data.get('doc_count', 0)
                
                # Calculate progress
                progress_pct = (doc_count / TARGET_DOCS * 100) if TARGET_DOCS > 0 else 0
                elapsed = time.time() - start_time
                
                # Calculate rate (docs/sec)
                current_time = time.time()
                time_delta = current_time - last_time
                docs_delta = doc_count - last_count
                rate = docs_delta / time_delta if time_delta > 0 else 0
                
                # Estimate time remaining
                remaining_docs = TARGET_DOCS - doc_count
                eta_seconds = (remaining_docs / rate) if rate > 0 else 0
                eta_minutes = eta_seconds / 60
                
                # Display
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] Docs: {doc_count:,}/{TARGET_DOCS:,} ({progress_pct:.1f}%) | "
                      f"Rate: {rate:.1f} docs/sec | ETA: {eta_minutes:.1f} min")
                
                # Update for next iteration
                last_count = doc_count
                last_time = current_time
                
                # Check if complete
                if doc_count >= TARGET_DOCS:
                    print("\n" + "=" * 70)
                    print("✅ SYNC COMPLETE!")
                    print(f"Total time: {elapsed/60:.1f} minutes")
                    print("=" * 70)
                    break
                    
            elif response.status_code == 404:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Database 'covina' not yet created...")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection error: {e}")
        
        time.sleep(REFRESH_INTERVAL)
        
except KeyboardInterrupt:
    print("\n\n" + "=" * 70)
    print("MONITORING STOPPED")
    print("=" * 70)
    elapsed = time.time() - start_time
    print(f"Elapsed: {elapsed/60:.1f} minutes")
    print(f"Last count: {last_count:,} documents")
