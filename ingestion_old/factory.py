"""Ingestion Factory (Phase A)

Erzeugt Router + Writer aus Konfiguration.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from config.loader import load_ingestion_config
from ingestion.core.ingest_router import ChunkRouter


def create_pipeline(config: Dict[str, Any] | None = None) -> Tuple[ChunkRouter, Any]:
    """Erzeuge Ingestion-Pipeline (Router + Writer) aus Konfiguration.

    Returns (router, writer)
    """
    cfg = config or load_ingestion_config()

    # Writer erzeugen (UDS3 als Default)
    writer_type = (cfg.get("writer", {}).get("type") or "uds3").lower()
    if writer_type != "uds3":
        raise NotImplementedError(f"Unbekannter Writer-Typ: {writer_type}")

    from ingestion.writers.uds3_adapter import UDS3Writer  # lazy import

    backend_cfg = cfg.get("backends", {})
    writer = UDS3Writer(config={
        "relational": {"enabled": bool(backend_cfg.get("relational", {}).get("enabled", True))},
        "vector": {"enabled": bool(backend_cfg.get("vector", {}).get("enabled", True))},
        "graph": {"enabled": bool(backend_cfg.get("graph", {}).get("enabled", True))},
        "file": {"enabled": bool(backend_cfg.get("file", {}).get("enabled", True))},
    })

    # Router erzeugen
    router_cfg = cfg.get("router", {})
    router = ChunkRouter(writer, fail_fast=bool(router_cfg.get("fail_fast", False)))

    return router, writer
