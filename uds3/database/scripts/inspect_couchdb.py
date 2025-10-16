import sys
from pathlib import Path
import importlib
import inspect

# ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.database_api_base import DatabaseBackend

mod_name = 'database.database_api_couchdb'
mod = importlib.import_module(mod_name)
print('module:', mod_name)
found = False
for name in dir(mod):
    attr = getattr(mod, name)
    if inspect.isclass(attr):
        print('class:', name, 'bases:', [b.__name__ for b in attr.__bases__])
        try:
            if issubclass(attr, DatabaseBackend) and attr is not DatabaseBackend:
                print('-> Found candidate backend class:', name)
                found = True
        except Exception as e:
            print('issubclass check error for', name, e)

print('Found any:', found)
