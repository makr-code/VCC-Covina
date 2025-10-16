#!/usr/bin/env python3
"""
Database API Base Classes
Abstrakte Basis-Klassen für alle Database-Backends
Mit integriertem Adaptive Batch Processing für optimale Performance
"""

import logging
import os
import json
import uuid
import time
import threading
import queue
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from datetime import datetime

NodeIdentifier = Union[str, Tuple[str, Any], Dict[str, Any]]
RelationshipIdentifier = Union[str, Tuple[str, Any], Dict[str, Any]]

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy, DatabaseRole, OperationType
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    logging.debug("UDS3 Core nicht verfügbar - verwende Fallback-Implementierung")

# AdaptiveBatchProcessor Import
try:
    from .adaptive_batch_processor import AdaptiveBatchProcessor
    logger = logging.getLogger(__name__)
    logger.debug("✅ AdaptiveBatchProcessor imported successfully")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ AdaptiveBatchProcessor import failed: {e}")
    
    # Fallback Mock Implementation
    class AdaptiveBatchProcessor:
        def __init__(self, *args, **kwargs):
            self.operation_type = kwargs.get('operation_type', 'unknown')
        
        def queue_operation(self, operation_data):
            return True
        
        def get_adaptive_stats(self):
            return {'operation_type': self.operation_type, 'status': 'fallback_mock'}


