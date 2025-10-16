#!/usr/bin/env python3
"""Test der verbesserten Debugging-Ausgabe"""
import asyncio
import sys
sys.path.append('.')

async def test_improved_debugging():
    print('🔧 Test der verbesserten Debugging-Ausgabe')
    print('=' * 50)
    
    # Importiere das Backend
    from backend import process_document_with_uds3
    
    # Erstelle Mock UDS3 Manager
    class MockUDS3Manager:
        def __init__(self):
            self.uds3_ready = False
            self.saga_orchestrator = None
            self.quality_manager = None
            self.security_manager = None  
            self.dsgvo_core = None
            
        def update_performance_metrics(self, result):
            pass
    
    # Test mit einem kleinen Dokument
    test_content = '''
    § 1 Testgesetz
    
    Dieses Gesetz dient der Demonstration der verbesserten Error-Behandlung.
    Es enthält typische rechtliche Begriffe wie Artikel, Paragraph und Bestimmung.
    '''
    
    try:
        mock_manager = MockUDS3Manager()
        result = await process_document_with_uds3('test.pdf', test_content, mock_manager)
        print('✅ Dokumentverarbeitung erfolgreich')
        print(f'📊 Result Keys: {list(result.keys())}')
        
        # Prüfe backend_writes Struktur
        backend_writes = result.get('backend_writes', {})
        print(f'📊 Backend Writes Keys: {list(backend_writes.keys()) if isinstance(backend_writes, dict) else type(backend_writes).__name__}')
        
        for backend, data in backend_writes.items():
            if isinstance(data, dict):
                success_status = data.get('success', 'unknown')
                print(f'  📊 {backend}: success={success_status}')
            else:
                print(f'  📊 {backend}: {type(data).__name__}')
                
    except Exception as e:
        print(f'❌ Test Error: {e}')
        import traceback
        print(f'🔍 Stacktrace: {traceback.format_exc()}')

if __name__ == '__main__':
    asyncio.run(test_improved_debugging())