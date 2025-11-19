#!/usr/bin/env python3
"""
Tests for OCR Processor
========================

Comprehensive test suite for OCR functionality.

Author: Covina System
Date: 19. November 2025
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import Mock, MagicMock, patch
from ingestion.ocr_processor import (
    OCRProcessor,
    OCRResult,
    process_scanned_pdf
)


class TestOCRProcessor(unittest.TestCase):
    """Test OCR processor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = OCRProcessor()
    
    def test_initialization_no_dependencies(self):
        """Test initialization when OCR dependencies not available"""
        processor = OCRProcessor()
        # Should not crash even if dependencies missing
        self.assertIsNotNone(processor)
        self.assertIn('deu', processor.languages)
        self.assertIn('eng', processor.languages)
        self.assertEqual(processor.dpi, 300)
    
    def test_is_available_without_dependencies(self):
        """Test availability check when dependencies missing"""
        processor = OCRProcessor()
        # If dependencies not installed, should return False
        available = processor.is_available()
        self.assertIsInstance(available, bool)
    
    def test_needs_ocr_low_text_content(self):
        """Test OCR detection for scanned PDFs (low text)"""
        # Mock PDF with very little text
        with patch.object(OCRProcessor, 'is_available', return_value=True):
            processor = OCRProcessor()
            
            # Simulate scanned PDF (10 chars per page)
            extracted_text = "Test"  # Very short
            
            with patch('PyPDF2.PdfReader') as mock_reader:
                mock_pdf = Mock()
                mock_pdf.pages = [Mock()] * 10  # 10 pages
                mock_reader.return_value = mock_pdf
                
                needs_ocr = processor.needs_ocr(
                    "dummy.pdf",
                    extracted_text,
                    threshold=100.0
                )
                
                # Should need OCR (4 chars / 10 pages = 0.4 < 100)
                self.assertTrue(needs_ocr)
    
    def test_needs_ocr_high_text_content(self):
        """Test OCR detection for normal PDFs (high text)"""
        with patch.object(OCRProcessor, 'is_available', return_value=True):
            processor = OCRProcessor()
            
            # Simulate normal PDF (lots of text)
            extracted_text = "A" * 10000  # 10K chars
            
            with patch('PyPDF2.PdfReader') as mock_reader:
                mock_pdf = Mock()
                mock_pdf.pages = [Mock()] * 10  # 10 pages
                mock_reader.return_value = mock_pdf
                
                needs_ocr = processor.needs_ocr(
                    "dummy.pdf",
                    extracted_text,
                    threshold=100.0
                )
                
                # Should NOT need OCR (10000 / 10 = 1000 > 100)
                self.assertFalse(needs_ocr)
    
    def test_ocr_result_creation(self):
        """Test OCRResult dataclass"""
        result = OCRResult(
            text="Sample text",
            page_count=5,
            confidence=0.95,
            is_ocr_processed=True,
            language="deu+eng",
            processing_time=2.5,
            errors=[]
        )
        
        self.assertEqual(result.text, "Sample text")
        self.assertEqual(result.page_count, 5)
        self.assertEqual(result.confidence, 0.95)
        self.assertTrue(result.is_ocr_processed)
        self.assertEqual(result.language, "deu+eng")
        self.assertEqual(result.processing_time, 2.5)
        self.assertEqual(len(result.errors), 0)
    
    def test_ocr_result_to_dict(self):
        """Test OCRResult serialization"""
        result = OCRResult(
            text="Test",
            page_count=1,
            confidence=0.9,
            is_ocr_processed=True,
            language="deu",
            processing_time=1.0,
            errors=["warning"]
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['text'], "Test")
        self.assertEqual(result_dict['page_count'], 1)
        self.assertEqual(result_dict['confidence'], 0.9)
        self.assertTrue(result_dict['is_ocr_processed'])
        self.assertEqual(result_dict['language'], "deu")
        self.assertEqual(result_dict['processing_time'], 1.0)
        self.assertEqual(len(result_dict['errors']), 1)
    
    def test_get_statistics(self):
        """Test statistics generation"""
        processor = OCRProcessor()
        
        result = OCRResult(
            text="Sample OCR text with multiple words",
            page_count=2,
            confidence=0.88,
            is_ocr_processed=True,
            language="deu+eng",
            processing_time=3.2,
            errors=[]
        )
        
        stats = processor.get_statistics(result)
        
        self.assertTrue(stats['ocr_processed'])
        self.assertEqual(stats['ocr_confidence'], 0.88)
        self.assertEqual(stats['ocr_language'], "deu+eng")
        self.assertEqual(stats['ocr_page_count'], 2)
        self.assertEqual(stats['ocr_processing_time'], 3.2)
        self.assertEqual(stats['ocr_char_count'], len(result.text))
        self.assertEqual(stats['ocr_word_count'], len(result.text.split()))
        self.assertFalse(stats['ocr_has_errors'])
        self.assertEqual(stats['ocr_error_count'], 0)
    
    def test_process_scanned_pdf_no_ocr_available(self):
        """Test processing when OCR not available"""
        original_text = "Original extracted text"
        
        with patch.object(OCRProcessor, 'is_available', return_value=False):
            final_text, metadata = process_scanned_pdf(
                "dummy.pdf",
                original_text
            )
            
            # Should return original text
            self.assertEqual(final_text, original_text)
            self.assertFalse(metadata['ocr_processed'])
            self.assertFalse(metadata['ocr_available'])
    
    def test_process_scanned_pdf_not_needed(self):
        """Test processing when OCR not needed"""
        original_text = "A" * 5000  # Lots of text
        
        with patch.object(OCRProcessor, 'is_available', return_value=True):
            with patch.object(OCRProcessor, 'needs_ocr', return_value=False):
                final_text, metadata = process_scanned_pdf(
                    "dummy.pdf",
                    original_text,
                    auto_detect=True
                )
                
                # Should return original text
                self.assertEqual(final_text, original_text)
                self.assertFalse(metadata['ocr_processed'])
                self.assertTrue(metadata['ocr_available'])
                self.assertFalse(metadata['ocr_needed'])
    
    def test_custom_languages(self):
        """Test processor with custom languages"""
        processor = OCRProcessor(languages=['deu', 'fra'])
        
        self.assertEqual(processor.languages, ['deu', 'fra'])
    
    def test_custom_dpi(self):
        """Test processor with custom DPI"""
        processor = OCRProcessor(dpi=150)
        
        self.assertEqual(processor.dpi, 150)


class TestOCRIntegration(unittest.TestCase):
    """Integration tests (require OCR dependencies)"""
    
    def test_ocr_availability_check(self):
        """Test if OCR dependencies are properly detected"""
        processor = OCRProcessor()
        
        # Should return bool without crashing
        available = processor.is_available()
        self.assertIsInstance(available, bool)
        
        if available:
            print("\n✓ OCR dependencies available (pytesseract + pdf2image)")
        else:
            print("\n⚠ OCR dependencies not available")
            print("Install with: pip install pytesseract pdf2image Pillow")
            print("And install Tesseract engine: apt-get install tesseract-ocr")


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("OCR Processor Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all tests
    suite.addTests(loader.loadTestsFromTestCase(TestOCRProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestOCRIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
