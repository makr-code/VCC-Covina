#!/usr/bin/env python3
"""
Direct SAGA Function Test

Tests process_document_with_saga() directly without going through the API.
"""

import asyncio
import sys

# Add parent directory to path
sys.path.insert(0, 'C:/VCC/Covina')

async def test_saga():
    print("=" * 60)
    print("SAGA Direct Function Test")
    print("=" * 60)
    print()
    
    # Import ingestion backend
    from ingestion_backend import get_job_manager, process_document_with_saga
    
    # Get job manager
    jm = get_job_manager()
    
    # Test file
    file_path = "C:/VCC/Covina/test_upload_small/test_doc_1.txt"
    content = "Test Dokument 1\nInhalt: Dies ist ein Testvertrag für die Ingestion.\nDatum: 2025-10-13"
    
    print(f"Testing SAGA with: {file_path}")
    print(f"Content length: {len(content)} chars")
    print()
    
    # Call SAGA function directly
    try:
        result = await process_document_with_saga(file_path, content, jm)
        
        print("✅ SAGA Result:")
        print(f"   processing_mode: {result.get('processing_mode')}")
        print(f"   saga_status: {result.get('saga_status')}")
        print(f"   document_id: {result.get('document_id')}")
        print(f"   classification: {result.get('classification')}")
        print(f"   databases_written: {result.get('databases_written')}")
        
        if result.get('error'):
            print(f"   ❌ Error: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ SAGA Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_saga())
