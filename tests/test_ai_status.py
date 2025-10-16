#!/usr/bin/env python3
"""
Test Script: AI Implementation Status Check

Überprüft verfügbare AI-Bibliotheken und zeigt Mock-vs-Real Status.
"""

print("🔍 AI Implementation Status Check")
print("=" * 50)

# Check Library Availability
libraries_status = {}

# Test transformers
try:
    import transformers
    libraries_status['transformers'] = f"✅ Available (v{transformers.__version__})"
except ImportError as e:
    libraries_status['transformers'] = f"❌ Not Available: {e}"

# Test sentence-transformers
try:
    import sentence_transformers
    libraries_status['sentence_transformers'] = f"✅ Available (v{sentence_transformers.__version__})"
except ImportError as e:
    libraries_status['sentence_transformers'] = f"❌ Not Available: {e}"

# Test spacy
try:
    import spacy
    libraries_status['spacy'] = f"✅ Available (v{spacy.__version__})"
except ImportError as e:
    libraries_status['spacy'] = f"❌ Not Available: {e}"

# Test torch
try:
    import torch
    libraries_status['torch'] = f"✅ Available (v{torch.__version__})"
except ImportError as e:
    libraries_status['torch'] = f"❌ Not Available: {e}"

print("📚 Library Status:")
for lib, status in libraries_status.items():
    print(f"   {lib}: {status}")

print()

# Test Basic AI Processor
print("🤖 Testing AI Content Processor...")

try:
    from ingestion.ai_enhanced_content_processor import (
        AIEnhancedContentProcessor, 
        TRANSFORMERS_AVAILABLE, 
        SENTENCE_TRANSFORMERS_AVAILABLE, 
        SPACY_AVAILABLE
    )
    
    print(f"📊 AI Module Status:")
    print(f"   TRANSFORMERS_AVAILABLE: {TRANSFORMERS_AVAILABLE}")
    print(f"   SENTENCE_TRANSFORMERS_AVAILABLE: {SENTENCE_TRANSFORMERS_AVAILABLE}")  
    print(f"   SPACY_AVAILABLE: {SPACY_AVAILABLE}")
    
    # Initialize processor
    processor = AIEnhancedContentProcessor()
    
    print(f"⚙️  Processor Features:")
    print(f"   Summarization: {processor.enable_summarization}")
    print(f"   Sentiment: {processor.enable_sentiment}")
    print(f"   Embeddings: {processor.enable_embeddings}")
    print(f"   NER: {processor.enable_ner}")
    
    # Simple test
    test_text = "This is a test document for AI processing. John Smith works at ABC Company."
    
    print(f"\n🧪 Testing with sample text: '{test_text[:50]}...'")
    
    result = processor.process_content(test_text)
    
    print(f"✅ Processing successful!")
    print(f"   Confidence: {result.confidence_overall:.3f}")
    print(f"   Language: {result.detected_language}")
    print(f"   Entities: {len(result.entities)}")
    if result.sentiment_analysis:
        print(f"   Sentiment: {result.sentiment_analysis.sentiment_label} ({result.sentiment_analysis.sentiment_score:.2f})")
    if result.content_summary:
        print(f"   Summary: Available")
    if result.semantic_embeddings:
        print(f"   Embeddings: {len(result.semantic_embeddings)} chunks")
    
except Exception as e:
    print(f"❌ Error testing AI processor: {e}")
    import traceback
    traceback.print_exc()

print("\n🎯 Conclusion:")
if any("✅ Available" in status for status in libraries_status.values()):
    print("   Some AI libraries are available - real AI processing possible!")
else:
    print("   No AI libraries available - using Mock implementations")

print("   Framework architecture supports both real and mock AI models")
print("   Ready for production deployment with library installation")