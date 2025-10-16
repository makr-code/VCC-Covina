"""
BM25 Keyword Search Index für Covina.

Implementiert BM25-Algorithmus (Best Match 25) für keyword-basierte Suche.
Ergänzt ChromaDB Vector Search für Hybrid Retrieval.

Features:
- Deutsche Tokenisierung (Unicode-normalisiert)
- Inkrementelle Index-Updates
- Pickle-Persistierung für schnelles Laden
- Configurable BM25-Parameter (k1, b)

Verwendung:
    >>> indexer = BM25DocumentIndex()
    >>> await indexer.add_documents(documents)
    >>> results = await indexer.search("Antrag Wohngeld", top_k=10)
"""

import asyncio
import logging
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class BM25Document:
    """Dokument für BM25-Index."""
    
    doc_id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class BM25SearchResult:
    """Suchergebnis mit BM25-Score."""
    
    doc_id: str
    score: float
    text: str
    metadata: Dict[str, Any]


class GermanTokenizer:
    """
    Deutscher Tokenizer für BM25.
    
    Features:
    - Unicode-Normalisierung (ä → ae, ö → oe, ü → ue, ß → ss)
    - Lowercase
    - Alphanumerische Tokens (min. 2 Zeichen)
    - Optionale Stopword-Filterung
    """
    
    # Deutsche Stopwords (häufigste)
    STOPWORDS = {
        'der', 'die', 'das', 'den', 'dem', 'des',
        'ein', 'eine', 'einer', 'eines', 'einem',
        'und', 'oder', 'aber', 'weil', 'wenn',
        'als', 'wie', 'bei', 'nach', 'von', 'zu',
        'im', 'am', 'um', 'an', 'auf', 'für', 'mit',
        'ist', 'sind', 'war', 'waren', 'wird', 'wurde',
        'hat', 'haben', 'hatte', 'hatten',
        'nicht', 'kein', 'keine', 'auch', 'noch',
    }
    
    UMLAUT_MAP = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
    }
    
    def __init__(self, use_stopwords: bool = True):
        """
        Args:
            use_stopwords: Stopwords filtern (Default: True)
        """
        self.use_stopwords = use_stopwords
    
    def normalize_umlauts(self, text: str) -> str:
        """Umlaute normalisieren für besseres Matching."""
        for umlaut, replacement in self.UMLAUT_MAP.items():
            text = text.replace(umlaut, replacement)
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """
        Text in Tokens zerlegen.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von Tokens (lowercase, normalisiert)
        """
        # Umlaute normalisieren
        text = self.normalize_umlauts(text)
        
        # Lowercase
        text = text.lower()
        
        # Regex: Alphanumerisch, min. 2 Zeichen
        tokens = re.findall(r'\b\w{2,}\b', text)
        
        # Stopwords filtern
        if self.use_stopwords:
            tokens = [t for t in tokens if t not in self.STOPWORDS]
        
        return tokens


