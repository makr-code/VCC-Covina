# Themis Adapter - Interface Design Document

**Erstellt:** 7. November 2025  
**Status:** Design Phase - Ready for Implementation  
**Ziel:** Python HTTP Adapter für Themis DB matching UDS3 Backend Interfaces  

---

## 📋 Design Overview

**Architecture:**
```
Covina Application Layer
         ↓
   ThemisAdapter
         ↓ (HTTP/REST)
   Themis DB Server (C++, port 8765)
         ↓
   RocksDB Storage
```

**Key Principle:** **Interface Compatibility** - Match UDS3 backend method signatures exactly!

---

## 🏗️ Class Structure

### 1. Main Adapter Class

```python
# File: Covina/database/themis_adapter.py

import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

@dataclass
class ThemisConfig:
    """Themis Connection Configuration"""
    url: str = "http://localhost:8765"
    timeout: int = 30
    max_retries: int = 3
    pool_size: int = 100
    auth_token: Optional[str] = None


class ThemisAdapter:
    """
    Main Themis Database Adapter
    
    Provides UDS3-compatible interface to Themis DB via HTTP API.
    Supports all 4 backend types: Relational, Vector, Graph, Document.
    """
    
    def __init__(self, config: Optional[ThemisConfig] = None):
        self.config = config or ThemisConfig()
        self.logger = logging.getLogger(__name__)
        
        # HTTP Client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.config.url,
            timeout=self.config.timeout,
            limits=httpx.Limits(
                max_connections=self.config.pool_size,
                max_keepalive_connections=20
            )
        )
        
        # Backend instances (lazy-initialized)
        self._relational_backend: Optional['ThemisRelationalBackend'] = None
        self._vector_backend: Optional['ThemisVectorBackend'] = None
        self._graph_backend: Optional['ThemisGraphBackend'] = None
        self._document_backend: Optional['ThemisDocumentBackend'] = None
        
        # Transaction management
        self._active_transaction: Optional[int] = None
    
    # UDS3-compatible backend getters (matching DatabaseManager interface)
    def get_relational_backend(self) -> 'ThemisRelationalBackend':
        """Get relational backend (UDS3 interface compatible)"""
        if self._relational_backend is None:
            self._relational_backend = ThemisRelationalBackend(self)
        return self._relational_backend
    
    def get_vector_backend(self) -> 'ThemisVectorBackend':
        """Get vector backend (UDS3 interface compatible)"""
        if self._vector_backend is None:
            self._vector_backend = ThemisVectorBackend(self)
        return self._vector_backend
    
    def get_graph_backend(self) -> 'ThemisGraphBackend':
        """Get graph backend (UDS3 interface compatible)"""
        if self._graph_backend is None:
            self._graph_backend = ThemisGraphBackend(self)
        return self._graph_backend
    
    def get_document_backend(self) -> 'ThemisDocumentBackend':
        """Get document backend (UDS3 interface compatible)"""
        if self._document_backend is None:
            self._document_backend = ThemisDocumentBackend(self)
        return self._document_backend
    
    # Transaction Management (Themis native support!)
    async def begin_transaction(self, isolation: str = "read_committed") -> int:
        """
        Begin ACID transaction
        
        Args:
            isolation: "read_committed" or "snapshot"
            
        Returns:
            transaction_id (int)
        """
        response = await self.client.post(
            "/transaction/begin",
            json={"isolation": isolation}
        )
        response.raise_for_status()
        data = response.json()
        self._active_transaction = data["transaction_id"]
        return self._active_transaction
    
    async def commit_transaction(self, transaction_id: Optional[int] = None) -> Dict[str, Any]:
        """Commit transaction"""
        txn_id = transaction_id or self._active_transaction
        if txn_id is None:
            raise ValueError("No active transaction")
        
        response = await self.client.post(
            "/transaction/commit",
            json={"transaction_id": txn_id}
        )
        response.raise_for_status()
        self._active_transaction = None
        return response.json()
    
    async def rollback_transaction(self, transaction_id: Optional[int] = None):
        """Rollback transaction"""
        txn_id = transaction_id or self._active_transaction
        if txn_id is None:
            return
        
        response = await self.client.post(
            "/transaction/rollback",
            json={"transaction_id": txn_id}
        )
        response.raise_for_status()
        self._active_transaction = None
    
    async def close(self):
        """Close HTTP client connection pool"""
        if self._active_transaction:
            await self.rollback_transaction()
        await self.client.aclose()
```

