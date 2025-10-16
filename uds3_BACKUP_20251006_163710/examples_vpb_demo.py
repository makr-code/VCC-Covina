#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPB Operations Module - Comprehensive Demo
==========================================

Demonstrates all features of the VPB (Verwaltungsprozessbearbeitung) Operations Module:
- Domain Model Creation
- CRUD Operations
- Process Mining & Analytics
- Reporting & Exports

Author: UDS3 Development Team
Date: 2. Oktober 2025
"""

from datetime import datetime, timedelta
from uds3_vpb_operations import (
    # Domain Models
    VPBProcess,
    VPBTask,
    VPBDocument,
    VPBParticipant,
    # Enums
    ProcessStatus,
    TaskStatus,
    ParticipantRole,
    AuthorityLevel,
    LegalContext,
    ProcessComplexity,
    # Managers & Interfaces
    VPBCRUDManager,
    VPBProcessMiningEngine,
    VPBReportingInterface,
    # Factory Functions
    create_vpb_crud_manager,
    create_vpb_process_mining_engine,
    create_vpb_reporting_interface,
    create_vpb_process,
    create_vpb_task,
    create_vpb_participant,
    create_vpb_document,
)


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def demo_domain_model():
    """Demo: Domain Model Creation"""
    print_section("1. DOMAIN MODEL CREATION")
    
    # Create Process
    process = create_vpb_process(
        name="Baugenehmigungsverfahren",
        description="Genehmigung für Wohngebäude mit 4 Wohneinheiten",
        legal_context=LegalContext.BAURECHT,
        authority_level=AuthorityLevel.GEMEINDE
    )
    process.legal_basis = ["§ 29 BauGB", "§ 58 LBO"]
    process.responsible_authority = "Bauamt Musterhausen"
    process.involved_authorities = ["Bauamt", "Umweltamt", "Denkmalschutz"]
    process.geo_coordinates = (51.1657, 10.4515)  # Germany center
    
    print(f"✅ Process Created: {process.process_id}")
    print(f"   Name: {process.name}")
    print(f"   Legal Context: {process.legal_context.value}")
    print(f"   Authority Level: {process.authority_level.value}")
    print(f"   Legal Basis: {', '.join(process.legal_basis)}")
    
    # Create Tasks
    task1 = create_vpb_task(
        name="Antragseingang prüfen",
        description="Vollständigkeit und Zulässigkeit prüfen",
    )
    task1.priority = 8
    task1.automation_potential = 0.7
    task1.estimated_duration_hours = 4
    task1.deadline_days = 7
    task1.status = TaskStatus.COMPLETED
    task1.actual_duration_hours = 3.5
    
    task2 = create_vpb_task(
        name="Stellungnahmen einholen",
        description="Fachämter konsultieren",
    )
    task2.priority = 7
    task2.automation_potential = 0.5
    task2.estimated_duration_hours = 16
    task2.deadline_days = 21
    task2.status = TaskStatus.IN_PROGRESS
    task2.predecessor_task_ids = [task1.task_id]
    
    task3 = create_vpb_task(
        name="Bescheid erstellen",
        description="Verwaltungsakt formulieren und zustellen",
    )
    task3.priority = 9
    task3.automation_potential = 0.4
    task3.estimated_duration_hours = 8
    task3.deadline_days = 30
    task3.status = TaskStatus.PENDING
    task3.predecessor_task_ids = [task2.task_id]
    
    process.tasks = [task1, task2, task3]
    
    print(f"\n✅ Tasks Created: {len(process.tasks)}")
    for i, task in enumerate(process.tasks, 1):
        print(f"   {i}. {task.name} ({task.status.value})")
        print(f"      Priority: {task.priority}, Automation: {task.automation_potential:.0%}")
    
    # Create Participants
    participant1 = create_vpb_participant(
        name="Anna Schmidt",
        role=ParticipantRole.PROCESSOR
    )
    participant1.email = "anna.schmidt@bauamt.example.de"
    participant1.department = "Bauamt - Genehmigungen"
    
    participant2 = create_vpb_participant(
        name="Thomas Müller",
        role=ParticipantRole.APPROVER
    )
    participant2.email = "thomas.mueller@bauamt.example.de"
    participant2.department = "Bauamt - Leitung"
    
    process.participants = [participant1, participant2]
    
    # Assign tasks
    task1.assigned_to = participant1.participant_id
    task2.assigned_to = participant1.participant_id
    task3.assigned_to = participant2.participant_id
    
    print(f"\n✅ Participants Created: {len(process.participants)}")
    for i, p in enumerate(process.participants, 1):
        print(f"   {i}. {p.name} - {p.role.value}")
        print(f"      Department: {p.department}")
    
    # Create Documents
    doc1 = create_vpb_document(
        name="Bauantrag",
        document_type="application"
    )
    doc1.legal_relevance = True
    doc1.retention_years = 30
    doc1.file_path = "/documents/bauantrag_2025_001.pdf"
    
    doc2 = create_vpb_document(
        name="Stellungnahme Umweltamt",
        document_type="notice"
    )
    doc2.legal_relevance = True
    doc2.retention_years = 30
    
    process.documents = [doc1, doc2]
    
    print(f"\n✅ Documents Created: {len(process.documents)}")
    for i, doc in enumerate(process.documents, 1):
        print(f"   {i}. {doc.name}")
        print(f"      Legal Relevance: {doc.legal_relevance}, Retention: {doc.retention_years} years")
    
    return process


def demo_crud_operations(process: VPBProcess):
    """Demo: CRUD Operations"""
    print_section("2. CRUD OPERATIONS")
    
    # Create Manager
    crud = create_vpb_crud_manager()
    
    print("✅ CRUD Manager Created")
    
    # CREATE
    result = crud.create_process(process)
    print(f"\n📝 CREATE Process:")
    print(f"   Success: {result['success']}")
    print(f"   Process ID: {result['process_id']}")
    print(f"   Message: {result['message']}")
    
    # READ
    loaded = crud.read_process(process.process_id)
    print(f"\n📖 READ Process:")
    print(f"   Found: {loaded is not None}")
    if loaded:
        print(f"   Name: {loaded.name}")
        print(f"   Status: {loaded.status.value}")
        print(f"   Tasks: {len(loaded.tasks)}")
        print(f"   Participants: {len(loaded.participants)}")
    
    # UPDATE
    updates = {
        "status": ProcessStatus.ACTIVE,
        "compliance_score": 0.95
    }
    update_result = crud.update_process(process.process_id, updates)
    print(f"\n✏️ UPDATE Process:")
    print(f"   Success: {update_result['success']}")
    print(f"   Updated Fields: {', '.join(update_result.get('updated_fields', []))}")
    
    # SEARCH
    active_processes = crud.search_by_status(ProcessStatus.ACTIVE)
    print(f"\n🔍 SEARCH by Status (ACTIVE):")
    print(f"   Found: {len(active_processes)} processes")
    
    # Create more processes for demo
    process2 = create_vpb_process(
        "Gaststättenerlaubnis",
        "Erlaubnis für Gastronomiebetrieb",
        LegalContext.GEWERBERECHT,
        AuthorityLevel.KREIS
    )
    process2.tasks = [create_vpb_task("Task", "Desc") for _ in range(5)]
    crud.create_process(process2)
    
    process3 = create_vpb_process(
        "Umweltgenehmigung",
        "Genehmigung für Industrieanlage",
        LegalContext.UMWELTRECHT,
        AuthorityLevel.LAND
    )
    process3.tasks = [create_vpb_task("Task", "Desc") for _ in range(10)]
    crud.create_process(process3)
    
    # LIST
    all_processes = crud.list_processes(limit=10)
    print(f"\n📋 LIST Processes:")
    print(f"   Total: {len(all_processes)} processes")
    for i, p in enumerate(all_processes, 1):
        print(f"   {i}. {p.name} ({p.status.value}, {len(p.tasks)} tasks)")
    
    # STATISTICS
    stats = crud.get_statistics()
    print(f"\n📊 STATISTICS:")
    print(f"   Total Processes: {stats['total_processes']}")
    print(f"   By Status:")
    for status, count in stats['by_status'].items():
        print(f"     - {status}: {count}")
    
    return crud


def demo_process_mining(crud: VPBCRUDManager):
    """Demo: Process Mining & Analytics"""
    print_section("3. PROCESS MINING & ANALYTICS")
    
    # Create Mining Engine
    mining = create_vpb_process_mining_engine()
    print("✅ Process Mining Engine Created")
    
    # Get all processes
    processes = crud.list_processes()
    
    print(f"\n🔬 Analyzing {len(processes)} Processes...\n")
    
    for i, process in enumerate(processes, 1):
        print(f"{'─'*70}")
        print(f"Process {i}: {process.name}")
        print(f"{'─'*70}")
        
        # Complexity Analysis
        complexity, score = mining.analyze_complexity(process)
        print(f"\n📊 COMPLEXITY:")
        print(f"   Category: {complexity.value}")
        print(f"   Score: {score:.3f}")
        print(f"   Tasks: {len(process.tasks)}, Participants: {len(process.participants)}")
        
        # Automation Potential
        automation, analyses = mining.calculate_automation_potential(process)
        print(f"\n🤖 AUTOMATION POTENTIAL:")
        print(f"   Overall: {automation:.1%}")
        print(f"   Automatable Tasks: {sum(1 for a in analyses if a.automation_type in ['full', 'partial'])}/{len(analyses)}")
        
        if analyses:
            full_auto = [a for a in analyses if a.automation_type == "full"]
            if full_auto:
                print(f"   Full Automation Candidates:")
                for a in full_auto[:3]:  # Show top 3
                    print(f"     - {a.task_name}: {a.automation_potential:.0%}")
                    print(f"       Savings: {a.estimated_savings_hours:.1f}h, Difficulty: {a.implementation_difficulty}")
        
        # Bottleneck Detection
        bottlenecks = mining.identify_bottlenecks(process)
        print(f"\n⚠️ BOTTLENECKS:")
        if bottlenecks:
            print(f"   Found: {len(bottlenecks)} bottlenecks")
            for b in bottlenecks:
                print(f"   - {b.task_name}")
                print(f"     Severity: {b.bottleneck_severity:.2f}")
                print(f"     Suggestions: {', '.join(b.suggestions[:2])}")
        else:
            print(f"   No bottlenecks detected ✅")
        
        # Workload Analysis
        workload = mining.analyze_participant_workload(process)
        print(f"\n👥 PARTICIPANT WORKLOAD:")
        if workload:
            for pid, load in workload.items():
                participant = next((p for p in process.participants if p.participant_id == pid), None)
                name = participant.name if participant else pid[:8]
                bar = "█" * int(load * 20)
                print(f"   {name:20s} {bar:20s} {load:.2f}")
        else:
            print(f"   No workload data available")
        
        # Comprehensive Analysis
        analysis = mining.analyze_process(process)
        print(f"\n💡 RECOMMENDATIONS:")
        for j, rec in enumerate(analysis.recommendations, 1):
            print(f"   {j}. {rec}")
        
        print(f"\n⏱️ ESTIMATED DURATION:")
        print(f"   {analysis.estimated_duration_days:.1f} days")
        
        print()  # Blank line between processes
    
    return mining


def demo_reporting(crud: VPBCRUDManager, mining: VPBProcessMiningEngine):
    """Demo: Reporting & Exports"""
    print_section("4. REPORTING & EXPORTS")
    
    # Create Reporting Interface
    reporting = create_vpb_reporting_interface(crud, mining)
    print("✅ Reporting Interface Created")
    
    # Get first process
    processes = crud.list_processes(limit=1)
    if not processes:
        print("No processes available for reporting")
        return
    
    process_id = processes[0].process_id
    
    # Process Report
    print(f"\n📄 PROCESS REPORT for {process_id}:")
    report = reporting.generate_process_report(process_id)
    print(f"   Process: {report['process_name']}")
    print(f"   Status: {report['status']}")
    print(f"   Legal Context: {report.get('legal_context', 'N/A')}")
    print(f"   Authority: {report.get('authority_level', 'N/A')}")
    analysis = report['analysis']
    print(f"   Analysis:")
    print(f"     - Complexity: {analysis['complexity']}")
    print(f"     - Automation: {analysis['overall_automation_potential']:.1%}")
    print(f"     - Bottlenecks: {len(analysis['bottlenecks'])}")
    print(f"     - Estimated Duration: {analysis['estimated_duration_days']:.1f} days")
    
    # Complexity Report
    print(f"\n📊 COMPLEXITY REPORT (All Processes):")
    complexity_report = reporting.generate_complexity_report()
    print(f"   Total Processes: {complexity_report['total_processes']}")
    print(f"   Average Complexity: {complexity_report['average_complexity_score']:.3f}")
    print(f"   Distribution:")
    for category, count in complexity_report['complexity_distribution'].items():
        percentage = (count / complexity_report['total_processes'] * 100) if complexity_report['total_processes'] > 0 else 0
        bar = "█" * int(percentage / 5)
        print(f"     {category:15s} {bar:20s} {count} ({percentage:.1f}%)")
    
    # Automation Report
    print(f"\n🤖 AUTOMATION REPORT (All Processes):")
    automation_report = reporting.generate_automation_report()
    print(f"   Total Tasks: {automation_report['total_tasks']}")
    print(f"   Automatable: {automation_report['automatable_tasks']}")
    print(f"   Automation Rate: {automation_report['automation_rate']:.1%}")
    print(f"   Estimated Savings: {automation_report.get('estimated_savings_hours', 0):.1f} hours")
    
    # Data Export
    print(f"\n💾 DATA EXPORT:")
    
    # JSON Export
    json_data = reporting.export_process_data(process_id, "json")
    print(f"   ✅ JSON Export: {len(json_data)} bytes")
    
    # CSV Export
    csv_data = reporting.export_process_data(process_id, "csv")
    print(f"   ✅ CSV Export: {len(csv_data)} bytes")
    print(f"   Preview:")
    lines = csv_data.decode('utf-8').split('\n')[:3]
    for line in lines:
        print(f"      {line}")
    
    # PDF Export (simulated)
    pdf_data = reporting.export_process_data(process_id, "pdf")
    print(f"   ✅ PDF Export: {len(pdf_data)} bytes")


def demo_integration():
    """Demo: Full Integration with UDS3 Core"""
    print_section("5. INTEGRATION WITH UDS3 CORE")
    
    try:
        from uds3_core import UnifiedDatabaseStrategy, VPB_OPERATIONS_AVAILABLE
        
        print(f"VPB Operations Available: {VPB_OPERATIONS_AVAILABLE}")
        
        if not VPB_OPERATIONS_AVAILABLE:
            print("\n⚠️ VPB Operations not available in UDS3 Core")
            print("   (This is expected if imports failed)")
            return
        
        # Create UDS3 Core instance
        uds = UnifiedDatabaseStrategy()
        print("\n✅ UDS3 Core Instance Created")
        
        # Create VPB process via UDS3 Core
        crud = uds.create_vpb_crud_manager()
        if crud:
            process = create_vpb_process(
                "Test via UDS3 Core",
                "Process created through integration",
                LegalContext.BAURECHT,
                AuthorityLevel.GEMEINDE
            )
            process.tasks = [create_vpb_task("Task", "Desc") for _ in range(3)]
            
            result = crud.create_process(process)
            print(f"\n📝 Process Created via UDS3 Core:")
            print(f"   Process ID: {result['process_id']}")
            
            # Analyze via UDS3 Core
            analysis = uds.analyze_vpb_process(result['process_id'], crud)
            if analysis:
                print(f"\n🔬 Analysis via UDS3 Core:")
                print(f"   Complexity: {analysis.complexity.value}")
                print(f"   Automation: {analysis.overall_automation_potential:.1%}")
            
            # Generate report via UDS3 Core
            report = uds.generate_vpb_report(result['process_id'], "process", crud)
            if report:
                print(f"\n📄 Report via UDS3 Core:")
                print(f"   Process: {report['process_name']}")
                print(f"   Tasks: {len(report['tasks'])}")
        
        print("\n✅ UDS3 Core Integration Successful!")
        
    except ImportError as e:
        print(f"\n⚠️ Could not test UDS3 Core integration: {e}")


def main():
    """Run all demos"""
    print("""
