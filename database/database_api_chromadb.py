#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""



"""
ChromaDB Vector Database Backend
"""

import logging
from typing import Dict, List, Optional, Any
from database.database_api_base import VectorDatabaseBackend
import inspect

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

# ChromaDB Import mit Fallback
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChromaVectorBackend(VectorDatabaseBackend):
    """ChromaDB Backend für Vektor-Operationen mit Adaptive Batch Processing"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.client = None
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8000)
        self.path = config.get('path', './chroma_db')
        # Mode handling: support 'persistent' (local) and 'server' (remote/service)
        raw_mode = (config.get('mode') or 'persistent').lower()
        # Normalize common aliases
        if raw_mode in ('http', 'server', 'remote', 'api'):
            self.mode = 'server'
        else:
            self.mode = 'persistent'

        # Initialize unified database strategy if available (import may have failed)
        if callable(get_unified_database_strategy):
            try:
                self.strategy = get_unified_database_strategy()
            except Exception:
                self.strategy = None
        else:
            self.strategy = None

        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"ChromaDB Backend initialisiert mit Strategie {strategy_version} (mode={self.mode})")
    
    def _backend_connect(self) -> bool:
        if not CHROMADB_AVAILABLE:
            logging.error("ChromaDB Python client nicht installiert")
            return False
            
        try:
            # Choose client type based on normalized mode
            if self.mode == 'server':
                # Allow either host/port or a full server_url in config
                server_url = self.config.get('server_url')
                if server_url:
                    logging.info(f"ChromaDB: connecting to server_url={server_url}")
                    # Some chroma client builds accept a URL argument; inspect HttpClient signature
                    HttpClient = getattr(chromadb, 'HttpClient', None)
                    if HttpClient is None:
                        raise RuntimeError('chromadb.HttpClient not available')

                    created = False
                    try:
                        # Log chromadb version if available
                        try:
                            version = getattr(chromadb, '__version__', None) or getattr(chromadb, 'version', None)
                            logging.info(f'ChromaDB client version detected: {version}')
                        except Exception:
                            logging.debug('Could not determine chromadb version')

                        sig = inspect.signature(HttpClient.__init__)
                        params = set(sig.parameters.keys())
                        # remove 'self'
                        params.discard('self')

                        # Prefer url/base_url if available
                        chosen = None
                        if 'url' in params:
                            self.client = HttpClient(url=server_url)
                            chosen = 'url'
                            created = True
                        elif 'base_url' in params:
                            self.client = HttpClient(base_url=server_url)
                            chosen = 'base_url'
                            created = True
                        elif 'host' in params and 'port' in params:
                            self.client = HttpClient(host=self.host, port=self.port)
                            chosen = 'host_port'
                            created = True
                        elif 'host' in params:
                            self.client = HttpClient(host=self.host)
                            chosen = 'host'
                            created = True
                        else:
                            # Last resort: try positional
                            try:
                                self.client = HttpClient(server_url)
                                chosen = 'positional'
                                created = True
                            except Exception:
                                created = False

                        logging.info(f'ChromaDB: HttpClient instantiated using strategy: {chosen}')
                    except Exception:
                        # If signature inspection fails, fall back to safe attempts
                        try:
                            self.client = HttpClient(host=self.host, port=self.port)
                            created = True
                        except Exception:
                            created = False

                    if not created:
                        raise RuntimeError('Could not instantiate chromadb.HttpClient with available signatures')
                    # If heartbeat fails, try adding common API prefix (/api/v2) and retry
                    try:
                        self.client.heartbeat()
                    except Exception:
                        # Try common prefix
                        prefixed = server_url.rstrip('/') + '/api/v2'
                        logging.info(f"ChromaDB: heartbeat failed, retrying with prefix {prefixed}")
                            # attempt to re-create client against the prefixed URL using same strategy
                        try:
                            HttpClient = getattr(chromadb, 'HttpClient', None)
                            recreated = False
                            try:
                                sig = inspect.signature(HttpClient.__init__)
                                params = set(sig.parameters.keys())
                                params.discard('self')
                                # Try same chosen strategy where possible
                                if chosen == 'url' and 'url' in params:
                                    self.client = HttpClient(url=prefixed)
                                    recreated = True
                                elif chosen == 'base_url' and 'base_url' in params:
                                    self.client = HttpClient(base_url=prefixed)
                                    recreated = True
                                elif chosen == 'host_port' and 'host' in params and 'port' in params:
                                    # host/port cannot express prefixed path; skip recreate
                                    recreated = False
                                elif 'url' in params:
                                    self.client = HttpClient(url=prefixed)
                                    recreated = True
                                elif 'base_url' in params:
                                    self.client = HttpClient(base_url=prefixed)
                                    recreated = True
                            except Exception:
                                recreated = False
                            if not recreated:
                                logging.debug('Could not recreate HttpClient for prefixed URL via signature-based attempt')
                        except Exception:
                            # fallback to previously constructed client
                            pass
                else:
                    logging.info(f"ChromaDB: connecting to host={self.host}, port={self.port}")
                    self.client = chromadb.HttpClient(host=self.host, port=self.port)
            else:
                # persistent/local mode
                logging.info(f"ChromaDB: opening persistent client at path={self.path}")
                self.client = chromadb.PersistentClient(
                    path=self.path,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            
            # Test connection
            self.client.heartbeat()
            logging.info(f"ChromaDB verbunden: {self.get_backend_type()}")
            return True
            
        except Exception as e:
            logging.error(f"ChromaDB Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        self.client = None
    
    def is_available(self) -> bool:
        try:
            if self.client:
                self.client.heartbeat()
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        mode = self.config.get('mode', 'persistent')
        return f"ChromaDB ({mode})"
    
    def create_collection(self, name: str, metadata: Dict = None) -> bool:
        try:
            # ChromaDB erfordert nicht-leere Metadaten für Collections
            if not metadata:
                metadata = {"created_by": "veritas_ingestion", "description": f"Collection {name}"}
            
            self.client.get_or_create_collection(
                name=name,
                metadata=metadata
            )
            return True
        except Exception as e:
            logging.error(f"ChromaDB Collection erstellen fehlgeschlagen: {e}")
            return False
    
    def get_collection(self, name: str):
        try:
            return self.client.get_collection(name)
        except Exception as e:
            logging.error(f"ChromaDB Collection abrufen fehlgeschlagen: {e}")
            return None
    
    def list_collections(self) -> List[str]:
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logging.error(f"ChromaDB Collections auflisten fehlgeschlagen: {e}")
            return []
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadatas: List[Dict], ids: List[str]) -> bool:
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return False
            
            # Filtere und bereinige Metadaten
            cleaned_metadatas = []
            for metadata in metadatas:
                cleaned = self._clean_metadata(metadata)
                cleaned_metadatas.append(cleaned)
            
            # WICHTIG: Erstelle explizit Embeddings mit dem korrekten Modell (all-minilm)
            # um Dimension-Mismatch zu vermeiden
            try:
                # Verwende direkte Ollama-Integration ohne LangChain
                import requests
                from database.config import EMBEDDING_MODEL, OLLAMA_HOST
                
                # Simple Ollama Embedding Wrapper (ohne LangChain)
                class SimpleOllamaEmbeddings:
                    def __init__(self, model=EMBEDDING_MODEL, base_url=OLLAMA_HOST):
                        self.model = model
                        self.base_url = base_url
                    
                    def embed_documents(self, texts):
                        embeddings = []
                        for text in texts:
                            try:
                                response = requests.post(f"{self.base_url}/api/embeddings", 
                                    json={"model": self.model, "prompt": text})
                                if response.status_code == 200:
                                    embeddings.append(response.json()["embedding"])
                                else:
                                    # Fallback: Zero-Embedding mit korrekter Dimension (384)
                                    embeddings.append([0.0] * 384)
                            except Exception:
                                embeddings.append([0.0] * 384)
                        return embeddings
                    
                    def embed_query(self, text):
                        return self.embed_documents([text])[0]
                
                embedding_model = SimpleOllamaEmbeddings()
                
                # Erstelle Embeddings für alle Dokumente
                embeddings = []
                for doc in documents:
                    embedding = embedding_model.embed_query(doc)
                    embeddings.append(embedding)
                
                # Füge Dokumente mit expliziten Embeddings hinzu
                collection.add(
                    documents=documents,
                    metadatas=cleaned_metadatas,
                    ids=ids,
                    embeddings=embeddings  # Explizite 384D Embeddings
                )
                
                logging.info(f"ChromaDB: {len(documents)} Dokumente mit {EMBEDDING_MODEL} ({len(embeddings[0])}D) hinzugefügt")
                
            except ImportError:
                # Fallback: ChromaDB automatische Embeddings (kann zu Dimension-Problemen führen)
                logging.warning("Langchain nicht verfügbar - verwende ChromaDB Standard-Embeddings")
                collection.add(
                    documents=documents,
                    metadatas=cleaned_metadatas,
                    ids=ids
                )
            
            return True
        except Exception as e:
            logging.error(f"ChromaDB Dokumente hinzufügen fehlgeschlagen: {e}")
            return False
    
    def add_vector(self, vector_id: str, vector: List[float], metadata: Dict = None) -> bool:
        """Füge einen einzelnen Vektor hinzu (ChromaDB-spezifische Implementierung)"""
        try:
            # Verwende Standard-Collection falls keine spezifiziert
            collection_name = metadata.get('collection', 'default') if metadata else 'default'
            
            # Collection erstellen falls nicht vorhanden
            self.create_collection(collection_name)
            collection = self.get_collection(collection_name)
            
            if not collection:
                logging.error(f"Collection '{collection_name}' konnte nicht erstellt/abgerufen werden")
                return False
            
            # Bereinige Metadaten
            cleaned_metadata = self._clean_metadata(metadata or {})
            
            # Dokumentinhalt aus Metadaten extrahieren oder Platzhalter verwenden
            document_text = cleaned_metadata.get('content', f"Vector document {vector_id}")
            
            collection.add(
                ids=[vector_id],
                embeddings=[vector],
                documents=[document_text],
                metadatas=[cleaned_metadata]
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Hinzufügen von Chunk {vector_id}: {e}")
            return False
    
    def add_document_with_strategy(self, collection_name: str, document_id: str, 
                                  content: str, metadata: Dict = None) -> bool:
        """Füge Dokument mit der neuen Unified Strategy hinzu"""
        try:
            # Erstelle Properties mit der ID
            base_metadata = metadata or {}
            base_metadata['id'] = document_id  # ID explizit setzen
            
            validated_metadata = self.strategy.validate_node_properties("Document", base_metadata)
            
            # Bereinige für ChromaDB
            clean_metadata = self._clean_metadata(validated_metadata)
            
            return self.add_documents(
                collection_name=collection_name,
                documents=[content],
                metadatas=[clean_metadata],
                ids=[document_id]
            )
            
        except Exception as e:
            logger.error(f"Dokument mit Strategy hinzufügen fehlgeschlagen: {e}")
            return False
    
    def add_chunk_with_strategy(self, collection_name: str, document_id: str, 
                               chunk_index: int, content: str, metadata: Dict = None) -> bool:
        """Füge DocumentChunk mit der neuen Unified Strategy hinzu"""
        try:
            # Generiere Chunk ID
            chunk_id = self.strategy.generate_chunk_id(document_id, chunk_index)
            
            # Erstelle Chunk Properties
            chunk_props = self.strategy.create_chunk_properties(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                **(metadata or {})
            )
            
            # Bereinige für ChromaDB
            clean_metadata = self._clean_metadata(chunk_props)
            
            return self.add_documents(
                collection_name=collection_name,
                documents=[content],
                metadatas=[clean_metadata],
                ids=[chunk_id]
            )
            
        except Exception as e:
            logger.error(f"Chunk mit Strategy hinzufügen fehlgeschlagen: {e}")
            return False

    def _clean_metadata(self, metadata: Dict) -> Dict:
        """Bereinigt Metadaten für ChromaDB-Kompatibilität"""
        if not metadata:
            return {"timestamp": "unknown"}
        
        cleaned = {}
        for key, value in metadata.items():
            # ChromaDB erlaubt nur bestimmte Datentypen in Metadaten
            if isinstance(value, (str, int, float, bool)):
                # Konvertiere sehr lange Strings zu kürzeren Versionen
                if isinstance(value, str) and len(value) > 500:
                    cleaned[key] = value[:500] + "..."
                else:
                    cleaned[key] = value
            elif isinstance(value, list):
                # Listen zu Strings konvertieren
                cleaned[key] = ", ".join(str(v) for v in value[:10])  # Maximal 10 Elemente
            elif value is None:
                cleaned[key] = "null"
            else:
                # Andere Typen zu String konvertieren
                cleaned[key] = str(value)[:500]
        
        # Mindestens ein Metadaten-Feld hinzufügen falls leer
        if not cleaned:
            cleaned["timestamp"] = "unknown"
            
        return cleaned
    
    def search_similar(self, collection_name: str, query: str, 
                      n_results: int = 5) -> List[Dict]:
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return []
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })
            
            return formatted_results
        except Exception as e:
            logging.error(f"ChromaDB Suche fehlgeschlagen: {e}")
            return []

    def search_vectors(self, query_vector: List[float], top_k: int = 10, 
                      collection_name: str = None) -> List[Dict]:
        """
        Sucht nach ähnlichen Vektoren in der ChromaDB.
        
        Args:
            query_vector: Der Abfrage-Vektor
            top_k: Anzahl der zurückzugebenden Ergebnisse
            collection_name: Name der Collection (optional, verwende erste verfügbare)
        
        Returns:
            Liste von Dictionaries mit Suchergebnissen
        """
        try:
            # Verwende angegebene Collection oder erste verfügbare
            if collection_name:
                collection = self.get_collection(collection_name)
            else:
                # Verwende erste verfügbare Collection
                collections = self.list_collections()
                if not collections:
                    logging.warning("ChromaDB: Keine Collections verfügbar für Vektorsuche")
                    return []
                collection = self.get_collection(collections[0])
            
            if not collection:
                logging.error(f"ChromaDB: Collection '{collection_name or 'erste verfügbare'}' nicht gefunden")
                return []
            
            # Führe Vektorsuche aus
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=top_k
            )
            
            # Formatiere Ergebnisse für einheitliche API
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] or {},
                    'score': 1.0 - results['distances'][0][i] if results.get('distances') else 1.0,  # ChromaDB gibt Distanzen zurück, konvertiere zu Scores
                    'distance': results['distances'][0][i] if results.get('distances') else 0.0
                }
                formatted_results.append(result)
            
            logging.info(f"ChromaDB Vektorsuche erfolgreich: {len(formatted_results)} Ergebnisse gefunden")
            return formatted_results
            
        except Exception as e:
            logging.error(f"ChromaDB Vektorsuche fehlgeschlagen: {e}")
            return []


def get_backend_class():
    """Factory-Funktion für ChromaDB Backend"""
    return ChromaVectorBackend if CHROMADB_AVAILABLE else None

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_chromadb"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "33ba904adab1e41ee829f6b3129daeee18f67bd94f75d9a167dba784a0798ce1"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
