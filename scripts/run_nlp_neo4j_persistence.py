"""
Task 6: NLP → Neo4j Full Persistence Wrapper
Führt NLP Graph Persistence mit optimierten Production Settings aus.

Usage:
    python scripts\run_nlp_neo4j_persistence.py [--dry-run]

Environment Variablen (optional):
- NLP_INPUT_JSONL (default: data/nlp/entities_full.jsonl)
- NLP_CHECKPOINT_INTERVAL (default: 500)
- NEO4J_URI (default: bolt://192.168.178.94:7687)
- NEO4J_USER (default: neo4j)
- NEO4J_PASSWORD (gelesen aus config oder ENV)
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add uds3 to path
uds3_path = project_root.parent / "uds3"
if uds3_path.exists():
    sys.path.insert(0, str(uds3_path))

try:
    from uds3.core.relations import UDS3RelationsCore
except ImportError:
    print("[WARNING] UDS3RelationsCore nicht verfügbar")
    UDS3RelationsCore = None

from ingestion.graph.nlp_graph_persistence import batch_persist_from_jsonl


def main():
    parser = argparse.ArgumentParser(description="NLP → Neo4j Persistence")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test-Modus ohne echte DB-Writes"
    )
    parser.add_argument(
        "--input",
        default=os.environ.get("NLP_INPUT_JSONL", "data/nlp/entities_full.jsonl"),
        help="Input JSONL file (default: data/nlp/entities_full.jsonl)"
    )
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=int(os.environ.get("NLP_CHECKPOINT_INTERVAL", "500")),
        help="Progress-Logging interval (default: 500)"
    )
    args = parser.parse_args()
    
    # Configuration
    jsonl_path = args.input
    checkpoint_interval = args.checkpoint
    dry_run = args.dry_run
    
    # Neo4j connection details
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://192.168.178.94:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD")
    
    # Try to load password from config_local.py if not in ENV
    if not neo4j_password:
        try:
            # Import config_local from uds3
            uds3_config_path = project_root.parent / "uds3"
            sys.path.insert(0, str(uds3_config_path))
            import config_local
            neo4j_password = getattr(config_local, "NEO4J_PASSWORD", None)
        except ImportError:
            pass
    
    # Default fallback (from copilot-instructions.md)
    if not neo4j_password:
        neo4j_password = "neo4j"  # Default for dev
    
    print("=" * 80)
    print("Task 6: NLP → Neo4j Full Persistence")
    print("=" * 80)
    print(f"Start Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input JSONL:   {jsonl_path}")
    print(f"Checkpoint:    Every {checkpoint_interval} docs")
    print(f"Dry Run:       {dry_run}")
    print(f"Neo4j URI:     {neo4j_uri}")
    print(f"Neo4j User:    {neo4j_user}")
    print("=" * 80)
    
    # Check if input file exists
    if not os.path.exists(jsonl_path):
        print(f"\n[ERROR] Input file not found: {jsonl_path}")
        print("[INFO] Waiting for NLP extraction to complete...")
        print("[INFO] Expected output from: python -m ingestion.nlp_extraction --batch")
        sys.exit(1)
    
    # Get file size for ETA estimation
    file_size_mb = os.path.getsize(jsonl_path) / (1024 * 1024)
    print(f"\n[INFO] Input file size: {file_size_mb:.1f} MB")
    
    # Count lines for progress tracking
    with open(jsonl_path, encoding="utf-8") as f:
        total_lines = sum(1 for line in f if line.strip())
    print(f"[INFO] Total documents to process: {total_lines:,}")
    
    # Estimate processing time (based on L4 benchmark: ~210 docs/min)
    estimated_minutes = total_lines / 210
    print(f"[INFO] Estimated processing time: ~{estimated_minutes:.0f} minutes")
    print()
    
    # Initialize UDS3 Neo4j wrapper if not dry-run
    neo4j_wrapper = None
    if not dry_run:
        if UDS3RelationsCore is None:
            print("[ERROR] UDS3RelationsCore nicht verfügbar - Verwende Dry-Run stattdessen")
            dry_run = True
        else:
            try:
                neo4j_wrapper = UDS3RelationsCore(
                    neo4j_uri=neo4j_uri,
                    neo4j_auth=(neo4j_user, neo4j_password)
                )
                print(f"[SUCCESS] UDS3 Neo4j Wrapper initialisiert")
                print(f"           URI: {neo4j_uri}")
                print()
            except Exception as e:
                print(f"[ERROR] UDS3 Initialisierung fehlgeschlagen: {e}")
                print("[INFO] Fallback zu Dry-Run Modus")
                dry_run = True
                print()
    
    # Run batch persistence
    start_time = datetime.now()
    
    try:
        stats = batch_persist_from_jsonl(
            jsonl_path=jsonl_path,
            neo4j_wrapper=neo4j_wrapper,
            checkpoint_interval=checkpoint_interval,
            dry_run=dry_run
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("Task 6: COMPLETE!")
        print("=" * 80)
        print(f"End Time:        {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:        {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print()
        print("Statistics:")
        print(f"  Docs processed:     {stats['docs_processed']:,}")
        print(f"  Entities created:   {stats['entities_created']:,}")
        print(f"  Relations created:  {stats['relations_created']:,}")
        print(f"  Errors:             {stats['errors']:,}")
        print()
        
        if stats['docs_processed'] > 0:
            docs_per_min = stats['docs_processed'] / (duration / 60)
            entities_per_doc = stats['entities_created'] / stats['docs_processed']
            relations_per_doc = stats['relations_created'] / stats['docs_processed']
            
            print("Performance:")
            print(f"  Processing speed:   {docs_per_min:.1f} docs/min")
            print(f"  Entities per doc:   {entities_per_doc:.1f}")
            print(f"  Relations per doc:  {relations_per_doc:.1f}")
            print()
        
        print("=" * 80)
        
        # Write summary to file
        summary_path = "data/nlp/persistence_summary.txt"
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("Task 6: NLP → Neo4j Full Persistence Summary\n")
            f.write("=" * 80 + "\n")
            f.write(f"Completed:       {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration:        {duration:.1f} seconds ({duration/60:.1f} minutes)\n")
            f.write(f"Input:           {jsonl_path}\n")
            f.write(f"Dry Run:         {dry_run}\n")
            f.write("\n")
            f.write("Statistics:\n")
            f.write(f"  Docs processed:     {stats['docs_processed']:,}\n")
            f.write(f"  Entities created:   {stats['entities_created']:,}\n")
            f.write(f"  Relations created:  {stats['relations_created']:,}\n")
            f.write(f"  Errors:             {stats['errors']:,}\n")
        
        print(f"[INFO] Summary saved to: {summary_path}")
        
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user (Ctrl+C)")
        print("[INFO] Partial progress has been saved to Neo4j")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Persistence failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
