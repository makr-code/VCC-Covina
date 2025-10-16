"""
UDS3 Graph Filter Module

Provides filtering and querying capabilities for Graph Databases (Neo4j).
Extends BaseFilter to support Cypher query generation with node/relationship filtering.

Author: UDS3 Team
Date: 1. Oktober 2025
"""

from typing import Any, List, Dict, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

try:
    from uds3_query_filters import (
        BaseFilter,
        FilterOperator,
        FilterCondition,
        QueryResult,
        LogicalOperator,
    )
except ImportError:
    raise ImportError(
        "uds3_query_filters module required. "
        "Please ensure BaseFilter is implemented first."
    )

logger = logging.getLogger(__name__)


class RelationshipDirection(Enum):
    """Direction for relationship traversal"""
    OUTGOING = "OUTGOING"  # -->
    INCOMING = "INCOMING"  # <--
    BOTH = "BOTH"  # --


class CypherOperator(Enum):
    """Cypher operators for WHERE clauses"""
    EQ = "="
    NE = "<>"
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    IN = "IN"
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS WITH"
    ENDS_WITH = "ENDS WITH"
    REGEX = "=~"


@dataclass
class NodeFilter:
    """Filter configuration for graph nodes"""
    label: Optional[str] = None
    properties: List[FilterCondition] = field(default_factory=list)
    variable: str = "n"  # Cypher variable name


@dataclass
class RelationshipFilter:
    """Filter configuration for graph relationships"""
    type: Optional[str] = None
    direction: RelationshipDirection = RelationshipDirection.OUTGOING
    properties: List[FilterCondition] = field(default_factory=list)
    variable: str = "r"  # Cypher variable name
    min_depth: int = 1
    max_depth: int = 1


@dataclass
class GraphQueryResult:
    """
    Extended result for graph queries.
    Similar to QueryResult but with graph-specific fields.
    """
    results: List[Dict] = field(default_factory=list)
    total_count: int = 0
    query_time_ms: Optional[float] = None
    nodes: Optional[List[Dict]] = None
    relationships: Optional[List[Dict]] = None
    paths: Optional[List[List[Dict]]] = None
    cypher_query: Optional[str] = None
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "success": self.success,
            "results": self.results,
            "count": len(self.results),
            "total_count": self.total_count,
        }
        if self.query_time_ms is not None:
            result["query_time_ms"] = self.query_time_ms
        if self.cypher_query:
            result["cypher_query"] = self.cypher_query
        if self.nodes:
            result["nodes"] = self.nodes
        if self.relationships:
            result["relationships"] = self.relationships
        if self.paths:
            result["paths"] = self.paths
        return result


