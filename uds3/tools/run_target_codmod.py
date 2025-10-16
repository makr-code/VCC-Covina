"""Run the conservative module-level annotation codemod on a targeted file list.

This wrapper imports the functions from `tools/add_module_var_annotations.py` and
applies `process_file` to each path in TARGETS. It prints a short summary per file.
"""
from pathlib import Path
import runpy

MODULE = 'tools/add_module_var_annotations.py'
TARGETS = [
    'uds3/uds3_core.py',
    'uds3/uds3_follow_up_orchestrator.py',
    'uds3/uds3_complete_process_integration.py',
    'uds3/uds3_core_geo.py',
    'database/database_manager.py',
]

if __name__ == '__main__':
    m = runpy.run_path(MODULE)
    process_file = m.get('process_file')
    if process_file is None:
        raise SystemExit(f"Could not load process_file from {MODULE}")
    for t in TARGETS:
        p = Path(t)
        if not p.exists():
            print(f'Not found: {t}')
            continue
        try:
            changed = process_file(p)
            print(f'Processed: {t} -> changed={changed}')
        except Exception as e:
            print(f'Error processing {t}: {e}')
