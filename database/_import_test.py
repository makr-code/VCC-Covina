import sys
sys.path.insert(0, r'C:\VCC\Covina')
import importlib, traceback
try:
    importlib.import_module('database')
    print('PACKAGE_IMPORT_OK')
except Exception:
    traceback.print_exc()
    print('PACKAGE_IMPORT_FAILED')