---

## 🗄️ Backend Implementations

### 2. Relational Backend

```python
# File: Covina/database/themis_relational.py

class ThemisRelationalBackend:
    """
    Relational Backend for Themis (PostgreSQL → Themis Entities + AQL)
    
    Maps UDS3 relational operations to Themis HTTP API:
    - CRUD → /entities/{key} (PUT/GET/DELETE)
    - Queries → /query/aql (AQL syntax)
    - Aggregations → COLLECT clause
    """
    
    def __init__(self, adapter: 'ThemisAdapter'):
        self.adapter = adapter
        self.client = adapter.client
        self.logger = adapter.logger
    
    # UDS3-compatible CRUD operations
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute SQL-like query (translates to AQL)
        
        Example:
            query = "SELECT * FROM users WHERE age > 18"
            → Translates to AQL: "FOR u IN users FILTER u.age > 18 RETURN u"
        """
        aql_query = self._translate_sql_to_aql(query, params)
        
        response = await self.client.post(
            "/query/aql",
            json={
                "query": aql_query,
                "allow_full_scan": True
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Parse JSON entities from response
        entities = [json.loads(entity_str) for entity_str in data.get("entities", [])]
        return entities
    
    async def insert(self, table: str, data: Dict[str, Any]) -> str:
        """
        Insert entity into table
        
        Args:
            table: Table name (becomes entity key prefix)
            data: Entity data (JSON dict)
            
        Returns:
            Entity key (table:pk)
        """
        # Generate PK if not provided
        pk = data.get("_key") or data.get("id") or str(uuid.uuid4())
        key = f"{table}:{pk}"
        
        response = await self.client.put(
            f"/entities/{key}",
            json={
                "key": key,
                "blob": json.dumps(data)
            }
        )
        response.raise_for_status()
        return key
    
    async def update(self, table: str, pk: str, data: Dict[str, Any]) -> bool:
        """Update entity (upsert in Themis)"""
        key = f"{table}:{pk}"
        response = await self.client.put(
            f"/entities/{key}",
            json={
                "key": key,
                "blob": json.dumps(data)
            }
        )
        return response.status_code in [200, 201]
    
    async def delete(self, table: str, pk: str) -> bool:
        """Delete entity"""
        key = f"{table}:{pk}"
        response = await self.client.delete(f"/entities/{key}")
        return response.status_code == 200
    
    async def get(self, table: str, pk: str) -> Optional[Dict]:
        """Get entity by primary key"""
        key = f"{table}:{pk}"
        response = await self.client.get(f"/entities/{key}")
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        return json.loads(data["blob"])
    
    # Aggregation support (AQL COLLECT)
    async def aggregate(self, table: str, group_by: str, aggregations: List[Dict]) -> List[Dict]:
        """
        Execute aggregation query
        
        Example:
            group_by = "city"
            aggregations = [
                {"func": "COUNT", "as": "total"},
                {"func": "AVG", "field": "salary", "as": "avg_sal"}
            ]
            
            → AQL: FOR u IN users 
                   COLLECT city = u.city 
                   AGGREGATE total = COUNT(), avg_sal = AVG(u.salary)
                   RETURN {city, total, avg_sal}
        """
        agg_clauses = []
        for agg in aggregations:
            func = agg["func"]
            field = agg.get("field", "")
            as_name = agg["as"]
            
            if func == "COUNT":
                agg_clauses.append(f"{as_name} = COUNT()")
            elif field:
                agg_clauses.append(f"{as_name} = {func}(doc.{field})")
        
        aql = f"""
        FOR doc IN {table}
        COLLECT {group_by}_val = doc.{group_by}
        AGGREGATE {", ".join(agg_clauses)}
        RETURN {{{group_by}: {group_by}_val, {", ".join(agg["as"] for agg in aggregations)}}}
        """
        
        response = await self.client.post("/query/aql", json={"query": aql})
        response.raise_for_status()
        
        entities = [json.loads(e) for e in response.json().get("entities", [])]
        return entities
    
    def _translate_sql_to_aql(self, sql: str, params: Optional[Dict]) -> str:
        """
        Translate simple SQL to AQL
        
        Supports:
        - SELECT * FROM table WHERE col = value
        - SELECT * FROM table WHERE col > value
        - SELECT * FROM table ORDER BY col DESC LIMIT n
        """
        # Simple pattern matching (can be extended with sqlparse library)
        import re
        
        # Extract components
        select_match = re.search(r"SELECT\s+(.+?)\s+FROM\s+(\w+)", sql, re.IGNORECASE)
        where_match = re.search(r"WHERE\s+(.+?)(?:\s+ORDER BY|\s+LIMIT|$)", sql, re.IGNORECASE)
        order_match = re.search(r"ORDER BY\s+(\w+)(?:\s+(ASC|DESC))?", sql, re.IGNORECASE)
        limit_match = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)
        
        if not select_match:
            raise ValueError(f"Invalid SQL: {sql}")
        
        fields, table = select_match.groups()
        
        # Build AQL
        aql_parts = [f"FOR doc IN {table}"]
        
        if where_match:
            where_clause = where_match.group(1)
            # Convert SQL operators to AQL
            where_clause = where_clause.replace(" = ", " == ")
            aql_parts.append(f"FILTER {where_clause}")
        
        if order_match:
            col, direction = order_match.groups()
            direction = direction or "ASC"
            aql_parts.append(f"SORT doc.{col} {direction}")
        
        if limit_match:
            limit = limit_match.group(1)
            aql_parts.append(f"LIMIT {limit}")
        
        # RETURN clause
        if fields.strip() == "*":
            aql_parts.append("RETURN doc")
        else:
            # Parse field list
            field_list = [f.strip() for f in fields.split(",")]
            return_obj = "{" + ", ".join(f"{f}: doc.{f}" for f in field_list) + "}"
            aql_parts.append(f"RETURN {return_obj}")
        
        return "\n".join(aql_parts)
```

