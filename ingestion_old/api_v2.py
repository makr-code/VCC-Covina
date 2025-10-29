"""API v2 für Ingestion – sauber getrennt als APIRouter.

- Baut Router + Writer aus Konfiguration (config/ingestion.yaml)
- Exponiert Endpunkte unter /v2
- Keine Seiteneffekte für V1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter

from config.loader import load_ingestion_config
from ingestion.factory import create_pipeline
from ingestion.core.interfaces import Chunk, ChunkMetadata


def build_v2_router(cfg: Optional[Dict[str, Any]] = None) -> APIRouter:
    """Erzeugt und konfiguriert den v2-APIRouter.

    Optional kann eine Konfiguration übergeben werden (z. B. für Tests),
    andernfalls wird die Standardkonfiguration geladen.
    """
    router = APIRouter(prefix="/v2", tags=["ingestion-v2"])

    # Pipeline bauen (Router + Writer)
    config = cfg or load_ingestion_config()
    _router, _writer = create_pipeline(config)

    @router.post("/ingest/chunk")
    async def ingest_chunk_v2(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Nimmt {text, metadata} entgegen und routet den Chunk über den neuen Router."""
        text = payload.get("text")
        md = payload.get("metadata", {})
        meta = ChunkMetadata(
            source_file=md.get("source_file", "unknown"),
            chunk_index=int(md.get("chunk_index", 0)),
            total_chunks=int(md.get("total_chunks", 1)),
        )
        chunk = Chunk(text=text, metadata=meta)
        res = await _router.process(chunk)
        return {"success": res.success, "error": res.error}

    return router
