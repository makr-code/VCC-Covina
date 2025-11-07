"""
Unit Tests: ThemisGraphBackend
===============================

Tests for graph database operations:
- create_node() - Create graph nodes
- create_relationship() - Link nodes
- query_graph() - Traverse graph
- Cypher→AQL translation
- Shortest path algorithms
- Pattern matching
"""

import pytest
from typing import Dict, Any, List

from database.themis_graph import ThemisGraphBackend
from database.themis_exceptions import ThemisNotFoundError, ThemisValidationError
from tests.themis.conftest import (
    create_success_response,
    create_error_response,
    MockAsyncClient,
)


class TestNodeOperations:
    """Test graph node operations"""
    
    @pytest.mark.asyncio
    async def test_create_node_success(self, mock_http_client):
        """Test: create_node() creates graph node"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        node_data = {
            "type": "Person",
            "properties": {"name": "Alice", "age": 30}
        }
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/nodes",
            create_success_response({"id": "node_123", "created": True})
        )
        
        result = await backend.create_node("node_123", node_data)
        
        assert result["id"] == "node_123"
        assert result["created"] is True
    
    @pytest.mark.asyncio
    async def test_get_node_success(self, mock_http_client):
        """Test: get_node() retrieves node by ID"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_node = {
            "id": "node_123",
            "type": "Person",
            "properties": {"name": "Alice"}
        }
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/graph/nodes/node_123",
            create_success_response(mock_node)
        )
        
        result = await backend.get_node("node_123")
        
        assert result["id"] == "node_123"
        assert result["properties"]["name"] == "Alice"
    
    @pytest.mark.asyncio
    async def test_get_node_not_found(self, mock_http_client):
        """Test: get_node() raises NotFoundError"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/graph/nodes/missing",
            create_error_response(404, "Node not found")
        )
        
        with pytest.raises(ThemisNotFoundError):
            await backend.get_node("missing")
    
    @pytest.mark.asyncio
    async def test_update_node_properties(self, mock_http_client):
        """Test: update_node() updates properties"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        update_data = {"properties": {"age": 31, "city": "Berlin"}}
        
        mock_http_client.set_response(
            "PUT",
            "http://localhost:8765/graph/nodes/node_123",
            create_success_response({"id": "node_123", "updated": True})
        )
        
        result = await backend.update_node("node_123", update_data)
        
        assert result["updated"] is True
    
    @pytest.mark.asyncio
    async def test_delete_node_success(self, mock_http_client):
        """Test: delete_node() removes node"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/graph/nodes/node_123",
            create_success_response({"deleted": True})
        )
        
        result = await backend.delete_node("node_123")
        
        assert result["deleted"] is True


class TestRelationshipOperations:
    """Test graph relationship operations"""
    
    @pytest.mark.asyncio
    async def test_create_relationship_success(self, mock_http_client):
        """Test: create_relationship() links nodes"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        rel_data = {
            "type": "WORKS_AT",
            "properties": {"since": "2020-01-01"}
        }
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/relationships",
            create_success_response({"id": "rel_456", "created": True})
        )
        
        result = await backend.create_relationship(
            from_node="node_1",
            to_node="node_2",
            relationship_type="WORKS_AT",
            properties=rel_data["properties"]
        )
        
        assert result["created"] is True
    
    @pytest.mark.asyncio
    async def test_get_relationships_for_node(self, mock_http_client):
        """Test: get_relationships() returns node relationships"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_relationships = [
            {"id": "rel_1", "type": "WORKS_AT", "to": "node_2"},
            {"id": "rel_2", "type": "KNOWS", "to": "node_3"},
        ]
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/graph/nodes/node_1/relationships",
            create_success_response({"relationships": mock_relationships})
        )
        
        result = await backend.get_relationships("node_1")
        
        assert len(result) == 2
        assert result[0]["type"] == "WORKS_AT"
    
    @pytest.mark.asyncio
    async def test_delete_relationship_success(self, mock_http_client):
        """Test: delete_relationship() removes edge"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "DELETE",
            "http://localhost:8765/graph/relationships/rel_456",
            create_success_response({"deleted": True})
        )
        
        result = await backend.delete_relationship("rel_456")
        
        assert result["deleted"] is True


