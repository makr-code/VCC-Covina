"""
Rule-Based Document Migration - Phase L5A
==========================================

Links documents to Legal Domains using rule-based inference from metadata.

Approach:
1. Extract domain hints from file_path (keywords like "baurecht", "arbeitsrecht")
2. Analyze classification + legal_terms_count patterns
3. Map to LegalDomain with confidence score
4. Create BELONGS_TO relationships in batches (UNWIND)

This approach does NOT require:
- NLP extraction
- Full document text content
- LLM API calls

Expected Coverage: 50-70% of documents (80-100k out of 161k)

Usage:
    # Dry-run (preview only)
    python -m ingestion.graph.document_migration_rulebased --dry-run --limit 100

    # Full migration
    ENABLE_DOCUMENT_MIGRATION=true python -m ingestion.graph.document_migration_rulebased

    # Resume from checkpoint
    python -m ingestion.graph.document_migration_rulebased --resume
"""

import argparse
import csv
import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Feature Flag
ENABLE_MIGRATION = os.getenv("ENABLE_DOCUMENT_MIGRATION", "false").lower() == "true"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/document_migration_rulebased.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# Domain Keyword Mapping
# ============================================================================


class DomainInference:
    """
    Infers legal domain from document metadata using rule-based heuristics.
    """

    # Keyword → Domain mapping (path-based detection)
    DOMAIN_KEYWORDS = {
        # Tier 1
        "oeffentlich": "oeffentliches_recht",
        "öffentlich": "oeffentliches_recht",
        "public": "oeffentliches_recht",
        "privat": "privatrecht",
        "private": "privatrecht",
        "civil": "privatrecht",
        
        # Tier 2 - Öffentliches Recht
        "bau": "baurecht",
        "baurecht": "baurecht",
        "construction": "baurecht",
        "wasser": "wasserrecht",
        "wasserrecht": "wasserrecht",
        "water": "wasserrecht",
        "immission": "immissionsschutzrecht",
        "emission": "immissionsschutzrecht",
        "umwelt": "immissionsschutzrecht",
        "environment": "immissionsschutzrecht",
        "bildung": "bildungsrecht",
        "bildungsrecht": "bildungsrecht",
        "schul": "bildungsrecht",
        "education": "bildungsrecht",
        "verwaltung": "verwaltungsrecht",
        "verwaltungsrecht": "verwaltungsrecht",
        "administrative": "verwaltungsrecht",
        "verfassung": "verfassungsrecht",
        "verfassungsrecht": "verfassungsrecht",
        "constitutional": "verfassungsrecht",
        "grundgesetz": "verfassungsrecht",
        "gg": "verfassungsrecht",
        
        # Tier 2 - Privatrecht
        "arbeit": "arbeitsrecht",
        "arbeitsrecht": "arbeitsrecht",
        "labor": "arbeitsrecht",
        "employment": "arbeitsrecht",
        "gesellschaft": "gesellschaftsrecht",
        "gesellschaftsrecht": "gesellschaftsrecht",
        "corporate": "gesellschaftsrecht",
        "company": "gesellschaftsrecht",
        "handel": "handelsrecht",
        "handelsrecht": "handelsrecht",
        "commercial": "handelsrecht",
        "trade": "handelsrecht",
        "zivil": "zivilrecht",
        "zivilrecht": "zivilrecht",
        "buergerlich": "zivilrecht",
        "bgb": "zivilrecht",
        
        # Tier 2 - Other
        "straf": "strafrecht",
        "strafrecht": "strafrecht",
        "criminal": "strafrecht",
        "stgb": "strafrecht",
        "voelker": "voelkerrecht",
        "völker": "voelkerrecht",
        "international": "voelkerrecht",
        
        # Tier 3
        "vertrag": "vertragsrecht",
        "vertragsrecht": "vertragsrecht",
        "contract": "vertragsrecht",
        "sachen": "sachenrecht",
        "sachenrecht": "sachenrecht",
        "property": "sachenrecht",
        "familie": "familienrecht",
        "familienrecht": "familienrecht",
        "family": "familienrecht",
        "ehe": "familienrecht",
        "scheidung": "familienrecht",
        "erb": "erbrecht",
        "erbrecht": "erbrecht",
        "inheritance": "erbrecht",
        "testament": "erbrecht",
        "miet": "mietrecht",
        "miete": "mietrecht",
        "tenant": "mietrecht",
        "landlord": "mietrecht",
        "steuer": "steuerrecht",
        "tax": "steuerrecht",
        "sozial": "sozialrecht",
        "social": "sozialrecht",
        "insolvenz": "insolvenzrecht",
        "bankruptcy": "insolvenzrecht",
        
        # Court Names → Domain Mapping (NEW - Phase L5B Enhancement)
        # High-confidence court-to-domain mappings
        "verwaltungsgericht": "verwaltungsrecht",
        "vg ": "verwaltungsrecht",  # Space after VG to avoid false matches
        "vgh ": "verwaltungsrecht",  # Verwaltungsgerichtshof
        "verwaltungsgerichtshof": "verwaltungsrecht",
        "bundesverwaltungsgericht": "verwaltungsrecht",
        "bverwg": "verwaltungsrecht",
        
        "arbeitsgericht": "arbeitsrecht",
        "lag ": "arbeitsrecht",  # Landesarbeitsgericht
        "landesarbeitsgericht": "arbeitsrecht",
        "bundesarbeitsgericht": "arbeitsrecht",
        "bag ": "arbeitsrecht",
        
        "sozialgericht": "sozialrecht",
        "sg ": "sozialrecht",  # Space after SG
        "landessozialgericht": "sozialrecht",
        "lsg ": "sozialrecht",
        "bundessozialgericht": "sozialrecht",
        "bsg ": "sozialrecht",
        
        "bundesverfassungsgericht": "verfassungsrecht",
        "bverfg": "verfassungsrecht",
        "verfassungsgericht": "verfassungsrecht",
        
        "finanzgericht": "steuerrecht",
        "fg ": "steuerrecht",
        "bundesfinanzhof": "steuerrecht",
        "bfh ": "steuerrecht",
        
        # Medium-confidence courts (multiple domains possible, use most common)
        "amtsgericht": "zivilrecht",  # AG handles civil + criminal, but mostly civil
        "ag ": "zivilrecht",
        "landgericht": "zivilrecht",  # LG handles civil + criminal, but mostly civil
        "lg ": "zivilrecht",
        "oberlandesgericht": "zivilrecht",  # OLG handles civil + criminal
        "olg ": "zivilrecht",
    }
    
    # Classification → Domain hints (weak signals)
    CLASSIFICATION_HINTS = {
        "RECHTSPRECHUNG": None,  # No direct mapping (could be any domain)
        "VERTRAG": "vertragsrecht",  # Contracts → Vertragsrecht (default)
        "GESETZ": None,  # No direct mapping (could be any domain)
        "DOCUMENT": None,  # Generic, no hint
    }
    
    # Statutory references → Domain mapping
    STATUTORY_REFS = {
        "bgb": "zivilrecht",
        "stgb": "strafrecht",
        "gg": "verfassungsrecht",
        "baug": "baurecht",
        "whg": "wasserrecht",
        "bundes-immissionsschutzgesetz": "immissionsschutzrecht",
        "bimschg": "immissionsschutzrecht",
        "hgb": "handelsrecht",
        "aktg": "gesellschaftsrecht",
        "gmbhg": "gesellschaftsrecht",
    }

    @classmethod
    def infer_from_file_path(cls, file_path: str) -> Optional[str]:
        """
        Infer domain from file path keywords.
        
        Args:
            file_path: Document file path
        
        Returns:
            Domain ID or None if no match
        """
        if not file_path:
            return None
        
        # Normalize: lowercase
        normalized = file_path.lower()
        
        # Check all keywords
        for keyword, domain_id in cls.DOMAIN_KEYWORDS.items():
            if keyword in normalized:
                return domain_id
        
        return None
    
    @classmethod
    def infer_from_classification(cls, classification: str) -> Optional[str]:
        """
        Infer domain from classification (weak hint).
        
        Args:
            classification: Document type (RECHTSPRECHUNG, VERTRAG, etc.)
        
        Returns:
            Domain ID or None
        """
        if not classification:
            return None
        
        return cls.CLASSIFICATION_HINTS.get(classification.upper())
    
    @classmethod
    def infer_from_metadata(
        cls,
        file_path: str,
        classification: str,
        legal_terms_count: int = 0
    ) -> Tuple[Optional[str], float]:
        """
        Infer domain from all available metadata.
        
        Args:
            file_path: Document file path
            classification: Document type
            legal_terms_count: Number of legal terms (optional)
        
        Returns:
            Tuple of (domain_id, confidence_score)
            confidence_score: 0.0-1.0 (0.0 = no match, 1.0 = high confidence)
        """
        # Method 1: File path (high confidence)
        path_domain = cls.infer_from_file_path(file_path)
        if path_domain:
            confidence = 0.8  # High confidence
            
            # Boost confidence if legal_terms_count is high
            if legal_terms_count > 50:
                confidence = min(0.95, confidence + 0.15)
            
            return (path_domain, confidence)
        
        # Method 2: Classification (low confidence)
        classification_domain = cls.infer_from_classification(classification)
        if classification_domain:
            confidence = 0.3  # Low confidence (weak signal)
            
            # Boost if legal_terms_count is very high
            if legal_terms_count > 100:
                confidence = min(0.6, confidence + 0.3)
            
            return (classification_domain, confidence)
        
        # No match
        return (None, 0.0)


