"""
Image Ingestion Handler with OCR Support

Handles image files (PNG, JPG, TIFF, etc.) with OCR text extraction.
"""
from .base import BaseIngestionHandler, HandlerContext
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageIngestionHandler(BaseIngestionHandler):
    """
    Handler for image files (PNG, JPG, TIFF, etc.).
    
    Features:
    - OCR text extraction from images
    - Image metadata extraction (dimensions, format)
    - Graceful fallback when OCR unavailable
    """
    
    def __init__(self):
        super().__init__()
        self._ocr_processor = None
    
    def _get_ocr_processor(self):
        """Lazy-load OCR processor"""
        if self._ocr_processor is None:
            try:
                from ingestion.ocr_processor import OCRProcessor
                self._ocr_processor = OCRProcessor()
                logger.info("✓ OCR processor initialized for images")
            except Exception as e:
                logger.warning(f"OCR processor unavailable: {e}")
                self._ocr_processor = None
        return self._ocr_processor
    
    def extract_metadata(self, context: HandlerContext) -> Dict[str, Any]:
        """Extract metadata from image files"""
        metadata = {
            "handler": "image",
            "file": str(context.file_path),
            "file_type": Path(context.file_path).suffix.lower()
        }
        
        # Try to get image dimensions
        try:
            from PIL import Image
            with Image.open(context.file_path) as img:
                metadata["image_width"] = img.width
                metadata["image_height"] = img.height
                metadata["image_format"] = img.format
                metadata["image_mode"] = img.mode
        except Exception as e:
            logger.debug(f"Could not extract image metadata: {e}")
        
        # Add file size
        try:
            metadata["file_size"] = Path(context.file_path).stat().st_size
        except:
            pass
        
        return metadata
    
    def extract_content(self, context: HandlerContext, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract text content from image using OCR.
        
        Returns:
            Extracted text if OCR successful, placeholder otherwise
        """
        file_path = str(context.file_path)
        
        # Try OCR extraction
        ocr_processor = self._get_ocr_processor()
        if ocr_processor and ocr_processor.is_available():
            try:
                logger.info(f"Applying OCR to image: {Path(file_path).name}")
                result = ocr_processor.process_image(file_path)
                
                # Add OCR metadata
                metadata.update(ocr_processor.get_statistics(result))
                
                if result.is_ocr_processed and result.text.strip():
                    logger.info(f"OCR extracted {len(result.text)} chars (confidence: {result.confidence:.2%})")
                    return result.text
                else:
                    logger.warning("OCR returned no text")
            
            except Exception as e:
                logger.error(f"OCR processing failed: {e}")
        else:
            logger.debug("OCR not available for image extraction")
        
        # Fallback: return placeholder
        return f"[Image: {context.file_path.name}]"


__all__ = ["ImageIngestionHandler"]
