#!/usr/bin/env python3
"""Quick Job Status Check"""
import requests
import json

response = requests.get("http://127.0.0.1:45679/jobs?limit=200", timeout=5)
data = response.json()

print(f"Total Jobs: {len(data)}")
print(f"Pending:    {sum(1 for j in data if j['status']=='pending')}")
print(f"Processing: {sum(1 for j in data if j['status']=='processing')}")
print(f"Completed:  {sum(1 for j in data if j['status']=='completed')}")
print(f"Failed:     {sum(1 for j in data if j['status']=='failed')}")

# Zeige älteste pending Jobs
pending = [j for j in data if j['status']=='pending']
if pending:
    print(f"\nÄlteste Pending Jobs:")
    for job in sorted(pending, key=lambda x: x['created_at'])[:5]:
        print(f"  - {job['job_id'][:8]}: {job['file_count']} files, created {job['created_at']}")
