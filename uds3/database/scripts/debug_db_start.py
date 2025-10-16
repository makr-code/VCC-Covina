#!/usr/bin/env python3
"""
Debug runner to trace where DatabaseManager startup hangs.
Run from project root with PYTHONPATH set, e.g. in PowerShell:

$env:PYTHONPATH = 'C:\VVC\Covina'; python -u -m database.scripts.debug_db_start

This script prints timestamped markers before/after key steps and prints
tracebacks for exceptions. It helps identify import or connect-time blockers.
"""
from __future__ import annotations

import logging
import time
import traceback
import sys

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('debug_db_start')

def stamp(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    try:
        stamp('STEP 1: about to import database.config')
        import database.config as config
        stamp('STEP 1: imported database.config')

        stamp('STEP 2: obtaining backend dict from config.get_database_backend_dict()')
        backend_dict = config.get_database_backend_dict()
        stamp(f"STEP 2: got backend dict keys: {list(backend_dict.keys())}")

        stamp('STEP 3: about to import DatabaseManager')
        from database.database_manager import DatabaseManager
        stamp('STEP 3: imported DatabaseManager')

        stamp('STEP 4: instantiate DatabaseManager (no autostart)')
        mgr = DatabaseManager(backend_dict, autostart=False)
        stamp('STEP 4: DatabaseManager instantiated')

        stamp('STEP 5: call start_all_backends() with timeout_per_backend=5')
        try:
            results = mgr.start_all_backends(timeout_per_backend=5)
            stamp(f'STEP 5: start_all_backends returned: {results}')
        except Exception as e:
            stamp(f'STEP 5: start_all_backends raised: {e}')
            traceback.print_exc()

        stamp('STEP 6: checking availability via get_backend_status()')
        try:
            status = mgr.get_backend_status()
            stamp(f'STEP 6: backend status: {status}')
        except Exception as e:
            stamp(f'STEP 6: get_backend_status raised: {e}')
            traceback.print_exc()

    except Exception as exc:
        stamp(f'MAIN: exception during debug run: {exc}')
        traceback.print_exc()
        sys.exit(2)

    stamp('DEBUG RUN COMPLETE')

if __name__ == '__main__':
    main()
