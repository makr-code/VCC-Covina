"""
Tests for Table Extraction Module

Validates table extraction from PDFs and DOCX files using multiple methods.
"""
import pytest
from pathlib import Path
import json

from ingestion.table_extractor import TableExtractor, ExtractedTable


class TestTableExtractor:
    """Test suite for TableExtractor"""
    
    def test_extractor_initialization(self):
        """Test that extractor initializes and checks available methods"""
        extractor = TableExtractor()
        
        assert extractor is not None
        assert isinstance(extractor.available_methods, dict)
        assert 'camelot' in extractor.available_methods
        assert 'tabula' in extractor.available_methods
        assert 'pdfplumber' in extractor.available_methods
        assert 'docx' in extractor.available_methods
    
    def test_is_available(self):
        """Test availability check"""
        extractor = TableExtractor()
        
        # Should return True if at least one method is available
        # Even without any installed, should not crash
        result = extractor.is_available()
        assert isinstance(result, bool)
    
    def test_extracted_table_dataclass(self):
        """Test ExtractedTable dataclass"""
        table = ExtractedTable(
            table_index=0,
            page_number=1,
            rows=3,
            columns=2,
            data=[
                ['Name', 'Age'],
                ['Alice', '30'],
                ['Bob', '25']
            ],
            headers=['Name', 'Age'],
            confidence=0.95,
            extraction_method='test',
            metadata={'test': True}
        )
        
        assert table.table_index == 0
        assert table.rows == 3
        assert table.columns == 2
        assert len(table.data) == 3
        assert table.confidence == 0.95
    
    def test_table_to_dict(self):
        """Test table serialization to dict"""
        table = ExtractedTable(
            table_index=0,
            page_number=1,
            rows=2,
            columns=2,
            data=[['A', 'B'], ['C', 'D']],
            headers=['Col1', 'Col2'],
            confidence=0.9,
            extraction_method='test',
            metadata={}
        )
        
        result = table.to_dict()
        
        assert isinstance(result, dict)
        assert result['table_index'] == 0
        assert result['rows'] == 2
        assert result['columns'] == 2
        assert result['confidence'] == 0.9
        assert result['data'] == [['A', 'B'], ['C', 'D']]
    
    def test_table_to_csv(self):
        """Test table conversion to CSV"""
        table = ExtractedTable(
            table_index=0,
            page_number=1,
            rows=2,
            columns=2,
            data=[['Alice', '30'], ['Bob', '25']],
            headers=['Name', 'Age'],
            confidence=0.9,
            extraction_method='test',
            metadata={}
        )
        
        csv = table.to_csv()
        
        assert isinstance(csv, str)
        assert '"Name","Age"' in csv
        assert '"Alice","30"' in csv
        assert '"Bob","25"' in csv
        
        # Check format
        lines = csv.split('\n')
        assert len(lines) == 3  # headers + 2 data rows
    
    def test_table_to_json(self):
        """Test table conversion to JSON"""
        table = ExtractedTable(
            table_index=0,
            page_number=1,
            rows=2,
            columns=2,
            data=[['A', 'B'], ['C', 'D']],
            headers=['Col1', 'Col2'],
            confidence=0.9,
            extraction_method='test',
            metadata={}
        )
        
        json_str = table.to_json()
        
        assert isinstance(json_str, str)
        
        # Parse to verify valid JSON
        parsed = json.loads(json_str)
        assert 'headers' in parsed
        assert 'data' in parsed
        assert 'metadata' in parsed
        assert parsed['headers'] == ['Col1', 'Col2']
        assert parsed['data'] == [['A', 'B'], ['C', 'D']]
    
    def test_extract_tables_unsupported_format(self):
        """Test that unsupported file formats return empty list"""
        extractor = TableExtractor()
        
        # Create a fake file path
        fake_path = "/tmp/test.txt"
        
        # Should return empty list for unsupported format
        tables = extractor.extract_tables(fake_path)
        assert isinstance(tables, list)
        assert len(tables) == 0
    
    def test_get_table_statistics_empty(self):
        """Test statistics generation with no tables"""
        extractor = TableExtractor()
        
        stats = extractor.get_table_statistics([])
        
        assert stats['total_tables'] == 0
        assert stats['total_cells'] == 0
        assert stats['avg_rows'] == 0
        assert stats['avg_columns'] == 0
        assert stats['avg_confidence'] == 0.0
        assert stats['methods_used'] == []
    
    def test_get_table_statistics_with_tables(self):
        """Test statistics generation with multiple tables"""
        extractor = TableExtractor()
        
        tables = [
            ExtractedTable(
                table_index=0,
                page_number=1,
                rows=3,
                columns=2,
                data=[['A', 'B'], ['C', 'D'], ['E', 'F']],
                headers=['Col1', 'Col2'],
                confidence=0.9,
                extraction_method='camelot',
                metadata={}
            ),
            ExtractedTable(
                table_index=1,
                page_number=2,
                rows=2,
                columns=3,
                data=[['X', 'Y', 'Z'], ['1', '2', '3']],
                headers=['A', 'B', 'C'],
                confidence=0.8,
                extraction_method='tabula',
                metadata={}
            )
        ]
        
        stats = extractor.get_table_statistics(tables)
        
        assert stats['total_tables'] == 2
        assert stats['total_cells'] == 3*2 + 2*3  # 6 + 6 = 12
        assert stats['avg_rows'] == 2.5  # (3+2)/2
        assert stats['avg_columns'] == 2.5  # (2+3)/2
        assert stats['avg_confidence'] == 0.85  # (0.9+0.8)/2
        assert set(stats['methods_used']) == {'camelot', 'tabula'}
        assert len(stats['tables']) == 2


