"""
Phase L4: NLP → Graph Persistence
Persistiert extrahierte Entities und Relations aus JSONL in Neo4j Knowledge Graph.

Environment Variablen:
- ENABLE_NLP_GRAPH_PERSISTENCE (default: false)
- NLP_INPUT_JSONL (default: data/nlp/entities_full.jsonl)
- NLP_CHECKPOINT_INTERVAL (default: 1000)
- NLP_PERSISTENCE_DRY_RUN (default: false)
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add uds3 to path if needed
uds3_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uds3"))
if os.path.exists(uds3_path) and uds3_path not in sys.path:
    sys.path.insert(0, uds3_path)

try:
    from uds3.core.relations import UDS3RelationsCore
except ImportError:
    print("[WARNING] UDS3RelationsCore nicht verfügbar - nur Dry-Run Modus möglich")
    UDS3RelationsCore = None


class NLPGraphPersister:
    """Persistiert NLP-Extraktionsergebnisse in Neo4j Knowledge Graph."""
    
    def __init__(self, neo4j_wrapper=None, dry_run: bool = False):
        """
        Args:
            neo4j_wrapper: UDS3 Neo4j Wrapper (graph backend)
            dry_run: Wenn True, keine echten DB-Writes
        """
        self.neo4j = neo4j_wrapper
        self.dry_run = dry_run
        self.stats = {
            "docs_processed": 0,
            "entities_created": 0,
            "relations_created": 0,
            "errors": 0,
        }
    
    def _create_legal_concept_node(self, entity: Dict[str, Any], doc_path: str) -> Optional[str]:
        """Erstellt oder updated einen LegalConcept-Node aus einem Entity.
        
        Returns:
            concept_id oder None bei Fehler
        """
        if self.dry_run:
            return f"concept_{entity['text'][:20]}"
        
        if not self.neo4j:
            return None
        
        # LegalConcept für relevante Entity-Labels (ORG, LOC, MISC mit Legal-Context)
        label = entity.get("label", "UNKNOWN")
        if label not in {"ORG", "LOC", "MISC", "PER"}:
            return None
        
        text = entity.get("text", "").strip()
        if not text or len(text) < 3:  # Minimal length filter
            return None
        
        concept_id = f"nlp_{label.lower()}_{text[:50]}"
        
        query = """
        MERGE (c:LegalConcept {id: $id})
        ON CREATE SET 
            c.name = $name,
            c.label = $label,
            c.source = 'nlp_extraction',
            c.created_at = datetime(),
            c.extraction_count = 1
        ON MATCH SET
            c.extraction_count = c.extraction_count + 1,
            c.last_seen = datetime()
        RETURN c.id as id
        """
        
        try:
            with self.neo4j.neo4j_session() as session:
                result = session.run(query, {
                    "id": concept_id,
                    "name": text,
                    "label": label,
                })
                record = result.single()
                if record:
                    self.stats["entities_created"] += 1
                    return concept_id
            return None
        except Exception as e:
            self.stats["errors"] += 1
            return None
    
    def _create_legal_norm_node(self, relation: Dict[str, Any]) -> Optional[str]:
        """Erstellt oder updated einen LegalNorm-Node aus einer CITES_NORM Relation.
        
        Returns:
            norm_id oder None bei Fehler
        """
        if self.dry_run:
            return f"norm_{relation.get('object', '')[:20]}"
        
        if not self.neo4j or relation.get("type") != "CITES_NORM":
            return None
        
        norm_text = relation.get("object", "").strip()
        if not norm_text:
            return None
        
        norm_id = f"nlp_norm_{norm_text[:50]}"
        
        query = """
        MERGE (n:LegalNorm {id: $id})
        ON CREATE SET 
            n.name = $name,
            n.source = 'nlp_extraction',
            n.created_at = datetime(),
            n.citation_count = 1
        ON MATCH SET
            n.citation_count = n.citation_count + 1,
            n.last_cited = datetime()
        RETURN n.id as id
        """
        
        try:
            with self.neo4j.neo4j_session() as session:
                result = session.run(query, {
                    "id": norm_id,
                    "name": norm_text,
                })
                record = result.single()
                if record:
                    self.stats["entities_created"] += 1
                    return norm_id
            return None
        except Exception as e:
            self.stats["errors"] += 1
            return None
    
    def _create_authority_node(self, relation: Dict[str, Any]) -> Optional[str]:
        """Erstellt oder updated einen Authority-Node aus einer HAS_JURISDICTION Relation.
        
        Returns:
            authority_id oder None bei Fehler
        """
        if self.dry_run:
            return f"auth_{relation.get('subject', '')[:20]}"
        
        if not self.neo4j or relation.get("type") != "HAS_JURISDICTION":
            return None
        
        authority_name = relation.get("subject", "").strip()
        if not authority_name:
            return None
        
        authority_id = f"nlp_authority_{authority_name[:50]}"
        
        query = """
        MERGE (a:Authority {id: $id})
        ON CREATE SET 
            a.name = $name,
            a.source = 'nlp_extraction',
            a.created_at = datetime(),
            a.mention_count = 1
        ON MATCH SET
            a.mention_count = a.mention_count + 1,
            a.last_mentioned = datetime()
        RETURN a.id as id
        """
        
        try:
            with self.neo4j.neo4j_session() as session:
                result = session.run(query, {
                    "id": authority_id,
                    "name": authority_name,
                })
                record = result.single()
                if record:
                    self.stats["entities_created"] += 1
                    return authority_id
            return None
        except Exception as e:
            self.stats["errors"] += 1
            return None
    
    def _link_document_to_concept(self, doc_path: str, concept_id: str) -> bool:
        """Verlinkt ein Document mit einem LegalConcept via MENTIONS Relation."""
        if self.dry_run:
            return True
        
        if not self.neo4j:
            return False
        
        # Match Document by file_path (full path)
        query = """
        MATCH (d:Document)
        WHERE d.file_path = $doc_path
        MATCH (c:LegalConcept {id: $concept_id})
        MERGE (d)-[r:MENTIONS]->(c)
        ON CREATE SET r.created_at = datetime()
        RETURN r
        """
        
        try:
            with self.neo4j.neo4j_session() as session:
                result = session.run(query, {
                    "doc_path": doc_path,
                    "concept_id": concept_id,
                })
                # Check if relation was created
                if result.single():
                    self.stats["relations_created"] += 1
                    return True
            return False
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def _link_document_to_norm(self, doc_path: str, norm_id: str) -> bool:
        """Verlinkt ein Document mit einer LegalNorm via CITES Relation."""
        if self.dry_run:
            return True
        
        if not self.neo4j:
            return False
        
        # Match Document by file_path (full path)
        query = """
        MATCH (d:Document)
        WHERE d.file_path = $doc_path
        MATCH (n:LegalNorm {id: $norm_id})
        MERGE (d)-[r:CITES]->(n)
        ON CREATE SET r.created_at = datetime()
        RETURN r
        """
        
        try:
            with self.neo4j.neo4j_session() as session:
                result = session.run(query, {
                    "doc_path": doc_path,
                    "norm_id": norm_id,
                })
                if result.single():
                    self.stats["relations_created"] += 1
                    return True
            return False
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def _link_document_to_authority(self, doc_path: str, authority_id: str) -> bool:
        """Verlinkt ein Document mit einer Authority via REFERENCES_AUTHORITY Relation."""
        if self.dry_run:
            return True
        
        if not self.neo4j:
            return False
        
        # Match Document by file_path (full path)
        query = """
        MATCH (d:Document)
        WHERE d.file_path = $doc_path
        MATCH (a:Authority {id: $authority_id})
        MERGE (d)-[r:REFERENCES_AUTHORITY]->(a)
        ON CREATE SET r.created_at = datetime()
        RETURN r
        """
        
        try:
            with self.neo4j.neo4j_session() as session:
                result = session.run(query, {
                    "doc_path": doc_path,
                    "authority_id": authority_id,
                })
                if result.single():
                    self.stats["relations_created"] += 1
                    return True
            return False
        except Exception as e:
            self.stats["errors"] += 1
            return False
    
    def _ensure_document_node(self, doc_path: str) -> bool:
        """Ensures Document node exists for given path (creates if missing)."""
        if self.dry_run:
            return True
        
        if not self.neo4j:
            return False
        
        query = """
        MERGE (d:Document {file_path: $path})
        ON CREATE SET
            d.id = substring(replace($path, '\\\\', '/'), size($path)-16, 16),
            d.source = 'nlp_extraction',
            d.created_at = datetime()
        RETURN d.id as id
        """
        
        try:
            with self.neo4j.neo4j_session() as session:
                result = session.run(query, {"path": doc_path})
                return result.single() is not None
        except Exception as e:
            return False
    
    def process_jsonl_record(self, record: Dict[str, Any]) -> None:
        """Verarbeitet einen JSONL-Record (1 Dokument) und persistiert Entities/Relations."""
        if "error" in record:
            self.stats["errors"] += 1
            return
        
        doc_path = record.get("path", "")
        entities = record.get("entities", [])
        relations = record.get("relations", [])
        
        # Ensure Document node exists
        if not self._ensure_document_node(doc_path):
            self.stats["errors"] += 1
            return
        
        # Entities → LegalConcept Nodes + Document Links
        for entity in entities:
            concept_id = self._create_legal_concept_node(entity, doc_path)
            if concept_id:
                self._link_document_to_concept(doc_path, concept_id)
        
        # Relations → LegalNorm/Authority Nodes + Document Links
        for relation in relations:
            rel_type = relation.get("type")
            if rel_type == "CITES_NORM":
                norm_id = self._create_legal_norm_node(relation)
                if norm_id:
                    self._link_document_to_norm(doc_path, norm_id)
            elif rel_type == "HAS_JURISDICTION":
                authority_id = self._create_authority_node(relation)
                if authority_id:
                    self._link_document_to_authority(doc_path, authority_id)
        
        self.stats["docs_processed"] += 1
    
    def get_stats(self) -> Dict[str, int]:
        """Liefert Statistiken über den Persistence-Lauf."""
        return self.stats.copy()


def batch_persist_from_jsonl(
    jsonl_path: str,
    neo4j_wrapper=None,
    checkpoint_interval: int = 1000,
    dry_run: bool = False
) -> Dict[str, int]:
    """Batch-Persistence aus JSONL mit Checkpointing.
    
    Args:
        jsonl_path: Pfad zur JSONL-Datei
        neo4j_wrapper: UDS3 Neo4j Wrapper
        checkpoint_interval: Progress-Logging alle N Dokumente
        dry_run: Test-Modus ohne DB-Writes
    
    Returns:
        Statistiken (docs_processed, entities_created, relations_created, errors)
    """
    persister = NLPGraphPersister(neo4j_wrapper, dry_run=dry_run)
    
    if not os.path.exists(jsonl_path):
        print(f"[ERROR] JSONL file not found: {jsonl_path}")
        return persister.get_stats()
    
    print(f"[NLP-PERSIST] Starting batch persistence from: {jsonl_path}")
    print(f"[NLP-PERSIST] Dry run: {dry_run}")
    print(f"[NLP-PERSIST] Checkpoint interval: {checkpoint_interval}")
    
    with open(jsonl_path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                persister.process_jsonl_record(record)
                
                if i % checkpoint_interval == 0:
                    stats = persister.get_stats()
                    print(f"[NLP-PERSIST] Checkpoint: {stats['docs_processed']} docs | "
                          f"{stats['entities_created']} entities | "
                          f"{stats['relations_created']} relations | "
                          f"{stats['errors']} errors")
            except json.JSONDecodeError:
                persister.stats["errors"] += 1
            except Exception as e:
                persister.stats["errors"] += 1
                print(f"[ERROR] Line {i}: {e}")
    
    stats = persister.get_stats()
    print(f"\n[NLP-PERSIST] Completed!")
    print(f"  Docs processed: {stats['docs_processed']}")
    print(f"  Entities created: {stats['entities_created']}")
    print(f"  Relations created: {stats['relations_created']}")
    print(f"  Errors: {stats['errors']}")
    
    return stats


if __name__ == "__main__":
    jsonl_path = os.environ.get("NLP_INPUT_JSONL", "data/nlp/entities_full.jsonl")
    checkpoint_interval = int(os.environ.get("NLP_CHECKPOINT_INTERVAL", "1000"))
    dry_run = os.environ.get("NLP_PERSISTENCE_DRY_RUN", "true").lower() in {"1", "true", "yes"}
    
    # Neo4j connection details (from copilot-instructions.md)
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://192.168.178.94:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "neo4j")
    
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
                print(f"[NLP-PERSIST] UDS3 Neo4j Wrapper initialisiert ({neo4j_uri})")
            except Exception as e:
                print(f"[ERROR] UDS3 Initialisierung fehlgeschlagen: {e}")
                print("[NLP-PERSIST] Fallback zu Dry-Run Modus")
                dry_run = True
    
    batch_persist_from_jsonl(
        jsonl_path=jsonl_path,
        neo4j_wrapper=neo4j_wrapper,
        checkpoint_interval=checkpoint_interval,
        dry_run=dry_run
    )

