"""
UDS3 Saga Compliance & Governance - Demo Script
================================================

Demonstrates all four interfaces:
- SagaComplianceEngine
- SagaMonitoringInterface
- SagaAdminInterface
- SagaReportingInterface

Author: UDS3 Team
Date: 2. Oktober 2025
"""

from uds3_core import UnifiedDatabaseStrategy
from datetime import datetime
import json

def main():
    print("=" * 80)
    print("UDS3 Saga Compliance & Governance - Full Demo")
    print("=" * 80)
    
    # Initialize core
    print("\n1. Initializing UDS3 Core...")
    core = UnifiedDatabaseStrategy()
    
    # Create all interfaces
    print("\n2. Creating Saga Compliance interfaces...")
    compliance = core.create_compliance_engine()
    monitoring = core.create_monitoring_interface()
    admin = core.create_admin_interface()
    reporting = core.create_reporting_interface(compliance, monitoring)
    
    print(f"   ✅ Compliance Engine: {compliance is not None}")
    print(f"   ✅ Monitoring Interface: {monitoring is not None}")
    print(f"   ✅ Admin Interface: {admin is not None}")
    print(f"   ✅ Reporting Interface: {reporting is not None}")
    
    # Test saga ID
    saga_id = "demo-saga-001"
    
    # =========================================================================
    # Demo 1: Compliance Engine
    # =========================================================================
    print("\n" + "=" * 80)
    print("DEMO 1: Compliance Engine")
    print("=" * 80)
    
    # 1.1 Initial compliance check
    print("\n1.1 Initial Compliance Check:")
    report1 = compliance.check_saga_compliance(saga_id)
    print(f"   Saga ID: {report1.saga_id}")
    print(f"   Status: {report1.compliance_status.value}")
    print(f"   Violations: {len(report1.violations)}")
    print(f"   Severity: {report1.severity}")
    
    # 1.2 Trigger timeout violation
    print("\n1.2 Triggering Timeout Violation...")
    compliance.check_timeout_compliance(saga_id, 400000)  # 400 seconds > 300s limit
    
    # 1.3 Check compliance again
    print("\n1.3 Compliance Check After Violation:")
    report2 = compliance.check_saga_compliance(saga_id)
    print(f"   Status: {report2.compliance_status.value}")
    print(f"   Violations: {len(report2.violations)}")
    print(f"   Severity: {report2.severity}")
    
    if report2.violations:
        violation = report2.violations[0]
        print(f"\n   Violation Details:")
        print(f"   - Type: {violation.violation_type}")
        print(f"   - Severity: {violation.severity}")
        print(f"   - Description: {violation.description}")
        print(f"   - Remediation: {violation.remediation}")
    
    # 1.4 Test retry policy
    print("\n1.4 Testing Retry Policy:")
    decision1 = compliance.enforce_retry_policy(saga_id, "step-1", 1)
    print(f"   Retry 1/3: {decision1}")
    
    decision2 = compliance.enforce_retry_policy(saga_id, "step-1", 3)
    print(f"   Retry 3/3: {decision2}")
    
    decision3 = compliance.enforce_retry_policy(saga_id, "step-1", 5)
    print(f"   Retry 5/3: {decision3}")
    
    # 1.5 Test authorization
    print("\n1.5 Testing Authorization:")
    auth_result1 = compliance.check_authorization_chain(saga_id, "admin-user")
    print(f"   Authorized user: {auth_result1}")
    
    auth_result2 = compliance.check_authorization_chain(saga_id, "anonymous")
    print(f"   Anonymous user: {auth_result2}")
    
    # 1.6 Apply governance rules
    print("\n1.6 Testing Governance Rules:")
    valid_definition = {
        "saga_id": "saga-001",
        "steps": [
            {"name": "step1", "action": "create"},
            {"name": "step2", "action": "update"}
        ],
        "timeout": 300
    }
    
    violations1 = compliance.apply_governance_rules(valid_definition)
    print(f"   Valid definition violations: {len(violations1)}")
    
    invalid_definition = {
        "steps": [{"action": "create"}]  # Missing name
    }
    
    violations2 = compliance.apply_governance_rules(invalid_definition)
    print(f"   Invalid definition violations: {len(violations2)}")
    for v in violations2:
        print(f"     - {v}")
    
    # 1.7 Audit log
    print("\n1.7 Creating Audit Log:")
    audit_entry = compliance.audit_saga_execution(saga_id)
    print(f"   Audit entry created: {audit_entry['saga_id']}")
    print(f"   Timestamp: {audit_entry['timestamp']}")
    print(f"   Violations: {audit_entry['violations_count']}")
    
    # =========================================================================
    # Demo 2: Monitoring Interface
    # =========================================================================
    print("\n" + "=" * 80)
    print("DEMO 2: Monitoring Interface")
    print("=" * 80)
    
    # 2.1 Setup saga monitoring
    print("\n2.1 Setting Up Saga Monitoring:")
    monitoring.active_sagas[saga_id] = {
        "errors": ["Connection timeout"],
        "warnings": ["Slow response"],
        "completion": 65.0,
        "current_step": "step-3",
        "execution_time_ms": 15000,
        "estimated_remaining_ms": 8000
    }
    print(f"   Saga {saga_id} added to monitoring")
    
    # 2.2 Get health metrics
    print("\n2.2 Checking Saga Health:")
    health = monitoring.get_saga_health(saga_id)
    print(f"   Status: {health.status.value}")
    print(f"   Health Score: {health.health_score:.2f}")
    print(f"   Completion: {health.completion_percentage}%")
    print(f"   Current Step: {health.current_step}")
    print(f"   Errors: {len(health.errors)}")
    print(f"   Warnings: {len(health.warnings)}")
    print(f"   Execution Time: {health.execution_time_ms}ms")
    
    # 2.3 Configure alert
    print("\n2.3 Configuring Alert:")
    alert_id = monitoring.configure_alert(saga_id, "TIMEOUT", 300)
    print(f"   Alert configured: {alert_id}")
    
    # 2.4 Get active sagas
    print("\n2.4 Active Sagas:")
    active_sagas = monitoring.get_active_sagas()
    print(f"   Total active sagas: {len(active_sagas)}")
    for saga in active_sagas:
        print(f"   - {saga.get('saga_id', 'unknown')}")
    
    # =========================================================================
    # Demo 3: Admin Interface
    # =========================================================================
    print("\n" + "=" * 80)
    print("DEMO 3: Admin Interface")
    print("=" * 80)
    
    # 3.1 Pause saga
    print("\n3.1 Pausing Saga:")
    pause_result = admin.pause_saga(saga_id, "Investigating timeout issue", "admin-user")
    print(f"   Pause successful: {pause_result}")
    
    # 3.2 Resume saga
    print("\n3.2 Resuming Saga:")
    resume_result = admin.resume_saga(saga_id, "admin-user")
    print(f"   Resume successful: {resume_result}")
    
    # 3.3 Retry saga
    print("\n3.3 Retrying Saga:")
    retry_result = admin.retry_saga(saga_id, "step-2", "admin-user")
    print(f"   Retry successful: {retry_result}")
    
    # 3.4 Cancel saga
    print("\n3.4 Cancelling Saga:")
    cancel_result = admin.cancel_saga(saga_id, "Unrecoverable error", "admin-user")
    print(f"   Cancel successful: {cancel_result}")
    
    # 3.5 Force compensation
    print("\n3.5 Force Compensation:")
    comp_result = admin.force_compensation(saga_id, "admin-user")
    print(f"   Compensation successful: {comp_result['compensated']}")
    print(f"   Action ID: {comp_result['action_id']}")
    
    # 3.6 Get admin actions
    print("\n3.6 Admin Action History:")
    actions = admin.get_admin_actions(saga_id=saga_id)
    print(f"   Total actions: {len(actions)}")
    for action in actions:
        print(f"   - {action.action_type}: {action.performed_by} at {action.timestamp}")
    
    # =========================================================================
    # Demo 4: Reporting Interface
    # =========================================================================
    print("\n" + "=" * 80)
    print("DEMO 4: Reporting Interface")
    print("=" * 80)
    
    # 4.1 Generate compliance report
    print("\n4.1 Generating Compliance Report:")
    comp_report = reporting.generate_compliance_report(saga_id)
    print(f"   Saga ID: {comp_report.saga_id}")
    print(f"   Status: {comp_report.compliance_status.value}")
    print(f"   Violations: {len(comp_report.violations)}")
    print(f"   Recommendations: {len(comp_report.recommendations)}")
    
    # 4.2 Generate audit trail
    print("\n4.2 Generating Audit Trail:")
    audit_trail = reporting.generate_audit_trail(saga_id)
    print(f"   Saga ID: {audit_trail.saga_id}")
    print(f"   Events: {len(audit_trail.events)}")
    print(f"   Data Changes: {len(audit_trail.data_changes)}")
    print(f"   User Actions: {len(audit_trail.user_actions)}")
    print(f"   Export Timestamp: {audit_trail.export_timestamp}")
    
    # 4.3 Export compliance data
    print("\n4.3 Exporting Compliance Data (JSON):")
    export_data = reporting.export_compliance_data(saga_id, "json")
    print(f"   Export size: {len(export_data)} bytes")
    
    # Parse and display
    parsed_data = json.loads(export_data.decode('utf-8'))
    print(f"   Exported data:")
    print(f"   - Saga ID: {parsed_data['saga_id']}")
    print(f"   - Compliance Status: {parsed_data['compliance_status']}")
    print(f"   - Timestamp: {parsed_data['timestamp']}")
    
    # 4.4 Get saga statistics
    print("\n4.4 Getting Saga Statistics:")
    from datetime import timedelta
    time_range = (datetime.now() - timedelta(days=7), datetime.now())
    stats = reporting.get_saga_statistics(time_range)
    print(f"   Total Sagas: {stats['total_sagas']}")
    print(f"   Successful: {stats['successful_sagas']}")
    print(f"   Failed: {stats['failed_sagas']}")
    
    # =========================================================================
    # Demo 5: Quick Methods via UDS3 Core
    # =========================================================================
    print("\n" + "=" * 80)
    print("DEMO 5: Quick Methods via UDS3 Core")
    print("=" * 80)
    
    # 5.1 Quick compliance check
    print("\n5.1 Quick Compliance Check:")
    quick_report = core.check_saga_compliance(saga_id)
    if quick_report:
        print(f"   Status: {quick_report.compliance_status.value}")
        print(f"   Violations: {len(quick_report.violations)}")
    
    # 5.2 Quick health check
    print("\n5.2 Quick Health Check:")
    quick_health = core.get_saga_health(saga_id)
    if quick_health:
        print(f"   Health Score: {quick_health.health_score:.2f}")
        print(f"   Status: {quick_health.status.value}")
    
    # 5.3 Quick pause
    print("\n5.3 Quick Pause:")
    pause_success = core.pause_saga(saga_id, "Quick maintenance", "admin")
    print(f"   Pause successful: {pause_success}")
    
    # 5.4 Quick audit trail
    print("\n5.4 Quick Audit Trail:")
    quick_audit = core.generate_saga_audit_trail(saga_id)
    if quick_audit:
        print(f"   Events: {len(quick_audit.events)}")
        print(f"   Export Timestamp: {quick_audit.export_timestamp}")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("DEMO COMPLETE - Summary")
    print("=" * 80)
    
    print("\n✅ Compliance Engine Features:")
    print("   - Compliance checks (timeout, retry, authorization)")
    print("   - Policy enforcement")
    print("   - Governance rules validation")
    print("   - Audit logging")
    
    print("\n✅ Monitoring Interface Features:")
    print("   - Real-time saga health monitoring")
    print("   - Health score calculation")
    print("   - Alert configuration")
    print("   - Active saga tracking")
    
    print("\n✅ Admin Interface Features:")
    print("   - Saga control (pause, resume, cancel, retry)")
    print("   - Force compensation (emergency)")
    print("   - Admin action history")
    print("   - User tracking")
    
    print("\n✅ Reporting Interface Features:")
    print("   - Compliance reports")
    print("   - Audit trail generation")
    print("   - GDPR-compliant data export")
    print("   - Saga statistics")
    
    print("\n" + "=" * 80)
    print("All Saga Compliance & Governance features demonstrated successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
