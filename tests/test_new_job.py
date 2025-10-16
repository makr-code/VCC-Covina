#!/usr/bin/env python3
"""Starte neuen Upload-Job zum Testen der verbesserten Error-Behandlung"""
import requests
import time

def test_new_upload_job():
    print('🔧 Starte neuen Upload-Job zum Testen der Error-Behandlung')
    print('=' * 60)

    try:
        # Starte neuen Upload-Job  
        test_data = {
            'directory_path': 'Y:/data/00_bund_gesetze_auswahl',
            'chunk_size': 5  # 5 Dateien pro Chunk
        }
        
        response = requests.post(
            'http://127.0.0.1:8001/upload/directory', 
            data=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data.get('job_id')
            file_count = job_data.get('file_count')
            print(f'✅ Neuer Job gestartet: {job_id}')
            print(f'📊 Dateien: {file_count}')
            
            # Warte 10 Sekunden damit Processing läuft
            print('⏳ Warte 10 Sekunden für Processing...')
            time.sleep(10)
            
            print('✅ Job sollte nun im Processing sein')
            print('📋 Überprüfe Server-Logs für verbesserte Error-Ausgaben')
            
        else:
            print(f'❌ Job Start fehlgeschlagen: {response.status_code}')
            print(response.text)
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    test_new_upload_job()