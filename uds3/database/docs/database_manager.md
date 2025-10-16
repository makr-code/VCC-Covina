# Database_manager.py - VERITAS Multi-Backend Database Manager

## Überblick
Zentraler Database Manager für dynamische Backend-Verwaltung mit Multi-Database-Architektur (Vector, Graph, Relational) und Factory-Pattern-basierter Instanziierung.

## Aktueller Stand

### Hauptfunktionalität
- **Multi-Backend Management**: Vector, Graph, Relational Database Backends
- **Dynamic Loading**: Factory-Pattern für flexible Backend-Konfiguration
- **Unified Interface**: Einheitliche API für alle Database-Operationen
- **Connection Management**: Automatische Verbindungsherstellung und -überwachung
- **Error Handling**: Robuste Fehlerbehandlung und Fallback-Mechanismen

### Supported Database Backends
```python
SUPPORTED_BACKENDS = {
    'vector': [
        'ChromaDB', 'Pinecone', 'Weaviate', 'Redis Vector'
    ],
    'graph': [
        'Neo4j', 'ArangoDB', 'HugeGraph', 'Cayley'
    ],
    'relational': [
        'SQLite', 'PostgreSQL', 'MongoDB', 'CozoDB'
    ]
}
```

### Architecture Pattern
- **Factory Pattern**: Dynamische Backend-Erstellung
- **Strategy Pattern**: Austauschbare Database-Strategien
- **Adapter Pattern**: Einheitliche Interface-Abstraktion
- **Facade Pattern**: Vereinfachte Multi-Backend-Operationen

## Architektur

### Core Components
```
DatabaseManager
├── Backend Factory
│   ├── Dynamic Module Loading
│   ├── Configuration Parsing
│   ├── Instance Creation
│   └── Dependency Injection
├── Connection Management
│   ├── Connection Pooling
│   ├── Health Monitoring
│   ├── Automatic Reconnection
│   └── Load Balancing
├── Unified API Layer
│   ├── Vector Operations
│   ├── Graph Operations
│   ├── Relational Operations
│   └── Cross-Backend Queries
└── Error Handling
    ├── Fallback Mechanisms
    ├── Circuit Breaker Pattern
    ├── Retry Logic
    └── Error Recovery
```

### Backend Architecture
```python
class DatabaseManager:
    def __init__(self, backend_dict):
        self.vector_backend = None      # ChromaDB, Pinecone, etc.
        self.graph_backend = None       # Neo4j, ArangoDB, etc.
        self.relational_backend = None  # SQLite, PostgreSQL, etc.
        
        self._initialize_backends(backend_dict)
        self._setup_health_monitoring()
        self._configure_failover()
```

## Implementation Details

### Dynamic Backend Loading
```python
def _initialize_backends(self, backend_dict: Dict[str, Any]):
    """Dynamische Backend-Initialisierung basierend auf Konfiguration"""
    
    # Vector Backend
    vector_conf = backend_dict.get('vector')
    if isinstance(vector_conf, dict) and vector_conf.get('enabled'):
        backend_type = vector_conf.get('type', 'chromadb')
        
        if backend_type == 'chromadb':
            from database_api_chromadb import ChromaVectorBackend
            conf = {k: v for k, v in vector_conf.items() if k not in ['enabled', 'type']}
            self.vector_backend = ChromaVectorBackend(conf)
            
        elif backend_type == 'pinecone':
            from database_api_pinecone import PineconeVectorBackend
            self.vector_backend = PineconeVectorBackend(vector_conf)
            
        # Weitere Vector Backends...
        
        self.vector_backend.connect()
        self.logger.info(f"Vector Backend '{backend_type}' erfolgreich initialisiert")
    
    # Graph Backend
    graph_conf = backend_dict.get('graph')
    if isinstance(graph_conf, dict) and graph_conf.get('enabled'):
        backend_type = graph_conf.get('type', 'neo4j')
        
        if backend_type == 'neo4j':
            from database_api_neo4j import Neo4jGraphBackend
            conf = {k: v for k, v in graph_conf.items() if k not in ['enabled', 'type']}
            self.graph_backend = Neo4jGraphBackend(conf)
            
        elif backend_type == 'arangodb':
            from database_api_arangodb import ArangoGraphBackend
            self.graph_backend = ArangoGraphBackend(graph_conf)
            
        self.graph_backend.connect()
        self.logger.info(f"Graph Backend '{backend_type}' erfolgreich initialisiert")
    
    # Relational Backend
    relational_conf = backend_dict.get('relational')
    if isinstance(relational_conf, dict) and relational_conf.get('enabled'):
        backend_type = relational_conf.get('type', 'sqlite')
        
        if backend_type == 'sqlite':
            from database_api_sqlite_relational import SQLiteRelationalBackend
            self.relational_backend = SQLiteRelationalBackend(relational_conf)
            
        elif backend_type == 'postgresql':
            from database_api_postgresql import PostgreSQLBackend
            self.relational_backend = PostgreSQLBackend(relational_conf)
            
        self.relational_backend.connect()
        self.logger.info(f"Relational Backend '{backend_type}' erfolgreich initialisiert")
```

