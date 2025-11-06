"""
CLI: Document Migration & Backfill Runner

Beispiel:
  # Dry-Run der ersten 100 Dokumente
  python scripts/migrate_documents_to_legal_graph.py --dry-run --limit 100

  # Vollständige Migration mit Batches und Delay
  python scripts/migrate_documents_to_legal_graph.py --batch-size 500 --delay 0.2

  # Resume anhand von data/migration_state.json
  python scripts/migrate_documents_to_legal_graph.py --resume

  # State zurücksetzen
  python scripts/migrate_documents_to_legal_graph.py --reset
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ingestion.graph.document_migration import DocumentMigrationJob, MigrationState


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run document migration backfill")
    p.add_argument("--dry-run", action="store_true", help="Keine Graph-Writes ausführen")
    p.add_argument("--batch-size", type=int, default=500, help="Dokumente pro Batch")
    p.add_argument("--delay", type=float, default=0.2, help="Delay zwischen Batches (Sekunden)")
    p.add_argument("--limit", type=int, default=None, help="Max. Anzahl Dokumente (None=alle)")
    p.add_argument("--state-file", type=str, default="data/migration_state.json", help="State-Datei Pfad")
    p.add_argument("--error-csv", type=str, default="data/migration_failed.csv", help="Error-CSV Pfad")
    p.add_argument("--resume", action="store_true", help="State laden und fortsetzen")
    p.add_argument("--reset", action="store_true", help="State löschen vor Start")
    p.add_argument("--no-backends", action="store_true", help="Backends nicht initialisieren (nur für Tests)")
    return p.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    state_file = Path(args.state_file)
    error_csv = Path(args.error_csv)

    if args.reset and state_file.exists():
        state_file.unlink()

    # Wenn nicht resume, vorhandenen State ignorieren (Datei bleibt bestehen)
    if not args.resume and state_file.exists():
        # optionally: backup state
        pass

    job = DocumentMigrationJob(
        batch_size=args.batch_size,
        delay=args.delay,
        dry_run=args.dry_run,
        state_file=state_file,
        error_csv_path=error_csv,
        init_backends=not args.no_backends,
    )

    summary = await job.run(limit=args.limit)
    print("\nMigration Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
