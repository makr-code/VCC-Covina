"""
Database API Base Classes
=========================

Base classes for database backends used in Covina.
Provides abstract interface for relational, graph, and vector databases.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class DatabaseBackend(ABC):
    """Base class for all database backends"""
    
    @abstractmethod
    def connect(self):
        """Establish connection to database"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close database connection"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if database is connected"""
        pass


class RelationalBackend(DatabaseBackend):
    """
    Base class for relational database backends (PostgreSQL, MySQL, etc.)
    """
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Any:
        """
        Execute SQL query
        
        Args:
            query: SQL query string
            params: Query parameters (tuple)
            
        Returns:
            Query results
        """
        pass
    
    @abstractmethod
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        Execute query with multiple parameter sets
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        pass
    
    @abstractmethod
    def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        """
        Fetch all results from query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        pass
    
    @abstractmethod
    def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict]:
        """
        Fetch single result from query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Result dictionary or None
        """
        pass
    
    @abstractmethod
    def commit(self):
        """Commit current transaction"""
        pass
    
    @abstractmethod
    def rollback(self):
        """Rollback current transaction"""
        pass


class GraphBackend(DatabaseBackend):
    """Base class for graph database backends (Neo4j, etc.)"""
    
    @abstractmethod
    def execute_cypher(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute Cypher query"""
        pass


class VectorBackend(DatabaseBackend):
    """Base class for vector database backends (ChromaDB, etc.)"""
    
    @abstractmethod
    def add_vectors(self, vectors: List[List[float]], metadata: List[Dict]) -> List[str]:
        """Add vectors with metadata"""
        pass
    
    @abstractmethod
    def query_vectors(self, query_vector: List[float], top_k: int = 10) -> List[Dict]:
        """Query similar vectors"""
        pass


# Alias for compatibility with existing code
VectorDatabaseBackend = VectorBackend


__all__ = [
    'DatabaseBackend',
    'RelationalBackend',
    'GraphBackend',
    'VectorBackend',
    'VectorDatabaseBackend'  # Alias
]
