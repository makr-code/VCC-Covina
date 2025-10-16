"""
Large Directory Test - 7.7 GB Upload with Progressbar Monitoring
Tests the bulk copy progressbar with real production-size data
"""
import requests
import json
import time
from datetime import datetime

def main():
    print('=' * 70)
    print('LARGE DIRECTORY TEST - 7.7 GB Upload with Progressbar')
    print('=' * 70)
    print()

    # Target directory
    test_dir = r'Y:\data\00_eu lex\LEG_DE_HTML_20250831_01_00'
    print(f'📁 Directory: {test_dir}')
    print()

    # Start upload
    print('📤 [UPLOAD] Starting directory upload...')
    start_time = time.time()

    try:
        r = requests.post('http://127.0.0.1:45679/upload/directory', 
                          data={'directory_path': test_dir},
                          timeout=30)
        
        if r.status_code != 200:
            print(f'❌ ERROR: Upload failed with status {r.status_code}')
            print(f'Response: {r.text[:500]}')
            return 1
        
        resp = r.json()
        scan_id = resp.get('scan_job_id')
        
        print(f'✅ [SUCCESS] Upload started!')
        print(f'   Scan Job ID: {scan_id}')
        print(f'   Status: {resp.get("status")}')
        print()
        
    except Exception as e:
        print(f'❌ ERROR: Request failed - {e}')
        return 1

    # Monitor progress
    print('📊 [MONITOR] Polling scan status every 5 seconds...')
    print()

    poll_count = 0
    max_polls = 300  # 25 minutes max

    while poll_count < max_polls:
        poll_count += 1
        elapsed = time.time() - start_time
        
        try:
            status_r = requests.get(f'http://127.0.0.1:45679/scan/{scan_id}', timeout=10)
            
            if status_r.status_code != 200:
                print(f'❌ [ERROR] Status check failed: {status_r.status_code}')
                break
            
            status = status_r.json()
            current_status = status.get('status', 'unknown')
            files_found = status.get('files_found', 0)
            upload_jobs = status.get('upload_jobs_created', 0)
            progress = status.get('progress_percent', 0.0)
            
            # Progress indicator
            if current_status == 'copying':
                icon = '📋'
            elif current_status == 'completed':
                icon = '✅'
            elif current_status == 'failed':
                icon = '❌'
            else:
                icon = '🔄'
            
            status_str = f'{current_status:10s}'
            progress_str = f'{progress:5.1f}%'
            files_str = f'{files_found:5d}'
            elapsed_str = f'{elapsed:6.1f}s'
            
            print(f'[{poll_count:3d}] {icon} Status: {status_str} | Progress: {progress_str} | Files: {files_str} | Elapsed: {elapsed_str}')
            
            if current_status in ['completed', 'failed']:
                print()
                print('=' * 70)
                print('🎉 SCAN COMPLETED')
                print('=' * 70)
                print(f'   Final Status: {current_status}')
                print(f'   Files Found: {files_found}')
                print(f'   Upload Jobs: {upload_jobs}')
                print(f'   Total Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)')
                print('=' * 70)
                break
            
            time.sleep(5)
            
        except Exception as e:
            print(f'❌ [ERROR] Polling failed: {e}')
            time.sleep(5)
            continue

    if poll_count >= max_polls:
        print()
        print('⏰ [TIMEOUT] Test exceeded 25 minutes - stopping monitoring')
    
    return 0

if __name__ == '__main__':
    exit(main())
