"""
UDS3 Polyglot Query Module
===========================

Multi-database query coordinator for executing queries across Vector, Graph, 
Relational, and File Storage databases with intelligent result joining.

Features:
- Cross-database query coordination
- Multiple join strategies (INTERSECTION, UNION, SEQUENTIAL)
- Parallel query execution for performance
- Result merging and deduplication
- Performance tracking and optimization
- Integration with all UDS3 filter modules

Join Strategies:
- INTERSECTION: Return results present in ALL databases (AND logic)
- UNION: Return results present in ANY database (OR logic)
- SEQUENTIAL: Use results from one DB to filter the next (pipeline)

Author: UDS3 Team
Date: 2. Oktober 2025
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

# Try to import all filter modules with fallback support
try:
    from uds3_vector_filter import VectorFilter, VectorFilterResult
    VECTOR_FILTER_AVAILABLE = True
except ImportError:
    VECTOR_FILTER_AVAILABLE = False
    logger.debug("VectorFilter not available for PolyglotQuery - using fallback mode")

try:
    from uds3_graph_filter import GraphFilter, GraphFilterResult
    GRAPH_FILTER_AVAILABLE = True
except ImportError:
    GRAPH_FILTER_AVAILABLE = False
    logger.debug("GraphFilter not available for PolyglotQuery - using fallback mode")

try:
    from uds3_relational_filter import RelationalFilter, RelationalQueryResult
    RELATIONAL_FILTER_AVAILABLE = True
except ImportError:
    RELATIONAL_FILTER_AVAILABLE = False
    logger.warning("RelationalFilter not available for PolyglotQuery")

try:
    from uds3_file_storage_filter import FileStorageFilter, FileFilterResult
    FILE_STORAGE_FILTER_AVAILABLE = True
except ImportError:
    FILE_STORAGE_FILTER_AVAILABLE = False
    logger.warning("FileStorageFilter not available for PolyglotQuery")


# ============================================================================
# Enums
# ============================================================================

class JoinStrategy(Enum):
    """Strategy for joining results from multiple databases"""
    INTERSECTION = "intersection"  # AND: Results must be in ALL databases
    UNION = "union"  # OR: Results from ANY database
    SEQUENTIAL = "sequential"  # Pipeline: Use DB1 results to filter DB2, etc.


class ExecutionMode(Enum):
    """Query execution mode"""
    PARALLEL = "parallel"  # Execute all queries simultaneously
    SEQUENTIAL = "sequential"  # Execute queries one after another
    SMART = "smart"  # Choose based on join strategy


class DatabaseType(Enum):
    """Supported database types"""
    VECTOR = "vector"
    GRAPH = "graph"
    RELATIONAL = "relational"
    FILE_STORAGE = "file_storage"


# ============================================================================
# Query Context
# ============================================================================

@dataclass
class QueryContext:
    """Context for a single database query"""
    database_type: DatabaseType
    filter_instance: Any  # VectorFilter | GraphFilter | RelationalFilter | FileStorageFilter
    query_params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0  # For SEQUENTIAL: lower number executes first
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "database_type": self.database_type.value,
            "query_params": self.query_params,
            "enabled": self.enabled,
            "priority": self.priority
        }


@dataclass
class QueryResult:
    """Result from a single database query"""
    database_type: DatabaseType
    success: bool
    document_ids: Set[str]  # For result joining
    results: List[Dict[str, Any]]  # Full result objects
    count: int
    execution_time_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "database_type": self.database_type.value,
            "success": self.success,
            "document_ids": list(self.document_ids),
            "count": self.count,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class PolyglotQueryResult:
    """Final result from polyglot query execution"""
    success: bool
    join_strategy: JoinStrategy
    execution_mode: ExecutionMode
    
    # Per-database results
    database_results: Dict[DatabaseType, QueryResult]
    
    # Joined results
    joined_document_ids: Set[str]
    joined_results: List[Dict[str, Any]]
    joined_count: int
    
    # Performance metrics
    total_execution_time_ms: float
    database_execution_times: Dict[DatabaseType, float]
    
    # Metadata
    databases_queried: List[DatabaseType]
    databases_succeeded: List[DatabaseType]
    databases_failed: List[DatabaseType]
    
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "join_strategy": self.join_strategy.value,
            "execution_mode": self.execution_mode.value,
            "database_results": {
                db.value: result.to_dict() 
                for db, result in self.database_results.items()
            },
            "joined_document_ids": list(self.joined_document_ids),
            "joined_count": self.joined_count,
            "total_execution_time_ms": self.total_execution_time_ms,
            "database_execution_times": {
                db.value: time_ms 
                for db, time_ms in self.database_execution_times.items()
            },
            "databases_queried": [db.value for db in self.databases_queried],
            "databases_succeeded": [db.value for db in self.databases_succeeded],
            "databases_failed": [db.value for db in self.databases_failed],
            "error": self.error,
            "warnings": self.warnings
        }


# ============================================================================
# Query Coordinator
# ============================================================================

class PolyglotQuery:
    """
    Multi-database query coordinator.
    
    Executes queries across Vector, Graph, Relational, and File Storage databases
    with intelligent result joining strategies.
    
    Example:
        ```python
        query = PolyglotQuery(unified_strategy)
        
        # Setup queries for each database
        query.vector().by_similarity(
            embedding=my_embedding,
            threshold=0.8,
            top_k=100
        )
        
        query.graph().by_relationship(
            relationship_type="CITES",
            direction="OUTGOING"
        )
        
        query.relational().where("status", "=", "active")
        
        # Execute with INTERSECTION join (results in ALL databases)
        result = query.join_strategy(JoinStrategy.INTERSECTION).execute()
        
        print(f"Found {result.joined_count} documents in all databases")
        ```
    """
    
    def __init__(
        self,
        unified_strategy: Any,  # UnifiedDatabaseStrategy instance
        execution_mode: ExecutionMode = ExecutionMode.SMART
    ):
        """
        Initialize PolyglotQuery.
        
        Args:
            unified_strategy: UnifiedDatabaseStrategy instance
            execution_mode: Execution mode (PARALLEL, SEQUENTIAL, SMART)
        """
        self.unified_strategy = unified_strategy
        self._execution_mode = execution_mode
        self._join_strategy = JoinStrategy.INTERSECTION
        
        # Query contexts for each database
        self._contexts: Dict[DatabaseType, QueryContext] = {}
        
        # Result cache
        self._result: Optional[PolyglotQueryResult] = None
        self._executed = False
        
        # Thread safety
        self._lock = threading.Lock()
    
    # ========================================================================
    # Fluent API: Database Query Setup
    # ========================================================================
    
    def vector(self) -> 'VectorQueryBuilder':
        """
        Start vector database query.
        
        Returns:
            VectorQueryBuilder for setting up vector query
        """
        if not VECTOR_FILTER_AVAILABLE:
            logger.warning("VectorFilter not available")
            return VectorQueryBuilder(self, enabled=False)
        
        return VectorQueryBuilder(self, enabled=True)
    
    def graph(self) -> 'GraphQueryBuilder':
        """
        Start graph database query.
        
        Returns:
            GraphQueryBuilder for setting up graph query
        """
        if not GRAPH_FILTER_AVAILABLE:
            logger.warning("GraphFilter not available")
            return GraphQueryBuilder(self, enabled=False)
        
        return GraphQueryBuilder(self, enabled=True)
    
    def relational(self) -> 'RelationalQueryBuilder':
        """
        Start relational database query.
        
        Returns:
            RelationalQueryBuilder for setting up relational query
        """
        if not RELATIONAL_FILTER_AVAILABLE:
            logger.warning("RelationalFilter not available")
            return RelationalQueryBuilder(self, enabled=False)
        
        return RelationalQueryBuilder(self, enabled=True)
    
    def file_storage(self) -> 'FileStorageQueryBuilder':
        """
        Start file storage query.
        
        Returns:
            FileStorageQueryBuilder for setting up file query
        """
        if not FILE_STORAGE_FILTER_AVAILABLE:
            logger.warning("FileStorageFilter not available")
            return FileStorageQueryBuilder(self, enabled=False)
        
        return FileStorageQueryBuilder(self, enabled=True)
    
    # ========================================================================
    # Configuration Methods
    # ========================================================================
    
    def join_strategy(self, strategy: JoinStrategy) -> 'PolyglotQuery':
        """
        Set join strategy for combining results.
        
        Args:
            strategy: JoinStrategy (INTERSECTION, UNION, SEQUENTIAL)
        
        Returns:
            Self for chaining
        """
        self._join_strategy = strategy
        return self
    
    def execution_mode(self, mode: ExecutionMode) -> 'PolyglotQuery':
        """
        Set execution mode.
        
        Args:
            mode: ExecutionMode (PARALLEL, SEQUENTIAL, SMART)
        
        Returns:
            Self for chaining
        """
        self._execution_mode = mode
        return self
    
    def _add_context(self, context: QueryContext):
        """Add query context for a database (internal)"""
        with self._lock:
            self._contexts[context.database_type] = context
    
    # ========================================================================
    # Execution Methods
    # ========================================================================
    
    def execute(self) -> PolyglotQueryResult:
        """
        Execute polyglot query across all configured databases.
        
        Returns:
            PolyglotQueryResult with joined results
        """
        start_time = time.time()
        
        # Validate we have at least one query
        if not self._contexts:
            return PolyglotQueryResult(
                success=False,
                join_strategy=self._join_strategy,
                execution_mode=self._execution_mode,
                database_results={},
                joined_document_ids=set(),
                joined_results=[],
                joined_count=0,
                total_execution_time_ms=0.0,
                database_execution_times={},
                databases_queried=[],
                databases_succeeded=[],
                databases_failed=[],
                error="No database queries configured"
            )
        
        # Determine execution mode
        execution_mode = self._determine_execution_mode()
        
        # Execute queries based on mode
        if execution_mode == ExecutionMode.PARALLEL:
            database_results = self._execute_parallel()
        elif execution_mode == ExecutionMode.SEQUENTIAL:
            database_results = self._execute_sequential()
        else:
            database_results = self._execute_sequential()  # Fallback
        
        # Join results based on strategy
        joined_ids, joined_results = self._join_results(database_results)
        
        # Calculate execution time
        total_time_ms = (time.time() - start_time) * 1000
        
        # Build result
        databases_queried = list(self._contexts.keys())
        databases_succeeded = [db for db, res in database_results.items() if res.success]
        databases_failed = [db for db, res in database_results.items() if not res.success]
        
        result = PolyglotQueryResult(
            success=len(databases_succeeded) > 0,
            join_strategy=self._join_strategy,
            execution_mode=execution_mode,
            database_results=database_results,
            joined_document_ids=joined_ids,
            joined_results=joined_results,
            joined_count=len(joined_results),
            total_execution_time_ms=total_time_ms,
            database_execution_times={
                db: res.execution_time_ms 
                for db, res in database_results.items()
            },
            databases_queried=databases_queried,
            databases_succeeded=databases_succeeded,
            databases_failed=databases_failed
        )
        
        self._result = result
        self._executed = True
        
        return result
    
    def _determine_execution_mode(self) -> ExecutionMode:
        """Determine execution mode based on join strategy (SMART mode)"""
        if self._execution_mode != ExecutionMode.SMART:
            return self._execution_mode
        
        # SEQUENTIAL join requires sequential execution
        if self._join_strategy == JoinStrategy.SEQUENTIAL:
            return ExecutionMode.SEQUENTIAL
        
        # INTERSECTION can benefit from parallel execution
        # UNION definitely benefits from parallel execution
        return ExecutionMode.PARALLEL
    
    def _execute_parallel(self) -> Dict[DatabaseType, QueryResult]:
        """Execute all queries in parallel using ThreadPoolExecutor"""
        database_results = {}
        
        with ThreadPoolExecutor(max_workers=len(self._contexts)) as executor:
            # Submit all query tasks
            future_to_db = {
                executor.submit(self._execute_single_query, db, ctx): db
                for db, ctx in self._contexts.items()
                if ctx.enabled
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_db):
                db_type = future_to_db[future]
                try:
                    result = future.result()
                    database_results[db_type] = result
                except Exception as e:
                    logger.error(f"Error executing {db_type.value} query: {e}")
                    database_results[db_type] = QueryResult(
                        database_type=db_type,
                        success=False,
                        document_ids=set(),
                        results=[],
                        count=0,
                        execution_time_ms=0.0,
                        error=str(e)
                    )
        
        return database_results
    
    def _execute_sequential(self) -> Dict[DatabaseType, QueryResult]:
        """Execute queries sequentially (optionally with pipeline filtering)"""
        database_results = {}
        
        # Sort contexts by priority (for SEQUENTIAL join strategy)
        sorted_contexts = sorted(
            [(db, ctx) for db, ctx in self._contexts.items() if ctx.enabled],
            key=lambda x: x[1].priority
        )
        
        previous_ids: Optional[Set[str]] = None
        
        for db_type, context in sorted_contexts:
            # For SEQUENTIAL join, apply previous results as filter
            if self._join_strategy == JoinStrategy.SEQUENTIAL and previous_ids is not None:
                # Add document_ids filter to query params
                context.query_params["document_ids_filter"] = list(previous_ids)
            
            # Execute query
            result = self._execute_single_query(db_type, context)
            database_results[db_type] = result
            
            # Update previous_ids for next iteration
            if result.success:
                previous_ids = result.document_ids
            
            # For INTERSECTION, early termination if no results
            if self._join_strategy == JoinStrategy.INTERSECTION and not result.document_ids:
                logger.info(f"Early termination: {db_type.value} returned no results")
                # Mark remaining databases as skipped
                remaining_dbs = [db for db, _ in sorted_contexts if db not in database_results]
                for db in remaining_dbs:
                    database_results[db] = QueryResult(
                        database_type=db,
                        success=True,
                        document_ids=set(),
                        results=[],
                        count=0,
                        execution_time_ms=0.0,
                        metadata={"skipped": True, "reason": "early_termination"}
                    )
                break
        
        return database_results
    
    def _execute_single_query(
        self,
        db_type: DatabaseType,
        context: QueryContext
    ) -> QueryResult:
        """Execute a single database query"""
        start_time = time.time()
        
        try:
            # Execute based on database type
            if db_type == DatabaseType.VECTOR:
                result = self._execute_vector_query(context)
            elif db_type == DatabaseType.GRAPH:
                result = self._execute_graph_query(context)
            elif db_type == DatabaseType.RELATIONAL:
                result = self._execute_relational_query(context)
            elif db_type == DatabaseType.FILE_STORAGE:
                result = self._execute_file_storage_query(context)
            else:
                raise ValueError(f"Unknown database type: {db_type}")
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Extract document IDs from results
            document_ids = self._extract_document_ids(result, db_type)
            
            return QueryResult(
                database_type=db_type,
                success=True,
                document_ids=document_ids,
                results=result if isinstance(result, list) else result.get("results", []),
                count=len(document_ids),
                execution_time_ms=execution_time_ms
            )
        
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Error executing {db_type.value} query: {e}")
            return QueryResult(
                database_type=db_type,
                success=False,
                document_ids=set(),
                results=[],
                count=0,
                execution_time_ms=execution_time_ms,
                error=str(e)
            )
    
    def _execute_vector_query(self, context: QueryContext) -> Any:
        """Execute vector database query"""
        filter_instance = context.filter_instance
        params = context.query_params
        
        # Use VectorFilter to execute query
        result = filter_instance.search(
            query_params=params
        )
        
        return result
    
    def _execute_graph_query(self, context: QueryContext) -> Any:
        """Execute graph database query"""
        filter_instance = context.filter_instance
        params = context.query_params
        
        # Use GraphFilter to execute query
        result = filter_instance.execute()
        
        return result
    
    def _execute_relational_query(self, context: QueryContext) -> Any:
        """Execute relational database query"""
        filter_instance = context.filter_instance
        params = context.query_params
        
        # Use RelationalFilter to execute query
        result = filter_instance.execute()
        
        return result
    
    def _execute_file_storage_query(self, context: QueryContext) -> Any:
        """Execute file storage query"""
        filter_instance = context.filter_instance
        params = context.query_params
        
        # Use FileStorageFilter to execute query
        query = params.get("query")
        base_directory = params.get("base_directory", ".")
        
        result = filter_instance.search(query, base_directory)
        
        return result
    
    def _extract_document_ids(self, result: Any, db_type: DatabaseType) -> Set[str]:
        """Extract document IDs from database-specific result format"""
        document_ids = set()
        
        try:
            if isinstance(result, dict):
                # Handle dict results (common format)
                if "results" in result:
                    results_list = result["results"]
                elif "documents" in result:
                    results_list = result["documents"]
                elif "files" in result:
                    results_list = result["files"]
                else:
                    results_list = []
                
                for item in results_list:
                    if isinstance(item, dict):
                        # Try common ID fields
                        doc_id = (
                            item.get("document_id") or
                            item.get("id") or
                            item.get("file_id") or
                            item.get("_id")
                        )
                        if doc_id:
                            document_ids.add(str(doc_id))
            
            elif isinstance(result, list):
                # Handle list results
                for item in result:
                    if isinstance(item, dict):
                        doc_id = (
                            item.get("document_id") or
                            item.get("id") or
                            item.get("file_id") or
                            item.get("_id")
                        )
                        if doc_id:
                            document_ids.add(str(doc_id))
        
        except Exception as e:
            logger.error(f"Error extracting document IDs from {db_type.value}: {e}")
        
        return document_ids
    
    # ========================================================================
    # Result Joining Methods
    # ========================================================================
    
    def _join_results(
        self,
        database_results: Dict[DatabaseType, QueryResult]
    ) -> tuple[Set[str], List[Dict[str, Any]]]:
        """
        Join results from multiple databases based on join strategy.
        
        Returns:
            Tuple of (joined_document_ids, joined_full_results)
        """
        if self._join_strategy == JoinStrategy.INTERSECTION:
            return self._join_intersection(database_results)
        elif self._join_strategy == JoinStrategy.UNION:
            return self._join_union(database_results)
        elif self._join_strategy == JoinStrategy.SEQUENTIAL:
            return self._join_sequential(database_results)
        else:
            # Default to INTERSECTION
            return self._join_intersection(database_results)
    
    def _join_intersection(
        self,
        database_results: Dict[DatabaseType, QueryResult]
    ) -> tuple[Set[str], List[Dict[str, Any]]]:
        """
        INTERSECTION join: Return document IDs present in ALL databases.
        
        AND logic: doc_id must be in Vector AND Graph AND Relational AND FileStorage
        """
        # Get successful results
        successful_results = [
            res for res in database_results.values() 
            if res.success and res.document_ids
        ]
        
        if not successful_results:
            return set(), []
        
        # Start with first result's IDs
        intersection_ids = successful_results[0].document_ids.copy()
        
        # Intersect with all other results
        for result in successful_results[1:]:
            intersection_ids &= result.document_ids
        
        # Collect full result objects for intersection IDs
        joined_results = self._collect_joined_results(
            intersection_ids,
            database_results
        )
        
        return intersection_ids, joined_results
    
    def _join_union(
        self,
        database_results: Dict[DatabaseType, QueryResult]
    ) -> tuple[Set[str], List[Dict[str, Any]]]:
        """
        UNION join: Return document IDs present in ANY database.
        
        OR logic: doc_id in Vector OR Graph OR Relational OR FileStorage
        """
        # Collect all document IDs from all databases
        union_ids = set()
        
        for result in database_results.values():
            if result.success:
                union_ids |= result.document_ids
        
        # Collect full result objects for union IDs
        joined_results = self._collect_joined_results(
            union_ids,
            database_results
        )
        
        return union_ids, joined_results
    
    def _join_sequential(
        self,
        database_results: Dict[DatabaseType, QueryResult]
    ) -> tuple[Set[str], List[Dict[str, Any]]]:
        """
        SEQUENTIAL join: Use results from first DB to filter second, etc.
        
        Pipeline logic: DB1 results → filter DB2 → filter DB3 → ...
        (Already handled in _execute_sequential, just return final results)
        """
        # Get the last successful result (final stage of pipeline)
        sorted_results = sorted(
            [(db, res) for db, res in database_results.items() if res.success],
            key=lambda x: self._contexts[x[0]].priority,
            reverse=True  # Get highest priority (last executed)
        )
        
        if not sorted_results:
            return set(), []
        
        final_db, final_result = sorted_results[0]
        final_ids = final_result.document_ids
        
        # Collect full result objects
        joined_results = self._collect_joined_results(
            final_ids,
            database_results
        )
        
        return final_ids, joined_results
    
    def _collect_joined_results(
        self,
        document_ids: Set[str],
        database_results: Dict[DatabaseType, QueryResult]
    ) -> List[Dict[str, Any]]:
        """
        Collect full result objects for joined document IDs.
        
        Combines results from all databases for each document ID.
        """
        # Create a map: document_id -> combined result
        combined_results = {}
        
        for doc_id in document_ids:
            combined_result = {
                "document_id": doc_id,
                "sources": []
            }
            
            # Collect data from each database
            for db_type, query_result in database_results.items():
                if not query_result.success:
                    continue
                
                # Find this document in the database results
                for result_item in query_result.results:
                    item_id = (
                        result_item.get("document_id") or
                        result_item.get("id") or
                        result_item.get("file_id") or
                        result_item.get("_id")
                    )
                    
                    if str(item_id) == doc_id:
                        combined_result["sources"].append({
                            "database": db_type.value,
                            "data": result_item
                        })
                        break
            
            combined_results[doc_id] = combined_result
        
        return list(combined_results.values())


# ============================================================================
# Query Builders (Fluent API)
# ============================================================================

class VectorQueryBuilder:
    """Builder for vector database queries"""
    
    def __init__(self, polyglot_query: PolyglotQuery, enabled: bool = True):
        self.polyglot_query = polyglot_query
        self.enabled = enabled
        self.params = {}
    
    def by_similarity(
        self,
        embedding: List[float],
        threshold: float = 0.7,
        top_k: int = 100,
        collection_name: str = "default"
    ) -> PolyglotQuery:
        """
        Query by vector similarity.
        
        Args:
            embedding: Query embedding vector
            threshold: Minimum similarity threshold
            top_k: Number of results
            collection_name: Collection name
        
        Returns:
            PolyglotQuery for chaining
        """
        if not self.enabled:
            return self.polyglot_query
        
        self.params = {
            "embedding": embedding,
            "threshold": threshold,
            "top_k": top_k,
            "collection_name": collection_name
        }
        
        # Create VectorFilter instance
        try:
            vector_filter = self.polyglot_query.unified_strategy.create_vector_filter()
            
            context = QueryContext(
                database_type=DatabaseType.VECTOR,
                filter_instance=vector_filter,
                query_params=self.params,
                enabled=True,
                priority=1  # Default priority
            )
            
            self.polyglot_query._add_context(context)
        except Exception as e:
            logger.error(f"Error creating vector query context: {e}")
        
        return self.polyglot_query


class GraphQueryBuilder:
    """Builder for graph database queries"""
    
    def __init__(self, polyglot_query: PolyglotQuery, enabled: bool = True):
        self.polyglot_query = polyglot_query
        self.enabled = enabled
        self.params = {}
    
    def by_relationship(
        self,
        relationship_type: str,
        direction: str = "OUTGOING",
        node_id: Optional[str] = None,
        max_depth: int = 1
    ) -> PolyglotQuery:
        """
        Query by graph relationship.
        
        Args:
            relationship_type: Type of relationship (e.g., "CITES")
            direction: Direction (OUTGOING, INCOMING, BOTH)
            node_id: Starting node ID (optional)
            max_depth: Maximum traversal depth
        
        Returns:
            PolyglotQuery for chaining
        """
        if not self.enabled:
            return self.polyglot_query
        
        self.params = {
            "relationship_type": relationship_type,
            "direction": direction,
            "node_id": node_id,
            "max_depth": max_depth
        }
        
        # Create GraphFilter instance
        try:
            graph_filter = self.polyglot_query.unified_strategy.create_graph_filter()
            
            # Apply filters to graph_filter
            graph_filter.by_relationship(
                relationship_type=relationship_type,
                direction=direction
            )
            
            if max_depth:
                graph_filter.with_depth(max_depth)
            
            context = QueryContext(
                database_type=DatabaseType.GRAPH,
                filter_instance=graph_filter,
                query_params=self.params,
                enabled=True,
                priority=2  # Default priority
            )
            
            self.polyglot_query._add_context(context)
        except Exception as e:
            logger.error(f"Error creating graph query context: {e}")
        
        return self.polyglot_query


class RelationalQueryBuilder:
    """Builder for relational database queries"""
    
    def __init__(self, polyglot_query: PolyglotQuery, enabled: bool = True):
        self.polyglot_query = polyglot_query
        self.enabled = enabled
        self.params = {}
        self.filter_instance = None
    
    def from_table(self, table: str) -> 'RelationalQueryBuilder':
        """Set table name"""
        self.params["table"] = table
        return self
    
    def where(self, field: str, operator: str, value: Any) -> 'RelationalQueryBuilder':
        """Add WHERE condition"""
        if "where_conditions" not in self.params:
            self.params["where_conditions"] = []
        
        self.params["where_conditions"].append({
            "field": field,
            "operator": operator,
            "value": value
        })
        
        return self
    
    def limit(self, limit: int) -> PolyglotQuery:
        """
        Set result limit and finalize relational query.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            PolyglotQuery for chaining
        """
        if not self.enabled:
            return self.polyglot_query
        
        self.params["limit"] = limit
        
        # Create RelationalFilter instance
        try:
            relational_filter = self.polyglot_query.unified_strategy.create_relational_filter()
            
            # Apply filters
            table = self.params.get("table", "documents_metadata")
            relational_filter.from_table(table)
            
            # Apply WHERE conditions
            for condition in self.params.get("where_conditions", []):
                relational_filter.where(
                    condition["field"],
                    condition["operator"],
                    condition["value"]
                )
            
            # Apply LIMIT
            if "limit" in self.params:
                relational_filter.limit(self.params["limit"])
            
            context = QueryContext(
                database_type=DatabaseType.RELATIONAL,
                filter_instance=relational_filter,
                query_params=self.params,
                enabled=True,
                priority=3  # Default priority
            )
            
            self.polyglot_query._add_context(context)
        except Exception as e:
            logger.error(f"Error creating relational query context: {e}")
        
        return self.polyglot_query


class FileStorageQueryBuilder:
    """Builder for file storage queries"""
    
    def __init__(self, polyglot_query: PolyglotQuery, enabled: bool = True):
        self.polyglot_query = polyglot_query
        self.enabled = enabled
        self.params = {}
    
    def by_extension(
        self,
        extensions: List[str],
        base_directory: str = ".",
        limit: Optional[int] = None
    ) -> PolyglotQuery:
        """
        Query by file extension.
        
        Args:
            extensions: List of extensions (e.g., ["py", "txt"])
            base_directory: Base directory to search
            limit: Maximum number of results
        
        Returns:
            PolyglotQuery for chaining
        """
        if not self.enabled:
            return self.polyglot_query
        
        # Create search query
        try:
            from uds3_file_storage_filter import create_search_query
            
            query = create_search_query(
                extensions=extensions,
                limit=limit
            )
            
            self.params = {
                "query": query,
                "base_directory": base_directory
            }
            
            # Create FileStorageFilter instance
            file_filter = self.polyglot_query.unified_strategy.create_file_storage_filter()
            
            context = QueryContext(
                database_type=DatabaseType.FILE_STORAGE,
                filter_instance=file_filter,
                query_params=self.params,
                enabled=True,
                priority=4  # Default priority
            )
            
            self.polyglot_query._add_context(context)
        except Exception as e:
            logger.error(f"Error creating file storage query context: {e}")
        
        return self.polyglot_query


# ============================================================================
# Factory Functions
# ============================================================================

def create_polyglot_query(
    unified_strategy: Any,
    execution_mode: ExecutionMode = ExecutionMode.SMART
) -> PolyglotQuery:
    """
    Create PolyglotQuery instance.
    
    Args:
        unified_strategy: UnifiedDatabaseStrategy instance
        execution_mode: Execution mode (PARALLEL, SEQUENTIAL, SMART)
    
    Returns:
        PolyglotQuery instance
    """
    return PolyglotQuery(unified_strategy, execution_mode)


# ============================================================================
# Built-in Test Script
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("  POLYGLOT QUERY MODULE - BUILT-IN TEST")
    print("=" * 80)
    
    print("\n[1/3] Module Import Check...")
    print(f"  VectorFilter Available: {VECTOR_FILTER_AVAILABLE}")
    print(f"  GraphFilter Available: {GRAPH_FILTER_AVAILABLE}")
    print(f"  RelationalFilter Available: {RELATIONAL_FILTER_AVAILABLE}")
    print(f"  FileStorageFilter Available: {FILE_STORAGE_FILTER_AVAILABLE}")
    
    print("\n[2/3] Enum Definitions...")
    print(f"  JoinStrategy: {[s.value for s in JoinStrategy]}")
    print(f"  ExecutionMode: {[m.value for m in ExecutionMode]}")
    print(f"  DatabaseType: {[d.value for d in DatabaseType]}")
    
    print("\n[3/3] Class Instantiation...")
    try:
        # Mock unified strategy
        class MockStrategy:
            pass
        
        query = PolyglotQuery(MockStrategy())
        print(f"  ✓ PolyglotQuery instantiated successfully")
        print(f"  ✓ Default join strategy: {query._join_strategy.value}")
        print(f"  ✓ Default execution mode: {query._execution_mode.value}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print("  BUILT-IN TEST COMPLETE")
    print("=" * 80)
