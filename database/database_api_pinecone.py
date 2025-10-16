#!/usr/bin/env python3
"""
Pinecone Vector Database Backend
"""

import logging
from typing import Dict, List, Optional
from database.database_api_base import VectorDatabaseBackend

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

logger = logging.getLogger(__name__)


class PineconeVectorBackend(VectorDatabaseBackend):
    """Pinecone Vector Database"""
    
    def __init__(self, config: Dict):
        # If pinecone client is missing, don't raise here; defer to connect()
        if not PINECONE_AVAILABLE:
            logger.warning("Pinecone client not available at import time; will fail on connect() if used")
        
        self.config = config
        self.api_key = config.get('api_key')
        self.environment = config.get('environment', 'us-west1-gcp')
        self.index_name = config.get('index_name', 'default-index')
        self.dimension = config.get('dimension', 1536)
        self.metric = config.get('metric', 'cosine')
        self.index = None
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for Pinecone: {exc}")
            self.strategy = None
        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"Pinecone Backend initialisiert mit Strategie {strategy_version}")
        
    def connect(self) -> bool:
        try:
            if not PINECONE_AVAILABLE:
                logging.error("Pinecone client library not installed")
                return False
            if not self.api_key:
                logging.error("Pinecone API Key fehlt")
                return False
            
            pinecone.init(
                api_key=self.api_key,
                environment=self.environment
            )
            
            # Index erstellen falls nicht vorhanden
            if self.index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric
                )
                logging.info(f"Pinecone Index erstellt: {self.index_name}")
            
            self.index = pinecone.Index(self.index_name)
            logging.info(f"Pinecone verbunden: {self.index_name}")
            return True
            
        except Exception as e:
            logging.error(f"Pinecone Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        self.index = None
    
    def is_available(self) -> bool:
        try:
            if self.index:
                stats = self.index.describe_index_stats()
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "Pinecone"
    
    def add_vectors(self, vectors: List[Dict]) -> bool:
        try:
            if not self.index:
                return False
            
            # Vectors in Pinecone Format konvertieren
            pinecone_vectors = []
            for vector in vectors:
                pinecone_vector = {
                    'id': vector['id'],
                    'values': vector['vector'],
                    'metadata': vector.get('metadata', {})
                }
                pinecone_vectors.append(pinecone_vector)
            
            # Batch upsert
            self.index.upsert(vectors=pinecone_vectors)
            return True
            
        except Exception as e:
            logging.error(f"Pinecone Add Vectors fehlgeschlagen: {e}")
            return False
    
    def search_vectors(self, query_vector: List[float], top_k: int = 10, 
                      filters: Dict = None) -> List[Dict]:
        try:
            if not self.index:
                return []
            
            # Query mit optionalen Filtern
            query_params = {
                'vector': query_vector,
                'top_k': top_k,
                'include_metadata': True,
                'include_values': True
            }
            
            if filters:
                query_params['filter'] = filters
            
            response = self.index.query(**query_params)
            
            results = []
            for match in response['matches']:
                results.append({
                    'id': match['id'],
                    'score': match['score'],
                    'vector': match.get('values', []),
                    'metadata': match.get('metadata', {})
                })
            
            return results
            
        except Exception as e:
            logging.error(f"Pinecone Search fehlgeschlagen: {e}")
            return []
    
    def get_vector(self, vector_id: str) -> Optional[Dict]:
        try:
            if not self.index:
                return None
            
            response = self.index.fetch(ids=[vector_id])
            
            if vector_id in response['vectors']:
                vector_data = response['vectors'][vector_id]
                return {
                    'id': vector_id,
                    'vector': vector_data.get('values', []),
                    'metadata': vector_data.get('metadata', {})
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Pinecone Get Vector fehlgeschlagen: {e}")
            return None
    
    def update_vector(self, vector_id: str, vector: List[float] = None, 
                     metadata: Dict = None) -> bool:
        try:
            if not self.index:
                return False
            
            update_params = {'id': vector_id}
            
            if vector:
                update_params['values'] = vector
            
            if metadata:
                update_params['set_metadata'] = metadata
            
            self.index.update(**update_params)
            return True
            
        except Exception as e:
            logging.error(f"Pinecone Update Vector fehlgeschlagen: {e}")
            return False
    
    def delete_vectors(self, vector_ids: List[str]) -> bool:
        try:
            if not self.index:
                return False
            
            self.index.delete(ids=vector_ids)
            return True
            
        except Exception as e:
            logging.error(f"Pinecone Delete Vectors fehlgeschlagen: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        try:
            if not self.index:
                return {}
            
            stats = self.index.describe_index_stats()
            return {
                'total_vectors': stats.get('total_vector_count', 0),
                'dimension': stats.get('dimension', 0),
                'index_fullness': stats.get('index_fullness', 0),
                'namespaces': stats.get('namespaces', {})
            }
            
        except Exception as e:
            logging.error(f"Pinecone Stats abrufen fehlgeschlagen: {e}")
            return {}
    
    def create_collection(self, collection_name: str, dimension: int = 1536) -> bool:
        try:
            # In Pinecone werden "Collections" als separate Indices verwaltet
            if collection_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=collection_name,
                    dimension=dimension,
                    metric=self.metric
                )
                return True
            return False
            
        except Exception as e:
            logging.error(f"Pinecone Create Collection fehlgeschlagen: {e}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        try:
            if collection_name in pinecone.list_indexes():
                pinecone.delete_index(collection_name)
                return True
            return False
            
        except Exception as e:
            logging.error(f"Pinecone Delete Collection fehlgeschlagen: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        try:
            return pinecone.list_indexes()
            
        except Exception as e:
            logging.error(f"Pinecone List Collections fehlgeschlagen: {e}")
            return []
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadatas: List[Dict], ids: List[str]) -> bool:
        """
        Fügt Dokumente mit beliebigen Metadaten (inkl. Relationen, Kontext, Tags) hinzu.
        """
        try:
            # Annahme: self.client.upsert unterstützt Dict-Metadaten
            for doc, meta, doc_id in zip(documents, metadatas, ids):
                self.client.upsert({
                    "collection": collection_name,
                    "document": doc,
                    "metadata": meta,
                    "id": doc_id
                })
            return True
        except Exception as e:
            logging.error(f"Fehler beim Hinzufügen von Dokumenten: {e}")
            return False
    
    def add_vector(self, vector_id: str, vector: List[float], metadata: Dict = None) -> bool:
        """Füge einen einzelnen Vektor hinzu"""
        try:
            if not self.index:
                return False
            
            vector_data = {
                'id': vector_id,
                'values': vector,
                'metadata': metadata or {}
            }
            
            self.index.upsert(vectors=[vector_data])
            return True
            
        except Exception as e:
            logging.error(f"Pinecone Vektor hinzufügen fehlgeschlagen: {e}")
            return False
    
    def search_similar(self, collection_name: str, query: str, 
                      n_results: int = 5) -> List[Dict]:
        """Suche ähnliche Dokumente (vereinfacht - benötigt Query-Embedding)"""
        try:
            if not self.index:
                return []
            
            # Placeholder: Hier müsste der Query-String in einen Vektor umgewandelt werden
            # Als Fallback verwende ich einen Null-Vektor
            query_vector = [0.0] * self.dimension
            
            results = self.index.query(
                vector=query_vector,
                top_k=n_results,
                include_values=True,
                include_metadata=True
            )
            
            formatted_results = []
            for match in results.get('matches', []):
                formatted_results.append({
                    'id': match['id'],
                    'score': match['score'],
                    'metadata': match.get('metadata', {}),
                    'document': match.get('metadata', {}).get('document', '')
                })
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Pinecone Suche fehlgeschlagen: {e}")
            return []
    
    def add_document_with_strategy(self, document_id: str, vector: List[float], 
                                  content: str, metadata: Dict = None) -> bool:
        """Füge Document mit der neuen Unified Strategy hinzu"""
        try:
            # Erstelle Properties mit der Strategy
            base_metadata = metadata or {}
            base_metadata['id'] = document_id
            base_metadata['content'] = content[:500]  # Pinecone Metadaten-Limit
            
            validated_metadata = self.strategy.validate_node_properties("Document", base_metadata)
            
            # Bereite für Pinecone auf (nur primitive Datentypen)
            clean_metadata = {}
            for key, value in validated_metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    if isinstance(value, str) and len(value) > 1000:
                        clean_metadata[key] = value[:1000]  # Pinecone Limit
                    else:
                        clean_metadata[key] = value
            
            return self.add_vector(document_id, vector, clean_metadata)
            
        except Exception as e:
            logger.error(f"Document mit Strategy hinzufügen fehlgeschlagen: {e}")
            return False
    
    def add_chunk_with_strategy(self, document_id: str, chunk_index: int, 
                               vector: List[float], content: str, metadata: Dict = None) -> bool:
        """Füge DocumentChunk mit der neuen Unified Strategy hinzu"""
        try:
            # Generiere Chunk ID und Properties
            chunk_id = self.strategy.generate_chunk_id(document_id, chunk_index)
            chunk_props = self.strategy.create_chunk_properties(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content[:500],  # Pinecone Metadaten-Limit
                **(metadata or {})
            )
            
            # Bereite für Pinecone auf
            clean_metadata = {}
            for key, value in chunk_props.items():
                if isinstance(value, (str, int, float, bool)):
                    if isinstance(value, str) and len(value) > 1000:
                        clean_metadata[key] = value[:1000]
                    else:
                        clean_metadata[key] = value
            
            return self.add_vector(chunk_id, vector, clean_metadata)
            
        except Exception as e:
            logger.error(f"Chunk mit Strategy hinzufügen fehlgeschlagen: {e}")
            return False


def get_backend_class():
    """Factory-Funktion für Pinecone Backend"""
    return PineconeVectorBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_pinecone"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...vnpl9C4="  # Gekuerzt fuer Sicherheit
module_organization_key = "706cc5364169edb3fc8ac55d65e6d558bccbede27de1f8ca56c1cab5be7b345c"
module_file_key = "e9c44b11710bd80c4f7a4c4ea762ac72132e25f289b2442ab45f6cfe30bcc23b"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
