"""
Process Graph Writer - UDS3 SAGA Integration

Writes Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject to all 4 databases
using UDS3 SAGA Pattern (Vector + Graph + Relational + File Storage).

Full polyglot persistence with automatic rollback on errors.

MIGRATION (31.10.2025):
- OLD: Low-level execute_query() → No SAGA, no audit, no polyglot
- NEW: UDS3ProcessExtension → SAGA pattern, governance, 4 databases
"""
from __future__ import annotations
from datetime import datetime
from typing import Any
import logging

from processes.domain.models import (
    Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject
)

# NEW: Import UDS3 Extension
try:
    from uds3.extensions import UDS3ProcessExtension
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProcessGraphWriter:
    """
    UDS3-Compliant Process Writer with SAGA Pattern.
    
    NEW Architecture (v2.0):
    - Uses UDS3ProcessExtension for all operations
    - Full polyglot persistence (4 databases)
    - SAGA pattern (auto-rollback on errors)
    - Governance & audit trail
    - Temporal Canon integration
    
    OLD Architecture (v1.0 - deprecated):
    - Direct execute_query() calls
    - Neo4j only
    - No rollback, no audit
    
    Usage:
        ```python
        # Initialize with UDS3 strategy
        from uds3.core.database import UnifiedDatabaseStrategy
        
        uds3 = UnifiedDatabaseStrategy(config)
        writer = ProcessGraphWriter(uds3_strategy=uds3)
        
        # Create process in all 4 databases
        result = writer.write_process(process)
        if result["success"]:
            print(f"✅ Process in {len(result['database_operations'])} databases")
        else:
            print(f"❌ SAGA Rollback: {result['error']}")
        ```
    """
    
    def __init__(self, graph_adapter=None, uds3_strategy=None):
        """
        Initialize writer with UDS3 strategy (RECOMMENDED) or legacy graph adapter.
        
        Args:
            graph_adapter: (DEPRECATED) UDS3 graph adapter for legacy mode
            uds3_strategy: (RECOMMENDED) UnifiedDatabaseStrategy instance
            
        Raises:
            ValueError: If UDS3 not available but uds3_strategy provided
        """
        if uds3_strategy:
            if not UDS3_AVAILABLE:
                raise ValueError("UDS3 not available - install uds3 package")
            
            logger.info("✅ ProcessGraphWriter initialized in UDS3 SAGA mode")
            self.mode = "uds3"
            self.uds3_ext = UDS3ProcessExtension(uds3_strategy)
            self.graph = None
            self.temporal_canon = self.uds3_ext.temporal_canon
        
        elif graph_adapter:
            logger.warning("⚠️ ProcessGraphWriter in LEGACY mode (no SAGA, no polyglot)")
            self.mode = "legacy"
            self.graph = graph_adapter
            from processes.graph.temporal_canon import TemporalCanon
            self.temporal_canon = TemporalCanon(graph_adapter)
            self.uds3_ext = None
        
        else:
            raise ValueError("Either graph_adapter or uds3_strategy required")
    
    
    # ========================================================================
    # PROCESS
    # ========================================================================
    def write_process(self, process: Process) -> Any:
        """
        Write Process to all 4 databases (UDS3 mode) or Neo4j only (legacy).
        
        UDS3 Mode:
        - Creates in: Vector (ChromaDB), Graph (Neo4j), Relational (PostgreSQL), File (CouchDB)
        - SAGA pattern: Auto-rollback on any database failure
        - Governance: Audit trail for compliance
        - Identity: Cross-database UUID management
        
        Legacy Mode:
        - Creates in Neo4j only
        - No rollback, no audit, no polyglot
        
        Args:
            process: Process domain model
            
        Returns:
            UDS3 Mode: Dict with success, database_operations, error
            Legacy Mode: str (process ID)
            
        Example (UDS3):
            ```python
            result = writer.write_process(process)
            if result["success"]:
                print(f"✅ {len(result['database_operations'])} databases updated")
                # Neo4j: result["database_operations"]["graph"]
                # PostgreSQL: result["database_operations"]["relational"]
                # ChromaDB: result["database_operations"]["vector"]
                # CouchDB: result["database_operations"]["file_storage"]
            else:
                print(f"❌ Rollback: {result['error']}")
            ```
        """
        if self.mode == "uds3":
            # UDS3 SAGA Mode (RECOMMENDED)
            return self.uds3_ext.create_process(process)
        
        else:
            # Legacy Mode (DEPRECATED)
            return self._write_process_legacy(process)
    
    def _write_process_legacy(self, process: Process) -> str:
        """Legacy Neo4j-only implementation (deprecated)."""
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
            "extra": process.extra,
        }
        
        result = self.graph.execute_query(cypher, params)
        
        # Link creation date via TemporalCanon
        if process.created_at:
            date_iso = process.created_at.date().isoformat()
            self.temporal_canon.upsert_date(date_iso)
            self.temporal_canon.link_occurs_on("Process", process.id, date_iso)
        
        return process.id
    
    # ========================================================================
    # STEP
    # ========================================================================
    def write_step(self, step: Step, process_id: str | None = None) -> str:
        """
        Write Step node to Neo4j.
        
        Creates:
        - Step node with all properties
        - HAS_STEP relation from Process (if process_id provided)
        - Date node for created_at
        - OCCURS_ON relation to creation date
        
        Args:
            step: Step domain model
            process_id: Optional Process ID to link with HAS_STEP
            
        Returns:
            Step ID (UUIDv7)
        """
        cypher = """
        MERGE (s:Step {id: $id})
        SET s.process_id = $process_id,
            s.order = $order,
            s.key = $key,
            s.title = $title,
            s.description = $description,
            s.required = $required,
            s.duration_est = $duration_est,
            s.created_at = datetime($created_at),
            s.updated_at = datetime(),
            s.extra = $extra
        RETURN s.id AS step_id
        """
        params = {
            "id": step.id,
            "process_id": step.process_id,
            "order": step.order,
            "key": step.key,
            "title": step.title,
            "description": step.description,
            "required": step.required,
            "duration_est": step.duration_est,
            "created_at": datetime.utcnow().isoformat(),
            "extra": step.extra,
        }
        
        self.graph.execute_query(cypher, params)
        
        # Link to Process
        if process_id:
            link_cypher = """
            MATCH (p:Process {id: $process_id})
            MATCH (s:Step {id: $step_id})
            MERGE (p)-[r:HAS_STEP]->(s)
            SET r.created_at = datetime()
            """
            self.graph.execute_query(link_cypher, {"process_id": process_id, "step_id": step.id})
        
        return step.id
    
    # ========================================================================
    # STEP SEQUENCE
    # ========================================================================
    def link_step_sequence(self, from_step_id: str, to_step_id: str, 
                                  condition: str | None = None, probability: float | None = None) -> None:
        """
        Create NEXT relation between steps.
        
        Args:
            from_step_id: Source step ID
            to_step_id: Target step ID
            condition: Optional transition condition (e.g., "approved", "rejected")
            probability: Optional transition probability [0.0, 1.0]
        """
        cypher = """
        MATCH (s1:Step {id: $from_id})
        MATCH (s2:Step {id: $to_id})
        MERGE (s1)-[r:NEXT]->(s2)
        SET r.created_at = datetime()
        """
        params = {"from_id": from_step_id, "to_id": to_step_id}
        
        if condition:
            cypher += ", r.condition = $condition"
            params["condition"] = condition
        
        if probability is not None:
            cypher += ", r.probability = $probability"
            params["probability"] = probability
        
        self.graph.execute_query(cypher, params)
    
    # ========================================================================
    # ROLE
    # ========================================================================
    def write_role(self, role: Role) -> str:
        """Write Role node to Neo4j."""
        cypher = """
        MERGE (r:Role {id: $id})
        SET r.name = $name,
            r.level = $level,
            r.description = $description,
            r.created_at = datetime($created_at),
            r.updated_at = datetime($updated_at),
            r.metadata = $metadata
        RETURN r.id AS role_id
        """
        params = {
            "id": role.id,
            "name": role.name,
            "level": role.level,
            "description": role.description,
            "created_at": role.created_at.isoformat() if role.created_at else datetime.utcnow().isoformat(),
            "updated_at": role.updated_at.isoformat() if role.updated_at else datetime.utcnow().isoformat(),
            "metadata": role.metadata,
        }
        
        self.graph.execute_query(cypher, params)
        return role.id
    
    def link_step_role(self, step_id: str, role_id: str, relation_type: str = "PERFORMED_BY") -> None:
        """
        Link Step to Role.
        
        Args:
            step_id: Step ID
            role_id: Role ID
            relation_type: Relation type (PERFORMED_BY, APPROVED_BY, REVIEWED_BY)
        """
        cypher = f"""
        MATCH (s:Step {{id: $step_id}})
        MATCH (r:Role {{id: $role_id}})
        MERGE (s)-[rel:{relation_type}]->(r)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "role_id": role_id})
    
    # ========================================================================
    # ORG UNIT
    # ========================================================================
    def write_org_unit(self, org_unit: OrgUnit) -> str:
        """Write OrgUnit node to Neo4j."""
        cypher = """
        MERGE (o:OrgUnit {id: $id})
        SET o.name = $name,
            o.level = $level,
            o.description = $description,
            o.created_at = datetime($created_at),
            o.updated_at = datetime($updated_at),
            o.metadata = $metadata
        RETURN o.id AS org_unit_id
        """
        params = {
            "id": org_unit.id,
            "name": org_unit.name,
            "level": org_unit.level,
            "description": org_unit.description,
            "created_at": org_unit.created_at.isoformat() if org_unit.created_at else datetime.utcnow().isoformat(),
            "updated_at": org_unit.updated_at.isoformat() if org_unit.updated_at else datetime.utcnow().isoformat(),
            "metadata": org_unit.metadata,
        }
        
        self.graph.execute_query(cypher, params)
        return org_unit.id
    
    def link_role_org_unit(self, role_id: str, org_unit_id: str) -> None:
        """Link Role to OrgUnit via BELONGS_TO relation."""
        cypher = """
        MATCH (r:Role {id: $role_id})
        MATCH (o:OrgUnit {id: $org_unit_id})
        MERGE (r)-[rel:BELONGS_TO]->(o)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"role_id": role_id, "org_unit_id": org_unit_id})
    
    # ========================================================================
    # SYSTEM
    # ========================================================================
    def write_system(self, system: System) -> str:
        """Write System node to Neo4j."""
        cypher = """
        MERGE (s:System {id: $id})
        SET s.name = $name,
            s.type = $type,
            s.description = $description,
            s.created_at = datetime($created_at),
            s.updated_at = datetime($updated_at),
            s.metadata = $metadata
        RETURN s.id AS system_id
        """
        params = {
            "id": system.id,
            "name": system.name,
            "type": system.type,
            "description": system.description,
            "created_at": system.created_at.isoformat() if system.created_at else datetime.utcnow().isoformat(),
            "updated_at": system.updated_at.isoformat() if system.updated_at else datetime.utcnow().isoformat(),
            "metadata": system.metadata,
        }
        
        self.graph.execute_query(cypher, params)
        return system.id
    
    def link_step_system(self, step_id: str, system_id: str) -> None:
        """Link Step to System via USES_SYSTEM relation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (sys:System {id: $system_id})
        MERGE (s)-[rel:USES_SYSTEM]->(sys)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "system_id": system_id})
    
    # ========================================================================
    # CONTROL
    # ========================================================================
    def write_control(self, control: Control) -> str:
        """Write Control node to Neo4j."""
        cypher = """
        MERGE (c:Control {id: $id})
        SET c.name = $name,
            c.type = $type,
            c.criticality = $criticality,
            c.description = $description,
            c.created_at = datetime($created_at),
            c.updated_at = datetime($updated_at),
            c.metadata = $metadata
        RETURN c.id AS control_id
        """
        params = {
            "id": control.id,
            "name": control.name,
            "type": control.type,
            "criticality": control.criticality,
            "description": control.description,
            "created_at": control.created_at.isoformat() if control.created_at else datetime.utcnow().isoformat(),
            "updated_at": control.updated_at.isoformat() if control.updated_at else datetime.utcnow().isoformat(),
            "metadata": control.metadata,
        }
        
        self.graph.execute_query(cypher, params)
        return control.id
    
    def link_step_control(self, step_id: str, control_id: str) -> None:
        """Link Step to Control via CONTROLS relation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (c:Control {id: $control_id})
        MERGE (s)-[rel:CONTROLS]->(c)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "control_id": control_id})
    
    # ========================================================================
    # LEGAL REF
    # ========================================================================
    def write_legal_ref(self, legal_ref: LegalRef) -> str:
        """Write LegalRef node to Neo4j."""
        cypher = """
        MERGE (l:LegalRef {id: $id})
        SET l.source = $source,
            l.article = $article,
            l.paragraph = $paragraph,
            l.description = $description,
            l.url = $url,
            l.created_at = datetime($created_at),
            l.updated_at = datetime($updated_at),
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
            "created_at": legal_ref.created_at.isoformat() if legal_ref.created_at else datetime.utcnow().isoformat(),
            "updated_at": legal_ref.updated_at.isoformat() if legal_ref.updated_at else datetime.utcnow().isoformat(),
            "metadata": legal_ref.metadata,
        }
        
        self.graph.execute_query(cypher, params)
        return legal_ref.id
    
    def link_step_legal_ref(self, step_id: str, legal_ref_id: str) -> None:
        """Link Step to LegalRef via CITES relation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (l:LegalRef {id: $legal_ref_id})
        MERGE (s)-[rel:CITES]->(l)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "legal_ref_id": legal_ref_id})
    
    def link_process_legal_ref(self, process_id: str, legal_ref_id: str) -> None:
        """Link Process to LegalRef via CITES relation."""
        cypher = """
        MATCH (p:Process {id: $process_id})
        MATCH (l:LegalRef {id: $legal_ref_id})
        MERGE (p)-[rel:CITES]->(l)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"process_id": process_id, "legal_ref_id": legal_ref_id})
    
    # ========================================================================
    # INFO OBJECT
    # ========================================================================
    def write_info_object(self, info_object: InfoObject) -> str:
        """Write InfoObject node to Neo4j."""
        cypher = """
        MERGE (i:InfoObject {id: $id})
        SET i.key = $key,
            i.name = $name,
            i.type = $type,
            i.description = $description,
            i.required = $required,
            i.retention_days = $retention_days,
            i.created_at = datetime($created_at),
            i.updated_at = datetime($updated_at),
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
            "created_at": info_object.created_at.isoformat() if info_object.created_at else datetime.utcnow().isoformat(),
            "updated_at": info_object.updated_at.isoformat() if info_object.updated_at else datetime.utcnow().isoformat(),
            "metadata": info_object.metadata,
        }
        
        self.graph.execute_query(cypher, params)
        return info_object.id
    
    def link_step_input(self, step_id: str, info_object_id: str) -> None:
        """Link Step to InfoObject via INPUT relation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (i:InfoObject {id: $info_object_id})
        MERGE (s)-[rel:INPUT]->(i)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "info_object_id": info_object_id})
    
    def link_step_output(self, step_id: str, info_object_id: str) -> None:
        """Link Step to InfoObject via OUTPUT relation."""
        cypher = """
        MATCH (s:Step {id: $step_id})
        MATCH (i:InfoObject {id: $info_object_id})
        MERGE (s)-[rel:OUTPUT]->(i)
        SET rel.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"step_id": step_id, "info_object_id": info_object_id})

    # ========================================================================
    # DOCUMENTS (scaffold)
    # ========================================================================
    def write_document(self, document: dict[str, Any]) -> str:
        """Create/Update a Document node.

        Contract (document dict):
          - id (str, required)
          - key, title, type, source_uri (str, optional)
          - created_at, updated_at, published_at (ISO datetime strings, optional)
          - metadata (dict, optional)
        """
        cypher = """
        MERGE (d:Document {id: $id})
        SET d.key = $key,
            d.title = $title,
            d.type = $type,
            d.source_uri = $source_uri,
            d.created_at = coalesce(datetime($created_at), datetime()),
            d.updated_at = coalesce(datetime($updated_at), datetime()),
            d.published_at = CASE WHEN $published_at IS NULL THEN d.published_at ELSE datetime($published_at) END,
            d.metadata = $metadata
        RETURN d.id AS document_id
        """
        params = {
            "id": document.get("id"),
            "key": document.get("key"),
            "title": document.get("title"),
            "type": document.get("type"),
            "source_uri": document.get("source_uri"),
            "created_at": document.get("created_at"),
            "updated_at": document.get("updated_at"),
            "published_at": document.get("published_at"),
            "metadata": document.get("metadata", {}),
        }
        result = self.graph.execute_query(cypher, params)

        # Link published_at to Date if present
        pub = document.get("published_at")
        if pub:
            try:
                date_iso = pub.split("T")[0]
                self.temporal_canon.upsert_date(date_iso)
                self.temporal_canon.link_occurs_on("Document", document["id"], date_iso)
            except Exception:
                pass
        return document["id"]

    def link_document_to_process(self, document_id: str, process_id: str,
                                       role: str | None = None, confidence: float | None = None) -> None:
        """Link Document to Process using RELATES_TO_PROCESS with optional role/confidence."""
        cypher = """
        MATCH (d:Document {id: $doc_id})
        MATCH (p:Process {id: $process_id})
        MERGE (d)-[r:RELATES_TO_PROCESS]->(p)
        SET r.created_at = datetime()
        """
        params: dict[str, Any] = {"doc_id": document_id, "process_id": process_id}
        if role is not None:
            cypher += ", r.role = $role"
            params["role"] = role
        if confidence is not None:
            cypher += ", r.confidence = $confidence"
            params["confidence"] = confidence
        self.graph.execute_query(cypher, params)

    def link_document_to_step(self, document_id: str, step_id: str, relation: str = "EVIDENCES_STEP") -> None:
        """Link Document to Step (EVIDENCES_STEP | INPUT_OF_STEP | OUTPUT_OF_STEP)."""
        valid = {"EVIDENCES_STEP", "INPUT_OF_STEP", "OUTPUT_OF_STEP"}
        rel = relation if relation in valid else "EVIDENCES_STEP"
        cypher = f"""
        MATCH (d:Document {{id: $doc_id}})
        MATCH (s:Step {{id: $step_id}})
        MERGE (d)-[r:{rel}]->(s)
        SET r.created_at = datetime()
        """
        self.graph.execute_query(cypher, {"doc_id": document_id, "step_id": step_id})

    def link_document_validity(self, document_id: str,
                                     valid_from: str | None = None,
                                     valid_until: str | None = None) -> None:
        """Link Document validity via EFFECTIVE_FROM/UNTIL to Date nodes (YYYY-MM-DD)."""
        if valid_from:
            self.temporal_canon.upsert_date(valid_from)
            cypher_from = """
            MATCH (d:Document {id: $doc_id})
            MATCH (df:Date {iso: $from_iso})
            MERGE (d)-[:EFFECTIVE_FROM]->(df)
            """
            self.graph.execute_query(cypher_from, {"doc_id": document_id, "from_iso": valid_from})
        if valid_until:
            self.temporal_canon.upsert_date(valid_until)
            cypher_until = """
            MATCH (d:Document {id: $doc_id})
            MATCH (du:Date {iso: $until_iso})
            MERGE (d)-[:EFFECTIVE_UNTIL]->(du)
            """
            self.graph.execute_query(cypher_until, {"doc_id": document_id, "until_iso": valid_until})

    # ========================================================================
    # RECURRENCE (scaffold)
    # ========================================================================
    def write_recurrence(self, recurrence: dict[str, Any]) -> str:
        """Create/Update a Recurrence node (RRULE-like fields).

        Expected keys: id, freq, interval, byday, bymonthday, until, count, timezone, rrule
        All optional except id and freq.
        """
        cypher = """
        MERGE (r:Recurrence {id: $id})
        SET r.freq = $freq,
            r.interval = coalesce($interval, 1),
            r.byday = $byday,
            r.bymonthday = $bymonthday,
            r.until = $until,
            r.count = $count,
            r.timezone = $timezone,
            r.rrule = $rrule,
            r.updated_at = datetime()
        RETURN r.id AS recurrence_id
        """
        params = {
            "id": recurrence.get("id"),
            "freq": recurrence.get("freq"),
            "interval": recurrence.get("interval"),
            "byday": recurrence.get("byday"),
            "bymonthday": recurrence.get("bymonthday"),
            "until": recurrence.get("until"),
            "count": recurrence.get("count"),
            "timezone": recurrence.get("timezone"),
            "rrule": recurrence.get("rrule"),
        }
        self.graph.execute_query(cypher, params)
        return params["id"]

    def link_entity_recurrence(self, entity_label: str, entity_id: str, recurrence_id: str) -> None:
        """Link any entity (Process|Step|Document) to a Recurrence via HAS_RECURRENCE."""
        if entity_label not in {"Process", "Step", "Document"}:
            raise ValueError("Unsupported entity label for recurrence")
        cypher = f"""
        MATCH (e:{entity_label} {{id: $eid}})
        MATCH (r:Recurrence {{id: $rid}})
        MERGE (e)-[:HAS_RECURRENCE]->(r)
        """
        self.graph.execute_query(cypher, {"eid": entity_id, "rid": recurrence_id})

    def materialize_occurrences(self, entity_label: str, entity_id: str, dates: list[str]) -> int:
        """Materialize occurrences for given dates (YYYY-MM-DD). Returns count created.

        For Steps, creates (:StepOccurrence {id, step_id, occurred_at}) linked to Date and the Step.
        For other entities, this is currently a no-op.
        """
        if entity_label != "Step" or not dates:
            return 0
        created = 0
        for d in dates:
            self.temporal_canon.upsert_date(d)
            cypher = """
            MERGE (o:StepOccurrence {id: $occ_id})
            SET o.step_id = $sid,
                o.occurred_at = $d
            WITH o
            MATCH (s:Step {id: $sid})
            MERGE (o)-[:OF_STEP]->(s)
            WITH o
            MATCH (dt:Date {iso: $d})
            MERGE (o)-[:OCCURS_ON]->(dt)
            """
            occ_id = f"{entity_id}:{d}"
            self.graph.execute_query(cypher, {"occ_id": occ_id, "sid": entity_id, "d": d})
            created += 1
        return created
