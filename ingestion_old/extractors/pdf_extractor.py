"""
PDF Extractor

Extracts text from PDF files using pypdf.
Produces a single Chunk with the concatenated text of all pages.
"""

import logging
from pathlib import Path
from typing import List, Optional

from pypdf import PdfReader

from ingestion.core.interfaces import (
    Extractor,
    Chunk,
    ChunkMetadata,
    ChunkClassification,
)

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extractor for PDF files using pypdf."""

    @property
    def supported_formats(self) -> List[str]:
        return [".pdf"]

    def can_extract(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    async def extract(
        self,
        file_path: Path,
        correlation_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[Chunk]:
        if not file_path.exists():
            raise RuntimeError(f"File not found: {file_path}")

        try:
            reader = PdfReader(str(file_path))
        except Exception as e:
            logger.error(f"Failed to open PDF {file_path.name}: {e}")
            raise

        texts: List[str] = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception as e:
                logger.warning(
                    f"Failed to extract text from page {i} in {file_path.name}: {e}"
                )
                text = ""
            texts.append(text)

        full_text = "\n".join(t for t in texts if t)
        if not full_text.strip():
            # Provide minimal non-empty text to satisfy Chunk validation
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
