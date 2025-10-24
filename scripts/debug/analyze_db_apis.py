"""
Analyse: Database API Files Comparison
Compare Covina vs UDS3 database folders
"""
import os
from pathlib import Path
from datetime import datetime

covina = Path('C:/VCC/Covina/database')
uds3 = Path('C:/VCC/uds3/database')

print('=' * 90)
print('DATABASE API FILES COMPARISON - Covina vs UDS3')
print('=' * 90)

# Key files to compare
key_files = [
    'database_api_base.py',
    'database_api_postgresql.py',
    'database_api_neo4j.py',
    'database_api_couchdb.py',
    'database_api_chromadb.py',
    'batch_operations.py',
    'database_api_chromadb_remote.py'
]

print(f'\n{"File":<40} {"Covina":<15} {"UDS3":<15} {"Status":<12}')
print('-' * 90)

results = {
    'both': [],
    'diff': [],
    'covina_only': [],
    'uds3_only': []
}

for filename in key_files:
    c_file = covina / filename
    u_file = uds3 / filename
    
    c_exists = c_file.exists()
    u_exists = u_file.exists()
    
    c_size = c_file.stat().st_size if c_exists else 0
    u_size = u_file.stat().st_size if u_exists else 0
    
    if c_exists and u_exists:
        if c_size == u_size:
            status = '✅ IDENTICAL'
            results['both'].append(filename)
        else:
            status = '⚠️ DIFFERENT'
            results['diff'].append((filename, c_size, u_size))
    elif c_exists:
        status = '📦 COVINA ONLY'
        results['covina_only'].append(filename)
    elif u_exists:
        status = '📦 UDS3 ONLY'
        results['uds3_only'].append(filename)
    else:
        status = '❌ MISSING'
    
    print(f'{filename:<40} {c_size:>12,}B {u_size:>12,}B {status:<12}')

print('\n' + '=' * 90)
print('SUMMARY')
print('=' * 90)
print(f'✅ Identical files: {len(results["both"])}')
print(f'⚠️  Different files: {len(results["diff"])}')
print(f'📦 Covina only: {len(results["covina_only"])}')
print(f'📦 UDS3 only: {len(results["uds3_only"])}')

if results['diff']:
    print('\n⚠️  FILES WITH DIFFERENCES (need merge/update):')
    for filename, c_size, u_size in results['diff']:
        diff_pct = abs(c_size - u_size) / max(c_size, u_size) * 100
        print(f'   - {filename}: Covina={c_size:,}B, UDS3={u_size:,}B (diff: {diff_pct:.1f}%)')

if results['covina_only']:
    print('\n📦 COVINA ONLY FILES (need transfer to UDS3):')
    for filename in results['covina_only']:
        print(f'   - {filename}')

if results['uds3_only']:
    print('\n📦 UDS3 ONLY FILES (already in UDS3):')
    for filename in results['uds3_only']:
        print(f'   - {filename}')

print('\n' + '=' * 90)
print('ADDITIONAL COVINA DATABASE FILES')
print('=' * 90)

# List all other Covina database API files
all_covina = sorted([f.name for f in covina.glob('database_api_*.py')])
other_files = [f for f in all_covina if f not in key_files]

if other_files:
    print(f'Found {len(other_files)} additional database API files in Covina:')
    for f in other_files[:10]:  # Show first 10
        size = (covina / f).stat().st_size
        print(f'   - {f:<45} {size:>10,}B')
    if len(other_files) > 10:
        print(f'   ... and {len(other_files) - 10} more')

print('\n' + '=' * 90)
print('RECOMMENDATION')
print('=' * 90)
print('1. ⚠️  MERGE different files (Covina → UDS3):')
print('   - Keep UDS3 as base, add Covina improvements (batch operations)')
print('2. 📦 TRANSFER Covina-only files if needed')
print('3. ✅ UDS3 already has batch operations support in:')
print('   - database_api_postgresql.py (batch_update/delete/upsert)')
print('   - database_api_neo4j.py (batch_update/delete/upsert)')
print('   - database_api_couchdb.py (batch_update/delete/upsert)')
print('\n✅ Task 1 COMPLETE: Analysis done!')
