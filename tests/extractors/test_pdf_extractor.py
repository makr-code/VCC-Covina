"""
Tests for PDFExtractor

Creates a simple PDF using fpdf2 and verifies extraction via pypdf.
"""

import pytest
from pathlib import Path

from fpdf import FPDF

from ingestion.core.router import ChunkRouter
from ingestion.extractors.pdf_extractor import PDFExtractor


@pytest.mark.asyncio
async def test_pdf_extractor_simple_text(tmp_path):
    # Create a simple PDF file
    pdf_path = tmp_path / "hello.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt="Hello PDF World", ln=True, align="L")
    pdf.output(str(pdf_path))

    # Setup router with PDF extractor
    router = ChunkRouter()
    router.register(PDFExtractor())

    # Extract
    result = await router.extract_file(pdf_path, correlation_id="corr-pdf", job_id="job-1")

    assert result.success is True
    assert len(result.chunks) == 1
    text = result.chunks[0].text
    assert isinstance(text, str)
    # Some PDF text extractors may add extra whitespace/newlines
    assert "Hello" in text and "PDF" in text
    assert result.chunks[0].metadata.correlation_id == "corr-pdf"
    assert result.chunks[0].metadata.job_id == "job-1"


@pytest.mark.asyncio
async def test_pdf_extractor_missing_file(tmp_path):
    router = ChunkRouter()
    router.register(PDFExtractor())

    missing = tmp_path / "missing.pdf"
    res = await router.extract_file(missing)

    assert res.success is False
    assert "not found" in res.error.lower()
