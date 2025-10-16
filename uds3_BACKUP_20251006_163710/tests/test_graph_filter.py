"""
Unit Tests for UDS3 Graph Filter Module

Tests GraphFilter class for Neo4j/Cypher query generation.

Author: UDS3 Team
Date: 1. Oktober 2025
"""

import pytest
from typing import Dict, List
from unittest.mock import Mock, MagicMock

from uds3_graph_filter import (
    GraphFilter,
    NodeFilter,
    RelationshipFilter,
    GraphQueryResult,
    RelationshipDirection,
    create_graph_filter,
)
from uds3_query_filters import FilterOperator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_neo4j_backend():
    """Mock Neo4j driver/session"""
    backend = Mock()
    backend.run = Mock(return_value=Mock(data=Mock(return_value=[])))
    backend.execute_query = Mock(return_value=([], None, None))
    return backend


@pytest.fixture
def graph_filter(mock_neo4j_backend):
    """GraphFilter instance with mock backend"""
    return GraphFilter(mock_neo4j_backend)


# ============================================================================
# TEST NODE FILTER
# ============================================================================

class TestNodeFilter:
    """Test NodeFilter dataclass"""
    
    def test_create_node_filter(self):
        """Test creating NodeFilter"""
        node_filter = NodeFilter(label="Document", variable="n")
        assert node_filter.label == "Document"
        assert node_filter.variable == "n"
        assert node_filter.properties == []
    
    def test_node_filter_defaults(self):
        """Test NodeFilter default values"""
        node_filter = NodeFilter()
        assert node_filter.label is None
        assert node_filter.variable == "n"
        assert node_filter.properties == []


class TestRelationshipFilter:
    """Test RelationshipFilter dataclass"""
    
    def test_create_relationship_filter(self):
        """Test creating RelationshipFilter"""
        rel_filter = RelationshipFilter(
            type="REFERENCES",
            direction=RelationshipDirection.OUTGOING
        )
        assert rel_filter.type == "REFERENCES"
        assert rel_filter.direction == RelationshipDirection.OUTGOING
        assert rel_filter.min_depth == 1
        assert rel_filter.max_depth == 1
    
    def test_relationship_filter_defaults(self):
        """Test RelationshipFilter default values"""
        rel_filter = RelationshipFilter()
        assert rel_filter.type is None
        assert rel_filter.direction == RelationshipDirection.OUTGOING
        assert rel_filter.variable == "r"


# ============================================================================
# TEST GRAPH FILTER BASICS
# ============================================================================

class TestGraphFilterBasics:
    """Test GraphFilter initialization and basic methods"""
    
    def test_create_graph_filter(self, mock_neo4j_backend):
        """Test creating GraphFilter"""
        filter = GraphFilter(mock_neo4j_backend)
        assert filter.backend == mock_neo4j_backend
        assert filter.node_filters == []
        assert filter.relationship_filters == []
    
    def test_graph_filter_with_start_node(self, mock_neo4j_backend):
        """Test GraphFilter with start node label"""
        filter = GraphFilter(mock_neo4j_backend, start_node_label="Document")
        assert len(filter.node_filters) == 1
        assert filter.node_filters[0].label == "Document"
    
    def test_graph_filter_factory(self, mock_neo4j_backend):
        """Test create_graph_filter factory function"""
        filter = create_graph_filter(mock_neo4j_backend, "Person")
        assert isinstance(filter, GraphFilter)
        assert filter.start_node_label == "Person"


# ============================================================================
# TEST NODE FILTERING
# ============================================================================

