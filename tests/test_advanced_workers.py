"""
Tests for Advanced Ingestion Features (Workers)

Tests for:
- Document Similarity Worker
- Quality Metrics Worker
- SAGA Executors

Author: GitHub Copilot
Date: 2025-11-19
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_similarity_worker():
    """Test 1: Similarity Worker Initialization"""
    print("=" * 80)
    print("Test 1: Similarity Worker Initialization")
    print("=" * 80)
    print()
    
    try:
        from ingestion.workers.similarity_worker import SimilarityWorker, SimilarityTask
        
        # Initialize worker
        worker = SimilarityWorker(num_workers=2)
        worker.start()
        
        print("✓ SimilarityWorker initialized successfully")
        print(f"  Workers: {worker.num_workers}")
        print(f"  Executor: {worker.executor is not None}")
        
        # Shutdown
        worker.shutdown()
        print("✓ Worker shutdown successful")
        
        return True
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_quality_worker():
    """Test 2: Quality Metrics Worker"""
    print()
    print("=" * 80)
    print("Test 2: Quality Metrics Worker")
    print("=" * 80)
    print()
    
    try:
        from ingestion.workers.quality_worker import QualityMetricsWorker, QualityTask
        
        # Initialize worker
        worker = QualityMetricsWorker(num_workers=4)
        worker.start()
        
        print("✓ QualityMetricsWorker initialized successfully")
        print(f"  Workers: {worker.num_workers}")
        
        # Create test task
        task = QualityTask(
            chunk_id='test_chunk_001',
            content='§ 1 Zweck des Gesetzes\n\n(1) Zweck dieses Gesetzes ist es, Menschen zu schützen.',
            metadata={'keywords': ['Schutz', 'Gesetz']},
            enrich_chromadb=False
        )
        
        # Process task
        result = worker.process_task(task)
        
        if result.get('success'):
            metrics = result['metrics']
            print("✓ Quality metrics computed successfully")
            print(f"  Overall Score: {metrics['overall_score']:.2f}")
            print(f"  Completeness: {metrics['completeness_score']:.2f}")
            print(f"  Readability: {metrics['readability_score']:.2f}")
            print(f"  Info Density: {metrics['information_density_score']:.2f}")
            print(f"  Word Count: {metrics['word_count']}")
            print(f"  Sentence Count: {metrics['sentence_count']}")
        else:
            print(f"❌ Quality computation failed: {result.get('error')}")
            return False
        
        # Shutdown
        worker.shutdown()
        print("✓ Worker shutdown successful")
        
        return True
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_batch_processing():
    """Test 3: Batch Quality Processing"""
    print()
    print("=" * 80)
    print("Test 3: Batch Quality Processing")
    print("=" * 80)
    print()
    
    try:
        from ingestion.workers.quality_worker import QualityMetricsWorker, QualityTask
        
        # Initialize worker
        worker = QualityMetricsWorker(num_workers=4)
        worker.start()
        
        # Create multiple tasks
        tasks = [
            QualityTask(
                chunk_id=f'chunk_{i:03d}',
                content=f'Test content {i} with some text.',
                metadata={},
                enrich_chromadb=False
            )
            for i in range(10)
        ]
        
        # Process batch
        results = worker.process_batch(tasks)
        
        successful = sum(1 for r in results if r.get('success'))
        print(f"✓ Batch processing completed")
        print(f"  Total tasks: {len(tasks)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {len(tasks) - successful}")
        
        if successful > 0:
            avg_score = sum(r['metrics']['overall_score'] for r in results if r.get('success')) / successful
            print(f"  Average quality score: {avg_score:.2f}")
        
        # Shutdown
        worker.shutdown()
        
        return successful == len(tasks)
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_document_chunks():
    """Test 4: Document-Wide Quality Analysis"""
    print()
    print("=" * 80)
    print("Test 4: Document-Wide Quality Analysis")
    print("=" * 80)
    print()
    
    try:
        from ingestion.workers.quality_worker import QualityMetricsWorker
        
        # Initialize worker
        worker = QualityMetricsWorker(num_workers=4)
        worker.start()
        
        # Sample document chunks
        chunks = [
            {
                'id': 'chunk_001',
                'content': '§ 1 Zweck des Gesetzes\n\n(1) Zweck dieses Gesetzes ist es...',
                'metadata': {'keywords': ['Schutz', 'Gesetz']}
            },
            {
                'id': 'chunk_002',
                'content': '(2) Soweit es sich um genehmigungsbedürftige Anlagen handelt...',
                'metadata': {'keywords': ['Anlage', 'Genehmigung']}
            },
            {
                'id': 'chunk_003',
                'content': '(3) Dieses Gesetz gilt für folgende Bereiche:\n- Industrie\n- Verkehr',
                'metadata': {}
            }
        ]
        
        # Process document
        result = worker.process_document_chunks(chunks, enrich_chromadb=False)
        
        print(f"✓ Document quality analysis completed")
        print(f"  Total chunks: {result['total_chunks']}")
        print(f"  Successful: {result['successful_chunks']}")
        print(f"  Failed: {result['failed_chunks']}")
        print()
        print("Aggregated Metrics:")
        metrics = result['aggregated_metrics']
        print(f"  Average Overall Score: {metrics['avg_overall_score']:.2f}")
        print(f"  Average Completeness: {metrics['avg_completeness_score']:.2f}")
        print(f"  Average Readability: {metrics['avg_readability_score']:.2f}")
        print(f"  Average Info Density: {metrics['avg_info_density_score']:.2f}")
        print(f"  Total Words: {metrics['total_words']}")
        print(f"  Total Sentences: {metrics['total_sentences']}")
        print(f"  Chunks with Headings: {metrics['chunks_with_headings']}")
        print(f"  Chunks with Lists: {metrics['chunks_with_lists']}")
        print(f"  Chunks with References: {metrics['chunks_with_references']}")
        
        # Shutdown
        worker.shutdown()
        
        return result['successful_chunks'] == result['total_chunks']
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_similarity_engine():
    """Test 5: Similarity Engine Basic Functions"""
    print()
    print("=" * 80)
    print("Test 5: Similarity Engine Basic Functions")
    print("=" * 80)
    print()
    
    try:
        from ingestion.document_similarity import DocumentSimilarityEngine
        import numpy as np
        
        # Initialize engine
        engine = DocumentSimilarityEngine()
        
        # Test cosine similarity
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        vec3 = np.array([1.0, 0.0, 0.0])
        
        sim_orthogonal = engine.cosine_similarity(vec1, vec2)
        sim_identical = engine.cosine_similarity(vec1, vec3)
        
        print("✓ Cosine similarity computed")
        print(f"  Orthogonal vectors: {sim_orthogonal:.2f} (expected: ~0.50)")
        print(f"  Identical vectors: {sim_identical:.2f} (expected: ~1.00)")
        
        # Test with actual embeddings
        emb1 = np.random.rand(384)
        emb2 = np.random.rand(384)
        
        sim = engine.cosine_similarity(emb1, emb2)
        print(f"  Random embeddings: {sim:.2f}")
        
        return True
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_saga_executors():
    """Test 6: SAGA Executors"""
    print()
    print("=" * 80)
    print("Test 6: SAGA Executors")
    print("=" * 80)
    print()
    
    try:
        from ingestion.saga_executors_advanced import (
            SimilaritySAGAExecutor,
            QualityMetricsSAGAExecutor,
            create_advanced_executors
        )
        
        # Create executors
        executors = create_advanced_executors()
        
        print("✓ SAGA executors created successfully")
        print(f"  Executors: {list(executors.keys())}")
        
        # Test quality metrics executor
        print()
        print("Testing Quality Metrics Executor:")
        
        quality_op = {
            'action': 'compute_quality',
            'params': {
                'chunk_id': 'test_chunk',
                'content': '§ 1 Test content for quality analysis.',
                'metadata': {'keywords': ['test']},
                'enrich_chromadb': False
            }
        }
        
        import asyncio
        
        async def test_quality_executor():
            result = await executors['quality_metrics'].execute_forward(quality_op)
            return result
        
        quality_result = asyncio.run(test_quality_executor())
        
        if quality_result.get('success'):
            print("  ✓ Quality computation successful")
            print(f"    Overall score: {quality_result['metrics']['overall_score']:.2f}")
        else:
            print(f"  ❌ Quality computation failed: {quality_result.get('error')}")
        
        # Shutdown executors
        executors['similarity'].shutdown()
        executors['quality_metrics'].shutdown()
        
        print("✓ Executors shutdown successfully")
        
        return quality_result.get('success', False)
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="  * 80)
    print("ADVANCED INGESTION FEATURES - TEST SUITE")
    print("=" * 80)
    print()
    
    tests = [
        ("Similarity Worker Init", test_similarity_worker),
        ("Quality Worker", test_quality_worker),
        ("Quality Batch Processing", test_quality_batch_processing),
        ("Document-Wide Quality", test_quality_document_chunks),
        ("Similarity Engine", test_similarity_engine),
        ("SAGA Executors", test_saga_executors),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed ({100*passed//total}%)")
    print()
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
    else:
        print("⚠️  SOME TESTS FAILED")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
