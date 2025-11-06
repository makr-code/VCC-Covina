"""
Document Binding & Temporal Queries - Example Test

Shows how to:
1. Write a Document node
2. Link it to Process and Step
3. Set validity period (EFFECTIVE_FROM/UNTIL)
4. Query documents by process/step/date

Run: python processes/test_document_binding.py
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from processes.graph.process_graph_writer import ProcessGraphWriter
from processes.domain.models import Process, Step
from uds3.database.database_api_neo4j import Neo4jGraphBackend
import os


async def main():
    # Connect to Neo4j
    neo4j_config = {
        'uri': os.getenv("NEO4J_URI", "bolt://192.168.178.94:7687"),
        'user': os.getenv("NEO4J_USER", "neo4j"),
        'password': os.getenv("NEO4J_PASSWORD", "neo4j"),
    }
    graph = Neo4jGraphBackend(neo4j_config)
    graph.connect()
    
    writer = ProcessGraphWriter(graph)
    
    print("=" * 70)
    print("Document Binding & Temporal Queries - Example")
    print("=" * 70)
    
    # 1. Create a test process
    process = Process(
        id="proc_test_doc_binding_001",
        key="test_process_doc_binding",
        title="Test Process for Document Binding",
        version="1.0",
        domain="Test",
        owner_org="System",
        status="draft",
    )
    await writer.write_process(process)
    print(f"\n✅ Process created: {process.id}")
    
    # 2. Create a test step
    step = Step(
        id="step_test_review_001",
        process_id=process.id,
        order=1,
        key="review_step",
        title="Review Step",
    )
    await writer.write_step(step, process_id=process.id)
    print(f"✅ Step created: {step.id}")
    
    # 3. Create a test document
    document = {
        "id": "doc_test_001",
        "key": "test-doc-2025",
        "title": "Test Document for Binding",
        "type": "guideline",
        "source_uri": "https://example.com/doc/test-doc-2025.pdf",
        "published_at": "2025-10-31T10:00:00",
        "metadata": {"author": "System", "department": "Test"}
    }
    doc_id = await writer.write_document(document)
    print(f"✅ Document created: {doc_id}")
    
    # 4. Link document to process with role and confidence
    await writer.link_document_to_process(
        document_id=doc_id,
        process_id=process.id,
        role="guideline",
        confidence=0.95
    )
    print(f"✅ Document linked to Process (role: guideline, confidence: 0.95)")
    
    # 5. Link document to step
    await writer.link_document_to_step(
        document_id=doc_id,
        step_id=step.id,
        relation="EVIDENCES_STEP"
    )
    print(f"✅ Document linked to Step (EVIDENCES_STEP)")
    
    # 6. Set document validity period
    await writer.link_document_validity(
        document_id=doc_id,
        valid_from="2025-11-01",
        valid_until="2026-10-31"
    )
    print(f"✅ Document validity set: 2025-11-01 to 2026-10-31")
    
    # 7. Query documents by process
    print("\n" + "=" * 70)
    print("Query: Documents for Process")
    print("=" * 70)
    cypher = """
    MATCH (p:Process {id: $pid})<-[r:RELATES_TO_PROCESS]-(doc:Document)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
    RETURN doc.id AS document_id, doc.title AS title, r.role AS role, r.confidence AS confidence,
           coalesce(df.iso, df.date) AS valid_from, coalesce(dt.iso, dt.date) AS valid_until
    """
    docs = graph.execute_query(cypher, {"pid": process.id})
    for doc in docs:
        print(f"  - {doc['title']}")
        print(f"    ID: {doc['document_id']}")
        print(f"    Role: {doc['role']}, Confidence: {doc['confidence']}")
        print(f"    Valid: {doc['valid_from']} to {doc['valid_until']}")
    
    # 8. Query documents by step
    print("\n" + "=" * 70)
    print("Query: Documents for Step")
    print("=" * 70)
    cypher_step = """
    MATCH (s:Step {id: $sid})<-[r]-(doc:Document)
    WHERE type(r) IN ['EVIDENCES_STEP', 'INPUT_OF_STEP', 'OUTPUT_OF_STEP']
    RETURN doc.id AS document_id, doc.title AS title, type(r) AS relation
    """
    step_docs = graph.execute_query(cypher_step, {"sid": step.id})
    for doc in step_docs:
        print(f"  - {doc['title']} ({doc['relation']})")
    
    # 9. Temporal query: documents valid on 2025-12-01
    print("\n" + "=" * 70)
    print("Query: Documents valid on 2025-12-01")
    print("=" * 70)
    cypher_temporal = """
    MATCH (p:Process {id: $pid})<-[:RELATES_TO_PROCESS]-(doc:Document)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
    OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
    WHERE (df.iso IS NULL OR df.iso <= $on_date)
      AND (dt.iso IS NULL OR dt.iso >= $on_date)
    RETURN doc.id AS document_id, doc.title AS title
    """
    valid_docs = graph.execute_query(cypher_temporal, {"pid": process.id, "on_date": "2025-12-01"})
    print(f"Found {len(valid_docs)} document(s) valid on 2025-12-01:")
    for doc in valid_docs:
        print(f"  - {doc['title']}")
    
    # 10. Cleanup (optional - comment out to keep data)
    print("\n" + "=" * 70)
    print("Cleanup (delete test data)")
    print("=" * 70)
    cleanup = """
    MATCH (p:Process {id: $pid})
    OPTIONAL MATCH (p)-[:HAS_STEP]->(s:Step)
    OPTIONAL MATCH (doc:Document {id: $doc_id})
    DETACH DELETE p, s, doc
    """
    graph.execute_query(cleanup, {"pid": process.id, "doc_id": doc_id})
    print("✅ Test data deleted")
    
    print("\n" + "=" * 70)
    print("✅ Document Binding Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
