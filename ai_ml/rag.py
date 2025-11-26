"""
VCC-Covina RAG (Retrieval-Augmented Generation) Pipeline
Self-hosted RAG implementation with ChromaDB and vLLM
On-premise, no vendor dependencies

Usage:
    from ai_ml.rag import RAGPipeline, RAGConfig
    
    config = RAGConfig(
        llm_endpoint="http://vllm-llama-service.covina-llm:8000",
        embedding_endpoint="http://embedding-service.covina-llm:8080",
        chromadb_host="chromadb-service.covina:8000"
    )
    rag = RAGPipeline(config)
    
    response = await rag.query("What are the compliance requirements?")
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)


class RetrievalStrategy(Enum):
    """Document retrieval strategies"""
    SEMANTIC = "semantic"  # Pure vector similarity
    HYBRID = "hybrid"  # Vector + keyword search
    MULTI_QUERY = "multi_query"  # Generate multiple queries
    CONTEXTUAL = "contextual"  # Context-aware retrieval


@dataclass
class RAGConfig:
    """Configuration for RAG pipeline"""
    # Service endpoints (all on-premise)
    llm_endpoint: str = "http://vllm-llama-service.covina-llm:8000"
    embedding_endpoint: str = "http://embedding-service.covina-llm:8080"
    reranker_endpoint: str = "http://reranker-service.covina-llm:8080"
    chromadb_host: str = "chromadb-service.covina"
    chromadb_port: int = 8000
    
    # Collection settings
    collection_name: str = "covina_documents"
    
    # Retrieval settings
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    top_k: int = 10  # Initial retrieval
    top_n: int = 5  # After reranking
    similarity_threshold: float = 0.7
    use_reranker: bool = True
    
    # Chunking settings
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # LLM settings
    max_context_tokens: int = 4096
    temperature: float = 0.3  # Lower for factual responses
    
    # API key
    api_key: str = "vcc-covina-llm-secret-key"
    
    # System prompt for RAG
    system_prompt: str = """Du bist ein präziser Assistent für das VCC-Covina System.
Beantworte Fragen basierend auf den bereitgestellten Dokumenten.
Wenn die Antwort nicht in den Dokumenten zu finden ist, sage das klar.
Zitiere relevante Quellen mit [Quelle: Dokumentname].
Bei rechtlichen Themen weise auf professionelle Beratung hin."""


@dataclass
class Document:
    """Document for RAG processing"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class RetrievedDocument:
    """Retrieved document with relevance score"""
    document: Document
    score: float
    highlights: List[str] = field(default_factory=list)


@dataclass
class RAGResponse:
    """Response from RAG pipeline"""
    answer: str
    sources: List[RetrievedDocument]
    query: str
    context_tokens: int
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGPipeline:
    """
    Self-hosted RAG Pipeline
    
    Features:
    - Multiple retrieval strategies
    - Hybrid search (semantic + keyword)
    - Reranking with cross-encoder
    - Context compression
    - Source attribution
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self) -> "RAGPipeline":
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
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def query(
        self,
        question: str,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> RAGResponse:
        """
        Execute RAG query
        
        Args:
            question: User question
            filters: Optional metadata filters
            **kwargs: Override config parameters
            
        Returns:
            RAGResponse with answer and sources
        """
        import time
        start_time = time.time()
        
        await self._ensure_session()
        
        # Step 1: Retrieve relevant documents
        retrieved_docs = await self._retrieve(question, filters)
        
        # Step 2: Rerank if enabled
        if self.config.use_reranker and len(retrieved_docs) > 0:
            retrieved_docs = await self._rerank(question, retrieved_docs)
        
        # Step 3: Build context
        context = self._build_context(retrieved_docs)
        
        # Step 4: Generate answer
        answer = await self._generate_answer(question, context)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return RAGResponse(
            answer=answer,
            sources=retrieved_docs[:self.config.top_n],
            query=question,
            context_tokens=len(context.split()),  # Approximate
            latency_ms=latency_ms,
            metadata={
                "strategy": self.config.strategy.value,
                "retrieved_count": len(retrieved_docs),
                "filters": filters
            }
        )
    
    async def _retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedDocument]:
        """Retrieve documents based on strategy"""
        
        if self.config.strategy == RetrievalStrategy.SEMANTIC:
            return await self._semantic_retrieve(query, filters)
        elif self.config.strategy == RetrievalStrategy.HYBRID:
            return await self._hybrid_retrieve(query, filters)
        elif self.config.strategy == RetrievalStrategy.MULTI_QUERY:
            return await self._multi_query_retrieve(query, filters)
        else:
            return await self._semantic_retrieve(query, filters)
    
    async def _semantic_retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedDocument]:
        """Pure semantic/vector retrieval"""
        
        # Get query embedding
        embedding = await self._get_embedding(query)
        
        # Query ChromaDB
        results = await self._query_chromadb(
            embedding=embedding,
            n_results=self.config.top_k,
            where=filters
        )
        
        return self._parse_chromadb_results(results)
    
    async def _hybrid_retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedDocument]:
        """Hybrid retrieval combining semantic and keyword search"""
        
        # Parallel retrieval
        semantic_task = self._semantic_retrieve(query, filters)
        keyword_task = self._keyword_retrieve(query, filters)
        
        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )
        
        # Merge and deduplicate
        return self._merge_results(semantic_results, keyword_results)
    
    async def _keyword_retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedDocument]:
        """Keyword-based retrieval"""
        # Query ChromaDB with where_document for text search
        results = await self._query_chromadb(
            query_text=query,
            n_results=self.config.top_k,
            where=filters
        )
        
        return self._parse_chromadb_results(results)
    
    async def _multi_query_retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedDocument]:
        """Generate multiple queries and retrieve for each"""
        
        # Generate query variations using LLM
        variations = await self._generate_query_variations(query)
        
        # Retrieve for all queries in parallel
        tasks = [self._semantic_retrieve(q, filters) for q in variations]
        all_results = await asyncio.gather(*tasks)
        
        # Merge all results
        merged = []
        seen_ids = set()
        for results in all_results:
            for doc in results:
                if doc.document.id not in seen_ids:
                    seen_ids.add(doc.document.id)
                    merged.append(doc)
        
        # Sort by score
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:self.config.top_k]
    
    async def _generate_query_variations(self, query: str) -> List[str]:
        """Generate query variations using LLM"""
        prompt = f"""Generiere 3 verschiedene Varianten der folgenden Suchanfrage,