class TestNodeFiltering:
    """Test node filtering methods"""
    
    def test_by_node_type(self, graph_filter):
        """Test by_node_type method"""
        result = graph_filter.by_node_type("Document")
        assert result == graph_filter  # Method chaining
        assert len(graph_filter.node_filters) == 1
        assert graph_filter.node_filters[0].label == "Document"
    
    def test_by_node_type_multiple(self, graph_filter):
        """Test adding multiple node types"""
        graph_filter.by_node_type("Document").by_node_type("Person")
        assert len(graph_filter.node_filters) == 2
        assert graph_filter.node_filters[0].label == "Document"
        assert graph_filter.node_filters[1].label == "Person"
    
    def test_by_property(self, graph_filter):
        """Test by_property method"""
        graph_filter.by_node_type("Document")
        result = graph_filter.by_property("status", FilterOperator.EQ, "active")
        assert result == graph_filter  # Method chaining
        assert len(graph_filter.node_filters[0].properties) == 1
        condition = graph_filter.node_filters[0].properties[0]
        assert condition.field == "status"
        assert condition.operator == FilterOperator.EQ
        assert condition.value == "active"
    
    def test_by_property_string_operator(self, graph_filter):
        """Test by_property with string operator"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("year", ">", 2020)
        assert len(graph_filter.node_filters[0].properties) == 1
        condition = graph_filter.node_filters[0].properties[0]
        assert condition.operator == FilterOperator.GT
    
    def test_by_property_multiple(self, graph_filter):
        """Test multiple property filters"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("status", "==", "active")
        graph_filter.by_property("year", ">=", 2020)
        graph_filter.by_property("priority", ">", 5)
        assert len(graph_filter.node_filters[0].properties) == 3
    
    def test_where_property_alias(self, graph_filter):
        """Test where_property alias"""
        graph_filter.by_node_type("Document")
        result = graph_filter.where_property("status", "==", "active")
        assert result == graph_filter
        assert len(graph_filter.node_filters[0].properties) == 1


# ============================================================================
# TEST RELATIONSHIP FILTERING
# ============================================================================

class TestRelationshipFiltering:
    """Test relationship filtering methods"""
    
    def test_by_relationship(self, graph_filter):
        """Test by_relationship method"""
        result = graph_filter.by_relationship("REFERENCES", RelationshipDirection.OUTGOING)
        assert result == graph_filter  # Method chaining
        assert len(graph_filter.relationship_filters) == 1
        rel = graph_filter.relationship_filters[0]
        assert rel.type == "REFERENCES"
        assert rel.direction == RelationshipDirection.OUTGOING
    
    def test_by_relationship_string_direction(self, graph_filter):
        """Test by_relationship with string direction"""
        graph_filter.by_relationship("KNOWS", "INCOMING")
        rel = graph_filter.relationship_filters[0]
        assert rel.direction == RelationshipDirection.INCOMING
    
    def test_by_relationship_both_direction(self, graph_filter):
        """Test by_relationship with BOTH direction"""
        graph_filter.by_relationship("RELATED_TO", RelationshipDirection.BOTH)
        rel = graph_filter.relationship_filters[0]
        assert rel.direction == RelationshipDirection.BOTH
    
    def test_with_relationship_alias(self, graph_filter):
        """Test with_relationship alias"""
        result = graph_filter.with_relationship("REFERENCES")
        assert result == graph_filter
        assert len(graph_filter.relationship_filters) == 1
    
    def test_by_relationship_property(self, graph_filter):
        """Test by_relationship_property method"""
        graph_filter.by_relationship("REFERENCES")
        result = graph_filter.by_relationship_property("weight", ">", 0.5)
        assert result == graph_filter
        rel = graph_filter.relationship_filters[0]
        assert len(rel.properties) == 1
        condition = rel.properties[0]
        assert condition.field == "weight"
        assert condition.value == 0.5
    
    def test_with_depth(self, graph_filter):
        """Test with_depth method"""
        graph_filter.by_relationship("REFERENCES")
        result = graph_filter.with_depth(1, 3)
        assert result == graph_filter
        rel = graph_filter.relationship_filters[0]
        assert rel.min_depth == 1
        assert rel.max_depth == 3
    
    def test_with_depth_single_value(self, graph_filter):
        """Test with_depth with single value"""
        graph_filter.by_relationship("REFERENCES")
        graph_filter.with_depth(2)
        rel = graph_filter.relationship_filters[0]
        assert rel.min_depth == 2
        assert rel.max_depth == 2


