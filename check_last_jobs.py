import requests

r = requests.get('http://127.0.0.1:45679/jobs', timeout=30)
jobs = r.json()

print(f'\n📊 Last 3 Jobs:\n')
for i, job in enumerate(jobs[-3:], 1):
    print(f"{i}. Job {job['job_id'][:8]}...")
    print(f"   Status: {job['status']}")
    print(f"   Files: {job['processed_files']}/{job['file_count']}")
    print(f"   Created: {job['created_at']}\n")