class TestGraphTraversal:
    """Test graph traversal operations"""
    
    @pytest.mark.asyncio
    async def test_traverse_graph_depth_1(self, mock_http_client):
        """Test: traverse() returns neighbors (depth=1)"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_neighbors = [
            {"id": "node_2", "type": "Company", "relationship": "WORKS_AT"},
            {"id": "node_3", "type": "Person", "relationship": "KNOWS"},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/traverse",
            create_success_response({"nodes": mock_neighbors, "count": 2})
        )
        
        result = await backend.traverse("node_1", depth=1)
        
        assert len(result) == 2
        assert result[0]["id"] == "node_2"
    
    @pytest.mark.asyncio
    async def test_traverse_graph_depth_2(self, mock_http_client):
        """Test: traverse() returns 2-hop neighbors"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        # 2-hop: node_1 → node_2 → node_4
        mock_neighbors = [
            {"id": "node_2", "depth": 1},
            {"id": "node_3", "depth": 1},
            {"id": "node_4", "depth": 2},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/traverse",
            create_success_response({"nodes": mock_neighbors, "count": 3})
        )
        
        result = await backend.traverse("node_1", depth=2)
        
        assert len(result) == 3
        assert any(node["depth"] == 2 for node in result)
    
    @pytest.mark.asyncio
    async def test_shortest_path_found(self, mock_http_client):
        """Test: shortest_path() finds path between nodes"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_path = {
            "path": ["node_1", "node_2", "node_3"],
            "length": 2,
            "relationships": ["WORKS_AT", "KNOWS"]
        }
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/shortest_path",
            create_success_response(mock_path)
        )
        
        result = await backend.shortest_path("node_1", "node_3")
        
        assert result["length"] == 2
        assert len(result["path"]) == 3
        assert result["path"][0] == "node_1"
        assert result["path"][-1] == "node_3"
    
    @pytest.mark.asyncio
    async def test_shortest_path_not_found(self, mock_http_client):
        """Test: shortest_path() returns None when no path exists"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/shortest_path",
            create_success_response({"path": None})
        )
        
        result = await backend.shortest_path("node_1", "node_isolated")
        
        assert result["path"] is None


class TestCypherToAQLTranslation:
    """Test Cypher → AQL translation"""
    
    @pytest.mark.asyncio
    async def test_translate_simple_match(self):
        """Test: Translate simple MATCH query"""
        backend = ThemisGraphBackend(MockAsyncClient(), "http://localhost:8765")
        
        cypher = "MATCH (n:Person) RETURN n"
        aql = backend._translate_cypher_to_aql(cypher)
        
        assert "FOR n IN Person" in aql or "FOR n IN nodes" in aql
        assert "RETURN n" in aql
    
    @pytest.mark.asyncio
    async def test_translate_match_with_where(self):
        """Test: Translate MATCH with WHERE clause"""
        backend = ThemisGraphBackend(MockAsyncClient(), "http://localhost:8765")
        
        cypher = "MATCH (n:Person) WHERE n.age > 30 RETURN n"
        aql = backend._translate_cypher_to_aql(cypher)
        
        assert "FILTER" in aql
        assert "n.age" in aql
    
    @pytest.mark.asyncio
    async def test_translate_match_relationship(self):
        """Test: Translate MATCH with relationship"""
        backend = ThemisGraphBackend(MockAsyncClient(), "http://localhost:8765")
        
        cypher = "MATCH (a:Person)-[:WORKS_AT]->(b:Company) RETURN a, b"
        aql = backend._translate_cypher_to_aql(cypher)
        
        # Should translate to AQL graph traversal
        assert "FOR" in aql
        # Relationships typically use GRAPH traversal in AQL
    
    @pytest.mark.asyncio
    async def test_translate_create_node(self):
        """Test: Translate CREATE node"""
        backend = ThemisGraphBackend(MockAsyncClient(), "http://localhost:8765")
        
        cypher = "CREATE (n:Person {name: 'Alice', age: 30})"
        aql = backend._translate_cypher_to_aql(cypher)
        
        assert "INSERT" in aql or "CREATE" in aql
        assert "Person" in aql


