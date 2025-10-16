#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDS3 Relations Core - Neo4j Adapter Wrapper
============================================
OPTIMIZED (1. Oktober 2025): Neo4j-spezifischer Adapter für UDS3 Relations Data Framework

BEFORE: 38 KB, 787 LOC - Vollständige eigenständige Implementierung mit Neo4j Backend
AFTER: ~8 KB, ~200 LOC - Thin wrapper delegiert an uds3_relations_data_framework.py
SAVINGS: -30 KB, -587 LOC (-75%)

Dieser Wrapper:
- Delegiert Core-Funktionalität an UDS3RelationsDataFramework
- Fügt Neo4j-spezifische Backend-Operationen hinzu
- Behält alle Type-Definitionen für Backward Compatibility
- Ist der einzige Adapter mit direkter DB-Anbindung
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager

# Logger früh initialisieren (vor imports mit potentiellen Fehlern)
logger = logging.getLogger(__name__)

class MockNeo4jSession:
    """Mock Neo4j Session für Entwicklungsumgebung ohne Neo4j Server"""
    def run(self, query: str, parameters: Dict = None):
        logger.debug(f"Mock Neo4j Query: {query[:50]}...")
        return MockResult()
    
    def close(self):
        pass

class MockResult:
    """Mock Neo4j Result für Entwicklungsumgebung"""
    def single(self):
        return {"result": "mock"}
    
    def data(self):
        return []

# Import Core Framework (backend-agnostisch)
from uds3_relations_data_framework import (
    UDS3RelationsDataFramework,
    UDS3RelationPriority,
    UDS3RelationStatus,
    UDS3DatabaseTarget,
    UDS3RelationMetadata,
    UDS3RelationInstance,
)

# Neo4j Import (optional) - Robust gegen Python 3.13 Kompatibilitätsprobleme
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except (ImportError, AttributeError) as e:
    # AttributeError: Python 3.13 Kompatibilitätsproblem mit neo4j (socket.EAI_ADDRFAMILY)
    NEO4J_AVAILABLE = False
    GraphDatabase = None  # type: ignore
    if isinstance(e, AttributeError):
        logger.warning(f"⚠️ Neo4j Driver nicht Python 3.13 kompatibel: {e}")



