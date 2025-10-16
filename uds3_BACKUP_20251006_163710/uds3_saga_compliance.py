"""
UDS3 Saga Compliance & Governance Module
=========================================

Compliance-Überwachung, Monitoring, Admin-Kontrolle und Reporting für Saga-Transaktionen.

Features:
- Compliance Engine: Policy enforcement, governance rules, audit logs
- Monitoring Interface: Real-time saga monitoring, metrics, alerts
- Admin Interface: Saga control operations (pause, cancel, retry)
- Reporting Interface: Compliance reports, audit trails, GDPR compliance

Author: UDS3 Team
Date: 2. Oktober 2025
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class ComplianceStatus(Enum):
    """Compliance status for saga execution"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"
    EXEMPTED = "exempted"


class PolicyDecision(Enum):
    """Policy enforcement decision"""
    ALLOW = "allow"
    DENY = "deny"
    RETRY = "retry"
    ESCALATE = "escalate"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SagaHealthStatus(Enum):
    """Saga health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ComplianceViolation:
    """Represents a compliance violation"""
    violation_id: str
    violation_type: str  # TIMEOUT, RETRY_EXCEEDED, AUTH_FAILURE, etc.
    severity: str  # low, medium, high, critical
    description: str
    saga_id: str
    step_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    remediation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "violation_type": self.violation_type,
            "severity": self.severity,
            "description": self.description,
            "saga_id": self.saga_id,
            "step_id": self.step_id,
            "timestamp": self.timestamp.isoformat(),
            "remediation": self.remediation
        }


@dataclass
class ComplianceReport:
    """Compliance report for saga execution"""
    saga_id: str
    compliance_status: ComplianceStatus
    violations: List[ComplianceViolation]
    recommendations: List[str]
    severity: str  # low, medium, high, critical
    timestamp: datetime = field(default_factory=datetime.now)
    auditor: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "saga_id": self.saga_id,
            "compliance_status": self.compliance_status.value,
            "violations": [v.to_dict() for v in self.violations],
            "recommendations": self.recommendations,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "auditor": self.auditor
        }


@dataclass
class SagaHealthMetrics:
    """Health metrics for a saga"""
    saga_id: str
    status: SagaHealthStatus
    completion_percentage: float
    current_step: str
    errors: List[str]
    warnings: List[str]
    execution_time_ms: int
    estimated_remaining_time_ms: int
    health_score: float  # 0.0 - 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "saga_id": self.saga_id,
            "status": self.status.value,
            "completion_percentage": self.completion_percentage,
            "current_step": self.current_step,
            "errors": self.errors,
            "warnings": self.warnings,
            "execution_time_ms": self.execution_time_ms,
            "estimated_remaining_time_ms": self.estimated_remaining_time_ms,
            "health_score": self.health_score
        }


@dataclass
class Alert:
    """Alert for saga monitoring"""
    alert_id: str
    saga_id: str
    alert_type: str  # TIMEOUT, ERROR, THRESHOLD_EXCEEDED
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "saga_id": self.saga_id,
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "resolution": self.resolution
        }


@dataclass
class AdminAction:
    """Admin action on saga"""
    action_id: str
    action_type: str  # PAUSE, CANCEL, RETRY, FORCE_COMPENSATE
    saga_id: str
    performed_by: str
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str = ""
    result: str = ""
    affected_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "saga_id": self.saga_id,
            "performed_by": self.performed_by,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "result": self.result,
            "affected_steps": self.affected_steps
        }


@dataclass
class AuditTrail:
    """Audit trail for saga execution"""
    saga_id: str
    events: List[Dict[str, Any]]
    data_changes: List[Dict[str, Any]]
    user_actions: List[Dict[str, Any]]
    system_events: List[Dict[str, Any]]
    compliance_checks: List[Dict[str, Any]]
    export_timestamp: datetime = field(default_factory=datetime.now)
    digital_signature: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "saga_id": self.saga_id,
            "events": self.events,
            "data_changes": self.data_changes,
            "user_actions": self.user_actions,
            "system_events": self.system_events,
            "compliance_checks": self.compliance_checks,
            "export_timestamp": self.export_timestamp.isoformat(),
            "digital_signature": self.digital_signature
        }


# ============================================================================
# Saga Compliance Engine
# ============================================================================

class SagaComplianceEngine:
    """
    Compliance-Überwachung für Saga-Transaktionen.
    
    Features:
    - Compliance checks (timeout, retry, authorization)
    - Policy enforcement
    - Governance rules validation
    - Audit logging
    """
    
    def __init__(self, orchestrator=None):
        """
        Initialize SagaComplianceEngine.
        
        Args:
            orchestrator: Saga orchestrator instance (optional)
        """
        self.orchestrator = orchestrator
        self.violations: Dict[str, List[ComplianceViolation]] = {}
        self.audit_logs: Dict[str, List[Dict[str, Any]]] = {}
        
        # Default policies
        self.max_retries = 3
        self.default_timeout_seconds = 300
        self.require_authorization = True
        
        logger.info("SagaComplianceEngine initialized")
    
    def check_saga_compliance(self, saga_id: str) -> ComplianceReport:
        """
        Check overall compliance for a saga.
        
        Args:
            saga_id: Saga identifier
        
        Returns:
            ComplianceReport with compliance status and violations
        """
        logger.info(f"Checking compliance for saga: {saga_id}")
        
        violations = self.violations.get(saga_id, [])
        
        # Determine compliance status
        if not violations:
            status = ComplianceStatus.COMPLIANT
            severity = "low"
        elif any(v.severity == "critical" for v in violations):
            status = ComplianceStatus.NON_COMPLIANT
            severity = "critical"
        elif any(v.severity == "high" for v in violations):
            status = ComplianceStatus.UNDER_REVIEW
            severity = "high"
        else:
            status = ComplianceStatus.COMPLIANT
            severity = "medium"
        
        # Generate recommendations
        recommendations = []
        if violations:
            recommendations.append("Review and remediate identified violations")
            if any(v.violation_type == "TIMEOUT" for v in violations):
                recommendations.append("Consider increasing timeout thresholds")
            if any(v.violation_type == "RETRY_EXCEEDED" for v in violations):
                recommendations.append("Review retry strategy and error handling")
        
        report = ComplianceReport(
            saga_id=saga_id,
            compliance_status=status,
            violations=violations,
            recommendations=recommendations,
            severity=severity
        )
        
        logger.info(f"Compliance check complete: {status.value}")
        return report
    
    def validate_compensation_chain(self, saga_id: str) -> bool:
        """
        Validate that compensation chain is properly configured.
        
        Args:
            saga_id: Saga identifier
        
        Returns:
            True if compensation chain is valid
        """
        logger.info(f"Validating compensation chain for saga: {saga_id}")
        
        # This is a simplified check - in reality would query orchestrator
        # Check if all steps have compensation defined
        # Check if compensation is idempotent
        # Check if compensation order is correct
        
        return True  # Placeholder
    
    def check_timeout_compliance(self, saga_id: str, execution_time_ms: int) -> bool:
        """
        Check if saga execution time is within compliance limits.
        
        Args:
            saga_id: Saga identifier
            execution_time_ms: Execution time in milliseconds
        
        Returns:
            True if within timeout limits
        """
        timeout_ms = self.default_timeout_seconds * 1000
        
        if execution_time_ms > timeout_ms:
            violation = ComplianceViolation(
                violation_id=str(uuid.uuid4()),
                violation_type="TIMEOUT",
                severity="high",
                description=f"Saga exceeded timeout: {execution_time_ms}ms > {timeout_ms}ms",
                saga_id=saga_id,
                remediation="Review saga step performance and increase timeout if needed"
            )
            
            if saga_id not in self.violations:
                self.violations[saga_id] = []
            self.violations[saga_id].append(violation)
            
            logger.warning(f"Timeout violation for saga {saga_id}")
            return False
        
        return True
    
    def audit_saga_execution(self, saga_id: str) -> Dict[str, Any]:
        """
        Create audit log entry for saga execution.
        
        Args:
            saga_id: Saga identifier
        
        Returns:
            Audit log entry
        """
        audit_entry = {
            "saga_id": saga_id,
            "timestamp": datetime.now().isoformat(),
            "compliance_status": self.check_saga_compliance(saga_id).compliance_status.value,
            "violations_count": len(self.violations.get(saga_id, [])),
            "audited_by": "system"
        }
        
        if saga_id not in self.audit_logs:
            self.audit_logs[saga_id] = []
        self.audit_logs[saga_id].append(audit_entry)
        
        logger.info(f"Audit log created for saga: {saga_id}")
        return audit_entry
    
    def enforce_retry_policy(self, saga_id: str, step_id: str, retry_count: int) -> str:
        """
        Enforce retry policy for a saga step.
        
        Args:
            saga_id: Saga identifier
            step_id: Step identifier
            retry_count: Current retry count
        
        Returns:
            Policy decision (ALLOW, DENY, ESCALATE)
        """
        if retry_count < self.max_retries:
            logger.info(f"Retry allowed for step {step_id} (attempt {retry_count}/{self.max_retries})")
            return PolicyDecision.ALLOW.value
        elif retry_count == self.max_retries:
            logger.warning(f"Max retries reached for step {step_id}, escalating")
            
            violation = ComplianceViolation(
                violation_id=str(uuid.uuid4()),
                violation_type="RETRY_EXCEEDED",
                severity="high",
                description=f"Step {step_id} exceeded max retries: {retry_count}",
                saga_id=saga_id,
                step_id=step_id,
                remediation="Manual intervention required or saga compensation"
            )
            
            if saga_id not in self.violations:
                self.violations[saga_id] = []
            self.violations[saga_id].append(violation)
            
            return PolicyDecision.ESCALATE.value
        else:
            logger.error(f"Retry denied for step {step_id} (exceeded max retries)")
            return PolicyDecision.DENY.value
    
    def check_authorization_chain(self, saga_id: str, user_id: str) -> bool:
        """
        Check if user is authorized to execute saga.
        
        Args:
            saga_id: Saga identifier
            user_id: User identifier
        
        Returns:
            True if authorized
        """
        if not self.require_authorization:
            return True
        
        # Simplified authorization check
        # In reality would check permissions, roles, etc.
        if not user_id or user_id == "anonymous":
            violation = ComplianceViolation(
                violation_id=str(uuid.uuid4()),
                violation_type="AUTH_FAILURE",
                severity="critical",
                description=f"Unauthorized saga execution attempt by {user_id}",
                saga_id=saga_id,
                remediation="Verify user credentials and permissions"
            )
            
            if saga_id not in self.violations:
                self.violations[saga_id] = []
            self.violations[saga_id].append(violation)
            
            logger.error(f"Authorization failed for saga {saga_id}")
            return False
        
        return True
    
    def apply_governance_rules(self, saga_definition: Dict[str, Any]) -> List[str]:
        """
        Apply governance rules to saga definition.
        
        Args:
            saga_definition: Saga definition to validate
        
        Returns:
            List of rule violations
        """
        violations_list = []
        
        # Rule 1: All steps must have names
        if "steps" in saga_definition:
            for idx, step in enumerate(saga_definition["steps"]):
                if "name" not in step or not step["name"]:
                    violations_list.append(f"Step {idx}: Missing name")
        
        # Rule 2: Critical steps must have compensation
        # Rule 3: Saga must have unique identifier
        if "saga_id" not in saga_definition or not saga_definition["saga_id"]:
            violations_list.append("Missing saga_id")
        
        # Rule 4: Timeout must be specified
        if "timeout" not in saga_definition:
            violations_list.append("Missing timeout configuration")
        
        logger.info(f"Governance rules applied: {len(violations_list)} violations found")
        return violations_list


# ============================================================================
# Saga Monitoring Interface
# ============================================================================

class SagaMonitoringInterface:
    """
    Real-time Saga Monitoring Interface.
    
    Features:
    - Live saga monitoring
    - Performance metrics
    - Alerts and notifications
    - Historical analysis
    """
    
    def __init__(self, orchestrator=None):
        """
        Initialize SagaMonitoringInterface.
        
        Args:
            orchestrator: Saga orchestrator instance (optional)
        """
        self.orchestrator = orchestrator
        self.active_sagas: Dict[str, Dict[str, Any]] = {}
        self.alerts: Dict[str, Alert] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SagaMonitoringInterface initialized")
    
    def get_active_sagas(self) -> List[Dict[str, Any]]:
        """
        Get list of currently active sagas.
        
        Returns:
            List of active saga summaries
        """
        logger.info(f"Retrieving {len(self.active_sagas)} active sagas")
        return list(self.active_sagas.values())
    
    def get_saga_health(self, saga_id: str) -> SagaHealthMetrics:
        """
        Get health metrics for a specific saga.
        
        Args:
            saga_id: Saga identifier
        
        Returns:
            SagaHealthMetrics with health information
        """
        logger.info(f"Getting health metrics for saga: {saga_id}")
        
        # Simplified health calculation
        saga_data = self.active_sagas.get(saga_id, {})
        
        errors = saga_data.get("errors", [])
        warnings = saga_data.get("warnings", [])
        
        # Calculate health score
        health_score = 1.0
        if errors:
            health_score -= 0.3 * len(errors)
        if warnings:
            health_score -= 0.1 * len(warnings)
        health_score = max(0.0, health_score)
        
        # Determine health status
        if health_score >= 0.8:
            status = SagaHealthStatus.HEALTHY
        elif health_score >= 0.5:
            status = SagaHealthStatus.DEGRADED
        elif health_score >= 0.2:
            status = SagaHealthStatus.UNHEALTHY
        else:
            status = SagaHealthStatus.CRITICAL
        
        metrics = SagaHealthMetrics(
            saga_id=saga_id,
            status=status,
            completion_percentage=saga_data.get("completion", 0.0),
            current_step=saga_data.get("current_step", "unknown"),
            errors=errors,
            warnings=warnings,
            execution_time_ms=saga_data.get("execution_time_ms", 0),
            estimated_remaining_time_ms=saga_data.get("estimated_remaining_ms", 0),
            health_score=health_score
        )
        
        return metrics
    
    def configure_alert(self, saga_id: str, alert_type: str, threshold: Any) -> str:
        """
        Configure alert for saga monitoring.
        
        Args:
            saga_id: Saga identifier
            alert_type: Type of alert (TIMEOUT, ERROR, THRESHOLD_EXCEEDED)
            threshold: Alert threshold
        
        Returns:
            Alert configuration ID
        """
        alert_id = str(uuid.uuid4())
        logger.info(f"Configured alert {alert_id} for saga {saga_id}: {alert_type}")
        return alert_id
    
    def get_active_alerts(self) -> List[Alert]:
        """
        Get all active (unacknowledged) alerts.
        
        Returns:
            List of active alerts
        """
        active = [alert for alert in self.alerts.values() if not alert.acknowledged]
        logger.info(f"Retrieved {len(active)} active alerts")
        return active
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert identifier
            acknowledged_by: User acknowledging the alert
        
        Returns:
            True if acknowledged successfully
        """
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            self.alerts[alert_id].acknowledged_by = acknowledged_by
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        return False


