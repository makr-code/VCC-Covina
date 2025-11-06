"""
Process Graph Writer - UDS3 SAGA Integration (v2.0)

COMPLETE MIGRATION from low-level Neo4j to UDS3 SAGA Pattern.

ALL 23 methods now use:
- UDS3 SAGA Pattern (auto-rollback on errors)
- Polyglot Persistence (4 databases: Vector, Graph, Relational, File)
- Governance & Audit Trail
- Identity Binding

Migration Date: 31. Oktober 2025
Author: Martin Krüger
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional, Dict
import logging

from processes.domain.models import (
    Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject
)

# UDS3 Extension Import
try:
    from uds3.extensions import UDS3ProcessExtension
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProcessGraphWriter:
    """
    UDS3-Compliant Process Writer with SAGA Pattern (v2.0).
    
    NEW Architecture:
    - Uses UDS3ProcessExtension for all operations
    - Full polyglot persistence (Neo4j + PostgreSQL + ChromaDB + CouchDB)
    - SAGA pattern (auto-rollback on errors)
    - Governance & audit trail
    - Temporal Canon integration
    
    OLD Architecture (v1.0 - deprecated):
    - Direct execute_query() calls
    - Neo4j only
    - No rollback, no audit
    
    Migration Status:
    ✅ 23/23 methods migrated to UDS3 SAGA
    ✅ Polyglot persistence activated
    ✅ Legacy mode preserved for backward compatibility
    
    Usage (UDS3 Mode - RECOMMENDED):
        ```python
        from uds3.core.database import UnifiedDatabaseStrategy
        
        uds3 = UnifiedDatabaseStrategy(config)
        writer = ProcessGraphWriter(uds3_strategy=uds3)
        
        # Create process in all 4 databases with SAGA
        result = writer.write_process(process)
        if result["success"]:
            print(f"✅ Process in {len(result['database_operations'])} databases")
            # Neo4j: result["database_operations"]["graph"]
            # PostgreSQL: result["database_operations"]["relational"]
            # ChromaDB: result["database_operations"]["vector"]
            # CouchDB: result["database_operations"]["file_storage"]
        else:
            print(f"❌ SAGA Rollback: {result['error']}")
        ```
    
    Usage (Legacy Mode - DEPRECATED):
        ```python
        from uds3.database.database_api_neo4j import Neo4jGraphBackend
        
        graph = Neo4jGraphBackend(uri, user, password)
        writer = ProcessGraphWriter(graph_adapter=graph)
        
        # Neo4j only, no SAGA, no rollback
        process_id = writer.write_process(process)
        ```
    """
    
    def __init__(self, graph_adapter=None, uds3_strategy=None):
        """
        Initialize writer with UDS3 strategy (RECOMMENDED) or legacy graph adapter.
        
        Args:
            graph_adapter: (DEPRECATED) UDS3 graph adapter for legacy mode
            uds3_strategy: (RECOMMENDED) UnifiedDatabaseStrategy instance
            
        Raises:
            ValueError: If both or neither provided
            ValueError: If UDS3 not available but uds3_strategy provided
        """
        if uds3_strategy and graph_adapter:
            raise ValueError("Provide either uds3_strategy OR graph_adapter, not both")
        
        if not uds3_strategy and not graph_adapter:
            raise ValueError("Either uds3_strategy or graph_adapter required")
        
        if uds3_strategy:
            if not UDS3_AVAILABLE:
                raise ValueError("UDS3 not available - install uds3 package or set sys.path")
            
            logger.info("✅ ProcessGraphWriter initialized in UDS3 SAGA mode (v2.0)")
            logger.info("   Polyglot: Neo4j + PostgreSQL + ChromaDB + CouchDB")
            logger.info("   SAGA: Automatic rollback on errors")
            self.mode = "uds3"
            self.uds3_ext = UDS3ProcessExtension(uds3_strategy)
            self.graph = None
            self.temporal_canon = self.uds3_ext.temporal_canon
        
        else:
            logger.warning("⚠️ ProcessGraphWriter in LEGACY mode (v1.0)")
            logger.warning("   Neo4j only | No SAGA | No polyglot | No rollback")
            logger.warning("   Upgrade to UDS3 mode for production use!")
            self.mode = "legacy"
            self.graph = graph_adapter
            from processes.graph.temporal_canon import TemporalCanon
            self.temporal_canon = TemporalCanon(graph_adapter)
            self.uds3_ext = None
    
    # ========================================================================
    # PROCESS
    # ========================================================================
    def write_process(self, process: Process) -> Any:
        """
        Write Process to all 4 databases (UDS3) or Neo4j only (legacy).
        
        UDS3 Mode (v2.0):
        - Creates in: ChromaDB (embeddings), Neo4j (graph), PostgreSQL (metadata), CouchDB (JSON)
        - SAGA: Auto-rollback if any database fails
        - Audit: Compliance trail logged
        - Identity: Cross-database UUID
        
        Legacy Mode (v1.0 - deprecated):
        - Creates in Neo4j only
        - No rollback, no audit, no polyglot
        
        Args:
            process: Process domain model
            
        Returns:
            UDS3: Dict with success, database_operations, error
            Legacy: str (process ID)
        """
        if self.mode == "uds3":
            return self.uds3_ext.create_process(process)
        else:
            return self._write_process_legacy(process)
    
    # ========================================================================
    # STEP
    # ========================================================================
    def write_step(self, step: Step, process_id: Optional[str] = None) -> Any:
        """
        Write Step to all 4 databases (UDS3) or Neo4j only (legacy).
        
        UDS3 Mode:
        - Polyglot persistence (4 databases)
        - Auto-creates HAS_STEP relation if process_id provided
        - SAGA rollback on error
        
        Legacy Mode:
        - Neo4j only, manual HAS_STEP
        
        Args:
            step: Step domain model
            process_id: Optional Process ID to link via HAS_STEP
            
        Returns:
            UDS3: Dict with success, database_operations
            Legacy: str (step ID)
        """
        if self.mode == "uds3":
            return self.uds3_ext.create_step(step, process_id=process_id)
        else:
            return self._write_step_legacy(step, process_id)
    
    def link_step_sequence(self, from_step_id: str, to_step_id: str,
                          condition: Optional[str] = None,
                          probability: Optional[float] = None) -> Any:
        """
        Create NEXT relation between steps.
        
        UDS3 Mode: Uses create_uds3_relation (SAGA-safe)
        Legacy Mode: Direct Cypher query
        
        Args:
            from_step_id: Source step
            to_step_id: Target step
            condition: Optional transition condition
            probability: Optional probability (0.0-1.0)
            
        Returns:
            UDS3: Dict with success
            Legacy: None
        """
        if self.mode == "uds3":
            return self.uds3_ext.create_step_sequence(
                from_step_id, to_step_id, condition, probability
            )
        else:
            return self._link_step_sequence_legacy(
                from_step_id, to_step_id, condition, probability
            )
    
    # ========================================================================
    # ROLE
    # ========================================================================
    def write_role(self, role: Role) -> Any:
        """Write Role to all 4 databases (UDS3) or Neo4j only (legacy)."""
        if self.mode == "uds3":
            return self.uds3_ext.create_role(role)
        else:
            return self._write_role_legacy(role)
    
    def link_step_role(self, step_id: str, role_id: str,
                      relation_type: str = "PERFORMED_BY") -> Any:
        """Link Step to Role (PERFORMED_BY, APPROVED_BY, REVIEWED_BY)."""
        if self.mode == "uds3":
            return self.uds3_ext.link_step_to_role(step_id, role_id, relation_type)
        else:
            return self._link_step_role_legacy(step_id, role_id, relation_type)
    
    # ========================================================================
    # ORGUNIT
    # ========================================================================
    def write_org_unit(self, org_unit: OrgUnit) -> Any:
        """Write OrgUnit to all 4 databases (UDS3) or Neo4j only (legacy)."""
        if self.mode == "uds3":
            return self.uds3_ext.create_org_unit(org_unit)
        else:
            return self._write_org_unit_legacy(org_unit)
    
    def link_role_org_unit(self, role_id: str, org_unit_id: str) -> Any:
        """Link Role to OrgUnit via PART_OF."""
        if self.mode == "uds3":
            return self.uds3_ext.uds3.create_uds3_relation(
                "PART_OF", role_id, org_unit_id,
                {"created_at": datetime.utcnow().isoformat()}
            )
        else:
            return self._link_role_org_unit_legacy(role_id, org_unit_id)
    
    # ========================================================================
    # SYSTEM
    # ========================================================================
    def write_system(self, system: System) -> Any:
        """Write System to all 4 databases (UDS3) or Neo4j only (legacy)."""
        if self.mode == "uds3":
            return self.uds3_ext.create_system(system)
        else:
            return self._write_system_legacy(system)
    
    def link_step_system(self, step_id: str, system_id: str) -> Any:
        """Link Step to System via USES_SYSTEM."""
        if self.mode == "uds3":
            return self.uds3_ext.uds3.create_uds3_relation(
                "USES_SYSTEM", step_id, system_id,
                {"created_at": datetime.utcnow().isoformat()}
            )
        else:
            return self._link_step_system_legacy(step_id, system_id)
    
    # ========================================================================
    # CONTROL
    # ========================================================================
    def write_control(self, control: Control) -> Any:
        """Write Control to all 4 databases (UDS3) or Neo4j only (legacy)."""
        if self.mode == "uds3":
            return self.uds3_ext.create_control(control)
        else:
            return self._write_control_legacy(control)
    
    def link_step_control(self, step_id: str, control_id: str) -> Any:
        """Link Step to Control via HAS_CONTROL."""
        if self.mode == "uds3":
            return self.uds3_ext.uds3.create_uds3_relation(
                "HAS_CONTROL", step_id, control_id,
                {"created_at": datetime.utcnow().isoformat()}
            )
        else:
            return self._link_step_control_legacy(step_id, control_id)
    
    # ========================================================================
    # LEGALREF
    # ========================================================================
    def write_legal_ref(self, legal_ref: LegalRef) -> Any:
        """Write LegalRef to all 4 databases (UDS3) or Neo4j only (legacy)."""
        if self.mode == "uds3":
            return self.uds3_ext.create_legal_ref(legal_ref)
        else:
            return self._write_legal_ref_legacy(legal_ref)
    
    def link_step_legal_ref(self, step_id: str, legal_ref_id: str) -> Any:
        """Link Step to LegalRef via MUST_COMPLY_WITH."""
        if self.mode == "uds3":
            return self.uds3_ext.uds3.create_uds3_relation(
                "MUST_COMPLY_WITH", step_id, legal_ref_id,
                {"created_at": datetime.utcnow().isoformat()}
            )
        else:
            return self._link_step_legal_ref_legacy(step_id, legal_ref_id)
    
    def link_process_legal_ref(self, process_id: str, legal_ref_id: str) -> Any:
        """Link Process to LegalRef via GOVERNED_BY."""
        if self.mode == "uds3":
            return self.uds3_ext.uds3.create_uds3_relation(
                "GOVERNED_BY", process_id, legal_ref_id,
                {"created_at": datetime.utcnow().isoformat()}
            )
        else:
            return self._link_process_legal_ref_legacy(process_id, legal_ref_id)
    
    # ========================================================================
    # INFOOBJECT
    # ========================================================================
    def write_info_object(self, info_object: InfoObject) -> Any:
        """Write InfoObject to all 4 databases (UDS3) or Neo4j only (legacy)."""
        if self.mode == "uds3":
            return self.uds3_ext.create_info_object(info_object)
        else:
            return self._write_info_object_legacy(info_object)
    
    def link_step_input(self, step_id: str, info_object_id: str) -> Any:
        """Link InfoObject to Step as INPUT."""
        if self.mode == "uds3":
            return self.uds3_ext.uds3.create_uds3_relation(
                "INPUT", info_object_id, step_id,
                {"created_at": datetime.utcnow().isoformat()}
            )
        else:
            return self._link_step_input_legacy(step_id, info_object_id)
    
    def link_step_output(self, step_id: str, info_object_id: str) -> Any:
        """Link Step to InfoObject as OUTPUT."""
        if self.mode == "uds3":
            return self.uds3_ext.uds3.create_uds3_relation(
                "OUTPUT", step_id, info_object_id,
                {"created_at": datetime.utcnow().isoformat()}
            )
        else:
            return self._link_step_output_legacy(step_id, info_object_id)
    
    # ========================================================================
    # DOCUMENT (Process Evidence)
    # ========================================================================
    def write_document(self, document: Dict[str, Any]) -> Any:
        """
        Write Document to all 4 databases (UDS3) or Neo4j only (legacy).
        
        Document Fields:
        - id, key, title, type, source_uri, published_at, metadata
        
        UDS3 Mode:
        - Polyglot persistence
        - Auto-links published_at to Temporal Canon
        - SAGA rollback
        
        Legacy Mode:
        - Neo4j only
        - Manual temporal linking
        """
        if self.mode == "uds3":
            return self.uds3_ext.create_process_document(document)
        else:
            return self._write_document_legacy(document)
    
    def link_document_to_process(self, document_id: str, process_id: str,
                                 role: Optional[str] = None,
                                 confidence: Optional[float] = None) -> Any:
        """Link Document to Process via RELATES_TO_PROCESS."""
        if self.mode == "uds3":
            return self.uds3_ext.link_document_to_process(
                document_id, process_id, role, confidence
            )
        else:
            return self._link_document_to_process_legacy(
                document_id, process_id, role, confidence
            )
    
    def link_document_to_step(self, document_id: str, step_id: str,
                             relation: str = "EVIDENCES_STEP") -> Any:
        """Link Document to Step (EVIDENCES_STEP | INPUT_OF_STEP | OUTPUT_OF_STEP)."""
        if self.mode == "uds3":
            return self.uds3_ext.link_document_to_step(document_id, step_id, relation)
        else:
            return self._link_document_to_step_legacy(document_id, step_id, relation)
    
    def link_document_validity(self, document_id: str,
                              valid_from: Optional[str] = None,
                              valid_until: Optional[str] = None) -> Any:
        """
        Link Document validity via EFFECTIVE_FROM/UNTIL to Date nodes.
        
        Args:
            document_id: Document ID
            valid_from: ISO date (YYYY-MM-DD)
            valid_until: ISO date (YYYY-MM-DD)
        """
        if self.mode == "uds3":
            return self.uds3_ext.link_document_validity(
                document_id, valid_from, valid_until
            )
        else:
            return self._link_document_validity_legacy(
                document_id, valid_from, valid_until
            )
    
    # ========================================================================
    # RECURRENCE
    # ========================================================================
    def write_recurrence(self, recurrence: Dict[str, Any]) -> Any:
        """
        Write Recurrence to all 4 databases (UDS3) or Neo4j only (legacy).
        
        Recurrence Fields:
        - id, freq, interval, byday, bymonthday, until, count, timezone, rrule
        """
        if self.mode == "uds3":
            return self.uds3_ext.create_recurrence(recurrence)
        else:
            return self._write_recurrence_legacy(recurrence)
    
    def link_entity_recurrence(self, entity_label: str, entity_id: str,
                              recurrence_id: str) -> Any:
        """Link entity (Process|Step|Document) to Recurrence via HAS_RECURRENCE."""
        if self.mode == "uds3":
            return self.uds3_ext.link_entity_recurrence(
                entity_label, entity_id, recurrence_id
            )
        else:
            return self._link_entity_recurrence_legacy(
                entity_label, entity_id, recurrence_id
            )
    
    def materialize_occurrences(self, entity_label: str, entity_id: str,
                               recurrence_id: str,
                               start_date: str, end_date: str) -> Any:
        """
        Materialize StepOccurrence nodes from Recurrence RRULE.
        
        TODO: Implement RRULE calculation utility
        
        Args:
            entity_label: Process | Step | Document
            entity_id: Entity ID
            recurrence_id: Recurrence ID
            start_date: ISO date (YYYY-MM-DD)
            end_date: ISO date (YYYY-MM-DD)
        """
        logger.warning("⚠️ materialize_occurrences not yet implemented (RRULE calculation pending)")
        return {"success": False, "error": "Not implemented - RRULE calculation needed"}
    
    # ========================================================================
    # LEGACY IMPLEMENTATIONS (v1.0 - Neo4j Only)
    # ========================================================================
    def _write_process_legacy(self, process: Process) -> str:
        """Legacy Neo4j-only implementation."""
        cypher = """
        MERGE (p:Process {id: $id})
        SET p.key = $key,
            p.title = $title,
            p.version = $version,
            p.domain = $domain,
            p.owner_org = $owner_org,
            p.status = $status,
            p.created_at = datetime($created_at),
            p.updated_at = datetime($updated_at),
            p.extra = $extra
        RETURN p.id AS process_id
        """
        params = {
            "id": process.id,
            "key": process.key,
            "title": process.title,
            "version": process.version,
            "domain": process.domain,
            "owner_org": process.owner_org,
            "status": process.status,
            "created_at": process.created_at.isoformat() if process.created_at else datetime.utcnow().isoformat(),
            "updated_at": process.updated_at.isoformat() if process.updated_at else datetime.utcnow().isoformat(),
            "extra": process.extra or {},
        }
        
        result = self.graph.execute_query(cypher, params)
        
        # Link to Temporal Canon
        if process.created_at:
            date_iso = process.created_at.date().isoformat()
            self.temporal_canon.upsert_date(date_iso)
            self.temporal_canon.link_occurs_on("Process", process.id, date_iso)
        
        return process.id
    
    def _write_step_legacy(self, step: Step, process_id: Optional[str]) -> str:
        """Legacy Neo4j-only implementation."""
        cypher = """
        MERGE (s:Step {id: $id})
        SET s.process_id = $process_id,
            s.order = $order,
            s.key = $key,
            s.title = $title,
            s.description = $description,
            s.required = $required,
            s.duration_est = $duration_est,
            s.extra = $extra
        RETURN s.id AS step_id
        """
        params = {
            "id": step.id,
            "process_id": step.process_id or process_id,
            "order": step.order,
            "key": step.key,
            "title": step.title,
            "description": step.description,
            "required": step.required,
            "duration_est": step.duration_est,
            "extra": step.extra or {},
        }
        
        self.graph.execute_query(cypher, params)
        
        # Link to Process
        if process_id:
            link_cypher = """
            MATCH (p:Process {id: $process_id})
            MATCH (s:Step {id: $step_id})
            MERGE (p)-[:HAS_STEP]->(s)
            """
            self.graph.execute_query(link_cypher, {
                "process_id": process_id,
                "step_id": step.id
            })
        
        return step.id
    
    def _link_step_sequence_legacy(self, from_step_id: str, to_step_id: str,
                                   condition: Optional[str], probability: Optional[float]) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (from:Step {id: $from_id})
        MATCH (to:Step {id: $to_id})
        MERGE (from)-[r:NEXT]->(to)
        SET r.condition = $condition,
            r.probability = $probability
        """
        self.graph.execute_query(cypher, {
            "from_id": from_step_id,
            "to_id": to_step_id,
            "condition": condition,
            "probability": probability
        })
    
    def _write_role_legacy(self, role: Role) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (r:Role {id: $id})
        SET r.name = $name,
            r.level = $level,
            r.description = $description,
            r.metadata = $metadata
        RETURN r.id AS role_id
        """
        params = {
            "id": role.id,
            "name": role.name,
            "level": role.level,
            "description": role.description,
            "metadata": role.metadata or {}
        }
        self.graph.execute_query(cypher, params)
        return role.id
    
    def _link_step_role_legacy(self, step_id: str, role_id: str, relation_type: str) -> None:
        """Legacy implementation."""
        valid_types = {"PERFORMED_BY", "APPROVED_BY", "REVIEWED_BY"}
        if relation_type not in valid_types:
            relation_type = "PERFORMED_BY"
        
        cypher = f"""
        MATCH (s:Step {{id: $step_id}})
        MATCH (r:Role {{id: $role_id}})
        MERGE (s)-[:{relation_type}]->(r)
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "role_id": role_id})
    
    def _write_org_unit_legacy(self, org_unit: OrgUnit) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (o:OrgUnit {id: $id})
        SET o.name = $name,
            o.level = $level,
            o.description = $description,
            o.metadata = $metadata
        RETURN o.id AS org_unit_id
        """
        params = {
            "id": org_unit.id,
            "name": org_unit.name,
            "level": org_unit.level,
            "description": org_unit.description,
            "metadata": org_unit.metadata or {}
        }
        self.graph.execute_query(cypher, params)
        return org_unit.id
    
    def _link_role_org_unit_legacy(self, role_id: str, org_unit_id: str) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (r:Role {id: $role_id})
        MATCH (o:OrgUnit {id: $org_unit_id})
        MERGE (r)-[:PART_OF]->(o)
        """
        self.graph.execute_query(cypher, {"role_id": role_id, "org_unit_id": org_unit_id})
    
    def _write_system_legacy(self, system: System) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (s:System {id: $id})
        SET s.name = $name,
            s.type = $type,
            s.description = $description,
            s.metadata = $metadata
        RETURN s.id AS system_id
        """
        params = {
            "id": system.id,
            "name": system.name,
            "type": system.type,
            "description": system.description,
            "metadata": system.metadata or {}
        }
        self.graph.execute_query(cypher, params)
        return system.id
    
    def _link_step_system_legacy(self, step_id: str, system_id: str) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (sys:System {id: $system_id})
        MERGE (s)-[:USES_SYSTEM]->(sys)
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "system_id": system_id})
    
    def _write_control_legacy(self, control: Control) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (c:Control {id: $id})
        SET c.name = $name,
            c.type = $type,
            c.criticality = $criticality,
            c.description = $description,
            c.metadata = $metadata
        RETURN c.id AS control_id
        """
        params = {
            "id": control.id,
            "name": control.name,
            "type": control.type,
            "criticality": control.criticality,
            "description": control.description,
            "metadata": control.metadata or {}
        }
        self.graph.execute_query(cypher, params)
        return control.id
    
    def _link_step_control_legacy(self, step_id: str, control_id: str) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (c:Control {id: $control_id})
        MERGE (s)-[:HAS_CONTROL]->(c)
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "control_id": control_id})
    
    def _write_legal_ref_legacy(self, legal_ref: LegalRef) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (l:LegalRef {id: $id})
        SET l.source = $source,
            l.article = $article,
            l.paragraph = $paragraph,
            l.description = $description,
            l.url = $url,
            l.metadata = $metadata
        RETURN l.id AS legal_ref_id
        """
        params = {
            "id": legal_ref.id,
            "source": legal_ref.source,
            "article": legal_ref.article,
            "paragraph": legal_ref.paragraph,
            "description": legal_ref.description,
            "url": legal_ref.url,
            "metadata": legal_ref.metadata or {}
        }
        self.graph.execute_query(cypher, params)
        return legal_ref.id
    
    def _link_step_legal_ref_legacy(self, step_id: str, legal_ref_id: str) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (l:LegalRef {id: $legal_ref_id})
        MERGE (s)-[:MUST_COMPLY_WITH]->(l)
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "legal_ref_id": legal_ref_id})
    
    def _link_process_legal_ref_legacy(self, process_id: str, legal_ref_id: str) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (p:Process {id: $process_id})
        MATCH (l:LegalRef {id: $legal_ref_id})
        MERGE (p)-[:GOVERNED_BY]->(l)
        """
        self.graph.execute_query(cypher, {"process_id": process_id, "legal_ref_id": legal_ref_id})
    
    def _write_info_object_legacy(self, info_object: InfoObject) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (i:InfoObject {id: $id})
        SET i.key = $key,
            i.name = $name,
            i.type = $type,
            i.description = $description,
            i.required = $required,
            i.retention_days = $retention_days,
            i.metadata = $metadata
        RETURN i.id AS info_object_id
        """
        params = {
            "id": info_object.id,
            "key": info_object.key,
            "name": info_object.name,
            "type": info_object.type,
            "description": info_object.description,
            "required": info_object.required,
            "retention_days": info_object.retention_days,
            "metadata": info_object.metadata or {}
        }
        self.graph.execute_query(cypher, params)
        return info_object.id
    
    def _link_step_input_legacy(self, step_id: str, info_object_id: str) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (i:InfoObject {id: $info_object_id})
        MATCH (s:Step {id: $step_id})
        MERGE (i)-[:INPUT]->(s)
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "info_object_id": info_object_id})
    
    def _link_step_output_legacy(self, step_id: str, info_object_id: str) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (i:InfoObject {id: $info_object_id})
        MERGE (s)-[:OUTPUT]->(i)
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "info_object_id": info_object_id})
    
    def _write_document_legacy(self, document: Dict[str, Any]) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (d:Document {id: $id})
        SET d.key = $key,
            d.title = $title,
            d.type = $type,
            d.source_uri = $source_uri,
            d.published_at = datetime($published_at),
            d.created_at = datetime(),
            d.metadata = $metadata
        RETURN d.id AS document_id
        """
        params = {
            "id": document["id"],
            "key": document.get("key"),
            "title": document.get("title"),
            "type": document.get("type"),
            "source_uri": document.get("source_uri"),
            "published_at": document.get("published_at", datetime.utcnow().isoformat()),
            "metadata": document.get("metadata", {})
        }
        self.graph.execute_query(cypher, params)
        
        # Link to Temporal Canon
        if document.get("published_at"):
            date_iso = document["published_at"].split("T")[0]
            self.temporal_canon.upsert_date(date_iso)
            self.temporal_canon.link_occurs_on("Document", document["id"], date_iso)
        
        return document["id"]
    
    def _link_document_to_process_legacy(self, document_id: str, process_id: str,
                                        role: Optional[str], confidence: Optional[float]) -> None:
        """Legacy implementation."""
        cypher = """
        MATCH (d:Document {id: $document_id})
        MATCH (p:Process {id: $process_id})
        MERGE (d)-[r:RELATES_TO_PROCESS]->(p)
        SET r.role = $role,
            r.confidence = $confidence,
            r.created_at = datetime()
        """
        self.graph.execute_query(cypher, {
            "document_id": document_id,
            "process_id": process_id,
            "role": role,
            "confidence": confidence
        })
    
    def _link_document_to_step_legacy(self, document_id: str, step_id: str, relation: str) -> None:
        """Legacy implementation."""
        valid_relations = {"EVIDENCES_STEP", "INPUT_OF_STEP", "OUTPUT_OF_STEP"}
        if relation not in valid_relations:
            relation = "EVIDENCES_STEP"
        
        cypher = f"""
        MATCH (d:Document {{id: $document_id}})
        MATCH (s:Step {{id: $step_id}})
        MERGE (d)-[:{relation}]->(s)
        """
        self.graph.execute_query(cypher, {"document_id": document_id, "step_id": step_id})
    
    def _link_document_validity_legacy(self, document_id: str,
                                      valid_from: Optional[str],
                                      valid_until: Optional[str]) -> None:
        """Legacy implementation."""
        if valid_from:
            self.temporal_canon.upsert_date(valid_from)
            # Create EFFECTIVE_FROM via Temporal Canon
            cypher_from = """
            MATCH (d:Document {id: $document_id})
            MATCH (date:Date {iso: $date_iso})
            MERGE (d)-[:EFFECTIVE_FROM]->(date)
            """
            self.graph.execute_query(cypher_from, {
                "document_id": document_id,
                "date_iso": valid_from
            })
        
        if valid_until:
            self.temporal_canon.upsert_date(valid_until)
            cypher_until = """
            MATCH (d:Document {id: $document_id})
            MATCH (date:Date {iso: $date_iso})
            MERGE (d)-[:EFFECTIVE_UNTIL]->(date)
            """
            self.graph.execute_query(cypher_until, {
                "document_id": document_id,
                "date_iso": valid_until
            })
    
    def _write_recurrence_legacy(self, recurrence: Dict[str, Any]) -> str:
        """Legacy implementation."""
        cypher = """
        MERGE (r:Recurrence {id: $id})
        SET r.freq = $freq,
            r.interval = $interval,
            r.byday = $byday,
            r.bymonthday = $bymonthday,
            r.until = $until,
            r.count = $count,
            r.timezone = $timezone,
            r.rrule = $rrule,
            r.created_at = datetime()
        RETURN r.id AS recurrence_id
        """
        params = {
            "id": recurrence["id"],
            "freq": recurrence.get("freq"),
            "interval": recurrence.get("interval"),
            "byday": recurrence.get("byday"),
            "bymonthday": recurrence.get("bymonthday"),
            "until": recurrence.get("until"),
            "count": recurrence.get("count"),
            "timezone": recurrence.get("timezone"),
            "rrule": recurrence.get("rrule")
        }
        self.graph.execute_query(cypher, params)
        return recurrence["id"]
    
    def _link_entity_recurrence_legacy(self, entity_label: str, entity_id: str,
                                      recurrence_id: str) -> None:
        """Legacy implementation."""
        if entity_label not in {"Process", "Step", "Document"}:
            raise ValueError(f"Unsupported entity: {entity_label}")
        
        cypher = f"""
        MATCH (e:{entity_label} {{id: $entity_id}})
        MATCH (r:Recurrence {{id: $recurrence_id}})
        MERGE (e)-[:HAS_RECURRENCE]->(r)
        """
        self.graph.execute_query(cypher, {
            "entity_id": entity_id,
            "recurrence_id": recurrence_id
        })
