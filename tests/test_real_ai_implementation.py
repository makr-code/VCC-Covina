#!/usr/bin/env python3
"""
Test Script: Real AI Implementation vs Mock

Testet die echte AI-Implementierung mit transformer Models
gegen die vorherigen Mock-Ergebnisse.
"""

import logging
from pathlib import Path
from ingestion.ai_enhanced_content_processor import AIEnhancedContentProcessor

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_real_ai_implementation():
    """Testet echte AI-Modelle mit verschiedenen Content-Typen"""
    
    print("🚀 Testing Real AI Implementation")
    print("=" * 60)
    
    # Initialize AI processor mit echten Modellen
    config = {
        'summarization_model': 'facebook/bart-large-cnn',  # Für Zusammenfassungen
        'embedding_model': 'all-MiniLM-L6-v2',  # Für Embeddings
        'sentiment_model': 'cardiffnlp/twitter-roberta-base-sentiment-latest',  # Für Sentiment
        'ner_model': 'en_core_web_sm',  # spaCy für NER (falls verfügbar)
        'enable_summarization': True,
        'enable_sentiment': True, 
        'enable_embeddings': True,
        'enable_ner': True,
        'enable_domain_analysis': True
    }
    
    processor = AIEnhancedContentProcessor(config)
    
    # Test Cases - dieselben wie im Mock-Test
    test_cases = [
        {
            'name': 'Business Report',
            'content': '''
            Q3 Financial Report - ABC Corporation
            
            Our quarterly results show strong performance across all business units. 
            Revenue increased by 15% to $2.5 million, while operating expenses remained 
            stable at $1.8 million. Key achievements include the successful launch of 
            our new product line and expansion into the European market.
            
            CEO John Smith commented: "We are pleased with these results and remain 
            optimistic about Q4 prospects." The company will announce dividend 
            payments next month.
            
            For more information, contact investor.relations@abc-corp.com
            '''
        },
        {
            'name': 'Medical Research',
            'content': '''
            Clinical Study: Efficacy of Treatment Protocol XYZ
            
            This randomized controlled trial evaluated the effectiveness of Treatment 
            Protocol XYZ in 200 patients with chronic condition ABC. Patient ID 12345 
            showed remarkable improvement, while participants demonstrated an average 
            symptom reduction of 40%.
            
            Dr. Sarah Johnson, lead researcher at Memorial Hospital, noted significant 
            improvements in quality of life metrics. The study was conducted according 
            to HIPAA guidelines and ethical standards.
            
            Contact: research@memorial-hospital.org
            Phone: +1-555-0123
            '''
        },
        {
            'name': 'Legal Document',
            'content': '''
            CONFIDENTIAL SETTLEMENT AGREEMENT
            
            This Agreement is entered into between Plaintiff Jane Doe (SSN: 123-45-6789) 
            and Defendant XYZ Corporation. The parties agree to settle all claims 
            related to Case No. CV-2023-001234 for the amount of $50,000.
            
            Attorney Michael Brown represents the plaintiff in this matter. 
            All proceedings are subject to federal regulations under 18 USC § 1964.
            
            This document contains privileged attorney-client communications and 
            is protected under applicable privacy laws including GDPR Article 6.
            '''
        }
    ]
    
    print(f"📋 Processing {len(test_cases)} test cases with REAL AI models...")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🔬 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Verarbeite mit echten AI-Modellen
            result = processor.process_content(
                content=test_case['content'],
                file_path=Path(f"test_{test_case['name'].lower().replace(' ', '_')}.txt")
            )
            
            # Zeige Ergebnisse
            print(f"✅ Processing successful!")
            print(f"📊 Overall confidence: {result.confidence_overall:.3f}")
            print(f"🗣️  Detected language: {result.detected_language}")
            print(f"📝 Content length: {result.content_length} characters")
            
            # Entities (NER)
            if result.entities:
                print(f"🏷️  Entities found: {len(result.entities)}")
                for entity in result.entities[:5]:  # Show first 5
                    print(f"   - {entity.text} ({entity.label}, confidence: {entity.confidence:.2f})")
            else:
                print("🏷️  No entities found (using fallback NER)")
            
            # Sentiment Analysis
            if result.sentiment_analysis:
                print(f"😊 Sentiment: {result.sentiment_analysis.sentiment_label}")
                print(f"   Score: {result.sentiment_analysis.sentiment_score:.3f}")
                print(f"   Confidence: {result.sentiment_analysis.confidence:.3f}")
            
            # Embeddings
            if result.semantic_embeddings:
                embedding = result.semantic_embeddings[0]
                print(f"🧠 Semantic embedding: {len(embedding.vector)}D vector")
                print(f"   Model: {embedding.model_name}")
                print(f"   Sample values: [{embedding.vector[0]:.3f}, {embedding.vector[1]:.3f}, ...]")
            
            # Summarization
            if result.content_summary:
                print(f"📋 Summary available:")
                print(f"   Abstractive: {result.content_summary.abstractive_summary[:100]}...")
                print(f"   Compression: {result.content_summary.compression_ratio:.1f}x")
                print(f"   Confidence: {result.content_summary.confidence_score:.3f}")
            
            # Domain Analysis
            if result.domain_analysis:
                print(f"🎯 Domain: {result.domain_analysis.domain}")
                print(f"   Risk Level: {result.domain_analysis.risk_assessment}")
                if result.domain_analysis.compliance_indicators:
                    print(f"   Compliance: {', '.join(result.domain_analysis.compliance_indicators)}")
            
            # PII Detection
            if result.advanced_pii:
                high_risk = [pii for pii in result.advanced_pii if pii.risk_level == 'high']
                print(f"🔒 PII Elements: {len(result.advanced_pii)} total")
                if high_risk:
                    print(f"   ⚠️  High Risk: {len(high_risk)} elements")
                    for pii in high_risk[:3]:
                        print(f"      - {pii.pii_type}: {pii.masked_text}")
            
            # Processing Info
            duration = (result.processing_timestamp).strftime("%H:%M:%S")
            models_info = []
            if processor.enable_summarization:
                models_info.append("✅ Real Summarization")
            if processor.enable_sentiment:
                models_info.append("✅ Real Sentiment")
            if processor.enable_embeddings:
                models_info.append("✅ Real Embeddings") 
            if processor.enable_ner:
                models_info.append("✅ Real NER")
            else:
                models_info.append("🔄 Mock NER")
            
            print(f"⚡ Models used: {', '.join(models_info)}")
            print(f"🕐 Processed at: {duration}")
            
        except Exception as e:
            print(f"❌ Error processing {test_case['name']}: {e}")
            logger.exception(f"Processing failed for {test_case['name']}")
        
        print()
    
    print("🎉 Real AI Implementation Test Complete!")
    print("=" * 60)
    
    # Model Status Summary
    print("📊 Final Model Status:")
    print(f"   Transformers Available: {hasattr(processor, 'enable_summarization') and processor.enable_summarization}")
    print(f"   Sentence-Transformers Available: {hasattr(processor, 'enable_embeddings') and processor.enable_embeddings}")
    print(f"   Sentiment Analysis Available: {hasattr(processor, 'enable_sentiment') and processor.enable_sentiment}")
    print(f"   spaCy NER Available: {hasattr(processor, 'enable_ner') and processor.enable_ner}")

if __name__ == "__main__":
    test_real_ai_implementation()