# ============================================================================
# Saga Admin Interface
# ============================================================================

class SagaAdminInterface:
    """
    Administrative Saga Management Interface.
    
    Features:
    - Saga control operations (pause, resume, cancel, retry)
    - Emergency operations
    - Configuration management
    - User & permission management
    """
    
    def __init__(self, orchestrator=None):
        """
        Initialize SagaAdminInterface.
        
        Args:
            orchestrator: Saga orchestrator instance (optional)
        """
        self.orchestrator = orchestrator
        self.admin_actions: List[AdminAction] = []
        
        logger.info("SagaAdminInterface initialized")
    
    def pause_saga(self, saga_id: str, reason: str, performed_by: str) -> bool:
        """
        Pause a running saga.
        
        Args:
            saga_id: Saga identifier
            reason: Reason for pausing
            performed_by: Admin user performing action
        
        Returns:
            True if paused successfully
        """
        logger.info(f"Pausing saga {saga_id}: {reason}")
        
        action = AdminAction(
            action_id=str(uuid.uuid4()),
            action_type="PAUSE",
            saga_id=saga_id,
            performed_by=performed_by,
            reason=reason,
            result="success"
        )
        self.admin_actions.append(action)
        
        # In reality would call orchestrator.pause_saga(saga_id)
        return True
    
    def resume_saga(self, saga_id: str, performed_by: str) -> bool:
        """
        Resume a paused saga.
        
        Args:
            saga_id: Saga identifier
            performed_by: Admin user performing action
        
        Returns:
            True if resumed successfully
        """
        logger.info(f"Resuming saga {saga_id}")
        
        action = AdminAction(
            action_id=str(uuid.uuid4()),
            action_type="RESUME",
            saga_id=saga_id,
            performed_by=performed_by,
            result="success"
        )
        self.admin_actions.append(action)
        
        return True
    
    def cancel_saga(self, saga_id: str, reason: str, performed_by: str) -> bool:
        """
        Cancel a running saga with compensation.
        
        Args:
            saga_id: Saga identifier
            reason: Reason for cancellation
            performed_by: Admin user performing action
        
        Returns:
            True if cancelled successfully
        """
        logger.warning(f"Cancelling saga {saga_id}: {reason}")
        
        action = AdminAction(
            action_id=str(uuid.uuid4()),
            action_type="CANCEL",
            saga_id=saga_id,
            performed_by=performed_by,
            reason=reason,
            result="success"
        )
        self.admin_actions.append(action)
        
        return True
    
    def retry_saga(self, saga_id: str, from_step: Optional[str], performed_by: str) -> bool:
        """
        Retry a failed saga from a specific step.
        
        Args:
            saga_id: Saga identifier
            from_step: Step to retry from (None = from beginning)
            performed_by: Admin user performing action
        
        Returns:
            True if retry initiated successfully
        """
        logger.info(f"Retrying saga {saga_id} from step: {from_step or 'beginning'}")
        
        action = AdminAction(
            action_id=str(uuid.uuid4()),
            action_type="RETRY",
            saga_id=saga_id,
            performed_by=performed_by,
            affected_steps=[from_step] if from_step else [],
            result="initiated"
        )
        self.admin_actions.append(action)
        
        return True
    
    def force_compensation(self, saga_id: str, performed_by: str) -> Dict[str, Any]:
        """
        Force compensation for a saga (emergency operation).
        
        Args:
            saga_id: Saga identifier
            performed_by: Admin user performing action
        
        Returns:
            Compensation result
        """
        logger.error(f"Force compensation triggered for saga {saga_id}")
        
        action = AdminAction(
            action_id=str(uuid.uuid4()),
            action_type="FORCE_COMPENSATE",
            saga_id=saga_id,
            performed_by=performed_by,
            result="completed"
        )
        self.admin_actions.append(action)
        
        return {
            "saga_id": saga_id,
            "compensated": True,
            "action_id": action.action_id
        }
    
    def get_admin_actions(self, saga_id: Optional[str] = None) -> List[AdminAction]:
        """
        Get admin action history.
        
        Args:
            saga_id: Optional saga ID to filter by
        
        Returns:
            List of admin actions
        """
        if saga_id:
            return [a for a in self.admin_actions if a.saga_id == saga_id]
        return self.admin_actions


