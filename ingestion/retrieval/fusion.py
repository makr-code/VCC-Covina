"""
Reciprocal Rank Fusion (RRF) für Hybrid Retrieval.

RRF kombiniert Ergebnisse aus mehreren Retrieval-Systemen:
- Vector Search (ChromaDB)
- Keyword Search (BM25)
- SQL Search (Metadata)

Algorithmus:
    RRF(d) = Σ 1 / (k + rank_i(d))

wobei:
- d = Dokument
- k = RRF-Konstante (default: 60)
- rank_i(d) = Rang von Dokument d in Ergebnisliste i

Features:
- Mehrere Retriever fusionieren
- Konfigurierbare Gewichte (α, β, γ)
- Tie-Breaking bei gleichen Scores
- Normalisierung der Scores

Referenz:
    Cormack, Clarke, Büttcher (2009): "Reciprocal Rank Fusion outperforms Condorcet"
    https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RankedDocument:
    """Dokument mit Ranking-Score."""
    
    doc_id: str
    score: float
    source: str  # "vector", "bm25", "sql"
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FusedDocument:
    """Fusioniertes Dokument mit RRF-Score."""
    
    doc_id: str
    rrf_score: float
    source_scores: Dict[str, float]  # {"vector": 0.95, "bm25": 0.82}
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) Algorithmus.
    
    Kombiniert Rankings aus mehreren Retrieval-Systemen durch:
    1. Berechnung von RRF-Scores für jedes Dokument
    2. Gewichtung nach Retriever-Typ (α, β, γ)
    3. Sortierung nach finalen RRF-Scores
    
    Attributes:
        k: RRF-Konstante (default: 60)
        weights: Gewichte für Retriever {"vector": 0.4, "bm25": 0.4, "sql": 0.2}
    """
    
    def __init__(
        self,
        k: int = 60,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        Args:
            k: RRF-Konstante (höher = sanftere Gewichtung)
            weights: Gewichte für Retriever (default: gleich verteilt)
        """
        self.k = k
        self.weights = weights or {
            'vector': 0.4,
            'bm25': 0.4,
            'sql': 0.2,
        }
        
        # Gewichte normalisieren (Summe = 1.0)
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}
        
        logger.info(f"RRF initialisiert: k={k}, weights={self.weights}")
    
    def fuse(
        self,
        ranked_lists: Dict[str, List[RankedDocument]],
        top_k: Optional[int] = None,
    ) -> List[FusedDocument]:
        """
        Rankings fusionieren mit RRF.
        
        Args:
            ranked_lists: Dict von Rankings {"vector": [...], "bm25": [...]}
            top_k: Top-K Ergebnisse (optional, default: alle)
        
        Returns:
            Liste von FusedDocument (sortiert nach RRF-Score)
        
        Beispiel:
            >>> fusion = ReciprocalRankFusion(k=60)
            >>> results = fusion.fuse({
            ...     "vector": vector_results,
            ...     "bm25": bm25_results,
            ...     "sql": sql_results,
            ... }, top_k=10)
        """
        # Dokument-Index bauen: doc_id -> {source: rank}
        doc_ranks: Dict[str, Dict[str, int]] = {}
        doc_data: Dict[str, Dict[str, Any]] = {}
        
        for source, ranked_docs in ranked_lists.items():
            weight = self.weights.get(source, 0.0)
            if weight == 0.0:
                logger.warning(f"Retriever '{source}' hat Gewicht 0.0, ignoriert")
                continue
            
            for rank, doc in enumerate(ranked_docs, start=1):
                # Ranks sammeln
                if doc.doc_id not in doc_ranks:
                    doc_ranks[doc.doc_id] = {}
                doc_ranks[doc.doc_id][source] = rank
                
                # Dokument-Daten speichern (erste Quelle gewinnt)
                if doc.doc_id not in doc_data:
                    doc_data[doc.doc_id] = {
                        'text': doc.text,
                        'metadata': doc.metadata or {},
                    }
        
        # RRF-Scores berechnen
        fused_docs: List[FusedDocument] = []
        
        for doc_id, ranks in doc_ranks.items():
            rrf_score = 0.0
            source_scores = {}
            
            for source, rank in ranks.items():
                weight = self.weights.get(source, 0.0)
                score = weight / (self.k + rank)
                rrf_score += score
                source_scores[source] = score
            
            fused_docs.append(FusedDocument(
                doc_id=doc_id,
                rrf_score=rrf_score,
                source_scores=source_scores,
                text=doc_data[doc_id].get('text'),
                metadata=doc_data[doc_id].get('metadata'),
            ))
        
        # Sortieren nach RRF-Score (descending)
        fused_docs.sort(key=lambda d: d.rrf_score, reverse=True)
        
        # Top-K
        if top_k:
            fused_docs = fused_docs[:top_k]
        
        logger.debug(f"RRF fusioniert: {len(fused_docs)} Dokumente")
        return fused_docs
    
    def analyze_fusion(
        self,
        fused_docs: List[FusedDocument],
    ) -> Dict[str, Any]:
        """
        Analyse der Fusion-Ergebnisse.
        
        Returns:
            Dict mit Statistiken:
            - source_coverage: Wie viele Docs pro Quelle
            - avg_sources_per_doc: Durchschnittlich wie viele Quellen pro Doc
            - top_sources: Häufigste Quellen in Top-10
        """
        if not fused_docs:
            return {
                'source_coverage': {},
                'avg_sources_per_doc': 0,
                'top_sources': {},
            }
        
        # Source Coverage
        source_coverage = {}
        for doc in fused_docs:
            for source in doc.source_scores.keys():
                source_coverage[source] = source_coverage.get(source, 0) + 1
        
        # Durchschnittliche Quellen pro Doc
        avg_sources = sum(len(d.source_scores) for d in fused_docs) / len(fused_docs)
        
        # Top-10 Quellen-Verteilung
        top_10_sources = {}
        for doc in fused_docs[:10]:
            for source in doc.source_scores.keys():
                top_10_sources[source] = top_10_sources.get(source, 0) + 1
        
        return {
            'total_docs': len(fused_docs),
            'source_coverage': source_coverage,
            'avg_sources_per_doc': round(avg_sources, 2),
            'top_10_sources': top_10_sources,
        }


class HybridRetrieverFusion:
    """
    High-Level Wrapper für Hybrid Retrieval mit RRF.
    
    Orchestriert:
    1. Parallel-Retrieval (Vector + BM25 + SQL)
    2. RRF-Fusion
    
    Verwendung:
        >>> fusion = HybridRetrieverFusion(
        ...     vector_retriever=chroma_client,
        ...     bm25_retriever=bm25_index,
        ...     sql_retriever=sqlite_client,
        ... )
        >>> results = await fusion.retrieve("Antrag Wohngeld", top_k=10)
    """
    
    def __init__(
        self,
        vector_retriever: Any,
        bm25_retriever: Any,
        sql_retriever: Optional[Any] = None,
        rrf_k: int = 60,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        Args:
            vector_retriever: Vector Search (z.B. ChromaDB)
            bm25_retriever: BM25 Index
            sql_retriever: SQL Search (optional)
            rrf_k: RRF-Konstante
            weights: Retriever-Gewichte
        """
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.sql_retriever = sql_retriever
        
        self.rrf = ReciprocalRankFusion(k=rrf_k, weights=weights)
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[FusedDocument]:
        """
        Hybrid Retrieval durchführen.
        
        Args:
            query: Suchanfrage
            top_k: Anzahl finaler Ergebnisse
        
        Returns:
            Liste von FusedDocument (RRF-sortiert)
        """
        import asyncio
        
        # Parallel-Retrieval
        tasks = []
        
        # Vector Search
        if self.vector_retriever:
            tasks.append(self._vector_search(query, top_k * 2))
        
        # BM25 Search
        if self.bm25_retriever:
            tasks.append(self._bm25_search(query, top_k * 2))
        
        # SQL Search
        if self.sql_retriever:
            tasks.append(self._sql_search(query, top_k * 2))
        
        results = await asyncio.gather(*tasks)
        
        # Rankings zusammenführen
        ranked_lists = {}
        if self.vector_retriever:
            ranked_lists['vector'] = results[0]
        if self.bm25_retriever:
            idx = 1 if self.vector_retriever else 0
            ranked_lists['bm25'] = results[idx]
        if self.sql_retriever:
            idx = len(results) - 1
            ranked_lists['sql'] = results[idx]
        
        # RRF-Fusion
        fused = self.rrf.fuse(ranked_lists, top_k=top_k)
        
        return fused
    
    async def _vector_search(
        self,
        query: str,
        top_k: int,
    ) -> List[RankedDocument]:
        """Vector Search (intern)."""
        # TODO: ChromaDB Integration
        # results = await self.vector_retriever.search(query, limit=top_k)
        # return [RankedDocument(doc_id=r['id'], score=r['score'], source='vector') for r in results]
        return []
    
    async def _bm25_search(
        self,
        query: str,
        top_k: int,
    ) -> List[RankedDocument]:
        """BM25 Search (intern)."""
        results = await self.bm25_retriever.search(query, top_k=top_k)
        return [
            RankedDocument(
                doc_id=r.doc_id,
                score=r.score,
                source='bm25',
                text=r.text,
                metadata=r.metadata,
            )
            for r in results
        ]
    
    async def _sql_search(
        self,
        query: str,
        top_k: int,
    ) -> List[RankedDocument]:
        """SQL Search (intern)."""
        # TODO: SQLite Integration
        # results = await self.sql_retriever.search(query, limit=top_k)
        # return [RankedDocument(doc_id=r['id'], score=r['score'], source='sql') for r in results]
        return []
