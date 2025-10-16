#!/usr/bin/env python3
"""
UDS3 Relations Framework - Programmatische Vereinheitlichung
===========================================================
Datentechnische Vereinheitlichung der Relations ohne direkte DB-Anbindung
Integriert in UDS3 Core für konsistente Relations-Verwaltung
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import logging


# Fallback-Stubs für das Veritas Relations Almanach (lokales Paket / optional)
VERITASRelationAlmanach: Any = None  # type: ignore
RelationType: Any = None  # type: ignore
GraphLevel: Any = None  # type: ignore
RelationDefinition: Any = None  # type: ignore

logger = logging.getLogger(__name__)


class UDS3RelationPriority(Enum):
    """UDS3-spezifische Relation-Prioritäten"""

    CRITICAL = "critical"  # Systemkritische Relations (PART_OF, CONTAINS_CHUNK)
    LEGAL = "legal"  # Rechtliche Relations (UDS3_LEGAL_REFERENCE)
    SEMANTIC = "semantic"  # Semantische Relations (UDS3_SEMANTIC_REFERENCE)
    STRUCTURAL = "structural"  # Strukturelle Relations (NEXT_CHUNK, etc.)
    QUALITY = "quality"  # Qualitäts-Relations
    SYSTEM = "system"  # System-Relations


class UDS3RelationStatus(Enum):
    """Status einer Relation im UDS3-System"""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"
    PLANNED = "planned"


class UDS3DatabaseTarget(Enum):
    """UDS3 Database-Ziele für Relations"""

    GRAPH = "graph"  # Graph DB (Neo4j, ArangoDB)
    VECTOR = "vector"  # Vector DB (ChromaDB, Pinecone)
    RELATIONAL = "relational"  # Relational DB (SQLite, PostgreSQL)
    ALL = "all"  # Alle Datenbanken
    NONE = "none"  # Nur konzeptuell


@dataclass
class UDS3RelationMetadata:
    """UDS3-spezifische Metadaten für Relations"""

    relation_name: str
    uds3_priority: UDS3RelationPriority
    status: UDS3RelationStatus
    database_targets: List[UDS3DatabaseTarget]
    performance_weight: float = 1.0
    legal_compliance: bool = True
    indexing_required: bool = True
    constraint_required: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: str = "3.0"


@dataclass
class UDS3RelationInstance:
    """Instanz einer UDS3 Relation"""

    relation_type: str
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    uds3_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    instance_id: Optional[str] = None

    def __post_init__(self):
        if self.instance_id is None:
            self.instance_id = self._generate_instance_id()

    def _generate_instance_id(self) -> str:
        """Generiert eindeutige Instance-ID"""
        content = f"{self.relation_type}:{self.source_id}:{self.target_id}:{self.created_at.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class UDS3RelationsDataFramework:
    """
    UDS3 Relations Data Framework - Programmatische Vereinheitlichung
    Verwaltet Relations-Definitionen und -Instanzen ohne direkte DB-Anbindung
    """

    def __init__(self):
        """Initialisiert UDS3 Relations Data Framework"""
        # Relations Almanach laden (Fallback wenn nicht verfügbar)
        if VERITASRelationAlmanach is not None:
            self.almanach = VERITASRelationAlmanach()
        else:
            self.almanach = None

        # UDS3-spezifische Metadaten
        self.uds3_metadata = self._initialize_uds3_metadata()

        # Relations-Instanzen Cache
        self.relation_instances: Dict[str, UDS3RelationInstance] = {}

        # Relations-Validierung
        self.validation_rules = self._create_validation_rules()

        # Performance-Tracking
        self.performance_stats = {
            "relations_created": 0,
            "relations_validated": 0,
            "validation_errors": 0,
            "total_operations": 0,
        }

        logger.info("UDS3 Relations Data Framework initialisiert")

    def _get_almanach_relations(self) -> Dict[str, Any]:
        """Sicherer Zugriff auf Almanach Relations mit Fallback"""
        if self.almanach is None or not hasattr(self.almanach, 'relations'):
            return {}
        return getattr(self.almanach, 'relations', {})

    def _initialize_uds3_metadata(self) -> Dict[str, UDS3RelationMetadata]:
        """Initialisiert UDS3-spezifische Metadaten für alle Relations"""
        metadata: dict[Any, Any] = {}

        # Sichere Relations laden
        relations = self._get_almanach_relations()
        if not relations:
            logger.warning("⚠️ VERITAS Relations Almanach nicht verfügbar - verwende leere Metadaten")
            return metadata

        for relation_name, relation_def in relations.items():
            # Bestimme UDS3 Priorität
            priority = self._determine_uds3_priority(relation_name, relation_def)

            # Bestimme Status
            status = self._determine_relation_status(relation_name, relation_def)

            # Bestimme Database-Ziele
            db_targets = self._determine_database_targets(relation_name, relation_def)

            # Performance Weight
            performance_weight = self._calculate_performance_weight(relation_def)

            # Erstelle Metadaten
            metadata[relation_name] = UDS3RelationMetadata(
                relation_name=relation_name,
                uds3_priority=priority,
                status=status,
                database_targets=db_targets,
                performance_weight=performance_weight,
                legal_compliance=relation_def.uds3_compliance,
                indexing_required=relation_def.kge_importance in ["critical", "high"],
                constraint_required=relation_name in ["PART_OF", "CONTAINS_CHUNK"],
            )

        return metadata

    def _determine_uds3_priority(
        self, relation_name: str, relation_def: Any
    ) -> UDS3RelationPriority:
        """Bestimmt UDS3-Priorität für eine Relation"""
        if relation_name.startswith("UDS3_"):
            return (
                UDS3RelationPriority.LEGAL
                if "LEGAL" in relation_name
                else UDS3RelationPriority.SEMANTIC
            )
        elif relation_name in [
            "PART_OF",
            "CONTAINS_CHUNK",
            "NEXT_CHUNK",
            "PREVIOUS_CHUNK",
        ]:
            return UDS3RelationPriority.CRITICAL
        elif relation_def.type == RelationType.LEGAL:
            return UDS3RelationPriority.LEGAL
        elif relation_def.type == RelationType.SEMANTIC:
            return UDS3RelationPriority.SEMANTIC
        elif relation_def.type == RelationType.STRUCTURAL:
            return UDS3RelationPriority.STRUCTURAL
        elif relation_def.type == RelationType.QUALITY:
            return UDS3RelationPriority.QUALITY
        else:
            return UDS3RelationPriority.SYSTEM

    def _determine_relation_status(
        self, relation_name: str, relation_def: Any
    ) -> UDS3RelationStatus:
        """Bestimmt Status einer Relation"""
        if relation_name.startswith("UDS3_"):
            return UDS3RelationStatus.ACTIVE
        elif relation_def.kge_importance == "critical":
            return UDS3RelationStatus.ACTIVE
        else:
            return UDS3RelationStatus.ACTIVE

    def _determine_database_targets(
        self, relation_name: str, relation_def: Any
    ) -> List[UDS3DatabaseTarget]:
        """Bestimmt Database-Ziele für eine Relation"""
        targets: list[Any] = []

        # Strukturelle Relations → Graph DB
        if relation_def.type in [
            RelationType.STRUCTURAL,
            RelationType.LEGAL,
            RelationType.SEMANTIC,
        ]:
            targets.append(UDS3DatabaseTarget.GRAPH)

        # Semantische Relations → Vector DB (für Embedding-basierte Suche)
        if relation_def.type == RelationType.SEMANTIC:
            targets.append(UDS3DatabaseTarget.VECTOR)

        # Metadaten-Relations → Relational DB
        if relation_def.type in [
            RelationType.ADMINISTRATIVE,
            RelationType.TECHNICAL,
            RelationType.QUALITY,
        ]:
            targets.append(UDS3DatabaseTarget.RELATIONAL)

        # UDS3-spezifische Relations → Graph DB
        if relation_name.startswith("UDS3_"):
            if UDS3DatabaseTarget.GRAPH not in targets:
                targets.append(UDS3DatabaseTarget.GRAPH)

        return targets if targets else [UDS3DatabaseTarget.ALL]

    def _calculate_performance_weight(self, relation_def: Any) -> float:
        """Berechnet Performance-Gewichtung"""
        weight = 1.0

        # KGE Wichtigkeit
        kge_weights = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5}
        weight *= kge_weights.get(relation_def.kge_importance, 1.0)

        # Transitivität
        if relation_def.transitivity:
            weight *= 1.3

        # UDS3-spezifische Relations
        if relation_def.name.startswith("UDS3_"):
            weight *= 1.8

        return round(weight, 2)

    def _create_validation_rules(self) -> Dict[str, Dict]:
        """Erstellt Validierungsregeln für Relations"""
        return {
            "required_properties": {
                "UDS3_LEGAL_REFERENCE": ["reference_type", "confidence"],
                "UDS3_SEMANTIC_REFERENCE": ["similarity_score"],
                "PART_OF": ["chunk_index"],
                "CONTAINS_CHUNK": ["total_chunks"],
            },
            "property_types": {
                "confidence": float,
                "similarity_score": float,
                "chunk_index": int,
                "total_chunks": int,
                "frequency": int,
            },
            "property_ranges": {
                "confidence": (0.0, 1.0),
                "similarity_score": (0.0, 1.0),
                "chunk_index": (0, None),
                "total_chunks": (1, None),
            },
        }

    # ================================================================
    # RELATION DEFINITION OPERATIONS
    # ================================================================

    def get_relation_definition(self, relation_type: str) -> Optional[Dict]:
        """
        Holt Relation-Definition aus dem Almanach

        Args:
            relation_type: Name des Relation-Typs

        Returns:
            Dict: Vollständige Relation-Definition oder None
        """
        relations = self._get_almanach_relations()
        if relation_type not in relations:
            return None

        relation_def = relations[relation_type]
        uds3_meta = self.uds3_metadata[relation_type]

        return {
            "relation_type": relation_type,
            "almanach_definition": {
                "type": relation_def.type.value,
                "level": relation_def.level.value,
                "description": relation_def.description,
                "source_node_types": relation_def.source_node_types,
                "target_node_types": relation_def.target_node_types,
                "properties": relation_def.properties,
                "inverse_relation": relation_def.inverse_relation,
                "transitivity": relation_def.transitivity,
                "symmetry": relation_def.symmetry,
                "reflexivity": relation_def.reflexivity,
                "weight_range": relation_def.weight_range,
                "uds3_compliance": relation_def.uds3_compliance,
                "kge_importance": relation_def.kge_importance,
            },
            "uds3_metadata": {
                "priority": uds3_meta.uds3_priority.value,
                "status": uds3_meta.status.value,
                "database_targets": [
                    target.value for target in uds3_meta.database_targets
                ],
                "performance_weight": uds3_meta.performance_weight,
                "legal_compliance": uds3_meta.legal_compliance,
                "indexing_required": uds3_meta.indexing_required,
                "constraint_required": uds3_meta.constraint_required,
                "version": uds3_meta.version,
            },
        }

    def list_relations_by_priority(self, priority: UDS3RelationPriority) -> List[str]:
        """Listet Relations nach UDS3-Priorität"""
        return [
            name
            for name, meta in self.uds3_metadata.items()
            if meta.uds3_priority == priority
        ]

    def list_relations_by_database_target(
        self, target: UDS3DatabaseTarget
    ) -> List[str]:
        """Listet Relations nach Database-Ziel"""
        return [
            name
            for name, meta in self.uds3_metadata.items()
            if target in meta.database_targets
            or UDS3DatabaseTarget.ALL in meta.database_targets
        ]

    def get_relation_schema_for_database(self, database_type: str) -> Dict:
        """
        Erstellt Relations-Schema für spezifische Datenbank

        Args:
            database_type: "graph", "vector", "relational"

        Returns:
            Dict: Database-spezifisches Relations-Schema
        """
        db_target = UDS3DatabaseTarget(database_type)
        relevant_relations = self.list_relations_by_database_target(db_target)

        schema = {
            "database_type": database_type,
            "total_relations": len(relevant_relations),
            "relations": {},
            "constraints": [],
            "indexes": [],
            "optimizations": [],
        }

        for relation_name in relevant_relations:
            relation_def = self.get_relation_definition(relation_name)
            schema["relations"][relation_name] = relation_def

            # Database-spezifische Optimierungen
            if relation_def["uds3_metadata"]["constraint_required"]:
                schema["constraints"].append(f"{relation_name}_constraint")

            if relation_def["uds3_metadata"]["indexing_required"]:
                schema["indexes"].append(f"{relation_name}_index")

        return schema

    # ================================================================
    # RELATION INSTANCE OPERATIONS
    # ================================================================

    def create_relation_instance(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Dict[str, Any] = None,
    ) -> Dict:
        """
        Erstellt eine Relations-Instanz (datentechnisch)

        Args:
            relation_type: Typ der Relation
            source_id: ID des Quell-Nodes
            target_id: ID des Ziel-Nodes
            properties: Relation-Properties

        Returns:
            Dict: Ergebnis der Instanz-Erstellung
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "operation": "CREATE_RELATION_INSTANCE",
            "relation_type": relation_type,
            "source_id": source_id,
            "target_id": target_id,
            "success": False,
            "instance_id": None,
            "validation_errors": [],
            "database_operations": {},
        }

        try:
            # 1. Validiere Relation-Typ
            if relation_type not in self._get_almanach_relations():
                result["validation_errors"].append(
                    f"Unbekannter Relation-Typ: {relation_type}"
                )
                return result

            # 2. Validiere Properties
            validation_errors = self._validate_relation_properties(
                relation_type, properties or {}
            )
            if validation_errors:
                result["validation_errors"].extend(validation_errors)
                return result

            # 3. Erweitere Properties mit UDS3-Metadaten
            enhanced_properties = self._enhance_properties_with_uds3(
                relation_type, properties or {}
            )

            # 4. Erstelle Relations-Instanz
            relation_instance = UDS3RelationInstance(
                relation_type=relation_type,
                source_id=source_id,
                target_id=target_id,
                properties=enhanced_properties,
                uds3_metadata=self._create_instance_metadata(relation_type),
            )

            # 5. Speichere Instanz
            self.relation_instances[relation_instance.instance_id] = relation_instance

            # 6. Erstelle Database-Operations
            result["database_operations"] = self._create_database_operations(
                relation_instance
            )

            result["success"] = True
            result["instance_id"] = relation_instance.instance_id

            # Statistics
            self.performance_stats["relations_created"] += 1
            self.performance_stats["total_operations"] += 1

            logger.debug(
                f"✅ UDS3 Relation-Instanz erstellt: {relation_type} ({source_id} -> {target_id})"
            )

        except Exception as e:
            result["validation_errors"].append(f"Unerwarteter Fehler: {str(e)}")
            logger.error(f"❌ UDS3 Relation-Instanz-Erstellung fehlgeschlagen: {e}")

        return result

    def _validate_relation_properties(
        self, relation_type: str, properties: Dict[str, Any]
    ) -> List[str]:
        """Validiert Relation-Properties"""
        errors: list[Any] = []

        # Required Properties Check
        if relation_type in self.validation_rules["required_properties"]:
            required = self.validation_rules["required_properties"][relation_type]
            for prop in required:
                if prop not in properties:
                    errors.append(
                        f"Required property '{prop}' missing for {relation_type}"
                    )

        # Property Types Check
        for prop_name, prop_value in properties.items():
            if prop_name in self.validation_rules["property_types"]:
                expected_type = self.validation_rules["property_types"][prop_name]
                if not isinstance(prop_value, expected_type):
                    errors.append(
                        f"Property '{prop_name}' should be {expected_type.__name__}, got {type(prop_value).__name__}"
                    )

        # Property Ranges Check
        for prop_name, prop_value in properties.items():
            if prop_name in self.validation_rules["property_ranges"]:
                min_val, max_val = self.validation_rules["property_ranges"][prop_name]
                if isinstance(prop_value, (int, float)):
                    if min_val is not None and prop_value < min_val:
                        errors.append(
                            f"Property '{prop_name}' value {prop_value} below minimum {min_val}"
                        )
                    if max_val is not None and prop_value > max_val:
                        errors.append(
                            f"Property '{prop_name}' value {prop_value} above maximum {max_val}"
                        )

        self.performance_stats["relations_validated"] += 1
        if errors:
            self.performance_stats["validation_errors"] += len(errors)

        return errors

    def _enhance_properties_with_uds3(
        self, relation_type: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Erweitert Properties mit UDS3-Standards"""
        enhanced = properties.copy()

        # UDS3-Standard Properties
        enhanced.update(
            {
                "uds3_created_at": datetime.now().isoformat(),
                "uds3_version": "3.0",
                "uds3_priority": self.uds3_metadata[relation_type].uds3_priority.value,
                "uds3_performance_weight": self.uds3_metadata[
                    relation_type
                ].performance_weight,
            }
        )

        # Relation-spezifische Defaults
        relation_def = self._get_almanach_relations()[relation_type]
        for prop_name, prop_type in relation_def.properties.items():
            if prop_name not in enhanced:
                # Standard-Werte
                defaults = {
                    "float": 1.0,
                    "int": 0,
                    "bool": True,
                    "str": "auto_generated",
                    "list": [],
                    "dict": {},
                }
                enhanced[prop_name] = defaults.get(prop_type, None)

        return enhanced

    def _create_instance_metadata(self, relation_type: str) -> Dict[str, Any]:
        """Erstellt Instanz-spezifische Metadaten"""
        uds3_meta = self.uds3_metadata[relation_type]

        return {
            "uds3_priority": uds3_meta.uds3_priority.value,
            "database_targets": [target.value for target in uds3_meta.database_targets],
            "performance_weight": uds3_meta.performance_weight,
            "legal_compliance": uds3_meta.legal_compliance,
            "created_by_framework": "UDS3_Relations_Data_Framework",
            "framework_version": "3.0",
        }

    def _create_database_operations(
        self, relation_instance: UDS3RelationInstance
    ) -> Dict[str, Any]:
        """Erstellt Database-Operations für Relations-Instanz"""
        operations: dict[Any, Any] = {}

        uds3_meta = self.uds3_metadata[relation_instance.relation_type]

        for db_target in uds3_meta.database_targets:
            if db_target == UDS3DatabaseTarget.GRAPH:
                operations["graph"] = {
                    "operation": "CREATE_RELATIONSHIP",
                    "cypher_template": f"CREATE (source)-[r:{relation_instance.relation_type}]->(target) SET r += $properties",
                    "parameters": {
                        "source_id": relation_instance.source_id,
                        "target_id": relation_instance.target_id,
                        "properties": relation_instance.properties,
                    },
                }

            elif db_target == UDS3DatabaseTarget.VECTOR:
                operations["vector"] = {
                    "operation": "UPDATE_EMBEDDING_METADATA",
                    "collection": "relation_metadata",
                    "metadata": {
                        "relation_id": relation_instance.instance_id,
                        "relation_type": relation_instance.relation_type,
                        "source_id": relation_instance.source_id,
                        "target_id": relation_instance.target_id,
                    },
                }

            elif db_target == UDS3DatabaseTarget.RELATIONAL:
                operations["relational"] = {
                    "operation": "INSERT_RELATION_METADATA",
                    "table": "uds3_relations",
                    "data": {
                        "instance_id": relation_instance.instance_id,
                        "relation_type": relation_instance.relation_type,
                        "source_id": relation_instance.source_id,
                        "target_id": relation_instance.target_id,
                        "properties_json": json.dumps(relation_instance.properties),
                        "created_at": relation_instance.created_at.isoformat(),
                    },
                }

        return operations

    # ================================================================
    # UTILITY METHODS
    # ================================================================

    def get_performance_stats(self) -> Dict[str, Any]:
        """Holt Performance-Statistiken"""
        return {
            "performance_stats": self.performance_stats,
            "total_relation_definitions": len(self._get_almanach_relations()),
            "active_relation_instances": len(self.relation_instances),
            "uds3_priorities_distribution": {
                priority.value: len(self.list_relations_by_priority(priority))
                for priority in UDS3RelationPriority
            },
            "database_targets_distribution": {
                target.value: len(self.list_relations_by_database_target(target))
                for target in UDS3DatabaseTarget
                if target != UDS3DatabaseTarget.ALL
            },
        }

    def export_uds3_schema(self, target_format: str = "json") -> str:
        """Exportiert UDS3 Relations-Schema"""
        schema_data = {
            "uds3_version": "3.0",
            "export_timestamp": datetime.now().isoformat(),
            "total_relations": len(self._get_almanach_relations()),
            "relations_metadata": {},
        }

        for relation_name in self._get_almanach_relations().keys():
            schema_data["relations_metadata"][relation_name] = (
                self.get_relation_definition(relation_name)
            )

        if target_format == "json":
            return json.dumps(schema_data, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {target_format}")

    def clear_relation_instances(self):
        """Löscht alle Relations-Instanzen (für Tests)"""
        self.relation_instances.clear()
        self.performance_stats = {
            "relations_created": 0,
            "relations_validated": 0,
            "validation_errors": 0,
            "total_operations": 0,
        }


# Singleton Pattern
_uds3_relations_framework: Any = None


def get_uds3_relations_framework() -> UDS3RelationsDataFramework:
    """Singleton-Zugriff auf UDS3 Relations Data Framework"""
    global _uds3_relations_framework
    if _uds3_relations_framework is None:
        _uds3_relations_framework = UDS3RelationsDataFramework()
    return _uds3_relations_framework


if __name__ == "__main__":
    print("🔗 UDS3 RELATIONS DATA FRAMEWORK - TEST")
    print("=" * 50)

    # Framework initialisieren
    framework = get_uds3_relations_framework()

    # 1. Relations-Definitionen testen
    print("\n📊 RELATIONS-DEFINITIONEN:")

    test_relations = [
        "UDS3_LEGAL_REFERENCE",
        "UDS3_SEMANTIC_REFERENCE",
        "PART_OF",
        "CONTAINS_CHUNK",
    ]
    for relation_type in test_relations:
        definition = framework.get_relation_definition(relation_type)
        if definition:
            print(f"\n🔍 {relation_type}:")
            print(f"  UDS3 Priority: {definition['uds3_metadata']['priority']}")
            print(
                f"  Database Targets: {definition['uds3_metadata']['database_targets']}"
            )
            print(
                f"  Performance Weight: {definition['uds3_metadata']['performance_weight']}"
            )
            print(
                f"  KGE Importance: {definition['almanach_definition']['kge_importance']}"
            )

    # 2. Relations nach Priorität
    print("\n📋 RELATIONS NACH PRIORITÄT:")
    for priority in UDS3RelationPriority:
        relations = framework.list_relations_by_priority(priority)
        print(f"  {priority.value}: {len(relations)} Relations")

    # 3. Database-spezifische Schemas
    print("\n🎯 DATABASE-SPEZIFISCHE SCHEMAS:")
    for db_type in ["graph", "vector", "relational"]:
        schema = framework.get_relation_schema_for_database(db_type)
        print(f"  {db_type}: {schema['total_relations']} Relations")

    # 4. Relations-Instanzen erstellen (Test)
    print("\n🔗 RELATIONS-INSTANZEN ERSTELLEN:")

    test_instances = [
        {
            "relation_type": "UDS3_LEGAL_REFERENCE",
            "source_id": "doc_001",
            "target_id": "legal_ref_bgb_123",
            "properties": {
                "reference_type": "paragraph",
                "confidence": 0.95,
                "context": "Rechtliche Grundlage",
            },
        },
        {
            "relation_type": "CONTAINS_CHUNK",
            "source_id": "doc_001",
            "target_id": "chunk_001",
            "properties": {
                "chunk_index": 0,
                "total_chunks": 5,
                "chunk_order": [0, 1, 2, 3, 4],
            },
        },
    ]

    for instance_data in test_instances:
        result = framework.create_relation_instance(**instance_data)

        if result["success"]:
            print(f"  ✅ {instance_data['relation_type']}: {result['instance_id']}")
            print(
                f"    Database Operations: {list(result['database_operations'].keys())}"
            )
        else:
            print(
                f"  ❌ {instance_data['relation_type']}: {result['validation_errors']}"
            )

    # 5. Performance Stats
    print("\n📊 PERFORMANCE STATISTIKEN:")
    stats = framework.get_performance_stats()

    print(f"  Relations erstellt: {stats['performance_stats']['relations_created']}")
    print(f"  Relations validiert: {stats['performance_stats']['relations_validated']}")
    print(f"  Validierungsfehler: {stats['performance_stats']['validation_errors']}")
    print(f"  Aktive Instanzen: {stats['active_relation_instances']}")

    print("\n🎉 UDS3 Relations Data Framework Test erfolgreich!")
