"""
VCC-Covina GraphRAG Pipeline
Self-hosted Graph-enhanced RAG with Neo4j Knowledge Graph
On-premise, no vendor dependencies

Usage:
    from ai_ml.graphrag import GraphRAGPipeline, GraphRAGConfig
    
    config = GraphRAGConfig(
        neo4j_uri="bolt://neo4j-service.covina:7687",
        llm_endpoint="http://vllm-llama-service.covina-llm:8000"
    )
    graphrag = GraphRAGPipeline(config)
    
    response = await graphrag.query("What companies are related to document X?")
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp

logger = logging.getLogger(__name__)


class GraphStrategy(Enum):
    """GraphRAG retrieval strategies"""
    LOCAL = "local"  # Local neighborhood traversal
    GLOBAL = "global"  # Community-based summarization
    HYBRID = "hybrid"  # Combine local + vector retrieval
    CHAIN = "chain"  # Chain-of-thought reasoning over graph


@dataclass
class GraphRAGConfig:
    """Configuration for GraphRAG pipeline"""
    # Service endpoints (all on-premise)
    neo4j_uri: str = "bolt://neo4j-service.covina:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j-password"
    
    llm_endpoint: str = "http://vllm-llama-service.covina-llm:8000"
    embedding_endpoint: str = "http://embedding-service.covina-llm:8080"
    chromadb_host: str = "chromadb-service.covina"
    chromadb_port: int = 8000
    
    # GraphRAG settings
    strategy: GraphStrategy = GraphStrategy.HYBRID
    max_hops: int = 2  # Maximum graph traversal depth
    max_entities: int = 20  # Maximum entities to consider
    community_level: int = 2  # Community hierarchy level for global search
    
    # Retrieval settings
    top_k_vector: int = 10
    top_k_graph: int = 15
    similarity_threshold: float = 0.7
    
    # LLM settings
    temperature: float = 0.3
    max_tokens: int = 2048
    
    # API key
    api_key: str = "vcc-covina-llm-secret-key"
    
    # System prompts
    entity_extraction_prompt: str = """Extrahiere alle wichtigen Entitäten aus der Frage.
Entitätstypen: Person, Organisation, Dokument, Datum, Ort, Gesetz, Vertrag.
Antworte im JSON-Format: {{"entities": [{{"name": "...", "type": "..."}}]}}"""
    
    synthesis_prompt: str = """Basierend auf den folgenden Informationen aus dem Wissensgraphen 
