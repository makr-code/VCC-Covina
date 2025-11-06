"""
Validation Script: Legal Graph Migration State & Errors

Usage examples:
  python scripts/validate_legal_graph_migration.py \
    --state-file data/migration_state.json --error-csv data/migration_failed.csv

  # Optional Neo4j checks (requires running DB and auth via env)
  python scripts/validate_legal_graph_migration.py --neo4j --sample 5
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate legal graph migration results")
    p.add_argument("--state-file", type=str, default="data/migration_state.json", help="Path to migration state JSON")
    p.add_argument("--error-csv", type=str, default="data/migration_failed.csv", help="Path to error CSV")
    p.add_argument("--neo4j", action="store_true", help="Run optional Neo4j checks (counts)")
    p.add_argument("--sample", type=int, default=3, help="Sample size for printing recent errors")
    return p.parse_args()


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def count_error_lines(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            # subtract header if present
            lines = f.readlines()
            return max(0, len(lines) - 1) if lines else 0
    except Exception:
        return 0


def print_error_samples(path: Path, sample: int = 3) -> None:
    if not path.exists():
        print("No error CSV found.")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = [line.rstrip("\n") for line in f.readlines()]
        if len(rows) <= 1:
            print("No errors logged.")
            return
        header, *data = rows
        print("\nRecent errors (up to sample):")
        for row in data[-sample:]:
            print("  ", row)
    except Exception:
        print("Could not read error samples.")


def optional_neo4j_checks() -> None:
    # Optional lightweight check using environment variables if available
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    pwd = os.environ.get("NEO4J_PASSWORD")

    if not (uri and user and pwd):
        print("Neo4j env not set; skipping DB checks. Set NEO4J_URI/USER/PASSWORD to enable.")
        return

    try:
        from neo4j import GraphDatabase
    except Exception as e:
        print(f"neo4j driver not available: {e}")
        return

    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as session:
            # Conservative counts; adjust to your domain labels if needed
            result = session.run("""
                MATCH (n) RETURN count(n) AS nodes
            """)
            nodes = result.single()["nodes"]

            result = session.run("""
                MATCH ()-[r]->() RETURN count(r) AS rels
            """)
            rels = result.single()["rels"]

        driver.close()
        print(f"Neo4j counts: nodes={nodes}, rels={rels}")
    except Exception as e:
        print(f"Neo4j check failed: {e}")


def main() -> None:
    args = parse_args()
    state_path = Path(args.state_file)
    error_path = Path(args.error_csv)

    state = load_state(state_path)
    errors = count_error_lines(error_path)

    print("Migration Validation Summary")
    print("=" * 32)
    if state:
        print(f"State file:         {state_path}")
        print(f"Last processed ID:  {state.get('last_processed_id')}")
        print(f"Total processed:    {state.get('total_processed')}")
        print(f"Entities extracted: {state.get('total_entities_extracted')}")
        print(f"Total errors:       {state.get('total_errors')}")
        print(f"Batches completed:  {state.get('batches_completed')}")
        print(f"Last updated at:    {state.get('last_updated_at')}")
    else:
        print("No state found.")

    print(f"Error CSV:          {error_path} ({errors} rows)")
    print_error_samples(error_path, sample=args.sample)

    if args.neo4j:
        print("\nRunning optional Neo4j checks...")
        optional_neo4j_checks()


if __name__ == "__main__":
    main()