class BM25DocumentIndex:
    """
    BM25-Index für keyword-basierte Suche.
    
    BM25 (Best Match 25) ist ein probabilistisches Ranking-Modell für
    Information Retrieval. Berücksichtigt Term-Frequency, Inverse Document
    Frequency und Dokumentlängen-Normalisierung.
    
    Parameter:
        k1 (float): Term-Frequency-Sättigung (default: 1.5)
                    Höher = TF hat mehr Einfluss
        b (float): Dokumentlängen-Normalisierung (default: 0.75)
                   0 = keine Normalisierung, 1 = volle Normalisierung
    
    Attributes:
        documents: Liste aller indizierten Dokumente
        bm25: BM25Okapi-Instanz (rank_bm25)
        tokenizer: Deutscher Tokenizer
        index_path: Pfad zur Index-Datei (optional)
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        index_path: Optional[Path] = None,
        use_stopwords: bool = True,
    ):
        """
        Args:
            k1: BM25-Parameter (Term-Frequency-Sättigung)
            b: BM25-Parameter (Dokumentlängen-Normalisierung)
            index_path: Pfad zum persistierten Index (lädt automatisch)
            use_stopwords: Stopword-Filterung aktivieren
        """
        self.k1 = k1
        self.b = b
        self.index_path = index_path
        self.tokenizer = GermanTokenizer(use_stopwords=use_stopwords)
        
        self.documents: List[BM25Document] = []
        self.bm25: Optional[BM25Okapi] = None
        self._tokenized_corpus: List[List[str]] = []
        
        # Index laden falls vorhanden
        if index_path and index_path.exists():
            self.load_index()
            logger.info(f"BM25-Index geladen: {len(self.documents)} Dokumente")
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        doc_id_field: str = "id",
        text_field: str = "text",
    ) -> None:
        """
        Dokumente zum Index hinzufügen.
        
        Args:
            documents: Liste von Dokumenten (Dict)
            doc_id_field: Feld-Name für Dokument-ID
            text_field: Feld-Name für Text
        
        Beispiel:
            >>> docs = [
            ...     {"id": "doc1", "text": "Antrag auf Wohngeld", "source": "form.pdf"},
            ...     {"id": "doc2", "text": "BAföG Richtlinien", "source": "law.pdf"},
            ... ]
            >>> await indexer.add_documents(docs)
        """
        for doc in documents:
            doc_id = doc.get(doc_id_field)
            text = doc.get(text_field, "")
            
            if not doc_id or not text:
                logger.warning(f"Dokument übersprungen (fehlende ID oder Text): {doc}")
                continue
            
            # Metadata = alles außer ID und Text
            metadata = {k: v for k, v in doc.items() if k not in [doc_id_field, text_field]}
            
            self.documents.append(BM25Document(
                doc_id=doc_id,
                text=text,
                metadata=metadata,
            ))
        
        # Index neu bauen
        await self._rebuild_index()
        logger.info(f"BM25-Index aktualisiert: {len(self.documents)} Dokumente")
    
    async def _rebuild_index(self) -> None:
        """BM25-Index neu bauen (intern)."""
        # Alle Dokumente tokenisieren
        self._tokenized_corpus = [
            self.tokenizer.tokenize(doc.text)
            for doc in self.documents
        ]
        
        # BM25-Index bauen
        self.bm25 = BM25Okapi(
            self._tokenized_corpus,
            k1=self.k1,
            b=self.b,
        )
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[BM25SearchResult]:
        """
        BM25-Suche durchführen.
        
        Args:
            query: Suchanfrage
            top_k: Anzahl Ergebnisse
        
        Returns:
            Liste von BM25SearchResult (sortiert nach Score)
        
        Beispiel:
            >>> results = await indexer.search("Antrag Wohngeld", top_k=5)
            >>> for res in results:
            ...     print(f"{res.doc_id}: {res.score:.3f}")
        """
        if not self.bm25:
            logger.warning("BM25-Index leer, keine Ergebnisse")
            return []
        
        # Query tokenisieren
        query_tokens = self.tokenizer.tokenize(query)
        
        # BM25-Scores berechnen
        scores = self.bm25.get_scores(query_tokens)
        
        # Top-K auswählen
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:top_k]
        
        # Ergebnisse formatieren
        results = []
        for idx in top_indices:
            doc = self.documents[idx]
            results.append(BM25SearchResult(
                doc_id=doc.doc_id,
                score=float(scores[idx]),
                text=doc.text,
                metadata=doc.metadata,
            ))
        
        return results
    
    async def batch_search(
        self,
        queries: List[str],
        top_k: int = 10,
    ) -> List[List[BM25SearchResult]]:
        """
        Batch-Suche für mehrere Queries.
        
        Args:
            queries: Liste von Suchanfragen
            top_k: Anzahl Ergebnisse pro Query
        
        Returns:
            Liste von Ergebnis-Listen
        """
        tasks = [self.search(q, top_k) for q in queries]
        return await asyncio.gather(*tasks)
    
    def save_index(self, path: Optional[Path] = None) -> None:
        """
        Index persistieren (Pickle).
        
        Args:
            path: Pfad zur Index-Datei (optional, nutzt self.index_path)
        
        Beispiel:
            >>> indexer.save_index(Path("data/bm25_index.pkl"))
        """
        path = path or self.index_path
        if not path:
            raise ValueError("Kein index_path angegeben")
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'documents': self.documents,
            'tokenized_corpus': self._tokenized_corpus,
            'k1': self.k1,
            'b': self.b,
        }
        
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"BM25-Index gespeichert: {path} ({len(self.documents)} docs)")
    
    def load_index(self, path: Optional[Path] = None) -> None:
        """
        Index laden (Pickle).
        
        Args:
            path: Pfad zur Index-Datei (optional, nutzt self.index_path)
        """
        path = path or self.index_path
        if not path or not path.exists():
            raise FileNotFoundError(f"Index nicht gefunden: {path}")
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        self.documents = data['documents']
        self._tokenized_corpus = data['tokenized_corpus']
        self.k1 = data['k1']
        self.b = data['b']
        
        # BM25-Instanz neu erstellen
        self.bm25 = BM25Okapi(
            self._tokenized_corpus,
            k1=self.k1,
            b=self.b,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Index-Statistiken.
        
        Returns:
            Dict mit Statistiken (num_docs, avg_doc_length, etc.)
        """
        if not self.documents:
            return {
                'num_documents': 0,
                'avg_doc_length': 0,
                'avg_tokens': 0,
            }
        
        avg_doc_len = sum(len(d.text) for d in self.documents) / len(self.documents)
        avg_tokens = sum(len(t) for t in self._tokenized_corpus) / len(self._tokenized_corpus)
        
        return {
            'num_documents': len(self.documents),
            'avg_doc_length': int(avg_doc_len),
            'avg_tokens': int(avg_tokens),
            'k1': self.k1,
            'b': self.b,
        }


# Convenience-Funktion
async def create_bm25_index(
    documents: List[Dict[str, Any]],
    index_path: Optional[Path] = None,
    **kwargs,
) -> BM25DocumentIndex:
    """
    BM25-Index erstellen (convenience).
    
    Args:
        documents: Liste von Dokumenten
        index_path: Pfad zum Index (optional)
        **kwargs: Parameter für BM25DocumentIndex
    
    Returns:
        BM25DocumentIndex-Instanz
    
    Beispiel:
        >>> docs = load_documents()
        >>> indexer = await create_bm25_index(
        ...     docs,
        ...     index_path=Path("data/bm25.pkl"),
        ...     k1=1.5,
        ...     b=0.75,
        ... )
    """
    indexer = BM25DocumentIndex(index_path=index_path, **kwargs)
    await indexer.add_documents(documents)
    
    if index_path:
        indexer.save_index()
    
    return indexer
