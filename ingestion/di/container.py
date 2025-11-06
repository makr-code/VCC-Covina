"""
Dependency Injection Container with Protocol Interfaces

Provides:
- Protocol interfaces (INeo4jWrapper, IConfigLoader, IMultiHopReasoner)
- DI Container with register/resolve pattern
- Optional singleton scope

Usage:
    container = DIContainer()
    container.register(INeo4jWrapper, UDS3RelationsCore, singleton=True)
    wrapper = container.resolve(INeo4jWrapper)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol, Type, TypeVar


# ---------- Protocol Interfaces ----------

class INeo4jWrapper(Protocol):
    """Protocol for Neo4j graph database wrapper."""
    
    def neo4j_session(self):
        """Return a Neo4j session context manager."""
        ...
    
    def run_cypher(self, query: str, params: Dict[str, Any]) -> Any:
        """Execute Cypher query and return results."""
        ...


class IConfigLoader(Protocol):
    """Protocol for configuration loader."""
    
    def load_file(self, path: str) -> Dict[str, Any]:
        """Load a single config file."""
        ...
    
    def load_and_merge(self, paths: list[str]) -> Dict[str, Any]:
        """Load and merge multiple config files."""
        ...
    
    def validate(self, config: Dict[str, Any]) -> None:
        """Validate config against schema."""
        ...


class IMultiHopReasoner(Protocol):
    """Protocol for multi-hop reasoning over knowledge graph."""
    
    def find_path(self, source_id: str, target_id: str, max_hops: int = 5) -> Optional[list[str]]:
        """Find path between two nodes."""
        ...
    
    def find_authority_for_concept(self, concept_id: str) -> Optional[str]:
        """Find authority responsible for a concept."""
        ...
    
    def explain_relationship(self, a_id: str, b_id: str, max_hops: int = 5) -> Dict[str, Any]:
        """Explain relationship between two nodes."""
        ...


# ---------- DI Container ----------

T = TypeVar('T')


class DIContainer:
    """Dependency Injection container with registration and resolution."""
    
    def __init__(self):
        self._registrations: Dict[Type, tuple[Callable, bool]] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register(self, interface: Type[T], implementation: Callable[..., T], singleton: bool = False) -> None:
        """Register an implementation for an interface.
        
        Args:
            interface: Protocol or abstract class
            implementation: Concrete class or factory function
            singleton: If True, return same instance on every resolve
        """
        self._registrations[interface] = (implementation, singleton)
    
    def resolve(self, interface: Type[T], *args, **kwargs) -> T:
        """Resolve an implementation for an interface.
        
        Args:
            interface: Protocol or abstract class to resolve
            *args, **kwargs: Arguments to pass to implementation constructor
            
        Returns:
            Instance of implementation
            
        Raises:
            KeyError: If interface is not registered
        """
        if interface not in self._registrations:
            raise KeyError(f"No registration found for {interface}")
        
        implementation, is_singleton = self._registrations[interface]
        
        if is_singleton:
            if interface not in self._singletons:
                self._singletons[interface] = implementation(*args, **kwargs)
            return self._singletons[interface]
        
        return implementation(*args, **kwargs)
    
    def clear(self) -> None:
        """Clear all registrations and singletons."""
        self._registrations.clear()
        self._singletons.clear()


# ---------- Global Container ----------

_global_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get global DI container (creates if not exists)."""
    global _global_container
    if _global_container is None:
        _global_container = DIContainer()
    return _global_container


def reset_container() -> None:
    """Reset global DI container (useful for tests)."""
    global _global_container
    if _global_container:
        _global_container.clear()
    _global_container = None
