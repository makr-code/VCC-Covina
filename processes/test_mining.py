"""Quick test for process mining pipeline.

Run:
    python -m processes.test_mining
"""

from processes.mining import RuleEngine, ProcessMiningPipeline, DocumentMeta


def main():
    print("=" * 80)
    print("Process Mining Pipeline - Quick Test")
    print("=" * 80)
    
    # Load YAML guidelines
    print("\n1. Loading YAML guidelines...")
    try:
        engine = RuleEngine(yaml_path="processes/guidelines/process_inference.yml")
        print("   ✅ RuleEngine loaded")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Create pipeline
    print("\n2. Creating pipeline...")
    pipeline = ProcessMiningPipeline(engine)
    print("   ✅ ProcessMiningPipeline created")
    
    # Test documents
    print("\n3. Creating test documents...")
    docs = [
        DocumentMeta(
            doc_id="doc_001",
            title="Antrag Bauleitplanung 2025-10-30",
            date="2025-10-30",
            authority="Landkreis Potsdam-Mittelmark",
            aktenzeichen="AZ-12345/2025"
        ),
        DocumentMeta(
            doc_id="doc_002",
            title="Stellungnahme 2025-11-06",
            date="2025-11-06",
            authority="Landkreis Potsdam-Mittelmark",
            aktenzeichen="AZ-12345/2025"
        ),
        DocumentMeta(
            doc_id="doc_003",
            title="Bescheid 2025-11-20",
            date="2025-11-20",
            authority="Stadt Brandenburg",
            aktenzeichen="V-98765/2025"
        ),
    ]
    print(f"   ✅ Created {len(docs)} test documents")
    
    # Run inference
    print("\n4. Running batch inference...")
    result = pipeline.infer_batch("bauleitplanung_test", docs)
    print(f"   ✅ Inference complete")
    
    # Display results
    print("\n" + "=" * 80)
    print("Results")
    print("=" * 80)
    
    print(f"\nProcess Key: {result.process_key}")
    print(f"Documents: {result.stats['docs']}")
    
    print("\nNode Confidence:")
    for step_key, conf in sorted(result.node_confidence.items(), key=lambda x: x[1], reverse=True):
        print(f"  {step_key:20s} {conf:.4f}")
    
    print(f"\nPaths: {len(result.paths)}")
    for path in result.paths:
        print(f"  {path.path_key} (confidence: {path.confidence:.4f})")
        print(f"    Steps: {len(path.steps)}")
        for step in path.steps[:3]:  # Show first 3
            print(f"      - {step.step_key} (confidence: {step.confidence:.4f})")
    
    print("\n" + "=" * 80)
    print("✅ Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
