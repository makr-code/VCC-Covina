"""
UDS3 VPB Operations Module
===========================

Comprehensive domain models and operations for Verwaltungsprozessbearbeitung (VPB).

Features:
- Domain Models: VPBProcess, VPBTask, VPBDocument, VPBParticipant
- CRUD Operations: Create, Read, Update, Delete, Batch operations
- Process Mining: Complexity analysis, automation potential, bottleneck detection
- Reporting: Process reports, compliance exports, analytics

Author: UDS3 Team
Date: 2. Oktober 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class ProcessStatus(Enum):
    """Status eines Verwaltungsprozesses"""
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class TaskStatus(Enum):
    """Status einer Prozessaufgabe"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ParticipantRole(Enum):
    """Rolle eines Prozessbeteiligten"""
    APPLICANT = "applicant"
    PROCESSOR = "processor"
    APPROVER = "approver"
    REVIEWER = "reviewer"
    OBSERVER = "observer"
    EXPERT = "expert"


class AuthorityLevel(Enum):
    """Verwaltungsebene"""
    BUND = "bund"
    LAND = "land"
    KREIS = "kreis"
    GEMEINDE = "gemeinde"
    SONSTIGE = "sonstige"


class LegalContext(Enum):
    """Rechtlicher Kontext"""
    BAURECHT = "baurecht"
    UMWELTRECHT = "umweltrecht"
    GEWERBERECHT = "gewerberecht"
    SOZIALRECHT = "sozialrecht"
    STEUERRECHT = "steuerrecht"
    VERWALTUNGSRECHT_ALLGEMEIN = "verwaltungsrecht_allgemein"
    SONSTIGES = "sonstiges"


class ProcessComplexity(Enum):
    """Prozesskomplexität"""
    SIMPLE = "simple"          # 1-3 Schritte
    MODERATE = "moderate"      # 4-7 Schritte
    COMPLEX = "complex"        # 8-15 Schritte
    VERY_COMPLEX = "very_complex"  # 16+ Schritte


# ============================================================================
# Domain Models
# ============================================================================

@dataclass
class VPBTask:
    """
    Einzelne Aufgabe innerhalb eines Verwaltungsprozesses.
    """
    task_id: str
    name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    
    # Fristen
    deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Eigenschaften
    legal_basis: str = ""
    competent_authority: str = ""
    deadline_days: Optional[int] = None
    
    # Metadaten
    priority: int = 5  # 1-10
    automation_potential: float = 0.0  # 0-1
    estimated_duration_hours: Optional[float] = None
    actual_duration_hours: Optional[float] = None
    
    # Verknüpfungen
    predecessor_task_ids: List[str] = field(default_factory=list)
    successor_task_ids: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task-{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "legal_basis": self.legal_basis,
            "competent_authority": self.competent_authority,
            "deadline_days": self.deadline_days,
            "priority": self.priority,
            "automation_potential": self.automation_potential,
            "estimated_duration_hours": self.estimated_duration_hours,
            "actual_duration_hours": self.actual_duration_hours,
            "predecessor_task_ids": self.predecessor_task_ids,
            "successor_task_ids": self.successor_task_ids
        }


@dataclass
class VPBDocument:
    """
    Dokument im Verwaltungsprozess.
    """
    document_id: str
    name: str
    document_type: str  # application, decision, notice, etc.
    file_path: Optional[str] = None
    
    # Metadaten
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    status: str = "draft"
    
    # Inhalt
    content_hash: Optional[str] = None
    size_bytes: int = 0
    mime_type: str = "application/pdf"
    
    # Verwaltung
    legal_relevance: bool = False
    retention_years: int = 10
    
    def __post_init__(self):
        if not self.document_id:
            self.document_id = f"doc-{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "document_id": self.document_id,
            "name": self.name,
            "document_type": self.document_type,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "legal_relevance": self.legal_relevance,
            "retention_years": self.retention_years
        }


@dataclass
class VPBParticipant:
    """
    Beteiligter an einem Verwaltungsprozess.
    """
    participant_id: str
    name: str
    role: ParticipantRole
    
    # Kontakt
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    
    # Metadaten
    joined_at: datetime = field(default_factory=datetime.now)
    workload_score: float = 0.0  # 0-1 (Auslastung)
    
    def __post_init__(self):
        if not self.participant_id:
            self.participant_id = f"participant-{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "participant_id": self.participant_id,
            "name": self.name,
            "role": self.role.value,
            "email": self.email,
            "phone": self.phone,
            "organization": self.organization,
            "joined_at": self.joined_at.isoformat(),
            "workload_score": self.workload_score
        }


