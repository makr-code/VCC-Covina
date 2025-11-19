"""
Simple validation tests for Table Extraction (no pytest required)

Run with: python tests/test_table_extraction_simple.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.table_extractor import TableExtractor, ExtractedTable


def test_extractor_initialization():
    """Test that extractor initializes correctly"""
    print("TEST: Extractor initialization...")
    extractor = TableExtractor()
    
    assert extractor is not None, "Extractor should not be None"
    assert hasattr(extractor, 'available_methods'), "Should have available_methods"
    assert isinstance(extractor.available_methods, dict), "available_methods should be dict"
    
    print("✓ Extractor initialized successfully")
    print(f"  Available methods: {extractor.available_methods}")
    return True


def test_is_available():
    """Test availability check"""
    print("\nTEST: Availability check...")
    extractor = TableExtractor()
    
    result = extractor.is_available()
    assert isinstance(result, bool), "is_available() should return bool"
    
    print(f"✓ Availability check: {result}")
    return True


def test_extracted_table_dataclass():
    """Test ExtractedTable dataclass"""
    print("\nTEST: ExtractedTable dataclass...")
    
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
    assert table.extraction_method == 'test'
    
    print("✓ ExtractedTable dataclass works correctly")
    return True


def test_table_to_dict():
    """Test table serialization to dict"""
    print("\nTEST: Table to_dict() conversion...")
    
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
    
    assert isinstance(result, dict), "to_dict() should return dict"
    assert result['table_index'] == 0
    assert result['rows'] == 2
    assert result['columns'] == 2
    assert result['confidence'] == 0.9
    
    print("✓ to_dict() conversion works")
    print(f"  Dict keys: {list(result.keys())}")
    return True


def test_table_to_csv():
    """Test table conversion to CSV"""
    print("\nTEST: Table to_csv() conversion...")
    
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
    
    assert isinstance(csv, str), "to_csv() should return string"
    assert '"Name","Age"' in csv, "Should contain headers"
    assert '"Alice","30"' in csv, "Should contain data"
    assert '"Bob","25"' in csv, "Should contain data"
    
    lines = csv.split('\n')
    assert len(lines) == 3, "Should have 3 lines (headers + 2 data)"
    
    print("✓ to_csv() conversion works")
    print(f"  CSV preview:\n{csv[:100]}...")
    return True


def test_table_to_json():
    """Test table conversion to JSON"""
    print("\nTEST: Table to_json() conversion...")
    
    import json
    
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
    
    assert isinstance(json_str, str), "to_json() should return string"
    
    # Parse to verify valid JSON
    parsed = json.loads(json_str)
    assert 'headers' in parsed
    assert 'data' in parsed
    assert 'metadata' in parsed
    assert parsed['headers'] == ['Col1', 'Col2']
    
    print("✓ to_json() conversion works")
    print(f"  JSON preview: {json_str[:100]}...")
    return True


def test_unsupported_format():
    """Test that unsupported formats are handled gracefully"""
    print("\nTEST: Unsupported format handling...")
    
    extractor = TableExtractor()
    
    # Unsupported format should return empty list
    tables = extractor.extract_tables("/tmp/test.txt")
    
    assert isinstance(tables, list), "Should return list"
    assert len(tables) == 0, "Should return empty list for unsupported format"
    
    print("✓ Unsupported formats handled gracefully")
    return True


def test_statistics_empty():
    """Test statistics with no tables"""
    print("\nTEST: Statistics with empty table list...")
    
    extractor = TableExtractor()
    stats = extractor.get_table_statistics([])
    
    assert stats['total_tables'] == 0
    assert stats['total_cells'] == 0
    assert stats['avg_rows'] == 0
    assert stats['avg_columns'] == 0
    assert stats['avg_confidence'] == 0.0
    assert stats['methods_used'] == []
    
    print("✓ Empty statistics calculated correctly")
    return True


def test_statistics_with_tables():
    """Test statistics with multiple tables"""
    print("\nTEST: Statistics with tables...")
    
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
    assert stats['total_cells'] == 3*2 + 2*3  # 12
    assert stats['avg_rows'] == 2.5
    assert stats['avg_columns'] == 2.5
    assert stats['avg_confidence'] == 0.85
    assert 'camelot' in stats['methods_used']
    assert 'tabula' in stats['methods_used']
    
    print("✓ Statistics calculated correctly")
    print(f"  Total tables: {stats['total_tables']}")
    print(f"  Total cells: {stats['total_cells']}")
    print(f"  Avg confidence: {stats['avg_confidence']}")
    return True


def test_graceful_fallback():
    """Test graceful fallback when libraries unavailable"""
    print("\nTEST: Graceful fallback...")
    
    extractor = TableExtractor()
    
    # Even without libraries, should not crash
    fake_pdf = "/tmp/nonexistent.pdf"
    tables = extractor.extract_tables(fake_pdf)
    
    assert isinstance(tables, list), "Should return list even without libraries"
    
    print("✓ Graceful fallback works")
    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("Table Extraction - Simple Validation Tests")
    print("=" * 70)
    
    tests = [
        test_extractor_initialization,
        test_is_available,
        test_extracted_table_dataclass,
        test_table_to_dict,
        test_table_to_csv,
        test_table_to_json,
        test_unsupported_format,
        test_statistics_empty,
        test_statistics_with_tables,
        test_graceful_fallback,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
