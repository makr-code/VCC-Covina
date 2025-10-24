import requests
import time

time.sleep(1)  # Quick wait

r = requests.get('http://127.0.0.1:45679/jobs', timeout=30)
jobs = r.json()

if not jobs:
    print('\n❌ No jobs found!')
    exit(1)

latest = jobs[-1]
print(f'\n📊 Latest Job Status:')
print(f'  Job ID: {latest["job_id"][:8]}...')
print(f'  Status: {latest["status"]}')
print(f'  Files: {latest["processed_files"]}/{latest["file_count"]} ✅')
print(f'  Created: {latest["created_at"]}')
print(f'  Updated: {latest["updated_at"]}')

if latest["processed_files"] > 0:
    print(f'\n🎉 SUCCESS! {latest["processed_files"]} files processed!')
    
# Database check
print('\n📊 Checking database...')
import subprocess
result = subprocess.run(['python', 'tests/check_database_stats.py'], capture_output=True, text=True)
lines = result.stdout.split('\n')
for line in lines[:3]:  # First 3 lines (total count)
    print(f'  {line}')
