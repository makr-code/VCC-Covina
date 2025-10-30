"""
Simple Document Migration - Legal Knowledge Graph Phase L5
===========================================================

Links existing documents to Legal Domains via classification field.

Approach:
- Query documents without BELONGS_TO relationship
- Map document.classification to LegalDomain.id
- Create BELONGS_TO relationships in batches (UNWIND)
- Save checkpoint for resumability

This is SIMPLER than document_migration.py:
- NO NLP extraction (no LegalEntityExtractor)
- NO entity persistence (no EntityGraphWriter)
- ONLY classification → LegalDomain mapping

Usage:
    # Dry-run (preview only)
    python -m ingestion.graph.document_migration_simple --dry-run --limit 100

    # Full migration
    ENABLE_DOCUMENT_MIGRATION=true python -m ingestion.graph.document_migration_simple

    # Resume from checkpoint
    python -m ingestion.graph.document_migration_simple --resume
"""

import argparse
import csv
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Feature Flag
ENABLE_MIGRATION = os.getenv("ENABLE_DOCUMENT_MIGRATION", "false").lower() == "true"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/document_migration_simple.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# Classification Mapper
# ============================================================================


class ClassificationMapper:
    """
    Maps document classification strings to LegalDomain IDs.

    Handles variations and normalizations:
    - "Baurecht" → "baurecht"
    - "Bau" → "baurecht"
    - "Immissionsschutz" → "immissionsschutzrecht"
    """

    # Static mapping (can be extended or loaded from YAML)
    MAPPINGS = {
        # Tier 1 (exact)
        "oeffentliches_recht": "oeffentliches_recht",
        "privatrecht": "privatrecht",
        # Tier 2 (exact)
        "baurecht": "baurecht",
        "wasserrecht": "wasserrecht",
        "immissionsschutzrecht": "immissionsschutzrecht",
        "bildungsrecht": "bildungsrecht",
        "arbeitsrecht": "arbeitsrecht",
        "gesellschaftsrecht": "gesellschaftsrecht",
        "handelsrecht": "handelsrecht",
        "strafrecht": "strafrecht",
        "verfassungsrecht": "verfassungsrecht",
        "verwaltungsrecht": "verwaltungsrecht",
        "voelkerrecht": "voelkerrecht",
        "zivilrecht": "zivilrecht",
        # Tier 3 (exact)
        "vertragsrecht": "vertragsrecht",
        "sachenrecht": "sachenrecht",
        "familienrecht": "familienrecht",
        "erbrecht": "erbrecht",
        # Variations (shortcuts)
        "bau": "baurecht",
        "wasser": "wasserrecht",
        "immissionsschutz": "immissionsschutzrecht",
        "bildung": "bildungsrecht",
        "arbeit": "arbeitsrecht",
        "gesellschaft": "gesellschaftsrecht",
        "handel": "handelsrecht",
        "straf": "strafrecht",
        "verfassung": "verfassungsrecht",
        "verwaltung": "verwaltungsrecht",
        "voelker": "voelkerrecht",
        "zivil": "zivilrecht",
        "vertrag": "vertragsrecht",
        "sachen": "sachenrecht",
        "familie": "familienrecht",
        "erb": "erbrecht",
        # Common German variations
        "öffentliches recht": "oeffentliches_recht",
        "öffentlich": "oeffentliches_recht",
        "privat": "privatrecht",
        "völkerrecht": "voelkerrecht",
    }

    @classmethod
    def map(cls, classification: str) -> Optional[str]:
        """
        Map classification string to LegalDomain ID.

        Args:
            classification: Document classification (e.g., "Baurecht", "Immissionsschutz")

        Returns:
            LegalDomain ID or None if no mapping found
        """
        if not classification:
            return None

        # Normalize: lowercase, strip whitespace
        normalized = classification.lower().strip()

        # Exact match
        if normalized in cls.MAPPINGS:
            return cls.MAPPINGS[normalized]

        # Partial match (contains)
        for key, value in cls.MAPPINGS.items():
            if key in normalized:
                return value

        # No match
        return None


# ============================================================================
# Migration State (Checkpointing)
# ============================================================================


@dataclass
class MigrationState:
    """Tracks migration progress for resumability."""

    last_processed_id: Optional[int] = None
    total_processed: int = 0
    total_linked: int = 0
    total_skipped: int = 0
    started_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    batches_completed: int = 0

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
# Document Migrator (Simple)
# ============================================================================


