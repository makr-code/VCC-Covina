"""
Document Migration Job - Legal Graph Backfilling
================================================

Migrates existing documents (161k+) to the Legal Knowledge Graph by:
1. Fetching documents from PostgreSQL in batches
2. Extracting legal entities via LegalEntityExtractor
3. Persisting entities and relationships via EntityGraphWriter
4. Tracking progress in migration state file (resumable)

Architecture:
- Resumable: Saves progress after each batch
- Rate-limited: Configurable delay between batches
- Dry-run mode: Preview without writing to Neo4j
- Progress logging: Console + file output
- Error handling: Skip failed docs, continue processing

Usage:
    # Dry-run (preview only, no Neo4j writes)
    python -m ingestion.graph.document_migration --dry-run --limit 100

    # Full migration (all documents)
    python -m ingestion.graph.document_migration --batch-size 50 --delay 1.0

    # Resume from checkpoint
    python -m ingestion.graph.document_migration --resume

    # Reset migration state
    python -m ingestion.graph.document_migration --reset
"""

import argparse
import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ingestion.graph.entity_graph_writer import EntityGraphWriter
from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/document_migration.log"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationState:
    """Tracks migration progress for resumability."""

    last_processed_id: Optional[str] = None
    total_processed: int = 0
    total_entities_extracted: int = 0
    total_errors: int = 0
    started_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    batches_completed: int = 0

    @classmethod
    def load(cls, state_file: Path) -> "MigrationState":
        """Load state from JSON file."""
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        return cls(started_at=datetime.now().isoformat())

    def save(self, state_file: Path) -> None:
        """Save state to JSON file."""
        self.last_updated_at = datetime.now().isoformat()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)