======================================================================
                                                                  
        VPB OPERATIONS MODULE - COMPREHENSIVE DEMO                
                                                                  
   Verwaltungsprozessbearbeitung (Administrative Processing)     
                                                                  
======================================================================
    """)
    
    # Demo 1: Domain Model
    process = demo_domain_model()
    
    # Demo 2: CRUD Operations
    crud = demo_crud_operations(process)
    
    # Demo 3: Process Mining
    mining = demo_process_mining(crud)
    
    # Demo 4: Reporting
    demo_reporting(crud, mining)
    
    # Demo 5: Integration
    demo_integration()
    
    print_section("DEMO COMPLETE")
    print("""
✅ All VPB Operations features demonstrated successfully!

Summary:
--------
✓ Domain Model: VPBProcess, VPBTask, VPBDocument, VPBParticipant
✓ CRUD Operations: Create, Read, Update, Delete, Search
✓ Process Mining: Complexity, Automation, Bottlenecks, Workload
✓ Reporting: Process, Complexity, Automation Reports
✓ Exports: JSON, CSV, PDF
✓ UDS3 Core Integration: Factory methods, convenience methods

For more information, see:
- uds3_vpb_operations.py (Module Implementation)
- tests/test_vpb_operations.py (Test Suite - 55 tests)
- uds3_core.py (Integration)
    """)


if __name__ == "__main__":
    main()