### Unified Query Interface
```python
def store_document(self, document: Dict[str, Any], collection_name: str) -> Dict[str, bool]:
    """Unified Document Storage über alle verfügbaren Backends"""
    
    results = {
        'vector': False,
        'graph': False,
        'relational': False,
        'success': False
    }
    
    document_id = document.get('id', str(uuid.uuid4()))
    
    # Vector Storage für semantische Suche
    if self.vector_backend:
        try:
            if 'embedding' not in document and 'text' in document:
                document['embedding'] = self._generate_embedding(document['text'])
            
            success = self.vector_backend.store_document(document, collection_name)
            results['vector'] = success
            
        except Exception as e:
            self.logger.error(f"Vector storage failed: {e}")
    
    # Graph Storage für Beziehungen
    if self.graph_backend:
        try:
            # Knoten für Dokument erstellen
            node_data = {
                'id': document_id,
                'title': document.get('title', ''),
                'type': document.get('document_type', 'document'),
                'collection': collection_name
            }
            
            success = self.graph_backend.create_node('Document', node_data)
            results['graph'] = success
            
            # Beziehungen zu anderen Dokumenten erstellen
            if 'references' in document:
                self._create_document_relationships(document_id, document['references'])
                
        except Exception as e:
            self.logger.error(f"Graph storage failed: {e}")
    
    # Relational Storage für Metadaten
    if self.relational_backend:
        try:
            metadata = {
                'document_id': document_id,
                'title': document.get('title', ''),
                'collection_name': collection_name,
                'document_type': document.get('document_type', ''),
                'created_date': document.get('created_date', ''),
                'file_path': document.get('file_path', ''),
                'processing_status': 'completed'
            }
            
            success = self.relational_backend.store_metadata(metadata)
            results['relational'] = success
            
        except Exception as e:
            self.logger.error(f"Relational storage failed: {e}")
    
    # Gesamterfolg wenn mindestens 2 von 3 Backends erfolgreich
    success_count = sum([results['vector'], results['graph'], results['relational']])
    results['success'] = success_count >= 2
    
    return results
```

### Cross-Backend Search
```python
def search_documents(self, 
                    query: str, 
                    collection_name: str = None,
                    search_type: str = 'hybrid',
                    limit: int = 10) -> List[Dict[str, Any]]:
    """Multi-Backend Document Search mit verschiedenen Strategien"""
    
    results = []
    
    if search_type in ['semantic', 'hybrid']:
        # Semantische Suche über Vector Backend
        if self.vector_backend:
            try:
                vector_results = self.vector_backend.similarity_search(
                    query, collection_name, limit
                )
                
                # Ergebnisse mit Metadaten anreichern
                for result in vector_results:
                    if self.relational_backend:
                        metadata = self.relational_backend.get_document_metadata(
                            result.get('id')
                        )
                        result.update(metadata or {})
                    
                    result['search_type'] = 'semantic'
                    result['backend'] = 'vector'
                
                results.extend(vector_results)
                
            except Exception as e:
                self.logger.error(f"Vector search failed: {e}")
    
    if search_type in ['graph', 'hybrid']:
        # Graph-basierte Suche für Beziehungen
        if self.graph_backend:
            try:
                graph_results = self.graph_backend.search_related_documents(
                    query, collection_name, limit
                )
                
                for result in graph_results:
                    result['search_type'] = 'graph'
                    result['backend'] = 'graph'
                
                results.extend(graph_results)
                
            except Exception as e:
                self.logger.error(f"Graph search failed: {e}")
    
    if search_type in ['metadata', 'hybrid']:
        # Metadaten-Suche über Relational Backend
        if self.relational_backend:
            try:
                metadata_results = self.relational_backend.search_metadata(
                    query, collection_name, limit
                )
                
                for result in metadata_results:
                    result['search_type'] = 'metadata'
                    result['backend'] = 'relational'
                
                results.extend(metadata_results)
                
            except Exception as e:
                self.logger.error(f"Metadata search failed: {e}")
    
    # Duplikate entfernen und nach Relevanz sortieren
    unique_results = self._deduplicate_results(results)
    ranked_results = self._rank_hybrid_results(unique_results)
    
    return ranked_results[:limit]
```