class DocumentMigrationJob:
    """
    Batch migration job for backfilling Legal Knowledge Graph.
    """

    def __init__(
        self,
        batch_size: int = 100,
        delay: float = 0.5,
        dry_run: bool = False,
        state_file: Path = Path("data/migration_state.json"),
    ):
        """
        Initialize migration job.

        Args:
            batch_size: Number of documents per batch
            delay: Delay in seconds between batches (rate limiting)
            dry_run: If True, skip Neo4j writes (preview only)
            state_file: Path to migration state file
        """
        self.batch_size = batch_size
        self.delay = delay
        self.dry_run = dry_run
        self.state_file = state_file
        self.state = MigrationState.load(state_file)

        # Initialize UDS3 DatabaseManager (backend orchestrator)
        # Import from database.database_manager (correct path in Covina project)
        from database.database_manager import DatabaseManager
        
        backend_config = {
            'relational': {'enabled': True},  # PostgreSQL for documents
            'file': {'enabled': True},        # CouchDB for content (optional)
        }
        if not dry_run:
            backend_config['graph'] = {'enabled': True}  # Neo4j for graph writes
        
        logger.info(f"[INIT] Initializing UDS3 DatabaseManager (autostart=True)...")
        self.db_manager = DatabaseManager(backend_config, autostart=True)
        
        # Log which backends are available
        backends_status = []
        if hasattr(self.db_manager, 'relational_backend') and self.db_manager.relational_backend:
            backends_status.append("PostgreSQL")
        if hasattr(self.db_manager, 'file_backend') and self.db_manager.file_backend:
            backends_status.append("CouchDB")
        if hasattr(self.db_manager, 'graph_backend') and self.db_manager.graph_backend:
            backends_status.append("Neo4j")
        logger.info(f"[BACKENDS] Available: {', '.join(backends_status) if backends_status else 'None'}")

        # Initialize extractor and writer
        self.extractor = LegalEntityExtractor()
        self.writer = None if dry_run else EntityGraphWriter()

        logger.info(f"[INIT] Migration Job initialized")
        logger.info(f"[CONFIG] Batch size: {batch_size}, Delay: {delay}s, Dry-run: {dry_run}")

    def get_postgres_connection(self):
        """
        Get PostgreSQL connection via UDS3.

        Returns:
            Database connection object
        """
        # Access relational_backend attribute directly
        relational_backend = self.db_manager.relational_backend

        if not relational_backend:
            raise RuntimeError("PostgreSQL backend not available in UDS3")

        return relational_backend

    async def fetch_documents_batch(
        self, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Fetch a batch of documents from PostgreSQL.

        Args:
            limit: Maximum number of documents to fetch (None = all)

        Returns:
            List of document records (id, file_path, content, classification)
        """
        try:
            backend = self.get_postgres_connection()

            # Build query with optional LIMIT and resume support
            query = """
            SELECT id, file_path, classification, content_length, created_at
            FROM documents
            """

            # Resume from last processed ID
            params = {}
            if self.state.last_processed_id:
                query += " WHERE id > %(last_id)s"
                params["last_id"] = self.state.last_processed_id

            query += " ORDER BY id ASC"

            if limit:
                query += f" LIMIT {limit}"

            # Execute query (sync backend)
            def _execute():
                return backend.execute_query(query, params)

            result = await asyncio.to_thread(_execute)

            # Extract records from result
            if hasattr(result, "fetchall"):
                records = result.fetchall()
            elif isinstance(result, list):
                records = result
            else:
                records = []

            logger.info(f"[FETCH] Retrieved {len(records)} documents from PostgreSQL")
            return [dict(r) for r in records] if records else []

        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch documents: {e}")
            return []

    async def fetch_document_content(self, document_id: str) -> Optional[str]:
        """
        Fetch full document content from CouchDB.

        Args:
            document_id: Document ID

        Returns:
            Full document text content (or None if not found)
        """
        try:
            # Access file_backend attribute directly
            document_backend = self.db_manager.file_backend

            if not document_backend:
                logger.warning(f"[WARN] CouchDB backend not available, skipping content fetch")
                return None

            # Fetch document from CouchDB (sync backend)
            def _fetch():
                return document_backend.get_document(document_id)

            result = await asyncio.to_thread(_fetch)

            # Extract content field
            if isinstance(result, dict) and "content" in result:
                return result["content"]
            
            logger.warning(f"[WARN] No content found for {document_id}")
            return None

        except Exception as e:
            logger.warning(f"[WARN] Failed to fetch content for {document_id}: {e}")
            return None

    async def process_document(self, doc_record: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single document: extract entities and persist to graph.

        Args:
            doc_record: Document record from PostgreSQL

        Returns:
            Processing stats (entities_extracted, errors, skipped)
        """
        document_id = doc_record.get("id")
        file_path = doc_record.get("file_path", "unknown")

        stats = {
            "document_id": document_id,
            "entities_extracted": 0,
            "entities_persisted": 0,
            "errors": 0,
            "skipped": False,
        }

        try:
            # Fetch full content from CouchDB
            content = await self.fetch_document_content(document_id)

            if not content:
                logger.warning(f"[SKIP] No content for {document_id} ({file_path})")
                stats["skipped"] = True
                return stats

            # Extract legal entities
            entities = self.extractor.extract(content)
            stats["entities_extracted"] = len(entities)

            if len(entities) == 0:
                logger.debug(f"[SKIP] No entities in {document_id} ({file_path})")
                return stats

            # Persist to Neo4j (unless dry-run)
            if self.dry_run:
                logger.info(
                    f"[DRY-RUN] Would persist {len(entities)} entities for {document_id}"
                )
                stats["entities_persisted"] = len(entities)
            else:
                # Process each entity
                for entity in entities:
                    try:
                        if entity.kind == "norm":
                            norm_id = entity.value.lower().replace(" ", "_")
                            self.writer.upsert_legal_norm(
                                norm_id=norm_id,
                                norm_text=entity.value,
                                law_abbreviation=entity.meta.get("law"),
                                paragraph=entity.meta.get("paragraph"),
                            )
                            self.writer.link_cites_norm(
                                document_id=document_id,
                                norm_id=norm_id,
                                count=1,
                                context=entity.meta.get("context_window"),
                            )
                            stats["entities_persisted"] += 1

                        elif entity.kind == "aktenzeichen":
                            concept_id = f"az_{entity.value.lower().replace(' ', '_')}"
                            self.writer.upsert_legal_concept(
                                concept_id=concept_id,
                                name=f"Aktenzeichen: {entity.value}",
                                tier=1,
                                context_window=entity.meta.get("context_window"),
                            )
                            self.writer.link_mentions_concept(
                                document_id=document_id,
                                concept_id=concept_id,
                                count=1,
                            )
                            stats["entities_persisted"] += 1

                        elif entity.kind == "ecli":
                            concept_id = entity.value.lower()
                            self.writer.upsert_legal_concept(
                                concept_id=concept_id,
                                name=f"ECLI: {entity.value}",
                                tier=1,
                                context_window=entity.meta.get("context_window"),
                            )
                            self.writer.link_mentions_concept(
                                document_id=document_id,
                                concept_id=concept_id,
                                count=1,
                            )
                            stats["entities_persisted"] += 1

                    except Exception as e:
                        logger.error(
                            f"[ERROR] Failed to persist entity {entity.kind}={entity.value} for {document_id}: {e}"
                        )
                        stats["errors"] += 1

        except Exception as e:
            logger.error(f"[ERROR] Failed to process {document_id}: {e}")
            stats["errors"] += 1

        return stats

    async def run(self, limit: Optional[int] = None) -> dict[str, Any]:
        """
        Run migration job.

        Args:
            limit: Maximum number of documents to process (None = all)

        Returns:
            Migration summary stats
        """
        logger.info(f"[START] Migration job started (limit={limit or 'ALL'})")
        start_time = time.time()

        batch_num = self.state.batches_completed
        total_docs = 0
        total_entities = 0
        total_errors = 0

        while True:
            # Fetch next batch
            documents = await self.fetch_documents_batch(
                limit=min(self.batch_size, limit - total_docs) if limit else self.batch_size
            )

            if not documents:
                logger.info("[COMPLETE] No more documents to process")
                break

            # Process batch
            batch_num += 1
            logger.info(f"[BATCH {batch_num}] Processing {len(documents)} documents...")

            batch_entities = 0
            batch_errors = 0

            for doc in documents:
                stats = await self.process_document(doc)
                batch_entities += stats["entities_extracted"]
                batch_errors += stats["errors"]

                # Update state
                self.state.last_processed_id = stats["document_id"]
                self.state.total_processed += 1
                total_docs += 1

            # Update totals
            total_entities += batch_entities
            total_errors += batch_errors
            self.state.total_entities_extracted += batch_entities
            self.state.total_errors += batch_errors
            self.state.batches_completed = batch_num

            # Save progress
            self.state.save(self.state_file)

            logger.info(
                f"[BATCH {batch_num}] Complete: {len(documents)} docs, "
                f"{batch_entities} entities, {batch_errors} errors"
            )

            # Check limit
            if limit and total_docs >= limit:
                logger.info(f"[LIMIT] Reached limit of {limit} documents")
                break

            # Rate limiting
            if self.delay > 0:
                await asyncio.sleep(self.delay)

        # Final summary
        elapsed = time.time() - start_time
        summary = {
            "total_documents_processed": total_docs,
            "total_entities_extracted": total_entities,
            "total_errors": total_errors,
            "batches_completed": batch_num,
            "elapsed_seconds": round(elapsed, 2),
            "docs_per_second": round(total_docs / elapsed, 2) if elapsed > 0 else 0,
            "dry_run": self.dry_run,
        }

        logger.info(f"[SUMMARY] Migration complete: {summary}")
        return summary

    def reset(self) -> None:
        """Reset migration state (start from beginning)."""
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info(f"[RESET] Migration state cleared: {self.state_file}")
        else:
            logger.info(f"[RESET] No state file found: {self.state_file}")


async def main():
    """CLI entry point for migration job."""
    parser = argparse.ArgumentParser(description="Legal Graph Document Migration Job")
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Documents per batch (default: 100)"
    )
    parser.add_argument(
        "--delay", type=float, default=0.5, help="Delay between batches in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview mode (no Neo4j writes)"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max documents to process (default: all)"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from last checkpoint"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Reset migration state and exit"
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("data/migration_state.json"),
        help="Path to state file (default: data/migration_state.json)",
    )

    args = parser.parse_args()

    # Reset mode
    if args.reset:
        job = DocumentMigrationJob(state_file=args.state_file)
        job.reset()
        return

    # Run migration
    job = DocumentMigrationJob(
        batch_size=args.batch_size,
        delay=args.delay,
        dry_run=args.dry_run,
        state_file=args.state_file,
    )

    if args.resume:
        logger.info(f"[RESUME] Continuing from last checkpoint")
        logger.info(f"[RESUME] Last processed: {job.state.last_processed_id}")
        logger.info(f"[RESUME] Total processed so far: {job.state.total_processed}")

    summary = await job.run(limit=args.limit)

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    for key, value in summary.items():
        print(f"{key:30s}: {value}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