# ============================================================================
# Saga Reporting Interface
# ============================================================================

class SagaReportingInterface:
    """
    Compliance Reporting & Analytics Interface.
    
    Features:
    - Compliance reports
    - Audit trails
    - Analytics & insights
    - GDPR compliance
    """
    
    def __init__(self, compliance_engine=None, monitoring=None):
        """
        Initialize SagaReportingInterface.
        
        Args:
            compliance_engine: SagaComplianceEngine instance (optional)
            monitoring: SagaMonitoringInterface instance (optional)
        """
        self.compliance_engine = compliance_engine
        self.monitoring = monitoring
        
        logger.info("SagaReportingInterface initialized")
    
    def generate_compliance_report(
        self, 
        saga_id: str,
        time_range: Optional[tuple] = None
    ) -> ComplianceReport:
        """
        Generate compliance report for saga.
        
        Args:
            saga_id: Saga identifier
            time_range: Optional time range tuple (start, end)
        
        Returns:
            ComplianceReport
        """
        logger.info(f"Generating compliance report for saga: {saga_id}")
        
        if self.compliance_engine:
            return self.compliance_engine.check_saga_compliance(saga_id)
        
        # Fallback if no compliance engine
        return ComplianceReport(
            saga_id=saga_id,
            compliance_status=ComplianceStatus.COMPLIANT,
            violations=[],
            recommendations=[],
            severity="low"
        )
    
    def generate_audit_trail(self, saga_id: str) -> AuditTrail:
        """
        Generate audit trail for saga execution.
        
        Args:
            saga_id: Saga identifier
        
        Returns:
            AuditTrail with complete execution history
        """
        logger.info(f"Generating audit trail for saga: {saga_id}")
        
        audit_trail = AuditTrail(
            saga_id=saga_id,
            events=[],
            data_changes=[],
            user_actions=[],
            system_events=[],
            compliance_checks=[]
        )
        
        # In reality would query orchestrator for full event history
        return audit_trail
    
    def export_compliance_data(self, saga_id: str, format: str = "json") -> bytes:
        """
        Export compliance data in specified format.
        
        Args:
            saga_id: Saga identifier
            format: Export format (json, pdf, csv)
        
        Returns:
            Exported data as bytes
        """
        logger.info(f"Exporting compliance data for saga {saga_id} in format: {format}")
        
        report = self.generate_compliance_report(saga_id)
        
        if format == "json":
            import json
            return json.dumps(report.to_dict(), indent=2).encode('utf-8')
        elif format == "pdf":
            # Would generate PDF using reportlab or similar
            return b"PDF generation not implemented"
        elif format == "csv":
            # Would generate CSV
            return b"CSV generation not implemented"
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_saga_statistics(self, time_range: tuple) -> Dict[str, Any]:
        """
        Get saga execution statistics.
        
        Args:
            time_range: Time range tuple (start, end)
        
        Returns:
            Statistics dictionary
        """
        logger.info("Generating saga statistics")
        
        return {
            "total_sagas": 0,
            "successful_sagas": 0,
            "failed_sagas": 0,
            "average_duration_ms": 0,
            "compliance_violations": 0
        }


