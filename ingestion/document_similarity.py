"""
Document Similarity Engine

Compute similarity between documents using embeddings and provide
clustering, duplicate detection, and recommendation features.

Author: GitHub Copilot
Date: 2025-11-19
"""

from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

# Graceful numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[WARNING] numpy not installed. Document similarity features will be limited.")
    print("  Install with: pip install numpy scikit-learn")


@dataclass
class SimilarityResult:
    """Result of similarity computation"""
    document_id: str
    similarity_score: float
    method: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'document_id': self.document_id,
            'similarity_score': self.similarity_score,
            'method': self.method,
            'metadata': self.metadata or {}
        }


@dataclass
class DocumentCluster:
    """Document cluster result"""
    cluster_id: int
    document_ids: List[str]
    centroid: Optional[Any] = None  # np.ndarray when numpy available
    avg_similarity: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'cluster_id': self.cluster_id,
            'document_ids': self.document_ids,
            'document_count': len(self.document_ids),
            'avg_similarity': self.avg_similarity
        }


class DocumentSimilarityEngine:
    """
    Compute document similarity using embeddings.
    
    Features:
    - Cosine similarity between documents
    - Find similar documents (top-k)
    - Duplicate detection
    - Document clustering (K-means)
    - Recommendations
    """
    
    def __init__(self, chromadb_client=None, postgresql_client=None, neo4j_driver=None):
        """
        Initialize similarity engine.
        
        Args:
            chromadb_client: ChromaDB client for embeddings
            postgresql_client: PostgreSQL client for metadata
            neo4j_driver: Neo4j driver for relationship storage
        """
        self.chromadb = chromadb_client
        self.postgresql = postgresql_client
        self.neo4j = neo4j_driver
        self._embedding_cache = {}
    
    def get_document_embedding(self, document_id: str, use_cache: bool = True) -> Optional[Any]:
        """
        Get document embedding by averaging all chunk embeddings.
        
        Args:
            document_id: Document ID
            use_cache: Use cached embeddings if available
        
        Returns:
            numpy array of shape (embedding_dim,) or None
        """
        if not NUMPY_AVAILABLE:
            print("[ERROR] numpy required for embeddings. Install: pip install numpy")
            return None
        
        # Check cache
        if use_cache and document_id in self._embedding_cache:
            return self._embedding_cache[document_id]
        
        if not self.chromadb:
            return None
        
        try:
            # Query ChromaDB for all chunks of this document
            # Assuming metadata has 'document_id' field
            results = self.chromadb.query(
                where={'document_id': document_id},
                n_results=1000  # Get all chunks
            )
            
            if not results or not results.get('embeddings'):
                return None
            
            # Average all chunk embeddings
            embeddings = np.array(results['embeddings'])
            avg_embedding = np.mean(embeddings, axis=0)
            
            # Cache result
            if use_cache:
                self._embedding_cache[document_id] = avg_embedding
            
            return avg_embedding
        
        except Exception as e:
            print(f"Error getting embedding for {document_id}: {e}")
            return None
    
    def cosine_similarity(self, embedding1: Any, embedding2: Any) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not NUMPY_AVAILABLE:
            print("[ERROR] numpy required for similarity. Install: pip install numpy")
            return 0.0
        
        # Normalize
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Convert from [-1, 1] to [0, 1]
        return (similarity + 1.0) / 2.0
    
    def find_similar_documents(
        self,
        document_id: str,
        top_k: int = 5,
        threshold: float = 0.7,
        exclude_self: bool = True
    ) -> List[SimilarityResult]:
        """
        Find top-k most similar documents.
        
        Args:
            document_id: Source document ID
            top_k: Number of results to return
            threshold: Minimum similarity score (0.0-1.0)
            exclude_self: Exclude the source document from results
        
        Returns:
            List of SimilarityResult ordered by similarity (descending)
        """
        # Get source document embedding
        source_embedding = self.get_document_embedding(document_id)
        if source_embedding is None:
            return []
        
        # Get all document IDs from PostgreSQL
        if not self.postgresql:
            return []
        
        try:
            # Query all documents
            all_docs = self.postgresql.execute_query(
                "SELECT document_id FROM documents"
            )
            
            if not all_docs:
                return []
            
            # Compute similarities
            results = []
            for doc_row in all_docs:
                target_id = doc_row['document_id']
                
                # Skip self if requested
                if exclude_self and target_id == document_id:
                    continue
                
                # Get target embedding
                target_embedding = self.get_document_embedding(target_id)
                if target_embedding is None:
                    continue
                
                # Compute similarity
                similarity = self.cosine_similarity(source_embedding, target_embedding)
                
                # Apply threshold
                if similarity >= threshold:
                    results.append(SimilarityResult(
                        document_id=target_id,
                        similarity_score=similarity,
                        method='cosine_embedding'
                    ))
            
            # Sort by similarity descending
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # Return top-k
            return results[:top_k]
        
        except Exception as e:
            print(f"Error finding similar documents: {e}")
            return []
    
    def detect_duplicates(
        self,
        threshold: float = 0.95,
        document_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Detect potential duplicate documents.
        
        Args:
            threshold: Minimum similarity to consider as duplicate (default: 0.95)
            document_ids: List of document IDs to check (None = all)
        
        Returns:
            List of (doc_id_1, doc_id_2, similarity_score) tuples
        """
        duplicates = []
        
        # Get document IDs
        if document_ids is None:
            if not self.postgresql:
                return []
            
            try:
                all_docs = self.postgresql.execute_query(
                    "SELECT document_id FROM documents"
                )
                document_ids = [row['document_id'] for row in all_docs]
            except Exception as e:
                print(f"Error getting document IDs: {e}")
                return []
        
        # Compare all pairs
        for i, doc_id_1 in enumerate(document_ids):
            emb1 = self.get_document_embedding(doc_id_1)
            if emb1 is None:
                continue
            
            for doc_id_2 in document_ids[i+1:]:
                emb2 = self.get_document_embedding(doc_id_2)
                if emb2 is None:
                    continue
                
                similarity = self.cosine_similarity(emb1, emb2)
                
                if similarity >= threshold:
                    duplicates.append((doc_id_1, doc_id_2, similarity))
        
        # Sort by similarity descending
        duplicates.sort(key=lambda x: x[2], reverse=True)
        
        return duplicates
    
    def cluster_documents(
        self,
        document_ids: List[str],
        n_clusters: int = 5,
        method: str = 'kmeans'
    ) -> List[DocumentCluster]:
        """
        Cluster documents using K-means on embeddings.
        
        Args:
            document_ids: List of document IDs to cluster
            n_clusters: Number of clusters
            method: Clustering method ('kmeans' only for now)
        
        Returns:
            List of DocumentCluster objects
        """
        if not NUMPY_AVAILABLE:
            print("[ERROR] numpy required for clustering. Install: pip install numpy scikit-learn")
            return []
        
        if method != 'kmeans':
            raise ValueError(f"Unsupported clustering method: {method}")
        
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            print("sklearn not installed, clustering unavailable")
            print("  Install with: pip install scikit-learn")
            return []
        
        # Get embeddings
        embeddings = []
        valid_doc_ids = []
        
        for doc_id in document_ids:
            emb = self.get_document_embedding(doc_id)
            if emb is not None:
                embeddings.append(emb)
                valid_doc_ids.append(doc_id)
        
        if len(embeddings) < n_clusters:
            print(f"Not enough documents ({len(embeddings)}) for {n_clusters} clusters")
            return []
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings)
        
        # K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings_array)
        
        # Group documents by cluster
        clusters_dict = defaultdict(list)
        for doc_id, label in zip(valid_doc_ids, cluster_labels):
            clusters_dict[label].append(doc_id)
        
        # Create cluster objects
        clusters = []
        for cluster_id, doc_ids in clusters_dict.items():
            # Compute average intra-cluster similarity
            cluster_embeddings = [self.get_document_embedding(doc_id) for doc_id in doc_ids]
            cluster_embeddings = [e for e in cluster_embeddings if e is not None]
            
            avg_sim = None
            if len(cluster_embeddings) > 1:
                # Compute pairwise similarities
                similarities = []
                for i, emb1 in enumerate(cluster_embeddings):
                    for emb2 in cluster_embeddings[i+1:]:
                        sim = self.cosine_similarity(emb1, emb2)
                        similarities.append(sim)
                
                if similarities:
                    avg_sim = np.mean(similarities)
            
            clusters.append(DocumentCluster(
                cluster_id=cluster_id,
                document_ids=doc_ids,
                centroid=kmeans.cluster_centers_[cluster_id],
                avg_similarity=avg_sim
            ))
        
        return clusters
    
    def create_similarity_relationships_neo4j(
        self,
        document_id: str,
        similar_docs: List[SimilarityResult],
        relationship_type: str = 'SIMILAR_TO'
    ) -> int:
        """
        Create similarity relationships in Neo4j graph.
        
        Args:
            document_id: Source document ID
            similar_docs: List of similar documents
            relationship_type: Neo4j relationship type
        
        Returns:
            Number of relationships created
        """
        if not self.neo4j:
            return 0
        
        count = 0
        try:
            with self.neo4j.session() as session:
                for similar in similar_docs:
                    query = """
                    MATCH (doc1:Document {id: $doc1_id})
                    MATCH (doc2:Document {id: $doc2_id})
                    MERGE (doc1)-[r:""" + relationship_type + """]->(doc2)
                    SET r.similarity_score = $score,
                        r.method = $method,
                        r.created_at = datetime()
                    RETURN r
                    """
                    
                    session.run(query, {
                        'doc1_id': document_id,
                        'doc2_id': similar.document_id,
                        'score': similar.similarity_score,
                        'method': similar.method
                    })
                    
                    count += 1
        
        except Exception as e:
            print(f"Error creating Neo4j relationships: {e}")
        
        return count
    
    def get_recommendations(
        self,
        document_id: str,
        top_k: int = 5,
        diversity_weight: float = 0.3
    ) -> List[SimilarityResult]:
        """
        Get document recommendations with diversity.
        
        Uses similarity but also considers diversity to avoid
        recommending too many very similar documents.
        
        Args:
            document_id: Source document ID
            top_k: Number of recommendations
            diversity_weight: Weight for diversity (0.0-1.0)
        
        Returns:
            List of recommended documents
        """
        # Get more candidates than needed
        candidates = self.find_similar_documents(
            document_id,
            top_k=top_k * 3,
            threshold=0.5
        )
        
        if not candidates:
            return []
        
        # Diversified selection
        selected = []
        selected_embeddings = []
        
        source_emb = self.get_document_embedding(document_id)
        
        for candidate in candidates:
            if len(selected) >= top_k:
                break
            
            cand_emb = self.get_document_embedding(candidate.document_id)
            if cand_emb is None:
                continue
            
            # Compute diversity score (inverse of similarity to already selected)
            diversity_score = 1.0
            if selected_embeddings:
                similarities_to_selected = [
                    self.cosine_similarity(cand_emb, sel_emb)
                    for sel_emb in selected_embeddings
                ]
                diversity_score = 1.0 - np.mean(similarities_to_selected)
            
            # Combined score
            combined_score = (
                (1.0 - diversity_weight) * candidate.similarity_score +
                diversity_weight * diversity_score
            )
            
            # Update candidate score
            candidate.similarity_score = combined_score
            candidate.metadata = {
                'original_similarity': candidate.similarity_score,
                'diversity_score': diversity_score,
                'combined_score': combined_score
            }
            
            selected.append(candidate)
            selected_embeddings.append(cand_emb)
        
        return selected
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()


# Example usage
if __name__ == "__main__":
    # Mock example
    print("Document Similarity Engine")
    print("=" * 50)
    print()
    print("Features:")
    print("  - Cosine similarity between documents")
    print("  - Find top-k similar documents")
    print("  - Duplicate detection (threshold: 0.95)")
    print("  - K-means clustering")
    print("  - Diverse recommendations")
    print("  - Neo4j relationship creation")
    print()
    print("Usage:")
    print("  engine = DocumentSimilarityEngine(chromadb, postgresql, neo4j)")
    print("  similar = engine.find_similar_documents('doc_123', top_k=5)")
    print("  duplicates = engine.detect_duplicates(threshold=0.95)")
    print("  clusters = engine.cluster_documents(doc_ids, n_clusters=5)")