---

## 📊 Vector Backend

```python
# File: Covina/database/themis_vector.py

class ThemisVectorBackend:
    """
    Vector Backend for Themis (ChromaDB → Themis Vector Index)
    
    Maps UDS3 vector operations to Themis HTTP API:
    - add() → /vector/batch_insert
    - query() → /vector/search
    - delete() → /vector/by-filter
    """
    
    def __init__(self, adapter: 'ThemisAdapter'):
        self.adapter = adapter
        self.client = adapter.client
        self.logger = adapter.logger
    
    async def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        documents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add vectors to index (ChromaDB-compatible signature)
        
        Args:
            ids: Document IDs
            embeddings: Vector embeddings (list of float arrays)
            metadatas: Optional metadata dicts
            documents: Optional text content
            
        Returns:
            Result dict with inserted count
        """
        metadatas = metadatas or [{}] * len(ids)
        documents = documents or [""] * len(ids)
        
        items = []
        for pk, vector, metadata, doc in zip(ids, embeddings, metadatas, documents):
            fields = {**metadata, "text": doc} if doc else metadata
            items.append({
                "pk": pk,
                "vector": vector,
                "fields": fields
            })
        
        response = await self.client.post(
            "/vector/batch_insert",
            json={
                "vector_field": "embedding",
                "items": items
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Query similar vectors (ChromaDB-compatible signature)
        
        Args:
            query_embeddings: Query vectors
            n_results: Number of results (k)
            where: Optional metadata filter
            
        Returns:
            Dict with ids, distances, metadatas, documents
        """
        results = {
            "ids": [],
            "distances": [],
            "metadatas": [],
            "documents": []
        }
        
        for query_vector in query_embeddings:
            response = await self.client.post(
                "/vector/search",
                json={
                    "vector": query_vector,
                    "k": n_results
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse results
            ids = [hit["pk"] for hit in data["results"]]
            distances = [hit["distance"] for hit in data["results"]]
            
            # Fetch metadata from entities
            metadatas = []
            documents = []
            for pk in ids:
                entity = await self._get_entity(pk)
                if entity:
                    metadatas.append(entity)
                    documents.append(entity.get("text", ""))
                else:
                    metadatas.append({})
                    documents.append("")
            
            results["ids"].append(ids)
            results["distances"].append(distances)
            results["metadatas"].append(metadatas)
            results["documents"].append(documents)
        
        return results
    
    async def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs"""
        response = await self.client.delete(
            "/vector/by-filter",
            json={"pks": ids}
        )
        return response.status_code == 200
    
    async def _get_entity(self, pk: str) -> Optional[Dict]:
        """Helper: Get entity metadata"""
        response = await self.client.get(f"/entities/{pk}")
        if response.status_code == 404:
            return None
        return json.loads(response.json()["blob"])
```

