"""
Test Document Binding & Temporal Queries (Sync Version)
=========================================================

Demonstrates:
1. Creating a document
2. Binding it to multiple processes (multi-process)
3. Binding it to steps (evidences)
4. Setting validity periods (EFFECTIVE_FROM/UNTIL)
5. Querying documents valid on a date / in a range
6. Calendar view (processes + steps + documents on a timeline)

Uses the UPS domain model and ProcessGraphWriter (SYNC version).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from processes.domain.models import Process, Step
from processes.graph.process_graph_writer import ProcessGraphWriter
from uds3.database.database_api_neo4j import Neo4jGraphBackend


def test_document_binding():
    # Connect to Neo4j
    graph = Neo4jGraphBackend({
        "NEO4J_URI": "bolt://192.168.178.94:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "neo4j"
    })
    graph.connect()
    writer = ProcessGraphWriter(graph)
    
    # 1. Create 2 processes
    p1 = Process(
        id="PROC_TEST_001",
        key="test-process-1",
        title="Test Process 1",
        version="1.0",
        domain="testing",
        owner_org="TestOrg",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        extra={}
    )
    p2 = Process(
        id="PROC_TEST_002",
        key="test-process-2",
        title="Test Process 2",
        version="1.0",
        domain="testing",
        owner_org="TestOrg",
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        extra={}
    )
    writer.write_process(p1)
    writer.write_process(p2)
    print("✅ Created 2 processes")
    
    # 2. Create 2 steps
    s1 = Step(
        id="STEP_TEST_001",
        process_id="PROC_TEST_001",
        order=1,
        key="step-1",
        title="Test Step 1",
        description="First test step",
        required=True,
        duration_est=5,
        extra={}
    )
    s2 = Step(
        id="STEP_TEST_002",
        process_id="PROC_TEST_002",
        order=1,
        key="step-2",
        title="Test Step 2",
        description="Second test step",
        required=False,
        duration_est=3,
        extra={}
    )
    writer.write_step(s1, "PROC_TEST_001")
    writer.write_step(s2, "PROC_TEST_002")
    print("✅ Created 2 steps")
    
    # 3. Create a document
    doc = {
        "id": "DOC_TEST_001",
        "key": "test-guideline-2025",
        "title": "Test Guideline 2025",
        "type": "guideline",
        "source_uri": "https://example.com/guideline.pdf",
        "published_at": "2025-10-31T10:00:00",
        "metadata": {"author": "Test System"}
    }
    writer.write_document(doc)
    print("✅ Created document")
    
    # 4. Bind document to both processes (multi-process)
    writer.link_document_to_process("DOC_TEST_001", "PROC_TEST_001", role="guideline", confidence=0.95)
    writer.link_document_to_process("DOC_TEST_001", "PROC_TEST_002", role="evidence", confidence=0.85)
    print("✅ Linked document to 2 processes")
    
    # 5. Bind document to steps
    writer.link_document_to_step("DOC_TEST_001", "STEP_TEST_001", "EVIDENCES_STEP")
    writer.link_document_to_step("DOC_TEST_001", "STEP_TEST_002", "INPUT_OF_STEP")
    print("✅ Linked document to 2 steps")
    
    # 6. Set validity period (1 year)
    writer.link_document_validity("DOC_TEST_001", valid_from="2025-11-01", valid_until="2026-10-31")
    print("✅ Set document validity (2025-11-01 to 2026-10-31)")
    
    # 7. Query 1: Documents for Process 1 valid in Nov 2025
    query1 = """
    MATCH (p:Process {id: $pid})<-[:RELATES_TO_PROCESS]-(doc:Document)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
    WHERE (df.iso IS NULL OR df.iso <= $until)
      AND (dt.iso IS NULL OR dt.iso >= $from)
    RETURN doc.id AS doc_id, doc.title AS title, doc.type AS type,
           df.iso AS valid_from, dt.iso AS valid_until
    """
    result1 = graph.execute_query(query1, {
        "pid": "PROC_TEST_001",
        "from": "2025-11-01",
        "until": "2025-11-30"
    })
    print(f"\n📄 Query 1: Documents valid for PROC_TEST_001 in Nov 2025:")
    for row in result1:
        print(f"  - {row}")
    
    # 8. Query 2: Documents evidencing Step 1 on a specific date
    query2 = """
    MATCH (s:Step {id: $sid})<-[:EVIDENCES_STEP]-(doc:Document)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
    WHERE (df.iso IS NULL OR df.iso <= $on_date)
      AND (dt.iso IS NULL OR dt.iso >= $on_date)
    RETURN doc.id AS doc_id, doc.title AS title
    """
    result2 = graph.execute_query(query2, {
        "sid": "STEP_TEST_001",
        "on_date": "2025-12-15"
    })
    print(f"\n📄 Query 2: Documents evidencing STEP_TEST_001 on 2025-12-15:")
    for row in result2:
        print(f"  - {row}")
    
    # 9. Query 3: Calendar view (all processes, steps, documents in date range)
    query3 = """
    MATCH (p:Process)-[:OCCURS_ON]->(d:Date)
    WHERE d.iso >= $from AND d.iso <= $until
    RETURN 'process' AS type, p.id AS id, p.title AS name, d.iso AS date
    UNION
    MATCH (s:Step)-[:OCCURS_ON]->(d:Date)
    WHERE d.iso >= $from AND d.iso <= $until
    RETURN 'step' AS type, s.id AS id, s.title AS name, d.iso AS date
    UNION
    MATCH (doc:Document)-[:EFFECTIVE_FROM]->(d:Date)
    WHERE d.iso >= $from AND d.iso <= $until
    RETURN 'document' AS type, doc.id AS id, doc.title AS name, d.iso AS date
    ORDER BY date ASC
    """
    result3 = graph.execute_query(query3, {
        "from": "2025-10-01",
        "until": "2025-11-30"
    })
    print(f"\n📅 Query 3: Calendar view (Oct-Nov 2025):")
    for row in result3:
        print(f"  - {row}")
    
    # 10. Cleanup
    cleanup = """
    MATCH (p:Process) WHERE p.id STARTS WITH 'PROC_TEST_' DETACH DELETE p
    MATCH (s:Step) WHERE s.id STARTS WITH 'STEP_TEST_' DETACH DELETE s
    MATCH (d:Document) WHERE d.id STARTS WITH 'DOC_TEST_' DETACH DELETE d
    """
    graph.execute_query(cleanup, {})
    print("\n✅ Cleanup complete")


if __name__ == "__main__":
    test_document_binding()
    print("\n🎉 Document Binding Test Complete!")