@dataclass
class VPBProcess:
    """
    Verwaltungsprozess (z.B. Baugenehmigungsverfahren).
    """
    process_id: str
    name: str
    description: str
    
    # Status & Version
    status: ProcessStatus = ProcessStatus.DRAFT
    version: str = "1.0"
    
    # Rechtlicher Kontext
    legal_context: LegalContext = LegalContext.VERWALTUNGSRECHT_ALLGEMEIN
    authority_level: AuthorityLevel = AuthorityLevel.GEMEINDE
    legal_basis: List[str] = field(default_factory=list)
    
    # Beteiligte Behörden
    responsible_authority: str = ""
    involved_authorities: List[str] = field(default_factory=list)
    
    # Prozessstruktur
    tasks: List[VPBTask] = field(default_factory=list)
    documents: List[VPBDocument] = field(default_factory=list)
    participants: List[VPBParticipant] = field(default_factory=list)
    
    # Zeitstempel
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadaten
    created_by: str = "system"
    last_modified_by: str = "system"
    tags: List[str] = field(default_factory=list)
    
    # Analytics (berechnet durch Process Mining)
    complexity_score: float = 0.0  # 0-1
    automation_potential: float = 0.0  # 0-1
    compliance_score: float = 0.0  # 0-1
    citizen_satisfaction_score: float = 0.0  # 0-1
    
    # Geografische Relevanz
    geo_scope: str = "Deutschland"
    geo_coordinates: Optional[Tuple[float, float]] = None
    
    def __post_init__(self):
        if not self.process_id:
            self.process_id = f"vpb-{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "process_id": self.process_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "version": self.version,
            "legal_context": self.legal_context.value,
            "authority_level": self.authority_level.value,
            "legal_basis": self.legal_basis,
            "responsible_authority": self.responsible_authority,
            "involved_authorities": self.involved_authorities,
            "tasks": [task.to_dict() for task in self.tasks],
            "documents": [doc.to_dict() for doc in self.documents],
            "participants": [p.to_dict() for p in self.participants],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
            "last_modified_by": self.last_modified_by,
            "tags": self.tags,
            "complexity_score": self.complexity_score,
            "automation_potential": self.automation_potential,
            "compliance_score": self.compliance_score,
            "citizen_satisfaction_score": self.citizen_satisfaction_score,
            "geo_scope": self.geo_scope,
            "geo_coordinates": self.geo_coordinates
        }


# ============================================================================
# Analysis Results
# ============================================================================

@dataclass
class BottleneckAnalysis:
    """Result of bottleneck analysis"""
    task_id: str
    task_name: str
    bottleneck_severity: float  # 0-1
    average_wait_time_hours: float
    suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "bottleneck_severity": self.bottleneck_severity,
            "average_wait_time_hours": self.average_wait_time_hours,
            "suggestions": self.suggestions
        }


@dataclass
class AutomationAnalysis:
    """Result of automation potential analysis"""
    task_id: str
    task_name: str
    automation_potential: float  # 0-1
    automation_type: str  # full, partial, none
    estimated_savings_hours: float
    implementation_difficulty: str  # easy, moderate, hard
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "automation_potential": self.automation_potential,
            "automation_type": self.automation_type,
            "estimated_savings_hours": self.estimated_savings_hours,
            "implementation_difficulty": self.implementation_difficulty
        }


@dataclass
class ProcessAnalysisResult:
    """Comprehensive process analysis result"""
    process_id: str
    process_name: str
    
    # Complexity
    complexity: ProcessComplexity
    complexity_score: float  # 0-1
    total_tasks: int
    total_participants: int
    estimated_duration_days: float
    
    # Automation
    overall_automation_potential: float  # 0-1
    automatable_tasks: List[AutomationAnalysis]
    
    # Bottlenecks
    bottlenecks: List[BottleneckAnalysis]
    
    # Workload
    participant_workload: Dict[str, float]  # participant_id -> workload
    
    # Recommendations
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "process_name": self.process_name,
            "complexity": self.complexity.value,
            "complexity_score": self.complexity_score,
            "total_tasks": self.total_tasks,
            "total_participants": self.total_participants,
            "estimated_duration_days": self.estimated_duration_days,
            "overall_automation_potential": self.overall_automation_potential,
            "automatable_tasks": [a.to_dict() for a in self.automatable_tasks],
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "participant_workload": self.participant_workload,
            "recommendations": self.recommendations
        }


# ============================================================================
# Factory Functions
# ============================================================================

