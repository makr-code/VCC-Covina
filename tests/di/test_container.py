import pytest
from ingestion.di.container import DIContainer, INeo4jWrapper, IConfigLoader, reset_container


class MockNeo4jWrapper:
    def neo4j_session(self):
        return None
    
    def run_cypher(self, query, params):
        return []


class MockConfigLoader:
    def load_file(self, path):
        return {}
    
    def load_and_merge(self, paths):
        return {}
    
    def validate(self, config):
        pass


def test_register_and_resolve():
    container = DIContainer()
    container.register(INeo4jWrapper, MockNeo4jWrapper)
    
    wrapper = container.resolve(INeo4jWrapper)
    assert isinstance(wrapper, MockNeo4jWrapper)


def test_singleton_mode():
    container = DIContainer()
    container.register(INeo4jWrapper, MockNeo4jWrapper, singleton=True)
    
    wrapper1 = container.resolve(INeo4jWrapper)
    wrapper2 = container.resolve(INeo4jWrapper)
    
    assert wrapper1 is wrapper2  # Same instance


def test_non_singleton_mode():
    container = DIContainer()
    container.register(INeo4jWrapper, MockNeo4jWrapper, singleton=False)
    
    wrapper1 = container.resolve(INeo4jWrapper)
    wrapper2 = container.resolve(INeo4jWrapper)
    
    assert wrapper1 is not wrapper2  # Different instances


def test_resolve_unregistered():
    container = DIContainer()
    
    with pytest.raises(KeyError):
        container.resolve(INeo4jWrapper)


def test_multiple_interfaces():
    container = DIContainer()
    container.register(INeo4jWrapper, MockNeo4jWrapper)
    container.register(IConfigLoader, MockConfigLoader)
    
    wrapper = container.resolve(INeo4jWrapper)
    loader = container.resolve(IConfigLoader)
    
    assert isinstance(wrapper, MockNeo4jWrapper)
    assert isinstance(loader, MockConfigLoader)


def test_clear():
    container = DIContainer()
    container.register(INeo4jWrapper, MockNeo4jWrapper, singleton=True)
    container.resolve(INeo4jWrapper)  # Create singleton
    
    container.clear()
    
    with pytest.raises(KeyError):
        container.resolve(INeo4jWrapper)


def test_global_container():
    from ingestion.di.container import get_container
    
    reset_container()  # Clean slate
    
    container = get_container()
    container.register(INeo4jWrapper, MockNeo4jWrapper)
    
    # Get container again - should be same instance
    container2 = get_container()
    assert container is container2
    
    # Resolve should work
    wrapper = container2.resolve(INeo4jWrapper)
    assert isinstance(wrapper, MockNeo4jWrapper)
    
    reset_container()  # Clean up
