import unittest
import logging
from database.database_manager import DatabaseManager

logging.getLogger('DatabaseManager').setLevel(logging.ERROR)

class DummyBackend:
    def __init__(self, should_connect=True, available=True, raise_on_status=False):
        self._should_connect = should_connect
        self._available = available
        self._raise_on_status = raise_on_status
        self.connected = False

    def connect(self):
        if self._should_connect:
            self.connected = True
            return True
        return False

    def disconnect(self):
        self.connected = False

    def is_available(self):
        return self._available

    def status(self):
        if self._raise_on_status:
            raise RuntimeError('status failure')
        return {'ok': True}

    def get_backend_type(self):
        return 'Dummy'

class TestManagerUnit(unittest.TestCase):
    def test_start_all_backends_success_and_failure(self):
        cfg = {'vector': None, 'graph': None, 'relational': None, 'file': None, 'key_value': None, 'governance': {}}
        dm = DatabaseManager(cfg)
        dm._backends_to_start['good'] = DummyBackend(should_connect=True)
        dm._backends_to_start['bad'] = DummyBackend(should_connect=False)

        results = dm.start_all_backends()
        self.assertTrue(results['good'])
        self.assertFalse(results['bad'])
        self.assertNotIn('good', dm._backends_to_start)
        self.assertIn('bad', dm._backends_to_start)

    def test_get_vector_backend_strict_and_non_strict(self):
        cfg = {'vector': None, 'graph': None, 'relational': None, 'file': None, 'key_value': None, 'governance': {}}
        dm = DatabaseManager(cfg, strict_mode=False)
        dm.vector_backend = None
        # non-strict should return None and not raise
        self.assertIsNone(dm.get_vector_backend())

        dm_strict = DatabaseManager(cfg, strict_mode=True)
        dm_strict.vector_backend = None
        with self.assertRaises(RuntimeError):
            dm_strict.get_vector_backend()

    def test_verify_backends_propagates_status_errors(self):
        cfg = {'vector': None, 'graph': None, 'relational': None, 'file': None, 'key_value': None, 'governance': {}}
        dm = DatabaseManager(cfg)
        class Bad:
            def status(self):
                raise RuntimeError('boom')
            def list_collections(self):
                raise RuntimeError('boom')
        dm.vector_backend = Bad()
        status = dm.verify_backends()
        self.assertIn('vector', status)
        # status entry should indicate an error (string or dict with 'Fehler')
        self.assertTrue(isinstance(status['vector'], str) or 'Fehler' in str(status['vector']))

if __name__ == '__main__':
    unittest.main()
