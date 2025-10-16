#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""



"""
MongoDB Document Database Backend
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.database_api_base import RelationalDatabaseBackend
# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

try:
    import pymongo
    from pymongo import MongoClient
    from bson import ObjectId
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

logger = logging.getLogger(__name__)


class MongoDBDocumentBackend(RelationalDatabaseBackend):
    """MongoDB Document Database"""
    
    def __init__(self, config: Dict):
        if not MONGODB_AVAILABLE:
            logger.warning("pymongo not available at import time; connect() will fail if used")
        
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 27017)
        self.database_name = config.get('database', 'veritas')
        self.username = config.get('username')
        self.password = config.get('password')
        self.auth_source = config.get('auth_source', 'admin')
        
        self.client = None
        self.db = None
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for MongoDB: {exc}")
            self.strategy = None
        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"MongoDB Backend initialisiert mit Strategie {strategy_version}")
        
    def connect(self) -> bool:
        try:
            connection_params = {
                'host': self.host,
                'port': self.port,
                'serverSelectionTimeoutMS': 5000
            }
            
            if self.username and self.password:
                connection_params.update({
                    'username': self.username,
                    'password': self.password,
                    'authSource': self.auth_source
                })
            
            self.client = MongoClient(**connection_params)
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.database_name]
            
            # Basis-Collections und Indices erstellen
            self._setup_collections()
            
            logging.info(f"MongoDB verbunden: {self.host}:{self.port}/{self.database_name}")
            return True
            
        except Exception as e:
            logging.error(f"MongoDB Verbindung fehlgeschlagen: {e}")
            return False
    
    def _setup_collections(self):
        """Collections und Indices einrichten"""
        try:
            # Standard-Collections
            collections = ['documents', 'authors', 'tags', 'users']
            
            for collection_name in collections:
                if collection_name not in self.db.list_collection_names():
                    self.db.create_collection(collection_name)
                    logging.info(f"MongoDB Collection erstellt: {collection_name}")
            
            # Indices erstellen
            self.db.documents.create_index([('title', pymongo.TEXT), ('content', pymongo.TEXT)])
            self.db.documents.create_index('created_at')
            self.db.authors.create_index('name', unique=True)
            self.db.tags.create_index('name', unique=True)
            
        except Exception as e:
            logging.error(f"MongoDB Collections Setup fehlgeschlagen: {e}")
    
    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
    
    def is_available(self) -> bool:
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "MongoDB"
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """MongoDB hat keine SQL Queries - diese Methode ist für Kompatibilität"""
        logging.warning("MongoDB unterstützt keine SQL Queries. Verwende spezifische MongoDB Methoden.")
        return []
    
    def insert(self, collection: str, data: Dict) -> str:
        """
        Fügt ein Dokument mit beliebigen Metadaten (inkl. Relationen, Kontext, Tags) als JSON ein.
        """
        try:
            result = self.client[collection].insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Fehler beim Einfügen des Dokuments: {e}")
            return None
    
    def select(self, collection: str, conditions: Dict = None, 
              order_by: str = None, limit: int = None) -> List[Dict]:
        try:
            if not self.db:
                return []
            
            collection_obj = self.db[collection]
            
            # Filter
            filter_dict = conditions or {}
            
            # Query ausführen
            cursor = collection_obj.find(filter_dict)
            
            # Sortierung
            if order_by:
                if order_by.startswith('-'):
                    cursor = cursor.sort(order_by[1:], pymongo.DESCENDING)
                else:
                    cursor = cursor.sort(order_by, pymongo.ASCENDING)
            
            # Limit
            if limit:
                cursor = cursor.limit(limit)
            
            results = []
            for document in cursor:
                # ObjectId zu String konvertieren
                if '_id' in document and isinstance(document['_id'], ObjectId):
                    document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logging.error(f"MongoDB Select fehlgeschlagen: {e}")
            return []
    
    def update(self, collection: str, data: Dict, conditions: Dict) -> bool:
        try:
            if not self.db:
                return False
            
            # updated_at hinzufügen
            data['updated_at'] = datetime.now()
            
            collection_obj = self.db[collection]
            result = collection_obj.update_many(
                conditions,
                {'$set': data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"MongoDB Update fehlgeschlagen: {e}")
            return False
    
    def delete(self, collection: str, conditions: Dict) -> bool:
        try:
            if not self.db:
                return False
            
            collection_obj = self.db[collection]
            result = collection_obj.delete_many(conditions)
            
            return result.deleted_count > 0
            
        except Exception as e:
            logging.error(f"MongoDB Delete fehlgeschlagen: {e}")
            return False
    
    def create_table(self, collection_name: str, schema: Dict = None) -> bool:
        """MongoDB Collections erstellen (Schema ist optional)"""
        try:
            if not self.db:
                return False
            
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)
                
                # Validation Schema falls angegeben
                if schema:
                    self.db.command('collMod', collection_name, validator=schema)
                
                return True
            return False
            
        except Exception as e:
            logging.error(f"MongoDB Create Collection fehlgeschlagen: {e}")
            return False
    
    def get_table_schema(self, collection_name: str) -> Dict:
        """MongoDB Collection Schema abrufen"""
        try:
            if not self.db:
                return {}
            
            collection_obj = self.db[collection_name]
            
            # Sample Document analysieren für Schema-Ableitung
            sample = collection_obj.find_one()
            if sample:
                schema = {}
                for key, value in sample.items():
                    schema[key] = type(value).__name__
                return schema
            
            return {}
            
        except Exception as e:
            logging.error(f"MongoDB Get Schema fehlgeschlagen: {e}")
            return {}
    
    def get_tables(self) -> List[str]:
        try:
            if not self.db:
                return []
            
            return self.db.list_collection_names()
            
        except Exception as e:
            logging.error(f"MongoDB Get Collections fehlgeschlagen: {e}")
            return []
    
    def aggregate(self, collection: str, pipeline: List[Dict]) -> List[Dict]:
        """MongoDB Aggregation Pipeline"""
        try:
            if not self.db:
                return []
            
            collection_obj = self.db[collection]
            results = []
            
            for document in collection_obj.aggregate(pipeline):
                # ObjectId zu String konvertieren
                if '_id' in document and isinstance(document['_id'], ObjectId):
                    document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logging.error(f"MongoDB Aggregation fehlgeschlagen: {e}")
            return []
    
    def text_search(self, collection: str, search_term: str) -> List[Dict]:
        """MongoDB Text Search"""
        try:
            if not self.db:
                return []
            
            collection_obj = self.db[collection]
            
            results = []
            cursor = collection_obj.find(
                {'$text': {'$search': search_term}},
                {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'})])
            
            for document in cursor:
                if '_id' in document and isinstance(document['_id'], ObjectId):
                    document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logging.error(f"MongoDB Text Search fehlgeschlagen: {e}")
            return []
    
    def create_index(self, collection: str, fields: List[str], **kwargs) -> bool:
        """MongoDB Index erstellen"""
        try:
            if not self.db:
                return False
            
            collection_obj = self.db[collection]
            
            # Index Spec erstellen
            if len(fields) == 1:
                index_spec = fields[0]
            else:
                index_spec = [(field, pymongo.ASCENDING) for field in fields]
            
            collection_obj.create_index(index_spec, **kwargs)
            return True
            
        except Exception as e:
            logging.error(f"MongoDB Create Index fehlgeschlagen: {e}")
            return False
    
    def get_collection_stats(self, collection: str) -> Dict:
        """MongoDB Collection Statistiken"""
        try:
            if not self.db:
                return {}
            
            stats = self.db.command('collStats', collection)
            
            return {
                'count': stats.get('count', 0),
                'size': stats.get('size', 0),
                'avgObjSize': stats.get('avgObjSize', 0),
                'storageSize': stats.get('storageSize', 0),
                'indexes': stats.get('nindexes', 0)
            }
            
        except Exception as e:
            logging.error(f"MongoDB Collection Stats fehlgeschlagen: {e}")
            return {}


def get_backend_class():
    """Factory-Funktion für MongoDB Backend"""
    return MongoDBDocumentBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_mongodb"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "666ce853d5a741a9026ec5f597ec23b26044f9682a289584e71b9067fc0dc338"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