# ============================================================================
# TEST RETURN CONFIGURATION
# ============================================================================

class TestReturnConfiguration:
    """Test return configuration methods"""
    
    def test_return_nodes_only(self, graph_filter):
        """Test return_nodes_only method"""
        result = graph_filter.return_nodes_only()
        assert result == graph_filter
        assert graph_filter.return_nodes is True
        assert graph_filter.return_relationships is False
        assert graph_filter.return_paths is False
    
    def test_return_relationships_also(self, graph_filter):
        """Test return_relationships_also method"""
        graph_filter.return_relationships_also()
        assert graph_filter.return_nodes is True
        assert graph_filter.return_relationships is True
        assert graph_filter.return_paths is False
    
    def test_return_full_paths(self, graph_filter):
        """Test return_full_paths method"""
        graph_filter.return_full_paths()
        assert graph_filter.return_nodes is True
        assert graph_filter.return_relationships is True
        assert graph_filter.return_paths is True


# ============================================================================
# TEST CYPHER GENERATION
# ============================================================================

class TestCypherGeneration:
    """Test Cypher query generation"""
    
    def test_to_cypher_simple_node(self, graph_filter):
        """Test to_cypher with simple node match"""
        graph_filter.by_node_type("Document")
        cypher = graph_filter.to_cypher()
        assert "MATCH (n:Document)" in cypher
        assert "RETURN n" in cypher
    
    def test_to_cypher_node_with_property(self, graph_filter):
        """Test to_cypher with node property filter"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("status", "==", "active")
        cypher = graph_filter.to_cypher()
        assert "MATCH (n:Document)" in cypher
        assert "WHERE n.status = 'active'" in cypher
        assert "RETURN n" in cypher
    
    def test_to_cypher_with_relationship(self, graph_filter):
        """Test to_cypher with relationship"""
        graph_filter.by_node_type("Document")
        graph_filter.by_relationship("REFERENCES", "OUTGOING")
        graph_filter.by_node_type("Document")
        cypher = graph_filter.to_cypher()
        assert "MATCH (n:Document)-[r:REFERENCES]->(m:Document)" in cypher
    
    def test_to_cypher_relationship_incoming(self, graph_filter):
        """Test to_cypher with incoming relationship"""
        graph_filter.by_node_type("Document")
        graph_filter.by_relationship("REFERENCES", "INCOMING")
        graph_filter.by_node_type("Document")
        cypher = graph_filter.to_cypher()
        assert "<-[r:REFERENCES]-" in cypher
    
    def test_to_cypher_relationship_both(self, graph_filter):
        """Test to_cypher with bidirectional relationship"""
        graph_filter.by_node_type("Person")
        graph_filter.by_relationship("KNOWS", "BOTH")
        graph_filter.by_node_type("Person")
        cypher = graph_filter.to_cypher()
        assert "-[r:KNOWS]-" in cypher
        assert not ("<-" in cypher or "->" in cypher)
    
    def test_to_cypher_with_depth(self, graph_filter):
        """Test to_cypher with traversal depth"""
        graph_filter.by_node_type("Document")
        graph_filter.by_relationship("REFERENCES", "OUTGOING")
        graph_filter.with_depth(1, 3)
        graph_filter.by_node_type("Document")
        cypher = graph_filter.to_cypher()
        assert "*1..3" in cypher
    
    def test_to_cypher_multiple_properties(self, graph_filter):
        """Test to_cypher with multiple property filters"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("status", "==", "active")
        graph_filter.by_property("year", ">=", 2020)
        cypher = graph_filter.to_cypher()
        assert "WHERE" in cypher
        assert "n.status = 'active'" in cypher
        assert "n.year >= 2020" in cypher
        assert " AND " in cypher
    
    def test_to_cypher_with_limit(self, graph_filter):
        """Test to_cypher with limit"""
        graph_filter.by_node_type("Document")
        graph_filter.limit(10)
        cypher = graph_filter.to_cypher()
        assert "LIMIT 10" in cypher
    
    def test_to_cypher_with_offset(self, graph_filter):
        """Test to_cypher with offset"""
        graph_filter.by_node_type("Document")
        graph_filter.offset(20)
        cypher = graph_filter.to_cypher()
        assert "SKIP 20" in cypher
    
    def test_to_cypher_count_only(self, graph_filter):
        """Test to_cypher with count_only=True"""
        graph_filter.by_node_type("Document")
        cypher = graph_filter.to_cypher(count_only=True)
        assert "RETURN COUNT(*) as count" in cypher
        assert "LIMIT" not in cypher


