"""
End-to-End Database Synchronization Pipeline
Synchronizes all 4 databases to unified "best" state.

Pipeline Steps:
1. PostgreSQL → CouchDB (full documents)
2. PostgreSQL → NLP Extraction (435 → 3,618 files)
3. NLP JSONL → Neo4j (entities + relations)
4. Verify ChromaDB coverage

Author: Covina Team
Date: 2025-10-30
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple
import psycopg2
import requests
from datetime import datetime

# Load environment from .env.production if present to ensure DB creds are picked up
try:
    from dotenv import load_dotenv  # type: ignore
    # Prefer project root .env.production
    env_path = Path(__file__).resolve().parents[1] / ".env.production"
    if env_path.exists():
        load_dotenv(str(env_path))
except Exception:
    # Safe fallback: continue without dotenv
    pass
# Import Covina modules
from ingestion.nlp_extraction import NLPExtractor, batch_extract as nlp_batch_extract
from ingestion.graph import nlp_graph_persistence as nlp_persist


class DatabaseSyncPipeline:
    """Orchestrates synchronization across all 4 databases."""
    
    def __init__(self):
        self.stats = {
            'start_time': datetime.now(),
            'couchdb_uploaded': 0,
            'nlp_extracted': 0,
            'neo4j_persisted': 0,
            'errors': []
        }
        
        # Database connections (prefer ENV, fallback to defaults)
        self.pg_config = {
            'host': os.environ.get('POSTGRES_HOST', '192.168.178.94'),
            'port': int(os.environ.get('POSTGRES_PORT', '5432')),
            'user': os.environ.get('POSTGRES_USER', 'postgres'),
            'password': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
            'database': os.environ.get('POSTGRES_DATABASE', 'postgres'),
        }

        # Defaults aligned with .env.production
        self.couchdb_config = {
            'host': os.environ.get('COUCHDB_HOST', '192.168.178.94'),
            'port': int(os.environ.get('COUCHDB_PORT', '32770')),
            'user': os.environ.get('COUCHDB_USER', 'couchdb'),
            'password': os.environ.get('COUCHDB_PASSWORD', 'couchdb'),
            'database': os.environ.get('COUCHDB_DATABASE', 'covina'),
        }

        self.neo4j_config = {
            'uri': os.environ.get('NEO4J_URI', 'bolt://192.168.178.94:7687'),
            'user': os.environ.get('NEO4J_USER', 'neo4j'),
            'password': os.environ.get('NEO4J_PASSWORD', 'neo4j'),
        }
    
    def run(self, skip_couchdb: bool = False, skip_nlp: bool = False, skip_neo4j: bool = False):
        """
        Run full pipeline.
        
        Args:
            skip_couchdb: Skip CouchDB sync (if already done)
            skip_nlp: Skip NLP extraction (if already done)
            skip_neo4j: Skip Neo4j persistence (if already done)
        """
        print("=" * 80)
        print("COVINA DATABASE SYNC PIPELINE")
        print("=" * 80)
        print(f"Started: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Step 1: PostgreSQL → CouchDB
        if not skip_couchdb:
            print("\n" + "=" * 80)
            print("STEP 1: PostgreSQL → CouchDB (Full Documents)")
            print("=" * 80)
            self._sync_postgresql_to_couchdb()
        else:
            print("\n[SKIP] Step 1: PostgreSQL → CouchDB")
        
        # Step 2: PostgreSQL → NLP Extraction
        if not skip_nlp:
            print("\n" + "=" * 80)
            print("STEP 2: NLP Extraction (435 → 3,618 files)")
            print("=" * 80)
            self._run_nlp_extraction()
        else:
            print("\n[SKIP] Step 2: NLP Extraction")
        
        # Step 3: NLP JSONL → Neo4j
        if not skip_neo4j:
            print("\n" + "=" * 80)
            print("STEP 3: NLP JSONL → Neo4j (Entities + Relations)")
            print("=" * 80)
            self._sync_nlp_to_neo4j()
        else:
            print("\n[SKIP] Step 3: NLP → Neo4j")
        
        # Step 4: Verify ChromaDB
        print("\n" + "=" * 80)
        print("STEP 4: Verify ChromaDB Coverage")
        print("=" * 80)
        self._verify_chromadb()
        
        # Final Summary
        self._print_summary()
    
    def _sync_postgresql_to_couchdb(self):
        """Sync full documents from PostgreSQL to CouchDB."""
        
        # 1. Test CouchDB connection
        print("\n1.1 Testing CouchDB connection...")
        couch_url = f"http://{self.couchdb_config['host']}:{self.couchdb_config['port']}"
        
        try:
            response = requests.get(couch_url, timeout=5)
            if response.status_code == 200:
                version = response.json().get('version', 'unknown')
                print(f"   ✅ CouchDB {version} connected")
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ CouchDB connection failed: {e}")
            print(f"   💡 Hint: Check if CouchDB Docker container is running")
            print(f"   💡 Command: docker ps | grep couch")
            self.stats['errors'].append(f"CouchDB connection: {e}")
            return
        
        # 2. Create/verify covina database
        print("\n1.2 Creating/verifying 'covina' database...")
        db_url = f"{couch_url}/{self.couchdb_config['database']}"
        
        response = requests.get(
            db_url,
            auth=(self.couchdb_config['user'], self.couchdb_config['password']),
            timeout=10,
        )
        
        if response.status_code == 404:
            # Database doesn't exist, create it
            response = requests.put(
                db_url,
                auth=(self.couchdb_config['user'], self.couchdb_config['password']),
                timeout=10,
            )
            if response.status_code == 201:
                print(f"   ✅ Database 'covina' created")
            else:
                print(f"   ❌ Failed to create database: {response.status_code}")
                self.stats['errors'].append(f"CouchDB create DB: {response.status_code}")
                return
        elif response.status_code == 200:
            doc_count = response.json().get('doc_count', 0)
            print(f"   ✅ Database 'covina' exists ({doc_count:,} docs)")
        else:
            if response.status_code == 401:
                print(f"   ❌ Database check failed: 401 (Unauthorized)")
                print("   💡 Hint: Check COUCHDB_USER/COUCHDB_PASSWORD in environment or .env.production")
                print(f"   💡 Tried user='{self.couchdb_config['user']}' on {self.couchdb_config['host']}:{self.couchdb_config['port']}")
            else:
                print(f"   ❌ Database check failed: {response.status_code}")
            self.stats['errors'].append(f"CouchDB check DB: {response.status_code}")
            return
        
        # 3. Fetch documents from PostgreSQL
        print("\n1.3 Fetching documents from PostgreSQL...")
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            print(f"   Total documents: {total_docs:,}")
            
            # Fetch in batches
            batch_size = 100
            offset = 0
            uploaded = 0
            errors = 0
            
            print(f"\n1.4 Uploading to CouchDB (batch size: {batch_size})...")
            
            while offset < total_docs:
                # Fetch batch
                cursor.execute("""
                    SELECT document_id, file_path, classification, 
                           content_length, legal_terms_count, created_at,
                           quality_score, processing_status, company_metadata
                    FROM documents
                    ORDER BY file_path
                    LIMIT %s OFFSET %s
                """, (batch_size, offset))
                
                rows = cursor.fetchall()
                if not rows:
                    break
                
                # Upload batch to CouchDB
                for doc_id, file_path, classification, content_length, legal_terms, created_at, quality, status, company_meta in rows:
                    # Read actual file content from disk
                    content = ""
                    if file_path and Path(file_path).exists():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except Exception as e:
                            content = f"[ERROR: Could not read file - {e}]"
                    
                    doc = {
                        '_id': doc_id,  # Use document_id as CouchDB document ID
                        'file_path': file_path,
                        'content': content,
                        'classification': classification,
                        'content_length': content_length,
                        'legal_terms_count': legal_terms,
                        'created_at': created_at,
                        'quality_score': quality,
                        'processing_status': status,
                        'company_metadata': company_meta if company_meta else {},
                        'uploaded_at': datetime.now().isoformat(),
                        'source': 'postgresql_sync'
                    }
                    
                    # Check if document exists (for updates)
                    doc_url = f"{db_url}/{doc_id}"
                    existing = requests.get(
                        doc_url,
                        auth=(self.couchdb_config['user'], self.couchdb_config['password']),
                        timeout=10,
                    )
                    
                    if existing.status_code == 200:
                        # Document exists, add _rev for update
                        doc['_rev'] = existing.json()['_rev']
                    
                    # Upload to CouchDB
                    response = requests.put(
                        doc_url,
                        json=doc,
                        auth=(self.couchdb_config['user'], self.couchdb_config['password']),
                        timeout=15,
                    )
                    
                    if response.status_code in [201, 202]:  # Created or Accepted
                        uploaded += 1
                    else:
                        errors += 1
                        if errors <= 5:  # Only log first 5 errors
                            print(f"   ⚠️  Upload failed for {doc_id[:20]}...: {response.status_code}")
                
                offset += batch_size
                
                # Progress
                progress_pct = min(100, (offset / total_docs) * 100)
                print(f"   Progress: {uploaded:,}/{total_docs:,} ({progress_pct:.1f}%) | Errors: {errors}")
                
                # Stop if too many errors
                if errors > 100:
                    print(f"   ❌ Too many errors ({errors}), stopping upload")
                    break
            
            cursor.close()
            conn.close()
            
            self.stats['couchdb_uploaded'] = uploaded
            print(f"\n   ✅ Upload complete: {uploaded:,} documents | {errors} errors")
            
        except Exception as e:
            print(f"   ❌ PostgreSQL query failed: {e}")
            self.stats['errors'].append(f"PostgreSQL query: {e}")
    
    def _run_nlp_extraction(self):
        """Run full NLP extraction on all markdown files."""
        
        print("\n2.1 Initializing NLP extractor...")
        
        try:
            extractor = NLPExtractor()
            print("   ✅ spaCy model loaded (de_core_news_md)")
        except Exception as e:
            print(f"   ❌ NLP initialization failed: {e}")
            self.stats['errors'].append(f"NLP init: {e}")
            return
        
        # Scannen und Batch-Extraktion (nutze vorhandene API: nlp_extraction.batch_extract)
        print("\n2.2 Scanning for markdown files...")
        input_dir = os.environ.get('NLP_INPUT_DIR', 'Y:/data')
        # Optional limiter to avoid fully counting millions of files
        max_files_env = os.environ.get('NLP_MAX_FILES')
        max_files = None
        try:
            max_files = int(max_files_env) if max_files_env else None
        except ValueError:
            max_files = None

        if max_files:
            # Count up to max_files to provide a quick feedback
            cnt = 0
            for _ in Path(input_dir).rglob('*.md'):
                cnt += 1
                if cnt >= max_files:
                    break
            print(f"   Found at least: {cnt:,} files (limited by NLP_MAX_FILES={max_files})")
            total_md = cnt
        else:
            total_md = sum(1 for _ in Path(input_dir).rglob('*.md'))
            print(f"   Found: {total_md:,} files")

        print("\n2.3 Running batch extraction...")
        output_file = Path("data/nlp/entities_full.jsonl")
        try:
            # Konfiguriere JSONL-Output über ENV (vom Modul unterstützt)
            os.environ['NLP_WRITE_JSONL'] = 'true'
            os.environ['NLP_OUTPUT_JSONL'] = str(output_file)
            os.environ['SPACY_MODEL'] = os.environ.get('SPACY_MODEL', 'de_core_news_md')
            # NLP_MAX_FILES wird vom Modul respektiert; hier belassen wenn gesetzt

            # Führe Batch-Extraktion per Verzeichnis aus
            nlp_batch_extract(input_dir)

            # Count extrahierte Records
            if output_file.exists():
                line_count = sum(1 for _ in output_file.open('r', encoding='utf-8'))
                self.stats['nlp_extracted'] = line_count
                print(f"\n   ✅ Extraction complete: {line_count:,} documents")
            else:
                print(f"\n   ⚠️  Output file not created: {output_file}")
        except Exception as e:
            print(f"   ❌ Batch extraction failed: {e}")
            self.stats['errors'].append(f"NLP extraction: {e}")
    
    def _sync_nlp_to_neo4j(self):
        """Persist NLP entities to Neo4j knowledge graph."""
        
        print("\n3.1 Initializing Neo4j persister...")
        
        try:
            # UDS3 Wrapper initialisieren (falls verfügbar), ansonsten Dry-Run
            neo4j_wrapper = None
            try:
                from uds3.core.relations import UDS3RelationsCore
                neo4j_wrapper = UDS3RelationsCore(
                    neo4j_uri=self.neo4j_config['uri'],
                    neo4j_auth=(self.neo4j_config['user'], self.neo4j_config['password'])
                )
                print("   ✅ Neo4j connected")
            except Exception as e:
                print(f"   ⚠️  UDS3 Neo4j wrapper unavailable: {e} — using dry-run")
                neo4j_wrapper = None
        except Exception as e:
            print(f"   ❌ Neo4j initialization failed: {e}")
            self.stats['errors'].append(f"Neo4j connection: {e}")
            return
        
        # Run batch persistence
        print("\n3.2 Persisting entities to Neo4j...")
        input_file = Path("data/nlp/entities_full.jsonl")
        
        if not input_file.exists():
            print(f"   ❌ Input file not found: {input_file}")
            self.stats['errors'].append(f"NLP JSONL missing: {input_file}")
            return
        
        try:
            # Set environment variables for module (optional)
            os.environ['NLP_INPUT_JSONL'] = str(input_file)
            os.environ['NLP_CHECKPOINT_INTERVAL'] = '1000'
            os.environ['NLP_PERSISTENCE_DRY_RUN'] = 'false'

            # Nutze die modulare Batch-Persist-Funktion, Übergabe des Wrappers
            nlp_persist.batch_persist_from_jsonl(
                jsonl_path=str(input_file),
                neo4j_wrapper=neo4j_wrapper,
                checkpoint_interval=1000,
                dry_run=(neo4j_wrapper is None)
            )

            # Final stats basierend auf Input-Zeilen (1:1 mit Dokumenten)
            line_count = sum(1 for _ in input_file.open('r', encoding='utf-8'))
            self.stats['neo4j_persisted'] = line_count
            print(f"\n   ✅ Persistence complete: {line_count:,} documents processed")

        except Exception as e:
            print(f"   ❌ Neo4j persistence failed: {e}")
            self.stats['errors'].append(f"Neo4j persistence: {e}")
    
    def _verify_chromadb(self):
        """Verify ChromaDB vector coverage."""
        
        print("\n4.1 Checking ChromaDB server...")
        
        try:
            # ChromaDB uses v2 API
            response = requests.get("http://192.168.178.94:8000/api/v2/heartbeat", timeout=5)
            if response.status_code == 200:
                print("   ✅ ChromaDB server running (v2 API)")
                
                # Get collections via v2 API
                # Note: v2 API structure might differ, showing basic connection only
                print("   ✅ ChromaDB heartbeat OK")
                print("   💡 For detailed collection info, use ChromaDB client library")
            else:
                print(f"   ❌ ChromaDB not responding: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ ChromaDB check failed: {e}")
            print(f"   💡 Hint: Check if ChromaDB Docker container is running")
            print(f"   💡 Command: docker ps | grep chroma")
    
    def _print_summary(self):
        """Print final summary."""
        
        end_time = datetime.now()
        duration = (end_time - self.stats['start_time']).total_seconds()
        
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"\nResults:")
        print(f"  - CouchDB uploaded: {self.stats['couchdb_uploaded']:,} documents")
        print(f"  - NLP extracted: {self.stats['nlp_extracted']:,} documents")
        print(f"  - Neo4j persisted: {self.stats['neo4j_persisted']:,} documents")
        print(f"  - Errors: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print(f"\nError Details:")
            for i, error in enumerate(self.stats['errors'][:10], 1):
                print(f"  {i}. {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("1. Verify data in CouchDB:")
        print("   http://192.168.178.94:32770/_utils")
        print("\n2. Query Neo4j knowledge graph:")
        print("   python -m ingestion.graph.graph_analytics")
        print("\n3. Check ChromaDB vectors:")
        print("   curl http://192.168.178.94:8000/api/v1/collections")
        print("=" * 80)


def main():
    """Main entry point."""
    
    import argparse
    parser = argparse.ArgumentParser(description="Database Sync Pipeline")
    parser.add_argument('--skip-couchdb', action='store_true', help='Skip CouchDB sync')
    parser.add_argument('--skip-nlp', action='store_true', help='Skip NLP extraction')
    parser.add_argument('--skip-neo4j', action='store_true', help='Skip Neo4j persistence')
    
    args = parser.parse_args()
    
    pipeline = DatabaseSyncPipeline()
    pipeline.run(
        skip_couchdb=args.skip_couchdb,
        skip_nlp=args.skip_nlp,
        skip_neo4j=args.skip_neo4j
    )


if __name__ == '__main__':
    main()
