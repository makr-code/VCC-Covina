#!/usr/bin/env python3
"""
OCR Processor for Scanned PDFs
================================

Automatic OCR processing for image-based PDFs and scanned documents.
Detects when PDFs contain primarily images and extracts text using Tesseract OCR.

Features:
- Image-based PDF detection (heuristic: text/page ratio)
- Multi-language OCR support (German + English)
- Page-by-page processing
- Fallback to original text extraction
- Quality metrics and confidence scores

Dependencies:
- pytesseract: Python wrapper for Tesseract OCR
- Pillow (PIL): Image processing
- pdf2image: PDF to image conversion

Installation:
```bash
# Install Tesseract OCR engine
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-deu

# macOS:
brew install tesseract tesseract-lang

# Windows:
# Download from: https://github.com/UB-Mannheim/tesseract/wiki

# Install Python packages
pip install pytesseract pdf2image Pillow
```

Author: Covina System
Date: 19. November 2025
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR processing"""
    text: str
    page_count: int
    confidence: float  # 0.0-1.0
    is_ocr_processed: bool
    language: str
    processing_time: float  # seconds
    errors: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'text': self.text,
            'page_count': self.page_count,
            'confidence': self.confidence,
            'is_ocr_processed': self.is_ocr_processed,
            'language': self.language,
            'processing_time': self.processing_time,
            'errors': self.errors
        }


