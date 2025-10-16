#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Manager – verwaltet dynamisch geladene Backend-Instanzen

Die Backends werden über die zentrale Konfiguration (server_config.json) und die Factory-Methode
config.create_backend_instances_dynamisch() erzeugt. Die Basisklassen befinden sich in database_api_base.py,
die konkreten Implementierungen in den jeweiligen Backend-Modulen (z.B. database_api_chromadb.py).
Siehe auch: DATABASE_API_SUMMARY.md
"""

import logging
import importlib
import concurrent.futures
from typing import Dict, Optional, Union, List
from .database_api_base import (
    DatabaseBackend,
    VectorDatabaseBackend,
    GraphDatabaseBackend,
    RelationalDatabaseBackend,
)
import uuid
from .adapter_governance import AdapterGovernance, AdapterGovernanceError

# Module Status Manager Import
try:
    from module_status_manager import (
        ModuleStatusManager, ModuleStatus, ModuleType,
        register_module, update_status
    )
    STATUS_MANAGER_AVAILABLE = True
except ImportError:
    STATUS_MANAGER_AVAILABLE = False

# Einfache Registrierungs-Registry um Duplikate zu vermeiden
_REGISTERED_MODULES = set()

def safe_register_module(module_id, name, module_type, critical=True, dependencies=None):
    """Registriert Modul nur wenn noch nicht registriert"""
    global _REGISTERED_MODULES
    
    if module_id in _REGISTERED_MODULES:
        logging.debug(f"📊 {module_id} bereits registriert - überspringe Registrierung")
        return False  # Bereits registriert
    
    if STATUS_MANAGER_AVAILABLE:
        try:
            register_module(module_id, name, module_type, critical=critical, dependencies=dependencies)
            _REGISTERED_MODULES.add(module_id)
            return True  # Erfolgreich registriert
        except Exception as e:
            logging.warning(f"⚠️ Modul-Registrierung fehlgeschlagen für {module_id}: {e}")
            return False
    
    return False  # Status Manager nicht verfügbar

class DatabaseManager:
    def __init__(self, backend_dict, strict_mode=False, autostart: bool = False):
        self.logger = logging.getLogger('DatabaseManager')
        self.strict_mode = strict_mode  # Neuer strict mode Parameter
        self.backend_errors = []        # Sammle Backend-Fehler
        self.module_status_enabled = STATUS_MANAGER_AVAILABLE  # Status Manager verfügbar
        # Keep track of backends that should be started later
        self._backends_to_start = {}
        self._backend_factories = {}
        self.autostart = bool(autostart)
        governance_conf = {}
        if isinstance(backend_dict, dict):
            governance_conf = backend_dict.get('governance', {}) or {}
        policies = governance_conf.get('policies') if isinstance(governance_conf, dict) else None
        strict_governance = True
        if isinstance(governance_conf, dict) and 'strict' in governance_conf:
            strict_governance = bool(governance_conf.get('strict'))
        self.adapter_governance = AdapterGovernance(policies, strict=strict_governance)
        
        # Status Manager Registrierung (mit Duplikat-Prüfung)
        if self.module_status_enabled:
            if safe_register_module("db_manager", "Database Manager", ModuleType.CORE, critical=True):
                update_status("db_manager", ModuleStatus.INITIALIZING, "Database Manager wird initialisiert")
            else:
                # Nur Status updaten wenn bereits registriert
                if STATUS_MANAGER_AVAILABLE:
                    update_status("db_manager", ModuleStatus.INITIALIZING, "Database Manager wird re-initialisiert")
    # ...existing code...
    # Vector Backend initialisieren
        vector_conf = backend_dict.get('vector')
        if isinstance(vector_conf, dict):
            if vector_conf.get('enabled'):
                try:
                    # prefer the full-featured chromadb python client adapter when available
                    try:
                        from database.database_api_chromadb import ChromaVectorBackend
                        backend_cls = ChromaVectorBackend
                    except Exception as inner_e:
                        # chromadb python client not available or adapter raised during import
                        self.logger.debug(f"Chroma client adapter import failed, will try HTTP-only adapter: {inner_e}")
                        from database.database_api_chromadb_remote import ChromaHTTPVectorBackend
                        backend_cls = ChromaHTTPVectorBackend

                    conf = {k: v for k, v in vector_conf.items() if k != 'enabled'}
                    # Defer instantiation to start_all_backends to avoid blocking in __init__
                    try:
                        self._backend_factories['vector'] = (backend_cls, conf)
                        self.vector_backend = None
                    except Exception as inst_e:
                        self.logger.error(f"Vector backend factory registration failed: {inst_e}")
                        self.vector_backend = None

                    # Status Manager Registrierung (mit Duplikat-Prüfung)
                    if self.module_status_enabled:
                        safe_register_module("db_vector", "Vector Database", ModuleType.DATABASE, critical=True)
                        update_status("db_vector", ModuleStatus.INITIALIZING, "Vector Backend wird initialisiert")

                    # Defer actual connect to start_all_backends()
                    # Defer actual connect/instantiation to start_all_backends()
                    self._backends_to_start['vector'] = self._backend_factories.get('vector')
                except Exception as e:
                    self.logger.error(f"Vector Backend Initialisierung fehlgeschlagen: {e}")
                    if self.module_status_enabled:
                        update_status("db_vector", ModuleStatus.CRITICAL, f"Vector Backend Initialisierung fehlgeschlagen: {e}")
                    self.vector_backend = None
            else:
                self.vector_backend = None
                if self.module_status_enabled:
                    safe_register_module("db_vector", "Vector Database", ModuleType.DATABASE, critical=False)
                    if STATUS_MANAGER_AVAILABLE:
                        update_status("db_vector", ModuleStatus.OFFLINE, "Vector Backend deaktiviert")
        elif vector_conf is not None:
            self.vector_backend = vector_conf
        else:
            self.vector_backend = None
    # ...existing code...
    # Graph Backend initialisieren
        graph_conf = backend_dict.get('graph')
        if isinstance(graph_conf, dict):
            if graph_conf.get('enabled'):
                try:
                    from database.database_api_neo4j import Neo4jGraphBackend
                    conf = {k: v for k, v in graph_conf.items() if k != 'enabled'}
                    # Defer instantiation to start_all_backends to avoid blocking in __init__
                    try:
                        self._backend_factories['graph'] = (Neo4jGraphBackend, conf)
                        self.graph_backend = None
                    except Exception as inst_e:
                        self.logger.error(f"Graph backend factory registration failed: {inst_e}")
                        self.graph_backend = None
                    
                    # Status Manager Registrierung (mit Duplikat-Prüfung)
                    if self.module_status_enabled:
                        if safe_register_module("db_graph", "Graph Database", ModuleType.DATABASE, critical=True, dependencies=["db_vector"]):
                            update_status("db_graph", ModuleStatus.INITIALIZING, "Graph Backend wird initialisiert")
                        else:
                            if STATUS_MANAGER_AVAILABLE:
                                update_status("db_graph", ModuleStatus.INITIALIZING, "Graph Backend wird re-initialisiert")

                    # Defer actual connect to start_all_backends()
                    # Defer actual connect/instantiation to start_all_backends()
                    self._backends_to_start['graph'] = self._backend_factories.get('graph')
                except Exception as e:
                    self.logger.error(f"Graph Backend Initialisierung fehlgeschlagen: {e}")
                    if self.module_status_enabled:
                        update_status("db_graph", ModuleStatus.CRITICAL, f"Graph Backend Initialisierung fehlgeschlagen: {e}")
                    self.graph_backend = None
            else:
                self.graph_backend = None
                if self.module_status_enabled:
                    safe_register_module("db_graph", "Graph Database", ModuleType.DATABASE, critical=False)
                    if STATUS_MANAGER_AVAILABLE:
                        update_status("db_graph", ModuleStatus.OFFLINE, "Graph Backend deaktiviert")
        elif graph_conf is not None:
            self.graph_backend = graph_conf
        else:
            self.graph_backend = None
    # ...existing code...
    # Relational Backend initialisieren
        rel_conf = backend_dict.get('relational')
        if isinstance(rel_conf, dict):
            if rel_conf.get('enabled'):
                # Determine backend implementation from config ('backend' field)
                conf = {k: v for k, v in rel_conf.items() if k != 'enabled'}
                backend_name = rel_conf.get('backend', '').lower() if isinstance(rel_conf.get('backend'), str) else ''
                try:
                    try:
                        # Temporärer Workaround: Verwende SQLite für Konsistenz mit manuellen SAGA-Aktionen
                        # Grund: PostgreSQL Timeout-Problem beim Backend-Start
                        if backend_name == 'postgresql':
                            # Verwende SQLite statt PostgreSQL für Development
                            self.logger.info("🔧 PostgreSQL -> SQLite Fallback aktiviert für Development")
                            from database.database_api_sqlite import SQLiteRelationalBackend
                            backend_cls_rel = SQLiteRelationalBackend
                            # Überschreibe Konfiguration für SQLite-Pfad
                            conf = {'database_path': './data/uds3_relational.db'}
                        elif backend_name == 'mongodb':
                            from database.database_api_mongodb import MongoDBDocumentBackend
                            backend_cls_rel = MongoDBDocumentBackend
                        elif backend_name == 'couchdb':
                            from database.database_api_couchdb import CouchDBAdapter
                            backend_cls_rel = CouchDBAdapter
                        else:
                            # Default to SQLite relational backend
                            from database.database_api_sqlite import SQLiteRelationalBackend
                            backend_cls_rel = SQLiteRelationalBackend
                        # Defer instantiation
                        try:
                            self._backend_factories['relational'] = (backend_cls_rel, conf)
                            self.relational_backend = None
                        except Exception as inst_e:
                            self.logger.error(f"Relational backend factory registration failed: {inst_e}")
                            self.relational_backend = None
                    except Exception as inst_e:
                        self.logger.error(f"Relational backend instantiation failed: {inst_e}")
                        self.relational_backend = None

                    # Defer actual connect to start_all_backends()
                    if self._backend_factories.get('relational'):
                        self._backends_to_start['relational'] = self._backend_factories.get('relational')

                except Exception as e:
                    self.logger.error(f"Relational Backend Initialisierung fehlgeschlagen: {e}")
                    self.relational_backend = None
            else:
                self.relational_backend = None
        elif rel_conf is not None:
            self.relational_backend = rel_conf
        else:
            self.relational_backend = None
    # ...existing code...
        # File Storage Backend initialisieren
        file_conf = backend_dict.get('file')
        self.file_backend = None
        if isinstance(file_conf, dict):
            if file_conf.get('enabled'):
                try:
                    # Bestimme Backend-Implementierung aus Config
                    backend_type = file_conf.get('backend_type', '').lower() if isinstance(file_conf.get('backend_type'), str) else ''
                    conf = {k: v for k, v in file_conf.items() if k != 'enabled'}
                    
                    # Wähle Backend basierend auf backend_type
                    if backend_type == 'couchdb':
                        from database.database_api_couchdb import CouchDBAdapter
                        backend_cls = CouchDBAdapter
                    elif backend_type == 's3':
                        from database.database_api_s3 import S3StorageBackend
                        backend_cls = S3StorageBackend
                    else:
                        # Default: FileSystemStorageBackend
                        from database.database_api_file_storage import FileSystemStorageBackend
                        backend_cls = FileSystemStorageBackend
                    
                    try:
                        # Defer instantiation of file backend
                        self._backend_factories['file'] = (backend_cls, conf)
                        self.file_backend = None
                    except Exception as inst_e:
                        self.logger.error(f"File storage backend factory registration failed: {inst_e}")
                        self.file_backend = None

                    if self.module_status_enabled:
                        safe_register_module("db_file", "File Storage", ModuleType.DATABASE, critical=False)
                        update_status("db_file", ModuleStatus.INITIALIZING, "File Storage Backend wird initialisiert")

                    # Defer actual connect to start_all_backends()
                    if self._backend_factories.get('file'):
                        self._backends_to_start['file'] = self._backend_factories.get('file')
                except Exception as e:
                    self.logger.error(f"File Storage Backend Initialisierung fehlgeschlagen: {e}")
                    if self.module_status_enabled:
                        update_status("db_file", ModuleStatus.CRITICAL, f"File Storage Backend Initialisierung fehlgeschlagen: {e}")
                    self.file_backend = None
            else:
                self.file_backend = None
                if self.module_status_enabled:
                    safe_register_module("db_file", "File Storage", ModuleType.DATABASE, critical=False)
                    if STATUS_MANAGER_AVAILABLE:
                        update_status("db_file", ModuleStatus.OFFLINE, "File Storage Backend deaktiviert")
        elif file_conf is not None:
            self.file_backend = file_conf
        else:
            self.file_backend = None

        # KeyValue Backend initialisieren
        # NOTE: config.py und server_config.json verwenden den Schlüssel 'key_value'
        kv_conf = backend_dict.get('key_value')
        if isinstance(kv_conf, dict):
            if kv_conf.get('enabled'):
                backend_name = (kv_conf.get('backend') or '').lower()
                conf = {k: v for k, v in kv_conf.items() if k != 'enabled'}
                backend_cls = None

                try:
                    if backend_name in ('redis', 'redis_cluster'):
                        from database.database_api_redis import RedisKeyValueBackend  # type: ignore
                        backend_cls = RedisKeyValueBackend
                    elif backend_name in ('postgresql', 'postgres', 'postgresql-keyvalue'):
                        from database.database_api_keyvalue_postgresql import PostgreSQLKeyValueBackend
                        backend_cls = PostgreSQLKeyValueBackend
                    else:
                        raise ValueError(f"Unsupported key-value backend '{backend_name}'")
                except ImportError as import_e:
                    self.logger.error(f"Failed to import keyvalue backend '{backend_name}': {import_e}")
                except ValueError as unsupported_e:
                    self.logger.error(str(unsupported_e))

                if backend_cls:
                    try:
                        self._backend_factories['keyvalue'] = (backend_cls, conf)
                        self.keyvalue_backend = None
                        if self._backend_factories.get('keyvalue'):
                            self._backends_to_start['keyvalue'] = self._backend_factories.get('keyvalue')
                    except Exception as inst_e:
                        self.logger.error(f"KeyValue backend instantiation failed: {inst_e}")
                        self.keyvalue_backend = None
                else:
                    self.keyvalue_backend = None
            else:
                self.keyvalue_backend = None
        elif kv_conf is not None:
            self.keyvalue_backend = kv_conf
        else:
            self.keyvalue_backend = None
    # ...existing code...
    # ...existing code...
        # Database Manager als gesund markieren nach Initialisierung
        if self.module_status_enabled:
            backends_initialized = []
            if self.vector_backend: backends_initialized.append("Vector")
            if self.graph_backend: backends_initialized.append("Graph")
            if self.relational_backend: backends_initialized.append("Relational")
            if self.file_backend: backends_initialized.append("File")
            if self.keyvalue_backend: backends_initialized.append("KeyValue")
            
            status_msg = f"Database Manager initialisiert mit: {', '.join(backends_initialized) if backends_initialized else 'Keine Backends'}"
            update_status("db_manager", ModuleStatus.HEALTHY, status_msg)
        
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)
        # If autostart requested, start all deferred backends now
        if self.autostart:
            try:
                results = self.start_all_backends(timeout_per_backend=10)
                self.logger.info(f"Autostart finished: {results}")
            except Exception as e:
                self.logger.error(f"Autostart failed: {e}")

    def create_database_if_missing(self, db_type: str, name: str) -> bool:
    # ...existing code...
        """
        Legt die Datenbank/Collection/Knoten an, falls sie fehlt. Meldet Erfolg/Misserfolg und Fehler.
        """
        backend = None
        if db_type == 'vector':
            backend = self.vector_backend
        elif db_type == 'graph':
            backend = self.graph_backend
        elif db_type == 'relational':
            backend = self.relational_backend
        elif db_type == 'keyvalue':
            backend = self.keyvalue_backend
        if not backend:
            self.logger.error(f"Kein Backend für Typ '{db_type}' verfügbar!")
            return False
        try:
            # VectorDB: Collection anlegen
            if db_type == 'vector' and hasattr(backend, 'list_collections') and hasattr(backend, 'create_collection'):
                try:
                    collections = backend.list_collections()
                except Exception as e:
                    self.logger.error(f"[ERROR] [VectorDB] Fehler beim Lesen der Collections: {e}")
                    return False
                if name not in collections:
                    try:
                        result = backend.create_collection(name)
                        if not result:
                            self.logger.error(f"[ERROR] [VectorDB] Collection '{name}' konnte nicht angelegt werden!")
                        return result
                    except Exception as e:
                        self.logger.error(f"[ERROR] [VectorDB] Fehler beim Schreiben/Erzeugen der Collection '{name}': {e}")
                        return False
                else:
                    return True
            # GraphDB: Knoten anlegen
            elif db_type == 'graph' and hasattr(backend, 'create_node'):
                result = backend.create_node('Collection', {'name': name})
                return bool(result)
            # RelationalDB: Tabelle anlegen
            elif db_type == 'relational' and hasattr(backend, 'create_table'):
                schema = {'id': 'INTEGER PRIMARY KEY AUTOINCREMENT', 'data': 'TEXT'}
                result = backend.create_table(name, schema)
                return result
            # KeyValueDB: Kein explizites Anlegen nötig
            else:
                return True
        except Exception as e:
            self.logger.error(f"[ERROR] Fehler beim Anlegen von '{name}' in '{db_type}': {e}")
            return False

    def verify_backends(self):
    # ...existing code...
        """
        Überprüft alle Backends auf Verfügbarkeit und gibt Status/Fehler zurück.
        """
        status = {}
        for typ, backend in [
            ('vector', self.vector_backend),
            ('graph', self.graph_backend),
            ('relational', self.relational_backend),
            ('file', getattr(self, 'file_backend', None)),
            ('keyvalue', self.keyvalue_backend)
        ]:
            try:
                if backend is None:
                    status[typ] = 'Nicht initialisiert'
                else:
                    # Test: Status und Collection-Listing
                    s = backend.status() if hasattr(backend, 'status') else 'Kein Status verfügbar'
                    cols = backend.list_collections() if hasattr(backend, 'list_collections') else 'Kein Collection-Listing'
                    status[typ] = {'status': s, 'collections': cols}
            except Exception as e:
                status[typ] = f'Fehler: {e}'
                self.logger.error(f"Backend '{typ}' Fehler: {e}")
        self.logger.info(f"Backend-Überprüfung: {status}")
        return status

    def stop_all_backends(self):
        """Stop and disconnect all started backend instances."""
        stopped = {}
        # Collect candidate backends from known attributes and deferred list
        candidates = {}
        for attr_name in ('vector_backend', 'graph_backend', 'relational_backend', 'file_backend', 'keyvalue_backend'):
            backend_obj = getattr(self, attr_name, None)
            if backend_obj is not None:
                candidates[attr_name.replace('_backend', '')] = backend_obj

        # include any still in _backends_to_start
        for name, backend in list(self._backends_to_start.items()):
            if backend is not None:
                candidates[name] = backend

        # Attempt to disconnect all unique backend instances
        seen = set()
        for name, backend in list(candidates.items()):
            try:
                if backend is None:
                    stopped[name] = False
                    continue
                # avoid duplicate disconnects for same object
                obj_id = id(backend)
                if obj_id in seen:
                    continue
                seen.add(obj_id)

                if hasattr(backend, 'disconnect'):
                    try:
                        backend.disconnect()
                        stopped[name] = True
                    except Exception as e:
                        self.logger.warning(f"Failed to disconnect backend {name}: {e}")
                        stopped[name] = False
                else:
                    stopped[name] = False

                # remove from to-start list if present
                try:
                    if name in self._backends_to_start:
                        del self._backends_to_start[name]
                except Exception:
                    pass

            except Exception as e:
                self.logger.error(f"Error while stopping backend {name}: {e}")
                stopped[name] = False

        return stopped
    
    def _load_graph_backend(self, backend_type: str, config: Dict) -> bool:
        """Lade Graph Database Backend"""
        try:
            if backend_type not in self.backend_modules:
                logging.error(f"Unbekannter Graph Backend Typ: {backend_type}")
                return False
            
            module_name = self.backend_modules[backend_type]
            module = importlib.import_module(module_name)
            backend_class = module.get_backend_class()
            
            self.graph_backend = backend_class(config)
            
            if self.graph_backend.connect():
                logging.info(f"Graph Backend geladen: {backend_type}")
                return True
            else:
                logging.error(f"Graph Backend Verbindung fehlgeschlagen: {backend_type}")
                return False
                
        except Exception as e:
            logging.error(f"Graph Backend laden fehlgeschlagen ({backend_type}): {e}")
            return False
    
    def _load_relational_backend(self, backend_type: str, config: Dict) -> bool:
        """Lade Relational Database Backend"""
        try:
            if backend_type not in self.backend_modules:
                logging.error(f"Unbekannter Relational Backend Typ: {backend_type}")
                return False
            
            module_name = self.backend_modules[backend_type]
            module = importlib.import_module(module_name)
            backend_class = module.get_backend_class()
            
            self.relational_backend = backend_class(config)
            
            if self.relational_backend.connect():
                logging.info(f"Relational Backend geladen: {backend_type}")
                return True
            else:
                logging.error(f"Relational Backend Verbindung fehlgeschlagen: {backend_type}")
                return False
                
        except Exception as e:
            logging.error(f"Relational Backend laden fehlgeschlagen ({backend_type}): {e}")
            return False
    
    def _load_key_value_backend(self, backend_type: str, config: Dict) -> bool:
        """Lade Key-Value Database Backend"""
        try:
            if backend_type not in self.backend_modules:
                logging.error(f"Unbekannter Key-Value Backend Typ: {backend_type}")
                return False
            
            module_name = self.backend_modules[backend_type]
            module = importlib.import_module(module_name)
            backend_class = module.get_backend_class()
            self.keyvalue_backend = backend_class(config)
            
            if self.keyvalue_backend.connect():
                logging.info(f"Key-Value Backend geladen: {backend_type}")
                return True
            else:
                logging.error(f"Key-Value Backend Verbindung fehlgeschlagen: {backend_type}")
                return False
                
        except Exception as e:
            logging.error(f"Key-Value Backend laden fehlgeschlagen ({backend_type}): {e}")
            return False
    
    def get_vector_backend(self) -> Optional[VectorDatabaseBackend]:
        """Hole Vector Database Backend mit verbesserter Fehlerbehandlung"""
        self.logger.debug(f"[DEBUG] get_vector_backend aufgerufen, Rückgabe: {self.vector_backend}")
        
        if self.vector_backend is None:
            error_msg = "Vector Backend ist nicht initialisiert"
            self.backend_errors.append(f"Vector: {error_msg}")
            if self.module_status_enabled:
                update_status("db_vector", ModuleStatus.ERROR, error_msg)
            if self.strict_mode:
                self.logger.error(f"❌ KRITISCHER FEHLER: {error_msg}")
                raise RuntimeError(f"Vector Backend kritischer Fehler: {error_msg}")
            else:
                self.logger.warning(f"⚠️ {error_msg}")
                return None
        
        # Verfügbarkeit prüfen wenn Backend vorhanden
        if hasattr(self.vector_backend, 'is_available'):
            try:
                if not self.vector_backend.is_available():
                    error_msg = f"Vector Backend nicht verfügbar: {self.vector_backend.get_backend_type()}"
                    self.backend_errors.append(f"Vector: {error_msg}")
                    if self.module_status_enabled:
                        update_status("db_vector", ModuleStatus.ERROR, error_msg)
                    if self.strict_mode:
                        self.logger.error(f"❌ KRITISCHER FEHLER: {error_msg}")
                        raise RuntimeError(f"Vector Backend kritischer Fehler: {error_msg}")
                    else:
                        self.logger.error(f"❌ {error_msg}")
                        return None
            except Exception as e:
                error_msg = f"Vector Backend Verfügbarkeits-Check fehlgeschlagen: {e}"
                self.backend_errors.append(f"Vector: {error_msg}")
                if self.module_status_enabled:
                    update_status("db_vector", ModuleStatus.CRITICAL, error_msg)
                if self.strict_mode:
                    self.logger.error(f"❌ KRITISCHER FEHLER: {error_msg}")
                    raise RuntimeError(f"Vector Backend kritischer Fehler: {error_msg}")
                else:
                    self.logger.error(f"❌ {error_msg}")
                    return None
        
        return self.vector_backend
    
    def get_graph_backend(self) -> Optional[GraphDatabaseBackend]:
        """Hole Graph Database Backend mit verbesserter Fehlerbehandlung"""
        self.logger.debug(f"[DEBUG] get_graph_backend aufgerufen, Rückgabe: {self.graph_backend}")
        
        if self.graph_backend is None:
            error_msg = "Graph Backend ist nicht initialisiert"
            self.backend_errors.append(f"Graph: {error_msg}")
            if self.module_status_enabled:
                update_status("db_graph", ModuleStatus.ERROR, error_msg)
            if self.strict_mode:
                self.logger.error(f"❌ KRITISCHER FEHLER: {error_msg}")
                raise RuntimeError(f"Graph Backend kritischer Fehler: {error_msg}")
            else:
                self.logger.warning(f"⚠️ {error_msg}")
                return None
        
        # Verfügbarkeit prüfen wenn Backend vorhanden
        if hasattr(self.graph_backend, 'is_available'):
            try:
                if not self.graph_backend.is_available():
                    error_msg = f"Graph Backend nicht verfügbar: {self.graph_backend.get_backend_type()}"
                    self.backend_errors.append(f"Graph: {error_msg}")
                    if self.module_status_enabled:
                        update_status("db_graph", ModuleStatus.ERROR, error_msg)
                    if self.strict_mode:
                        self.logger.error(f"❌ KRITISCHER FEHLER: {error_msg}")
                        raise RuntimeError(f"Graph Backend kritischer Fehler: {error_msg}")
                    else:
                        self.logger.error(f"❌ {error_msg}")
                        return None
            except Exception as e:
                error_msg = f"Graph Backend Verfügbarkeits-Check fehlgeschlagen: {e}"
                self.backend_errors.append(f"Graph: {error_msg}")
                if self.module_status_enabled:
                    update_status("db_graph", ModuleStatus.CRITICAL, error_msg)
                if self.strict_mode:
                    self.logger.error(f"❌ KRITISCHER FEHLER: {error_msg}")
                    raise RuntimeError(f"Graph Backend kritischer Fehler: {error_msg}")
                else:
                    self.logger.error(f"❌ {error_msg}")
                    return None
        
        return self.graph_backend
    
    def get_relational_backend(self) -> Optional[RelationalDatabaseBackend]:
        self.logger.debug(f"[DEBUG] get_relational_backend aufgerufen, Rückgabe: {self.relational_backend}")
        """Hole Relational Database Backend"""
        return self.relational_backend
    
    def get_key_value_backend(self) -> Optional[DatabaseBackend]:
        self.logger.debug(f"[DEBUG] get_key_value_backend aufgerufen, Rückgabe: {self.keyvalue_backend}")
        """Hole Key-Value Database Backend"""
        return self.keyvalue_backend
    
    def get_backend_errors(self) -> List[str]:
        """Gibt alle Backend-Fehler zurück"""
        return self.backend_errors.copy()
    
    def clear_backend_errors(self):
        """Löscht die Backend-Fehler-Liste"""
        self.backend_errors.clear()
    
    def enable_strict_mode(self):
        """Aktiviert den Strict Mode"""
        self.strict_mode = True
        self.logger.info("🚨 Strict Mode aktiviert - Pipeline stoppt bei kritischen Backend-Fehlern")
    
    def disable_strict_mode(self):
        """Deaktiviert den Strict Mode"""
        self.strict_mode = False
        self.logger.info("⚠️ Strict Mode deaktiviert - Pipeline toleriert Backend-Fehler")

    # ------------------------------------------------------------------
    # Adapter Governance Helpers
    # ------------------------------------------------------------------
    def ensure_operation_allowed(self, backend_key: str, operation: str) -> None:
        if not hasattr(self, 'adapter_governance') or self.adapter_governance is None:
            return
        try:
            self.adapter_governance.ensure_operation_allowed(backend_key, operation)
        except AdapterGovernanceError:
            self.logger.error("🚫 Governance-Verstoß: Operation '%s' auf Backend '%s' ist nicht erlaubt", operation, backend_key)
            raise

    def enforce_payload_policy(self, backend_key: str, operation: str, payload) -> None:
        if not hasattr(self, 'adapter_governance') or self.adapter_governance is None:
            return
        try:
            self.adapter_governance.enforce_payload(backend_key, operation, payload)
        except AdapterGovernanceError as exc:
            self.logger.error("🚫 Governance-Payload-Verstoß (%s/%s): %s", backend_key, operation, exc)
            raise

    def get_adapter_governance(self) -> Optional[AdapterGovernance]:
        return getattr(self, 'adapter_governance', None)
    
    def get_backend_status(self) -> Dict:
        """Status aller Backends"""
        status = {}
        
        if self.vector_backend:
            status['vector'] = {
                'type': self.vector_backend.get_backend_type(),
                'available': self.vector_backend.is_available()
            }
        
        if self.graph_backend:
            status['graph'] = {
                'type': self.graph_backend.get_backend_type(),
                'available': self.graph_backend.is_available()
            }
        
        if self.relational_backend:
            status['relational'] = {
                'type': self.relational_backend.get_backend_type(),
                'available': self.relational_backend.is_available()
            }
        if hasattr(self, 'file_backend') and self.file_backend:
            status['file'] = {
                'type': self.file_backend.get_backend_type(),
                'available': self.file_backend.is_available()
            }
        if self.keyvalue_backend:
            # Verwende externes Schlüssel-Naming 'key_value' für Status/Reporting
            status['key_value'] = {
                'type': self.keyvalue_backend.get_backend_type(),
                'available': self.keyvalue_backend.is_available()
            }
        
        return status
    
    def disconnect_all(self):
        """Trenne alle Backend-Verbindungen"""
        for backend in [
            self.vector_backend,
            self.graph_backend,
            self.relational_backend,
            getattr(self, 'file_backend', None),
            getattr(self, 'keyvalue_backend', None),
        ]:
            if backend:
                try:
                    backend.disconnect()
                except Exception as e:
                    logging.error(f"Fehler beim Trennen von Backend: {e}")
        
        logging.info("Alle Database Backends getrennt")
    
    def test_all_backends(self) -> Dict:
        """Teste alle verfügbaren Backends"""
        results = {}
        
        # Vector Backend Test
        if self.vector_backend:
            try:
                stats = self.vector_backend.get_collection_stats()
                results['vector'] = {
                    'status': 'success',
                    'type': self.vector_backend.get_backend_type(),
                    'stats': stats
                }
            except Exception as e:
                results['vector'] = {
                    'status': 'error',
                    'type': self.vector_backend.get_backend_type(),
                    'error': str(e)
                }
        
        # Graph Backend Test
        if self.graph_backend:
            try:
                # Test Node erstellen und abrufen
                test_id = self.graph_backend.create_node('TestNode', {'test': 'data'})
                if test_id:
                    node = self.graph_backend.get_node(test_id)
                    results['graph'] = {
                        'status': 'success',
                        'type': self.graph_backend.get_backend_type(),
                        'test_result': node is not None
                    }
                else:
                    results['graph'] = {
                        'status': 'error',
                        'type': self.graph_backend.get_backend_type(),
                        'error': 'Failed to create test node'
                    }
            except Exception as e:
                results['graph'] = {
                    'status': 'error',
                    'type': self.graph_backend.get_backend_type(),
                    'error': str(e)
                }
        
        # Relational Backend Test
        if self.relational_backend:
            try:
                tables = self.relational_backend.get_tables()
                results['relational'] = {
                    'status': 'success',
                    'type': self.relational_backend.get_backend_type(),
                    'tables': tables
                }
            except Exception as e:
                results['relational'] = {
                    'status': 'error',
                    'type': self.relational_backend.get_backend_type(),
                    'error': str(e)
                }
        
        # Key-Value Backend Test
        if self.keyvalue_backend:
            try:
                # Test Set/Get
                test_key = 'test_key'
                test_value = {'test': 'data'}
                
                if hasattr(self.keyvalue_backend, 'set'):
                    self.keyvalue_backend.set(test_key, test_value)
                    retrieved = self.keyvalue_backend.get(test_key)
                    
                    results['key_value'] = {
                        'status': 'success',
                        'type': self.keyvalue_backend.get_backend_type(),
                        'test_result': retrieved == test_value
                    }
                else:
                    results['key_value'] = {
                        'status': 'success',
                        'type': self.keyvalue_backend.get_backend_type(),
                        'available': self.keyvalue_backend.is_available()
                    }
            except Exception as e:
                results['key_value'] = {
                    'status': 'error',
                    'type': self.keyvalue_backend.get_backend_type(),
                    'error': str(e)
                }
        
        return results

    def list_collections_by_type(self, db_type: str):
        """
        Gibt die verfügbaren Collections/Knoten für den angegebenen Typ zurück.
        db_type: 'vector' oder 'graph'
        """
        if db_type == 'vector' and self.vector_backend:
            try:
                return self.vector_backend.list_collections()
            except Exception as e:
                logging.error(f"Fehler beim Auflisten der VectorDB-Collections: {e}")
                return []
        elif db_type == 'graph' and self.graph_backend:
            try:
                if hasattr(self.graph_backend, 'list_collections'):
                    return self.graph_backend.list_collections()
                elif hasattr(self.graph_backend, 'list_nodes'):
                    return self.graph_backend.list_nodes()
                else:
                    return []
            except Exception as e:
                logging.error(f"Fehler beim Auflisten der GraphDB-Knoten: {e}")
                return []
        else:
            return []

    def debug_status(self):
        """
        Gibt eine Übersicht über die Verfügbarkeit und Verbindung aller Backends zurück.
        """
        status = {}
        for typ, backend in [('vector', self.vector_backend), ('graph', self.graph_backend), ('relational', self.relational_backend), ('file', getattr(self, 'file_backend', None)), ('keyvalue', self.get_key_value_backend())]:
            if backend:
                try:
                    available = backend.is_available() if hasattr(backend, 'is_available') else None
                    backend_type = backend.get_backend_type() if hasattr(backend, 'get_backend_type') else str(type(backend))
                    status[typ] = {
                        'type': backend_type,
                        'available': available,
                        'connected': getattr(backend, 'client', None) is not None or getattr(backend, 'driver', None) is not None
                    }
                except Exception as e:
                    status[typ] = {'error': str(e)}
            else:
                status[typ] = {'available': False, 'connected': False}
        return status

    def get_file_backend(self) -> Optional[DatabaseBackend]:
        self.logger.debug(f"[DEBUG] get_file_backend aufgerufen, Rückgabe: {getattr(self, 'file_backend', None)}")
        return getattr(self, 'file_backend', None)

    def test_operation(self, db_type: str, operation: str, *args, **kwargs):
        """
        Testet eine Operation auf dem angegebenen Backend und gibt Erfolg/Misserfolg und Fehler zurück.
        """
        backend = None
        if db_type == 'vector':
            backend = self.vector_backend
        elif db_type == 'graph':
            backend = self.graph_backend
        elif db_type == 'relational':
            backend = self.relational_backend
        elif db_type == 'key_value':
            backend = self.keyvalue_backend
        if not backend:
            logging.error(f"[DEBUG] Kein Backend für Typ '{db_type}' verfügbar!")
            return {'success': False, 'error': 'Backend nicht verfügbar'}
        try:
            method = getattr(backend, operation, None)
            if not method:
                logging.error(f"[DEBUG] Operation '{operation}' existiert nicht im Backend '{db_type}'!")
                return {'success': False, 'error': f"Operation '{operation}' nicht gefunden"}
            result = method(*args, **kwargs)
            logging.info(f"[DEBUG] Operation '{operation}' auf Backend '{db_type}' erfolgreich: {result}")
            return {'success': True, 'result': result}
        except Exception as e:
            logging.error(f"[DEBUG] Fehler bei Operation '{operation}' auf Backend '{db_type}': {e}")
            return {'success': False, 'error': str(e)}

    def add_document_with_metadata(self, collection_name: str, document: str, metadata: dict, doc_id: str = None):
        """
        Fügt ein Dokument mit beliebigen Metadaten (inkl. Relationen, Kontext, Tags) in die VectorDB ein.
        """
        vector_backend = self.get_vector_backend()
        if vector_backend:
            return vector_backend.add_documents(collection_name, [document], [metadata], [doc_id or str(uuid.uuid4())])
        return False

    def start_all_backends(self, backend_names: Optional[List[str]] = None, timeout_per_backend: int = 5) -> Dict[str, bool]:
        """Starte alle zuvor instanzierten, aber nicht verbundenen Backends.

        Wenn backend_names angegeben ist, starte nur die genannten Backends.
        Gibt ein Dict mapping backend_name -> bool (erfolgreich) zurück.
        """
        results = {}
        to_start = self._backends_to_start.copy() if backend_names is None else {k: v for k, v in self._backends_to_start.items() if k in backend_names}

        if not to_start:
            return results

        # Use a thread pool so a single backend.connect() can't hang the whole process
        max_workers = min(8, max(1, len(to_start)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for name, backend_or_factory in to_start.items():
                logging.info(f"Starting backend: {name}")
                try:
                    # backend_or_factory may be either an actual backend instance
                    # or a factory tuple (backend_cls, conf). If factory, create inside thread.
                    if isinstance(backend_or_factory, tuple) and len(backend_or_factory) == 2:
                        backend_cls, conf = backend_or_factory
                        # submit a callable that instantiates then connects
                        def instantiate_and_connect(cls=backend_cls, cfg=conf):
                            inst = None
                            try:
                                inst = cls(cfg)
                            except Exception as e:
                                logging.error(f"Instantiation failed for backend {name}: {e}")
                                raise
                            try:
                                return inst.connect(), inst
                            except Exception:
                                # if connect fails, propagate exception
                                raise

                        future = executor.submit(instantiate_and_connect)
                        future_map[name] = (future, 'factory')
                    else:
                        # assume an already-instantiated backend
                        future = executor.submit(backend_or_factory.connect)
                        future_map[name] = (future, backend_or_factory)
                except Exception as e:
                    logging.error(f"Failed to submit connect() for backend {name}: {e}")
                    results[name] = False

            # collect results with timeout
            for name, (future, payload) in future_map.items():
                ok = False
                try:
                    res = future.result(timeout=timeout_per_backend)
                    # res may be a tuple (connect_result, instance) for factory path
                    if isinstance(res, tuple) and len(res) == 2:
                        connect_ok, inst = res
                        ok = bool(connect_ok)
                        # attach instantiated backend to manager attributes
                        if ok:
                            if name == 'vector':
                                self.vector_backend = inst
                            elif name == 'graph':
                                self.graph_backend = inst
                            elif name == 'relational':
                                self.relational_backend = inst
                            elif name == 'file':
                                self.file_backend = inst
                            elif name == 'keyvalue':
                                self.keyvalue_backend = inst
                    else:
                        # non-factory path: res is connect() return value
                        ok = bool(res)
                        if ok and isinstance(payload, object) and payload != 'factory':
                            # ensure backend attribute is set
                            if name == 'vector' and getattr(self, 'vector_backend', None) is None:
                                self.vector_backend = payload
                            if name == 'graph' and getattr(self, 'graph_backend', None) is None:
                                self.graph_backend = payload
                            if name == 'relational' and getattr(self, 'relational_backend', None) is None:
                                self.relational_backend = payload
                            if name == 'file' and getattr(self, 'file_backend', None) is None:
                                self.file_backend = payload
                            if name == 'keyvalue' and getattr(self, 'keyvalue_backend', None) is None:
                                self.keyvalue_backend = payload
                except concurrent.futures.TimeoutError:
                    logging.error(f"connect() timed out for backend {name} after {timeout_per_backend}s")
                    ok = False
                except Exception as e:
                    logging.error(f"connect() raised for backend {name}: {e}")
                    ok = False

                results[name] = ok

                # Update module status manager if available
                if self.module_status_enabled:
                    status_key = f"db_{name}"
                    if ok:
                        update_status(status_key, ModuleStatus.HEALTHY, f"{name} Backend erfolgreich verbunden")
                    else:
                        update_status(status_key, ModuleStatus.ERROR, f"{name} Backend Verbindung fehlgeschlagen")

                # If successful, remove from to_start registry
                if ok and name in self._backends_to_start:
                    try:
                        del self._backends_to_start[name]
                    except Exception:
                        pass

        return results

    def create_graph_node_with_metadata(self, node_type: str, properties: dict):
        """
        Erstellt einen Graph-Knoten mit beliebigen Properties (inkl. Metadaten, Relationen etc.)
        """
        graph_backend = self.get_graph_backend()
        if graph_backend:
            return graph_backend.create_node(node_type, properties)
        return None

    def create_graph_edge_with_metadata(self, from_id: str, to_id: str, edge_type: str, properties: dict = None):
        """
        Erstellt eine Graph-Kante mit beliebigen Properties (inkl. Relationen, Kontext etc.)
        """
        graph_backend = self.get_graph_backend()
        if graph_backend:
            return graph_backend.create_edge(from_id, to_id, edge_type, properties)
        return None

def create_database_manager(config: Dict) -> DatabaseManager:
    """Factory-Funktion für DatabaseManager"""
    manager = DatabaseManager(config)
    # If config contains explicit autostart flag, pass it through
    autostart = False
    if isinstance(config, dict):
        autostart = bool(config.get('autostart', False))
    manager = DatabaseManager(config, autostart=autostart)
    return manager

if __name__ == "__main__":
    import pprint
    import logging
    from database import config
    logging.basicConfig(level=logging.DEBUG)
    print("=== DatabaseManager Debug ===")
    dbm = create_database_manager(config.create_backend_instances_dynamisch())

    # Test: create_database_if_missing für VectorDB
    print("[TEST] Teste create_database_if_missing für VectorDB...")
    dbm.create_database_if_missing('vector', 'test_collection')

    # Test: Backend-Getter
    print("[TEST] Teste Backend-Getter...")
    print("Vector-Backend:", dbm.get_vector_backend())
    print("Graph-Backend:", dbm.get_graph_backend())
    print("Relational-Backend:", dbm.get_relational_backend())
    print("KeyValue-Backend:", dbm.get_key_value_backend())

    # Test: Backend-Status
    print("[TEST] Teste get_backend_status...")
    pprint.pprint(dbm.get_backend_status())

    # Test: debug_status
    print("[TEST] Teste debug_status...")
    pprint.pprint(dbm.debug_status())

    print("[TEST] Alle Kernfunktionen wurden getestet.")

    print("\n[Test: VectorDB list_collections]")
    result = dbm.test_operation('vector', 'list_collections')
    pprint.pprint(result)

    print("\n[Test: GraphDB get_graph_stats]")
    result = dbm.test_operation('graph', 'get_graph_stats')
    pprint.pprint(result)

    print("\n[Test: RelationalDB get_tables]")
    result = dbm.test_operation('relational', 'get_tables')
    pprint.pprint(result)

    print("\n[Test: KeyValueDB is_available]")
    result = dbm.test_operation('key_value', 'is_available')
    pprint.pprint(result)


# ===== GLOBALER MANAGER (Kompatibilität) =====
_database_manager = None

def get_database_manager(strict_mode: bool = False):
    """Singleton Database Manager für Kompatibilität mit Strict Mode Support"""
    global _database_manager
    if _database_manager is None:
        # Verwende den top-level config Shim (einheitliche API)
        # Alle Codepfade verwenden jetzt die globale `config`-Instanz
        from database import config as cfg
        backend_instances = cfg.get_database_backend_dict()
        # honor autostart if present in config
        autostart = False
        if isinstance(backend_instances, dict):
            autostart = bool(backend_instances.get('autostart', False))
        _database_manager = DatabaseManager(backend_instances, strict_mode=strict_mode, autostart=autostart)
    return _database_manager
