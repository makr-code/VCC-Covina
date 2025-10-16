from pathlib import Path
import runpy
ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'tools' / 'add_module_var_annotations.py'
TARGETS = [
    Path('C:/VCC/Covina/uds3/uds3_core.py'),
    Path('C:/VCC/Covina/uds3/uds3_follow_up_orchestrator.py'),
    Path('C:/VCC/Covina/uds3/uds3_complete_process_integration.py'),
    Path('C:/VCC/Covina/uds3/uds3_core_geo.py'),
    Path('C:/VCC/Covina/uds3/database/database_manager.py'),
]
print('Loading module:', MODULE)
m = runpy.run_path(str(MODULE))
process_file = m.get('process_file')
if process_file is None:
    raise SystemExit('process_file not found')
for p in TARGETS:
    if not p.exists():
        print('Not found:', p)
        continue
    try:
        changed = process_file(p)
        print(f'Processed: {p} -> changed={changed}')
    except Exception as e:
        print('Error processing', p, e)
