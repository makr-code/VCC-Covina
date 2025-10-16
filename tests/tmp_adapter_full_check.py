import os,sys,importlib,inspect,traceback,json
print('PYTHONPATH=', sys.path[0])
base = importlib.import_module('database.database_api_base')
mods = []
import glob
for p in glob.glob(os.path.join(os.getcwd(),'database','database_api_*.py')):
    m = 'database.'+os.path.basename(p)[:-3]
    mods.append(m)
report = {}
for m in mods:
    entry = {'import':None,'classes':[]}
    try:
        mod = importlib.import_module(m)
        entry['import']='ok'
    except Exception as e:
        entry['import']='error'
        entry['error']=traceback.format_exc()
        report[m]=entry
        continue
    # find classes defined in module that subclass base classes
    for name, cls in inspect.getmembers(mod, inspect.isclass):
        try:
            if cls.__module__!=mod.__name__:
                continue
        except Exception:
            continue
        kind = None
        try:
            if issubclass(cls, base.VectorDatabaseBackend):
                kind='vector'
            elif issubclass(cls, base.GraphDatabaseBackend):
                kind='graph'
            elif issubclass(cls, base.RelationalDatabaseBackend):
                kind='relational'
        except Exception:
            # Not related
            continue
        centry = {'name': name, 'kind': kind, 'instantiate': None}
        # try instantiate with safe minimal config
        try:
            obj = cls({'test': True})
            centry['instantiate']='ok'
        except Exception as e:
            centry['instantiate']='error'
            centry['error']=traceback.format_exc()
        entry['classes'].append(centry)
    report[m]=entry
print(json.dumps(report, indent=2))