class DatabaseBackend(ABC):
    """Enhanced Abstract Base Class mit Adaptive Batch Processing und UDS3-Integration"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._adaptive_processors = {}  # Dictionary für verschiedene Operation-Types
        self._is_connected = False
        
        # UDS3-Integration
        self.uds3_strategy = None
        self.uds3_enabled = UDS3_AVAILABLE and self.config.get('uds3_enabled', True)
        
        if self.uds3_enabled and UDS3_AVAILABLE:
            try:
                self.uds3_strategy = UnifiedDatabaseStrategy(
                    security_level=self.config.get('uds3_security_level'),
                    strict_quality=self.config.get('uds3_strict_quality', False)
                )
                self.logger.info(f"✅ UDS3-Integration aktiviert für {self.__class__.__name__}")
            except Exception as e:
                self.logger.warning(f"⚠️ UDS3-Initialisierung fehlgeschlagen: {e}")
                self.uds3_strategy = None
                self.uds3_enabled = False
    
    def _initialize_adaptive_batch_processing(self):
        """Initialize adaptive batch processors for common operations (Mock-Implementation)"""
        try:
            # Mock AdaptiveBatchProcessor für Stabilität
            class MockAdaptiveBatchProcessor:
                def __init__(self, backend, operation_type, batch_executor=None):
                    self.backend = backend
                    self.operation_type = operation_type
                    self.batch_executor = batch_executor
                    self.queued_operations = []
                
                def queue_operation(self, operation_data):
                    self.queued_operations.append(operation_data)
                    return True
                
                def get_adaptive_stats(self):
                    return {
                        'operation_type': self.operation_type,
                        'queued_count': len(self.queued_operations),
                        'backend': self.backend.__class__.__name__
                    }
            
            # Initialize different processors for different operation types
            self._adaptive_processors['insert'] = MockAdaptiveBatchProcessor(
                self, "insert", 
                batch_executor=getattr(self, '_batch_insert_executor', None)
            )
            
            self._adaptive_processors['update'] = MockAdaptiveBatchProcessor(
                self, "update", 
                batch_executor=getattr(self, '_batch_update_executor', None)
            )
            
            self._adaptive_processors['delete'] = MockAdaptiveBatchProcessor(
                self, "delete",
                batch_executor=getattr(self, '_batch_delete_executor', None)
            )
            
            self.logger.info(f"✅ Mock Adaptive batch processing initialized for {self.__class__.__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adaptive batch processing: {e}")
    
    def queue_batch_operation(self, operation_type: str, operation_data: Dict) -> bool:
        """Queue an operation for adaptive batch processing"""
        if operation_type not in self._adaptive_processors:
            self.logger.debug(f"No adaptive processor for operation type: {operation_type}")
            return self._execute_immediate_operation(operation_type, operation_data)
        
        return self._adaptive_processors[operation_type].queue_operation(operation_data)
    
    def _execute_immediate_operation(self, operation_type: str, operation_data: Dict) -> bool:
        """Fallback for immediate operation execution"""
        # To be implemented by specific backends
        self.logger.debug(f"Immediate execution: {operation_type}")
        return True
    
    def get_all_adaptive_stats(self) -> Dict:
        """Get statistics for all adaptive processors"""
        stats = {}
        for op_type, processor in self._adaptive_processors.items():
            stats[op_type] = processor.get_adaptive_stats()
        
        # Add backend-specific stats
        stats['backend_type'] = self.get_backend_type()
        stats['is_connected'] = self._is_connected
        stats['total_processors'] = len(self._adaptive_processors)
        
        return stats
    
    def flush_all_adaptive_batches(self):
        """Flush all pending operations in all processors"""
        for op_type, processor in self._adaptive_processors.items():
            processor.flush_pending()
    
    def stop_all_adaptive_processing(self):
        """Stop all adaptive processors gracefully"""
        for op_type, processor in self._adaptive_processors.items():
            processor.stop()
    
    def is_duplicate(self, file_hash: str, collection_name: str = None) -> bool:
        """
        Standard-Duplikatprüfung per Hash. Sollte von konkreten Backends überschrieben werden.
        Gibt False zurück, wenn keine Duplikatprüfung möglich ist.
        """
        # Default: Kein Duplikat-Check implementiert
        return False

    def log_duplicate(self, file_hash: str, collection_name: str = None):
        """
        Loggt einen Duplikat-Fall. Kann von Backends überschrieben werden.
        """
        logging.info(f"[DUPLICATE] Datei mit Hash {file_hash} bereits in Collection '{collection_name}' vorhanden.")
    
    # ==============================
    # UDS3-INTEGRATION METHODS
    # ==============================
    
    def get_uds3_metadata(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generiert UDS3-kompatible Metadaten für ein Dokument"""
        if not self.uds3_enabled or not self.uds3_strategy:
            return {}
        
        try:
            # Basis UDS3-Metadaten
            uds3_metadata = {
                'uds3_document_id': str(uuid.uuid4()),
                'uds3_created_at': datetime.now().isoformat(),
                'uds3_backend_type': self.__class__.__name__,
                'uds3_processing_stage': 'stored',
                'uds3_quality_score': document_data.get('quality_score', 0.8),
                'uds3_content_hash': self._generate_content_hash(document_data),
                'uds3_schema_version': '3.0'
            }
            
            # Erweiterte UDS3-Metadaten durch Strategy
            enhanced_metadata = self.uds3_strategy.enhance_document_metadata(
                document_data, 
                database_role=self._get_database_role(),
                backend_info={
                    'backend_class': self.__class__.__name__,
                    'supports_transactions': hasattr(self, 'begin_transaction'),
                    'supports_batch': bool(self._adaptive_processors)
                }
            )
            
            uds3_metadata.update(enhanced_metadata)
            return uds3_metadata
            
        except Exception as e:
            self.logger.warning(f"UDS3-Metadaten-Generierung fehlgeschlagen: {e}")
            return {}
    
    def _get_database_role(self) -> 'DatabaseRole':
        """Bestimmt die UDS3-Datenbankrolle basierend auf Backend-Typ"""
        if not UDS3_AVAILABLE:
            return None
            
        class_name = self.__class__.__name__.lower()
        
        if any(term in class_name for term in ['vector', 'embedding', 'semantic']):
            return DatabaseRole.VECTOR
        elif any(term in class_name for term in ['graph', 'neo4j', 'arangodb', 'cayley']):
            return DatabaseRole.GRAPH
        else:
            return DatabaseRole.RELATIONAL
    
    def _generate_content_hash(self, document_data: Dict[str, Any]) -> str:
        """Generiert Content-Hash für UDS3-Integrität"""
        try:
            # Wichtige Felder für Hash-Generierung
            hash_content = {
                'content': document_data.get('content', ''),
                'file_path': document_data.get('file_path', ''),
                'file_size': document_data.get('file_size', 0),
                'mime_type': document_data.get('mime_type', '')
            }
            
            content_str = json.dumps(hash_content, sort_keys=True)
            return str(hash(content_str))
            
        except Exception:
            return str(uuid.uuid4())
    
    def validate_uds3_consistency(self, document_id: str) -> Dict[str, Any]:
        """Validiert UDS3-Konsistenz für ein Dokument"""
        if not self.uds3_enabled or not self.uds3_strategy:
            return {'uds3_consistent': False, 'reason': 'UDS3 nicht verfügbar'}
        
        try:
            return self.uds3_strategy.validate_cross_database_consistency(
                document_id=document_id,
                backend_type=self.__class__.__name__
            )
        except Exception as e:
            return {'uds3_consistent': False, 'error': str(e)}
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Erweiterte Backend-Informationen mit UDS3-Status"""
        base_info = {
            'backend_class': self.__class__.__name__,
            'is_connected': self._is_connected,
            'adaptive_processors': list(self._adaptive_processors.keys()),
            'config_keys': list(self.config.keys())
        }
        
        if self.uds3_enabled:
            base_info.update({
                'uds3_enabled': True,
                'uds3_strategy_version': getattr(self.uds3_strategy, 'version', 'unknown'),
                'uds3_database_role': str(self._get_database_role()) if self._get_database_role() else None,
                'uds3_security_level': self.config.get('uds3_security_level', 'standard')
            })
        else:
            base_info['uds3_enabled'] = False
            
        return base_info
    
    @abstractmethod
    def connect(self) -> bool:
        """Stelle Verbindung zur Datenbank her"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Schließe Datenbankverbindung"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Prüfe ob Datenbank verfügbar ist"""
        pass
    
    @abstractmethod
    def get_backend_type(self) -> str:
        """Gibt den Backend-Typ zurück"""
        pass

class VectorDatabaseBackend(DatabaseBackend):
    """Enhanced Abstract Base für Vektor-Datenbanken mit Adaptive Batch Processing"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
    
    def connect(self) -> bool:
        """Enhanced connect with adaptive batch initialization"""
        success = self._backend_connect() if hasattr(self, '_backend_connect') else self._connect_impl()
        if success:
            self._is_connected = True
            self._initialize_adaptive_batch_processing()
            # Initialize vector-specific processors
            self._initialize_vector_batch_processors()
        return success
    
    def _connect_impl(self) -> bool:
        """Default implementation - to be overridden"""
        return True
    
    def _initialize_vector_batch_processors(self):
        """Initialize vector-specific adaptive batch processors"""
        try:
            # Vector-specific operations
            self._adaptive_processors['add_documents'] = AdaptiveBatchProcessor(
                self, "add_documents",
                base_batch_size=50,  # Vectors benefit from larger batches
                max_batch_size=500,
                batch_executor=getattr(self, '_batch_add_documents_executor', None)
            )
            
            self._adaptive_processors['add_vectors'] = AdaptiveBatchProcessor(
                self, "add_vectors",
                base_batch_size=100,  # Pure vectors can handle even larger batches
                max_batch_size=1000,
                batch_executor=getattr(self, '_batch_add_vectors_executor', None)
            )
            
            self.logger.info("✅ Vector-specific adaptive batch processors initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector batch processors: {e}")
    
    def batch_add_documents(self, collection_name: str, documents: List[str], 
                           metadatas: List[Dict], ids: List[str]) -> bool:
        """Queue documents for adaptive batch processing"""
        operation_data = {
            'type': 'add_documents',
            'collection_name': collection_name,
            'documents': documents,
            'metadatas': metadatas,
            'ids': ids
        }
        return self.queue_batch_operation('add_documents', operation_data)
    
    def batch_add_vector(self, vector_id: str, vector: List[float], 
                        metadata: Dict = None, collection_name: str = None) -> bool:
        """Queue vector for adaptive batch processing"""
        operation_data = {
            'type': 'add_vector',
            'vector_id': vector_id,
            'vector': vector,
            'metadata': metadata,
            'collection_name': collection_name
        }
        return self.queue_batch_operation('add_vectors', operation_data)
    
    @abstractmethod
    def create_collection(self, name: str, metadata: Dict = None) -> bool:
        """Erstelle eine neue Collection"""
        pass
    
    @abstractmethod
    def get_collection(self, name: str):
        """Hole eine bestehende Collection"""
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """Liste alle Collections"""
        pass
    
    @abstractmethod
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadatas: List[Dict], ids: List[str]) -> bool:
        """Füge Dokumente zur Collection hinzu"""
        pass
    
    @abstractmethod
    def add_vector(self, vector_id: str, vector: List[float], metadata: Dict = None) -> bool:
        """Füge einen einzelnen Vektor hinzu"""
        pass
    
    @abstractmethod
    def search_similar(self, collection_name: str, query: str, 
                      n_results: int = 5) -> List[Dict]:
        """Suche ähnliche Dokumente"""
        pass
    
    @abstractmethod
    def search_vectors(self, query_vector: List[float], top_k: int = 10, 
                      collection_name: str = None) -> List[Dict]:
        """Suche nach ähnlichen Vektoren basierend auf einem Abfrage-Vektor"""
        pass