class OCRProcessor:
    """
    Process scanned PDFs and images with OCR.
    
    Features:
    - Automatic image-based PDF detection
    - Multi-language support (German + English)
    - Graceful fallback when OCR unavailable
    - Quality metrics (confidence scores)
    
    Usage:
    ```python
    processor = OCRProcessor()
    
    # Check if PDF needs OCR
    if processor.needs_ocr("scan.pdf", text_content):
        result = processor.process_pdf("scan.pdf")
        print(f"Extracted: {len(result.text)} chars")
        print(f"Confidence: {result.confidence:.2f}")
    ```
    """
    
    def __init__(
        self,
        languages: List[str] = None,
        dpi: int = 300,
        tesseract_cmd: Optional[str] = None
    ):
        """
        Initialize OCR processor.
        
        Args:
            languages: OCR languages (default: ['deu', 'eng'])
            dpi: DPI for PDF to image conversion (default: 300)
            tesseract_cmd: Path to tesseract executable (auto-detect if None)
        """
        self.languages = languages or ['deu', 'eng']
        self.dpi = dpi
        self.tesseract_available = False
        self.pdf2image_available = False
        
        # Try to import dependencies
        try:
            import pytesseract
            self.pytesseract = pytesseract
            
            # Set tesseract command if provided
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            
            # Test if tesseract is available
            try:
                pytesseract.get_tesseract_version()
                self.tesseract_available = True
                logger.info(f"✓ Tesseract OCR available: {pytesseract.get_tesseract_version()}")
            except Exception as e:
                logger.warning(f"⚠ Tesseract not available: {e}")
                
        except ImportError:
            logger.warning("⚠ pytesseract not installed. OCR disabled.")
            logger.info("Install with: pip install pytesseract")
        
        # Try to import pdf2image
        try:
            from pdf2image import convert_from_path
            self.convert_from_path = convert_from_path
            self.pdf2image_available = True
            logger.info("✓ pdf2image available")
        except ImportError:
            logger.warning("⚠ pdf2image not installed. PDF OCR disabled.")
            logger.info("Install with: pip install pdf2image")
    
    def is_available(self) -> bool:
        """Check if OCR is available"""
        return self.tesseract_available and self.pdf2image_available
    
    def needs_ocr(
        self,
        file_path: str,
        extracted_text: str,
        threshold: float = 100.0
    ) -> bool:
        """
        Determine if a PDF needs OCR processing.
        
        Heuristic: If text extraction yields less than `threshold` chars per page,
        the PDF is likely image-based.
        
        Args:
            file_path: Path to PDF file
            extracted_text: Text extracted by standard method
            threshold: Chars per page threshold (default: 100)
        
        Returns:
            True if OCR recommended
        """
        if not self.is_available():
            return False
        
        # Get page count
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
        except Exception as e:
            logger.warning(f"Could not count pages: {e}")
            page_count = 1
        
        # Calculate chars per page
        chars_per_page = len(extracted_text.strip()) / max(page_count, 1)
        
        needs_ocr = chars_per_page < threshold
        
        if needs_ocr:
            logger.info(
                f"📄 PDF appears to be scanned "
                f"({chars_per_page:.1f} chars/page < {threshold}). "
                f"OCR recommended."
            )
        
        return needs_ocr
    
    def process_pdf(
        self,
        file_path: str,
        max_pages: Optional[int] = None
    ) -> OCRResult:
        """
        Process a PDF file with OCR.
        
        Args:
            file_path: Path to PDF file
            max_pages: Maximum pages to process (None = all)
        
        Returns:
            OCRResult with extracted text and metadata
        """
        import time
        start_time = time.time()
        
        errors = []
        
        if not self.is_available():
            return OCRResult(
                text="",
                page_count=0,
                confidence=0.0,
                is_ocr_processed=False,
                language="",
                processing_time=0.0,
                errors=["OCR dependencies not available"]
            )
        
        try:
            # Convert PDF to images
            logger.info(f"Converting PDF to images (DPI: {self.dpi})...")
            images = self.convert_from_path(
                file_path,
                dpi=self.dpi,
                first_page=1,
                last_page=max_pages
            )
            
            page_count = len(images)
            logger.info(f"Processing {page_count} pages with OCR...")
            
            # Process each page
            page_texts = []
            confidences = []
            
            for i, image in enumerate(images, 1):
                try:
                    # OCR with detailed output
                    data = self.pytesseract.image_to_data(
                        image,
                        lang='+'.join(self.languages),
                        output_type=self.pytesseract.Output.DICT
                    )
                    
                    # Extract text
                    page_text = self.pytesseract.image_to_string(
                        image,
                        lang='+'.join(self.languages)
                    )
                    page_texts.append(page_text)
                    
                    # Calculate average confidence for this page
                    page_confidences = [
                        float(conf) for conf in data['conf']
                        if conf != '-1'  # -1 means no text detected
                    ]
                    if page_confidences:
                        avg_confidence = sum(page_confidences) / len(page_confidences)
                        confidences.append(avg_confidence / 100.0)  # Normalize to 0-1
                    
                    logger.debug(f"Page {i}/{page_count}: {len(page_text)} chars extracted")
                    
                except Exception as e:
                    error_msg = f"Error processing page {i}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    page_texts.append("")
            
            # Combine results
            full_text = '\n\n'.join(page_texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            processing_time = time.time() - start_time
            
            logger.info(
                f"✓ OCR complete: {len(full_text)} chars extracted "
                f"from {page_count} pages "
                f"(confidence: {avg_confidence:.2%}, "
                f"time: {processing_time:.1f}s)"
            )
            
            return OCRResult(
                text=full_text,
                page_count=page_count,
                confidence=avg_confidence,
                is_ocr_processed=True,
                language='+'.join(self.languages),
                processing_time=processing_time,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"OCR processing failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            return OCRResult(
                text="",
                page_count=0,
                confidence=0.0,
                is_ocr_processed=False,
                language="",
                processing_time=time.time() - start_time,
                errors=errors
            )
    
    def process_image(
        self,
        file_path: str
    ) -> OCRResult:
        """
        Process a single image file with OCR.
        
        Args:
            file_path: Path to image file (PNG, JPG, TIFF, etc.)
        
        Returns:
            OCRResult with extracted text
        """
        import time
        start_time = time.time()
        
        errors = []
        
        if not self.tesseract_available:
            return OCRResult(
                text="",
                page_count=0,
                confidence=0.0,
                is_ocr_processed=False,
                language="",
                processing_time=0.0,
                errors=["Tesseract not available"]
            )
        
        try:
            from PIL import Image
            
            # Load image
            image = Image.open(file_path)
            
            # OCR with confidence
            data = self.pytesseract.image_to_data(
                image,
                lang='+'.join(self.languages),
                output_type=self.pytesseract.Output.DICT
            )
            
            # Extract text
            text = self.pytesseract.image_to_string(
                image,
                lang='+'.join(self.languages)
            )
            
            # Calculate confidence
            confidences = [
                float(conf) for conf in data['conf']
                if conf != '-1'
            ]
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"✓ Image OCR: {len(text)} chars "
                f"(confidence: {avg_confidence:.2%})"
            )
            
            return OCRResult(
                text=text,
                page_count=1,
                confidence=avg_confidence,
                is_ocr_processed=True,
                language='+'.join(self.languages),
                processing_time=processing_time,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Image OCR failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            return OCRResult(
                text="",
                page_count=0,
                confidence=0.0,
                is_ocr_processed=False,
                language="",
                processing_time=time.time() - start_time,
                errors=errors
            )
    
    def get_statistics(self, result: OCRResult) -> Dict:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with stats for metadata
        """
        return {
            'ocr_processed': result.is_ocr_processed,
            'ocr_confidence': result.confidence,
            'ocr_language': result.language,
            'ocr_page_count': result.page_count,
            'ocr_processing_time': result.processing_time,
            'ocr_char_count': len(result.text),
            'ocr_word_count': len(result.text.split()),
            'ocr_has_errors': len(result.errors) > 0,
            'ocr_error_count': len(result.errors)
        }


# Convenience function for easy integration
def process_scanned_pdf(
    file_path: str,
    extracted_text: str,
    auto_detect: bool = True
) -> Tuple[str, Dict]:
    """
    Process a potentially scanned PDF with automatic OCR detection.
    
    Args:
        file_path: Path to PDF file
        extracted_text: Text extracted by standard method
        auto_detect: Auto-detect if OCR needed (default: True)
    
    Returns:
        Tuple of (final_text, ocr_metadata)
        
    Usage:
    ```python
    text, metadata = process_scanned_pdf("scan.pdf", original_text)
    
    # metadata includes:
    # - ocr_processed: bool
    # - ocr_confidence: float
    # - ocr_char_count: int
    # etc.
    ```
    """
    processor = OCRProcessor()
    
    # Check if OCR is available
    if not processor.is_available():
        logger.info("OCR not available - using original text extraction")
        return extracted_text, {
            'ocr_processed': False,
            'ocr_available': False,
            'ocr_confidence': 0.0
        }
    
    # Auto-detect if OCR needed
    if auto_detect and not processor.needs_ocr(file_path, extracted_text):
        logger.info("PDF has sufficient text - OCR not needed")
        return extracted_text, {
            'ocr_processed': False,
            'ocr_available': True,
            'ocr_needed': False,
            'ocr_confidence': 1.0  # Standard extraction
        }
    
    # Process with OCR
    logger.info("Processing PDF with OCR...")
    result = processor.process_pdf(file_path)
    
    # Use OCR text if successful and better than original
    if result.is_ocr_processed and len(result.text.strip()) > len(extracted_text.strip()):
        logger.info(f"Using OCR text ({len(result.text)} chars vs {len(extracted_text)} chars)")
        final_text = result.text
    else:
        logger.info("Using original extracted text")
        final_text = extracted_text
    
    return final_text, processor.get_statistics(result)
