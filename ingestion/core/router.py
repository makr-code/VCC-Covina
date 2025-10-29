"""
ChunkRouter - Format-based routing logic

Routes chunks to appropriate extractors based on file format.
Implements chain-of-responsibility pattern for extractor selection.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .interfaces import Chunk, Extractor, ExtractionResult

logger = logging.getLogger(__name__)


class ChunkRouter:
    """
    Routes files to appropriate extractors based on format.
    
    Maintains a registry of extractors and selects the first one
    that can handle a given file format.
    
    Example:
        >>> router = ChunkRouter()
        >>> router.register(PDFExtractor())
        >>> router.register(DOCXExtractor())
        >>> chunks = await router.extract_file(Path("invoice.pdf"))
    """
    
    def __init__(self):
        """Initialize router with empty extractor registry."""
        self._extractors: List[Extractor] = []
        self._format_cache: Dict[str, Extractor] = {}
    
    def register(self, extractor: Extractor) -> None:
        """
        Register an extractor with the router.
        
        Args:
            extractor: Extractor instance to register
            
        Raises:
            ValueError: If extractor is already registered
        """
        if extractor in self._extractors:
            raise ValueError(f"Extractor {extractor} already registered")
        
        self._extractors.append(extractor)
        logger.info(
            f"Registered extractor for formats: {extractor.supported_formats}"
        )
    
    def unregister(self, extractor: Extractor) -> None:
        """
        Unregister an extractor from the router.
        
        Args:
            extractor: Extractor instance to unregister
        """
        if extractor in self._extractors:
            self._extractors.remove(extractor)
            # Clear cache entries for this extractor
            self._format_cache = {
                fmt: ext
                for fmt, ext in self._format_cache.items()
                if ext != extractor
            }
            logger.info(f"Unregistered extractor: {extractor}")
    
    def get_extractor(self, file_path: Path) -> Optional[Extractor]:
        """
        Get the appropriate extractor for a file.
        
        Uses caching to avoid repeated can_extract() calls for
        the same file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            Extractor instance if found, None otherwise
        """
        # Check cache first
        ext = file_path.suffix.lower()
        if ext in self._format_cache:
            return self._format_cache[ext]
        
        # Find suitable extractor
        for extractor in self._extractors:
            if extractor.can_extract(file_path):
                # Cache for future lookups
                self._format_cache[ext] = extractor
                logger.debug(f"Matched {file_path.name} to {extractor}")
                return extractor
        
        logger.warning(f"No extractor found for {file_path.name}")
        return None
    
    async def extract_file(
        self,
        file_path: Path,
        correlation_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract chunks from a file using appropriate extractor.
        
        Args:
            file_path: Path to file to extract
            correlation_id: Optional correlation ID for tracing
            job_id: Optional job ID for tracking
            
        Returns:
            ExtractionResult with chunks or error
        """
        if not file_path.exists():
            return ExtractionResult(
                success=False,
                error=f"File not found: {file_path}",
                file_path=str(file_path),
            )
        
        extractor = self.get_extractor(file_path)
        if extractor is None:
            return ExtractionResult(
                success=False,
                error=f"No extractor for format: {file_path.suffix}",
                file_path=str(file_path),
            )
        
        try:
            chunks = await extractor.extract(
                file_path,
                correlation_id=correlation_id,
                job_id=job_id,
            )
            
            logger.info(
                f"Extracted {len(chunks)} chunks from {file_path.name}",
                extra={"correlation_id": correlation_id, "job_id": job_id},
            )
            
            return ExtractionResult(
                success=True,
                chunks=chunks,
                file_path=str(file_path),
            )
            
        except Exception as e:
            logger.error(
                f"Extraction failed for {file_path.name}: {e}",
                extra={"correlation_id": correlation_id, "job_id": job_id},
                exc_info=True,
            )
            return ExtractionResult(
                success=False,
                error=str(e),
                file_path=str(file_path),
            )
    
    async def extract_batch(
        self,
        file_paths: List[Path],
        correlation_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[ExtractionResult]:
        """
        Extract chunks from multiple files.
        
        Processes files independently - failures don't stop batch.
        
        Args:
            file_paths: List of file paths to extract
            correlation_id: Optional correlation ID for tracing
            job_id: Optional job ID for tracking
            
        Returns:
            List of ExtractionResult (one per file)
        """
        results = []
        for file_path in file_paths:
            result = await self.extract_file(
                file_path,
                correlation_id=correlation_id,
                job_id=job_id,
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Batch extraction: {success_count}/{len(file_paths)} succeeded",
            extra={"correlation_id": correlation_id, "job_id": job_id},
        )
        
        return results
    
    def list_extractors(self) -> List[Dict[str, Any]]:
        """
        List all registered extractors with their formats.
        
        Returns:
            List of extractor metadata dictionaries
        """
        return [
            {
                "formats": extractor.supported_formats,
                "type": type(extractor).__name__,
            }
            for extractor in self._extractors
        ]
    
    def clear_cache(self) -> None:
        """Clear the format-to-extractor cache."""
        self._format_cache.clear()
        logger.debug("Cleared extractor cache")
    
    @property
    def extractor_count(self) -> int:
        """Get number of registered extractors."""
        return len(self._extractors)
    
    @property
    def supported_formats(self) -> List[str]:
        """
        Get all supported file formats across extractors.
        
        Returns:
            List of unique file extensions
        """
        formats = set()
        for extractor in self._extractors:
            formats.update(extractor.supported_formats)
        return sorted(formats)
