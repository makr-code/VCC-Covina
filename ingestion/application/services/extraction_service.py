from __future__ import annotations
from typing import Protocol, Any

class ExtractionService(Protocol):
    async def extract(self, text: str) -> Any: ...

class RegexExtractionService:
    """Tier-1 regex-based extractor (placeholder)."""
    async def extract(self, text: str) -> Any:
        return {"entities": [], "concepts": [], "norms": []}