---

## 🕸️ Graph Backend

```python
# File: Covina/database/themis_graph.py

class ThemisGraphBackend:
    """
    Graph Backend for Themis (Neo4j → Themis Graph Traversal + Dijkstra)
    
    Maps UDS3 graph operations to Themis HTTP API:
    - execute_query() (Cypher) → AQL graph traversal
    - BFS → /graph/traverse
    - Shortest path → Native Dijkstra support
    """
    
    def __init__(self, adapter: 'ThemisAdapter'):
        self.adapter = adapter
        self.client = adapter.client
        self.logger = adapter.logger
    
    async def execute_query(self, cypher: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute Cypher-like query (translates to AQL)
        
        Example:
            cypher = "MATCH (u:User)-[:FRIEND]->(f) WHERE u.name = 'Alice' RETURN f"
            → Translates to AQL: FOR f, e, p IN 1..1 OUTBOUND 'users:alice' friendships RETURN f
        """
        aql_query = self._translate_cypher_to_aql(cypher, params)
        
        response = await self.client.post(
            "/query/aql",
            json={"query": aql_query, "allow_full_scan": True}
        )
        response.raise_for_status()
        
        entities = [json.loads(e) for e in response.json().get("entities", [])]
        return entities
    
    async def create_node(self, label: str, properties: Dict) -> str:
        """
        Create graph node (entity)
        
        Args:
            label: Node label (becomes table name)
            properties: Node properties
            
        Returns:
            Node key
        """
        pk = properties.get("_key") or properties.get("id") or str(uuid.uuid4())
        key = f"{label}:{pk}"
        
        response = await self.client.put(
            f"/entities/{key}",
            json={
                "key": key,
                "blob": json.dumps({**properties, "_label": label})
            }
        )
        response.raise_for_status()
        return key
    
    async def create_relationship(
        self,
        from_node: str,
        to_node: str,
        rel_type: str,
        properties: Optional[Dict] = None
    ) -> str:
        """
        Create graph edge (relationship)
        
        Args:
            from_node: Source node key
            to_node: Target node key
            rel_type: Relationship type
            properties: Optional edge properties
            
        Returns:
            Edge key
        """
        edge_id = f"edge_{uuid.uuid4()}"
        edge_key = f"edges:{edge_id}"
        
        edge_data = {
            "id": edge_id,
            "_from": from_node,
            "_to": to_node,
            "type": rel_type,
            **(properties or {})
        }
        
        response = await self.client.put(
            f"/entities/{edge_key}",
            json={
                "key": edge_key,
                "blob": json.dumps(edge_data)
            }
        )
        response.raise_for_status()
        return edge_key
    
    async def traverse(
        self,
        start_vertex: str,
        max_depth: int = 3,
        direction: str = "OUTBOUND"
    ) -> List[str]:
        """
        BFS traversal
        
        Args:
            start_vertex: Start node key
            max_depth: Maximum traversal depth
            direction: "OUTBOUND", "INBOUND", or "ANY"
            
        Returns:
            List of visited node keys
        """
        response = await self.client.post(
            "/graph/traverse",
            json={
                "start_vertex": start_vertex,
                "max_depth": max_depth
            }
        )
        response.raise_for_status()
        return response.json()["visited"]
    
    async def shortest_path(self, start: str, target: str) -> Dict[str, Any]:
        """
        Find shortest path (Dijkstra)
        
        Returns:
            Dict with path (list of nodes) and distance
        """
        # Note: Themis Dijkstra currently internal C++ API
        # For now, use AQL traversal as workaround
        # TODO: Add HTTP endpoint /graph/shortest-path
        
        # Fallback: Use multi-depth BFS
        for depth in range(1, 10):
            visited = await self.traverse(start, max_depth=depth)
            if target in visited:
                return {
                    "path": self._reconstruct_path(visited, start, target),
                    "distance": depth
                }
        
        return {"path": [], "distance": -1}
    
    def _translate_cypher_to_aql(self, cypher: str, params: Optional[Dict]) -> str:
        """Translate Cypher to AQL (simplified)"""
        # Pattern: MATCH (a)-[r:TYPE]->(b) WHERE ... RETURN ...
        import re
        
        match = re.search(
            r"MATCH\s+\((\w+):?(\w*)\)-\[(\w+):(\w+)\]->\((\w+):?(\w*)\)",
            cypher,
            re.IGNORECASE
        )
        
        if match:
            var_a, label_a, var_r, rel_type, var_b, label_b = match.groups()
            
            # Build AQL
            aql = f"FOR {var_b}, {var_r}, p IN 1..1 OUTBOUND '{label_a}:*' {rel_type}\n"
            
            where_match = re.search(r"WHERE\s+(.+?)(?:\s+RETURN|$)", cypher, re.IGNORECASE)
            if where_match:
                where_clause = where_match.group(1)
                aql += f"FILTER {where_clause}\n"
            
            return_match = re.search(r"RETURN\s+(.+)$", cypher, re.IGNORECASE)
            if return_match:
                return_expr = return_match.group(1)
                aql += f"RETURN {return_expr}"
            else:
                aql += f"RETURN {var_b}"
            
            return aql
        
        raise ValueError(f"Unsupported Cypher pattern: {cypher}")
```