# ============================================================================
# TEST VALUE FORMATTING
# ============================================================================

class TestValueFormatting:
    """Test _format_value method"""
    
    def test_format_string_value(self, graph_filter):
        """Test formatting string values"""
        formatted = graph_filter._format_value("test")
        assert formatted == "'test'"
    
    def test_format_string_with_quotes(self, graph_filter):
        """Test formatting string with quotes"""
        formatted = graph_filter._format_value("test's value")
        assert formatted == "'test\\'s value'"
    
    def test_format_integer_value(self, graph_filter):
        """Test formatting integer values"""
        formatted = graph_filter._format_value(42)
        assert formatted == "42"
    
    def test_format_float_value(self, graph_filter):
        """Test formatting float values"""
        formatted = graph_filter._format_value(3.14)
        assert formatted == "3.14"
    
    def test_format_boolean_true(self, graph_filter):
        """Test formatting boolean True"""
        formatted = graph_filter._format_value(True)
        assert formatted == "true"
    
    def test_format_boolean_false(self, graph_filter):
        """Test formatting boolean False"""
        formatted = graph_filter._format_value(False)
        assert formatted == "false"
    
    def test_format_none_value(self, graph_filter):
        """Test formatting None value"""
        formatted = graph_filter._format_value(None)
        assert formatted == "null"
    
    def test_format_list_value(self, graph_filter):
        """Test formatting list values"""
        formatted = graph_filter._format_value(["a", "b", "c"])
        assert formatted == "['a', 'b', 'c']"


# ============================================================================
# TEST OPERATOR MAPPING
# ============================================================================

class TestOperatorMapping:
    """Test operator mapping and conversion"""
    
    def test_condition_to_cypher_eq(self, graph_filter):
        """Test EQ operator conversion"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("status", FilterOperator.EQ, "active")
        cypher = graph_filter.to_cypher()
        assert "n.status = 'active'" in cypher
    
    def test_condition_to_cypher_ne(self, graph_filter):
        """Test NE operator conversion"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("status", FilterOperator.NE, "deleted")
        cypher = graph_filter.to_cypher()
        assert "n.status <> 'deleted'" in cypher
    
    def test_condition_to_cypher_gt(self, graph_filter):
        """Test GT operator conversion"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("count", FilterOperator.GT, 10)
        cypher = graph_filter.to_cypher()
        assert "n.count > 10" in cypher
    
    def test_condition_to_cypher_in(self, graph_filter):
        """Test IN operator conversion"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("type", FilterOperator.IN, ["pdf", "docx"])
        cypher = graph_filter.to_cypher()
        assert "n.type IN ['pdf', 'docx']" in cypher
    
    def test_condition_to_cypher_contains(self, graph_filter):
        """Test CONTAINS operator conversion"""
        graph_filter.by_node_type("Document")
        graph_filter.by_property("title", FilterOperator.CONTAINS, "test")
        cypher = graph_filter.to_cypher()
        assert "n.title CONTAINS 'test'" in cypher