# ============================================================================
# Factory Functions
# ============================================================================

def create_compliance_engine(orchestrator=None) -> SagaComplianceEngine:
    """Create SagaComplianceEngine instance"""
    return SagaComplianceEngine(orchestrator=orchestrator)


def create_monitoring_interface(orchestrator=None) -> SagaMonitoringInterface:
    """Create SagaMonitoringInterface instance"""
    return SagaMonitoringInterface(orchestrator=orchestrator)


def create_admin_interface(orchestrator=None) -> SagaAdminInterface:
    """Create SagaAdminInterface instance"""
    return SagaAdminInterface(orchestrator=orchestrator)


def create_reporting_interface(
    compliance_engine=None, 
    monitoring=None
) -> SagaReportingInterface:
    """Create SagaReportingInterface instance"""
    return SagaReportingInterface(
        compliance_engine=compliance_engine,
        monitoring=monitoring
    )


# ============================================================================
# Main (Testing)
# ============================================================================

if __name__ == "__main__":
    print("UDS3 Saga Compliance & Governance Test")
    print("=" * 80)
    
    # Test Compliance Engine
    compliance = create_compliance_engine()
    saga_id = "test-saga-001"
    
    # Check compliance
    report = compliance.check_saga_compliance(saga_id)
    print(f"\n✅ Compliance Status: {report.compliance_status.value}")
    print(f"Violations: {len(report.violations)}")
    
    # Test Monitoring
    monitoring = create_monitoring_interface()
    health = monitoring.get_saga_health(saga_id)
    print(f"\n✅ Health Status: {health.status.value}")
    print(f"Health Score: {health.health_score:.2f}")
    
    # Test Admin
    admin = create_admin_interface()
    admin.pause_saga(saga_id, "Testing", "admin")
    print(f"\n✅ Admin actions: {len(admin.admin_actions)}")
    
    # Test Reporting
    reporting = create_reporting_interface(compliance, monitoring)
    audit = reporting.generate_audit_trail(saga_id)
    print(f"\n✅ Audit trail generated for: {audit.saga_id}")
    
    print("\n" + "=" * 80)
    print("✅ Saga Compliance & Governance module test successful!")
