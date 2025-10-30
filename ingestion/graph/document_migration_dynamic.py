"""
Dynamic Document Migration - Phase L5B
=======================================

Enhanced version of Phase L5A with:
1. YAML-based configuration (config/domain_inference_rules.yaml)
2. Self-learning patterns during ingestion
3. Auto-updating rules file
4. Statistics tracking

This replaces hard-coded keyword mappings with a dynamic, extensible system.

Usage:
    # Test with small sample
    python -m ingestion.graph.document_migration_dynamic --dry-run --limit 100
    
    # Production migration with learning enabled
    ENABLE_DOCUMENT_MIGRATION=true python -m ingestion.graph.document_migration_dynamic
    
    # Show learning statistics
    python -m ingestion.graph.document_migration_dynamic --stats
"""

import argparse
import csv
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ingestion.graph.domain_inference_engine import DomainInferenceEngine

# Feature Flag
ENABLE_MIGRATION = os.getenv("ENABLE_DOCUMENT_MIGRATION", "false").lower() == "true"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/document_migration_dynamic.log"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationState:
    """Persistent migration state for resumability."""
    last_processed_id: Optional[str] = None
    total_processed: int = 0
    total_linked: int = 0
    total_skipped_no_match: int = 0
    total_skipped_low_confidence: int = 0
    batches_completed: int = 0
    min_confidence: float = 0.3
    dry_run: bool = True


