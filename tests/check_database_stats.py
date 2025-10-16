#!/usr/bin/env python3
"""Check Database Stats"""
import requests
from datetime import datetime

response = requests.get("http://127.0.0.1:45678/database/stats", timeout=30)
data = response.json()

print(f"Total Documents: {data['total_documents']}")
print(f"\nClassifications:")
for cls, count in sorted(data['classifications'].items(), key=lambda x: -x[1]):
    print(f"  {cls:20s}: {count:5d}")

print(f"\nMost Recent Documents:")
for doc in data['recent_documents'][:5]:
    dt = datetime.fromisoformat(doc['processed_at'])
    print(f"  {dt.strftime('%Y-%m-%d %H:%M:%S')} - {doc['classification']:15s} - {doc['file']}")

print(f"\nPolyglot Status:")
for db_name, db_info in data['polyglot_status'].items():
    if isinstance(db_info, dict):
        count = db_info.get('documents') or db_info.get('nodes') or db_info.get('processed_files', 0)
        print(f"  {db_name:20s}: {count:6d} items")
