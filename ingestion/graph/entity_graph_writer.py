"""
Entity Graph Writer - UDS3-Managed Neo4j Persistence
=====================================================

Upserts extracted legal entities (LegalConcept, Authority, Jurisdiction, LegalNorm)
and their relationships (MENTIONS_CONCEPT, CITES_NORM, ISSUED_BY, APPLIES_TO)
into the Neo4j knowledge graph via UDS3 Gateway.

Architecture:
- Uses UDS3Gateway for all graph operations (no direct Neo4j driver)
- MERGE-based upserts (idempotent)
- Timestamps: created_at (once) / updated_at (every write)
- All IDs normalized (lowercase, stripped) for consistency

Node Types:
- LegalConcept: {id, name, tier, keywords, context_window}
- Authority: {id, name, level, jurisdiction, contact_info}
- Jurisdiction: {id, name, level, parent_id}
- LegalNorm: {id, norm_text, law_abbreviation, article, paragraph, sentence}

Relationships:
- MENTIONS_CONCEPT: (Document)-[:MENTIONS_CONCEPT {count, first_seen_at}]->(LegalConcept)
- CITES_NORM: (Document)-[:CITES_NORM {count, context}]->(LegalNorm)
- ISSUED_BY: (Document)-[:ISSUED_BY {effective_date}]->(Authority)
- APPLIES_TO: (Document)-[:APPLIES_TO]->(Jurisdiction)
"""

from datetime import datetime
from typing import Any, Optional
from ingestion.infrastructure.clients.uds3_gateway import UDS3Gateway
from ingestion.observability.legal_nlp_metrics import record_graph_write


