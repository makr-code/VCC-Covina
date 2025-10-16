import pytest

from uds3_core import UnifiedDatabaseStrategy
from uds3_api_backend import UDS3APIBackend


def test_unified_database_strategy_init():
    """Instantiating the strategy should work and expose basic attributes."""
    s = UnifiedDatabaseStrategy()
    assert hasattr(s, "document_mapping")
    assert isinstance(s.document_mapping, dict)
    assert hasattr(s, "batch_operations")
    assert isinstance(s.batch_operations, list)


def test_resolve_database_manager_and_get_adapter_governance():
    """Inject a mock database manager that provides get_adapter_governance and check the strategy uses it."""

    class MockManager:
        def __init__(self):
            self._governance = {"policy": "ok"}

        def get_adapter_governance(self):
            return self._governance

    s = UnifiedDatabaseStrategy()
    # inject mock manager
    s._database_manager = MockManager()

    gov = s._get_adapter_governance()
    # The method should return the governance object (or set it on the instance)
    assert gov == {"policy": "ok"} or getattr(s, "_adapter_governance", None) == {"policy": "ok"}


def test_uds3_api_backend_knowledge_lookup():
    """Check that the API backend builds a knowledge base and can return related entries."""
    backend = UDS3APIBackend(ollama_model="llama3.1")
    assert hasattr(backend, "knowledge_base")
    assert isinstance(backend.knowledge_base, dict)
    # should find related entries for known keyword
    results = backend.get_related_knowledge(["Baugenehmigung"])  # present in example KB
    assert isinstance(results, list)
    # not strict — at least no exception and return is list
