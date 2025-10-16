#!/usr/bin/env python3
"""
Test PLIS Brandenburg WFS Ingestion
Flächennutzungspläne Brandenburg an der Havel
"""

import asyncio
import json
from pathlib import Path
from ingestion.wfs_ingestion_worker import WFSIngestionWorker

async def main():
    # Load config
    config_path = Path("examples/wfs_metadata_plis_brandenburg_test.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("=" * 80)
    print("PLIS Brandenburg - Flächennutzungspläne Test-Ingestion")
    print("=" * 80)
    print(f"Service: {config['ingestion_config']['source_name']}")
    print(f"URL: {config['wfs_service']['url']}")
    print(f"Layers: {len(config['wfs_service']['layers'])}")
    print(f"Feature Limit: {config['wfs_service']['max_features']}")
    print("=" * 80)
    
    # Create worker
    worker = WFSIngestionWorker(config_path)
    
    # Run ingestion
    print("\n🚀 Starting ingestion...\n")
    results = await worker.run_ingestion()
    
    # Print results
    print("\n" + "=" * 80)
    print("INGESTION RESULTS")
    print("=" * 80)
    
    total_fetched = sum(r.features_fetched for r in results)
    total_ingested = sum(r.features_ingested for r in results)
    total_errors = sum(len(r.errors) for r in results)
    total_time = sum(r.processing_time for r in results)
    
    print(f"✅ Total Fetched:      {total_fetched}")
    print(f"✅ Total Ingested:     {total_ingested}")
    print(f"❌ Total Errors:       {total_errors}")
    print(f"⏱️  Processing Time:    {total_time:.2f}s")
    
    if total_fetched > 0:
        print(f"⚡ Speed:              {total_fetched / total_time:.1f} features/sec")
    
    print("=" * 80)
    
    # Layer breakdown
    print("\nLAYER BREAKDOWN:")
    print("-" * 80)
    for result in results:
        layer_name = config['wfs_service']['layers'][results.index(result)]
        layer_short = layer_name.split(':')[-1]  # Remove namespace
        print(f"  {layer_short}:")
        print(f"    Features: {result.features_fetched}")
        print(f"    Ingested: {result.features_ingested}")
        print(f"    Errors:   {len(result.errors)}")
        print(f"    Time:     {result.processing_time:.2f}s")
    
    # Error details
    if total_errors > 0:
        print("\nERROR DETAILS:")
        print("-" * 80)
        for result in results:
            if result.errors:
                for error in result.errors[:5]:  # First 5 errors
                    print(f"  • {error}")
    
    return 0 if all(r.success for r in results) else 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