---

## 📄 Document Backend

```python
# File: Covina/database/themis_document.py

class ThemisDocumentBackend:
    """
    Document Backend for Themis (CouchDB → Themis Content API)
    
    Maps UDS3 document operations to Themis HTTP API:
    - store_document() → /content/import
    - get_document() → /content/{id}
    - get_blob() → /content/{id}/blob
    """
    
    def __init__(self, adapter: 'ThemisAdapter'):
        self.adapter = adapter
        self.client = adapter.client
        self.logger = adapter.logger
    
    async def store_document(
        self,
        doc_id: str,
        file_path: str,
        mime_type: str,
        metadata: Optional[Dict] = None,
        blob_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Store document with content
        
        Args:
            doc_id: Document ID
            file_path: Original file path
            mime_type: MIME type
            metadata: Optional metadata
            blob_data: Optional binary data
            
        Returns:
            Result dict with content_id
        """
        import base64
        import hashlib
        from pathlib import Path
        
        content_meta = {
            "id": doc_id,
            "mime_type": mime_type,
            "category": self._get_category(mime_type),
            "original_filename": Path(file_path).name,
            "size_bytes": len(blob_data) if blob_data else 0,
            "hash_sha256": hashlib.sha256(blob_data).hexdigest() if blob_data else "",
            "user_metadata": metadata or {}
        }
        
        payload = {"content": content_meta}
        
        if blob_data:
            payload["blob_base64"] = base64.b64encode(blob_data).decode()
        
        response = await self.client.post("/content/import", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get document metadata"""
        response = await self.client.get(f"/content/{doc_id}")
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return response.json()
    
    async def get_blob(self, doc_id: str) -> Optional[bytes]:
        """Get document binary data"""
        response = await self.client.get(f"/content/{doc_id}/blob")
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return response.content
    
    async def get_chunks(self, doc_id: str, page: int = 1, page_size: int = 100) -> List[Dict]:
        """Get document chunks (for chunked content)"""
        response = await self.client.get(
            f"/content/{doc_id}/chunks",
            params={"page": page, "page_size": page_size}
        )
        response.raise_for_status()
        return response.json()["chunks"]
    
    def _get_category(self, mime_type: str) -> int:
        """Map MIME type to Themis category enum"""
        if mime_type.startswith("text"):
            return 0  # TEXT
        elif mime_type.startswith("image"):
            return 1  # IMAGE
        elif mime_type.startswith("audio"):
            return 2  # AUDIO
        elif mime_type.startswith("video"):
            return 3  # VIDEO
        elif mime_type == "application/pdf":
            return 8  # BINARY
        else:
            return 9  # UNKNOWN
```

---

## 🔧 Utility Classes

### Error Handling

```python
# File: Covina/database/themis_exceptions.py

class ThemisError(Exception):
    """Base exception for Themis operations"""
    pass

class ThemisConnectionError(ThemisError):
    """Connection error"""
    pass

class ThemisNotFoundError(ThemisError):
    """Entity not found (404)"""
    pass

class ThemisValidationError(ThemisError):
    """Invalid request (400)"""
    pass

class ThemisTransactionError(ThemisError):
    """Transaction conflict or error"""
    pass


def map_http_error(status_code: int, message: str) -> ThemisError:
    """Map HTTP status codes to Themis exceptions"""
    if status_code == 404:
        return ThemisNotFoundError(message)
    elif status_code == 400:
        return ThemisValidationError(message)
    elif status_code >= 500:
        return ThemisConnectionError(message)
    else:
        return ThemisError(message)
```