### Health Monitoring
```python
def health_check(self) -> Dict[str, Any]:
    """Umfassende Gesundheitsprüfung aller Backends"""
    
    health_status = {
        'overall_status': 'healthy',
        'backends': {},
        'timestamp': datetime.now().isoformat()
    }
    
    backend_health = []
    
    # Vector Backend Health
    if self.vector_backend:
        try:
            vector_health = self.vector_backend.health_check()
            health_status['backends']['vector'] = vector_health
            backend_health.append(vector_health.get('status') == 'healthy')
        except Exception as e:
            health_status['backends']['vector'] = {'status': 'unhealthy', 'error': str(e)}
            backend_health.append(False)
    
    # Graph Backend Health
    if self.graph_backend:
        try:
            graph_health = self.graph_backend.health_check()
            health_status['backends']['graph'] = graph_health
            backend_health.append(graph_health.get('status') == 'healthy')
        except Exception as e:
            health_status['backends']['graph'] = {'status': 'unhealthy', 'error': str(e)}
            backend_health.append(False)
    
    # Relational Backend Health
    if self.relational_backend:
        try:
            relational_health = self.relational_backend.health_check()
            health_status['backends']['relational'] = relational_health
            backend_health.append(relational_health.get('status') == 'healthy')
        except Exception as e:
            health_status['backends']['relational'] = {'status': 'unhealthy', 'error': str(e)}
            backend_health.append(False)
    
    # Overall Status bestimmen
    healthy_count = sum(backend_health)
    total_count = len(backend_health)
    
    if healthy_count == total_count:
        health_status['overall_status'] = 'healthy'
    elif healthy_count >= total_count // 2:
        health_status['overall_status'] = 'degraded'
    else:
        health_status['overall_status'] = 'unhealthy'
    
    health_status['healthy_backends'] = healthy_count
    health_status['total_backends'] = total_count
    
    return health_status
```

## Zusätzliche Komponenten (Kurzbeschreibung)

- KGE-Queue (lightweight SQLite):
    - Implementiert in `database_api.py`. Bietet `kge_tasks`, `kge_results` und `enrichment_logs` Tabellen zur Persistenz von Task- und Ergebnisdaten.
    - Funktionen: `kge_enqueue_task`, `kge_fetch_next_pending_task`, `kge_set_task_status`, `kge_store_result`, `kge_get_task_result`, `kge_get_queue_size`, `enrichment_log`.
    - Zweck: zuverlässige, lokale Task-Persistenz ohne zusätzliches externes System.

- PersistentBackupManager:
    - Multi-Storage Backup (SQLite + JSON + Cache-SQLite) zur Wiederherstellung aus anstehenden Operationen nach Absturz.
    - Nutzt lokale Dateien in einem konfigurierbaren Backup-Ordner (standard: `./database_backup`).

- AdaptiveBatchProcessor:
    - Asynchroner, adaptiver Batch-Worker mit persistentem Backup- und Cache-Support.
    - Passt Batch-Größe dynamisch an, nutzt Metriken (operations/sec, queue pressure, avg batch time), und startet eine Hintergrund-Thread-Loop.

- Module Status Manager (optional):
    - `database_manager.py` integriert optionales Monitoring über `module_status_manager` (Registrierung via `safe_register_module`, Status-Updates via `update_status`).
    - Ermöglicht zentralisiertes Health-Reporting (z.B. INITIALIZING, HEALTHY, ERROR, CRITICAL, OFFLINE).

- AdapterGovernance:
    - Richtlinien-Wrapper (AdapterGovernance) steuert Verhalten wie `strict` vs. `lenient` Mode für Backends.

## Kurze Qualitätsprüfung (Checkliste vor Deployment)

1. Sicherstellen, dass die lokalen SQLite-Dateien (z. B. `veritas_backend.sqlite`) beschreibbar sind.
2. Falls Konnektivität zu entfernten Backends (Neo4j, Chroma, Redis) erwartet wird: entsprechende Clients/Libraries installieren und Umgebungsvariablen setzen.
3. `dm.verify_backends()` ausführen und Log-Ausgaben prüfen (WARN/ERROR für fehlende Backends).
4. Backup-Ordner überprüfen (`./database_backup`) und Schreibrechte sicherstellen.
5. (Optional) `module_status_manager` verfügbar machen für zentrales Monitoring.

