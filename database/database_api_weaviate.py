#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""



"""
Weaviate Vector Database Backend
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
    import weaviate
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

logger = logging.getLogger(__name__)


class WeaviateVectorBackend(VectorDatabaseBackend):
    """Weaviate Vector Database"""
    
    def __init__(self, config: Dict):
        if not WEAVIATE_AVAILABLE:
            logger.warning("Weaviate client not available at import time; connect() will fail if used")
        
        self.config = config
        self.url = config.get('url', 'http://localhost:8080')
        self.api_key = config.get('api_key')
        self.class_name = config.get('class_name', 'Document')
        self.client = None
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for Weaviate: {exc}")
            self.strategy = None
        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"Weaviate Backend initialisiert mit Strategie {strategy_version}")
        
    def connect(self) -> bool:
        try:
            if not WEAVIATE_AVAILABLE:
                logging.error("Weaviate client library not installed")
                return False
            auth_config = None
            if self.api_key:
                auth_config = weaviate.AuthApiKey(api_key=self.api_key)
            
            self.client = weaviate.Client(
                url=self.url,
                auth_client_secret=auth_config
            )
            
            # Test connection
            self.client.schema.get()
            
            # Standard-Klasse erstellen falls nicht vorhanden
            self._ensure_class_exists()
            
            logging.info(f"Weaviate verbunden: {self.url}")
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Verbindung fehlgeschlagen: {e}")
            return False
    
    def _ensure_class_exists(self):
        """Stelle sicher, dass die Standard-Klasse existiert"""
        try:
            existing_classes = self.client.schema.get()['classes']
            class_names = [cls['class'] for cls in existing_classes]
            
            if self.class_name not in class_names:
                class_schema = {
                    "class": self.class_name,
                    "description": "Standard document class for vector storage",
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The content of the document"
                        },
                        {
                            "name": "title",
                            "dataType": ["string"],
                            "description": "The title of the document"
                        },
                        {
                            "name": "source",
                            "dataType": ["string"],
                            "description": "The source of the document"
                        }
                    ],
                    "vectorizer": "none"  # Wir fügen Vektoren manuell hinzu
                }
                
                self.client.schema.create_class(class_schema)
                logging.info(f"Weaviate Klasse '{self.class_name}' erstellt")
                
        except Exception as e:
            logging.error(f"Weaviate Klasse erstellen fehlgeschlagen: {e}")
    
    def disconnect(self):
        self.client = None
    
    def is_available(self) -> bool:
        try:
            if self.client:
                self.client.schema.get()
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "Weaviate"
    
    def add_vectors(self, vectors: List[Dict]) -> bool:
        try:
            if not self.client:
                return False
            
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for vector in vectors:
                    properties = vector.get('metadata', {})
                    # Sicherstellen, dass Standard-Properties existieren
                    properties.setdefault('content', vector.get('content', ''))
                    properties.setdefault('title', vector.get('title', ''))
                    properties.setdefault('source', vector.get('source', ''))
                    
                    batch.add_data_object(
                        data_object=properties,
                        class_name=self.class_name,
                        uuid=vector['id'],
                        vector=vector['vector']
                    )
            
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Add Vectors fehlgeschlagen: {e}")
            return False
    
    def search_vectors(self, query_vector: List[float], top_k: int = 10, 
                      filters: Dict = None) -> List[Dict]:
        try:
            if not self.client:
                return []
            
            query = (
                self.client.query
                .get(self.class_name)
                .with_near_vector({"vector": query_vector})
                .with_limit(top_k)
                .with_additional(["distance", "id"])
            )
            
            # Filter hinzufügen falls vorhanden
            if filters:
                where_filter = self._build_where_filter(filters)
                if where_filter:
                    query = query.with_where(where_filter)
            
            response = query.do()
            
            results = []
            if 'data' in response and 'Get' in response['data']:
                objects = response['data']['Get'].get(self.class_name, [])
                
                for obj in objects:
                    additional = obj.get('_additional', {})
                    # Metadata ohne interne Felder
                    metadata = {k: v for k, v in obj.items() if not k.startswith('_')}
                    
                    results.append({
                        'id': additional.get('id', ''),
                        'score': 1.0 - additional.get('distance', 1.0),  # Distanz zu Score
                        'vector': [],  # Weaviate gibt Vektoren nicht standardmäßig zurück
                        'metadata': metadata
                    })
            
            return results
            
        except Exception as e:
            logging.error(f"Weaviate Search fehlgeschlagen: {e}")
            return []
    
    def _build_where_filter(self, filters: Dict) -> Optional[Dict]:
        """Erstelle Weaviate WHERE Filter aus Dict"""
        try:
            conditions = []
            
            for key, value in filters.items():
                condition = {
                    "path": [key],
                    "operator": "Equal",
                    "valueString": str(value)
                }
                conditions.append(condition)
            
            if len(conditions) == 1:
                return conditions[0]
            elif len(conditions) > 1:
                return {
                    "operator": "And",
                    "operands": conditions
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Weaviate Filter erstellen fehlgeschlagen: {e}")
            return None
    
    def get_vector(self, vector_id: str) -> Optional[Dict]:
        try:
            if not self.client:
                return None
            
            response = (
                self.client.query
                .get(self.class_name)
                .with_where({
                    "path": ["id"],
                    "operator": "Equal",
                    "valueString": vector_id
                })
                .with_additional(["id", "vector"])
                .do()
            )
            
            if 'data' in response and 'Get' in response['data']:
                objects = response['data']['Get'].get(self.class_name, [])
                
                if objects:
                    obj = objects[0]
                    additional = obj.get('_additional', {})
                    metadata = {k: v for k, v in obj.items() if not k.startswith('_')}
                    
                    return {
                        'id': vector_id,
                        'vector': additional.get('vector', []),
                        'metadata': metadata
                    }
            
            return None
            
        except Exception as e:
            logging.error(f"Weaviate Get Vector fehlgeschlagen: {e}")
            return None
    
    def update_vector(self, vector_id: str, vector: List[float] = None, 
                     metadata: Dict = None) -> bool:
        try:
            if not self.client:
                return False
            
            if metadata:
                self.client.data_object.update(
                    uuid=vector_id,
                    class_name=self.class_name,
                    data_object=metadata
                )
            
            if vector:
                self.client.data_object.update(
                    uuid=vector_id,
                    class_name=self.class_name,
                    vector=vector
                )
            
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Update Vector fehlgeschlagen: {e}")
            return False
    
    def delete_vectors(self, vector_ids: List[str]) -> bool:
        try:
            if not self.client:
                return False
            
            for vector_id in vector_ids:
                self.client.data_object.delete(
                    uuid=vector_id,
                    class_name=self.class_name
                )
            
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Delete Vectors fehlgeschlagen: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        try:
            if not self.client:
                return {}
            
            response = (
                self.client.query
                .aggregate(self.class_name)
                .with_meta_count()
                .do()
            )
            
            count = 0
            if 'data' in response and 'Aggregate' in response['data']:
                aggregate = response['data']['Aggregate'].get(self.class_name, [])
                if aggregate:
                    count = aggregate[0].get('meta', {}).get('count', 0)
            
            return {
                'total_vectors': count,
                'class_name': self.class_name
            }
            
        except Exception as e:
            logging.error(f"Weaviate Stats abrufen fehlgeschlagen: {e}")
            return {}
    
    def create_collection(self, collection_name: str, dimension: int = 1536) -> bool:
        try:
            if not self.client:
                return False
            
            class_schema = {
                "class": collection_name,
                "description": f"Collection {collection_name}",
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "The content"
                    }
                ],
                "vectorizer": "none"
            }
            
            self.client.schema.create_class(class_schema)
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Create Collection fehlgeschlagen: {e}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        try:
            if not self.client:
                return False
            
            self.client.schema.delete_class(collection_name)
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Delete Collection fehlgeschlagen: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        try:
            if not self.client:
                return []
            
            schema = self.client.schema.get()
            return [cls['class'] for cls in schema.get('classes', [])]
            
        except Exception as e:
            logging.error(f"Weaviate List Collections fehlgeschlagen: {e}")
            return []
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadatas: List[Dict], ids: List[str]) -> bool:
        """Füge Dokumente zur Weaviate Collection hinzu"""
        try:
            if not self.client:
                return False
            
            # Verwende collection_name als Klasse oder Standard-Klasse
            target_class = collection_name if collection_name in self.list_collections() else self.class_name
            
            # Batch-Import
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for doc_id, document, metadata in zip(ids, documents, metadatas):
                    properties = {
                        "content": document,
                        "title": metadata.get("title", "Untitled"),
                        "source": metadata.get("source", "Unknown")
                    }
                    
                    # Weitere Metadaten hinzufügen
                    for key, value in metadata.items():
                        if key not in ["content", "title", "source"] and isinstance(value, (str, int, float, bool)):
                            properties[key] = value
                    
                    batch.add_data_object(
                        data_object=properties,
                        class_name=target_class,
                        uuid=doc_id
                    )
            
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Dokumente hinzufügen fehlgeschlagen: {e}")
            return False
    
    def add_vector(self, vector_id: str, vector: List[float], metadata: Dict = None) -> bool:
        """Füge einen einzelnen Vektor hinzu"""
        try:
            if not self.client:
                return False
            
            metadata = metadata or {}
            
            properties = {
                "content": metadata.get("content", ""),
                "title": metadata.get("title", "Untitled"),
                "source": metadata.get("source", "Unknown")
            }
            
            # Weitere Metadaten hinzufügen
            for key, value in metadata.items():
                if key not in ["content", "title", "source"] and isinstance(value, (str, int, float, bool)):
                    properties[key] = value
            
            self.client.data_object.create(
                data_object=properties,
                class_name=self.class_name,
                uuid=vector_id,
                vector=vector
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Weaviate Vektor hinzufügen fehlgeschlagen: {e}")
            return False
    
    def search_similar(self, collection_name: str, query: str, 
                      n_results: int = 5) -> List[Dict]:
        """Suche ähnliche Dokumente"""
        try:
            if not self.client:
                return []
            
            # Verwende collection_name als Klasse oder Standard-Klasse
            target_class = collection_name if collection_name in self.list_collections() else self.class_name
            
            # Einfache Text-Suche (BM25)
            result = (
                self.client.query
                .get(target_class, ["content", "title", "source"])
                .with_bm25(query=query)
                .with_limit(n_results)
                .with_additional(["score"])
                .do()
            )
            
            formatted_results = []
            
            if 'data' in result and 'Get' in result['data']:
                objects = result['data']['Get'].get(target_class, [])
                
                for obj in objects:
                    formatted_results.append({
                        'document': obj.get('content', ''),
                        'metadata': {
                            'title': obj.get('title', ''),
                            'source': obj.get('source', '')
                        },
                        'score': obj.get('_additional', {}).get('score', 0)
                    })
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Weaviate Suche fehlgeschlagen: {e}")
            return []


def get_backend_class():
    """Factory-Funktion für Weaviate Backend"""
    return WeaviateVectorBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_weaviate"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "472409f7898c336ef90b4eb486db6a1f3c38211504bb13ed3e47ee0df4aeddb7"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
