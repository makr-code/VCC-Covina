"""
Cross-Encoder Re-Ranking für Covina.

Re-Ranking verbessert Präzision durch:
1. Bi-Encoder (SBERT) für initiales Retrieval → schnell, ca. 10k docs/sec
2. Cross-Encoder für Re-Ranking Top-K → langsam, ca. 40 pairs/sec, aber präzise

Cross-Encoder bewertet Query-Document-Paare direkt:
    score = CrossEncoder(query + [SEP] + document)

Im Gegensatz zu Bi-Encodern (separate Embeddings) kann der Cross-Encoder
Interaktionen zwischen Query und Document modellieren.

Features:
- sentence-transformers Integration
- Batch-Processing für Performance
- Mehrere Modelle verfügbar (ms-marco, distilbert)
- Async API

Verwendung:
    >>> reranker = CrossEncoderReranker(model_name="ms-marco-MiniLM-L-6-v2")
    >>> reranked = await reranker.rerank(query, candidates, top_k=10)

Referenz:
    Nogueira, Cho (2019): "Passage Re-ranking with BERT"
    https://arxiv.org/abs/1901.04085
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


@dataclass
class RerankCandidate:
    """Dokument-Kandidat für Re-Ranking."""
    
    doc_id: str
    text: str
    initial_score: float  # Score vom initialen Retrieval (RRF)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RerankResult:
    """Re-Ranking-Ergebnis."""
    
    doc_id: str
    rerank_score: float  # Cross-Encoder Score
    initial_score: float
    text: str
    metadata: Optional[Dict[str, Any]] = None


class CrossEncoderReranker:
    """
    Cross-Encoder Re-Ranker.
    
    Modelle (empfohlen):
    - "ms-marco-MiniLM-L-6-v2": Schnell, gute Qualität (Englisch, ok für Deutsch)
    - "cross-encoder/ms-marco-MiniLM-L-12-v2": Besser, langsamer
    - "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1": Multilingual (inkl. Deutsch)
    
    Performance:
    - MiniLM-L-6: ~40 pairs/sec (CPU), ~400 pairs/sec (GPU)
    - Batch-Size: 16-32 für beste Latency/Throughput
    
    Attributes:
        model: CrossEncoder-Instanz
        model_name: Name des Modells
        batch_size: Batch-Größe für Inferenz
    """
    
    # Verfügbare Modelle
    MODELS = {
        'ms-marco-mini': 'ms-marco-MiniLM-L-6-v2',
        'ms-marco-base': 'cross-encoder/ms-marco-MiniLM-L-12-v2',
        'mmarco-multi': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',
    }
    
    def __init__(
        self,
        model_name: str = "ms-marco-MiniLM-L-6-v2",
        batch_size: int = 16,
        device: Optional[str] = None,
    ):
        """
        Args:
            model_name: Modell-Name (siehe MODELS)
            batch_size: Batch-Größe für Inferenz
            device: Device ('cuda', 'cpu', None=auto)
        """
        # Alias auflösen
        if model_name in self.MODELS:
            model_name = self.MODELS[model_name]
        
        self.model_name = model_name
        self.batch_size = batch_size
        
        logger.info(f"Lade Cross-Encoder: {model_name}")
        self.model = CrossEncoder(model_name, device=device)
        logger.info(f"Cross-Encoder geladen: {model_name}")
    
    async def rerank(
        self,
        query: str,
        candidates: List[RerankCandidate],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        Re-Ranking durchführen.
        
        Args:
            query: Suchanfrage
            candidates: Kandidaten vom initialen Retrieval
            top_k: Top-K Ergebnisse (optional, default: alle)
        
        Returns:
            Liste von RerankResult (sortiert nach rerank_score)
        
        Beispiel:
            >>> candidates = [
            ...     RerankCandidate("doc1", "Text 1", 0.95),
            ...     RerankCandidate("doc2", "Text 2", 0.87),
            ... ]
            >>> results = await reranker.rerank("Query", candidates, top_k=5)
        """
        if not candidates:
            return []
        
        # Query-Document-Paare erstellen
        pairs = [(query, cand.text) for cand in candidates]
        
        # Cross-Encoder Scores berechnen (async)
        scores = await self._predict_scores(pairs)
        
        # Ergebnisse formatieren
        results = [
            RerankResult(
                doc_id=cand.doc_id,
                rerank_score=float(score),
                initial_score=cand.initial_score,
                text=cand.text,
                metadata=cand.metadata,
            )
            for cand, score in zip(candidates, scores)
        ]
        
        # Sortieren nach rerank_score
        results.sort(key=lambda r: r.rerank_score, reverse=True)
        
        # Top-K
        if top_k:
            results = results[:top_k]
        
        logger.debug(f"Re-Ranked {len(candidates)} → {len(results)} Dokumente")
        return results
    
    async def _predict_scores(self, pairs: List[tuple]) -> List[float]:
        """
        Cross-Encoder Scores berechnen (async).
        
        Nutzt asyncio.to_thread für non-blocking Inferenz.
        """
        loop = asyncio.get_event_loop()
        
        # Cross-Encoder predict ist CPU-bound → Thread-Pool
        scores = await loop.run_in_executor(
            None,
            self.model.predict,
            pairs,
            self.batch_size,
        )
        
        return scores.tolist()
    
    def rerank_sync(
        self,
        query: str,
        candidates: List[RerankCandidate],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        Synchrone Re-Ranking-Version (für Legacy-Code).
        
        Args:
            query: Suchanfrage
            candidates: Kandidaten
            top_k: Top-K Ergebnisse
        
        Returns:
            Liste von RerankResult
        """
        if not candidates:
            return []
        
        pairs = [(query, cand.text) for cand in candidates]
        scores = self.model.predict(pairs, batch_size=self.batch_size)
        
        results = [
            RerankResult(
                doc_id=cand.doc_id,
                rerank_score=float(score),
                initial_score=cand.initial_score,
                text=cand.text,
                metadata=cand.metadata,
            )
            for cand, score in zip(candidates, scores)
        ]
        
        results.sort(key=lambda r: r.rerank_score, reverse=True)
        
        if top_k:
            results = results[:top_k]
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Modell-Informationen.
        
        Returns:
            Dict mit Modell-Details
        """
        return {
            'model_name': self.model_name,
            'batch_size': self.batch_size,
            'device': str(self.model.device),
            'max_length': self.model.max_length,
        }


class AdaptiveReranker:
    """
    Adaptive Re-Ranking-Strategie.
    
    Features:
    - Dynamische Top-K-Selektion basierend auf Score-Gap
    - Score-Threshold für Qualitätssicherung
    - Optional: Initial Score + Rerank Score kombinieren
    
    Verwendung:
        >>> reranker = AdaptiveReranker(
        ...     cross_encoder=CrossEncoderReranker(),
        ...     score_threshold=0.5,
        ...     combine_scores=True,
        ... )
        >>> results = await reranker.rerank(query, candidates)
    """
    
    def __init__(
        self,
        cross_encoder: CrossEncoderReranker,
        score_threshold: float = 0.5,
        combine_scores: bool = True,
        alpha: float = 0.7,  # Gewicht für rerank_score
    ):
        """
        Args:
            cross_encoder: CrossEncoderReranker-Instanz
            score_threshold: Minimaler Score für Ergebnisse
            combine_scores: Initial Score mit Rerank Score kombinieren
            alpha: Gewicht für rerank_score (1-alpha für initial_score)
        """
        self.cross_encoder = cross_encoder
        self.score_threshold = score_threshold
        self.combine_scores = combine_scores
        self.alpha = alpha
    
    async def rerank(
        self,
        query: str,
        candidates: List[RerankCandidate],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        Adaptives Re-Ranking.
        
        1. Cross-Encoder Re-Ranking
        2. Optional: Scores kombinieren
        3. Threshold-Filterung
        4. Top-K-Selektion
        """
        # Standard Re-Ranking
        results = await self.cross_encoder.rerank(query, candidates)
        
        # Scores kombinieren (gewichteter Durchschnitt)
        if self.combine_scores:
            for res in results:
                # Normalisieren (falls nötig)
                norm_rerank = self._normalize_score(res.rerank_score)
                norm_initial = self._normalize_score(res.initial_score)
                
                combined = (
                    self.alpha * norm_rerank +
                    (1 - self.alpha) * norm_initial
                )
                res.rerank_score = combined
            
            # Neu sortieren
            results.sort(key=lambda r: r.rerank_score, reverse=True)
        
        # Threshold-Filterung
        results = [r for r in results if r.rerank_score >= self.score_threshold]
        
        # Top-K
        if top_k:
            results = results[:top_k]
        
        return results
    
    def _normalize_score(self, score: float) -> float:
        """Score normalisieren zu [0, 1] (Sigmoid)."""
        import math
        return 1 / (1 + math.exp(-score))


# Convenience-Funktionen

async def rerank_documents(
    query: str,
    documents: List[Dict[str, Any]],
    model_name: str = "ms-marco-mini",
    top_k: int = 10,
    doc_id_field: str = "id",
    text_field: str = "text",
    score_field: str = "score",
) -> List[RerankResult]:
    """
    Convenience-Funktion für Re-Ranking.
    
    Args:
        query: Suchanfrage
        documents: Liste von Dokumenten (Dict)
        model_name: Cross-Encoder Modell
        top_k: Top-K Ergebnisse
        doc_id_field: Feld-Name für Dokument-ID
        text_field: Feld-Name für Text
        score_field: Feld-Name für initialen Score
    
    Returns:
        Liste von RerankResult
    
    Beispiel:
        >>> docs = [
        ...     {"id": "doc1", "text": "...", "score": 0.95},
        ...     {"id": "doc2", "text": "...", "score": 0.87},
        ... ]
        >>> results = await rerank_documents("Query", docs, top_k=5)
    """
    # Kandidaten erstellen
    candidates = [
        RerankCandidate(
            doc_id=doc.get(doc_id_field),
            text=doc.get(text_field, ""),
            initial_score=doc.get(score_field, 0.0),
            metadata={k: v for k, v in doc.items() if k not in [doc_id_field, text_field, score_field]},
        )
        for doc in documents
    ]
    
    # Re-Ranker
    reranker = CrossEncoderReranker(model_name=model_name)
    
    # Re-Ranking
    return await reranker.rerank(query, candidates, top_k=top_k)