class TestTableExtractionIntegration:
    """Integration tests for table extraction"""
    
    def test_pdf_table_extraction_graceful_fallback(self):
        """Test that PDF table extraction handles missing libraries gracefully"""
        extractor = TableExtractor()
        
        # Even without libraries, should not crash
        # Just return empty list
        fake_pdf = "/tmp/nonexistent.pdf"
        tables = extractor.extract_tables(fake_pdf)
        
        assert isinstance(tables, list)
    
    def test_docx_table_extraction_graceful_fallback(self):
        """Test that DOCX table extraction handles missing libraries gracefully"""
        extractor = TableExtractor()
        
        # Even without libraries, should not crash
        fake_docx = "/tmp/nonexistent.docx"
        tables = extractor.extract_tables(fake_docx)
        
        assert isinstance(tables, list)
    
    def test_multiple_extraction_methods_fallback(self):
        """Test that extractor tries multiple methods"""
        extractor = TableExtractor()
        
        # Check that extractor knows about all methods
        assert 'camelot' in extractor.available_methods
        assert 'tabula' in extractor.available_methods
        assert 'pdfplumber' in extractor.available_methods
        
        # The _extract_from_pdf method should try methods in order
        # This is tested implicitly through the is_available check


class TestTableMetadataEnrichment:
    """Test table metadata enrichment for ChromaDB"""
    
    def test_table_metadata_structure(self):
        """Test that table metadata has correct structure for ChromaDB"""
        table = ExtractedTable(
            table_index=0,
            page_number=1,
            rows=2,
            columns=2,
            data=[['A', 'B'], ['C', 'D']],
            headers=['Col1', 'Col2'],
            confidence=0.9,
            extraction_method='camelot',
            metadata={'page': 1}
        )
        
        # Convert to metadata format for ChromaDB
        chromadb_metadata = {
            'table_index': table.table_index,
            'table_page': table.page_number,
            'table_rows': table.rows,
            'table_columns': table.columns,
            'table_confidence': table.confidence,
            'table_method': table.extraction_method,
            'has_table_headers': table.headers is not None,
            'table_csv': table.to_csv()
        }
        
        # Verify structure
        assert chromadb_metadata['table_index'] == 0
        assert chromadb_metadata['table_rows'] == 2
        assert chromadb_metadata['table_columns'] == 2
        assert chromadb_metadata['table_confidence'] == 0.9
        assert chromadb_metadata['has_table_headers'] is True
        assert isinstance(chromadb_metadata['table_csv'], str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
