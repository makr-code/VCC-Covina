"""
Office Document Ingestion Handler

Handles PDF, DOCX, XLSX, PPTX extraction with OCR support for scanned PDFs.
"""
from .base import BaseIngestionHandler, HandlerContext
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class OfficeIngestionHandler(BaseIngestionHandler):
    """
    Handler for office documents (PDF, DOCX, XLSX, PPTX).
    
    Features:
    - PDF text extraction
    - OCR for scanned PDFs (automatic detection)
    - DOCX, XLSX, PPTX extraction (basic)
    """
    
    def __init__(self):
        super().__init__()
        self._ocr_processor = None
        self._table_extractor = None
    
    def _get_ocr_processor(self):
        """Lazy-load OCR processor"""
        if self._ocr_processor is None:
            try:
                from ingestion.ocr_processor import OCRProcessor
                self._ocr_processor = OCRProcessor()
                logger.info("✓ OCR processor initialized")
            except Exception as e:
                logger.warning(f"OCR processor unavailable: {e}")
                self._ocr_processor = None
        return self._ocr_processor
    
    def _get_table_extractor(self):
        """Lazy-load table extractor"""
        if self._table_extractor is None:
            try:
                from ingestion.table_extractor import TableExtractor
                self._table_extractor = TableExtractor()
                if self._table_extractor.is_available():
                    logger.info("✓ Table extractor initialized")
                else:
                    logger.warning("Table extraction libraries not available")
                    self._table_extractor = None
            except Exception as e:
                logger.warning(f"Table extractor unavailable: {e}")
                self._table_extractor = None
        return self._table_extractor
    
    def extract_metadata(self, context: HandlerContext) -> Dict[str, Any]:
        """Extract metadata from office documents"""
        metadata = {
            "handler": "office",
            "file": str(context.file_path),
            "file_type": Path(context.file_path).suffix.lower()
        }
        
        # Add file size
        try:
            metadata["file_size"] = Path(context.file_path).stat().st_size
        except:
            pass
        
        # Extract tables if available
        table_extractor = self._get_table_extractor()
        if table_extractor:
            try:
                tables = table_extractor.extract_tables(str(context.file_path))
                if tables:
                    # Add table statistics to metadata
                    table_stats = table_extractor.get_table_statistics(tables)
                    metadata['tables'] = table_stats
                    metadata['has_tables'] = True
                    metadata['table_count'] = len(tables)
                    
                    # Store extracted tables for later use
                    context.tables = tables
                    
                    logger.info(f"✓ Extracted {len(tables)} tables from {context.file_path}")
            except Exception as e:
                logger.warning(f"Table extraction failed: {e}")
                metadata['has_tables'] = False
        
        return metadata
    
    def extract_content(self, context: HandlerContext, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract content from office documents.
        
        Supports:
        - PDF (with OCR fallback for scanned documents)
        - DOCX, XLSX, PPTX (basic extraction)
        - TXT (direct read)
        """
        file_path = str(context.file_path)
        file_type = Path(file_path).suffix.lower()
        
        try:
            # PDF handling with OCR support
            if file_type == '.pdf':
                return self._extract_pdf(file_path, metadata)
            
            # DOCX handling
            elif file_type in ['.docx', '.doc']:
                return self._extract_docx(file_path, metadata)
            
            # Plain text fallback
            else:
                return self._extract_text(file_path)
        
        except Exception as e:
            logger.error(f"Content extraction failed for {file_path}: {e}")
            return None
    
    def _extract_pdf(self, file_path: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract text from PDF with OCR fallback for scanned documents.
        
        Strategy:
        1. Try standard PDF text extraction (PyPDF2)
        2. If insufficient text (<100 chars/page), try OCR
        3. Use better result
        """
        text = ""
        
        # Try standard PDF extraction first
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            
            pages_text = []
            for page in reader.pages:
                pages_text.append(page.extract_text())
            
            text = '\n\n'.join(pages_text)
            metadata['pdf_page_count'] = len(reader.pages)
            logger.debug(f"PDF standard extraction: {len(text)} chars from {len(reader.pages)} pages")
        
        except Exception as e:
            logger.warning(f"Standard PDF extraction failed: {e}")
        
        # Check if OCR needed (scanned PDF detection)
        ocr_processor = self._get_ocr_processor()
        if ocr_processor and ocr_processor.is_available():
            # Check if text extraction was poor (likely scanned)
            if ocr_processor.needs_ocr(file_path, text):
                logger.info(f"Scanned PDF detected - applying OCR: {Path(file_path).name}")
                
                try:
                    from ingestion.ocr_processor import process_scanned_pdf
                    ocr_text, ocr_metadata = process_scanned_pdf(file_path, text, auto_detect=False)
                    
                    # Update metadata with OCR info
                    metadata.update(ocr_metadata)
                    
                    # Use OCR text if better
                    if len(ocr_text.strip()) > len(text.strip()):
                        logger.info(f"Using OCR text ({len(ocr_text)} chars vs {len(text)} chars)")
                        text = ocr_text
                    
                except Exception as e:
                    logger.error(f"OCR processing failed: {e}")
                    # Continue with standard extraction
        
        return text if text.strip() else None
    
    def _extract_docx(self, file_path: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract text from DOCX files"""
        try:
            import docx
            doc = docx.Document(file_path)
            
            paragraphs = [para.text for para in doc.paragraphs]
            text = '\n\n'.join(paragraphs)
            
            metadata['docx_paragraph_count'] = len(paragraphs)
            return text if text.strip() else None
        
        except ImportError:
            logger.warning("python-docx not installed - cannot extract DOCX")
            return None
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return None
    
    def _extract_text(self, file_path: str) -> Optional[str]:
        """Fallback: read as plain text"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return None


__all__ = ["OfficeIngestionHandler"]
