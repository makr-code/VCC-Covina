"""
DOCX Extractor

Extracts text from Microsoft Word .docx files using python-docx.
Produces a single Chunk with concatenated paragraphs.
"""

import logging
from pathlib import Path
from typing import List, Optional

from docx import Document

from ingestion.core.interfaces import (
    Extractor,
    Chunk,
    ChunkMetadata,
    ChunkClassification,
)

logger = logging.getLogger(__name__)


class DOCXExtractor:
    """Extractor for DOCX files using python-docx."""

    @property
    def supported_formats(self) -> List[str]:
        return [".docx", ".doc"]

    def can_extract(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in [".docx", ".doc"]

    async def extract(
        self,
        file_path: Path,
        correlation_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[Chunk]:
        if not file_path.exists():
            raise RuntimeError(f"File not found: {file_path}")

        try:
            doc = Document(str(file_path))
        except Exception as e:
            logger.error(f"Failed to open DOCX {file_path.name}: {e}")
            raise

        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        full_text = "\n".join(paragraphs)
        if not full_text.strip():
            full_text = "(no text extracted)"

        metadata = ChunkMetadata(
            source_file=str(file_path),
            chunk_index=0,
            total_chunks=1,
            classification=ChunkClassification.UNBEKANNT,
            confidence=0.0,
            correlation_id=correlation_id,
            job_id=job_id,
        )

        chunk = Chunk(text=full_text, metadata=metadata)
        return [chunk]
