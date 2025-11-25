"""
VCC-Covina Embedding Service Client
Self-hosted embedding generation with Text Embedding Inference
On-premise, no vendor dependencies

Usage:
    from ai_ml.embeddings import EmbeddingService, EmbeddingConfig
    
    config = EmbeddingConfig(
        endpoint="http://embedding-service.covina-llm:8080"
    )
    embeddings = EmbeddingService(config)
    
    vectors = await embeddings.embed(["Document text 1", "Document text 2"])
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import aiohttp
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingModel(Enum):
    """Available embedding models (all self-hosted)"""
    MULTILINGUAL_E5_LARGE = "intfloat/multilingual-e5-large"
    LEGAL_BERT = "nlpaueb/legal-bert-base-uncased"
    GERMAN_BERT = "deutsche-telekom/bert-multi-english-german-squad2"
    BGE_M3 = "BAAI/bge-m3"
    SENTENCE_TRANSFORMERS = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding service"""
    # Service endpoint (on-premise)
    endpoint: str = "http://embedding-service.covina-llm:8080"
    gpu_endpoint: str = "http://embedding-service-gpu.covina-llm:8080"
    
    # Model settings
    model: EmbeddingModel = EmbeddingModel.MULTILINGUAL_E5_LARGE
    
    # Batch settings
    batch_size: int = 32
    max_length: int = 512
    
    # Request settings
    timeout: float = 60.0
    max_retries: int = 3
    use_gpu: bool = True  # Try GPU endpoint first
    
    # Normalization
    normalize: bool = True