## Roadmap 2025-2026

### Q1 2025: Advanced Backend Support
- [ ] **New Database Backends**
  - Elasticsearch Vector Support
  - MemGraph Graph Database
  - CockroachDB Distributed SQL
  - Redis Enterprise Multi-Model

- [ ] **Connection Optimization**
  - Advanced Connection Pooling
  - Load Balancing Algorithms
  - Automatic Failover
  - Circuit Breaker Implementation

### Q2 2025: Performance Enhancement
- [ ] **Query Optimization**
  - Query Plan Optimization
  - Cross-Backend Join Operations
  - Intelligent Query Routing
  - Result Caching Strategies

- [ ] **Scalability Features**
  - Horizontal Scaling Support
  - Distributed Query Processing
  - Partition Management
  - Auto-scaling Backends

### Q3 2025: AI Integration
- [ ] **ML-Enhanced Operations**
  - Predictive Query Optimization
  - Intelligent Backend Selection
  - Automated Index Management
  - Performance Anomaly Detection

- [ ] **Advanced Analytics**
  - Cross-Backend Analytics
  - Real-time Performance Monitoring
  - Query Pattern Analysis
  - Resource Usage Optimization

### Q4 2025: Enterprise Features
- [ ] **High Availability**
  - Multi-Region Support
  - Disaster Recovery
  - Backup Automation
  - Zero-Downtime Upgrades

- [ ] **Security Enhancement**
  - End-to-end Encryption
  - Fine-grained Access Control
  - Audit Logging
  - Compliance Frameworks

### Q1 2026: Next-Generation Architecture
- [ ] **Cloud-Native Features**
  - Kubernetes Native Deployment
  - Serverless Backend Support
  - Edge Computing Integration
  - Global Distribution

- [ ] **Advanced Automation**
  - Self-healing Databases
  - Autonomous Optimization
  - Predictive Maintenance
  - Intelligent Resource Management

## Configuration

### Backend Configuration
```python
DATABASE_MANAGER_CONFIG = {
    'vector': {
        'enabled': True,
        'type': 'chromadb',
        'config': {
            'host': 'localhost',
            'port': 8000,
            'collection_prefix': 'veritas_'
        }
    },
    'graph': {
        'enabled': True,
        'type': 'neo4j',
        'config': {
            'uri': 'bolt://localhost:7687',
            'username': 'neo4j',
            'password': 'password'
        }
    },
    'relational': {
        'enabled': True,
        'type': 'sqlite',
        'config': {
            'database_path': 'databases/veritas.db',
            'enable_wal': True
        }
    }
}
```

### Performance Settings
```python
PERFORMANCE_CONFIG = {
    'connection_pool_size': 20,
    'query_timeout': 30,
    'retry_attempts': 3,
    'circuit_breaker_threshold': 5,
    'cache_ttl': 300,
    'batch_size': 100
}
```

## Dependencies

### Core Dependencies
- `database_api_base`: Abstract base classes
- `importlib`: Dynamic module loading
- `logging`: System logging
- `uuid`: Unique identifier generation

### Backend Dependencies
- `chromadb`: Vector database
- `neo4j`: Graph database
- `sqlite3`: Relational database
- `redis`: Cache and vector support

### Optional Dependencies
- `asyncio`: Asynchronous operations
- `aiofiles`: Async file operations
- `prometheus_client`: Metrics collection
- `structlog`: Structured logging

## Performance Metrics

### Current Performance
- **Multi-Backend Query**: 50-200ms
- **Document Storage**: 100-500ms
- **Health Check**: < 50ms
- **Connection Overhead**: < 10ms

### Target Performance (2026)
- **Multi-Backend Query**: 20-100ms
- **Document Storage**: 50-200ms
- **Health Check**: < 20ms
- **Connection Overhead**: < 5ms

## Status
- **Version**: 1.3 Production
- **Features**: ✅ Multi-Backend ✅ Dynamic Loading ✅ Unified API ✅ Health Monitoring
- **Backends**: ✅ Vector ✅ Graph ✅ Relational ✅ Factory Pattern
- **Performance**: ✅ Connection Pooling ✅ Query Optimization ✅ Error Handling
- **Integration**: ✅ UDS3 ✅ Configuration ✅ Monitoring ✅ APIs
- **Stability**: Production Ready ✅
- **Maintainer**: VERITAS Core Team
- **Last Update**: 31. August 2025