---

## 📝 Usage Example

```python
# Example: Covina Integration

import asyncio
from database.themis_adapter import ThemisAdapter, ThemisConfig

async def main():
    # Initialize adapter
    config = ThemisConfig(
        url="http://localhost:8765",
        timeout=30,
        max_retries=3
    )
    
    adapter = ThemisAdapter(config)
    
    try:
        # Get backends (UDS3-compatible!)
        relational = adapter.get_relational_backend()
        vector = adapter.get_vector_backend()
        graph = adapter.get_graph_backend()
        document = adapter.get_document_backend()
        
        # --- Transaction Example ---
        txn_id = await adapter.begin_transaction(isolation="snapshot")
        
        try:
            # Insert document metadata
            doc_key = await relational.insert("documents", {
                "title": "Test Document",
                "author": "Alice",
                "created_at": "2025-11-07"
            })
            
            # Add vector embedding
            await vector.add(
                ids=[doc_key],
                embeddings=[[0.1, 0.2, 0.3, ...]],  # 384-dim
                metadatas=[{"title": "Test Document"}]
            )
            
            # Create graph node
            node_key = await graph.create_node("Document", {
                "id": doc_key,
                "title": "Test Document"
            })
            
            # Commit transaction
            await adapter.commit_transaction(txn_id)
            print("✅ Transaction committed!")
            
        except Exception as e:
            # Rollback on error
            await adapter.rollback_transaction(txn_id)
            print(f"❌ Transaction rolled back: {e}")
            raise
        
        # --- Query Example (AQL) ---
        results = await relational.execute_query(
            "SELECT * FROM documents WHERE author = 'Alice'"
        )
        print(f"Found {len(results)} documents")
        
        # --- Vector Search Example ---
        similar = await vector.query(
            query_embeddings=[[0.1, 0.2, 0.3, ...]],
            n_results=10
        )
        print(f"Found {len(similar['ids'][0])} similar documents")
        
        # --- Graph Traversal Example ---
        visited = await graph.traverse(
            start_vertex=node_key,
            max_depth=3,
            direction="OUTBOUND"
        )
        print(f"Visited {len(visited)} nodes")
        
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## ✅ Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] ThemisAdapter main class with HTTP client
- [ ] Configuration management (ThemisConfig)
- [ ] Error handling (exceptions)
- [ ] Connection pooling
- [ ] Retry logic with exponential backoff

### Phase 2: Backend Implementations
- [ ] ThemisRelationalBackend (CRUD + AQL)
- [ ] ThemisVectorBackend (k-NN search)
- [ ] ThemisGraphBackend (traversal + Dijkstra)
- [ ] ThemisDocumentBackend (content API)

### Phase 3: Transaction Support
- [ ] begin_transaction()
- [ ] commit_transaction()
- [ ] rollback_transaction()
- [ ] Transaction context manager

### Phase 4: Advanced Features
- [ ] SQL → AQL translation (sqlparse)
- [ ] Cypher → AQL translation
- [ ] Batch operations
- [ ] Caching layer (optional)

### Phase 5: Integration
- [ ] Modify main_backend.py (replace UDS3)
- [ ] Modify ingestion_backend.py (replace UDS3)
- [ ] ENV configuration (.env with THEMIS_URL)
- [ ] Backward compatibility layer (optional)

### Phase 6: Testing
- [ ] Unit tests (mock HTTP responses)
- [ ] Integration tests (live Themis instance)
- [ ] Performance tests (vs UDS3 baseline)
- [ ] Migration validation tests

---

## 🎯 Next Steps

1. **Start Implementation:** Create base adapter class (Phase 1)
2. **Implement Relational Backend:** Most critical for Covina (Phase 2.1)
3. **Add Transaction Support:** Test ACID operations (Phase 3)
4. **Integrate into Covina:** Replace UDS3 in main_backend.py (Phase 5)

**Ready to proceed with implementation?**

---

**Design Version:** 1.0  
**Last Updated:** 7. November 2025  
**Status:** ✅ Design Complete - Ready for Coding!