class EntityGraphWriter:
    """
    Persists extracted legal entities and their relationships to Neo4j via UDS3.
    """

    def __init__(self, uds3_gateway: Optional[UDS3Gateway] = None, graph_adapter=None):
        """
        Initialize writer with UDS3Gateway or graph_adapter (for tests).

        Args:
            uds3_gateway: UDS3Gateway instance (production)
            graph_adapter: Direct adapter (for testing)
        """
        if graph_adapter:
            self._graph = graph_adapter
        elif uds3_gateway:
            self._graph = uds3_gateway.get_graph_adapter()
        else:
            gateway = UDS3Gateway()
            self._graph = gateway.get_graph_adapter()

    def upsert_legal_concept(
        self,
        concept_id: str,
        name: str,
        tier: int = 1,
        keywords: Optional[list[str]] = None,
        context_window: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Upsert a LegalConcept node.

        Args:
            concept_id: Unique identifier (normalized)
            name: Human-readable concept name
            tier: Extraction tier (1=regex, 2=spaCy, 3=LLM)
            keywords: Associated keywords/synonyms
            context_window: Surrounding text context (for validation)

        Returns:
            Result dict from Neo4j
        """
        concept_id = concept_id.lower().strip()
        now = datetime.utcnow().isoformat()
        keywords = keywords or []

        cypher = """
        MERGE (c:LegalConcept {id: $id})
        ON CREATE SET
            c.name = $name,
            c.tier = $tier,
            c.keywords = $keywords,
            c.context_window = $context_window,
            c.created_at = $now,
            c.updated_at = $now
        ON MATCH SET
            c.name = $name,
            c.tier = $tier,
            c.keywords = $keywords,
            c.context_window = $context_window,
            c.updated_at = $now
        RETURN c
        """
        params = {
            "id": concept_id,
            "name": name,
            "tier": tier,
            "keywords": keywords,
            "context_window": context_window,
            "now": now,
        }
        try:
            result = self._execute_sync(cypher, params)
            record_graph_write(True, "node")
            return result
        except Exception:
            record_graph_write(False, "node")
            raise

    def upsert_authority(
        self,
        authority_id: str,
        name: str,
        level: str,
        jurisdiction: Optional[str] = None,
        contact_info: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Upsert an Authority node.

        Args:
            authority_id: Unique identifier (normalized)
            name: Authority name (e.g., "Bundesverwaltungsgericht")
            level: Level (federal, state, local)
            jurisdiction: Jurisdiction identifier
            contact_info: Contact details (optional)

        Returns:
            Result dict from Neo4j
        """
        authority_id = authority_id.lower().strip()
        now = datetime.utcnow().isoformat()

        cypher = """
        MERGE (a:Authority {id: $id})
        ON CREATE SET
            a.name = $name,
            a.level = $level,
            a.jurisdiction = $jurisdiction,
            a.contact_info = $contact_info,
            a.created_at = $now,
            a.updated_at = $now
        ON MATCH SET
            a.name = $name,
            a.level = $level,
            a.jurisdiction = $jurisdiction,
            a.contact_info = $contact_info,
            a.updated_at = $now
        RETURN a
        """
        params = {
            "id": authority_id,
            "name": name,
            "level": level,
            "jurisdiction": jurisdiction,
            "contact_info": contact_info or {},
            "now": now,
        }
        try:
            result = self._execute_sync(cypher, params)
            record_graph_write(True, "node")
            return result
        except Exception:
            record_graph_write(False, "node")
            raise

    def upsert_jurisdiction(
        self,
        jurisdiction_id: str,
        name: str,
        level: str,
        parent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Upsert a Jurisdiction node.

        Args:
            jurisdiction_id: Unique identifier (normalized)
            name: Jurisdiction name (e.g., "Baden-Württemberg")
            level: Level (federal, state, local)
            parent_id: Parent jurisdiction (for hierarchy)

        Returns:
            Result dict from Neo4j
        """
        jurisdiction_id = jurisdiction_id.lower().strip()
        now = datetime.utcnow().isoformat()

        cypher = """
        MERGE (j:Jurisdiction {id: $id})
        ON CREATE SET
            j.name = $name,
            j.level = $level,
            j.parent_id = $parent_id,
            j.created_at = $now,
            j.updated_at = $now
        ON MATCH SET
            j.name = $name,
            j.level = $level,
            j.parent_id = $parent_id,
            j.updated_at = $now
        RETURN j
        """
        params = {
            "id": jurisdiction_id,
            "name": name,
            "level": level,
            "parent_id": parent_id,
            "now": now,
        }
        try:
            result = self._execute_sync(cypher, params)
            record_graph_write(True, "node")
            return result
        except Exception:
            record_graph_write(False, "node")
            raise

    def upsert_legal_norm(
        self,
        norm_id: str,
        norm_text: str,
        law_abbreviation: Optional[str] = None,
        article: Optional[str] = None,
        paragraph: Optional[str] = None,
        sentence: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Upsert a LegalNorm node.

        Args:
            norm_id: Unique identifier (normalized)
            norm_text: Full norm text (e.g., "§ 3 Abs. 1 BauGB")
            law_abbreviation: Law abbreviation (e.g., "BauGB")
            article: Article number (if applicable)
            paragraph: Paragraph number
            sentence: Sentence number (if applicable)

        Returns:
            Result dict from Neo4j
        """
        norm_id = norm_id.lower().strip()
        now = datetime.utcnow().isoformat()

        cypher = """
        MERGE (n:LegalNorm {id: $id})
        ON CREATE SET
            n.norm_text = $norm_text,
            n.law_abbreviation = $law_abbreviation,
            n.article = $article,
            n.paragraph = $paragraph,
            n.sentence = $sentence,
            n.created_at = $now,
            n.updated_at = $now
        ON MATCH SET
            n.norm_text = $norm_text,
            n.law_abbreviation = $law_abbreviation,
            n.article = $article,
            n.paragraph = $paragraph,
            n.sentence = $sentence,
            n.updated_at = $now
        RETURN n
        """
        params = {
            "id": norm_id,
            "norm_text": norm_text,
            "law_abbreviation": law_abbreviation,
            "article": article,
            "paragraph": paragraph,
            "sentence": sentence,
            "now": now,
        }
        try:
            result = self._execute_sync(cypher, params)
            record_graph_write(True, "node")
            return result
        except Exception:
            record_graph_write(False, "node")
            raise

    def link_mentions_concept(
        self,
        document_id: str,
        concept_id: str,
        count: int = 1,
    ) -> dict[str, Any]:
        """
        Link document to mentioned concept.

        Args:
            document_id: Source document identifier
            concept_id: Target concept identifier
            count: Number of mentions in document

        Returns:
            Result dict from Neo4j
        """
        concept_id = concept_id.lower().strip()
        now = datetime.utcnow().isoformat()

        cypher = """
        MATCH (d:Document {id: $doc_id})
        MATCH (c:LegalConcept {id: $concept_id})
        MERGE (d)-[r:MENTIONS_CONCEPT]->(c)
        ON CREATE SET
            r.count = $count,
            r.first_seen_at = $now,
            r.updated_at = $now
        ON MATCH SET
            r.count = $count,
            r.updated_at = $now
        RETURN r
        """
        params = {
            "doc_id": document_id,
            "concept_id": concept_id,
            "count": count,
            "now": now,
        }
        try:
            result = self._execute_sync(cypher, params)
            record_graph_write(True, "relation")
            return result
        except Exception:
            record_graph_write(False, "relation")
            raise

    def link_cites_norm(
        self,
        document_id: str,
        norm_id: str,
        count: int = 1,
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Link document to cited norm.

        Args:
            document_id: Source document identifier
            norm_id: Target norm identifier
            count: Number of citations in document
            context: Surrounding text context

        Returns:
            Result dict from Neo4j
        """
        norm_id = norm_id.lower().strip()
        now = datetime.utcnow().isoformat()

        cypher = """
        MATCH (d:Document {id: $doc_id})
        MATCH (n:LegalNorm {id: $norm_id})
        MERGE (d)-[r:CITES_NORM]->(n)
        ON CREATE SET
            r.count = $count,
            r.context = $context,
            r.first_seen_at = $now,
            r.updated_at = $now
        ON MATCH SET
            r.count = $count,
            r.context = $context,
            r.updated_at = $now
        RETURN r
        """
        params = {
            "doc_id": document_id,
            "norm_id": norm_id,
            "count": count,
            "context": context,
            "now": now,
        }
        try:
            result = self._execute_sync(cypher, params)
            record_graph_write(True, "relation")
            return result
        except Exception:
            record_graph_write(False, "relation")
            raise

    def link_issued_by(
        self,
        document_id: str,
        authority_id: str,
        effective_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Link document to issuing authority.

        Args:
            document_id: Source document identifier
            authority_id: Target authority identifier
            effective_date: Effective date (ISO format)

        Returns:
            Result dict from Neo4j
        """
        authority_id = authority_id.lower().strip()
        now = datetime.utcnow().isoformat()

        cypher = """
        MATCH (d:Document {id: $doc_id})
        MATCH (a:Authority {id: $authority_id})
        MERGE (d)-[r:ISSUED_BY]->(a)
        ON CREATE SET
            r.effective_date = $effective_date,
            r.created_at = $now,
            r.updated_at = $now
        ON MATCH SET
            r.effective_date = $effective_date,
            r.updated_at = $now
        RETURN r
        """
        params = {
            "doc_id": document_id,
            "authority_id": authority_id,
            "effective_date": effective_date,
            "now": now,
        }
        try:
            result = self._execute_sync(cypher, params)
            record_graph_write(True, "relation")
            return result
        except Exception:
            record_graph_write(False, "relation")
            raise

    def link_applies_to(
        self,
        document_id: str,
        jurisdiction_id: str,
    ) -> dict[str, Any]:
        """
        Link document to applicable jurisdiction.

        Args:
            document_id: Source document identifier
            jurisdiction_id: Target jurisdiction identifier

        Returns:
            Result dict from Neo4j
        """
        jurisdiction_id = jurisdiction_id.lower().strip()
        now = datetime.utcnow().isoformat()

        cypher = """
        MATCH (d:Document {id: $doc_id})
        MATCH (j:Jurisdiction {id: $jurisdiction_id})
        MERGE (d)-[r:APPLIES_TO]->(j)
        ON CREATE SET
            r.created_at = $now,
            r.updated_at = $now
        ON MATCH SET
            r.updated_at = $now
        RETURN r
        """
        params = {
            "doc_id": document_id,
            "jurisdiction_id": jurisdiction_id,
            "now": now,
        }
        return self._execute_sync(cypher, params)

    def _execute_sync(self, cypher: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """
        Execute Cypher via UDS3 Neo4j adapter (synchronous).

        Args:
            cypher: Cypher query
            params: Query parameters

        Returns:
            Result dict from Neo4j
        """
        return self._graph.execute_query(cypher, params or {})