und den relevanten Dokumenten, beantworte die Frage präzise.
Verweise auf die Quellen mit [Quelle: ...].
Bei rechtlichen Themen weise auf professionelle Beratung hin."""


@dataclass
class Entity:
    """Knowledge graph entity"""
    id: str
    name: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    """Knowledge graph relationship"""
    source: Entity
    target: Entity
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphContext:
    """Context from knowledge graph"""
    entities: List[Entity]
    relationships: List[Relationship]
    communities: List[Dict[str, Any]]
    summary: str = ""


@dataclass
class GraphRAGResponse:
    """Response from GraphRAG pipeline"""
    answer: str
    graph_context: GraphContext
    vector_sources: List[Dict[str, Any]]
    reasoning_chain: List[str]
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphRAGPipeline:
    """
    Self-hosted GraphRAG Pipeline
    
    Combines knowledge graph traversal with vector retrieval for 
    enhanced context in RAG responses.
    
    Features:
    - Entity extraction from queries
    - Multi-hop graph traversal
    - Community-based summarization
    - Hybrid retrieval (graph + vector)
    - Chain-of-thought reasoning
    """
    
    def __init__(self, config: Optional[GraphRAGConfig] = None):
        self.config = config or GraphRAGConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._neo4j_driver = None
    
    async def __aenter__(self) -> "GraphRAGPipeline":
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized"""
        if self._session is None or self._session.closed:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}"
            }
            self._session = aiohttp.ClientSession(headers=headers)
    
    async def close(self):
        """Close connections"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def query(
        self,
        question: str,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> GraphRAGResponse:
        """
        Execute GraphRAG query
        
        Args:
            question: User question
            filters: Optional filters for retrieval
            **kwargs: Override config parameters
            
        Returns:
            GraphRAGResponse with answer and context
        """
        import time
        start_time = time.time()
        
        await self._ensure_session()
        
        # Step 1: Extract entities from question
        entities = await self._extract_entities(question)
        
        # Step 2: Get graph context based on strategy
        graph_context = await self._get_graph_context(entities, question)
        
        # Step 3: Get vector-based context
        vector_sources = await self._get_vector_context(question, filters)
        
        # Step 4: Build reasoning chain
        reasoning_chain = await self._build_reasoning_chain(
            question, graph_context, vector_sources
        )
        
        # Step 5: Synthesize final answer
        answer = await self._synthesize_answer(
            question, graph_context, vector_sources, reasoning_chain
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return GraphRAGResponse(
            answer=answer,
            graph_context=graph_context,
            vector_sources=vector_sources,
            reasoning_chain=reasoning_chain,
            latency_ms=latency_ms,
            metadata={
                "strategy": self.config.strategy.value,
                "entities_found": len(entities),
                "graph_entities": len(graph_context.entities),
                "graph_relationships": len(graph_context.relationships),
                "vector_sources": len(vector_sources)
            }
        )
    
    async def _extract_entities(self, question: str) -> List[Entity]:
        """Extract entities from question using LLM"""
        
        prompt = f"{self.config.entity_extraction_prompt}\n\nFrage: {question}"
        
        response = await self._llm_generate(prompt, max_tokens=500)
        
        try:
            # Parse JSON response
            data = json.loads(response)
            entities = [
                Entity(
                    id=f"query_{i}",
                    name=e["name"],
                    type=e["type"]
                )
                for i, e in enumerate(data.get("entities", []))
            ]
            return entities
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse entity extraction response: {response}")
            return []
    
    async def _get_graph_context(
        self,
        entities: List[Entity],
        question: str
    ) -> GraphContext:
        """Get context from knowledge graph"""
        
        if self.config.strategy == GraphStrategy.LOCAL:
            return await self._local_search(entities)
        elif self.config.strategy == GraphStrategy.GLOBAL:
            return await self._global_search(question)
        elif self.config.strategy == GraphStrategy.HYBRID:
            local = await self._local_search(entities)
            global_ctx = await self._global_search(question)
            return self._merge_contexts(local, global_ctx)
        else:
            return await self._local_search(entities)
    
    async def _local_search(self, entities: List[Entity]) -> GraphContext:
        """Local neighborhood search around seed entities"""
        
        if not entities:
            return GraphContext(entities=[], relationships=[], communities=[])
        
        # Build Cypher query for multi-hop traversal
        entity_names = [e.name for e in entities]
        
        cypher = """
        MATCH (n)
        WHERE n.name IN $entity_names OR toLower(n.name) IN [x IN $entity_names | toLower(x)]
        CALL {
            WITH n
            MATCH path = (n)-[*1..%d]-(m)
            RETURN DISTINCT m, relationships(path) as rels
            LIMIT %d
        }
        RETURN n, collect(DISTINCT m) as neighbors, collect(DISTINCT rels) as all_rels
        """ % (self.config.max_hops, self.config.max_entities)
        
        # Execute query via HTTP API (avoiding neo4j-driver dependency)
        results = await self._execute_cypher(cypher, {"entity_names": entity_names})
        
        return self._parse_neo4j_results(results)
    
    async def _global_search(self, question: str) -> GraphContext:
        """Global community-based search"""
        
        # Get community summaries from graph
        cypher = """
        MATCH (c:Community)
        WHERE c.level = $level
        RETURN c.id as id, c.summary as summary, c.members as members
        ORDER BY c.importance DESC
        LIMIT 10
        """
        
        results = await self._execute_cypher(
            cypher, 
            {"level": self.config.community_level}
        )
        
        communities = []
        for record in results.get("results", [{}])[0].get("data", []):
            row = record.get("row", [])
            if len(row) >= 3:
                communities.append({
                    "id": row[0],
                    "summary": row[1],
                    "members": row[2]
                })
        
        return GraphContext(
            entities=[],
            relationships=[],
            communities=communities,
            summary=self._summarize_communities(communities)
        )
    
    def _merge_contexts(
        self,
        local: GraphContext,
        global_ctx: GraphContext
    ) -> GraphContext:
        """Merge local and global contexts"""
        return GraphContext(
            entities=local.entities,
            relationships=local.relationships,
            communities=global_ctx.communities,
            summary=f"Lokaler Kontext:\n{self._format_local_context(local)}\n\nGlobaler Kontext:\n{global_ctx.summary}"
        )
    
    async def _get_vector_context(
        self,
        question: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get context from vector store"""
        
        # Get question embedding
        embedding = await self._get_embedding(question)
        
        # Query ChromaDB
        url = f"http://{self.config.chromadb_host}:{self.config.chromadb_port}"
        
        query_body = {
            "query_embeddings": [embedding],
            "n_results": self.config.top_k_vector
        }
        if filters:
            query_body["where"] = filters
        
        async with self._session.post(
            f"{url}/api/v1/collections/covina_documents/query",
            json=query_body
        ) as response:
            if response.status != 200:
                logger.error(f"ChromaDB query failed: {await response.text()}")
                return []
            
            data = await response.json()
            
            sources = []
            ids = data.get("ids", [[]])[0]
            distances = data.get("distances", [[]])[0]
            documents = data.get("documents", [[]])[0]
            metadatas = data.get("metadatas", [[]])[0]
            
            for i, doc_id in enumerate(ids):
                sources.append({
                    "id": doc_id,
                    "content": documents[i] if i < len(documents) else "",
                    "score": 1 - distances[i] if i < len(distances) else 0,
                    "metadata": metadatas[i] if i < len(metadatas) else {}
                })
            
            return sources
    
    async def _build_reasoning_chain(
        self,
        question: str,
        graph_context: GraphContext,
        vector_sources: List[Dict[str, Any]]
    ) -> List[str]:
        """Build chain-of-thought reasoning"""
        
        context_summary = self._format_context_summary(graph_context, vector_sources)
        
        prompt = f"""Erstelle einen Schritt-für-Schritt Denkprozess zur Beantwortung der Frage.

Frage: {question}

Verfügbarer Kontext:
{context_summary}

Erstelle 3-5 Denkschritte, die zur Antwort führen.
Format: Nummerierte Liste."""
        
        response = await self._llm_generate(prompt, max_tokens=500)
        
        # Parse steps
        steps = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                steps.append(line.lstrip("0123456789.-) "))
        
        return steps
    
    async def _synthesize_answer(
        self,
        question: str,
        graph_context: GraphContext,
        vector_sources: List[Dict[str, Any]],
        reasoning_chain: List[str]
    ) -> str:
        """Synthesize final answer"""
        
        context = self._format_full_context(graph_context, vector_sources)
        reasoning = "\n".join([f"- {step}" for step in reasoning_chain])
        
        prompt = f"""{self.config.synthesis_prompt}

Wissensgraph-Kontext:
{self._format_graph_context(graph_context)}

Dokumenten-Kontext:
{self._format_vector_context(vector_sources)}

Denkschritte:
{reasoning}

Frage: {question}

Antwort:"""
        
        return await self._llm_generate(prompt, max_tokens=self.config.max_tokens)
    
    async def _execute_cypher(
        self,
        query: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Cypher query via Neo4j HTTP API"""
        
        # Neo4j HTTP API endpoint
        url = self.config.neo4j_uri.replace("bolt://", "http://").replace(":7687", ":7474")
        
        auth = aiohttp.BasicAuth(self.config.neo4j_user, self.config.neo4j_password)
        
        async with self._session.post(
            f"{url}/db/neo4j/tx/commit",
            json={
                "statements": [{
                    "statement": query,
                    "parameters": parameters
                }]
            },
            auth=auth
        ) as response:
            if response.status != 200:
                logger.error(f"Neo4j query failed: {await response.text()}")
                return {"results": []}
            
            return await response.json()
    
    def _parse_neo4j_results(self, results: Dict[str, Any]) -> GraphContext:
        """Parse Neo4j results into GraphContext"""
        
        entities = []
        relationships = []
        seen_entities: Set[str] = set()
        
        for result in results.get("results", []):
            for record in result.get("data", []):
                row = record.get("row", [])
                
                if len(row) >= 1 and row[0]:
                    node = row[0]
                    if isinstance(node, dict):
                        entity = Entity(
                            id=str(node.get("id", "")),
                            name=node.get("name", ""),
                            type=node.get("type", "Unknown"),
                            properties=node
                        )
                        if entity.name not in seen_entities:
                            entities.append(entity)
                            seen_entities.add(entity.name)
        
        return GraphContext(
            entities=entities[:self.config.max_entities],
            relationships=relationships,
            communities=[]
        )
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        
        async with self._session.post(
            f"{self.config.embedding_endpoint}/embed",
            json={"inputs": text}
        ) as response:
            if response.status != 200:
                raise GraphRAGError(f"Embedding request failed: {response.status}")
            
            data = await response.json()
            return data[0] if isinstance(data, list) else data.get("embedding", [])
    
    async def _llm_generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate text using LLM"""
        
        async with self._session.post(
            f"{self.config.llm_endpoint}/v1/chat/completions",
            json={
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": self.config.temperature
            }
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise GraphRAGError(f"LLM generation failed: {error}")
            
            data = await response.json()
            return data["choices"][0]["message"]["content"]
    
    def _format_local_context(self, context: GraphContext) -> str:
        """Format local context for display"""
        lines = []
        for entity in context.entities[:10]:
            lines.append(f"- {entity.name} ({entity.type})")
        return "\n".join(lines) if lines else "Keine lokalen Entitäten gefunden."
    
    def _summarize_communities(self, communities: List[Dict[str, Any]]) -> str:
        """Summarize community information"""
        if not communities:
            return "Keine Community-Informationen verfügbar."
        
        lines = []
        for comm in communities[:5]:
            summary = comm.get("summary", "Keine Zusammenfassung")
            lines.append(f"- {summary}")
        return "\n".join(lines)
    
    def _format_context_summary(
        self,
        graph_context: GraphContext,
        vector_sources: List[Dict[str, Any]]
    ) -> str:
        """Format combined context summary"""
        
        graph_summary = f"Graph: {len(graph_context.entities)} Entitäten, {len(graph_context.relationships)} Beziehungen"
        vector_summary = f"Dokumente: {len(vector_sources)} relevante Abschnitte"
        
        return f"{graph_summary}\n{vector_summary}"
    
    def _format_full_context(
        self,
        graph_context: GraphContext,
        vector_sources: List[Dict[str, Any]]
    ) -> str:
        """Format full context for synthesis"""
        
        parts = [
            "=== Wissensgraph ===",
            self._format_graph_context(graph_context),
            "",
            "=== Dokumente ===",
            self._format_vector_context(vector_sources)
        ]
        
        return "\n".join(parts)
    
    def _format_graph_context(self, context: GraphContext) -> str:
        """Format graph context"""
        
        lines = []
        
        if context.entities:
            lines.append("Entitäten:")
            for entity in context.entities[:10]:
                lines.append(f"  - {entity.name} ({entity.type})")
        
        if context.relationships:
            lines.append("\nBeziehungen:")
            for rel in context.relationships[:10]:
                lines.append(f"  - {rel.source.name} --[{rel.type}]--> {rel.target.name}")
        
        if context.summary:
            lines.append(f"\nZusammenfassung:\n{context.summary}")
        
        return "\n".join(lines) if lines else "Keine Graph-Informationen."
    
    def _format_vector_context(self, sources: List[Dict[str, Any]]) -> str:
        """Format vector sources"""
        
        lines = []
        for i, source in enumerate(sources[:5]):
            filename = source.get("metadata", {}).get("filename", f"Dokument {i+1}")
            content = source.get("content", "")[:500]
            lines.append(f"[{filename}]\n{content}...")
        
        return "\n\n".join(lines) if lines else "Keine Dokumente gefunden."
    
    async def index_entity(
        self,
        entity: Entity,
        relationships: Optional[List[Tuple[str, Entity]]] = None
    ) -> bool:
        """
        Index entity into knowledge graph
        
        Args:
            entity: Entity to index
            relationships: Optional list of (relation_type, target_entity)
            
        Returns:
            Success status
        """
        # Create entity node
        cypher = """
        MERGE (n:%s {name: $name})
        SET n += $properties
        RETURN n
        """ % entity.type
        
        result = await self._execute_cypher(cypher, {
            "name": entity.name,
            "properties": entity.properties
        })
        
        # Create relationships
        if relationships:
            for rel_type, target in relationships:
                rel_cypher = """
                MATCH (s {name: $source_name})
                MERGE (t:%s {name: $target_name})
                MERGE (s)-[r:%s]->(t)
                RETURN r
                """ % (target.type, rel_type)
                
                await self._execute_cypher(rel_cypher, {
                    "source_name": entity.name,
                    "target_name": target.name
                })
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check GraphRAG pipeline health"""
        await self._ensure_session()
        
        results = {}
        
        # Check Neo4j
        try:
            neo4j_result = await self._execute_cypher("RETURN 1 as test", {})
            results["neo4j"] = {
                "status": "healthy" if neo4j_result else "unhealthy"
            }
        except Exception as e:
            results["neo4j"] = {"status": "error", "error": str(e)}
        
        # Check other services
        services = [
            ("llm", f"{self.config.llm_endpoint}/health"),
            ("embedding", f"{self.config.embedding_endpoint}/health"),
            ("chromadb", f"http://{self.config.chromadb_host}:{self.config.chromadb_port}/api/v1/heartbeat")
        ]
        
        for name, url in services:
            try:
                async with self._session.get(url) as response:
                    results[name] = {
                        "status": "healthy" if response.status == 200 else "unhealthy"
                    }
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        
        return results


class GraphRAGError(Exception):
    """GraphRAG pipeline error"""
    pass
