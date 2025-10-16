"""
Pydantic Models für das Automation Framework
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    """Typen von automatischen Aktionen"""
    GOLDEN_DATASET_ADD = "golden_dataset_add"
    GAP_RESOLUTION = "gap_resolution" 
    QUALITY_OPTIMIZATION = "quality_optimization"
    MODEL_RETRAINING = "model_retraining"
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"
    PROCESS_OPTIMIZATION = "process_optimization"


class ReviewPriority(str, Enum):
    """Prioritäten für Human Review Items"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewStatus(str, Enum):
    """Status von Review Items"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AutomationConfig(BaseModel):
    """Konfiguration für das Automation System"""
    enabled: bool = True
    
    confidence_thresholds: Dict[str, float] = Field(default={
        "auto_execute": 0.85,
        "human_review": 0.65,
        "human_required": 0.65
    })
    
    scheduling: Dict[str, Any] = Field(default={
        "gap_detection": {
            "frequency": "daily",
            "time": "02:00",
            "auto_fix_enabled": True
        },
        "golden_dataset_expansion": {
            "frequency": "weekly", 
            "day": "sunday",
            "max_additions_per_run": 20
        },
        "quality_monitoring": {
            "frequency": "hourly",
            "threshold_degradation": 0.05
        }
    })
    
    human_review: Dict[str, Any] = Field(default={
        "max_queue_size": 50,
        "escalation_time_hours": 24,
        "notification_channels": ["email"],
        "auto_approve_high_confidence": True
    })
    
    learning: Dict[str, Any] = Field(default={
        "feedback_window_days": 30,
        "threshold_adjustment_rate": 0.02,
        "min_decision_sample_size": 10
    })


class TaskResult(BaseModel):
    """Ergebnis einer automatischen Aufgabe"""
    task_id: str
    task_type: str
    status: Literal["success", "failed", "needs_review", "auto_executed"]
    confidence: float = Field(ge=0.0, le=1.0)
    
    result_data: Dict[str, Any] = Field(default={})
    error_message: Optional[str] = None
    
    execution_time_ms: float
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Human Review Informationen
    needs_human_review: bool = False
    review_reason: Optional[str] = None
    review_priority: ReviewPriority = ReviewPriority.MEDIUM


class ReviewItem(BaseModel):
    """Item in der Human Review Queue"""
    id: str = Field(description="Eindeutige Review ID")
    
    # Basis-Informationen
    action_type: ActionType
    title: str = Field(description="Kurze Beschreibung der vorgeschlagenen Aktion")
    description: str = Field(description="Detaillierte Beschreibung")
    
    # Automatisierungs-Context
    ai_confidence: float = Field(ge=0.0, le=1.0, description="AI Confidence Score")
    proposed_action: Dict[str, Any] = Field(description="Vorgeschlagene Aktion (JSON)")
    
    # Review Management
    priority: ReviewPriority = ReviewPriority.MEDIUM
    status: ReviewStatus = ReviewStatus.PENDING
    
    # Context Daten
    affected_items: List[str] = Field(default=[], description="Betroffene Dokumente/Entitäten")
    risk_assessment: Dict[str, Any] = Field(default={}, description="Risikobewertung")
    potential_impact: str = Field(description="Erwartete Auswirkung")
    
    # Zeitstempel
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    
    # Review Ergebnis
    reviewer_id: Optional[str] = None
    reviewer_comment: Optional[str] = None


class ReviewDecision(BaseModel):
    """Entscheidung eines Human Reviewers"""
    approved: bool
    confidence_boost: Optional[float] = Field(
        ge=-0.2, le=0.2, 
        description="Anpassung der Confidence (-0.2 bis +0.2)"
    )
    reason: Optional[str] = Field(description="Begründung für die Entscheidung")
    reviewer_id: str
    additional_notes: Optional[str] = None


class ConfidenceAdjustment(BaseModel):
    """Anpassung der Confidence-Schwellwerte"""
    action_type: ActionType
    old_threshold: float
    new_threshold: float
    adjustment_reason: str
    sample_size: int
    success_rate: float
    adjusted_at: datetime = Field(default_factory=datetime.now)


class AutomationMetrics(BaseModel):
    """Metriken für das Automation System"""
    total_tasks_executed: int = 0
    auto_executed_tasks: int = 0
    human_reviewed_tasks: int = 0
    
    # Success Rates
    auto_execution_success_rate: float = 0.0
    human_approval_rate: float = 0.0
    
    # Queue Statistics
    current_queue_size: int = 0
    average_review_time_hours: float = 0.0
    
    # Learning Statistics
    confidence_adjustments_count: int = 0
    last_learning_cycle: Optional[datetime] = None
    
    # Performance
    avg_task_execution_time_ms: float = 0.0
    system_load_percentage: float = 0.0
    
    updated_at: datetime = Field(default_factory=datetime.now)


class ScheduledTask(BaseModel):
    """Geplante Aufgabe"""
    id: str
    name: str
    task_type: str
    
    # Scheduling
    cron_expression: str
    next_run: datetime
    last_run: Optional[datetime] = None
    
    # Configuration
    enabled: bool = True
    max_retries: int = 3
    retry_delay_minutes: int = 5
    
    # Context
    parameters: Dict[str, Any] = Field(default={})
    
    # Statistics
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)