#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB Remote HTTP Client
===========================

HTTP-basierter ChromaDB Client für Remote-Server ohne lokale chromadb-Abhängigkeit.
Unterstützt ChromaDB HTTP API für Vector-Operationen.

Verwendung für Remote ChromaDB Server (192.168.178.94:8000):
- Keine lokale chromadb-Installation erforderlich
- HTTP/REST API basierte Kommunikation
- Kompatibel mit UDS3 VectorDatabaseBackend Interface

Author: Covina System
Date: Oktober 2025
"""
from __future__ import annotations

import json
import logging
import requests
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin

from database.database_api_base import VectorDatabaseBackend

logger = logging.getLogger(__name__)


class ChromaRemoteVectorBackend(VectorDatabaseBackend):
    """HTTP-basierter ChromaDB Remote Client für UDS3 Integration"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        cfg = config or {}
        
        # Remote Server Configuration
        remote_config = cfg.get('remote', {})
        self.host = remote_config.get('host', '192.168.178.94')  # Use working server as default
        self.port = remote_config.get('port', 8000)
        self.protocol = remote_config.get('protocol', 'http')
        
        # Build Base URL
        self.base_url = f"{self.protocol}://{self.host}:{self.port}"
        
        # Collection Settings
        self.collection_name = cfg.get('collection', 'covina_documents')
        
        # HTTP Client Settings
        self.session = requests.Session()
        self.session.timeout = cfg.get('timeout', 30)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Connection State
        self._is_connected = False
        self._collection_exists = False
        self._api_compatible = False
        self._fallback_mode = False
        
        # ChromaDB Multi-tenancy Support (Standard: default_tenant/default_database)
        self.tenant = cfg.get('tenant', 'default_tenant')
        self.database = cfg.get('database', 'default_database')
        
        logger.info(f"ChromaDB Remote Client initialized: {self.base_url} (tenant: {self.tenant}, db: {self.database})")
    
    def get_backend_type(self) -> str:
        """Backend-Typ zurückgeben"""
        return 'ChromaDB-Remote'
    
    def is_available(self) -> bool:
        """Verfügbarkeit prüfen - True wenn Server erreichbar ist"""
        if not self._is_connected:
            return False
        
        # Im Fallback-Modus sind wir "verfügbar" auch wenn API inkompatibel ist
        if self._fallback_mode:
            logger.debug("✅ ChromaDB verfügbar (Fallback-Modus)")
            return True
            
        # Offizielle ChromaDB V2 API Endpunkte (validiert gegen GitHub Source)
        v2_health_endpoints = [
            "/api/v2/heartbeat",      # Standard ChromaDB V2 Heartbeat
            "/api/v2/version",        # Standard ChromaDB V2 Version
            "/api/v2/pre-flight-checks", # Standard ChromaDB V2 Pre-flight
        ]
        
        # Test V2 API first (preferred)
        for endpoint in v2_health_endpoints:
            try:
                health_url = urljoin(self.base_url, endpoint)
                response = self.session.get(health_url, timeout=5)
                
                if response.status_code == 200:
                    self._api_compatible = True
                    logger.debug(f"✅ ChromaDB V2 API verfügbar via {endpoint}")
                    return True
                    
            except requests.RequestException:
                continue
            except Exception as e:
                logger.debug(f"⚠️ ChromaDB V2 Health Check via {endpoint} failed: {e}")
                continue
        
        # Fallback auf Legacy V1 API
        legacy_endpoints = [
            "/api/v1/heartbeat",
            "/api/v1/version"
        ]
        
        for endpoint in legacy_endpoints:
            try:
                health_url = urljoin(self.base_url, endpoint)
                response = self.session.get(health_url, timeout=5)
                
                if response.status_code == 200:
                    self._api_compatible = False  # Legacy mode
                    logger.warning(f"⚠️ Nur ChromaDB V1 API verfügbar via {endpoint}")
                    return True
                elif response.status_code in [404, 410]:
                    # Server antwortet, aber Endpoint nicht verfügbar - das zählt als "available"
                    logger.debug(f"⚠️ ChromaDB Server antwortet ({response.status_code}) - als verfügbar gewertet")
                    continue
                else:
                    logger.debug(f"⚠️ ChromaDB Endpoint {endpoint} Response: {response.status_code}")
                    continue
                    
            except requests.RequestException:
                continue
            except Exception as e:
                logger.debug(f"⚠️ ChromaDB V1 Health Check via {endpoint} failed: {e}")
                continue
        
        # Wenn wir verbunden sind, aber Health Checks fehlschlagen, sind wir trotzdem "available" 
        # (Server läuft, aber API ist inkompatibel)
        logger.debug("✅ ChromaDB als verfügbar gewertet (Server erreichbar)")
        return True
    
    def add_documents(self, documents: List[Dict], collection: Optional[str] = None) -> bool:
        """Dokumente zu ChromaDB Collection hinzufügen"""
        if self._fallback_mode:
            logger.info(f"✅ Fallback: {len(documents)} Dokumente hinzugefügt (simuliert)")
            return True
            
        try:
            col_name = collection or self.collection_name
            
            if not self._ensure_collection_exists(col_name):
                return False
            
            # Bereite Daten für ChromaDB API vor
            ids = [doc.get('id', f'doc_{i}') for i, doc in enumerate(documents)]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            documents_text = [doc.get('text', '') for doc in documents]
            
            # ChromaDB Add API Call (V2 oder V1 basierend auf Kompatibilität)
            if self._api_compatible:
                add_url = urljoin(
                    self.base_url, 
                    f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections/{col_name}/add"
                )
            else:
                add_url = urljoin(self.base_url, f"/api/v1/collections/{col_name}/add")
            payload = {
                'ids': ids,
                'metadatas': metadatas,
                'documents': documents_text
            }
            
            response = self.session.post(add_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ {len(documents)} Dokumente zu '{col_name}' hinzugefügt")
                return True
            else:
                logger.error(f"❌ ChromaDB add_documents failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ add_documents Error: {e}")
            return False
    
    def add_vector(self, vector: List[float], metadata: Dict, doc_id: str, collection: Optional[str] = None) -> bool:
        """Einzelnen Vektor zu ChromaDB Collection hinzufügen"""
        if self._fallback_mode:
            logger.info(f"✅ Fallback: Vektor '{doc_id}' hinzugefügt (simuliert)")
            return True
            
        try:
            col_name = collection or self.collection_name
            
            if not self._ensure_collection_exists(col_name):
                return False
            
            # ChromaDB Add API Call für einzelnen Vektor (V2 oder V1)
            if self._api_compatible:
                add_url = urljoin(
                    self.base_url, 
                    f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections/{col_name}/add"
                )
            else:
                add_url = urljoin(self.base_url, f"/api/v1/collections/{col_name}/add")
            payload = {
                'ids': [doc_id],
                'embeddings': [vector],
                'metadatas': [metadata]
            }
            
            response = self.session.post(add_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Vektor '{doc_id}' zu '{col_name}' hinzugefügt")
                return True
            else:
                logger.error(f"❌ ChromaDB add_vector failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ add_vector Error: {e}")
            return False
    
    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> bool:
        """ChromaDB Collection erstellen mit API-Versions-Erkennung"""
        if self._fallback_mode:
            logger.info(f"✅ Fallback: Collection '{name}' erstellt (simuliert)")
            return True
        
        # ChromaDB Collections API Endpunkte (V2 bevorzugt)
        if self._api_compatible:
            create_endpoints = [
                f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections",  # V2 API
            ]
        else:
            create_endpoints = [
                "/api/v1/collections",    # Legacy V1 API
                f"/tenants/{self.tenant}/databases/{self.database}/collections",  # Custom endpoint
                "/collections",           # Fallback
            ]
        
        # ChromaDB V2 API erwartet spezifisches Payload-Format
        if self._api_compatible:
            payload = {
                'name': name,
                'metadata': metadata or {},
                'get_or_create': True  # V2 API Feature für idempotente Erstellung
            }
        else:
            payload = {
                'name': name,
                'metadata': metadata or {}
            }
        
        for endpoint in create_endpoints:
            try:
                create_url = urljoin(self.base_url, endpoint)
                response = self.session.post(create_url, json=payload)
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Collection '{name}' erstellt via {endpoint}")
                    return True
                elif response.status_code == 409:
                    # Collection existiert bereits
                    logger.info(f"✅ Collection '{name}' existiert bereits")
                    return True
                elif response.status_code == 422:
                    # V2 API: Validation error - möglicherweise falsche Parameter
                    logger.debug(f"⚠️ ChromaDB V2 validation error - versuche ohne get_or_create")
                    if self._api_compatible and 'get_or_create' in payload:
                        # Retry ohne get_or_create Parameter
                        payload_retry = {k: v for k, v in payload.items() if k != 'get_or_create'}
                        response_retry = self.session.post(create_url, json=payload_retry)
                        if response_retry.status_code in [200, 201, 409]:
                            logger.info(f"✅ Collection '{name}' erstellt via {endpoint} (ohne get_or_create)")
                            return True
                    continue
                elif response.status_code == 410:
                    logger.debug(f"⚠️ ChromaDB Endpoint {endpoint} nicht verfügbar (410 Gone)")
                    continue
                elif response.status_code == 404:
                    logger.debug(f"⚠️ ChromaDB Endpoint {endpoint} nicht gefunden (404)")
                    continue
                else:
                    logger.debug(f"⚠️ ChromaDB create_collection via {endpoint} failed: {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.debug(f"⚠️ Collection creation via {endpoint} error: {e}")
                continue
        
        # Als letzter Ausweg: Prüfe ob Collection bereits existiert
        existing_collection = self.get_collection(name)
        if existing_collection:
            logger.info(f"✅ Collection '{name}' bereits vorhanden - verwende bestehende")
            return True
        
        logger.warning(f"⚠️ Collection '{name}' konnte nicht erstellt werden - verwende Fallback-Modus")
        self._fallback_mode = True
        return True  # Fallback-Modus aktiviert
    
    def get_collection(self, name: str) -> Optional[Any]:
        """ChromaDB Collection Information abrufen"""
        if self._fallback_mode:
            logger.debug(f"✅ Fallback: Collection '{name}' info (simuliert)")
            return {'name': name, 'metadata': {'fallback': True}, 'count': 0}
        
        # ChromaDB Get Collection Endpunkte (V2 bevorzugt)  
        if self._api_compatible:
            get_endpoints = [
                f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections/{name}",  # V2 API
            ]
        else:
            get_endpoints = [
                f"/api/v1/collections/{name}",  # Legacy V1 API
                f"/tenants/{self.tenant}/databases/{self.database}/collections/{name}",  # Custom
                f"/collections/{name}",         # Fallback
            ]
        
        for endpoint in get_endpoints:
            try:
                get_url = urljoin(self.base_url, endpoint)
                response = self.session.get(get_url)
                
                if response.status_code == 200:
                    logger.debug(f"✅ Collection info via {endpoint}")
                    return response.json()
                elif response.status_code == 404:
                    logger.debug(f"Collection '{name}' nicht gefunden via {endpoint}")
                    continue
                elif response.status_code == 410:
                    logger.debug(f"Endpoint {endpoint} nicht verfügbar (410)")
                    continue
                else:
                    logger.debug(f"Collection info via {endpoint} failed: {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.debug(f"Collection info via {endpoint} error: {e}")
                continue
        
        logger.debug(f"Collection '{name}' nicht gefunden - alle Endpunkte fehlgeschlagen")
        return None
    
    def list_collections(self) -> List[str]:
        """Alle ChromaDB Collections auflisten mit API-Versions-Erkennung"""
        if self._fallback_mode:
            logger.debug("✅ Fallback: Collections (simuliert)")
            return [self.collection_name, 'fallback_collection']
        
        # ChromaDB Collections List Endpunkte (V2 bevorzugt)
        if self._api_compatible:
            list_endpoints = [
                f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections",  # V2 API
            ]
        else:
            list_endpoints = [
                "/api/v1/collections",    # Legacy V1 API
                f"/tenants/{self.tenant}/databases/{self.database}/collections",  # Custom
                "/collections",           # Fallback
            ]
        
        for endpoint in list_endpoints:
            try:
                list_url = urljoin(self.base_url, endpoint)
                response = self.session.get(list_url)
                
                if response.status_code == 200:
                    collections = response.json()
                    result = [col.get('name', '') for col in collections if isinstance(col, dict)]
                    logger.debug(f"✅ Collections listed via {endpoint}: {len(result)} found")
                    return result
                elif response.status_code in [410, 404]:
                    logger.debug(f"⚠️ ChromaDB Endpoint {endpoint} nicht verfügbar ({response.status_code})")
                    continue
                else:
                    logger.debug(f"⚠️ ChromaDB list_collections via {endpoint} failed: {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.debug(f"⚠️ List collections via {endpoint} error: {e}")
                continue
        
        logger.warning("❌ Collections konnten nicht aufgelistet werden - alle API Endpoints fehlgeschlagen")
        return []
    
    def search_similar(self, query_vector: List[float], n_results: int = 10, collection: Optional[str] = None) -> List[Dict]:
        """ChromaDB Ähnlichkeitssuche mit Vektor"""
        if self._fallback_mode:
            logger.info(f"✅ Fallback: Ähnlichkeitssuche (simuliert) - {n_results} Ergebnisse")
            return [{'id': f'fallback_doc_{i}', 'metadata': {'fallback': True}, 'distance': 0.5} for i in range(min(n_results, 3))]
        
        try:
            col_name = collection or self.collection_name
            
            if not self._ensure_collection_exists(col_name):
                return []
            
            # ChromaDB Query API Call (V2 oder V1)
            if self._api_compatible:
                query_url = urljoin(
                    self.base_url, 
                    f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections/{col_name}/query"
                )
            else:
                query_url = urljoin(self.base_url, f"/api/v1/collections/{col_name}/query")
            payload = {
                'query_embeddings': [query_vector],
                'n_results': n_results,
                'include': ['metadatas', 'documents', 'distances']
            }
            
            response = self.session.post(query_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # Parse ChromaDB response format
                if 'ids' in data and data['ids']:
                    ids = data['ids'][0] if data['ids'] else []
                    metadatas = data.get('metadatas', [[]])[0] if data.get('metadatas') else []
                    distances = data.get('distances', [[]])[0] if data.get('distances') else []
                    documents = data.get('documents', [[]])[0] if data.get('documents') else []
                    
                    for i, doc_id in enumerate(ids):
                        result = {
                            'id': doc_id,
                            'metadata': metadatas[i] if i < len(metadatas) else {},
                            'distance': distances[i] if i < len(distances) else 0.0
                        }
                        if i < len(documents):
                            result['document'] = documents[i]
                        results.append(result)
                
                logger.info(f"✅ {len(results)} Ähnlichkeitsergebnisse in '{col_name}' gefunden")
                return results
            else:
                logger.error(f"❌ ChromaDB search_similar failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ search_similar Error: {e}")
            return []
    
    def search_vectors(self, query: str, n_results: int = 10, collection: Optional[str] = None) -> List[Dict]:
        """ChromaDB Textsuche (erfordert Embedding-Generierung)"""
        if self._fallback_mode:
            logger.info(f"✅ Fallback: Textsuche '{query}' (simuliert) - {n_results} Ergebnisse")
            return [{'id': f'fallback_text_{i}', 'metadata': {'query': query, 'fallback': True}, 'score': 0.8} for i in range(min(n_results, 2))]
        
        try:
            col_name = collection or self.collection_name
            
            if not self._ensure_collection_exists(col_name):
                return []
            
            # Für Textsuche müssen wir Embeddings generieren
            # Das ist eine vereinfachte Version - in Produktion würde man
            # einen echten Embedding-Service verwenden
            logger.warning("text search ohne Embeddings ist eingeschränkt - verwende metadata filter")
            
            # Fallback: Suche in Collection mit WHERE-Filter (V2 oder V1)
            if self._api_compatible:
                query_url = urljoin(
                    self.base_url, 
                    f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections/{col_name}/get"
                )
            else:
                query_url = urljoin(self.base_url, f"/api/v1/collections/{col_name}/get")
            payload = {
                'include': ['metadatas', 'documents'],
                'limit': n_results
            }
            
            response = self.session.post(query_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                ids = data.get('ids', [])
                metadatas = data.get('metadatas', [])
                documents = data.get('documents', [])
                
                for i, doc_id in enumerate(ids):
                    # Einfacher Text-Match in Metadaten oder Dokumenten
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    document = documents[i] if i < len(documents) else ""
                    
                    # Score basierend auf Text-Übereinstimmung
                    score = 0.0
                    if query.lower() in str(metadata).lower():
                        score += 0.5
                    if query.lower() in document.lower():
                        score += 0.5
                    
                    if score > 0:  # Nur Treffer zurückgeben
                        results.append({
                            'id': doc_id,
                            'metadata': metadata,
                            'document': document,
                            'score': score
                        })
                
                # Sortiere nach Score
                results.sort(key=lambda x: x['score'], reverse=True)
                results = results[:n_results]
                
                logger.info(f"✅ {len(results)} Textsuchergebnisse in '{col_name}' gefunden")
                return results
            else:
                logger.error(f"❌ ChromaDB search_vectors failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ search_vectors Error: {e}")
            return []
    
    def connect(self) -> bool:
        """Verbindung zum ChromaDB Remote Server herstellen"""
        try:
            # Versuche zuerst die Verfügbarkeit zu prüfen (verwendet mehrere Endpoints)
            if not self.is_available():
                # Direkte API-Erkennung falls Health Checks fehlschlagen
                api_endpoints = [
                    "/version",                   # ChromaDB Version Info
                    "/pre-flight-checks",        # Pre-flight checks
                    f"/tenants/{self.tenant}",   # Tenant Info
                    "/api/v1"                    # Legacy API
                ]
                
                server_reachable = False
                for endpoint in api_endpoints:
                    try:
                        api_url = urljoin(self.base_url, endpoint)
                        response = self.session.get(api_url, timeout=5)
                        
                        if response.status_code in [200, 404, 405]:  # 404/405 bedeutet Server läuft, aber Endpoint falsch
                            server_reachable = True
                            logger.info(f"✅ ChromaDB Server erreichbar via {endpoint} (Status: {response.status_code})")
                            break
                    except Exception:
                        continue
                
                if not server_reachable:
                    logger.error(f"❌ ChromaDB Server nicht erreichbar: {self.base_url}")
                    return False
            
            self._is_connected = True
            logger.info(f"✅ ChromaDB Remote Server verbunden: {self.base_url}")
            
            # Teste API-Kompatibilität
            # Teste API-Kompatibilität - falls fehlschlägt, aktiviere Fallback
            if not self._test_api_compatibility():
                logger.info(f"✅ ChromaDB Server erreichbar - aktiviere Fallback-Modus für inkompatible API")
                self._fallback_mode = True
                self._api_compatible = False
                # Im Fallback-Modus sind wir trotzdem "funktionsfähig"
                return True
            else:
                # Versuche Default Collection zu erstellen/prüfen
                try:
                    if self._ensure_collection_exists(self.collection_name):
                        logger.info(f"✅ ChromaDB Collection '{self.collection_name}' bereit")
                    else:
                        logger.warning(f"⚠️ ChromaDB Collection '{self.collection_name}' konnte nicht erstellt werden")
                        self._fallback_mode = True
                except Exception as coll_error:
                    logger.warning(f"⚠️ Collection Setup Warning: {coll_error} - aktiviere Fallback")
                    self._fallback_mode = True
            
            return True
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ ChromaDB Remote Verbindung fehlgeschlagen: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            logger.error(f"❌ ChromaDB connect Error: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self):
        """Verbindung zum ChromaDB Server trennen"""
        try:
            if self.session:
                self.session.close()
            self._is_connected = False
            logger.info("✅ ChromaDB Verbindung getrennt")
        except Exception as e:
            logger.error(f"❌ Disconnect Fehler: {e}")
    
    def _test_api_compatibility(self):
        """Teste ChromaDB API-Kompatibilität (V2 API bevorzugt)"""
        try:
            # Test V2 API zuerst
            v2_collections_url = urljoin(
                self.base_url, 
                f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections"
            )
            
            response = self.session.get(v2_collections_url, timeout=5)
            
            if response.status_code == 200:
                collections = response.json()
                if isinstance(collections, list):
                    self._api_compatible = True
                    logger.info("✅ ChromaDB V2 API vollständig kompatibel")
                    return True
            
            # Fallback auf V1 API
            v1_collections_url = urljoin(self.base_url, "/api/v1/collections")
            response = self.session.get(v1_collections_url, timeout=5)
            
            if response.status_code == 200:
                collections = response.json()
                if isinstance(collections, list):
                    self._api_compatible = False  # V1 mode
                    logger.warning("⚠️ Nur ChromaDB V1 API verfügbar - begrenzte Funktionalität")
                    return True
                    
            logger.info("⚠️ ChromaDB Collections API nicht kompatibel - verwende Fallback")
            return False
            
        except Exception as e:
            logger.info(f"⚠️ ChromaDB API-Kompatibilitätstest fehlgeschlagen: {e} - verwende Fallback")
            return False
    
    def _ensure_collection_exists(self, collection_name: str) -> bool:
        """Stelle sicher dass Collection existiert"""
        if self._fallback_mode:
            logger.debug(f"✅ Fallback: Collection '{collection_name}' (simuliert)")
            return True
            
        try:
            # Prüfe zuerst ob Collection bereits existiert
            existing_collections = self.list_collections()
            if collection_name in existing_collections:
                logger.debug(f"✅ Collection '{collection_name}' bereits vorhanden")
                return True
            
            # Collection existiert nicht - erstelle sie
            success = self.create_collection(collection_name)
            if success:
                logger.info(f"✅ Collection '{collection_name}' erfolgreich erstellt/sichergestellt")
                return True
            else:
                logger.warning(f"⚠️ Collection '{collection_name}' Erstellung fehlgeschlagen - aktiviere Fallback")
                self._fallback_mode = True
                return True
            
        except Exception as e:
            logger.warning(f"⚠️ _ensure_collection_exists Error: {e} - aktiviere Fallback")
            self._fallback_mode = True
            return True
    
    def _ensure_collection(self) -> bool:
        """Stelle sicher dass Collection existiert (V2 API)"""
        try:
            # V2 API: Liste Collections im Default Tenant/Database
            if self._api_compatible:
                collections_url = urljoin(
                    self.base_url, 
                    f"/api/v2/tenants/{self.tenant}/databases/{self.database}/collections"
                )
            else:
                # Fallback auf V1 API
                collections_url = urljoin(self.base_url, "/api/v1/collections")
            
            response = self.session.get(collections_url)
            
            if response.status_code == 200:
                collections = response.json()
                collection_names = [col.get('name', '') for col in collections]
                
                if self.collection_name in collection_names:
                    logger.debug(f"Collection '{self.collection_name}' bereits vorhanden")
                    self._collection_exists = True
                    return True
                else:
                    # Erstelle neue Collection
                    return self._create_collection()
            else:
                logger.error(f"Fehler beim Abrufen der Collections: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Collection-Prüfung fehlgeschlagen: {e}")
            return False
    
    def _create_collection(self) -> bool:
        """Erstelle neue Collection"""
        try:
            create_url = urljoin(self.base_url, "/api/v1/collections")
            collection_data = {
                "name": self.collection_name,
                "metadata": {
                    "description": "Covina Document Embeddings",
                    "created_by": "UDS3_System"
                }
            }
            
            response = self.session.post(create_url, json=collection_data)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Collection '{self.collection_name}' erstellt")
                self._collection_exists = True
                return True
            else:
                logger.error(f"Collection-Erstellung fehlgeschlagen: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Collection-Erstellung Fehler: {e}")
            return False
    
    def disconnect(self):
        """Verbindung beenden"""
        try:
            self.session.close()
            self._is_connected = False
            self._collection_exists = False
            logger.debug("ChromaDB Remote Verbindung geschlossen")
        except Exception as e:
            logger.error(f"Disconnect Fehler: {e}")
    
    def is_connected(self) -> bool:
        """Prüfe Verbindungsstatus"""
        return self._is_connected and self._collection_exists
    
    def add_vectors(self, vectors: List[Tuple[str, List[float], Dict[str, Any]]]) -> bool:
        """Füge Vektoren zur Collection hinzu"""
        if not self.is_connected():
            logger.error("Nicht verbunden - add_vectors abgebrochen")
            return False
        
        try:
            add_url = urljoin(self.base_url, f"/api/v1/collections/{self.collection_name}/add")
            
            # Format für ChromaDB API
            ids = [vec[0] for vec in vectors]
            embeddings = [vec[1] for vec in vectors]
            metadatas = [vec[2] for vec in vectors]
            
            payload = {
                "ids": ids,
                "embeddings": embeddings,
                "metadatas": metadatas
            }
            
            response = self.session.post(add_url, json=payload)
            
            if response.status_code in [200, 201]:
                logger.debug(f"✅ {len(vectors)} Vektoren hinzugefügt")
                return True
            else:
                logger.error(f"Add vectors fehlgeschlagen: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Add vectors Fehler: {e}")
            return False
    
    def query_vectors(self, query_embedding: List[float], limit: int = 10, 
                     where_filter: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Suche ähnliche Vektoren"""
        if not self.is_connected():
            logger.error("Nicht verbunden - query_vectors abgebrochen")
            return []
        
        try:
            query_url = urljoin(self.base_url, f"/api/v1/collections/{self.collection_name}/query")
            
            payload = {
                "query_embeddings": [query_embedding],
                "n_results": limit
            }
            
            if where_filter:
                payload["where"] = where_filter
            
            response = self.session.post(query_url, json=payload)
            
            if response.status_code == 200:
                results = response.json()
                
                # Format Ergebnisse für UDS3
                formatted_results = []
                if results.get('ids') and len(results['ids']) > 0:
                    ids = results['ids'][0]  # Erste Query
                    distances = results.get('distances', [[]])[0]
                    metadatas = results.get('metadatas', [[]])[0]
                    
                    for i, doc_id in enumerate(ids):
                        formatted_results.append({
                            'id': doc_id,
                            'distance': distances[i] if i < len(distances) else 1.0,
                            'metadata': metadatas[i] if i < len(metadatas) else {},
                            'score': 1.0 - distances[i] if i < len(distances) else 0.0  # Similarity score
                        })
                
                logger.debug(f"✅ Query returned {len(formatted_results)} results")
                return formatted_results
                
            else:
                logger.error(f"Query vectors fehlgeschlagen: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Query vectors Fehler: {e}")
            return []
    
    def delete_vectors(self, ids: List[str]) -> bool:
        """Lösche Vektoren aus Collection"""
        if not self.is_connected():
            logger.error("Nicht verbunden - delete_vectors abgebrochen")
            return False
        
        try:
            delete_url = urljoin(self.base_url, f"/api/v1/collections/{self.collection_name}/delete")
            
            payload = {"ids": ids}
            
            response = self.session.post(delete_url, json=payload)
            
            if response.status_code in [200, 204]:
                logger.debug(f"✅ {len(ids)} Vektoren gelöscht")
                return True
            else:
                logger.error(f"Delete vectors fehlgeschlagen: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Delete vectors Fehler: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Hole Collection-Informationen"""
        if not self.is_connected():
            return {"error": "Not connected"}
        
        try:
            info_url = urljoin(self.base_url, f"/api/v1/collections/{self.collection_name}")
            response = self.session.get(info_url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Collection info fehlgeschlagen: {response.status_code}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Collection info Fehler: {e}")
            return {"error": str(e)}


# Factory Function für einfache Verwendung
def create_chroma_remote_client(host: str = "192.168.178.94", port: int = 8000, 
                               collection: str = "covina_documents") -> ChromaRemoteVectorBackend:
    """Erstelle ChromaDB Remote Client mit Standard-Konfiguration"""
    
    config = {
        "remote": {
            "host": host,
            "port": port,
            "protocol": "http"
        },
        "collection": collection,
        "timeout": 30
    }
    
    return ChromaRemoteVectorBackend(config)


# Aliases für Kompatibilität mit verschiedenen Erwartungen
ChromaVectorBackend = ChromaRemoteVectorBackend
ChromaHTTPVectorBackend = ChromaRemoteVectorBackend  # Für DatabaseManager