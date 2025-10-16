# tmp_adapter_inst_test.py
import os, sys, importlib, inspect, traceback, json, glob
base_dir = os.path.join(os.getcwd(), 'database')
modules = ['database.' + os.path.basename(p)[:-3] for p in glob.glob(os.path.join(base_dir, 'database_api_*.py'))]
report = {}
for m in modules:
    entry = {'import': None, 'classes': []}
    try:
        mod = importlib.import_module(m)
        entry['import'] = 'ok'
    except Exception:
        entry['import'] = 'error'
        entry['error'] = traceback.format_exc()
        report[m] = entry
        continue
    # inspect for backend subclasses
    try:
        base = importlib.import_module('database.database_api_base')
    except Exception:
        entry['base_import_error'] = traceback.format_exc()
        report[m] = entry
        continue
    for name, cls in inspect.getmembers(mod, inspect.isclass):
        if getattr(cls, '__module__', None) != mod.__name__:
            continue
        try:
            if issubclass(cls, base.VectorDatabaseBackend) or issubclass(cls, base.GraphDatabaseBackend) or issubclass(cls, base.RelationalDatabaseBackend):
                cent = {'name': name, 'instantiated': None}
                try:
                    obj = cls({'test': True})
                    cent['instantiated'] = True
                except Exception:
                    cent['instantiated'] = False
                    cent['error'] = traceback.format_exc()
                entry['classes'].append(cent)
        except Exception:
            continue
    report[m] = entry
print(json.dumps(report, indent=2))