@dataclass
class EmbeddingResult:
    """Result from embedding service"""
    embeddings: List[List[float]]
    model: str
    dimensions: int
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmbeddingService:
    """
    Self-hosted Embedding Service
    
    Features:
    - Multiple model support
    - Batch processing
    - GPU acceleration
    - Automatic failover (GPU -> CPU)
    - Caching support
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._embedding_cache: Dict[str, List[float]] = {}
        self._cache_hits = 0
        self._total_requests = 0
    
    async def __aenter__(self) -> "EmbeddingService":
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def embed(
        self,
        texts: Union[str, List[str]],
        use_cache: bool = True,
        **kwargs
    ) -> EmbeddingResult:
        """
        Generate embeddings for texts
        
        Args:
            texts: Single text or list of texts
            use_cache: Use embedding cache
            **kwargs: Override config parameters
            
        Returns:
            EmbeddingResult with embeddings
        """
        import time
        start_time = time.time()
        
        await self._ensure_session()
        
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]
        
        self._total_requests += len(texts)
        
        # Check cache
        embeddings = []
        texts_to_embed = []
        cache_indices = []
        
        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._cache_key(text)
                if cache_key in self._embedding_cache:
                    embeddings.append(self._embedding_cache[cache_key])
                    self._cache_hits += 1
                else:
                    texts_to_embed.append(text)
                    cache_indices.append(i)
        else:
            texts_to_embed = texts
            cache_indices = list(range(len(texts)))
        
        # Generate embeddings for non-cached texts
        if texts_to_embed:
            new_embeddings = await self._batch_embed(texts_to_embed, **kwargs)
            
            # Update cache
            for i, (text, emb) in enumerate(zip(texts_to_embed, new_embeddings)):
                cache_key = self._cache_key(text)
                self._embedding_cache[cache_key] = emb
            
            # Merge with cached embeddings
            result_embeddings = [None] * len(texts)
            cache_idx = 0
            new_idx = 0
            
            for i in range(len(texts)):
                if use_cache and i not in cache_indices:
                    result_embeddings[i] = embeddings[cache_idx]
                    cache_idx += 1
                else:
                    result_embeddings[i] = new_embeddings[new_idx]
                    new_idx += 1
            
            embeddings = [e for e in result_embeddings if e is not None]
        
        latency_ms = (time.time() - start_time) * 1000
        
        return EmbeddingResult(
            embeddings=embeddings,
            model=self.config.model.value,
            dimensions=len(embeddings[0]) if embeddings else 0,
            latency_ms=latency_ms,
            metadata={
                "cached": self._cache_hits,
                "total": self._total_requests,
                "batch_size": len(texts)
            }
        )
    
    async def _batch_embed(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """Generate embeddings in batches"""
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            batch_embeddings = await self._embed_batch(batch, **kwargs)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def _embed_batch(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """Embed a single batch"""
        
        # Truncate texts
        truncated = [t[:self.config.max_length * 4] for t in texts]  # Approx chars
        
        # Try GPU endpoint first, fallback to CPU
        endpoints = []
        if self.config.use_gpu:
            endpoints.append(self.config.gpu_endpoint)
        endpoints.append(self.config.endpoint)
        
        last_error = None
        for endpoint in endpoints:
            for attempt in range(self.config.max_retries):
                try:
                    async with self._session.post(
                        f"{endpoint}/embed",
                        json={"inputs": truncated}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            embeddings = data if isinstance(data, list) else data.get("embeddings", [])
                            
                            # Normalize if configured
                            if self.config.normalize:
                                embeddings = self._normalize_embeddings(embeddings)
                            
                            return embeddings
                        else:
                            error_text = await response.text()
                            last_error = f"HTTP {response.status}: {error_text}"
                            
                except aiohttp.ClientError as e:
                    last_error = str(e)
                    logger.warning(f"Embedding request failed: {e}")
                
                # Wait before retry
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        raise EmbeddingError(f"All embedding endpoints failed: {last_error}")
    
    def _normalize_embeddings(self, embeddings: List[List[float]]) -> List[List[float]]:
        """L2 normalize embeddings"""
        normalized = []
        for emb in embeddings:
            arr = np.array(emb)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            normalized.append(arr.tolist())
        return normalized
    
    def _cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    async def similarity(
        self,
        query: str,
        documents: List[str]
    ) -> List[float]:
        """
        Calculate similarity between query and documents
        
        Args:
            query: Query text
            documents: List of documents to compare
            
        Returns:
            List of similarity scores (0-1)
        """
        # Get embeddings
        all_texts = [query] + documents
        result = await self.embed(all_texts)
        
        query_emb = np.array(result.embeddings[0])
        doc_embs = np.array(result.embeddings[1:])
        
        # Cosine similarity
        similarities = np.dot(doc_embs, query_emb)
        return similarities.tolist()
    
    async def cluster(
        self,
        texts: List[str],
        n_clusters: int = 5
    ) -> Dict[str, Any]:
        """
        Cluster texts based on embeddings
        
        Args:
            texts: List of texts to cluster
            n_clusters: Number of clusters
            
        Returns:
            Cluster assignments and centroids
        """
        from sklearn.cluster import KMeans
        
        # Get embeddings
        result = await self.embed(texts)
        embeddings = np.array(result.embeddings)
        
        # Cluster
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        return {
            "labels": labels.tolist(),
            "centroids": kmeans.cluster_centers_.tolist(),
            "inertia": kmeans.inertia_
        }
    
    async def deduplicate(
        self,
        texts: List[str],
        threshold: float = 0.95
    ) -> List[int]:
        """
        Find duplicate texts based on embedding similarity
        
        Args:
            texts: List of texts
            threshold: Similarity threshold for duplicates
            
        Returns:
            List of indices to keep (deduplicated)
        """
        if len(texts) <= 1:
            return list(range(len(texts)))
        
        # Get embeddings
        result = await self.embed(texts)
        embeddings = np.array(result.embeddings)
        
        # Pairwise similarity
        similarity_matrix = np.dot(embeddings, embeddings.T)
        
        # Find duplicates
        keep_indices = []
        removed = set()
        
        for i in range(len(texts)):
            if i in removed:
                continue
            keep_indices.append(i)
            
            # Mark similar texts as duplicates
            for j in range(i + 1, len(texts)):
                if j not in removed and similarity_matrix[i, j] >= threshold:
                    removed.add(j)
        
        return keep_indices
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        self._cache_hits = 0
        self._total_requests = 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        cache_size = len(self._embedding_cache)
        hit_rate = self._cache_hits / max(self._total_requests, 1)
        
        return {
            "cache_size": cache_size,
            "cache_hits": self._cache_hits,
            "total_requests": self._total_requests,
            "hit_rate": hit_rate,
            "model": self.config.model.value,
            "endpoint": self.config.endpoint
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check embedding service health"""
        await self._ensure_session()
        
        results = {}
        endpoints = [
            ("cpu", self.config.endpoint),
            ("gpu", self.config.gpu_endpoint)
        ]
        
        for name, endpoint in endpoints:
            try:
                async with self._session.get(f"{endpoint}/health") as response:
                    results[name] = {
                        "status": "healthy" if response.status == 200 else "unhealthy",
                        "endpoint": endpoint,
                        "status_code": response.status
                    }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "endpoint": endpoint,
                    "error": str(e)
                }
        
        return results


class EmbeddingError(Exception):
    """Embedding service error"""
    pass
