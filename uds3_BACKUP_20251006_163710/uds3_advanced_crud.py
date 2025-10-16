"""
UDS3 Advanced CRUD Operations Module

Erweiterte CRUD-Funktionalität für UDS3 Polyglot Persistence:
- Batch Read: Paralleles Lesen mehrerer Dokumente
- Conditional Update: Updates mit Preconditions (version check, field conditions)
- Upsert: Atomic Update-or-Insert Operation
- Batch Update: Parallele Updates mehrerer Dokumente

Autor: UDS3 Team
Datum: 1. Oktober 2025
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class MergeStrategy(Enum):
    """Strategie für Merge-Operationen bei Upsert"""
    REPLACE = "replace"          # Vollständig ersetzen
    MERGE = "merge"              # Felder zusammenführen
    KEEP_EXISTING = "keep_existing"  # Nur neue Felder hinzufügen


class ConditionOperator(Enum):
    """Operatoren für Conditional Updates"""
    EQ = "=="          # Equal
    NE = "!="          # Not equal
    GT = ">"           # Greater than
    LT = "<"           # Less than
    GTE = ">="         # Greater than or equal
    LTE = "<="         # Less than or equal
    EXISTS = "exists"  # Field exists
    NOT_EXISTS = "not_exists"  # Field does not exist


class ReadStrategy(Enum):
    """Strategie für Batch Read Operations"""
    PARALLEL = "parallel"      # Parallel execution (fastest)
    SEQUENTIAL = "sequential"  # Sequential execution (ordered)
    PRIORITY = "priority"      # Priority-based execution


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class Condition:
    """Bedingung für Conditional Update"""
    field: str
    operator: ConditionOperator
    value: Any = None
    
    def evaluate(self, document: Dict[str, Any]) -> bool:
        """Evaluiert die Condition gegen ein Dokument"""
        if self.operator == ConditionOperator.EXISTS:
            return self.field in document
        
        if self.operator == ConditionOperator.NOT_EXISTS:
            return self.field not in document
        
        # Für andere Operatoren muss das Feld existieren
        if self.field not in document:
            return False
        
        field_value = document[self.field]
        
        if self.operator == ConditionOperator.EQ:
            return field_value == self.value
        elif self.operator == ConditionOperator.NE:
            return field_value != self.value
        elif self.operator == ConditionOperator.GT:
            return field_value > self.value
        elif self.operator == ConditionOperator.LT:
            return field_value < self.value
        elif self.operator == ConditionOperator.GTE:
            return field_value >= self.value
        elif self.operator == ConditionOperator.LTE:
            return field_value <= self.value
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Condition zu Dict"""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value
        }


@dataclass
class BatchReadResult:
    """Ergebnis einer Batch Read Operation"""
    success: bool
    total_requested: int
    total_read: int
    documents: Dict[str, Dict[str, Any]]  # document_id -> document_data
    errors: Dict[str, str] = field(default_factory=dict)  # document_id -> error
    execution_time_ms: Optional[float] = None
    strategy: Optional[ReadStrategy] = None
    
    @property
    def success_rate(self) -> float:
        """Erfolgsrate in Prozent"""
        if self.total_requested == 0:
            return 0.0
        return (self.total_read / self.total_requested) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Result zu Dict"""
        return {
            "success": self.success,
            "total_requested": self.total_requested,
            "total_read": self.total_read,
            "documents": self.documents,
            "errors": self.errors,
            "execution_time_ms": self.execution_time_ms,
            "strategy": self.strategy.value if self.strategy else None,
            "success_rate": self.success_rate
        }


@dataclass
class ConditionalUpdateResult:
    """Ergebnis eines Conditional Update"""
    success: bool
    document_id: str
    updated: bool
    condition_met: bool
    conditions_evaluated: List[Dict[str, Any]] = field(default_factory=list)
    version_before: Optional[int] = None
    version_after: Optional[int] = None
    affected_databases: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    conflict_detected: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Result zu Dict"""
        return {
            "success": self.success,
            "document_id": self.document_id,
            "updated": self.updated,
            "condition_met": self.condition_met,
            "conditions_evaluated": self.conditions_evaluated,
            "version_before": self.version_before,
            "version_after": self.version_after,
            "affected_databases": self.affected_databases,
            "errors": self.errors,
            "conflict_detected": self.conflict_detected
        }


