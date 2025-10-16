"""
UDS3 Vector Database Filter Module

Filter-Implementierung für Vector Database (ChromaDB/Pinecone) Queries:
- Similarity Search mit Embeddings
- Metadata Filtering
- Collection-basierte Queries
- Kombinierte Queries (Similarity + Metadata)

Autor: UDS3 Team
Datum: 1. Oktober 2025
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import logging
from datetime import datetime

try:
    from uds3_query_filters import (
        BaseFilter,
        FilterOperator,
        FilterCondition,
        QueryResult,
        SortOrder,
        LogicalOperator,
    )
    BASE_FILTER_AVAILABLE = True
except ImportError:
    BASE_FILTER_AVAILABLE = False
    print("Warning: BaseFilter not available")

logger = logging.getLogger(__name__)


# ============================================================================
# VECTOR-SPECIFIC DATACLASSES
# ============================================================================


@dataclass
class SimilarityQuery:
    """Similarity Search Query Configuration"""
    query_embedding: List[float]
    threshold: float = 0.7
    top_k: int = 10
    metric: str = "cosine"  # "cosine", "l2", "ip" (inner product)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict"""
        return {
            "query_embedding": self.query_embedding,
            "threshold": self.threshold,
            "top_k": self.top_k,
            "metric": self.metric
        }


