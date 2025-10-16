import sys, traceback, importlib
print('PYTHONPATH=', sys.path[0])

results = {}
modules = []
import glob, os
base = os.path.join(os.getcwd(), 'database')
for p in glob.glob(os.path.join(base, 'database_api_*.py')):
    m = os.path.basename(p)[:-3]
    modules.append('database.'+m)

print('Found modules:', modules)

for m in modules:
    try:
        mod = importlib.import_module(m)
        results[m] = {'import': 'ok'}
    except Exception as e:
        results[m] = {'import': 'error', 'error': repr(e)}
        print('IMPORT ERROR', m)
        traceback.print_exc()

# Try to instantiate common adapter classes if present
for m in modules:
    try:
        mod = importlib.import_module(m)
        inst_results = []
        # Vector backend class name heuristics
        for clsname in ['ChromaVectorBackend','VectorBackend','ChromaHTTPVectorBackend','VectorDatabaseBackendImpl','PostGIS4DBackend','CayleyGraphBackend','ChromaHTTPVectorBackend']:
            if hasattr(mod, clsname):
                cls = getattr(mod, clsname)
                try:
                    obj = cls({'test': True})
                    inst_results.append((clsname, 'ok'))
                except Exception as e:
                    inst_results.append((clsname, 'error', repr(e)))
        results[m]['instantiate'] = inst_results
    except Exception:
        pass

import json
print(json.dumps(results, indent=2))