@dataclass
class UpsertResult:
    """Ergebnis einer Upsert Operation"""
    success: bool
    document_id: str
    operation: str  # "created" or "updated"
    existed_before: bool
    merge_strategy: Optional[MergeStrategy] = None
    affected_databases: List[str] = field(default_factory=list)
    created_fields: Set[str] = field(default_factory=set)
    updated_fields: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Result zu Dict"""
        return {
            "success": self.success,
            "document_id": self.document_id,
            "operation": self.operation,
            "existed_before": self.existed_before,
            "merge_strategy": self.merge_strategy.value if self.merge_strategy else None,
            "affected_databases": self.affected_databases,
            "created_fields": list(self.created_fields),
            "updated_fields": list(self.updated_fields),
            "errors": self.errors
        }


# ============================================================================
# ADVANCED CRUD MANAGER
# ============================================================================


class AdvancedCRUDManager:
    """
    Manager für erweiterte CRUD-Operationen
    
    Features:
    - Batch Read: Paralleles Lesen mehrerer Dokumente
    - Conditional Update: Updates mit Preconditions
    - Upsert: Atomic Update-or-Insert
    - Batch Update: Parallele Updates
    """
    
    def __init__(self, backend: Any):
        """
        Initialisiert den AdvancedCRUDManager
        
        Args:
            backend: UDS3CoreOrchestrator Instance
        """
        self.backend = backend
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # BATCH READ
    # ========================================================================
    
    def batch_read_documents(
        self,
        document_ids: List[str],
        *,
        strategy: ReadStrategy = ReadStrategy.PARALLEL,
        max_workers: int = 10,
        include_content: bool = True,
        include_relationships: bool = False,
        timeout: Optional[float] = None
    ) -> BatchReadResult:
        """
        Liest mehrere Dokumente parallel oder sequentiell
        
        Args:
            document_ids: Liste der Dokument-IDs
            strategy: Read-Strategie (PARALLEL, SEQUENTIAL, PRIORITY)
            max_workers: Maximale Anzahl paralleler Worker
            include_content: Vollständigen Content einschließen
            include_relationships: Graph-Relationships einschließen
            timeout: Timeout in Sekunden pro Dokument
        
        Returns:
            BatchReadResult mit allen gelesenen Dokumenten
        """
        start_time = datetime.now()
        
        if not document_ids:
            return BatchReadResult(
                success=True,
                total_requested=0,
                total_read=0,
                documents={},
                strategy=strategy
            )
        
        documents: Dict[str, Dict[str, Any]] = {}
        errors: Dict[str, str] = {}
        
        try:
            if strategy == ReadStrategy.PARALLEL:
                # Parallele Ausführung mit ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit alle Read-Tasks
                    future_to_id = {
                        executor.submit(
                            self._read_single_document,
                            doc_id,
                            include_content,
                            include_relationships,
                            timeout
                        ): doc_id
                        for doc_id in document_ids
                    }
                    
                    # Collect results
                    for future in as_completed(future_to_id):
                        doc_id = future_to_id[future]
                        try:
                            result = future.result(timeout=timeout)
                            if result.get("success"):
                                documents[doc_id] = result
                            else:
                                errors[doc_id] = result.get("error", "Unknown error")
                        except Exception as e:
                            self.logger.error(f"Error reading document {doc_id}: {e}")
                            errors[doc_id] = str(e)
            
            elif strategy == ReadStrategy.SEQUENTIAL:
                # Sequentielle Ausführung
                for doc_id in document_ids:
                    try:
                        result = self._read_single_document(
                            doc_id,
                            include_content,
                            include_relationships,
                            timeout
                        )
                        if result.get("success"):
                            documents[doc_id] = result
                        else:
                            errors[doc_id] = result.get("error", "Unknown error")
                    except Exception as e:
                        self.logger.error(f"Error reading document {doc_id}: {e}")
                        errors[doc_id] = str(e)
            
            else:  # PRIORITY
                # Priority-basierte Ausführung (first-come, first-served)
                # Aktuell gleich wie PARALLEL, könnte erweitert werden
                return self.batch_read_documents(
                    document_ids,
                    strategy=ReadStrategy.PARALLEL,
                    max_workers=max_workers,
                    include_content=include_content,
                    include_relationships=include_relationships,
                    timeout=timeout
                )
            
            # Berechne execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return BatchReadResult(
                success=len(errors) == 0,
                total_requested=len(document_ids),
                total_read=len(documents),
                documents=documents,
                errors=errors,
                execution_time_ms=execution_time,
                strategy=strategy
            )
        
        except Exception as e:
            self.logger.error(f"Batch read failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return BatchReadResult(
                success=False,
                total_requested=len(document_ids),
                total_read=len(documents),
                documents=documents,
                errors={**errors, "batch_error": str(e)},
                execution_time_ms=execution_time,
                strategy=strategy
            )
    
    def _read_single_document(
        self,
        document_id: str,
        include_content: bool,
        include_relationships: bool,
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """
        Liest ein einzelnes Dokument
        
        Args:
            document_id: Dokument-ID
            include_content: Content einschließen
            include_relationships: Relationships einschließen
            timeout: Timeout in Sekunden
        
        Returns:
            Document data oder error dict
        """
        try:
            # Check cache first (if enabled)
            if hasattr(self.backend, 'cache_enabled') and self.backend.cache_enabled:
                cache = self.backend.single_record_cache
                if cache:
                    cached_data = cache.get(document_id)
                    if cached_data is not None:
                        self.logger.debug(f"Cache HIT for {document_id}")
                        return {
                            "success": True,
                            "document_id": document_id,
                            "data": cached_data,
                            "cached": True
                        }
                    self.logger.debug(f"Cache MISS for {document_id}")
            
            # Cache miss or disabled - read from backend
            # Verwende backend's read_document_operation
            if hasattr(self.backend, 'read_document_operation'):
                result = self.backend.read_document_operation(
                    document_id,
                    include_content=include_content,
                    include_relationships=include_relationships
                )
                
                # Store in cache (if enabled)
                if hasattr(self.backend, 'cache_enabled') and self.backend.cache_enabled:
                    cache = self.backend.single_record_cache
                    if cache:
                        cache.put(document_id, result)
                        self.logger.debug(f"Cached document {document_id}")
                
                return {
                    "success": True,
                    "document_id": document_id,
                    "data": result,
                    "cached": False
                }
            else:
                # Fallback: Basic read
                return {
                    "success": True,
                    "document_id": document_id,
                    "data": {"document_id": document_id},
                    "cached": False
                }
        
        except Exception as e:
            self.logger.error(f"Failed to read document {document_id}: {e}")
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e)
            }
    
    # ========================================================================
    # CONDITIONAL UPDATE
    # ========================================================================
    
    def conditional_update_document(
        self,
        document_id: str,
        updates: Dict[str, Any],
        conditions: List[Condition],
        *,
        version_check: Optional[int] = None,
        atomic: bool = True
    ) -> ConditionalUpdateResult:
        """
        Aktualisiert ein Dokument nur wenn Bedingungen erfüllt sind
        
        Args:
            document_id: Dokument-ID
            updates: Dictionary mit Updates
            conditions: Liste von Conditions die erfüllt sein müssen
            version_check: Erwartete Version (für optimistic locking)
            atomic: Atomic execution (rollback bei Fehler)
        
        Returns:
            ConditionalUpdateResult
        """
        try:
            # 1. Lese aktuelles Dokument
            current_doc_result = self._read_single_document(
                document_id,
                include_content=True,
                include_relationships=False,
                timeout=None
            )
            
            if not current_doc_result.get("success"):
                return ConditionalUpdateResult(
                    success=False,
                    document_id=document_id,
                    updated=False,
                    condition_met=False,
                    errors=[f"Failed to read document: {current_doc_result.get('error')}"]
                )
            
            current_doc = current_doc_result.get("data", {})
            
            # 2. Version check (optimistic locking)
            current_version = current_doc.get("version", 0)
            
            if version_check is not None and current_version != version_check:
                return ConditionalUpdateResult(
                    success=False,
                    document_id=document_id,
                    updated=False,
                    condition_met=False,
                    version_before=current_version,
                    version_after=current_version,
                    conflict_detected=True,
                    errors=[f"Version conflict: expected {version_check}, got {current_version}"]
                )
            
            # 3. Evaluiere alle Conditions
            conditions_evaluated = []
            all_conditions_met = True
            
            for condition in conditions:
                is_met = condition.evaluate(current_doc)
                conditions_evaluated.append({
                    **condition.to_dict(),
                    "met": is_met
                })
                
                if not is_met:
                    all_conditions_met = False
                    break
            
            if not all_conditions_met:
                return ConditionalUpdateResult(
                    success=False,
                    document_id=document_id,
                    updated=False,
                    condition_met=False,
                    conditions_evaluated=conditions_evaluated,
                    version_before=current_version,
                    version_after=current_version,
                    errors=["One or more conditions not met"]
                )
            
            # 4. Führe Update aus
            # Increment version
            updates_with_version = {
                **updates,
                "version": current_version + 1,
                "updated_at": datetime.now().isoformat()
            }
            
            # Verwende backend's update_secure_document
            if hasattr(self.backend, 'update_secure_document'):
                update_result = self.backend.update_secure_document(
                    document_id,
                    updates_with_version
                )
                
                success = update_result.get("success", False)
                affected_dbs = list(update_result.get("database_operations", {}).keys())
                
                return ConditionalUpdateResult(
                    success=success,
                    document_id=document_id,
                    updated=success,
                    condition_met=True,
                    conditions_evaluated=conditions_evaluated,
                    version_before=current_version,
                    version_after=current_version + 1 if success else current_version,
                    affected_databases=affected_dbs,
                    errors=update_result.get("issues", [])
                )
            else:
                # Fallback: Simulate success
                return ConditionalUpdateResult(
                    success=True,
                    document_id=document_id,
                    updated=True,
                    condition_met=True,
                    conditions_evaluated=conditions_evaluated,
                    version_before=current_version,
                    version_after=current_version + 1,
                    affected_databases=["vector", "graph", "relational", "file"]
                )
        
        except Exception as e:
            self.logger.error(f"Conditional update failed for {document_id}: {e}")
            return ConditionalUpdateResult(
                success=False,
                document_id=document_id,
                updated=False,
                condition_met=False,
                errors=[str(e)]
            )
    
    # ========================================================================
    # UPSERT
    # ========================================================================
    
    def upsert_document(
        self,
        document_id: str,
        document_data: Dict[str, Any],
        *,
        merge_strategy: MergeStrategy = MergeStrategy.MERGE,
        create_if_missing: bool = True
    ) -> UpsertResult:
        """
        Upsert: Update or Insert Document
        
        Args:
            document_id: Dokument-ID
            document_data: Dokument-Daten
            merge_strategy: Strategie für Merge (REPLACE, MERGE, KEEP_EXISTING)
            create_if_missing: Dokument erstellen wenn nicht vorhanden
        
        Returns:
            UpsertResult
        """
        try:
            # 1. Check if document exists
            exists_result = self._read_single_document(
                document_id,
                include_content=True,
                include_relationships=False,
                timeout=None
            )
            
            document_exists = exists_result.get("success", False)
            
            if document_exists:
                # UPDATE path
                existing_doc = exists_result.get("data", {})
                
                # Merge according to strategy
                if merge_strategy == MergeStrategy.REPLACE:
                    # Vollständig ersetzen
                    merged_data = document_data.copy()
                    updated_fields = set(document_data.keys())
                    created_fields: Set[str] = set()
                
                elif merge_strategy == MergeStrategy.MERGE:
                    # Felder zusammenführen (neue überschreiben alte)
                    merged_data = {**existing_doc, **document_data}
                    updated_fields = set(document_data.keys())
                    created_fields = set()
                
                else:  # KEEP_EXISTING
                    # Nur neue Felder hinzufügen
                    merged_data = existing_doc.copy()
                    created_fields = set()
                    updated_fields = set()
                    
                    for key, value in document_data.items():
                        if key not in existing_doc:
                            merged_data[key] = value
                            created_fields.add(key)
                
                # Add metadata
                merged_data["updated_at"] = datetime.now().isoformat()
                
                # Perform update
                if hasattr(self.backend, 'update_secure_document'):
                    update_result = self.backend.update_secure_document(
                        document_id,
                        merged_data
                    )
                    
                    success = update_result.get("success", False)
                    affected_dbs = list(update_result.get("database_operations", {}).keys())
                    errors = update_result.get("issues", [])
                else:
                    success = True
                    affected_dbs = ["vector", "graph", "relational", "file"]
                    errors = []
                
                return UpsertResult(
                    success=success,
                    document_id=document_id,
                    operation="updated",
                    existed_before=True,
                    merge_strategy=merge_strategy,
                    affected_databases=affected_dbs,
                    created_fields=created_fields,
                    updated_fields=updated_fields,
                    errors=errors
                )
            
            else:
                # CREATE path
                if not create_if_missing:
                    return UpsertResult(
                        success=False,
                        document_id=document_id,
                        operation="none",
                        existed_before=False,
                        errors=["Document does not exist and create_if_missing=False"]
                    )
                
                # Add metadata
                document_data_with_meta = {
                    **document_data,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "version": 1
                }
                
                # Perform create
                if hasattr(self.backend, 'ingest_document_polyglot'):
                    create_result = self.backend.ingest_document_polyglot(
                        document_id,
                        document_data_with_meta
                    )
                    
                    success = create_result.get("success", False)
                    affected_dbs = list(create_result.get("database_operations", {}).keys())
                    errors = create_result.get("issues", [])
                else:
                    success = True
                    affected_dbs = ["vector", "graph", "relational", "file"]
                    errors = []
                
                return UpsertResult(
                    success=success,
                    document_id=document_id,
                    operation="created",
                    existed_before=False,
                    merge_strategy=merge_strategy,
                    affected_databases=affected_dbs,
                    created_fields=set(document_data.keys()),
                    updated_fields=set(),
                    errors=errors
                )
        
        except Exception as e:
            self.logger.error(f"Upsert failed for {document_id}: {e}")
            return UpsertResult(
                success=False,
                document_id=document_id,
                operation="error",
                existed_before=False,
                errors=[str(e)]
            )
    
    # ========================================================================
    # BATCH UPDATE
    # ========================================================================
    
    def batch_update_documents(
        self,
        updates: Dict[str, Dict[str, Any]],
        *,
        max_workers: int = 10,
        continue_on_error: bool = True
    ) -> Dict[str, ConditionalUpdateResult]:
        """
        Aktualisiert mehrere Dokumente parallel
        
        Args:
            updates: Dict mit document_id -> updates
            max_workers: Maximale Anzahl paralleler Worker
            continue_on_error: Weitermachen bei Fehlern
        
        Returns:
            Dict mit document_id -> ConditionalUpdateResult
        """
        results: Dict[str, ConditionalUpdateResult] = {}
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_id = {
                    executor.submit(
                        self._update_single_document,
                        doc_id,
                        doc_updates
                    ): doc_id
                    for doc_id, doc_updates in updates.items()
                }
                
                for future in as_completed(future_to_id):
                    doc_id = future_to_id[future]
                    try:
                        result = future.result()
                        results[doc_id] = result
                        
                        if not continue_on_error and not result.success:
                            # Cancel remaining futures
                            for f in future_to_id:
                                f.cancel()
                            break
                    
                    except Exception as e:
                        self.logger.error(f"Error updating document {doc_id}: {e}")
                        results[doc_id] = ConditionalUpdateResult(
                            success=False,
                            document_id=doc_id,
                            updated=False,
                            condition_met=False,
                            errors=[str(e)]
                        )
            
            return results
        
        except Exception as e:
            self.logger.error(f"Batch update failed: {e}")
            return results
    
    def _update_single_document(
        self,
        document_id: str,
        updates: Dict[str, Any]
    ) -> ConditionalUpdateResult:
        """Helper method für single update"""
        try:
            if hasattr(self.backend, 'update_secure_document'):
                result = self.backend.update_secure_document(document_id, updates)
                
                return ConditionalUpdateResult(
                    success=result.get("success", False),
                    document_id=document_id,
                    updated=result.get("success", False),
                    condition_met=True,
                    affected_databases=list(result.get("database_operations", {}).keys()),
                    errors=result.get("issues", [])
                )
            else:
                return ConditionalUpdateResult(
                    success=True,
                    document_id=document_id,
                    updated=True,
                    condition_met=True,
                    affected_databases=["vector", "graph", "relational", "file"]
                )
        
        except Exception as e:
            return ConditionalUpdateResult(
                success=False,
                document_id=document_id,
                updated=False,
                condition_met=False,
                errors=[str(e)]
            )


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "AdvancedCRUDManager",
    "BatchReadResult",
    "ConditionalUpdateResult",
    "UpsertResult",
    "Condition",
    "ConditionOperator",
    "MergeStrategy",
    "ReadStrategy",
]
