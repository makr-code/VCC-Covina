#!/usr/bin/env python3

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class DatabaseType(Enum):
    """Database-Typen für modulares System"""
    VECTOR = "vector"
    GRAPH = "graph"
    RELATIONAL = "relational"
    FILE = "file"
    KEY_VALUE = "key_value"

class DatabaseBackend(Enum):
    """Verfügbare Database-Backends"""
    # Vector Databases
    CHROMADB = "chromadb"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    COZODB_VECTOR = "cozodb_vector"
    COUCHDB = "couchdb"
    
    # Graph Databases
    NEO4J = "neo4j"
    SQLITE_GRAPH = "sqlite_graph"
    ARANGODB = "arangodb"
    CAYLEY = "cayley"
    COZODB_GRAPH = "cozodb_graph"
    HUGEGRAPH = "hugegraph"
    
    # Relational Databases
    SQLITE_RELATIONAL = "sqlite_relational"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    COZODB_RELATIONAL = "cozodb_relational"
    S3 = "s3"
    ACTIVE_DIRECTORY = "active_directory"
    
    # Key-Value Databases
    REDIS = "redis"

    # File-based Backends


@dataclass
class DatabaseConnection:
    """Einheitliche Database-Verbindungsparameter"""
    db_type: DatabaseType
    backend: DatabaseBackend
    enabled: bool = True
    
    # Standard Verbindungsparameter (einheitlich für alle Backends)
    host: str = "localhost"
    port: int = 0
    username: str = ""
    password: str = ""
    database: str = ""
    
    # Dateipfad-basierte Backends (SQLite, CozoDB etc.)
    path: str = ""
    
    # Zusätzliche Backend-spezifische Parameter
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Performance & Caching
    connection_pool_size: int = 10
    query_timeout: int = 30
    cache_ttl: int = 300
    
    def __post_init__(self):
        """Setze Standard-Ports basierend auf Backend"""
        if self.port == 0:
            self.port = self._get_default_port()
    
    def _get_default_port(self) -> int:
        """Standard-Ports für verschiedene Backends"""
        port_mapping = {
            DatabaseBackend.CHROMADB: 8000,
            DatabaseBackend.NEO4J: 7687,
            DatabaseBackend.POSTGRESQL: 5432,
            DatabaseBackend.MONGODB: 27017,
            DatabaseBackend.REDIS: 6379,
            DatabaseBackend.ARANGODB: 8529,
            DatabaseBackend.CAYLEY: 64210,
            DatabaseBackend.HUGEGRAPH: 8080,
            DatabaseBackend.WEAVIATE: 8080,
            DatabaseBackend.PINECONE: 443,
        }
        return port_mapping.get(self.backend, 0)
    
    def get_connection_string(self) -> str:
        """Generiere Verbindungsstring für Backend"""
        if self.backend == DatabaseBackend.NEO4J:
            return f"bolt://{self.host}:{self.port}"
        elif self.backend == DatabaseBackend.POSTGRESQL:
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.backend == DatabaseBackend.MONGODB:
            return f"mongodb://{self.host}:{self.port}/{self.database}"
        elif self.backend == DatabaseBackend.REDIS:
            return f"redis://{self.host}:{self.port}/{self.settings.get('db', 0)}"
        elif self.backend in [DatabaseBackend.SQLITE_GRAPH, DatabaseBackend.SQLITE_RELATIONAL]:
            return self.path
        elif self.backend.value.startswith('cozodb'):
            return self.path
        else:
            return f"http://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiere zu Dictionary für Legacy-Kompatibilität"""
        return {
            'enabled': self.enabled,
            'backend': self.backend.value,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'user': self.username,
            'password': self.password,
            'database': self.database,
            'path': self.path,
            'settings': self.settings,
            'connection_pool_size': self.connection_pool_size,
            'query_timeout': self.query_timeout,
            'cache_ttl': self.cache_ttl,
            'connection_string': self.get_connection_string()
        }

