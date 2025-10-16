import importlib
import sys
from pathlib import Path
import pytest

# Ensure repository package root is on sys.path for package imports
# parents[2] -> project root (one level above 'database' folder)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database.database_manager as db_manager_mod
importlib.reload(db_manager_mod)


class MockVectorBackend:
    def __init__(self):
        self.collections = ['existing']

    def list_collections(self):
        return self.collections

    def create_collection(self, name):
        if name in self.collections:
            return True
        self.collections.append(name)
        return True


class MockGraphBackend:
    def __init__(self):
        self.nodes = []

    def create_node(self, label, props):
        self.nodes.append((label, props))
        return True


class MockRelationalBackend:
    def __init__(self):
        self.tables = set()

    def create_table(self, name, schema):
        if name in self.tables:
            return True
        self.tables.add(name)
        return True


@pytest.fixture
def dbm():
    # Provide a minimal backend_dict that DatabaseManager expects in ctor
    cfg = {
        'vector': None,
        'graph': None,
        'relational': None,
        'file': None,
        'keyvalue': None,
        'governance': {}
    }
    dm = db_manager_mod.DatabaseManager(cfg)
    return dm


def test_create_collection_when_missing(dbm):
    dbm.vector_backend = MockVectorBackend()
    assert dbm.create_database_if_missing('vector', 'newcol') is True
    # Creating existing should be true and not duplicate
    assert dbm.create_database_if_missing('vector', 'newcol') is True


def test_create_graph_node(dbm):
    dbm.graph_backend = MockGraphBackend()
    assert dbm.create_database_if_missing('graph', 'mycollection') is True


def test_create_relational_table(dbm):
    dbm.relational_backend = MockRelationalBackend()
    assert dbm.create_database_if_missing('relational', 'mytable') is True


def test_start_all_backends_and_error_propagation(dbm):
    # Prepare two simple dummy backends: one connects, one fails
    class ConnectBackend:
        def __init__(self):
            self.connected = False
        def connect(self):
            self.connected = True
            return True
        def is_available(self):
            return True

    class FailBackend:
        def __init__(self):
            self.connected = False
        def connect(self):
            return False
        def is_available(self):
            return False

    dbm._backends_to_start['one'] = ConnectBackend()
    dbm._backends_to_start['two'] = FailBackend()

    results = dbm.start_all_backends()
    assert results.get('one') is True
    assert results.get('two') is False
    # backend 'one' should be removed from registry
    assert 'one' not in dbm._backends_to_start
    # backend 'two' stays pending
    assert 'two' in dbm._backends_to_start


def test_strict_mode_propagates_exception(dbm):
    # When strict_mode True, get_vector_backend should raise when backend missing
    dm = dbm
    dm.strict_mode = True
    dm.vector_backend = None
    import pytest as _pytest
    with _pytest.raises(RuntimeError):
        dm.get_vector_backend()


def test_verify_backends_handles_status_exception(dbm):
    class BadStatus:
        def status(self):
            raise RuntimeError('boom')
        def list_collections(self):
            raise RuntimeError('boom')

    dbm.vector_backend = BadStatus()
    status = dbm.verify_backends()
    assert 'vector' in status
    # Expect an error string recorded
    assert isinstance(status['vector'], (str, dict))