class GraphDatabaseBackend(DatabaseBackend):
    """Enhanced Abstract Base für Graph-Datenbanken mit Adaptive Batch Processing"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
    
    def connect(self) -> bool:
        """Enhanced connect with adaptive batch initialization"""
        success = self._backend_connect() if hasattr(self, '_backend_connect') else self._connect_impl()
        if success:
            self._is_connected = True
            self._initialize_adaptive_batch_processing()
            # Initialize graph-specific processors
            self._initialize_graph_batch_processors()
        return success
    
    def _connect_impl(self) -> bool:
        """Default implementation - to be overridden"""
        return True
    
    def _initialize_graph_batch_processors(self):
        """Initialize graph-specific adaptive batch processors"""
        try:
            # Graph-specific operations
            self._adaptive_processors['create_nodes'] = AdaptiveBatchProcessor(
                self, "create_nodes",
                base_batch_size=30,  # Nodes can be batched efficiently
                max_batch_size=300,
                batch_executor=getattr(self, '_batch_create_nodes_executor', None)
            )
            
            self._adaptive_processors['create_edges'] = AdaptiveBatchProcessor(
                self, "create_edges",
                base_batch_size=20,  # Edges might need more validation
                max_batch_size=200,
                batch_executor=getattr(self, '_batch_create_edges_executor', None)
            )
            
            self.logger.info("✅ Graph-specific adaptive batch processors initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize graph batch processors: {e}")
    
    def batch_create_node(self, node_type: str, properties: Dict) -> bool:
        """Queue node creation for adaptive batch processing"""
        operation_data = {
            'type': 'create_node',
            'node_type': node_type,
            'properties': properties
        }
        return self.queue_batch_operation('create_nodes', operation_data)
    
    def batch_create_edge(self, from_id: str, to_id: str, edge_type: str, 
                         properties: Dict = None) -> bool:
        """Queue edge creation for adaptive batch processing"""
        operation_data = {
            'type': 'create_edge',
            'from_id': from_id,
            'to_id': to_id,
            'edge_type': edge_type,
            'properties': properties or {}
        }
        return self.queue_batch_operation('create_edges', operation_data)
    
    @abstractmethod
    def create_node(self, node_type: str, properties: Dict) -> str:
        """Erstelle einen Knoten"""
        pass
    
    @abstractmethod
    def create_edge(self, from_id: str, to_id: str, edge_type: str, 
                   properties: Dict = None) -> str:
        """Erstelle eine Kante zwischen Knoten"""
        pass
    
    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Hole einen Knoten"""
        pass
    
    @abstractmethod
    def find_nodes(self, node_type: str, filters: Dict = None) -> List[Dict]:
        """Finde Knoten nach Typ und Filtern"""
        pass
    
    @abstractmethod
    def get_relationships(self, node_id: str, direction: str = "both") -> List[Dict]:
        """Hole Beziehungen eines Knotens"""
        pass

    # ------------------------------------------------------------------
    # High-Level Relationship Lifecycle Operations

    def delete_relationship(self, edge_id: RelationshipIdentifier) -> bool:
        """Löscht eine Relationship anhand eines beliebigen Identifiers.

        Implementierungen sollten Business-Identifier (Label::ID, Mapping-Dicts) sowie
        native elementIds akzeptieren. Default verweist auf NotImplemented.
        """

        raise NotImplementedError("delete_relationship ist für dieses Backend nicht implementiert")

    def update_relationship_weight(
        self,
        relationship_id: RelationshipIdentifier,
        *,
        weight: float,
        confidence: Optional[float] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Aktualisiert Gewichtungsinformationen einer Relationship.

        Rückgabewert sollte die aktualisierten Properties enthalten. Default verweist auf
        NotImplemented, sodass spezialisierte Backends die Funktionalität explizit bereitstellen
        müssen.
        """

        raise NotImplementedError("update_relationship_weight ist für dieses Backend nicht implementiert")

    def soft_delete_relationship(
        self,
        relationship_id: RelationshipIdentifier,
        *,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Markiert eine Relationship als inaktiv (Soft Delete).

        Implementierungen sollten Lifecycle-Metadaten speichern und True/False zurückgeben.
        """

        raise NotImplementedError("soft_delete_relationship ist für dieses Backend nicht implementiert")

    def restore_relationship(
        self,
        relationship_id: RelationshipIdentifier,
        *,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Stellt eine zuvor soft-gelöschte Relationship wieder her."""

        raise NotImplementedError("restore_relationship ist für dieses Backend nicht implementiert")

class RelationalDatabaseBackend(DatabaseBackend):
    """Enhanced Abstract Base für relationale Datenbanken mit Adaptive Batch Processing"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
    
    def connect(self) -> bool:
        """Enhanced connect with adaptive batch initialization"""
        success = self._backend_connect() if hasattr(self, '_backend_connect') else self._connect_impl()
        if success:
            self._is_connected = True
            self._initialize_adaptive_batch_processing()
            # Initialize relational-specific processors
            self._initialize_relational_batch_processors()
        return success
    
    def _connect_impl(self) -> bool:
        """Default implementation - to be overridden"""  
        return True
    
    def _initialize_relational_batch_processors(self):
        """Initialize relational-specific adaptive batch processors"""
        try:
            # Relational-specific operations
            self._adaptive_processors['insert_records'] = AdaptiveBatchProcessor(
                self, "insert_records",
                base_batch_size=100,  # SQL INSERTs can handle large batches
                max_batch_size=1000,
                batch_executor=getattr(self, '_batch_insert_records_executor', None)
            )
            
            self._adaptive_processors['update_records'] = AdaptiveBatchProcessor(
                self, "update_records",
                base_batch_size=50,  # UPDATEs might be more complex
                max_batch_size=500,
                batch_executor=getattr(self, '_batch_update_records_executor', None)
            )
            
            self.logger.info("✅ Relational-specific adaptive batch processors initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize relational batch processors: {e}")
    
    def batch_insert_record(self, table_name: str, data: Dict) -> bool:
        """Queue record insertion for adaptive batch processing"""
        operation_data = {
            'type': 'insert_record',
            'table_name': table_name,
            'data': data
        }
        return self.queue_batch_operation('insert_records', operation_data)
    
    def batch_update_record(self, table_name: str, record_id: Any, data: Dict) -> bool:
        """Queue record update for adaptive batch processing"""
        operation_data = {
            'type': 'update_record',
            'table_name': table_name,
            'record_id': record_id,
            'data': data
        }
        return self.queue_batch_operation('update_records', operation_data)
    
    @abstractmethod
    def execute_query(self, query: str, params: Tuple = None) -> List[Dict]:
        """Führe SQL-Query aus"""
        pass
    
    @abstractmethod
    def create_table(self, table_name: str, schema: Dict) -> bool:
        """Erstelle Tabelle"""
        pass
    
    @abstractmethod
    def insert_record(self, table_name: str, data: Dict) -> Any:
        """Füge Datensatz ein"""
        pass
    
    @abstractmethod
    def update_record(self, table_name: str, record_id: Any, data: Dict) -> bool:
        """Update Datensatz"""
        pass

class FileDatabaseBackend(DatabaseBackend):
    """Enhanced Abstract Base für Dateibasierte Datenbanken mit Adaptive Batch Processing"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
    
    def connect(self) -> bool:
        """Enhanced connect with adaptive batch initialization"""
        success = self._backend_connect() if hasattr(self, '_backend_connect') else self._connect_impl()
        if success:
            self._is_connected = True
            self._initialize_adaptive_batch_processing()
            # Initialize file-specific processors
            self._initialize_file_batch_processors()
        return success
    
    def _connect_impl(self) -> bool:
        """Default implementation - to be overridden"""
        return True
    
    def _initialize_file_batch_processors(self):
        """Initialize file-specific adaptive batch processors"""
        try:
            # File-specific operations
            self._adaptive_processors['write_files'] = AdaptiveBatchProcessor(
                self, "write_files",
                base_batch_size=20,  # File writes can be batched moderately
                max_batch_size=100,
                batch_executor=getattr(self, '_batch_write_files_executor', None)
            )
            
            self.logger.info("✅ File-specific adaptive batch processors initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize file batch processors: {e}")
    
    def batch_write_file(self, file_path: str, content: bytes) -> bool:
        """Queue file write for adaptive batch processing"""
        operation_data = {
            'type': 'write_file',
            'file_path': file_path,
            'content': content
        }
        return self.queue_batch_operation('write_files', operation_data)
    
    @abstractmethod
    def read_file(self, file_path: str) -> Optional[bytes]:
        """Lese Datei-Inhalt"""
        pass
    
    @abstractmethod
    def write_file(self, file_path: str, content: bytes) -> bool:
        """Schreibe Datei-Inhalt"""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Lösche Datei"""
        pass