class GraphFilter(BaseFilter):
    """
    Filter for Graph Database Queries (Neo4j).
    
    Extends BaseFilter to support Cypher query generation with:
    - Node filtering by label and properties
    - Relationship filtering by type and direction
    - Graph traversal with configurable depth
    - Complex pattern matching
    
    Example:
        filter = GraphFilter(neo4j_driver)
        result = (filter
                  .by_node_type("Document")
                  .by_property("status", FilterOperator.EQ, "active")
                  .by_relationship("REFERENCES", direction="OUTGOING")
                  .with_depth(2)
                  .execute())
    """
    
    def __init__(
        self,
        backend: Any,
        start_node_label: Optional[str] = None
    ):
        """
        Initialize GraphFilter.
        
        Args:
            backend: Neo4j driver or session
            start_node_label: Optional label for starting nodes
        """
        super().__init__(backend)
        self.node_filters: List[NodeFilter] = []
        self.relationship_filters: List[RelationshipFilter] = []
        self.start_node_label = start_node_label
        self.traversal_depth = 1
        self.return_nodes = True
        self.return_relationships = False
        self.return_paths = False
        
        # Initialize with start node if provided
        if start_node_label:
            self.node_filters.append(NodeFilter(label=start_node_label))
    
    def by_node_type(
        self,
        label: str,
        variable: str = "n"
    ) -> 'GraphFilter':
        """
        Filter by node label/type.
        
        Args:
            label: Node label (e.g., "Document", "Person")
            variable: Cypher variable name (default: "n")
        
        Returns:
            Self for method chaining
        
        Example:
            filter.by_node_type("Document")
            filter.by_node_type("Person", variable="p")
        """
        node_filter = NodeFilter(label=label, variable=variable)
        self.node_filters.append(node_filter)
        logger.debug(f"Added node type filter: {label}")
        return self
    
    def by_property(
        self,
        key: str,
        operator: Union[str, FilterOperator],
        value: Any,
        variable: str = "n"
    ) -> 'GraphFilter':
        """
        Filter by node property.
        
        Args:
            key: Property name
            operator: Filter operator (EQ, GT, IN, etc.)
            value: Property value
            variable: Cypher variable name (default: "n")
        
        Returns:
            Self for method chaining
        
        Example:
            filter.by_property("status", FilterOperator.EQ, "active")
            filter.by_property("age", ">", 18)
        """
        # Convert string operator to FilterOperator
        if isinstance(operator, str):
            operator = self._parse_operator(operator)
        
        condition = FilterCondition(
            field=key,
            operator=operator,
            value=value
        )
        
        # Add to appropriate node filter
        if self.node_filters:
            # Add to last node filter
            self.node_filters[-1].properties.append(condition)
        else:
            # Create new node filter
            node_filter = NodeFilter(variable=variable)
            node_filter.properties.append(condition)
            self.node_filters.append(node_filter)
        
        # Also add to base conditions for compatibility
        self.conditions.append(condition)
        
        logger.debug(f"Added property filter: {key} {operator} {value}")
        return self
    
    def where_property(
        self,
        key: str,
        operator: Union[str, FilterOperator],
        value: Any,
        variable: str = "n"
    ) -> 'GraphFilter':
        """
        Alias for by_property().
        
        Args:
            key: Property name
            operator: Filter operator
            value: Property value
            variable: Cypher variable name
        
        Returns:
            Self for method chaining
        """
        return self.by_property(key, operator, value, variable)
    
    def by_relationship(
        self,
        rel_type: str,
        direction: Union[str, RelationshipDirection] = RelationshipDirection.OUTGOING,
        variable: str = "r"
    ) -> 'GraphFilter':
        """
        Filter by relationship type and direction.
        
        Args:
            rel_type: Relationship type (e.g., "REFERENCES", "KNOWS")
            direction: Direction (OUTGOING, INCOMING, BOTH)
            variable: Cypher variable name (default: "r")
        
        Returns:
            Self for method chaining
        
        Example:
            filter.by_relationship("REFERENCES", "OUTGOING")
            filter.by_relationship("KNOWS", RelationshipDirection.BOTH)
        """
        # Convert string direction to enum
        if isinstance(direction, str):
            direction = RelationshipDirection[direction.upper()]
        
        rel_filter = RelationshipFilter(
            type=rel_type,
            direction=direction,
            variable=variable
        )
        self.relationship_filters.append(rel_filter)
        
        logger.debug(f"Added relationship filter: {rel_type} ({direction.value})")
        return self
    
    def with_relationship(
        self,
        rel_type: str,
        direction: Union[str, RelationshipDirection] = RelationshipDirection.OUTGOING
    ) -> 'GraphFilter':
        """
        Alias for by_relationship().
        
        Args:
            rel_type: Relationship type
            direction: Direction (OUTGOING, INCOMING, BOTH)
        
        Returns:
            Self for method chaining
        """
        return self.by_relationship(rel_type, direction)
    
    def by_relationship_property(
        self,
        key: str,
        operator: Union[str, FilterOperator],
        value: Any,
        variable: str = "r"
    ) -> 'GraphFilter':
        """
        Filter by relationship property.
        
        Args:
            key: Property name
            operator: Filter operator
            value: Property value
            variable: Cypher variable name (default: "r")
        
        Returns:
            Self for method chaining
        
        Example:
            filter.by_relationship_property("weight", ">", 0.5)
        """
        # Convert string operator to FilterOperator
        if isinstance(operator, str):
            operator = self._parse_operator(operator)
        
        condition = FilterCondition(
            field=key,
            operator=operator,
            value=value
        )
        
        # Add to last relationship filter
        if self.relationship_filters:
            self.relationship_filters[-1].properties.append(condition)
        else:
            logger.warning("No relationship filter defined. Call by_relationship() first.")
        
        logger.debug(f"Added relationship property filter: {key} {operator} {value}")
        return self
    
    def with_depth(
        self,
        min_depth: int = 1,
        max_depth: Optional[int] = None
    ) -> 'GraphFilter':
        """
        Set traversal depth for relationship patterns.
        
        Args:
            min_depth: Minimum traversal depth (default: 1)
            max_depth: Maximum traversal depth (default: same as min_depth)
        
        Returns:
            Self for method chaining
        
        Example:
            filter.with_depth(1, 3)  # Match paths 1-3 hops
            filter.with_depth(2)     # Match paths exactly 2 hops
        """
        if max_depth is None:
            max_depth = min_depth
        
        self.traversal_depth = max_depth
        
        # Update last relationship filter if exists
        if self.relationship_filters:
            self.relationship_filters[-1].min_depth = min_depth
            self.relationship_filters[-1].max_depth = max_depth
        
        logger.debug(f"Set traversal depth: {min_depth}-{max_depth}")
        return self
    
    def return_nodes_only(self) -> 'GraphFilter':
        """Configure to return only nodes (default)."""
        self.return_nodes = True
        self.return_relationships = False
        self.return_paths = False
        return self
    
    def return_relationships_also(self) -> 'GraphFilter':
        """Configure to return nodes and relationships."""
        self.return_nodes = True
        self.return_relationships = True
        return self
    
    def return_full_paths(self) -> 'GraphFilter':
        """Configure to return full paths (nodes + relationships)."""
        self.return_nodes = True
        self.return_relationships = True
        self.return_paths = True
        return self
    
    def execute(self) -> GraphQueryResult:
        """
        Execute graph query against Neo4j backend.
        
        Returns:
            GraphQueryResult with nodes, relationships, and/or paths
        
        Raises:
            ValueError: If no backend is configured
        """
        if not self.backend:
            raise ValueError("No backend configured for GraphFilter")
        
        start_time = datetime.now()
        
        try:
            # Generate Cypher query
            cypher_query = self.to_cypher()
            logger.info(f"Executing Cypher query: {cypher_query}")
            
            # Execute query
            # Note: Actual Neo4j execution would use backend.run() or backend.execute_query()
            # For now, we'll structure the result format
            
            # Placeholder for actual Neo4j execution
            # results = self.backend.run(cypher_query, parameters).data()
            results = []  # Would be populated by actual query
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Parse results
            parsed_results = self._parse_results(results)
            
            return GraphQueryResult(
                results=parsed_results,
                total_count=len(parsed_results),
                query_time_ms=execution_time,
                cypher_query=cypher_query,
                success=True
            )
        
        except Exception as e:
            logger.error(f"Error executing graph query: {e}")
            raise
    
    def count(self) -> int:
        """
        Count matching nodes without returning data.
        
        Returns:
            Number of matching nodes
        """
        if not self.backend:
            raise ValueError("No backend configured for GraphFilter")
        
        try:
            # Generate count query
            cypher_query = self.to_cypher(count_only=True)
            logger.info(f"Executing count query: {cypher_query}")
            
            # Placeholder for actual execution
            # result = self.backend.run(cypher_query).single()
            # return result['count']
            
            return 0  # Would be populated by actual query
        
        except Exception as e:
            logger.error(f"Error executing count query: {e}")
            raise
    
    def to_cypher(self, count_only: bool = False) -> str:
        """
        Generate Cypher query from filter configuration.
        
        Args:
            count_only: If True, generate COUNT query instead of full query
        
        Returns:
            Cypher query string
        
        Example:
            MATCH (n:Document)-[r:REFERENCES]->(m:Document)
            WHERE n.status = 'active' AND m.year > 2020
            RETURN n, r, m
        """
        # Build MATCH clause
        match_clause = self._build_match_clause()
        
        # Build WHERE clause
        where_clause = self._build_where_clause()
        
        # Build RETURN clause
        if count_only:
            return_clause = "RETURN COUNT(*) as count"
        else:
            return_clause = self._build_return_clause()
        
        # Combine clauses
        query_parts = [match_clause]
        if where_clause:
            query_parts.append(where_clause)
        query_parts.append(return_clause)
        
        # Add limit/offset if specified
        if not count_only:
            if self.limit_value:
                query_parts.append(f"LIMIT {self.limit_value}")
            if self.offset_value:
                query_parts.append(f"SKIP {self.offset_value}")
        
        cypher_query = "\n".join(query_parts)
        return cypher_query
    
    def to_query(self) -> Dict:
        """
        Convert filter to query dictionary.
        
        Returns:
            Dict with cypher query and parameters
        """
        return {
            "cypher": self.to_cypher(),
            "parameters": {},  # Would include parameterized values
            "node_filters": [
                {"label": nf.label, "properties": len(nf.properties)}
                for nf in self.node_filters
            ],
            "relationship_filters": [
                {"type": rf.type, "direction": rf.direction.value}
                for rf in self.relationship_filters
            ],
            "limit": self.limit_value,
            "offset": self.offset_value
        }
    
    def _build_match_clause(self) -> str:
        """
        Build MATCH clause from filters.
        
        Returns:
            MATCH clause string
        
        Example:
            MATCH (n:Document)-[r:REFERENCES*1..3]->(m:Document)
        """
        if not self.node_filters and not self.relationship_filters:
            return "MATCH (n)"
        
        # Simple case: single node
        if self.node_filters and not self.relationship_filters:
            node = self.node_filters[0]
            label = f":{node.label}" if node.label else ""
            return f"MATCH ({node.variable}{label})"
        
        # Complex case: nodes + relationships
        if len(self.node_filters) >= 2 and self.relationship_filters:
            source_node = self.node_filters[0]
            # Ensure target node has different variable name
            target_node = self.node_filters[1]
            if target_node.variable == source_node.variable:
                target_node.variable = "m"
            rel = self.relationship_filters[0]
            
            source_label = f":{source_node.label}" if source_node.label else ""
            target_label = f":{target_node.label}" if target_node.label else ""
            rel_type = f":{rel.type}" if rel.type else ""
            
            # Build relationship pattern
            if rel.min_depth == rel.max_depth == 1:
                depth = ""
            elif rel.min_depth == rel.max_depth:
                depth = f"*{rel.min_depth}"
            else:
                depth = f"*{rel.min_depth}..{rel.max_depth}"
            
            # Build direction arrows
            if rel.direction == RelationshipDirection.OUTGOING:
                pattern = f"({source_node.variable}{source_label})-[{rel.variable}{rel_type}{depth}]->({target_node.variable}{target_label})"
            elif rel.direction == RelationshipDirection.INCOMING:
                pattern = f"({source_node.variable}{source_label})<-[{rel.variable}{rel_type}{depth}]-({target_node.variable}{target_label})"
            else:  # BOTH
                pattern = f"({source_node.variable}{source_label})-[{rel.variable}{rel_type}{depth}]-({target_node.variable}{target_label})"
            
            return f"MATCH {pattern}"
        
        # Fallback: simple node match
        return "MATCH (n)"
    
    def _build_where_clause(self) -> str:
        """
        Build WHERE clause from property filters.
        
        Returns:
            WHERE clause string or empty string
        
        Example:
            WHERE n.status = 'active' AND n.year > 2020
        """
        conditions = []
        
        # Add node property conditions
        for node_filter in self.node_filters:
            for condition in node_filter.properties:
                cypher_condition = self._condition_to_cypher(
                    condition,
                    node_filter.variable
                )
                conditions.append(cypher_condition)
        
        # Add relationship property conditions
        for rel_filter in self.relationship_filters:
            for condition in rel_filter.properties:
                cypher_condition = self._condition_to_cypher(
                    condition,
                    rel_filter.variable
                )
                conditions.append(cypher_condition)
        
        if not conditions:
            return ""
        
        return "WHERE " + " AND ".join(conditions)
    
    def _build_return_clause(self) -> str:
        """
        Build RETURN clause based on configuration.
        
        Returns:
            RETURN clause string
        """
        return_parts = []
        
        # Return nodes
        if self.return_nodes:
            for node_filter in self.node_filters:
                return_parts.append(node_filter.variable)
        
        # Return relationships
        if self.return_relationships:
            for rel_filter in self.relationship_filters:
                return_parts.append(rel_filter.variable)
        
        if not return_parts:
            return_parts = ["n"]  # Default fallback
        
        return "RETURN " + ", ".join(return_parts)
    
    def _condition_to_cypher(
        self,
        condition: FilterCondition,
        variable: str
    ) -> str:
        """
        Convert FilterCondition to Cypher WHERE condition.
        
        Args:
            condition: FilterCondition to convert
            variable: Cypher variable name (e.g., "n", "r")
        
        Returns:
            Cypher condition string
        
        Example:
            n.status = 'active'
            r.weight > 0.5
        """
        field = f"{variable}.{condition.field}"
        value = self._format_value(condition.value)
        
        # Map FilterOperator to Cypher operator
        operator_map = {
            FilterOperator.EQ: "=",
            FilterOperator.NE: "<>",
            FilterOperator.GT: ">",
            FilterOperator.LT: "<",
            FilterOperator.GTE: ">=",
            FilterOperator.LTE: "<=",
            FilterOperator.IN: "IN",
            FilterOperator.CONTAINS: "CONTAINS",
            FilterOperator.STARTS_WITH: "STARTS WITH",
            FilterOperator.ENDS_WITH: "ENDS WITH",
            FilterOperator.REGEX: "=~",
        }
        
        op = operator_map.get(condition.operator, "=")
        
        if condition.operator == FilterOperator.IN:
            return f"{field} {op} {value}"
        else:
            return f"{field} {op} {value}"
    
    def _format_value(self, value: Any) -> str:
        """
        Format Python value for Cypher query.
        
        Args:
            value: Python value
        
        Returns:
            Cypher-formatted string
        """
        if isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "\\'")
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            # Format list for IN operator
            formatted_items = [self._format_value(item) for item in value]
            return f"[{', '.join(formatted_items)}]"
        elif value is None:
            return "null"
        else:
            return f"'{str(value)}'"
    
    def _parse_results(self, results: List[Dict]) -> List[Dict]:
        """
        Parse Neo4j query results.
        
        Args:
            results: Raw results from Neo4j
        
        Returns:
            Parsed results list
        """
        # Placeholder for actual Neo4j result parsing
        # Would extract nodes, relationships, properties
        return results
    
    def _parse_operator(self, operator: str) -> FilterOperator:
        """Parse string operator to FilterOperator enum."""
        operator_map = {
            "==": FilterOperator.EQ,
            "=": FilterOperator.EQ,
            "!=": FilterOperator.NE,
            "<>": FilterOperator.NE,
            ">": FilterOperator.GT,
            "<": FilterOperator.LT,
            ">=": FilterOperator.GTE,
            "<=": FilterOperator.LTE,
            "in": FilterOperator.IN,
            "contains": FilterOperator.CONTAINS,
            "starts_with": FilterOperator.STARTS_WITH,
            "ends_with": FilterOperator.ENDS_WITH,
            "regex": FilterOperator.REGEX,
        }
        return operator_map.get(operator.lower(), FilterOperator.EQ)


def create_graph_filter(
    backend: Any,
    start_node_label: Optional[str] = None
) -> GraphFilter:
    """
    Factory function for creating GraphFilter instances.
    
    Args:
        backend: Neo4j driver or session
        start_node_label: Optional label for starting nodes
    
    Returns:
        GraphFilter instance
    
    Example:
        filter = create_graph_filter(neo4j_driver, "Document")
        result = filter.by_property("status", "==", "active").execute()
    """
    return GraphFilter(backend, start_node_label)