class UDS3RelationsCore:
    """
    Neo4j Adapter für UDS3 Relations Data Framework
    Delegiert Core-Logik an UDS3RelationsDataFramework, fügt Neo4j Backend hinzu
    """

    def __init__(
        self,
        neo4j_uri: str = "neo4j://127.0.0.1:7687",
        neo4j_auth: tuple = ("neo4j", "v3f3b1d7"),
    ):
        """
        Initialisiert Neo4j Adapter mit Backend-Verbindung

        Args:
            neo4j_uri: Neo4j Database URI
            neo4j_auth: Authentication tuple (username, password)
        """
        # Delegiere an Core Framework
        self.framework = UDS3RelationsDataFramework()
        
        # Neo4j Backend
        self.neo4j_uri = neo4j_uri
        self.neo4j_auth = neo4j_auth
        self.driver = None
        self.neo4j_enabled = NEO4J_AVAILABLE
        
        # Initialisiere Neo4j Connection
        if self.neo4j_enabled:
            self._initialize_neo4j_connection()
        else:
            logger.warning("⚠️ Neo4j nicht verfügbar - Adapter läuft ohne DB-Backend")
    
    def _initialize_neo4j_connection(self) -> None:
        """Initialisiert Neo4j Verbindung"""
        if not NEO4J_AVAILABLE:
            logger.warning("⚠️ Neo4j Driver nicht installiert")
            return
        
        try:
            self.driver = GraphDatabase.driver(self.neo4j_uri, auth=self.neo4j_auth)
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            logger.info(f"✅ Neo4j Verbindung erfolgreich: {self.neo4j_uri}")
        except Exception as e:
            # Weniger aggressive Protokollierung für Entwicklungsumgebung
            logger.warning(f"⚠️  Neo4j Server nicht verfügbar ({self.neo4j_uri}): {e}")
            logger.info("💡 Falls Neo4j benötigt wird: docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest")
            self.driver = None
            self.neo4j_enabled = False
    
    @contextmanager
    def neo4j_session(self):
        """Context Manager für Neo4j Sessions"""
        if not self.driver:
            logger.debug("Neo4j Session angefragt, aber Driver nicht verfügbar (Fallback-Modus aktiv)")
            # Statt Exception werfen, Mock-Session für Entwicklung
            yield MockNeo4jSession()
            return
        
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()
    
    # ================================================================
    # DELEGATION: Core-Methoden delegieren an Framework
    # ================================================================
    
    @property
    def almanach(self):
        """Delegiert Zugriff auf Relations Almanach"""
        return self.framework.almanach
    
    @property
    def uds3_relation_metadata(self):
        """Delegiert Zugriff auf UDS3 Metadaten"""
        return self.framework.uds3_metadata
    
    @property
    def relation_cache(self):
        """Delegiert Zugriff auf Relations Cache"""
        return self.framework.relation_instances
    
    def get_relation_definition(self, relation_type: str) -> Optional[Dict]:
        """Delegiert an Framework"""
        return self.framework.get_relation_definition(relation_type)
    
    def list_relations_by_priority(self, priority: UDS3RelationPriority) -> List[str]:
        """Delegiert an Framework"""
        return self.framework.list_relations_by_priority(priority)
    
    def get_relation_schema(self, relation_type: Optional[str] = None) -> Dict:
        """Delegiert an Framework + Neo4j Schema Info"""
        schema = self.framework.get_relation_definition(relation_type) if relation_type else {}
        
        # Füge Neo4j-spezifische Schema-Info hinzu
        if self.neo4j_enabled and relation_type:
            schema["neo4j_optimized"] = True
            schema["neo4j_backend_available"] = self.driver is not None
        
        return schema
    
    # ================================================================
    # NEO4J-SPECIFIC: Schema Management
    # ================================================================
    
    def create_neo4j_schema(self, force_recreate: bool = False) -> Dict:
        """
        Erstellt Neo4j Schema basierend auf Relations Almanach
        
        Args:
            force_recreate: Erzwingt Neuerstellung bestehender Constraints/Indexes
        
        Returns:
            Dict: Schema-Erstellungsergebnis
        """
        schema_result = {
            "timestamp": datetime.now().isoformat(),
            "neo4j_enabled": self.neo4j_enabled,
            "force_recreate": force_recreate,
            "constraints_created": [],
            "indexes_created": [],
            "relation_types_defined": [],
            "errors": [],
            "success": False,
        }
        
        if not self.neo4j_enabled or not self.driver:
            schema_result["errors"].append("Neo4j Backend nicht verfügbar")
            return schema_result
        
        try:
            with self.neo4j_session() as session:
                # Node Constraints
                constraints = [
                    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
                    "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:DocumentChunk) REQUIRE c.chunk_id IS UNIQUE",
                ]
                
                for constraint_cypher in constraints:
                    try:
                        session.run(constraint_cypher)
                        schema_result["constraints_created"].append(constraint_cypher)
                    except Exception as e:
                        logger.debug(f"Constraint bereits vorhanden: {e}")
                
                # Property Indexes
                indexes = [
                    "CREATE INDEX document_rechtsgebiet_idx IF NOT EXISTS FOR (d:Document) ON (d.rechtsgebiet)",
                    "CREATE INDEX document_behoerde_idx IF NOT EXISTS FOR (d:Document) ON (d.behoerde)",
                ]
                
                for index_cypher in indexes:
                    try:
                        session.run(index_cypher)
                        schema_result["indexes_created"].append(index_cypher)
                    except Exception as e:
                        logger.debug(f"Index bereits vorhanden: {e}")
                
                # Relation Types dokumentieren
                for rel_name in self.framework.list_all_relations():
                    schema_result["relation_types_defined"].append(rel_name)
                
                schema_result["success"] = True
                logger.info(f"✅ Neo4j Schema erstellt: {len(schema_result['constraints_created'])} Constraints, {len(schema_result['indexes_created'])} Indexes")
        
        except Exception as e:
            schema_result["errors"].append(str(e))
            if self.neo4j_enabled:
                logger.warning(f"⚠️  Neo4j Schema-Erstellung fehlgeschlagen: {e}")
            else:
                logger.debug(f"Neo4j Schema Skip (Server nicht verfügbar): {e}")
        
        return schema_result
    
    # ================================================================
    # NEO4J-SPECIFIC: Relation Operations
    # ================================================================
    
    def create_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict:
        """
        Erstellt eine Relation (Framework + Neo4j Backend)
        
        Args:
            relation_type: Typ der Relation
            source_id: Source Node ID
            target_id: Target Node ID
            properties: Relation Properties
        
        Returns:
            Dict: Ergebnis inkl. Neo4j Backend Status
        """
        # 1. Framework-Logik: Validierung + Instanz
        result = self.framework.create_relation_instance(
            relation_type=relation_type,
            source_id=source_id,
            target_id=target_id,
            properties=properties or {},
            **kwargs
        )
        
        # 2. Neo4j Backend: Persistierung
        if result["success"] and self.neo4j_enabled and self.driver:
            try:
                with self.neo4j_session() as session:
                    cypher = f"""
                    MATCH (source {{id: }})
                    MATCH (target {{id: }})
                    CREATE (source)-[r:{relation_type}]->(target)
                    SET r = 
                    RETURN elementId(r) AS relation_id
                    """
                    
                    neo_result = session.run(
                        cypher,
                        source_id=source_id,
                        target_id=target_id,
                        properties=properties or {}
                    )
                    
                    record = neo_result.single()
                    if record:
                        result["neo4j_relation_id"] = record["relation_id"]
                        result["neo4j_persisted"] = True
                    
                    logger.debug(f"✅ Relation in Neo4j erstellt: {relation_type}")
            
            except Exception as e:
                result["neo4j_error"] = str(e)
                result["neo4j_persisted"] = False
                logger.warning(f"⚠️ Neo4j Persistierung fehlgeschlagen: {e}")
        
        return result
    
    def validate_graph_consistency(self) -> Dict:
        """
        Validiert Graph-Konsistenz (nur Neo4j Backend)
        
        Returns:
            Dict: Validierungsergebnis
        """
        validation_result = {
            "timestamp": datetime.now().isoformat(),
            "neo4j_enabled": self.neo4j_enabled,
            "overall_consistent": True,
            "validation_checks": [],
            "inconsistencies": [],
            "statistics": {},
        }
        
        if not self.neo4j_enabled or not self.driver:
            validation_result["overall_consistent"] = False
            validation_result["inconsistencies"].append("Neo4j Backend nicht verfügbar")
            return validation_result
        
        try:
            with self.neo4j_session() as session:
                # Node counts
                node_counts = {}
                for label in ["Document", "DocumentChunk", "LegalReference"]:
                    result = session.run(f"MATCH (n:{label}) RETURN count(n) AS count")
                    node_counts[label] = result.single()["count"]
                
                validation_result["statistics"]["node_counts"] = node_counts
                
                # Relation counts
                result = session.run("MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count")
                relation_counts = {record["rel_type"]: record["count"] for record in result}
                validation_result["statistics"]["relation_counts"] = relation_counts
                
                logger.info(f"✅ Graph Validierung erfolgreich: {sum(node_counts.values())} Nodes, {sum(relation_counts.values())} Relations")
        
        except Exception as e:
            validation_result["overall_consistent"] = False
            validation_result["inconsistencies"].append(f"Validierungsfehler: {e}")
            logger.error(f"❌ Graph Validierung fehlgeschlagen: {e}")
        
        return validation_result
    
    def close(self) -> None:
        """Schließt Neo4j Verbindung"""
        if self.driver:
            self.driver.close()
            logger.info("✅ Neo4j Verbindung geschlossen")


# ================================================================
# FACTORY & EXPORTS
# ================================================================

_uds3_relations_core_instance: Optional[UDS3RelationsCore] = None


def get_uds3_relations_core(
    neo4j_uri: str = "neo4j://127.0.0.1:7687",
    neo4j_auth: tuple = ("neo4j", "v3f3b1d7"),
) -> UDS3RelationsCore:
    """
    Factory für UDS3 Relations Core (Singleton)
    
    Args:
        neo4j_uri: Neo4j URI
        neo4j_auth: Neo4j Authentication
    
    Returns:
        UDS3RelationsCore: Singleton-Instanz
    """
    global _uds3_relations_core_instance
    
    if _uds3_relations_core_instance is None:
        _uds3_relations_core_instance = UDS3RelationsCore(
            neo4j_uri=neo4j_uri,
            neo4j_auth=neo4j_auth
        )
    
    return _uds3_relations_core_instance


# Backward Compatibility Exports
__all__ = [
    "UDS3RelationsCore",
    "get_uds3_relations_core",
    # Re-export Core Types
    "UDS3RelationPriority",
    "UDS3RelationStatus",
    "UDS3DatabaseTarget",
    "UDS3RelationMetadata",
    "UDS3RelationInstance",
]