um unterschiedliche relevante Dokumente zu finden.

Original: {query}

Antworte nur mit den 3 Varianten, eine pro Zeile."""
        
        response = await self._llm_generate(prompt, max_tokens=200)
        variations = [query]  # Include original
        variations.extend([v.strip() for v in response.split("\n") if v.strip()])
        return variations[:4]  # Max 4 queries
    
    async def _rerank(
        self,
        query: str,
        documents: List[RetrievedDocument]
    ) -> List[RetrievedDocument]:
        """Rerank documents using cross-encoder"""
        
        if len(documents) == 0:
            return documents
        
        # Prepare reranking request
        texts = [doc.document.content[:512] for doc in documents]  # Truncate for efficiency
        
        try:
            async with self._session.post(
                f"{self.config.reranker_endpoint}/rerank",
                json={
                    "query": query,
                    "texts": texts,
                    "return_documents": False
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Update scores based on reranking
                    for i, score_info in enumerate(data):
                        idx = score_info.get("index", i)
                        if idx < len(documents):
                            documents[idx] = RetrievedDocument(
                                document=documents[idx].document,
                                score=score_info.get("score", documents[idx].score),
                                highlights=documents[idx].highlights
                            )
                    
                    # Resort by new scores
                    documents.sort(key=lambda x: x.score, reverse=True)
                    
        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")
        
        return documents
    
    def _build_context(self, documents: List[RetrievedDocument]) -> str:
        """Build context string from retrieved documents"""
        
        context_parts = []
        total_tokens = 0
        max_tokens = self.config.max_context_tokens
        
        for i, doc in enumerate(documents[:self.config.top_n]):
            # Estimate tokens (rough: 4 chars per token)
            doc_tokens = len(doc.document.content) // 4
            
            if total_tokens + doc_tokens > max_tokens:
                # Truncate if needed
                remaining = max_tokens - total_tokens
                truncated = doc.document.content[:remaining * 4]
                context_parts.append(f"[Dokument {i+1}: {doc.document.metadata.get('filename', 'Unbekannt')}]\n{truncated}...\n")
                break
            
            context_parts.append(
                f"[Dokument {i+1}: {doc.document.metadata.get('filename', 'Unbekannt')}]\n{doc.document.content}\n"
            )
            total_tokens += doc_tokens
        
        return "\n---\n".join(context_parts)
    
    async def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using LLM"""
        
        prompt = f"""Kontext aus relevanten Dokumenten:
{context}

---

Frage: {question}

Beantworte die Frage basierend auf dem Kontext. Zitiere relevante Quellen."""
        
        return await self._llm_generate(prompt)
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        
        async with self._session.post(
            f"{self.config.embedding_endpoint}/embed",
            json={"inputs": text}
        ) as response:
            if response.status != 200:
                raise RAGError(f"Embedding request failed: {response.status}")
            
            data = await response.json()
            return data[0] if isinstance(data, list) else data.get("embedding", [])
    
    async def _query_chromadb(
        self,
        embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query ChromaDB"""
        
        url = f"http://{self.config.chromadb_host}:{self.config.chromadb_port}"
        
        query_body = {
            "n_results": n_results
        }
        
        if embedding:
            query_body["query_embeddings"] = [embedding]
        if query_text:
            query_body["query_texts"] = [query_text]
        if where:
            query_body["where"] = where
        
        async with self._session.post(
            f"{url}/api/v1/collections/{self.config.collection_name}/query",
            json=query_body
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise RAGError(f"ChromaDB query failed: {error}")
            
            return await response.json()
    
    def _parse_chromadb_results(self, results: Dict[str, Any]) -> List[RetrievedDocument]:
        """Parse ChromaDB results into RetrievedDocument objects"""
        
        documents = []
        
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        doc_contents = results.get("documents", [[]])[0]
        
        for i, doc_id in enumerate(ids):
            # Convert distance to similarity score (assuming cosine distance)
            score = 1 - distances[i] if i < len(distances) else 0.5
            
            documents.append(RetrievedDocument(
                document=Document(
                    id=doc_id,
                    content=doc_contents[i] if i < len(doc_contents) else "",
                    metadata=metadatas[i] if i < len(metadatas) else {}
                ),
                score=score
            ))
        
        return documents
    
    def _merge_results(
        self,
        semantic: List[RetrievedDocument],
        keyword: List[RetrievedDocument]
    ) -> List[RetrievedDocument]:
        """Merge semantic and keyword results using reciprocal rank fusion"""
        
        k = 60  # RRF constant
        scores: Dict[str, Tuple[float, RetrievedDocument]] = {}
        
        # Score from semantic
        for rank, doc in enumerate(semantic):
            doc_id = doc.document.id
            rrf_score = 1 / (k + rank + 1)
            scores[doc_id] = (rrf_score, doc)
        
        # Add scores from keyword
        for rank, doc in enumerate(keyword):
            doc_id = doc.document.id
            rrf_score = 1 / (k + rank + 1)
            if doc_id in scores:
                scores[doc_id] = (scores[doc_id][0] + rrf_score, doc)
            else:
                scores[doc_id] = (rrf_score, doc)
        
        # Sort by combined score
        merged = sorted(scores.values(), key=lambda x: x[0], reverse=True)
        
        return [
            RetrievedDocument(
                document=doc.document,
                score=score,
                highlights=doc.highlights
            )
            for score, doc in merged
        ]
    
    async def _llm_generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate text using LLM"""
        
        async with self._session.post(
            f"{self.config.llm_endpoint}/v1/chat/completions",
            json={
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "messages": [
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": self.config.temperature
            }
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise RAGError(f"LLM generation failed: {error}")
            
            data = await response.json()
            return data["choices"][0]["message"]["content"]
    
    async def index_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> str:
        """
        Index a document for RAG retrieval
        
        Args:
            content: Document content
            metadata: Document metadata
            doc_id: Optional document ID (generated if not provided)
            
        Returns:
            Document ID
        """
        await self._ensure_session()
        
        # Generate ID if not provided
        if doc_id is None:
            doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Chunk document
        chunks = self._chunk_text(content)
        
        # Get embeddings for chunks
        embeddings = await asyncio.gather(*[
            self._get_embedding(chunk) for chunk in chunks
        ])
        
        # Add to ChromaDB
        url = f"http://{self.config.chromadb_host}:{self.config.chromadb_port}"
        
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        chunk_metadatas = [
            {**metadata, "chunk_index": i, "parent_id": doc_id}
            for i in range(len(chunks))
        ]
        
        async with self._session.post(
            f"{url}/api/v1/collections/{self.config.collection_name}/add",
            json={
                "ids": chunk_ids,
                "embeddings": embeddings,
                "documents": chunks,
                "metadatas": chunk_metadatas
            }
        ) as response:
            if response.status not in [200, 201]:
                error = await response.text()
                raise RAGError(f"Failed to index document: {error}")
        
        return doc_id
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        
        chunks = []
        words = text.split()
        
        chunk_words = []
        for word in words:
            chunk_words.append(word)
            if len(chunk_words) >= self.config.chunk_size:
                chunks.append(" ".join(chunk_words))
                # Keep overlap
                chunk_words = chunk_words[-self.config.chunk_overlap:]
        
        # Add remaining
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        
        return chunks
    
    async def health_check(self) -> Dict[str, Any]:
        """Check RAG pipeline health"""
        await self._ensure_session()
        
        results = {}
        
        # Check each service
        services = [
            ("llm", f"{self.config.llm_endpoint}/health"),
            ("embedding", f"{self.config.embedding_endpoint}/health"),
            ("reranker", f"{self.config.reranker_endpoint}/health"),
            ("chromadb", f"http://{self.config.chromadb_host}:{self.config.chromadb_port}/api/v1/heartbeat")
        ]
        
        for name, url in services:
            try:
                async with self._session.get(url) as response:
                    results[name] = {
                        "status": "healthy" if response.status == 200 else "unhealthy",
                        "status_code": response.status
                    }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results


class RAGError(Exception):
    """RAG pipeline error"""
    pass
