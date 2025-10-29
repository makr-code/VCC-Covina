from __future__ import annotations
from typing import Protocol, Any, Optional
import logging

from ingestion.graph.entity_graph_writer import EntityGraphWriter
from ingestion.observability.legal_nlp_metrics import record_graph_write

class GraphWriterService(Protocol):
    async def write(self, result: Any) -> None: ...

class NoopGraphWriter(GraphWriterService):
    async def write(self, result: Any) -> None:
        return None


class RealGraphWriter(GraphWriterService):
    """Production graph writer using EntityGraphWriter.

    Expects an extraction result dict with optional keys like concepts, norms,
    authorities, jurisdictions, and document id. Missing keys are ignored.
    """

    def __init__(self, writer: Optional[EntityGraphWriter] = None) -> None:
        self._writer = writer or EntityGraphWriter()
        self._log = logging.getLogger("ingestion.graph_writer")

    async def write(self, result: Any) -> None:
        if not isinstance(result, dict) or not result:
            return  # nothing to write

        doc_id = str(result.get("document_id") or result.get("doc_id") or "").strip()
        # Without document id we only perform node upserts if provided

        # Concepts
        for c in (result.get("concepts") or []):
            try:
                # c may be str id or dict
                if isinstance(c, str):
                    self._writer.upsert_legal_concept(c, c, tier=1)
                    if doc_id:
                        self._writer.link_mentions_concept(doc_id, c, count=1)
                elif isinstance(c, dict):
                    cid = str(c.get("id") or c.get("name") or "").strip()
                    if not cid:
                        continue
                    self._writer.upsert_legal_concept(
                        cid, c.get("name") or cid, tier=int(c.get("tier") or 1),
                        keywords=c.get("keywords"), context_window=c.get("context")
                    )
                    if doc_id:
                        self._writer.link_mentions_concept(doc_id, cid, count=int(c.get("count") or 1))
            except Exception:
                self._log.exception("graph_write_concept_failed")

        # Norms
        for n in (result.get("norms") or []):
            try:
                if isinstance(n, str):
                    self._writer.upsert_legal_norm(n, n)
                    if doc_id:
                        self._writer.link_cites_norm(doc_id, n, count=1)
                elif isinstance(n, dict):
                    nid = str(n.get("id") or n.get("norm_text") or "").strip()
                    if not nid:
                        continue
                    self._writer.upsert_legal_norm(
                        nid, n.get("norm_text") or nid, n.get("law_abbreviation"),
                        n.get("article"), n.get("paragraph"), n.get("sentence")
                    )
                    if doc_id:
                        self._writer.link_cites_norm(doc_id, nid, count=int(n.get("count") or 1), context=n.get("context"))
            except Exception:
                self._log.exception("graph_write_norm_failed")

        # Authorities
        for a in (result.get("authorities") or []):
            try:
                if isinstance(a, str):
                    self._writer.upsert_authority(a, a, level="unknown")
                elif isinstance(a, dict):
                    aid = str(a.get("id") or a.get("name") or "").strip()
                    if not aid:
                        continue
                    self._writer.upsert_authority(
                        aid, a.get("name") or aid, a.get("level") or "unknown",
                        a.get("jurisdiction"), a.get("contact_info")
                    )
                    if doc_id:
                        self._writer.link_issued_by(doc_id, aid, effective_date=a.get("effective_date"))
            except Exception:
                self._log.exception("graph_write_authority_failed")

        # Jurisdictions
        for j in (result.get("jurisdictions") or []):
            try:
                if isinstance(j, str):
                    self._writer.upsert_jurisdiction(j, j, level="unknown")
                    if doc_id:
                        self._writer.link_applies_to(doc_id, j)
                elif isinstance(j, dict):
                    jid = str(j.get("id") or j.get("name") or "").strip()
                    if not jid:
                        continue
                    self._writer.upsert_jurisdiction(
                        jid, j.get("name") or jid, j.get("level") or "unknown", j.get("parent_id")
                    )
                    if doc_id:
                        self._writer.link_applies_to(doc_id, jid)
            except Exception:
                self._log.exception("graph_write_jurisdiction_failed")
