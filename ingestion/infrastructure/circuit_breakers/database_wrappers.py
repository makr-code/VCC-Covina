"""
Database Circuit Breaker Wrappers

Provides circuit-breaker-wrapped database clients:
- PostgreSQLBreakerWrapper
- ChromaDBBreakerWrapper
- Neo4jBreakerWrapper

Usage:
    pg_wrapper = PostgreSQLBreakerWrapper(psycopg_connection)
    result = pg_wrapper.execute_query("SELECT * FROM documents")
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from ingestion.infrastructure.circuit_breakers.circuit_breaker import CircuitBreaker


class PostgreSQLBreakerWrapper:
    """PostgreSQL wrapper with circuit breaker protection."""
    
    def __init__(self, connection: Any, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.connection = connection
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query with circuit breaker protection."""
        @self.breaker.call
        def _execute():
            cursor = self.connection.cursor()
            cursor.execute(query, params or {})
            if cursor.description:
                cols = [desc[0] for desc in cursor.description]
                return [dict(zip(cols, row)) for row in cursor.fetchall()]
            return []
        
        return _execute()
    
    @property
    def state(self):
        return self.breaker.state


class ChromaDBBreakerWrapper:
    """ChromaDB wrapper with circuit breaker protection."""
    
    def __init__(self, client: Any, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.client = client
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    def query(self, collection_name: str, query_texts: List[str], n_results: int = 10) -> Dict[str, Any]:
        """Query collection with circuit breaker protection."""
        @self.breaker.call
        def _query():
            collection = self.client.get_collection(collection_name)
            return collection.query(query_texts=query_texts, n_results=n_results)
        
        return _query()
    
    def add(self, collection_name: str, documents: List[str], metadatas: List[Dict], ids: List[str]) -> None:
        """Add documents with circuit breaker protection."""
        @self.breaker.call
        def _add():
            collection = self.client.get_collection(collection_name)
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
        
        _add()
    
    @property
    def state(self):
        return self.breaker.state


class Neo4jBreakerWrapper:
    """Neo4j wrapper with circuit breaker protection."""
    
    def __init__(self, driver: Any, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.driver = driver
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    def run_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute Cypher query with circuit breaker protection."""
        @self.breaker.call
        def _run():
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        
        return _run()
    
    @property
    def state(self):
        return self.breaker.state