# ============================================================================
# Migration State (Checkpointing)
# ============================================================================


@dataclass
class MigrationState:
    """Tracks migration progress for resumability."""

    last_processed_id: Optional[str] = None
    total_processed: int = 0
    total_linked: int = 0
    total_skipped_no_match: int = 0
    total_skipped_low_confidence: int = 0
    started_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    batches_completed: int = 0
    min_confidence: float = 0.5  # Minimum confidence threshold

    @classmethod
    def load(cls, state_file: Path) -> "MigrationState":
        """Load state from JSON file."""
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                return cls(started_at=datetime.now().isoformat())
        return cls(started_at=datetime.now().isoformat())

    def save(self, state_file: Path) -> None:
        """Save state to JSON file."""
        self.last_updated_at = datetime.now().isoformat()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)


# ============================================================================
# Rule-Based Migrator
# ============================================================================


class RuleBasedMigrator:
    """
    Rule-based document migration using metadata inference.
    """

    def __init__(
        self,
        batch_size: int = 1000,
        min_confidence: float = 0.5,
        dry_run: bool = False,
        resume: bool = False,
        state_file: Path = Path("data/migration_rulebased_state.json"),
        unmapped_file: Path = Path("data/unmapped_rulebased.csv"),
        low_confidence_file: Path = Path("data/low_confidence_rulebased.csv"),
    ):
        """
        Args:
            batch_size: Documents per batch (default: 1000)
            min_confidence: Minimum confidence for linking (default: 0.5)
            dry_run: If True, no Neo4j writes (default: False)
            resume: If True, resume from checkpoint (default: False)
            state_file: Path to checkpoint file
            unmapped_file: CSV file for unmapped documents
            low_confidence_file: CSV file for low-confidence matches
        """
        self.batch_size = batch_size
        self.min_confidence = min_confidence
        self.dry_run = dry_run
        self.resume = resume
        self.state_file = state_file
        self.unmapped_file = unmapped_file
        self.low_confidence_file = low_confidence_file

        # Load state
        self.state = MigrationState.load(state_file) if resume else MigrationState(
            started_at=datetime.now().isoformat(),
            min_confidence=min_confidence
        )

        # Initialize UDS3
        from database.database_manager import DatabaseManager

        backend_config = {"relational": {"enabled": True}}
        if not dry_run:
            backend_config["graph"] = {"enabled": True}

        logger.info("[INIT] Initializing UDS3 DatabaseManager...")
        self.db_manager = DatabaseManager(backend_config, autostart=True)

        # Log backends
        backends = []
        if self.db_manager.relational_backend:
            backends.append("PostgreSQL")
        if hasattr(self.db_manager, "graph_backend") and self.db_manager.graph_backend:
            backends.append("Neo4j")
        logger.info(f"[BACKENDS] Available: {', '.join(backends)}")

        # Tracking
        self.unmapped = []  # (doc_id, file_path, classification)
        self.low_confidence = []  # (doc_id, domain_id, confidence, file_path)

    def query_documents_to_migrate(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query documents for migration.

        Returns:
            List of dicts: {"document_id": str, "file_path": str, "classification": str, "legal_terms_count": int}
        """
        backend = self.db_manager.relational_backend
        if not backend:
            raise RuntimeError("PostgreSQL backend not available")

        # Build query
        query = """
        SELECT document_id, file_path, classification, legal_terms_count
        FROM documents
        """

        # Resume from checkpoint
        if self.resume and self.state.last_processed_id:
            query += f" WHERE document_id > '{self.state.last_processed_id}'"

        query += " ORDER BY document_id ASC"

        if limit:
            query += f" LIMIT {limit}"

        # Execute
        result = backend.execute_query(query, fetch=True)

        if not result:
            return []

        logger.info(f"[FETCH] Retrieved {len(result)} documents from PostgreSQL")
        return result

    def create_relationships_batch(self, links: List[Dict[str, Any]]) -> None:
        """
        Create BELONGS_TO relationships in batch (UNWIND).

        Args:
            links: List of {"doc_id": str, "domain_id": str, "confidence": float}
        """
        if not links:
            return

        backend = self.db_manager.graph_backend
        if not backend:
            raise RuntimeError("Neo4j backend not available")

        # Batch UNWIND query
        query = """
        UNWIND $links AS link
        MATCH (d:Document {id: link.doc_id})
        MATCH (domain:LegalDomain {id: link.domain_id})
        MERGE (d)-[r:BELONGS_TO]->(domain)
        SET r.confidence = link.confidence,
            r.method = 'rule_based',
            r.created_at = datetime()
        """

        # Execute
        backend.execute_query(query, {"links": links})

    def process_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Process one batch of documents.

        Args:
            batch: List of document records

        Returns:
            Stats: {"linked": int, "skipped_no_match": int, "skipped_low_confidence": int}
        """
        stats = {"linked": 0, "skipped_no_match": 0, "skipped_low_confidence": 0}

        # Infer domains
        links = []
        for doc in batch:
            doc_id = doc["document_id"]
            file_path = doc.get("file_path", "")
            classification = doc.get("classification", "")
            legal_terms_count = doc.get("legal_terms_count", 0)

            # Infer domain
            domain_id, confidence = DomainInference.infer_from_metadata(
                file_path, classification, legal_terms_count
            )

            if not domain_id:
                stats["skipped_no_match"] += 1
                self.unmapped.append((doc_id, file_path, classification))
                continue

            if confidence < self.min_confidence:
                stats["skipped_low_confidence"] += 1
                self.low_confidence.append((doc_id, domain_id, confidence, file_path))
                continue

            links.append({"doc_id": doc_id, "domain_id": domain_id, "confidence": confidence})

        # Create relationships
        if links:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would link {len(links)} documents (confidence >= {self.min_confidence})")
            else:
                self.create_relationships_batch(links)
            stats["linked"] = len(links)

        return stats

    def export_unmapped(self) -> None:
        """Export unmapped documents to CSV."""
        if not self.unmapped:
            return

        self.unmapped_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.unmapped_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["document_id", "file_path", "classification"])
            writer.writerows(self.unmapped)

        logger.info(f"[EXPORT] Unmapped documents saved to {self.unmapped_file}")

    def export_low_confidence(self) -> None:
        """Export low-confidence matches to CSV."""
        if not self.low_confidence:
            return

        self.low_confidence_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.low_confidence_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["document_id", "inferred_domain", "confidence", "file_path"])
            writer.writerows(self.low_confidence)

        logger.info(f"[EXPORT] Low-confidence matches saved to {self.low_confidence_file}")

    def run(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Run migration.

        Args:
            limit: Max documents to process (None = all)

        Returns:
            Summary stats
        """
        if not ENABLE_MIGRATION and not self.dry_run:
            logger.warning("[MIGRATION] Disabled (ENABLE_DOCUMENT_MIGRATION=false)")
            logger.warning("[MIGRATION] Use --dry-run to test or set ENABLE_DOCUMENT_MIGRATION=true")
            return {"status": "disabled"}

        logger.info(f"[START] Rule-Based Document Migration (min_confidence={self.min_confidence})")

        # Query documents
        documents = self.query_documents_to_migrate(limit)

        if not documents:
            logger.info("[COMPLETE] No documents to migrate")
            return {"total_processed": 0}

        # Process in batches
        total_docs = len(documents)
        batch_num = self.state.batches_completed

        for i in range(0, total_docs, self.batch_size):
            batch = documents[i : i + self.batch_size]
            batch_num += 1

            logger.info(f"[BATCH {batch_num}] Processing {len(batch)} documents...")

            # Process batch
            stats = self.process_batch(batch)

            # Update state
            self.state.total_processed += len(batch)
            self.state.total_linked += stats["linked"]
            self.state.total_skipped_no_match += stats["skipped_no_match"]
            self.state.total_skipped_low_confidence += stats["skipped_low_confidence"]
            self.state.last_processed_id = batch[-1]["document_id"]
            self.state.batches_completed = batch_num

            # Save checkpoint
            if not self.dry_run:
                self.state.save(self.state_file)

            logger.info(
                f"[BATCH {batch_num}] Complete: {stats['linked']} linked, "
                f"{stats['skipped_no_match']} no match, "
                f"{stats['skipped_low_confidence']} low confidence"
            )

        # Export CSVs
        if self.unmapped:
            self.export_unmapped()
        if self.low_confidence:
            self.export_low_confidence()

        # Summary
        coverage_pct = (self.state.total_linked / self.state.total_processed * 100) if self.state.total_processed > 0 else 0
        
        summary = {
            "total_processed": self.state.total_processed,
            "total_linked": self.state.total_linked,
            "total_skipped_no_match": self.state.total_skipped_no_match,
            "total_skipped_low_confidence": self.state.total_skipped_low_confidence,
            "coverage_percent": round(coverage_pct, 2),
            "batches_completed": batch_num,
            "min_confidence": self.min_confidence,
            "dry_run": self.dry_run,
        }

        logger.info(f"[SUMMARY] Migration complete: {summary}")
        return summary


# ============================================================================
# CLI Entry Point
# ============================================================================


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Rule-Based Document Migration (Phase L5A)")
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Documents per batch (default: 1000)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum confidence for linking (default: 0.5, range: 0.0-1.0)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview mode (no Neo4j writes)"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max documents to process (default: all)"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from checkpoint"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Rule-Based Document Migration - Phase L5A")
    print("=" * 70)
    print()

    if args.dry_run:
        print("Mode: DRY-RUN (no writes)")
    else:
        if not ENABLE_MIGRATION:
            print("ERROR: Migration disabled (ENABLE_DOCUMENT_MIGRATION=false)")
            print("   Set ENABLE_DOCUMENT_MIGRATION=true to enable")
            print("   Or use --dry-run to test without writing")
            return 1
        print("Mode: LIVE (will write to Neo4j)")

    print(f"Batch Size: {args.batch_size}")
    print(f"Min Confidence: {args.min_confidence}")
    print(f"Resume: {args.resume}")
    print(f"Limit: {args.limit or 'ALL'}")
    print()

    try:
        # Run migration
        migrator = RuleBasedMigrator(
            batch_size=args.batch_size,
            min_confidence=args.min_confidence,
            dry_run=args.dry_run,
            resume=args.resume,
        )

        summary = migrator.run(limit=args.limit)

        # Print summary
        print()
        print("=" * 70)
        print("Migration Summary:")
        print("-" * 70)
        for key, value in summary.items():
            print(f"  {key:30s}: {value}")
        print("=" * 70)

        if summary.get("total_skipped_no_match", 0) > 0:
            print(f"\nUnmapped documents saved to: data/unmapped_rulebased.csv")
        
        if summary.get("total_skipped_low_confidence", 0) > 0:
            print(f"Low-confidence matches saved to: data/low_confidence_rulebased.csv")

        if args.dry_run:
            print("\nDRY-RUN complete - no changes made")
        else:
            print("\nMigration complete!")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
