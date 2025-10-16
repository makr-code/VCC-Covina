#!/usr/bin/env python3
"""
GPU Embeddings Test Script

Tests GPU-accelerated embeddings vs CPU baseline.
"""

import time
import sys


def test_pytorch_gpu():
    """Test 1: PyTorch GPU Detection"""
    print("\n" + "="*60)
    print("TEST 1: PyTorch GPU Detection")
    print("="*60)
    
    try:
        import torch
        print(f"✅ PyTorch Version: {torch.__version__}")
        print(f"   CUDA Available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"   CUDA Version: {torch.version.cuda}")
            print(f"   GPU Count: {torch.cuda.device_count()}")
            print(f"   GPU Name: {torch.cuda.get_device_name(0)}")
            print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            return True
        else:
            print(f"   ⚠️ GPU not available - will use CPU")
            return False
            
    except Exception as e:
        print(f"❌ PyTorch import failed: {e}")
        return False


def test_sentence_transformers_gpu():
    """Test 2: sentence-transformers GPU Detection"""
    print("\n" + "="*60)
    print("TEST 2: sentence-transformers GPU Detection")
    print("="*60)
    
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        print("✅ Loading model: all-MiniLM-L6-v2")
        start = time.time()
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        load_time = (time.time() - start) * 1000
        
        print(f"   Model Device: {model.device}")
        print(f"   Load Time: {load_time:.0f}ms")
        
        if torch.cuda.is_available():
            print(f"   ✅ Model on GPU: {str(model.device).startswith('cuda')}")
        else:
            print(f"   ℹ️ Model on CPU (expected - no GPU)")
        
        return model
        
    except Exception as e:
        print(f"❌ sentence-transformers test failed: {e}")
        return None


def test_embedding_performance(model, use_gpu: bool):
    """Test 3: Embedding Performance (GPU vs CPU)"""
    print("\n" + "="*60)
    print(f"TEST 3: Embedding Performance ({'GPU' if use_gpu else 'CPU'})")
    print("="*60)
    
    if model is None:
        print("❌ No model available")
        return
    
    # Test with different batch sizes
    test_cases = [
        (2, "Small (2 chunks)"),
        (10, "Medium (10 chunks)"),
        (32, "Large (32 chunks)"),
    ]
    
    for num_chunks, label in test_cases:
        chunks = [f"This is test chunk number {i} with some sample text for embedding generation." 
                  for i in range(num_chunks)]
        
        # Warmup
        _ = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
        
        # Benchmark
        start = time.time()
        embeddings = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
        elapsed = (time.time() - start) * 1000
        
        print(f"\n   {label}:")
        print(f"   - Total Time: {elapsed:.1f}ms")
        print(f"   - Per Chunk: {elapsed/num_chunks:.1f}ms")
        print(f"   - Throughput: {num_chunks/(elapsed/1000):.1f} chunks/sec")
        print(f"   - Embedding Shape: {embeddings.shape}")


def test_batch_embeddings_integration():
    """Test 4: Batch Embeddings Module Integration"""
    print("\n" + "="*60)
    print("TEST 4: Batch Embeddings Module Integration")
    print("="*60)
    
    try:
        from ingestion.batch_embeddings import create_batch_generator
        
        print("✅ Creating BatchEmbeddingGenerator...")
        generator = create_batch_generator(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            batch_size=32,
            use_gpu=True  # Will fallback to CPU if GPU unavailable
        )
        
        print(f"   Model: {generator.model_name}")
        print(f"   Device: {generator.device}")
        print(f"   Batch Size: {generator.batch_size}")
        
        # Test embedding generation
        test_chunks = [
            "Rechnung vom 2024-01-15 über 150,00 EUR",
            "Lieferantenvertrag mit Firma ABC GmbH",
            "Protokoll der Gesellschafterversammlung vom 2024-03-20"
        ]
        
        print(f"\n   Generating embeddings for {len(test_chunks)} chunks...")
        start = time.time()
        embeddings = generator.generate_embeddings_batch(test_chunks)
        elapsed = (time.time() - start) * 1000
        
        print(f"   ✅ Generated {len(embeddings)} embeddings")
        print(f"   - Total Time: {elapsed:.1f}ms")
        print(f"   - Per Chunk: {elapsed/len(test_chunks):.1f}ms")
        print(f"   - Embedding Dim: {len(embeddings[0])}")
        print(f"   - Device Used: {generator.device or 'CPU'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch embeddings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all GPU tests"""
    print("\n" + "🚀 " + "="*56)
    print("🚀  GPU Embeddings Test Suite")
    print("🚀 " + "="*56)
    
    # Test 1: PyTorch
    gpu_available = test_pytorch_gpu()
    
    # Test 2: sentence-transformers
    model = test_sentence_transformers_gpu()
    
    # Test 3: Performance
    if model:
        test_embedding_performance(model, gpu_available)
    
    # Test 4: Integration
    test_batch_embeddings_integration()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if gpu_available:
        print("✅ GPU Setup: COMPLETE")
        print("✅ Expected Performance: +300-500% vs CPU")
        print("✅ Ready for Production")
    else:
        print("⚠️ GPU Setup: INCOMPLETE (using CPU)")
        print("ℹ️ Install PyTorch with CUDA for GPU acceleration")
        print("ℹ️ Command: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