class SimpleMigrator:
    """
    Simple migrator: Links documents to Legal Domains via classification.

    Workflow:
    1. Query documents without BELONGS_TO relationship
    2. Map classification → LegalDomain
    3. Create relationships in batches (UNWIND)
    4. Save checkpoint after each batch
    """

    def __init__(
        self,
        batch_size: int = 1000,
        dry_run: bool = False,
        resume: bool = False,
        state_file: Path = Path("data/migration_simple_state.json"),
        unmapped_file: Path = Path("data/unmapped_classifications.csv"),
    ):
        """
        Args:
            batch_size: Documents per batch (default: 1000)
            dry_run: If True, no Neo4j writes (default: False)
            resume: If True, resume from checkpoint (default: False)
            state_file: Path to checkpoint file
            unmapped_file: CSV file for unmapped classifications
        """
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.resume = resume
        self.state_file = state_file
        self.unmapped_file = unmapped_file

        # Load state
        self.state = MigrationState.load(state_file) if resume else MigrationState(started_at=datetime.now().isoformat())

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

        # Unmapped classifications tracker
        self.unmapped = set()

    def query_documents_to_migrate(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query documents without BELONGS_TO relationship.

        Returns:
            List of dicts: {"document_id": int, "classification": str}
        """
        # Get PostgreSQL backend
        backend = self.db_manager.relational_backend
        if not backend:
            raise RuntimeError("PostgreSQL backend not available")

        # Build query
        query = """
        SELECT document_id, classification
        FROM documents
        WHERE classification IS NOT NULL
        """

        # Resume from checkpoint
        if self.resume and self.state.last_processed_id:
            query += f" AND document_id > {self.state.last_processed_id}"

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
            links: List of {"doc_id": int, "domain_id": str}
        """
        if not links:
            return

        # Get Neo4j backend
        backend = self.db_manager.graph_backend
        if not backend:
            raise RuntimeError("Neo4j backend not available")

        # Batch UNWIND query
        # Note: PostgreSQL uses 'document_id', Neo4j uses 'id' property
        query = """
        UNWIND $links AS link
        MATCH (d:Document {id: link.doc_id})
        MATCH (domain:LegalDomain {id: link.domain_id})
        MERGE (d)-[:BELONGS_TO]->(domain)
        """

        # Execute
        backend.execute_query(query, {"links": links})

    def process_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Process one batch of documents.

        Args:
            batch: List of {"document_id": int, "classification": str}

        Returns:
            Stats: {"linked": int, "skipped": int}
        """
        stats = {"linked": 0, "skipped": 0}

        # Map classifications to domains
        links = []
        for doc in batch:
            doc_id = doc["document_id"]
            classification = doc.get("classification")

            if not classification:
                stats["skipped"] += 1
                continue

            domain_id = ClassificationMapper.map(classification)

            if not domain_id:
                stats["skipped"] += 1
                self.unmapped.add(classification)
                continue

            links.append({"doc_id": doc_id, "domain_id": domain_id})

        # Create relationships
        if links:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would link {len(links)} documents")
            else:
                self.create_relationships_batch(links)
            stats["linked"] = len(links)

        return stats

    def export_unmapped_classifications(self) -> None:
        """Export unmapped classifications to CSV."""
        if not self.unmapped:
            return

        self.unmapped_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.unmapped_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["classification", "count"])
            for classification in sorted(self.unmapped):
                writer.writerow([classification, 1])  # TODO: Track counts

        logger.info(f"[EXPORT] Unmapped classifications saved to {self.unmapped_file}")

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

        logger.info("[START] Simple Document Migration to Legal Graph")

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
            self.state.total_skipped += stats["skipped"]
            self.state.last_processed_id = batch[-1]["document_id"]
            self.state.batches_completed = batch_num

            # Save checkpoint
            if not self.dry_run:
                self.state.save(self.state_file)

            logger.info(
                f"[BATCH {batch_num}] Complete: {stats['linked']} linked, {stats['skipped']} skipped"
            )

        # Export unmapped
        if self.unmapped:
            self.export_unmapped_classifications()

        # Summary
        summary = {
            "total_processed": self.state.total_processed,
            "total_linked": self.state.total_linked,
            "total_skipped": self.state.total_skipped,
            "batches_completed": batch_num,
            "unmapped_classifications": len(self.unmapped),
            "dry_run": self.dry_run,
        }

        logger.info(f"[SUMMARY] Migration complete: {summary}")
        return summary


# ============================================================================
# CLI Entry Point
# ============================================================================


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Simple Document Migration to Legal Graph")
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Documents per batch (default: 1000)"
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
    print("Simple Document Migration - Legal Knowledge Graph Phase L5")
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
    print(f"Resume: {args.resume}")
    print(f"Limit: {args.limit or 'ALL'}")
    print()

    try:
        # Run migration
        migrator = SimpleMigrator(
            batch_size=args.batch_size,
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

        if summary.get("unmapped_classifications", 0) > 0:
            print(f"\nUnmapped classifications saved to: data/unmapped_classifications.csv")

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