class TestPatternMatching:
    """Test graph pattern matching"""
    
    @pytest.mark.asyncio
    async def test_find_pattern_simple(self, mock_http_client):
        """Test: find_pattern() matches simple pattern"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        pattern = "(a:Person)-[:WORKS_AT]->(b:Company)"
        
        mock_matches = [
            {"a": {"id": "node_1", "name": "Alice"}, "b": {"id": "node_2", "name": "Acme"}},
            {"a": {"id": "node_3", "name": "Bob"}, "b": {"id": "node_2", "name": "Acme"}},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/pattern",
            create_success_response({"matches": mock_matches, "count": 2})
        )
        
        result = await backend.find_pattern(pattern)
        
        assert len(result) == 2
        assert result[0]["a"]["name"] == "Alice"
    
    @pytest.mark.asyncio
    async def test_find_pattern_with_properties(self, mock_http_client):
        """Test: find_pattern() matches with property constraints"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        pattern = "(a:Person {age: 30})-[:WORKS_AT]->(b:Company)"
        
        mock_matches = [
            {"a": {"id": "node_1", "name": "Alice", "age": 30}, "b": {"id": "node_2"}}
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/pattern",
            create_success_response({"matches": mock_matches, "count": 1})
        )
        
        result = await backend.find_pattern(pattern)
        
        assert len(result) == 1
        assert result[0]["a"]["age"] == 30


class TestBatchOperations:
    """Test batch graph operations"""
    
    @pytest.mark.asyncio
    async def test_batch_create_nodes(self, mock_http_client):
        """Test: batch_create_nodes() inserts multiple nodes"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        nodes = [
            {"id": "node_1", "type": "Person", "properties": {"name": "Alice"}},
            {"id": "node_2", "type": "Person", "properties": {"name": "Bob"}},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/nodes/batch",
            create_success_response({"created": 2, "ids": ["node_1", "node_2"]})
        )
        
        result = await backend.batch_create_nodes(nodes)
        
        assert result["created"] == 2
    
    @pytest.mark.asyncio
    async def test_batch_create_relationships(self, mock_http_client):
        """Test: batch_create_relationships() creates multiple edges"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        relationships = [
            {"from": "node_1", "to": "node_2", "type": "KNOWS"},
            {"from": "node_1", "to": "node_3", "type": "WORKS_AT"},
        ]
        
        mock_http_client.set_response(
            "POST",
            "http://localhost:8765/graph/relationships/batch",
            create_success_response({"created": 2})
        )
        
        result = await backend.batch_create_relationships(relationships)
        
        assert result["created"] == 2


class TestGraphStatistics:
    """Test graph statistics operations"""
    
    @pytest.mark.asyncio
    async def test_get_node_count(self, mock_http_client):
        """Test: count_nodes() returns total nodes"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/graph/stats/nodes",
            create_success_response({"count": 1234})
        )
        
        count = await backend.count_nodes()
        
        assert count == 1234
    
    @pytest.mark.asyncio
    async def test_get_relationship_count(self, mock_http_client):
        """Test: count_relationships() returns total edges"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/graph/stats/relationships",
            create_success_response({"count": 5678})
        )
        
        count = await backend.count_relationships()
        
        assert count == 5678
    
    @pytest.mark.asyncio
    async def test_get_node_degree(self, mock_http_client):
        """Test: get_degree() returns node degree (edges count)"""
        backend = ThemisGraphBackend(mock_http_client, "http://localhost:8765")
        
        mock_http_client.set_response(
            "GET",
            "http://localhost:8765/graph/nodes/node_1/degree",
            create_success_response({"degree": 12})
        )
        
        degree = await backend.get_degree("node_1")
        
        assert degree == 12


# Run tests with: pytest tests/themis/test_themis_graph.py -v
