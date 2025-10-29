"""Ingestion Chunk Router (Phase A)

Routet Chunks an einen Writer. Diese Komponente ist unabhängig vom
Extractor-Router in `ingestion.core.router` und wird nach der Extraktion
verwendet.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from ingestion.core.interfaces import Writer, Chunk


@dataclass
class RouteResult:
    success: bool
    error: Optional[str] = None


class ChunkRouter:
    """Ein minimaler, testbarer Router für Ingestion-Chunks."""

    def __init__(self, writer: Writer, *, fail_fast: bool = False) -> None:
        self._writer = writer
        self._fail_fast = fail_fast

    async def process(self, chunk: Chunk) -> RouteResult:
        try:
            ok = await self._writer.write(chunk)
            return RouteResult(success=bool(ok), error=None if ok else "write_failed")
        except Exception as e:  # pragma: no cover - optional fail_fast Pfad
            if self._fail_fast:
                raise
            return RouteResult(success=False, error=str(e))