# ============================================================================
# TEST QUERY EXECUTION
# ============================================================================

class TestQueryExecution:
    """Test query execution"""
    
    def test_execute_without_backend(self):
        """Test execute without backend raises error"""
        filter = GraphFilter(None)
        with pytest.raises(ValueError, match="No backend configured"):
            filter.execute()
    
    def test_execute_returns_graph_query_result(self, graph_filter):
        """Test execute returns GraphQueryResult"""
        graph_filter.by_node_type("Document")
        result = graph_filter.execute()
        assert isinstance(result, GraphQueryResult)
        assert result.cypher_query is not None
        assert result.query_time_ms is not None
    
    def test_count_without_backend(self):
        """Test count without backend raises error"""
        filter = GraphFilter(None)
        with pytest.raises(ValueError, match="No backend configured"):
            filter.count()


# ============================================================================
# TEST COMPLEX QUERIES
# ============================================================================

class TestComplexQueries:
    """Test complex query combinations"""
    
    def test_complex_query_full(self, graph_filter):
        """Test complex query with nodes, relationships, properties"""
        cypher = (graph_filter
                  .by_node_type("Document")
                  .by_property("status", "==", "active")
                  .by_relationship("REFERENCES", "OUTGOING")
                  .by_relationship_property("weight", ">", 0.5)
                  .with_depth(1, 2)
                  .by_node_type("Document")
                  .by_property("year", ">=", 2020)
                  .limit(10)
                  .to_cypher())
        
        assert "MATCH (n:Document)-[r:REFERENCES*1..2]->(m:Document)" in cypher
        assert "WHERE" in cypher
        assert "n.status = 'active'" in cypher
        assert "r.weight > 0.5" in cypher
        assert "m.year >= 2020" in cypher
        assert "LIMIT 10" in cypher
    
    def test_fluent_chaining(self, graph_filter):
        """Test fluent API chaining"""
        result = (graph_filter
                  .by_node_type("Person")
                  .by_property("age", ">", 18)
                  .by_relationship("KNOWS", "BOTH")
                  .by_node_type("Person")
                  .limit(5))
        assert result == graph_filter
        assert len(graph_filter.node_filters) == 2
        assert len(graph_filter.relationship_filters) == 1


# ============================================================================
# TEST TO_QUERY METHOD
# ============================================================================

class TestToQuery:
    """Test to_query method"""
    
    def test_to_query_basic(self, graph_filter):
        """Test to_query returns dict"""
        graph_filter.by_node_type("Document")
        query = graph_filter.to_query()
        assert isinstance(query, dict)
        assert "cypher" in query
        assert "parameters" in query
        assert "node_filters" in query
    
    def test_to_query_with_filters(self, graph_filter):
        """Test to_query includes filter info"""
        graph_filter.by_node_type("Document")
        graph_filter.by_relationship("REFERENCES")
        query = graph_filter.to_query()
        assert len(query["node_filters"]) == 1
        assert len(query["relationship_filters"]) == 1


# ============================================================================
# TEST EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_filter(self, graph_filter):
        """Test filter with no conditions"""
        cypher = graph_filter.to_cypher()
        assert "MATCH" in cypher
        assert "RETURN" in cypher
    
    def test_relationship_property_without_relationship(self, graph_filter):
        """Test adding relationship property without relationship"""
        graph_filter.by_relationship_property("weight", ">", 0.5)
        # Should not raise error, but log warning
        assert len(graph_filter.relationship_filters) == 0
    
    def test_multiple_node_types(self, graph_filter):
        """Test with multiple different node types"""
        graph_filter.by_node_type("Document")
        graph_filter.by_node_type("Person")
        graph_filter.by_node_type("Organization")
        assert len(graph_filter.node_filters) == 3
    
    def test_depth_without_relationship(self, graph_filter):
        """Test setting depth without relationship"""
        graph_filter.with_depth(2, 5)
        assert graph_filter.traversal_depth == 5


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