@dataclass
class VectorQueryResult(QueryResult):
    """Extended QueryResult mit Vector-spezifischen Feldern"""
    distances: Optional[List[float]] = None
    similarities: Optional[List[float]] = None
    collection: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dict"""
        base = super().to_dict()
        base.update({
            "distances": self.distances,
            "similarities": self.similarities,
            "collection": self.collection
        })
        return base


# ============================================================================
# VECTORFILTER CLASS
# ============================================================================


class VectorFilter(BaseFilter):
    """
    Filter für Vector Database Queries (ChromaDB/Pinecone)
    
    Features:
    - Similarity Search mit query embeddings
    - Metadata filtering
    - Collection filtering
    - Combined queries (similarity + metadata)
    
    Example:
        ```python
        filter = VectorFilter(backend)
            .by_similarity(embedding, threshold=0.8, top_k=5)
            .by_metadata("status", FilterOperator.EQ, "active")
            .by_collection("documents")
            .execute()
        ```
    """
    
    def __init__(self, backend: Any = None, collection_name: str = "default"):
        """
        Initialisiert VectorFilter
        
        Args:
            backend: Vector database backend (ChromaDB client)
            collection_name: Default collection name
        """
        super().__init__(backend)
        self.collection_name = collection_name
        self.similarity_query: Optional[SimilarityQuery] = None
        self.metadata_filters: List[FilterCondition] = []
        self.collection_filters: List[str] = []
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # SIMILARITY SEARCH
    # ========================================================================
    
    def by_similarity(
        self,
        query_embedding: List[float],
        threshold: float = 0.7,
        top_k: int = 10,
        metric: str = "cosine"
    ) -> 'VectorFilter':
        """
        Fügt Similarity Search hinzu
        
        Args:
            query_embedding: Query embedding vector
            threshold: Minimum similarity threshold (0.0-1.0)
            top_k: Number of results to return
            metric: Distance metric ("cosine", "l2", "ip")
        
        Returns:
            Self für method chaining
        
        Example:
            ```python
            filter.by_similarity([0.1, 0.2, ...], threshold=0.8, top_k=5)
            ```
        """
        self.similarity_query = SimilarityQuery(
            query_embedding=query_embedding,
            threshold=threshold,
            top_k=top_k,
            metric=metric
        )
        
        # Update limit to match top_k
        self.limit_value = top_k
        
        self.logger.debug(
            f"Added similarity search: threshold={threshold}, top_k={top_k}, metric={metric}"
        )
        
        return self
    
    def with_embedding(
        self,
        embedding: List[float],
        min_similarity: float = 0.7
    ) -> 'VectorFilter':
        """
        Alias für by_similarity mit simplified parameters
        
        Args:
            embedding: Query embedding vector
            min_similarity: Minimum similarity (0.0-1.0)
        
        Returns:
            Self für method chaining
        """
        return self.by_similarity(
            query_embedding=embedding,
            threshold=min_similarity
        )
    
    # ========================================================================
    # METADATA FILTERING
    # ========================================================================
    
    def by_metadata(
        self,
        field: str,
        operator: Union[FilterOperator, str],
        value: Any = None
    ) -> 'VectorFilter':
        """
        Fügt Metadata Filter hinzu
        
        Args:
            field: Metadata field name
            operator: Filter operator (EQ, NE, GT, LT, etc.)
            value: Filter value
        
        Returns:
            Self für method chaining
        
        Example:
            ```python
            filter.by_metadata("status", FilterOperator.EQ, "active")
            filter.by_metadata("priority", FilterOperator.GT, 5)
            ```
        """
        # Convert string to FilterOperator if needed
        if isinstance(operator, str):
            operator_map = {
                "==": FilterOperator.EQ,
                "!=": FilterOperator.NE,
                ">": FilterOperator.GT,
                "<": FilterOperator.LT,
                ">=": FilterOperator.GTE,
                "<=": FilterOperator.LTE,
                "in": FilterOperator.IN,
                "not_in": FilterOperator.NOT_IN,
                "contains": FilterOperator.CONTAINS,
            }
            operator = operator_map.get(operator, FilterOperator.EQ)
        
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value,
            logical_op=LogicalOperator.AND
        )
        
        self.metadata_filters.append(condition)
        self.conditions.append(condition)
        
        self.logger.debug(f"Added metadata filter: {field} {operator.value} {value}")
        
        return self
    
    def where_metadata(
        self,
        field: str,
        operator: Union[FilterOperator, str],
        value: Any = None
    ) -> 'VectorFilter':
        """Alias für by_metadata"""
        return self.by_metadata(field, operator, value)
    
    # ========================================================================
    # COLLECTION FILTERING
    # ========================================================================
    
    def by_collection(self, collection_name: str) -> 'VectorFilter':
        """
        Setzt die Collection für die Query
        
        Args:
            collection_name: Name der Collection
        
        Returns:
            Self für method chaining
        
        Example:
            ```python
            filter.by_collection("documents")
            ```
        """
        self.collection_name = collection_name
        self.collection_filters.append(collection_name)
        
        self.logger.debug(f"Set collection: {collection_name}")
        
        return self
    
    def in_collection(self, collection_name: str) -> 'VectorFilter':
        """Alias für by_collection"""
        return self.by_collection(collection_name)
    
    # ========================================================================
    # QUERY EXECUTION
    # ========================================================================
    
    def execute(self) -> VectorQueryResult:
        """
        Führt die Vector Query aus
        
        Returns:
            VectorQueryResult mit results, distances, similarities
        
        Raises:
            ValueError: Wenn backend nicht verfügbar
        """
        start_time = datetime.now()
        
        if not self.backend:
            return VectorQueryResult(
                success=False,
                results=[],
                database="vector",
                errors=["No backend available"]
            )
        
        try:
            # Build query
            query = self.to_query()
            
            # Execute query gegen backend
            if hasattr(self.backend, 'query_collection'):
                # ChromaDB-style query
                raw_results = self.backend.query_collection(
                    collection_name=self.collection_name,
                    query_embeddings=query.get("query_embeddings"),
                    n_results=query.get("n_results", 10),
                    where=query.get("where"),
                    include=["documents", "metadatas", "distances"]
                )
                
                # Parse results
                results = self._parse_chromadb_results(raw_results)
                distances = raw_results.get("distances", [[]])[0] if raw_results.get("distances") else None
                
                # Convert distances to similarities (for cosine: similarity = 1 - distance)
                similarities = None
                if distances and self.similarity_query:
                    if self.similarity_query.metric == "cosine":
                        similarities = [1.0 - d for d in distances]
                    elif self.similarity_query.metric == "ip":
                        similarities = distances  # Inner product is already similarity
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return VectorQueryResult(
                    success=True,
                    results=results,
                    total_count=len(results),
                    has_more=False,
                    query_time_ms=execution_time,
                    database="vector",
                    distances=distances,
                    similarities=similarities,
                    collection=self.collection_name
                )
            
            elif hasattr(self.backend, 'query'):
                # Alternative query method
                raw_results = self.backend.query(**query)
                results = self._parse_results(raw_results)
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return VectorQueryResult(
                    success=True,
                    results=results,
                    total_count=len(results),
                    query_time_ms=execution_time,
                    database="vector",
                    collection=self.collection_name
                )
            
            else:
                # Fallback: Mock results
                self.logger.warning("Backend has no query method, returning empty results")
                return VectorQueryResult(
                    success=True,
                    results=[],
                    database="vector",
                    collection=self.collection_name
                )
        
        except Exception as e:
            self.logger.error(f"Vector query failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return VectorQueryResult(
                success=False,
                results=[],
                database="vector",
                errors=[str(e)],
                query_time_ms=execution_time
            )
    
    def count(self) -> int:
        """
        Zählt Anzahl der matching documents
        
        Returns:
            Anzahl der Results
        """
        if not self.backend:
            return 0
        
        try:
            if hasattr(self.backend, 'count_collection'):
                return self.backend.count_collection(
                    collection_name=self.collection_name,
                    where=self._build_where_clause()
                )
            elif hasattr(self.backend, 'count'):
                query = self.to_query()
                return self.backend.count(**query)
            else:
                # Fallback: Execute and count results
                result = self.execute()
                return len(result.results)
        
        except Exception as e:
            self.logger.error(f"Count failed: {e}")
            return 0
    
    def to_query(self) -> Dict[str, Any]:
        """
        Konvertiert Filter zu Vector DB Query Format
        
        Returns:
            Dict mit query parameters
        """
        query: Dict[str, Any] = {
            "collection_name": self.collection_name
        }
        
        # Add similarity query
        if self.similarity_query:
            query["query_embeddings"] = [self.similarity_query.query_embedding]
            query["n_results"] = self.similarity_query.top_k
        
        # Add metadata filters (where clause)
        where_clause = self._build_where_clause()
        if where_clause:
            query["where"] = where_clause
        
        # Add limit/offset
        if self.limit_value:
            query["limit"] = self.limit_value
        if self.offset_value:
            query["offset"] = self.offset_value
        
        return query
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _build_where_clause(self) -> Optional[Dict[str, Any]]:
        """
        Baut ChromaDB where clause aus metadata filters
        
        Returns:
            Where clause dict or None
        """
        if not self.metadata_filters:
            return None
        
        # Simple case: Single filter
        if len(self.metadata_filters) == 1:
            return self._condition_to_where(self.metadata_filters[0])
        
        # Multiple filters: Combine with AND
        where_clause = {
            "$and": [
                self._condition_to_where(cond)
                for cond in self.metadata_filters
            ]
        }
        
        return where_clause
    
    def _condition_to_where(self, condition: FilterCondition) -> Dict[str, Any]:
        """
        Konvertiert FilterCondition zu ChromaDB where clause
        
        Args:
            condition: FilterCondition
        
        Returns:
            Where clause dict
        """
        field = condition.field
        operator = condition.operator
        value = condition.value
        
        # Map operators to ChromaDB format
        if operator == FilterOperator.EQ:
            return {field: {"$eq": value}}
        elif operator == FilterOperator.NE:
            return {field: {"$ne": value}}
        elif operator == FilterOperator.GT:
            return {field: {"$gt": value}}
        elif operator == FilterOperator.LT:
            return {field: {"$lt": value}}
        elif operator == FilterOperator.GTE:
            return {field: {"$gte": value}}
        elif operator == FilterOperator.LTE:
            return {field: {"$lte": value}}
        elif operator == FilterOperator.IN:
            return {field: {"$in": value}}
        elif operator == FilterOperator.NOT_IN:
            return {field: {"$nin": value}}
        elif operator == FilterOperator.CONTAINS:
            return {field: {"$contains": value}}
        else:
            # Fallback: Equality
            return {field: value}
    
    def _parse_chromadb_results(self, raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parsed ChromaDB results zu standard format
        
        Args:
            raw_results: Raw ChromaDB results
        
        Returns:
            List of document dicts
        """
        results = []
        
        # ChromaDB returns nested lists
        ids = raw_results.get("ids", [[]])[0]
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]
        
        for i, doc_id in enumerate(ids):
            result = {
                "id": doc_id,
                "document": documents[i] if i < len(documents) else None,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else None
            }
            results.append(result)
        
        return results
    
    def _parse_results(self, raw_results: Any) -> List[Dict[str, Any]]:
        """
        Generic result parser
        
        Args:
            raw_results: Raw results from backend
        
        Returns:
            List of document dicts
        """
        if isinstance(raw_results, list):
            return raw_results
        elif isinstance(raw_results, dict):
            return raw_results.get("results", [])
        else:
            return []


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_vector_filter(
    backend: Any = None,
    collection_name: str = "default"
) -> VectorFilter:
    """
    Factory function für VectorFilter
    
    Args:
        backend: Vector database backend
        collection_name: Collection name
    
    Returns:
        VectorFilter instance
    """
    return VectorFilter(backend, collection_name)


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "VectorFilter",
    "SimilarityQuery",
    "VectorQueryResult",
    "create_vector_filter",
]