class DatabaseManager:
    """Manager für Database-Konfigurationen"""
    
    def __init__(self):
        self.databases: List[DatabaseConnection] = []
        self._load_default_config()
    
    def _load_default_config(self):
        """Lade Standard-Konfiguration"""
        # Zentrales Namensschema (Prefix + Komponente + ENV)
        PROJECT_PREFIX = os.getenv('PROJECT_PREFIX', 'vcc')
        ENV = os.getenv('ENV', 'prod')

        def make_name(component: str, purpose: str = None) -> str:
            """Generiert standardisierte Namen: {prefix}_{component}_{env}[_purpose]"""
            base = f"{PROJECT_PREFIX}_{component}_{ENV}"
            return f"{base}_{purpose}" if purpose else base

        self.databases = [
            # Vector Database - ChromaDB als primär
            DatabaseConnection(
                db_type=DatabaseType.VECTOR,
                backend=DatabaseBackend.CHROMADB,
                host=os.getenv('CHROMA_CLIENT_HOST', '192.168.178.94'),
                port=int(os.getenv('CHROMA_CLIENT_PORT', 8000)),
                path=os.getenv('CHROMA_PERSIST_PATH', f"./chroma/{make_name('vector')}.db"),
                settings={
                    'mode': 'persistent',
                    'anonymized_telemetry': False,
                    'allow_reset': True,
                    'similarity_threshold': float(os.getenv('CHROMA_SIMILARITY_THRESHOLD', 0.3)),
                    'default_k': int(os.getenv('DEFAULT_K', 5)),
                    'index_name': os.getenv('CHROMA_INDEX_NAME', make_name('vector'))
                }
            ),
            
            # Graph Database - Neo4j als primär (Remote Server 192.168.178.94)
            DatabaseConnection(
                db_type=DatabaseType.GRAPH,
                backend=DatabaseBackend.NEO4J,
                host=os.getenv('NEO4J_HOST', '192.168.178.94'),
                port=int(os.getenv('NEO4J_PORT', 7687)),
                username=os.getenv('NEO4J_USERNAME', 'neo4j'),
                password=os.getenv('NEO4J_PASSWORD', 'v3f3b1d7'),
                database=os.getenv('NEO4J_DATABASE', 'neo4j'),
                settings={
                    'uri': os.getenv('NEO4J_URI', 'neo4j://192.168.178.94:7687'),
                    'db_name': os.getenv('NEO4J_DATABASE', make_name('graph'))
                }
            ),
            
            # PostgreSQL (remote)
            DatabaseConnection(
                db_type=DatabaseType.RELATIONAL,
                backend=DatabaseBackend.POSTGRESQL,
                enabled=True,
                host=os.getenv('POSTGRES_HOST', '192.168.178.94'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                username=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
                database=os.getenv('POSTGRES_DB', make_name('relational')),
                settings={
                    'sslmode': os.getenv('POSTGRES_SSLMODE', 'disable')
                }
            ),
            
            # Key-Value Database - Redis deaktiviert da nicht installiert
            DatabaseConnection(
                db_type=DatabaseType.KEY_VALUE,
                backend=DatabaseBackend.REDIS,
                enabled=False,  # Deaktiviert da Redis nicht läuft
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD', None),
                settings={
                    'db': int(os.getenv('REDIS_DB', 0)),
                    'decode_responses': True
                }
            ),

            # Key-Value via PostgreSQL (als temporärer Proxy/Store)
            DatabaseConnection(
                db_type=DatabaseType.KEY_VALUE,
                backend=DatabaseBackend.POSTGRESQL,
                enabled=True,
                host=os.getenv('POSTGRES_HOST', '192.168.178.94'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                username=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
                database=os.getenv('POSTGRES_KV_DB') or os.getenv('POSTGRES_DB', make_name('relational')),
                settings={
                    'table': 'kv_store',
                    'encoding': 'utf-8'
                }
            ),
            
            # Alternative Vector Database - Pinecone
            DatabaseConnection(
                db_type=DatabaseType.VECTOR,
                backend=DatabaseBackend.PINECONE,
                enabled=False,  # Standardmäßig deaktiviert
                settings={
                    'api_key': os.getenv('PINECONE_API_KEY', ''),
                    'environment': os.getenv('PINECONE_ENVIRONMENT', 'us-east1-gcp'),
                    'index_name': os.getenv('PINECONE_INDEX_NAME', make_name('vector')),
                    'dimension': 384,
                    'metric': 'cosine'
                }
            ),
            
            # Alternative Graph Database - ArangoDB
            DatabaseConnection(
                db_type=DatabaseType.GRAPH,
                backend=DatabaseBackend.ARANGODB,
                enabled=False,
                host=os.getenv('ARANGODB_HOST', 'localhost'),
                port=8529,
                database=os.getenv('ARANGODB_DATABASE', make_name('graph')),
                settings={
                    'graph_name': 'knowledge_graph',
                    'vertex_collection': 'vertices',
                    'edge_collection': 'edges'
                }
            ),

            # CouchDB (remote)
            DatabaseConnection(
                db_type=DatabaseType.FILE,
                backend=DatabaseBackend.COUCHDB,
                enabled=True,
                host=os.getenv('COUCHDB_HOST', '192.168.178.94'),
                port=int(os.getenv('COUCHDB_PORT', 32931)),
                username=os.getenv('COUCHDB_USER', 'couchdb'),
                password=os.getenv('COUCHDB_PASSWORD', 'couchdb'),
                database=os.getenv('COUCHDB_DB', make_name('couch')),
                settings={
                    'protocol': 'http',
                    'max_connections': 10
                }
            ),
            # File-based: Amazon S3
            DatabaseConnection(
                db_type=DatabaseType.FILE,
                backend=DatabaseBackend.S3,
                enabled=False,
                settings={
                    'bucket': os.getenv('S3_BUCKET', make_name('s3')),
                    'region': os.getenv('S3_REGION', 'eu-central-1'),
                    'access_key': os.getenv('S3_ACCESS_KEY', ''),
                    'secret_key': os.getenv('S3_SECRET_KEY', '')
                }
            ),
            # File-based: Active Directory (LDAP) - nur Konfiguration, kein Store
            DatabaseConnection(
                db_type=DatabaseType.FILE,
                backend=DatabaseBackend.ACTIVE_DIRECTORY,
                enabled=False,
                host=os.getenv('AD_HOST', '192.168.178.94'),
                port=int(os.getenv('AD_PORT', 389)),
                username=os.getenv('AD_USER', ''),
                password=os.getenv('AD_PASSWORD', ''),
                settings={
                    'base_dn': os.getenv('AD_BASE_DN', ''),
                    'use_ssl': os.getenv('AD_USE_SSL', 'false').lower() in ('1','true','yes')
                }
            ),
            
            # Hybrid Database - CozoDB (Vector + Graph + Relational)
            DatabaseConnection(
                db_type=DatabaseType.VECTOR,
                backend=DatabaseBackend.COZODB_VECTOR,
                enabled=False,
                path=os.getenv('COZODB_VECTOR_PATH', f"./cozodb/{make_name('cozodb_vector')}.db"),
                settings={
                    'backend_type': 'sqlite',
                    'hnsw_m': 16,
                    'hnsw_ef_construction': 200,
                    'hnsw_ef': 64
                }
            ),
            
            # Enterprise Graph Database - HugeGraph
            DatabaseConnection(
                db_type=DatabaseType.GRAPH,
                backend=DatabaseBackend.HUGEGRAPH,
                enabled=False,
                host=os.getenv('HUGEGRAPH_HOST', 'localhost'),
                port=int(os.getenv('HUGEGRAPH_PORT', 8080)),
                username=os.getenv('HUGEGRAPH_USERNAME', 'admin'),
                password=os.getenv('HUGEGRAPH_PASSWORD', 'admin'),
                settings={
                    'graph_name': os.getenv('HUGEGRAPH_GRAPH', make_name('graph'))
                }
            )
        ]

    def get_database_backend_dict(self) -> Dict[str, Any]:
        """Legacy helper: Liefert ein dict mit Backend-Konfigurationen passend für DatabaseManager.

        Konvertiert die in self.databases gehaltene Liste von DatabaseConnection-Objekten
        in das erwartete dict-Format (keys: vector, graph, relational, file, keyvalue).
        """
        backend_map: Dict[str, Any] = {}
        for conn in self.databases:
            key = conn.db_type.value
            item = conn.to_dict()
            existing = backend_map.get(key)

            # Bevorzuge aktivierte Einträge; fällt auf deaktivierte zurück, wenn kein aktiver vorhanden ist
            if existing is None:
                backend_map[key] = item
            elif not existing.get('enabled', True) and item.get('enabled', True):
                backend_map[key] = item
        return backend_map


def get_database_backend_dict() -> Dict[str, Any]:
    """Module-level helper für Abwärtskompatibilität.

    Erstellt eine lokale DatabaseManager (config.DatabaseManager) Instanz und
    gibt das Backend-Dict zurück, damit externe Module wie
    `database.database_manager.DatabaseManager` initialisiert werden können.
    """
    mgr = DatabaseManager()
    return mgr.get_database_backend_dict()
    
    def get_databases_by_type(self, db_type: DatabaseType) -> List[DatabaseConnection]:
        """Hole alle Datenbanken eines bestimmten Typs"""
        return [db for db in self.databases if db.db_type == db_type and db.enabled]
    
    def get_primary_database(self, db_type: DatabaseType) -> Optional[DatabaseConnection]:
        """Hole primäre Datenbank eines Typs (erste aktivierte)"""
        databases = self.get_databases_by_type(db_type)
        return databases[0] if databases else None
    
    def get_database_by_backend(self, backend: DatabaseBackend) -> Optional[DatabaseConnection]:
        """Hole Datenbank nach Backend-Typ"""
        for db in self.databases:
            if db.backend == backend and db.enabled:
                return db
        return None
    
    def add_database(self, database: DatabaseConnection):
        """Füge neue Datenbank hinzu"""
        self.databases.append(database)
    
    def enable_database(self, backend: DatabaseBackend):
        """Aktiviere Datenbank"""
        for db in self.databases:
            if db.backend == backend:
                db.enabled = True
                break
    
    def disable_database(self, backend: DatabaseBackend):
        """Deaktiviere Datenbank"""
        for db in self.databases:
            if db.backend == backend:
                db.enabled = False
                break
    
    def get_legacy_config(self) -> Dict[str, Any]:
        """Generiere Legacy-kompatible Konfiguration"""
        config = {
            'vector': {},
            'graph': {},
            'relational': {},
            'key_value': {},
            'features': {
                'graph_integration': True,
                'semantic_search': True,
                'relationship_extraction': True,
                'entity_recognition': True,
                'metadata_enhancement': True,
                'auto_fallback': True
            },
            'performance': {
                'connection_pool_size': 10,
                'query_timeout': 30,
                'cache_ttl': 300,
                'batch_size': 100
            }
        }
        
        # Primäre Datenbanken setzen
        for db_type in DatabaseType:
            primary_db = self.get_primary_database(db_type)
            if primary_db:
                config[db_type.value] = primary_db.to_dict()
        
        return config
    
    def list_databases(self) -> str:
        """Erstelle lesbare Liste aller Datenbanken"""
        output = []
        for db_type in DatabaseType:
            databases = self.get_databases_by_type(db_type)
            output.append(f"\n{db_type.value.upper()} DATABASES:")
            if databases:
                for db in databases:
                    status = "✅ AKTIV" if db.enabled else "❌ DEAKTIVIERT"
                    output.append(f"  - {db.backend.value}: {status}")
                    output.append(f"    Connection: {db.get_connection_string()}")
            else:
                output.append("  - Keine Datenbanken konfiguriert")
        
        return "\n".join(output)

# Globale Instanz für einfache Verwendung
database_manager = DatabaseManager()

# Helper-Funktionen für Legacy-Kompatibilität
def get_database_config() -> Dict[str, Any]:
    """Hole Legacy-kompatible DATABASE_CONFIG"""
    return database_manager.get_legacy_config()

def get_vector_database() -> Optional[DatabaseConnection]:
    """Hole primäre Vector Database"""
    return database_manager.get_primary_database(DatabaseType.VECTOR)

def get_graph_database() -> Optional[DatabaseConnection]:
    """Hole primäre Graph Database"""
    return database_manager.get_primary_database(DatabaseType.GRAPH)

def get_relational_database() -> Optional[DatabaseConnection]:
    """Hole primäre Relational Database"""
    return database_manager.get_primary_database(DatabaseType.RELATIONAL)

def get_key_value_database() -> Optional[DatabaseConnection]:
    """Hole primäre Key-Value Database"""
    return database_manager.get_primary_database(DatabaseType.KEY_VALUE)

def get_file_database() -> Optional[DatabaseConnection]:
    """Hole primäre File-based Database"""
    return database_manager.get_primary_database(DatabaseType.FILE)

if __name__ == "__main__":
    # Test der neuen Konfiguration
    print("=== VERITAS DATABASE CONFIGURATION ===")
    print(database_manager.list_databases())
    
    print("\n=== LEGACY-KOMPATIBLE KONFIGURATION ===")
    legacy_config = get_database_config()
    for key, value in legacy_config.items():
        if isinstance(value, dict) and 'backend' in value:
            print(f"{key.upper()}: {value['backend']} ({value.get('connection_string', 'N/A')})")