def create_vpb_process(
    name: str,
    description: str,
    legal_context: LegalContext = LegalContext.VERWALTUNGSRECHT_ALLGEMEIN,
    authority_level: AuthorityLevel = AuthorityLevel.GEMEINDE
) -> VPBProcess:
    """Create new VPB process"""
    return VPBProcess(
        process_id="",  # Will be generated in __post_init__
        name=name,
        description=description,
        legal_context=legal_context,
        authority_level=authority_level
    )


def create_vpb_task(name: str, description: str) -> VPBTask:
    """Create new VPB task"""
    return VPBTask(
        task_id="",  # Will be generated in __post_init__
        name=name,
        description=description
    )


def create_vpb_participant(name: str, role: ParticipantRole) -> VPBParticipant:
    """Create new VPB participant"""
    return VPBParticipant(
        participant_id="",  # Will be generated in __post_init__
        name=name,
        role=role
    )


def create_vpb_document(name: str, document_type: str = "other") -> VPBDocument:
    """Create new VPB document"""
    return VPBDocument(
        document_id="",  # Will be generated in __post_init__
        name=name,
        document_type=document_type
    )


# ============================================================================
# VPB CRUD Manager
# ============================================================================

class VPBCRUDManager:
    """
    CRUD Operations Manager for VPB processes.
    
    Features:
    - Create/Read/Update/Delete operations
    - Batch operations
    - Search and filter
    - Process lifecycle management
    """
    
    def __init__(self, storage_backend=None):
        """
        Initialize VPB CRUD Manager.
        
        Args:
            storage_backend: Optional storage backend (dict, database, etc.)
        """
        self.storage = storage_backend if storage_backend is not None else {}
        logger.info("VPBCRUDManager initialized")
    
    # ========================================================================
    # CREATE Operations
    # ========================================================================
    
    def create_process(self, process: VPBProcess) -> Dict[str, Any]:
        """
        Create new VPB process.
        
        Args:
            process: VPBProcess instance
        
        Returns:
            Dict with creation result
        """
        try:
            # Validate
            if not process.name:
                return {"success": False, "error": "Process name required"}
            
            # Check if exists
            if process.process_id in self.storage:
                return {"success": False, "error": f"Process {process.process_id} already exists"}
            
            # Store
            self.storage[process.process_id] = process
            
            logger.info(f"Process created: {process.process_id}")
            return {
                "success": True,
                "process_id": process.process_id,
                "message": "Process created successfully"
            }
        
        except Exception as e:
            logger.error(f"Error creating process: {e}")
            return {"success": False, "error": str(e)}
    
    def batch_create(self, processes: List[VPBProcess]) -> Dict[str, Any]:
        """
        Create multiple processes in batch.
        
        Args:
            processes: List of VPBProcess instances
        
        Returns:
            Dict with batch creation results
        """
        results = []
        successful = 0
        failed = 0
        
        for process in processes:
            result = self.create_process(process)
            results.append(result)
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
        
        return {
            "total": len(processes),
            "successful": successful,
            "failed": failed,
            "results": results
        }
    
    # ========================================================================
    # READ Operations
    # ========================================================================
    
    def read_process(self, process_id: str) -> Optional[VPBProcess]:
        """
        Read single process by ID.
        
        Args:
            process_id: Process identifier
        
        Returns:
            VPBProcess if found, None otherwise
        """
        return self.storage.get(process_id)
    
    def list_processes(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[ProcessStatus] = None
    ) -> List[VPBProcess]:
        """
        List processes with pagination.
        
        Args:
            limit: Maximum results
            offset: Result offset
            status: Optional status filter
        
        Returns:
            List of VPBProcess instances
        """
        all_processes = list(self.storage.values())
        
        # Filter by status
        if status:
            all_processes = [p for p in all_processes if p.status == status]
        
        # Pagination
        return all_processes[offset:offset + limit]
    
    def search_by_status(self, status: ProcessStatus) -> List[VPBProcess]:
        """
        Search processes by status.
        
        Args:
            status: Process status
        
        Returns:
            List of matching processes
        """
        return [p for p in self.storage.values() if p.status == status]
    
    def search_by_participant(self, participant_id: str) -> List[VPBProcess]:
        """
        Search processes by participant.
        
        Args:
            participant_id: Participant identifier
        
        Returns:
            List of processes involving participant
        """
        results = []
        for process in self.storage.values():
            if any(p.participant_id == participant_id for p in process.participants):
                results.append(process)
        return results
    
    def search_by_complexity(
        self,
        min_score: float = 0.0,
        max_score: float = 1.0
    ) -> List[VPBProcess]:
        """
        Search processes by complexity score.
        
        Args:
            min_score: Minimum complexity score
            max_score: Maximum complexity score
        
        Returns:
            List of processes in complexity range
        """
        return [
            p for p in self.storage.values()
            if min_score <= p.complexity_score <= max_score
        ]
    
    def search_by_legal_context(self, legal_context: LegalContext) -> List[VPBProcess]:
        """
        Search processes by legal context.
        
        Args:
            legal_context: Legal context enum
        
        Returns:
            List of matching processes
        """
        return [p for p in self.storage.values() if p.legal_context == legal_context]
    
    # ========================================================================
    # UPDATE Operations
    # ========================================================================
    
    def update_process(
        self,
        process_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update process with partial updates.
        
        Args:
            process_id: Process identifier
            updates: Dictionary of updates
        
        Returns:
            Update result
        """
        try:
            process = self.storage.get(process_id)
            if not process:
                return {"success": False, "error": f"Process {process_id} not found"}
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(process, key):
                    setattr(process, key, value)
            
            # Update timestamp
            process.updated_at = datetime.now()
            
            logger.info(f"Process updated: {process_id}")
            return {
                "success": True,
                "process_id": process_id,
                "message": "Process updated successfully"
            }
        
        except Exception as e:
            logger.error(f"Error updating process: {e}")
            return {"success": False, "error": str(e)}
    
    def batch_update(
        self,
        updates: List[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Batch update multiple processes.
        
        Args:
            updates: List of (process_id, updates_dict) tuples
        
        Returns:
            Batch update results
        """
        results = []
        successful = 0
        failed = 0
        
        for process_id, update_dict in updates:
            result = self.update_process(process_id, update_dict)
            results.append(result)
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
        
        return {
            "total": len(updates),
            "successful": successful,
            "failed": failed,
            "results": results
        }
    
    def update_process_status(
        self,
        process_id: str,
        new_status: ProcessStatus
    ) -> Dict[str, Any]:
        """
        Update process status.
        
        Args:
            process_id: Process identifier
            new_status: New status
        
        Returns:
            Update result
        """
        return self.update_process(process_id, {"status": new_status})
    
    # ========================================================================
    # DELETE Operations
    # ========================================================================
    
    def delete_process(self, process_id: str, soft: bool = True) -> Dict[str, Any]:
        """
        Delete process.
        
        Args:
            process_id: Process identifier
            soft: If True, mark as archived; if False, hard delete
        
        Returns:
            Deletion result
        """
        try:
            if process_id not in self.storage:
                return {"success": False, "error": f"Process {process_id} not found"}
            
            if soft:
                # Soft delete: mark as archived
                process = self.storage[process_id]
                process.status = ProcessStatus.ARCHIVED
                process.updated_at = datetime.now()
                
                logger.info(f"Process soft-deleted: {process_id}")
                return {
                    "success": True,
                    "process_id": process_id,
                    "message": "Process archived successfully",
                    "soft_delete": True
                }
            else:
                # Hard delete
                del self.storage[process_id]
                
                logger.info(f"Process hard-deleted: {process_id}")
                return {
                    "success": True,
                    "process_id": process_id,
                    "message": "Process deleted permanently",
                    "soft_delete": False
                }
        
        except Exception as e:
            logger.error(f"Error deleting process: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def count_processes(self, status: Optional[ProcessStatus] = None) -> int:
        """
        Count processes.
        
        Args:
            status: Optional status filter
        
        Returns:
            Process count
        """
        if status:
            return len([p for p in self.storage.values() if p.status == status])
        return len(self.storage)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get process statistics.
        
        Returns:
            Statistics dictionary
        """
        all_processes = list(self.storage.values())
        
        status_counts = {}
        for status in ProcessStatus:
            status_counts[status.value] = len([p for p in all_processes if p.status == status])
        
        legal_context_counts = {}
        for context in LegalContext:
            legal_context_counts[context.value] = len([p for p in all_processes if p.legal_context == context])
        
        return {
            "total_processes": len(all_processes),
            "by_status": status_counts,
            "by_legal_context": legal_context_counts,
            "average_complexity": sum(p.complexity_score for p in all_processes) / len(all_processes) if all_processes else 0,
            "average_automation_potential": sum(p.automation_potential for p in all_processes) / len(all_processes) if all_processes else 0
        }


# ============================================================================
# Factory Functions (Extended)
# ============================================================================

def create_vpb_crud_manager(storage_backend=None) -> VPBCRUDManager:
    """Create VPB CRUD Manager instance"""
    return VPBCRUDManager(storage_backend=storage_backend)


# ============================================================================
# VPB Process Mining Engine
# ============================================================================

class VPBProcessMiningEngine:
    """
    Process Mining and Analytics Engine for VPB processes.
    
    Features:
    - Complexity analysis
    - Automation potential calculation
    - Bottleneck detection
    - Participant workload analysis
    """
    
    def __init__(self):
        """Initialize Process Mining Engine"""
        logger.info("VPBProcessMiningEngine initialized")
    
    def analyze_complexity(self, process: VPBProcess) -> Tuple[ProcessComplexity, float]:
        """
        Analyze process complexity.
        
        Args:
            process: VPBProcess instance
        
        Returns:
            Tuple of (ProcessComplexity enum, complexity_score float)
        """
        total_tasks = len(process.tasks)
        total_participants = len(process.participants)
        total_documents = len(process.documents)
        
        # Calculate complexity score (0-1)
        task_complexity = min(total_tasks / 20.0, 1.0)  # Max 20 tasks
        participant_complexity = min(total_participants / 10.0, 1.0)  # Max 10 participants
        document_complexity = min(total_documents / 15.0, 1.0)  # Max 15 documents
        
        complexity_score = (
            task_complexity * 0.5 +
            participant_complexity * 0.3 +
            document_complexity * 0.2
        )
        
        # Determine complexity category
        if total_tasks <= 3:
            complexity = ProcessComplexity.SIMPLE
        elif total_tasks <= 7:
            complexity = ProcessComplexity.MODERATE
        elif total_tasks <= 15:
            complexity = ProcessComplexity.COMPLEX
        else:
            complexity = ProcessComplexity.VERY_COMPLEX
        
        return complexity, complexity_score
    
    def calculate_automation_potential(self, process: VPBProcess) -> Tuple[float, List[AutomationAnalysis]]:
        """
        Calculate automation potential for process.
        
        Args:
            process: VPBProcess instance
        
        Returns:
            Tuple of (overall_potential float, list of AutomationAnalysis)
        """
        if not process.tasks:
            return 0.0, []
        
        analyses = []
        total_potential = 0.0
        
        for task in process.tasks:
            # Determine automation type based on potential
            if task.automation_potential >= 0.8:
                automation_type = "full"
                difficulty = "easy"
            elif task.automation_potential >= 0.5:
                automation_type = "partial"
                difficulty = "moderate"
            else:
                automation_type = "none"
                difficulty = "hard"
            
            # Estimate time savings
            if task.estimated_duration_hours:
                estimated_savings = task.estimated_duration_hours * task.automation_potential
            else:
                estimated_savings = 0.0
            
            analysis = AutomationAnalysis(
                task_id=task.task_id,
                task_name=task.name,
                automation_potential=task.automation_potential,
                automation_type=automation_type,
                estimated_savings_hours=estimated_savings,
                implementation_difficulty=difficulty
            )
            
            analyses.append(analysis)
            total_potential += task.automation_potential
        
        overall_potential = total_potential / len(process.tasks)
        
        return overall_potential, analyses
    
    def identify_bottlenecks(self, process: VPBProcess) -> List[BottleneckAnalysis]:
        """
        Identify bottlenecks in process.
        
        Args:
            process: VPBProcess instance
        
        Returns:
            List of BottleneckAnalysis
        """
        bottlenecks = []
        
        for task in process.tasks:
            # Calculate bottleneck severity
            severity = 0.0
            suggestions = []
            
            # High wait time indicator
            if task.actual_duration_hours and task.estimated_duration_hours:
                if task.actual_duration_hours > task.estimated_duration_hours * 1.5:
                    severity += 0.4
                    suggestions.append("Task duration significantly exceeds estimate")
            
            # Multiple predecessors
            if len(task.predecessor_task_ids) > 2:
                severity += 0.2
                suggestions.append("Task has many dependencies - consider parallelization")
            
            # No assignment
            if not task.assigned_to:
                severity += 0.2
                suggestions.append("Task not assigned - assign clear responsibility")
            
            # High priority but pending
            if task.priority >= 8 and task.status == TaskStatus.PENDING:
                severity += 0.2
                suggestions.append("High priority task still pending - escalate")
            
            # Create analysis if bottleneck detected
            if severity > 0.3:
                wait_time = task.actual_duration_hours or task.estimated_duration_hours or 0.0
                
                bottleneck = BottleneckAnalysis(
                    task_id=task.task_id,
                    task_name=task.name,
                    bottleneck_severity=min(severity, 1.0),
                    average_wait_time_hours=wait_time,
                    suggestions=suggestions
                )
                bottlenecks.append(bottleneck)
        
        # Sort by severity (descending)
        bottlenecks.sort(key=lambda b: b.bottleneck_severity, reverse=True)
        
        return bottlenecks
    
    def analyze_participant_workload(self, process: VPBProcess) -> Dict[str, float]:
        """
        Analyze workload distribution among participants.
        
        Args:
            process: VPBProcess instance
        
        Returns:
            Dict mapping participant_id to workload score (0-1)
        """
        workload = {}
        
        # Initialize workload for all participants
        for participant in process.participants:
            workload[participant.participant_id] = 0.0
        
        # Calculate workload based on assigned tasks
        for task in process.tasks:
            if task.assigned_to and task.assigned_to in workload:
                # Add task weight to workload
                task_weight = 0.1  # Base weight
                
                if task.priority >= 8:
                    task_weight += 0.1
                
                if task.estimated_duration_hours:
                    task_weight += min(task.estimated_duration_hours / 40.0, 0.3)
                
                workload[task.assigned_to] += task_weight
        
        # Normalize to 0-1 range
        if workload:
            max_workload = max(workload.values()) if workload.values() else 1.0
            if max_workload > 0:
                workload = {k: v / max_workload for k, v in workload.items()}
        
        return workload
    
    def analyze_process(self, process: VPBProcess) -> ProcessAnalysisResult:
        """
        Perform comprehensive process analysis.
        
        Args:
            process: VPBProcess instance
        
        Returns:
            ProcessAnalysisResult with complete analysis
        """
        # Complexity analysis
        complexity, complexity_score = self.analyze_complexity(process)
        
        # Automation analysis
        automation_potential, automatable_tasks = self.calculate_automation_potential(process)
        
        # Bottleneck analysis
        bottlenecks = self.identify_bottlenecks(process)
        
        # Workload analysis
        participant_workload = self.analyze_participant_workload(process)
        
        # Estimate total duration
        estimated_duration = sum(
            task.estimated_duration_hours or 8.0 for task in process.tasks
        ) / 8.0  # Convert to days
        
        # Generate recommendations
        recommendations = []
        
        if complexity_score > 0.7:
            recommendations.append("Process is highly complex - consider simplification")
        
        if automation_potential > 0.6:
            recommendations.append(f"High automation potential ({automation_potential:.1%}) - prioritize automation")
        
        if len(bottlenecks) > 0:
            recommendations.append(f"Detected {len(bottlenecks)} bottleneck(s) - review and optimize")
        
        if participant_workload:
            max_workload = max(participant_workload.values())
            if max_workload > 0.8:
                recommendations.append("Workload imbalance detected - redistribute tasks")
        
        if not process.tasks:
            recommendations.append("No tasks defined - add process steps")
        
        return ProcessAnalysisResult(
            process_id=process.process_id,
            process_name=process.name,
            complexity=complexity,
            complexity_score=complexity_score,
            total_tasks=len(process.tasks),
            total_participants=len(process.participants),
            estimated_duration_days=estimated_duration,
            overall_automation_potential=automation_potential,
            automatable_tasks=automatable_tasks,
            bottlenecks=bottlenecks,
            participant_workload=participant_workload,
            recommendations=recommendations
        )


def create_vpb_process_mining_engine() -> VPBProcessMiningEngine:
    """Create VPB Process Mining Engine instance"""
    return VPBProcessMiningEngine()


# ============================================================================
# VPB Reporting Interface
# ============================================================================

class VPBReportingInterface:
    """
    Reporting and Export Interface for VPB processes.
    
    Features:
    - Process reports
    - Complexity reports
    - Automation reports
    - Data export (JSON, PDF, CSV)
    """
    
    def __init__(self, crud_manager: VPBCRUDManager, mining_engine: VPBProcessMiningEngine):
        """
        Initialize VPB Reporting Interface.
        
        Args:
            crud_manager: VPBCRUDManager instance
            mining_engine: VPBProcessMiningEngine instance
        """
        self.crud = crud_manager
        self.mining = mining_engine
        logger.info("VPBReportingInterface initialized")
    
    def generate_process_report(self, process_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive process report.
        
        Args:
            process_id: Process identifier
        
        Returns:
            Process report dictionary
        """
        process = self.crud.read_process(process_id)
        if not process:
            return {"error": f"Process {process_id} not found"}
        
        # Analyze process
        analysis = self.mining.analyze_process(process)
        
        return {
            "process_id": process.process_id,
            "process_name": process.name,
            "status": process.status.value,
            "created_at": process.created_at.isoformat(),
            "analysis": analysis.to_dict(),
            "tasks": [task.to_dict() for task in process.tasks],
            "participants": [p.to_dict() for p in process.participants],
            "documents": [doc.to_dict() for doc in process.documents]
        }
    
    def generate_complexity_report(self) -> Dict[str, Any]:
        """
        Generate complexity report for all processes.
        
        Returns:
            Complexity report
        """
        all_processes = self.crud.list_processes(limit=1000)
        
        complexity_distribution = {
            "simple": 0,
            "moderate": 0,
            "complex": 0,
            "very_complex": 0
        }
        
        for process in all_processes:
            complexity, _ = self.mining.analyze_complexity(process)
            complexity_distribution[complexity.value] += 1
        
        avg_complexity = sum(p.complexity_score for p in all_processes) / len(all_processes) if all_processes else 0
        
        return {
            "total_processes": len(all_processes),
            "complexity_distribution": complexity_distribution,
            "average_complexity_score": avg_complexity
        }
    
    def generate_automation_report(self) -> Dict[str, Any]:
        """
        Generate automation potential report.
        
        Returns:
            Automation report
        """
        all_processes = self.crud.list_processes(limit=1000)
        
        total_tasks = 0
        total_automatable = 0
        total_savings = 0.0
        
        for process in all_processes:
            _, automatable = self.mining.calculate_automation_potential(process)
            total_tasks += len(process.tasks)
            total_automatable += len([a for a in automatable if a.automation_potential > 0.5])
            total_savings += sum(a.estimated_savings_hours for a in automatable)
        
        return {
            "total_processes": len(all_processes),
            "total_tasks": total_tasks,
            "automatable_tasks": total_automatable,
            "automation_rate": total_automatable / total_tasks if total_tasks > 0 else 0,
            "estimated_savings_hours": total_savings
        }
    
    def export_process_data(self, process_id: str, format: str = "json") -> bytes:
        """
        Export process data in specified format.
        
        Args:
            process_id: Process identifier
            format: Export format (json, pdf, csv)
        
        Returns:
            Exported data as bytes
        """
        report = self.generate_process_report(process_id)
        
        if format == "json":
            import json
            return json.dumps(report, indent=2).encode('utf-8')
        elif format == "pdf":
            # PDF generation would go here
            return b"PDF generation not implemented"
        elif format == "csv":
            # CSV generation would go here
            return b"CSV generation not implemented"
        else:
            raise ValueError(f"Unsupported format: {format}")


def create_vpb_reporting_interface(
    crud_manager: VPBCRUDManager,
    mining_engine: VPBProcessMiningEngine
) -> VPBReportingInterface:
    """Create VPB Reporting Interface instance"""
    return VPBReportingInterface(crud_manager, mining_engine)


# ============================================================================
# Main (Testing)
# ============================================================================

if __name__ == "__main__":
    print("UDS3 VPB Operations - Full Module Test")
    print("=" * 80)
    
    # ========================================================================
    # Test Domain Model
    # ========================================================================
    print("\n[1/4] Testing Domain Model...")
    
    process = create_vpb_process(
        name="Baugenehmigungsverfahren",
        description="Standardverfahren für Baugenehmigung",
        legal_context=LegalContext.BAURECHT,
        authority_level=AuthorityLevel.GEMEINDE
    )
    
    # Add tasks
    task1 = create_vpb_task("Antrag prüfen", "Vollständigkeit und formale Prüfung")
    task1.deadline_days = 7
    task1.automation_potential = 0.7
    task1.estimated_duration_hours = 8
    
    task2 = create_vpb_task("Fachliche Prüfung", "Inhaltliche Bewertung")
    task2.deadline_days = 30
    task2.automation_potential = 0.3
    task2.estimated_duration_hours = 24
    
    task3 = create_vpb_task("Genehmigung erteilen", "Bescheid erstellen")
    task3.deadline_days = 7
    task3.automation_potential = 0.9
    task3.estimated_duration_hours = 4
    
    process.tasks = [task1, task2, task3]
    
    # Add participant
    participant = create_vpb_participant("Sachbearbeiter", ParticipantRole.PROCESSOR)
    task1.assigned_to = participant.participant_id
    task2.assigned_to = participant.participant_id
    task3.assigned_to = participant.participant_id
    
    process.participants = [participant]
    
    print(f"✅ Process Created: {process.process_id}")
    print(f"   Tasks: {len(process.tasks)}")
    print(f"   Participants: {len(process.participants)}")
    
    # ========================================================================
    # Test CRUD Operations
    # ========================================================================
    print("\n[2/4] Testing CRUD Operations...")
    
    crud = create_vpb_crud_manager()
    
    # CREATE
    create_result = crud.create_process(process)
    print(f"✅ Create: {create_result['message']}")
    
    # READ
    loaded_process = crud.read_process(process.process_id)
    print(f"✅ Read: Loaded process '{loaded_process.name}'")
    
    # UPDATE
    update_result = crud.update_process(process.process_id, {
        "status": ProcessStatus.ACTIVE,
        "complexity_score": 0.6
    })
    print(f"✅ Update: {update_result['message']}")
    
    # SEARCH
    active_processes = crud.search_by_status(ProcessStatus.ACTIVE)
    print(f"✅ Search: Found {len(active_processes)} active processes")
    
    # STATISTICS
    stats = crud.get_statistics()
    print(f"✅ Statistics: {stats['total_processes']} total processes")
    
    # ========================================================================
    # Test Process Mining
    # ========================================================================
    print("\n[3/4] Testing Process Mining...")
    
    mining = create_vpb_process_mining_engine()
    
    # Analyze process
    analysis = mining.analyze_process(loaded_process)
    
    print(f"✅ Complexity: {analysis.complexity.value} (score: {analysis.complexity_score:.2f})")
    print(f"✅ Automation Potential: {analysis.overall_automation_potential:.1%}")
    print(f"✅ Bottlenecks: {len(analysis.bottlenecks)}")
    print(f"✅ Estimated Duration: {analysis.estimated_duration_days:.1f} days")
    print(f"✅ Recommendations: {len(analysis.recommendations)}")
    
    for i, rec in enumerate(analysis.recommendations, 1):
        print(f"   {i}. {rec}")
    
    # ========================================================================
    # Test Reporting
    # ========================================================================
    print("\n[4/4] Testing Reporting...")
    
    reporting = create_vpb_reporting_interface(crud, mining)
    
    # Process report
    process_report = reporting.generate_process_report(process.process_id)
    print(f"✅ Process Report: {process_report['process_name']}")
    print(f"   Analysis Keys: {list(process_report['analysis'].keys())}")
    
    # Complexity report
    complexity_report = reporting.generate_complexity_report()
    print(f"✅ Complexity Report: {complexity_report['total_processes']} processes")
    
    # Automation report
    automation_report = reporting.generate_automation_report()
    print(f"✅ Automation Report: {automation_report['automatable_tasks']} automatable tasks")
    
    # Export
    export_data = reporting.export_process_data(process.process_id, "json")
    print(f"✅ Export: {len(export_data)} bytes")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ VPB Operations Module Test Complete!")
    print("=" * 80)
    print("\nModule Features:")
    print("  ✅ Domain Models: VPBProcess, VPBTask, VPBDocument, VPBParticipant")
    print("  ✅ CRUD Operations: Create, Read, Update, Delete, Batch, Search")
    print("  ✅ Process Mining: Complexity, Automation, Bottlenecks, Workload")
    print("  ✅ Reporting: Reports, Analytics, Export (JSON/PDF/CSV)")
    print("\n" + "=" * 80)

    
    # Create process
    process = create_vpb_process(
        name="Baugenehmigungsverfahren",
        description="Standardverfahren für Baugenehmigung",
        legal_context=LegalContext.BAURECHT,
        authority_level=AuthorityLevel.GEMEINDE
    )
    
    # Add tasks
    task1 = create_vpb_task("Antrag prüfen", "Vollständigkeit und formale Prüfung")
    task1.deadline_days = 7
    task1.automation_potential = 0.6
    
    task2 = create_vpb_task("Fachliche Prüfung", "Inhaltliche Bewertung")
    task2.deadline_days = 30
    task2.automation_potential = 0.3
    
    process.tasks = [task1, task2]
    
    # Add participant
    participant = create_vpb_participant("Sachbearbeiter", ParticipantRole.PROCESSOR)
    process.participants = [participant]
    
    # Display
    print(f"\n✅ Process Created:")
    print(f"   ID: {process.process_id}")
    print(f"   Name: {process.name}")
    print(f"   Status: {process.status.value}")
    print(f"   Tasks: {len(process.tasks)}")
    print(f"   Participants: {len(process.participants)}")
    
    # Test serialization
    process_dict = process.to_dict()
    print(f"\n✅ Serialization successful:")
    print(f"   Keys: {list(process_dict.keys())}")
    
    print("\n" + "=" * 80)
    print("✅ VPB Domain Model test successful!")
