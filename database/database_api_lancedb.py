#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

"""
LanceDB Vector + SQL Database Backend
=====================================

Moderne Vector-Database mit SQL-Metadaten-Support
- Vector Search + SQL Queries in einem
- Apache Arrow/Parquet basiert
- Ultra-schnelle Similarity Search
- Rich Metadata Filtering
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from database.database_api_base import VectorDatabaseBackend

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

# LanceDB Import mit Fallback
try:
    import lancedb
    import pyarrow as pa
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False

logger = logging.getLogger(__name__)


class LanceVectorBackend(VectorDatabaseBackend):
    """LanceDB Backend für Vector + SQL-Operationen mit UDS3-Integration"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.client = None
        self.database_path = config.get('database_path', './lance_db')
        self.embedding_dimension = config.get('embedding_dimension', 384)
        self.distance_metric = config.get('distance_metric', 'cosine')
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for LanceDB: {exc}")
            self.strategy = None
        
        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"LanceDB Vector Backend initialisiert mit Strategie {strategy_version}")
    
    def _backend_connect(self) -> bool:
        """Verbindung zu LanceDB herstellen"""
        if not LANCEDB_AVAILABLE:
            logger.error("LanceDB Python client nicht installiert")
            return False
            
        try:
            # LanceDB-Verbindung öffnen
            self.client = lancedb.connect(self.database_path)
            
            # Test-Query
            tables = self.client.table_names()
            logger.info(f"LanceDB verbunden: {len(tables)} Tabellen ({self.get_backend_type()})")
            return True
            
        except Exception as e:
            logger.error(f"LanceDB Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        """Verbindung schließen"""
        if self.client:
            self.client = None
    
    def is_available(self) -> bool:
        """Prüft ob Backend verfügbar ist"""
        try:
            if self.client:
                self.client.table_names()
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        """Backend-Typ für Logging"""
        return f"LanceDB Vector+SQL"
    
    def create_collection(self, name: str, metadata: Dict = None) -> bool:
        """Collection/Tabelle erstellen"""
        try:
            # Schema für Vector + Metadaten definieren
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self.embedding_dimension)),
                pa.field("document", pa.string()),
                pa.field("metadata", pa.string()),  # JSON als String
                pa.field("created_at", pa.timestamp('us')),
                pa.field("updated_at", pa.timestamp('us'))
            ])
            
            # Leere Tabelle erstellen
            table = self.client.create_table(name, schema=schema, exist_ok=True)
            
            logger.debug(f"LanceDB Collection erstellt: {name}")
            return True
            
        except Exception as e:
            logger.error(f"LanceDB Collection erstellen fehlgeschlagen: {e}")
            return False
    
    def get_collection(self, name: str):
        """Collection/Tabelle abrufen"""
        try:
            return self.client.open_table(name)
        except Exception as e:
            logger.error(f"LanceDB Collection abrufen fehlgeschlagen: {e}")
            return None
    
    def list_collections(self) -> List[str]:
        """Alle Collections auflisten"""
        try:
            return self.client.table_names()
        except Exception as e:
            logger.error(f"LanceDB Collections auflisten fehlgeschlagen: {e}")
            return []
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadatas: List[Dict], ids: List[str], 
                     embeddings: List[List[float]] = None) -> bool:
        """Dokumente hinzufügen"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                # Collection erstellen falls nicht vorhanden
                if not self.create_collection(collection_name):
                    return False
                table = self.get_collection(collection_name)
            
            # Embeddings generieren falls nicht vorhanden
            if embeddings is None:
                embeddings = self._generate_embeddings(documents)
            
            # Daten vorbereiten
            import datetime
            now = datetime.datetime.now()
            
            records = []
            for i, (doc, metadata, doc_id, embedding) in enumerate(zip(documents, metadatas, ids, embeddings)):
                record = {
                    "id": doc_id,
                    "vector": embedding,
                    "document": doc,
                    "metadata": json.dumps(metadata),
                    "created_at": now,
                    "updated_at": now
                }
                records.append(record)
            
            # Batch-Insert
            table.add(records)
            
            logger.debug(f"LanceDB Dokumente hinzugefügt: {len(records)} in {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"LanceDB Dokumente hinzufügen fehlgeschlagen: {e}")
            return False
    
    def _generate_embeddings(self, documents: List[str]) -> List[List[float]]:
        """Embeddings für Dokumente generieren"""
        try:
            # Einfaches Dummy-Embedding für Demo
            # In Produktion: Ollama/OpenAI/HuggingFace Integration
            import random
            embeddings = []
            for doc in documents:
                # Dummy-Embedding mit korrekter Dimension
                embedding = [random.random() for _ in range(self.embedding_dimension)]
                embeddings.append(embedding)
            
            logger.warning("LanceDB: Dummy-Embeddings verwendet - Produktions-Embedding-Model integrieren!")
            return embeddings
            
        except Exception as e:
            logger.error(f"LanceDB Embedding-Generation fehlgeschlagen: {e}")
            return []
    
    def similarity_search(self, collection_name: str, query_embedding: List[float], 
                         limit: int = 10, metadata_filter: Dict = None) -> List[Dict]:
        """Similarity Search"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                return []
            
            # Vector Search Query
            query = table.search(query_embedding).limit(limit)
            
            # Metadata-Filter hinzufügen falls vorhanden
            if metadata_filter:
                # LanceDB SQL-Style Filtering
                filter_conditions = []
                for key, value in metadata_filter.items():
                    if isinstance(value, str):
                        filter_conditions.append(f"json_extract(metadata, '$.{key}') = '{value}'")
                    else:
                        filter_conditions.append(f"json_extract(metadata, '$.{key}') = {value}")
                
                if filter_conditions:
                    where_clause = " AND ".join(filter_conditions)
                    query = query.where(where_clause)
            
            # Ergebnisse abrufen
            results = query.to_list()
            
            # Formatieren
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': result.get('id'),
                    'document': result.get('document'),
                    'metadata': json.loads(result.get('metadata', '{}')),
                    'score': result.get('_distance', 0.0),
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at')
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"LanceDB Similarity Search fehlgeschlagen: {e}")
            return []
    
    def sql_query(self, collection_name: str, sql_filter: str) -> List[Dict]:
        """SQL-Query auf Metadaten"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                return []
            
            # SQL-Query ausführen
            results = table.search().where(sql_filter).to_list()
            
            # Formatieren
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': result.get('id'),
                    'document': result.get('document'),
                    'metadata': json.loads(result.get('metadata', '{}')),
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at')
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"LanceDB SQL Query fehlgeschlagen: {e}")
            return []
    
    def hybrid_search(self, collection_name: str, query_embedding: List[float],
                     sql_filter: str = None, limit: int = 10) -> List[Dict]:
        """Hybrid Search: Vector + SQL Filter"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                return []
            
            # Vector Search mit SQL Filter
            query = table.search(query_embedding).limit(limit)
            
            if sql_filter:
                query = query.where(sql_filter)
            
            results = query.to_list()
            
            # Formatieren
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': result.get('id'),
                    'document': result.get('document'),
                    'metadata': json.loads(result.get('metadata', '{}')),
                    'vector_score': result.get('_distance', 0.0),
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at')
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"LanceDB Hybrid Search fehlgeschlagen: {e}")
            return []
    
    def update_document(self, collection_name: str, doc_id: str, 
                       document: str = None, metadata: Dict = None) -> bool:
        """Dokument aktualisieren"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                return False
            
            # Update-Daten vorbereiten
            update_data = {}
            if document is not None:
                update_data['document'] = document
                # Neues Embedding generieren
                embeddings = self._generate_embeddings([document])
                if embeddings:
                    update_data['vector'] = embeddings[0]
            
            if metadata is not None:
                update_data['metadata'] = json.dumps(metadata)
            
            if update_data:
                import datetime
                update_data['updated_at'] = datetime.datetime.now()
                
                # Update ausführen
                table.update(where=f"id = '{doc_id}'", values=update_data)
            
            return True
            
        except Exception as e:
            logger.error(f"LanceDB Dokument Update fehlgeschlagen: {e}")
            return False
    
    def delete_documents(self, collection_name: str, doc_ids: List[str]) -> bool:
        """Dokumente löschen"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                return False
            
            # Batch-Delete
            for doc_id in doc_ids:
                table.delete(f"id = '{doc_id}'")
            
            return True
            
        except Exception as e:
            logger.error(f"LanceDB Dokumente löschen fehlgeschlagen: {e}")
            return False
    
    def get_table_stats(self, collection_name: str) -> Dict:
        """Tabellen-Statistiken abrufen"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                return {}
            
            # Basis-Statistiken
            stats = {
                'table_name': collection_name,
                'backend_type': self.get_backend_type(),
                'embedding_dimension': self.embedding_dimension,
                'distance_metric': self.distance_metric
            }
            
            try:
                # Erweiterte Statistiken
                total_rows = table.count_rows()
                stats['total_documents'] = total_rows
                
                # Schema-Info
                schema = table.schema
                stats['schema'] = str(schema)
                
            except Exception as e:
                logger.warning(f"LanceDB erweiterte Statistiken nicht verfügbar: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"LanceDB Statistiken abrufen fehlgeschlagen: {e}")
            return {}
    
    def compact_table(self, collection_name: str) -> bool:
        """Tabelle kompaktieren/optimieren"""
        try:
            table = self.get_collection(collection_name)
            if not table:
                return False
            
            # LanceDB Kompaktierung
            table.compact_files()
            
            logger.info(f"LanceDB Tabelle kompaktiert: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"LanceDB Kompaktierung fehlgeschlagen: {e}")
            return False


def get_backend_class():
    """Factory-Funktion für LanceDB Backend"""
    return LanceVectorBackend if LANCEDB_AVAILABLE else None


"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_lancedb"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "55db916cfcb1f53gf949g8d4349ecfgf39g89df06g97faf389fdb906c099fg3f"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===