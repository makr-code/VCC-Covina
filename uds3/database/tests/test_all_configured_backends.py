import unittest
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Apply import guard to patch environment issues (must be before adapter imports)
try:
    import tests.test_import_guard as _import_guard
    _ = _import_guard.patched
except Exception:
    # best-effort; if this fails, proceed — tests will still report import errors
    pass

from database import config as cfg_module
from database.database_manager import DatabaseManager

MODULE_MAP = {
    'chromadb': 'database.database_api_chromadb',
    'neo4j': 'database.database_api_neo4j',
    'postgresql': 'database.database_api_postgresql',
    'couchdb': 'database.database_api_couchdb',
    'sqlite': 'database.database_api_sqlite',
    'redis': 'database.database_api_redis',
    'pinecone': 'database.database_api_pinecone',
    'weaviate': 'database.database_api_weaviate',
    'arangodb': 'database.database_api_arangodb',
    'hugegraph': 'database.database_api_hugegraph',
    'mongodb': 'database.database_api_mongodb'
}

class TestConfiguredBackends(unittest.TestCase):
    def test_server_config_backends_connect(self):
        """Instantiate and attempt to connect adapters listed in server_config.json (non-fatal)."""
        # server_config.json lives in the database folder (one level up from tests)
        DB_DIR = Path(__file__).resolve().parents[1]
        scf = DB_DIR / 'server_config.json'
        self.assertTrue(scf.exists(), f'server_config.json not found at {scf}')

        data = json.loads(scf.read_text())
        # find the DatabaseAPIServer section
        backends = None
        for entry in data:
            if entry.get('type') == 'DatabaseAPIServer':
                backends = entry.get('backends', {})
                break
        self.assertIsNotNone(backends, 'No DatabaseAPIServer entry in server_config.json')

        results = {}
        for key, conf in backends.items():
            backend_name = conf.get('backend') or key
            module_path = MODULE_MAP.get(backend_name)
            if not module_path:
                # Unknown backend: skip but note
                results[key] = 'skipped'
                continue
            try:
                mod = __import__(module_path, fromlist=['*'])
            except Exception as e:
                results[key] = f'import_error: {e}'
                continue

            # Resolve backend class / factory
            BackendClass = None
            try:
                # Prefer an explicit getter
                backend_cls_getter = getattr(mod, 'get_backend_class', None)
                if callable(backend_cls_getter):
                    BackendClass = backend_cls_getter()
                else:
                    # Fallback: find any concrete subclass of DatabaseBackend exported by the module
                    from database.database_api_base import DatabaseBackend as _DatabaseBackend
                    import inspect
                    for name in dir(mod):
                        attr = getattr(mod, name)
                        if inspect.isclass(attr) and issubclass(attr, _DatabaseBackend) and attr is not _DatabaseBackend:
                            # make sure it's not abstract
                            if not inspect.isabstract(attr):
                                BackendClass = attr
                                break
            except Exception:
                BackendClass = None

            if BackendClass is None:
                results[key] = 'no_backend_class'
                continue

            # Build a minimal config for constructor
            conf_for_ctor = {}
            for k in ('host', 'port', 'username', 'password', 'database', 'db_path', 'path', 'server_url', 'index_name'):
                if k in conf:
                    conf_for_ctor[k] = conf[k]

            # attempt instantiation and connect
            try:
                try:
                    inst = BackendClass(conf_for_ctor)
                except TypeError:
                    inst = BackendClass()
            except Exception as e:
                results[key] = f'instantiation_error: {e}'
                continue

            try:
                ok = inst.connect() if hasattr(inst, 'connect') else False
                results[key] = bool(ok)
            except Exception as e:
                results[key] = f'connect_error: {e}'
            finally:
                # make a best-effort disconnect to release resources (drivers, sessions)
                try:
                    if hasattr(inst, 'disconnect'):
                        inst.disconnect()
                except Exception:
                    pass

        # At least ensure results is populated and contains booleans or strings
        self.assertIsInstance(results, dict)
        # store results for human inspection
        print('\nBackend connect results:', results)

    def test_config_py_backends_start_all(self):
        """Construct DatabaseManager from config.py and call start_all_backends; ensure safe execution."""
        backend_dict = cfg_module.get_database_backend_dict()
        mgr = DatabaseManager(backend_dict)
        # call start_all_backends and ensure it returns a dict
        results = mgr.start_all_backends()
        self.assertIsInstance(results, dict)
        # each result value must be boolean
        for k, v in results.items():
            self.assertIsInstance(v, bool)
        print('\nstart_all_backends results:', results)
        # cleanup: stop all started backends to close drivers/sessions
        try:
            mgr.stop_all_backends()
        except Exception:
            pass

if __name__ == '__main__':
    unittest.main()
