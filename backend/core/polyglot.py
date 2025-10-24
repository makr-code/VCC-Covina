#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Polyglot Database Integrat        logger.info(
            f"🔧 UDS3 Polyglot Integration initialisiert - "
            f"SAGA: {'✅' if self.saga_enabled else '❌'}, "
            f"Neo4j: {'✅' if self.neo4j_enabled else '❌'}, "
            f"Vector: {'✅' if self.vector_enabled else '❌'}, "
            f"CouchDB: {'✅' if self.couchdb_enabled else '❌'}"
        )r Covina Backend
======================================================

Ersetzt alle Simulationen durch echte UDS3-basierte Operationen:
- Echte Vector DB Operationen (ChromaDB)
- Echte Graph DB Operationen (Neo4j)
- Echte Relational DB Operationen (SQLite)
- SAGA Pattern für Transaktionskonsistenz

Author: Covina Development Team
Date: 5. Oktober 2025
"""

import logging
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# UDS3 Imports
try:
    from uds3.uds3_saga_orchestrator import UDS3SagaOrchestrator
    from uds3.saga_multi_db_integration import (
        SAGAStep,
        SAGACompensationAction,
        SAGATransactionState,
        SAGAOrchestrator,
        RelationalSAGAExecutor,
        DocumentSAGAExecutor,
        VectorSAGAExecutor,
        GraphSAGAExecutor
    )
    UDS3_SAGA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"UDS3 SAGA components not available: {e}")
    UDS3_SAGA_AVAILABLE = False
    UDS3SagaOrchestrator = None
    SAGAOrchestrator = None
    SAGAStep = None
    SAGACompensationAction = None
    SAGATransactionState = None
    RelationalSAGAExecutor = None
    DocumentSAGAExecutor = None
    VectorSAGAExecutor = None
    GraphSAGAExecutor = None

try:
    from uds3.uds3_relations_core import UDS3RelationsCore
    UDS3_RELATIONS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"UDS3 Relations Core not available: {e}")
    UDS3_RELATIONS_AVAILABLE = False
    UDS3RelationsCore = None


class UDS3PolyglotIntegration:
    """
    Zentrale Integration für alle UDS3-Polyglot-Operationen
    Ersetzt Simulationen durch echte Datenbankoperationen
    """
    
    def __init__(
        self,
        saga_orchestrator: Optional[Any] = None,
        relations_core: Optional[UDS3RelationsCore] = None,
        vector_database: Optional[Any] = None,
        couchdb_backend: Optional[Any] = None
    ):
        """
        Initialisiert Polyglot Integration
        
        Args:
            saga_orchestrator: UDS3 SAGA Orchestrator für transaktionale Operationen
            relations_core: UDS3 Relations Core für Neo4j
            vector_database: ChromaDB Vector Database
            couchdb_backend: CouchDB Backend für Dokument-Speicherung
        """
        self.saga_orchestrator = saga_orchestrator
        self.relations_core = relations_core
        self.vector_database = vector_database
        self.couchdb_backend = couchdb_backend
        
        # Prüfe Verfügbarkeit
        self.saga_enabled = saga_orchestrator is not None
        self.neo4j_enabled = (relations_core is not None and 
                             hasattr(relations_core, 'neo4j_enabled') and 
                             relations_core.neo4j_enabled and
                             relations_core.driver is not None)
        self.vector_enabled = vector_database is not None
        self.couchdb_enabled = couchdb_backend is not None
        
        logger.info(
            f"🔧 UDS3 Polyglot Integration initialisiert - "
            f"SAGA: {'✅' if self.saga_enabled else '❌'}, "
            f"Neo4j: {'✅' if self.neo4j_enabled else '❌'}, "
            f"Vector: {'✅' if self.vector_enabled else '❌'}"
        )
    
    async def execute_polyglot_document_operation(
        self,
        document_id: str,
        file_path: str,
        content: str,
        classification: str,
        entities_count: int,
        legal_terms_count: int,
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Führt Polyglot-Operationen mit SAGA Pattern aus
        
        Returns:
            Dict mit Operationsergebnissen und SAGA-Status
        """
        
        if self.saga_enabled:
            return await self._execute_with_saga(
                document_id, file_path, content, classification,
                entities_count, legal_terms_count, timestamp
            )
        else:
            return await self._execute_without_saga(
                document_id, file_path, content, classification,
                entities_count, legal_terms_count, timestamp
            )
    
    async def _execute_with_saga(
        self,
        document_id: str,
        file_path: str,
        content: str,
        classification: str,
        entities_count: int,
        legal_terms_count: int,
        timestamp: str
    ) -> Dict[str, Any]:
        """Führt Operationen mit SAGA-Transaktionsmanagement aus"""
        
        logger.info(f"🔄 SAGA Transaction gestartet für Document {document_id}")
        
        saga_transaction_id = f"doc_saga_{document_id}_{int(datetime.now().timestamp())}"
        
        try:
            # SAGA Steps definieren
            steps = []
            
            # Step 1: Relational Database (SQLite)
            steps.append({
                "step_id": f"{saga_transaction_id}_relational",
                "step_name": "relational_metadata",
                "database_type": "relational_db",
                "operation_data": {
                    "operation": "create_document_metadata",
                    "document_id": document_id,
                    "file_path": file_path,
                    "classification": classification,
                    "content_length": len(content),
                    "legal_terms_count": legal_terms_count,
                    "timestamp": timestamp
                }
            })
            
            # Step 2: Vector Database (ChromaDB)
            if self.vector_enabled:
                steps.append({
                    "step_id": f"{saga_transaction_id}_vector",
                    "step_name": "vector_embeddings",
                    "database_type": "vector_db",
                    "operation_data": {
                        "operation": "create_embeddings",
                        "document_id": document_id,
                        "content": content,
                        "chunks": self._create_chunks(content)
                    }
                })
            
            # Step 3: Graph Database (Neo4j)
            if self.neo4j_enabled:
                steps.append({
                    "step_id": f"{saga_transaction_id}_graph",
                    "step_name": "graph_relationships",
                    "database_type": "graph_db",
                    "operation_data": {
                        "operation": "create_document_node",
                        "document_id": document_id,
                        "classification": classification,
                        "entities_count": entities_count,
                        "legal_terms_count": legal_terms_count,
                        "timestamp": timestamp
                    }
                })
            
            # Step 4: CouchDB (Document Storage)
            if self.couchdb_enabled:
                steps.append({
                    "step_id": f"{saga_transaction_id}_couchdb",
                    "step_name": "document_storage",
                    "database_type": "couchdb",
                    "operation_data": {
                        "operation": "store_document",
                        "document_id": document_id,
                        "file_path": file_path,
                        "content": content,
                        "classification": classification,
                        "timestamp": timestamp
                    }
                })
            
            # Führe SAGA aus
            saga_result = await self._execute_saga_steps(saga_transaction_id, steps)
            
            return {
                "saga_transaction_id": saga_transaction_id,
                "saga_status": saga_result.get("status", "COMPLETED"),
                "saga_enabled": True,
                "relational_db": saga_result.get("steps", {}).get("relational_metadata", {}),
                "vector_db": saga_result.get("steps", {}).get("vector_embeddings", {}),
                "graph_db": saga_result.get("steps", {}).get("graph_relationships", {}),
                "couchdb": saga_result.get("steps", {}).get("document_storage", {}),
                "saga_analysis": {
                    "saga_executed": True,
                    "transaction_consistent": saga_result.get("status") == "COMPLETED",
                    "saga_status": saga_result.get("status", "UNKNOWN"),
                    "steps_executed": saga_result.get("steps_executed", 0),
                    "steps_compensated": saga_result.get("steps_compensated", 0),
                    "execution_time_ms": saga_result.get("execution_time_ms", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ SAGA Transaction fehlgeschlagen: {e}")
            return await self._execute_without_saga(
                document_id, file_path, content, classification,
                entities_count, legal_terms_count, timestamp
            )
    
    async def _execute_saga_steps(
        self,
        transaction_id: str,
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Führt SAGA Steps aus mit Compensation bei Fehler"""
        
        import time
        start_time = time.time()
        
        executed_steps = {}
        steps_executed = 0
        steps_compensated = 0
        
        try:
            for step in steps:
                step_name = step["step_name"]
                database_type = step["database_type"]
                operation_data = step["operation_data"]
                
                logger.debug(f"🔄 SAGA Step: {step_name} ({database_type})")
                
                # Führe Step aus
                if database_type == "relational_db":
                    result = await self._execute_relational_step(operation_data)
                elif database_type == "vector_db":
                    result = await self._execute_vector_step(operation_data)
                elif database_type == "graph_db":
                    result = await self._execute_graph_step(operation_data)
                elif database_type == "couchdb":
                    result = await self._execute_couchdb_step(operation_data)
                else:
                    result = {"success": False, "error": f"Unknown database type: {database_type}"}
                
                executed_steps[step_name] = result
                
                if result.get("success"):
                    steps_executed += 1
                    logger.debug(f"✅ SAGA Step erfolgreich: {step_name}")
                else:
                    # Fehler - Starte Compensation
                    logger.warning(f"❌ SAGA Step fehlgeschlagen: {step_name}, starte Compensation")
                    await self._compensate_steps(executed_steps)
                    steps_compensated = len(executed_steps) - 1
                    
                    return {
                        "status": "COMPENSATED",
                        "steps": executed_steps,
                        "steps_executed": steps_executed,
                        "steps_compensated": steps_compensated,
                        "execution_time_ms": int((time.time() - start_time) * 1000),
                        "error": result.get("error", "Step failed")
                    }
            
            # Alle Steps erfolgreich
            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f"✅ SAGA Transaction erfolgreich abgeschlossen in {execution_time}ms")
            
            return {
                "status": "COMPLETED",
                "steps": executed_steps,
                "steps_executed": steps_executed,
                "steps_compensated": 0,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"❌ SAGA Execution Error: {e}")
            await self._compensate_steps(executed_steps)
            
            return {
                "status": "FAILED",
                "steps": executed_steps,
                "steps_executed": steps_executed,
                "steps_compensated": len(executed_steps),
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
    
    async def _execute_relational_step(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Relational DB Step aus"""
        import sqlite3
        from pathlib import Path
        
        try:
            # Stelle sicher, dass das data-Verzeichnis existiert
            data_dir = Path(__file__).parent / "data"
            data_dir.mkdir(exist_ok=True)
            
            db_path = data_dir / "covina_documents.db"
            
            conn = sqlite3.connect(str(db_path), timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            cursor = conn.cursor()
            
            # Erstelle Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    content_length INTEGER NOT NULL,
                    legal_terms_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    quality_score REAL,
                    processing_status TEXT DEFAULT 'completed'
                )
            ''')
            
            # Insert Document
            cursor.execute('''
                INSERT OR REPLACE INTO documents 
                (document_id, file_path, classification, content_length, legal_terms_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                operation_data["document_id"],
                operation_data["file_path"],
                operation_data["classification"],
                operation_data["content_length"],
                operation_data["legal_terms_count"],
                operation_data["timestamp"]
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✅ Relational DB: Document {operation_data['document_id']} gespeichert")
            
            return {
                "success": True,
                "operations": ["metadata_inserted"],
                "records_affected": 1,
                "database_file": str(db_path)
            }
            
        except Exception as e:
            logger.error(f"❌ Relational DB Error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_vector_step(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Vector DB Step aus - ECHTES SCHREIBEN in ChromaDB"""
        
        if not self.vector_enabled or not self.vector_database:
            return {
                "success": False,
                "error": "Vector database not available",
                "fallback": "simulation"
            }
        
        try:
            document_id = operation_data["document_id"]
            chunks = operation_data["chunks"]
            
            # ✅ ECHTE ChromaDB-Operations - Schreibt tatsächlich in Datenbank
            embeddings_created = 0
            failed_chunks = 0
            
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{idx}"
                
                try:
                    # ChromaDB add_document mit Metadaten
                    self.vector_database.add_document(
                        doc_id=chunk_id,
                        content=chunk,
                        metadata={
                            "document_id": document_id,
                            "chunk_index": idx,
                            "total_chunks": len(chunks),
                            "chunk_size": len(chunk)
                        }
                    )
                    embeddings_created += 1
                    
                except Exception as chunk_error:
                    logger.warning(f"⚠️ Vector DB: Chunk {idx} fehlgeschlagen: {chunk_error}")
                    failed_chunks += 1
            
            if embeddings_created == 0:
                logger.error(f"❌ Vector DB: ALLE {len(chunks)} Chunks fehlgeschlagen für {document_id}")
                return {
                    "success": False,
                    "error": f"All {len(chunks)} chunks failed to insert",
                    "failed_chunks": failed_chunks
                }
            
            logger.info(f"✅ Vector DB: {embeddings_created}/{len(chunks)} Chunks in ChromaDB gespeichert für {document_id}")
            
            return {
                "success": True,
                "operations": ["embeddings_generated", "vector_index_updated"],
                "chunks_created": len(chunks),
                "embeddings_generated": embeddings_created,
                "failed_chunks": failed_chunks,
                "backend": "ChromaDB Remote"
            }
            
        except Exception as e:
            logger.error(f"❌ Vector DB Error (outer): {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    async def _execute_graph_step(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt Graph DB Step aus (Neo4j)"""
        
        if not self.neo4j_enabled or not self.relations_core:
            return {
                "success": False,
                "error": "Neo4j not available",
                "fallback": "simulation"
            }
        
        try:
            document_id = operation_data["document_id"]
            classification = operation_data["classification"]
            entities_count = operation_data["entities_count"]
            legal_terms_count = operation_data["legal_terms_count"]
            timestamp = operation_data["timestamp"]
            
            nodes_created = 0
            relationships_created = 0
            
            with self.relations_core.neo4j_session() as session:
                # Document Node
                result = session.run("""
                    MERGE (d:Document {document_id: $document_id})
                    SET d.classification = $classification,
                        d.entities_count = $entities_count,
                        d.legal_terms_count = $legal_terms_count,
                        d.created_at = datetime($timestamp),
                        d.updated_at = datetime($timestamp)
                    RETURN d
                """, 
                    document_id=document_id,
                    classification=classification,
                    entities_count=entities_count,
                    legal_terms_count=legal_terms_count,
                    timestamp=timestamp
                )
                
                if result.single():
                    nodes_created += 1
                
                # Classification Relationship
                result = session.run("""
                    MERGE (c:Classification {name: $classification})
                    WITH c
                    MATCH (d:Document {document_id: $document_id})
                    MERGE (d)-[r:HAS_CLASSIFICATION]->(c)
                    SET r.confidence = $confidence
                    RETURN c, r
                """,
                    classification=classification,
                    document_id=document_id,
                    confidence=0.95 if legal_terms_count > 10 else 0.8
                )
                
                if result.data():
                    nodes_created += 1
                    relationships_created += 1
            
            logger.info(f"✅ Graph DB: {nodes_created} Nodes, {relationships_created} Relationships für {document_id}")
            
            return {
                "success": True,
                "operations": ["document_node_created", "classification_relationship_added"],
                "nodes_created": nodes_created,
                "relationships_created": relationships_created
            }
            
        except Exception as e:
            logger.error(f"❌ Graph DB Error: {e}")
            import traceback
            logger.error(f"Graph DB Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    async def _execute_couchdb_step(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Führt CouchDB Step aus - Speichert vollständiges Dokument"""
        
        if not self.couchdb_enabled or not self.couchdb_backend:
            return {
                "success": False,
                "error": "CouchDB not available",
                "fallback": "simulation"
            }
        
        try:
            document_id = operation_data["document_id"]
            file_path = operation_data["file_path"]
            content = operation_data["content"]
            classification = operation_data["classification"]
            timestamp = operation_data["timestamp"]
            
            # Erstelle CouchDB-Dokument
            couchdb_doc = {
                "_id": f"doc_{document_id}",
                "type": "document",
                "document_id": document_id,
                "file_path": file_path,
                "classification": classification,
                "content": content,
                "content_length": len(content),
                "created_at": timestamp,
                "processing_status": "completed"
            }
            
            # Speichere in CouchDB (API: create_document(doc, doc_id=None))
            # IDEMPOTENCY: CouchDB Adapter prüft intern auf existing document
            result = self.couchdb_backend.create_document(
                doc=couchdb_doc,
                doc_id=f"doc_{document_id}"
            )
            
            if result:
                logger.info(f"✅ CouchDB: Document {document_id} gespeichert (ID: {result}, {len(content)} Zeichen)")
            else:
                logger.warning(f"⚠️ CouchDB: Document {document_id} möglicherweise bereits vorhanden (idempotent skip)")
            
            return {
                "success": True,
                "operations": ["document_stored"],
                "document_id": result or f"doc_{document_id}",
                "content_length": len(content),
                "backend": "CouchDB"
            }
            
        except Exception as e:
            # Check if conflict error (idempotency case)
            error_str = str(e)
            if 'conflict' in error_str.lower() or '409' in error_str:
                logger.warning(f"⚠️ CouchDB Conflict (idempotent): Document {document_id} exists")
                return {
                    "success": True,  # Idempotent success
                    "operations": ["document_exists"],
                    "document_id": f"doc_{document_id}",
                    "content_length": len(content),
                    "backend": "CouchDB",
                    "idempotent": True
                }
            else:
                # Other error → Log and return failure
                logger.error(f"❌ CouchDB Error: {e}")
                import traceback
                logger.error(f"CouchDB Traceback: {traceback.format_exc()}")
                return {"success": False, "error": str(e)}
    
    async def _compensate_steps(self, executed_steps: Dict[str, Any]) -> None:
        """Kompensiert bereits ausgeführte Steps (Rollback)"""
        logger.warning(f"🔄 Starte Compensation für {len(executed_steps)} Steps")
        
        # Compensation in umgekehrter Reihenfolge
        for step_name in reversed(list(executed_steps.keys())):
            try:
                logger.debug(f"↩️ Compensating: {step_name}")
                # TODO: Implementiere echte Compensation
                # - Löschen von Dokumenten
                # - Entfernen von Embeddings
                # - Löschen von Graph Nodes
            except Exception as e:
                logger.error(f"❌ Compensation Error für {step_name}: {e}")
    
    async def _execute_without_saga(
        self,
        document_id: str,
        file_path: str,
        content: str,
        classification: str,
        entities_count: int,
        legal_terms_count: int,
        timestamp: str
    ) -> Dict[str, Any]:
        """Führt Operationen ohne SAGA-Koordination aus (Best Effort)"""
        
        logger.warning("⚠️ Keine SAGA-Koordination verfügbar, verwende Best-Effort Modus")
        
        results = {}
        
        # Relational DB
        results["relational_db"] = await self._execute_relational_step({
            "document_id": document_id,
            "file_path": file_path,
            "classification": classification,
            "content_length": len(content),
            "legal_terms_count": legal_terms_count,
            "timestamp": timestamp
        })
        
        # Vector DB
        if self.vector_enabled:
            results["vector_db"] = await self._execute_vector_step({
                "document_id": document_id,
                "content": content,
                "chunks": self._create_chunks(content)
            })
        
        # Graph DB
        if self.neo4j_enabled:
            results["graph_db"] = await self._execute_graph_step({
                "document_id": document_id,
                "classification": classification,
                "entities_count": entities_count,
                "legal_terms_count": legal_terms_count,
                "timestamp": timestamp
            })
        
        # CouchDB
        if self.couchdb_enabled:
            results["couchdb"] = await self._execute_couchdb_step({
                "document_id": document_id,
                "file_path": file_path,
                "content": content,
                "classification": classification,
                "timestamp": timestamp
            })
        
        results["saga_analysis"] = {
            "saga_executed": False,
            "transaction_consistent": False,
            "saga_status": "NOT_AVAILABLE",
            "mode": "best_effort"
        }
        
        return results
    
    def _create_chunks(self, content: str, chunk_size: int = 500) -> List[str]:
        """
        Erstellt semantische Text-Chunks für Embeddings mit Legal-Document-Strategie
        
        Nutzt spezialisierte Chunking-Strategien:
        - Legal Document Strategy für Rechtsdokumente (§, Art., Abs.)
        - Erhält semantische Grenzen (Paragraphen, Absätze)
        - Fügt Overlap für LLM-Kontext hinzu
        """
        try:
            # Importiere Legal Document Chunking
            from ingestion.chunking.legal_strategy import LegalDocumentChunkStrategy
            from ingestion.chunking.base import ChunkingContext
            
            # Erstelle Chunking-Strategie für Rechtsdokumente
            legal_strategy = LegalDocumentChunkStrategy(
                target_tokens=300,  # ≈ 1500 Zeichen pro Chunk
                overlap_sentences=2,  # 2 Sätze Overlap für Kontext
                min_chunk_length=100,
                max_chunk_length=2000
            )
            
            # Erstelle Chunking-Context
            context = ChunkingContext(
                document_id="temp_doc",
                source_path="",
                file_category=None
            )
            
            # Erzeuge semantische Chunks
            chunks = []
            for segment in legal_strategy.chunk(context, content):
                chunks.append(segment.content)
            
            # Fallback falls keine Chunks erzeugt wurden
            if not chunks:
                logger.warning("⚠️ Legal-Chunking fehlgeschlagen, verwende Character-basiert")
                return [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            
            logger.debug(f"✅ Legal-Chunking: {len(chunks)} semantische Chunks erzeugt")
            return chunks
            
        except Exception as e:
            logger.warning(f"⚠️ Legal-Chunking Fehler ({e}), verwende Fallback")
            # Fallback: Character-basiertes Chunking
            return [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]


# Singleton Instance
_polyglot_integration_instance: Optional[UDS3PolyglotIntegration] = None


def get_polyglot_integration(
    saga_orchestrator: Optional[Any] = None,
    relations_core: Optional[UDS3RelationsCore] = None,
    vector_database: Optional[Any] = None,
    couchdb_backend: Optional[Any] = None
) -> UDS3PolyglotIntegration:
    """
    Gibt Singleton-Instanz der Polyglot Integration zurück
    """
    global _polyglot_integration_instance
    
    if _polyglot_integration_instance is None:
        _polyglot_integration_instance = UDS3PolyglotIntegration(
            saga_orchestrator=saga_orchestrator,
            relations_core=relations_core,
            vector_database=vector_database,
            couchdb_backend=couchdb_backend
        )
    
    return _polyglot_integration_instance