class DynamicDocumentMigration:
    """
    Dynamic document-to-domain migration using YAML-based inference engine.
    """
    
    def __init__(
        self,
        min_confidence: float = 0.3,
        batch_size: int = 1000,
        dry_run: bool = True,
        auto_save_every: int = 1000
    ):
        """
        Initialize migration job.
        
        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
            batch_size: Documents per batch for UNWIND operations
            dry_run: Preview mode (no writes to Neo4j)
            auto_save_every: Save rules every N documents
        """
        self.min_confidence = min_confidence
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.auto_save_every = auto_save_every
        
        # Initialize inference engine
        self.engine = DomainInferenceEngine()
        
        # State
        self.state = MigrationState(min_confidence=min_confidence, dry_run=dry_run)
        
        # Exports
        self.unmapped_file = Path("data/unmapped_dynamic.csv")
        self.low_confidence_file = Path("data/low_confidence_dynamic.csv")
        
        logger.info(f"[INIT] Dynamic Document Migration")
        logger.info(f"[INIT] Min Confidence: {min_confidence}")
        logger.info(f"[INIT] Batch Size: {batch_size}")
        logger.info(f"[INIT] Dry Run: {dry_run}")
        logger.info(f"[INIT] Auto-save every: {auto_save_every} docs")
    
    def run(self, limit: Optional[int] = None):
        """
        Run migration job.
        
        Args:
            limit: Limit number of documents (for testing)
        """
        from database.database_manager import DatabaseManager
        
        logger.info(f"[START] Starting dynamic document migration")
        
        # Initialize databases
        dm = DatabaseManager(
            {
                "relational": {"enabled": True},
                "graph": {"enabled": True}
            },
            autostart=True
        )
        
        rel_backend = dm.relational_backend
        graph_backend = dm.graph_backend
        
        # Fetch documents from PostgreSQL
        query = """
        SELECT document_id, file_path, classification, legal_terms_count
        FROM documents
        ORDER BY document_id
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"[FETCH] Retrieving documents from PostgreSQL...")
        documents = rel_backend.execute_query(query, fetch=True)
        logger.info(f"[FETCH] Retrieved {len(documents)} documents")
        
        # Process in batches
        batch_links = []
        unmapped_docs = []
        low_confidence_docs = []
        
        for i, doc in enumerate(documents, 1):
            doc_id = doc["document_id"]
            file_path = doc["file_path"]
            classification = doc.get("classification")
            legal_terms_count = doc.get("legal_terms_count", 0)
            
            # Infer domain
            domain_id, confidence = self.engine.infer(
                file_path=file_path,
                classification=classification,
                legal_terms_count=legal_terms_count
            )
            
            # Track state
            self.state.total_processed += 1
            self.state.last_processed_id = doc_id
            
            if not domain_id:
                # No match
                self.state.total_skipped_no_match += 1
                unmapped_docs.append({
                    "document_id": doc_id,
                    "file_path": file_path,
                    "classification": classification
                })
            elif confidence < self.min_confidence:
                # Low confidence
                self.state.total_skipped_low_confidence += 1
                low_confidence_docs.append({
                    "document_id": doc_id,
                    "file_path": file_path,
                    "domain": domain_id,
                    "confidence": confidence
                })
            else:
                # Success - add to batch
                self.state.total_linked += 1
                batch_links.append({
                    "doc_id": doc_id,
                    "domain_id": domain_id,
                    "confidence": confidence
                })
                
                # Learn pattern (for auto-enrichment)
                self.engine.learn_pattern(
                    file_path=file_path,
                    domain=domain_id,
                    confidence=confidence,
                    source="auto"
                )
            
            # Flush batch
            if len(batch_links) >= self.batch_size:
                self._flush_batch(batch_links, graph_backend)
                batch_links = []
                self.state.batches_completed += 1
            
            # Auto-save rules
            if i % self.auto_save_every == 0:
                logger.info(f"[AUTO-SAVE] Saving learned patterns (after {i} docs)")
                self.engine.save_rules()
            
            # Progress log
            if i % 100 == 0:
                logger.info(
                    f"[PROGRESS] {i}/{len(documents)} docs | "
                    f"Linked: {self.state.total_linked} | "
                    f"Unmapped: {self.state.total_skipped_no_match}"
                )
        
        # Flush remaining batch
        if batch_links:
            self._flush_batch(batch_links, graph_backend)
            self.state.batches_completed += 1
        
        # Final save of rules
        logger.info(f"[FINAL-SAVE] Saving all learned patterns")
        self.engine.save_rules()
        
        # Export unmapped/low-confidence
        self._export_unmapped(unmapped_docs)
        self._export_low_confidence(low_confidence_docs)
        
        # Summary
        self._print_summary()
    
    def _flush_batch(self, links: List[Dict], graph_backend):
        """Write batch of relationships to Neo4j."""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would create {len(links)} BELONGS_TO relationships")
            return
        
        query = """
        UNWIND $links AS link
        MATCH (d:Document {id: link.doc_id})
        MATCH (domain:LegalDomain {id: link.domain_id})
        MERGE (d)-[r:BELONGS_TO]->(domain)
        SET r.confidence = link.confidence,
            r.method = 'dynamic_rules',
            r.created_at = datetime()
        RETURN COUNT(r) AS created
        """
        
        try:
            result = graph_backend.execute_query(query, {"links": links})
            logger.info(f"[BATCH] Created {len(links)} BELONGS_TO relationships")
        except Exception as e:
            logger.error(f"[ERROR] Batch write failed: {e}")
    
    def _export_unmapped(self, docs: List[Dict]):
        """Export unmapped documents to CSV."""
        if not docs:
            logger.info(f"[EXPORT] No unmapped documents")
            return
        
        self.unmapped_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.unmapped_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["document_id", "file_path", "classification"])
            writer.writeheader()
            writer.writerows(docs)
        
        logger.info(f"[EXPORT] Unmapped documents saved to {self.unmapped_file}")
    
    def _export_low_confidence(self, docs: List[Dict]):
        """Export low-confidence matches to CSV."""
        if not docs:
            logger.info(f"[EXPORT] No low-confidence documents")
            return
        
        self.low_confidence_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.low_confidence_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["document_id", "file_path", "domain", "confidence"])
            writer.writeheader()
            writer.writerows(docs)
        
        logger.info(f"[EXPORT] Low-confidence documents saved to {self.low_confidence_file}")
    
    def _print_summary(self):
        """Print migration summary."""
        coverage = (self.state.total_linked / self.state.total_processed * 100) if self.state.total_processed > 0 else 0
        
        logger.info(f"")
        logger.info(f"{'='*70}")
        logger.info(f"MIGRATION SUMMARY (Dynamic Rules)")
        logger.info(f"{'='*70}")
        logger.info(f"Total Processed:        {self.state.total_processed:,}")
        logger.info(f"Total Linked:           {self.state.total_linked:,} ({coverage:.2f}%)")
        logger.info(f"Unmapped (no match):    {self.state.total_skipped_no_match:,}")
        logger.info(f"Low Confidence (<{self.min_confidence}): {self.state.total_skipped_low_confidence:,}")
        logger.info(f"Batches Completed:      {self.state.batches_completed}")
        logger.info(f"Dry Run:                {self.dry_run}")
        logger.info(f"")
        
        # Inference engine stats
        stats = self.engine.get_stats()
        logger.info(f"INFERENCE ENGINE STATS:")
        logger.info(f"Total Inferences:       {stats['total']:,}")
        logger.info(f"Successful:             {stats['success']:,}")
        logger.info(f"Failed:                 {stats['failed']:,}")
        logger.info(f"Learned Patterns:       {stats['learned_patterns_count']:,}")
        logger.info(f"")
        logger.info(f"Top Domains:")
        for domain, count in sorted(stats['by_domain'].items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {domain:<25} {count:>6,} docs")
        logger.info(f"{'='*70}")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamic Document Migration (Phase L5B)")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode (no Neo4j writes)")
    parser.add_argument("--limit", type=int, help="Limit number of documents")
    parser.add_argument("--min-confidence", type=float, default=0.3, help="Minimum confidence threshold")
    parser.add_argument("--batch-size", type=int, default=1000, help="Documents per batch")
    parser.add_argument("--auto-save-every", type=int, default=1000, help="Auto-save rules every N docs")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    
    args = parser.parse_args()
    
    if args.stats:
        # Show stats from existing engine
        engine = DomainInferenceEngine()
        import yaml
        print(yaml.dump(engine.get_stats(), default_flow_style=False))
    else:
        # Run migration
        job = DynamicDocumentMigration(
            min_confidence=args.min_confidence,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            auto_save_every=args.auto_save_every
        )
        
        job.run(limit=args.limit)
