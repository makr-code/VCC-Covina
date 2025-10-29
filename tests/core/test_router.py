"""
Unit Tests for ChunkRouter

Tests the routing logic for format-based extractor selection:
- Extractor registration/unregistration
- Format matching and caching
- File extraction (single and batch)
- Error handling
"""

import pytest
from pathlib import Path
from typing import List, Optional

from ingestion.core.interfaces import (
    Chunk,
    ChunkMetadata,
    ChunkClassification,
    Extractor,
    ExtractionResult,
)
from ingestion.core.router import ChunkRouter


# ============================================================================
# Mock Extractor Implementations
# ============================================================================

class MockPDFExtractor:
    """Mock PDF extractor for testing."""
    
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
        """Extract mock PDF chunks."""
        metadata = ChunkMetadata(
            source_file=str(file_path),
            chunk_index=0,
            total_chunks=1,
            correlation_id=correlation_id,
            job_id=job_id,
        )
        return [Chunk(text=f"PDF content from {file_path.name}", metadata=metadata)]


class MockDOCXExtractor:
    """Mock DOCX extractor for testing."""
    
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
        """Extract mock DOCX chunks."""
        metadata = ChunkMetadata(
            source_file=str(file_path),
            chunk_index=0,
            total_chunks=1,
            correlation_id=correlation_id,
            job_id=job_id,
        )
        return [Chunk(text=f"DOCX content from {file_path.name}", metadata=metadata)]


class MockFailingExtractor:
    """Mock extractor that always fails for testing error handling."""
    
    @property
    def supported_formats(self) -> List[str]:
        return [".fail"]
    
    def can_extract(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".fail"
    
    async def extract(
        self,
        file_path: Path,
        correlation_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> List[Chunk]:
        """Always raise an error."""
        raise RuntimeError("Mock extraction failure")


# ============================================================================
# Test ChunkRouter
# ============================================================================

class TestChunkRouter:
    """Test ChunkRouter functionality."""
    
    def test_router_initialization(self):
        """Test that router initializes with empty registry."""
        router = ChunkRouter()
        
        assert router.extractor_count == 0
        assert router.supported_formats == []
    
    def test_register_extractor(self):
        """Test registering an extractor."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        
        router.register(pdf_extractor)
        
        assert router.extractor_count == 1
        assert ".pdf" in router.supported_formats
    
    def test_register_multiple_extractors(self):
        """Test registering multiple extractors."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        docx_extractor = MockDOCXExtractor()
        
        router.register(pdf_extractor)
        router.register(docx_extractor)
        
        assert router.extractor_count == 2
        assert set(router.supported_formats) == {".pdf", ".doc", ".docx"}
    
    def test_register_duplicate_extractor(self):
        """Test that registering duplicate extractor raises ValueError."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        
        router.register(pdf_extractor)
        
        with pytest.raises(ValueError, match="already registered"):
            router.register(pdf_extractor)
    
    def test_unregister_extractor(self):
        """Test unregistering an extractor."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        
        router.register(pdf_extractor)
        router.unregister(pdf_extractor)
        
        assert router.extractor_count == 0
        assert router.supported_formats == []
    
    def test_get_extractor_match(self):
        """Test getting extractor for matching file."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        router.register(pdf_extractor)
        
        extractor = router.get_extractor(Path("test.pdf"))
        
        assert extractor is pdf_extractor
    
    def test_get_extractor_no_match(self):
        """Test getting extractor for unsupported file."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        router.register(pdf_extractor)
        
        extractor = router.get_extractor(Path("test.txt"))
        
        assert extractor is None
    
    def test_get_extractor_caching(self):
        """Test that extractor lookup uses caching."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        router.register(pdf_extractor)
        
        # First lookup (should cache)
        extractor1 = router.get_extractor(Path("test1.pdf"))
        # Second lookup (should use cache)
        extractor2 = router.get_extractor(Path("test2.pdf"))
        
        assert extractor1 is pdf_extractor
        assert extractor2 is pdf_extractor
    
    def test_clear_cache(self):
        """Test clearing the extractor cache."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        router.register(pdf_extractor)
        
        router.get_extractor(Path("test.pdf"))  # Populate cache
        router.clear_cache()
        
        # Cache should be empty (can't directly test, but no error)
        assert router.get_extractor(Path("test.pdf")) is pdf_extractor
    
    @pytest.mark.asyncio
    async def test_extract_file_success(self, tmp_path):
        """Test successful file extraction."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        router.register(pdf_extractor)
        
        # Create test file
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy content")
        
        result = await router.extract_file(test_file, correlation_id="corr-123")
        
        assert result.success is True
        assert len(result.chunks) == 1
        assert result.chunks[0].metadata.correlation_id == "corr-123"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_extract_file_not_found(self):
        """Test extraction of non-existent file."""
        router = ChunkRouter()
        
        result = await router.extract_file(Path("missing.pdf"))
        
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_extract_file_no_extractor(self, tmp_path):
        """Test extraction with no matching extractor."""
        router = ChunkRouter()
        
        # Create test file with unsupported format
        test_file = tmp_path / "test.txt"
        test_file.write_text("dummy content")
        
        result = await router.extract_file(test_file)
        
        assert result.success is False
        assert result.error is not None
        assert "No extractor" in result.error
    
    @pytest.mark.asyncio
    async def test_extract_file_extractor_failure(self, tmp_path):
        """Test extraction when extractor fails."""
        router = ChunkRouter()
        failing_extractor = MockFailingExtractor()
        router.register(failing_extractor)
        
        # Create test file
        test_file = tmp_path / "test.fail"
        test_file.write_text("dummy content")
        
        result = await router.extract_file(test_file)
        
        assert result.success is False
        assert result.error is not None
        assert "Mock extraction failure" in result.error
    
    @pytest.mark.asyncio
    async def test_extract_batch_success(self, tmp_path):
        """Test successful batch extraction."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        docx_extractor = MockDOCXExtractor()
        router.register(pdf_extractor)
        router.register(docx_extractor)
        
        # Create test files
        pdf_file = tmp_path / "test1.pdf"
        pdf_file.write_text("pdf content")
        docx_file = tmp_path / "test2.docx"
        docx_file.write_text("docx content")
        
        results = await router.extract_batch([pdf_file, docx_file])
        
        assert len(results) == 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_extract_batch_partial_failure(self, tmp_path):
        """Test batch extraction with some failures."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        router.register(pdf_extractor)
        
        # Create one valid file and one invalid path
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("pdf content")
        missing_file = tmp_path / "missing.pdf"
        
        results = await router.extract_batch([pdf_file, missing_file])
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
    
    def test_list_extractors(self):
        """Test listing registered extractors."""
        router = ChunkRouter()
        pdf_extractor = MockPDFExtractor()
        docx_extractor = MockDOCXExtractor()
        
        router.register(pdf_extractor)
        router.register(docx_extractor)
        
        extractors = router.list_extractors()
        
        assert len(extractors) == 2
        assert any(e["formats"] == [".pdf"] for e in extractors)
        assert any(e["formats"] == [".docx", ".doc"] for e in extractors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
