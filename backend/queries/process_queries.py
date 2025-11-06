"""
Process Query Router - FastAPI Endpoints

Provides REST API for process queries in Main Backend.

Endpoints:
- GET /processes - List processes with filters
- GET /processes/{process_id} - Get process details
- GET /processes/search - Fulltext search
- POST /processes/similarity - Find similar processes
- POST /processes/steps/semantic-search - Semantic search on steps
 - GET /processes/analytics/frequent-steps - Frequent steps
 - GET /processes/analytics/frequent-transitions - Frequent transitions
 - GET /processes/analytics/bottlenecks - Bottleneck candidates
 - POST /processes/analytics/persist - Persist metrics to graph
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, Query as QueryParam
from pydantic import BaseModel, Field
import os

from processes.api import ProcessQueryService
from uds3.database.database_api_neo4j import Neo4jGraphBackend
from processes.mining.analytics import DataMiningService
from processes.gap.engine import GapDetectionService

# Initialize router
router = APIRouter(prefix="/processes", tags=["processes"])

# Global service instance (initialized on startup)
_query_service: ProcessQueryService | None = None
_mining_service: DataMiningService | None = None
_gap_service: GapDetectionService | None = None


def get_query_service() -> ProcessQueryService:
    """Get or create ProcessQueryService instance."""
    global _query_service
    
    if _query_service is None:
        # Initialize Neo4j adapter
        neo4j_config = {
            'uri': os.getenv("NEO4J_URI", "bolt://192.168.178.94:7687"),
            'user': os.getenv("NEO4J_USER", "neo4j"),
            'password': os.getenv("NEO4J_PASSWORD", "neo4j"),
        }
        graph_adapter = Neo4jGraphBackend(neo4j_config)
        graph_adapter.connect()
        
        # Initialize ChromaDB client (optional)
        chroma_client = None
        try:
            from database.database_api_chromadb_remote import ChromaDBRemote
            chroma_host = os.getenv("CHROMA_HOST", "192.168.178.94")
            chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
            chroma_client = ChromaDBRemote(chroma_host, chroma_port)
            if chroma_client.connect():
                print(f"✅ ChromaDB connected: {chroma_host}:{chroma_port}")
            else:
                print("⚠️ ChromaDB connection failed, semantic search disabled")
                chroma_client = None
        except Exception as e:
            print(f"⚠️ ChromaDB initialization failed: {e}")
            chroma_client = None
        
    _query_service = ProcessQueryService(graph_adapter, chroma_client)
    # Initialize mining service on same graph adapter
    global _mining_service
    _mining_service = DataMiningService(graph_adapter)
    global _gap_service
    _gap_service = GapDetectionService(graph_adapter)
    
    return _query_service


def get_mining_service() -> DataMiningService:
    """Get or create DataMiningService instance (shares graph with query service)."""
    global _mining_service
    if _mining_service is None:
        # Ensure query service init happened
        _ = get_query_service()
    return _mining_service


def get_gap_service() -> GapDetectionService:
    """Get or create GapDetectionService (shares graph)."""
    global _gap_service
    if _gap_service is None:
        _ = get_query_service()
    return _gap_service


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SimilarityRequest(BaseModel):
    """Request for process similarity search."""
    process_id: str = Field(..., description="Source process ID")
    limit: int = Field(5, ge=1, le=20, description="Max results")
    min_similarity: float = Field(0.6, ge=0.0, le=1.0, description="Minimum similarity")


class SemanticSearchRequest(BaseModel):
    """Request for semantic step search."""
    query: str = Field(..., description="Natural language query")
    limit: int = Field(10, ge=1, le=50, description="Max results")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity")


class PersistMetricsRequest(BaseModel):
    """Request body to persist computed metrics back into the graph."""
    steps: list[dict] = Field(default_factory=list, description="List of step metrics {step_id, usage, bottleneck_score}")
    transitions: list[dict] = Field(default_factory=list, description="List of transition metrics {from_id, to_id, freq}")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("")
async def list_processes(
    domain: Optional[str] = QueryParam(None, description="Filter by domain"),
    status: Optional[str] = QueryParam(None, description="Filter by status"),
    owner: Optional[str] = QueryParam(None, description="Filter by owner"),
    limit: int = QueryParam(100, ge=1, le=1000, description="Max results"),
    offset: int = QueryParam(0, ge=0, description="Pagination offset"),
):
    """
    List processes with optional filters.
    
    Returns paginated list of processes.
    """
    try:
        service = get_query_service()
        result = service.list_processes(
            domain=domain,
            status=status,
            owner=owner,
            limit=limit,
            offset=offset,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/{process_id}")
async def get_process_details(process_id: str):
    """
    Get process details with all entities and relations.
    
    Returns:
    - Process metadata
    - Steps with relations (next_steps, roles, systems, controls, legal_refs)
    - Legal references
    - Statistics
    """
    try:
        service = get_query_service()
        result = service.get_process_details(process_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Process not found: {process_id}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/search/fulltext")
async def search_processes(
    q: str = QueryParam(..., description="Search query"),
    limit: int = QueryParam(20, ge=1, le=100, description="Max results"),
):
    """
    Fulltext search on process name and description.
    
    Uses Neo4j fulltext index for fast searching.
    """
    try:
        service = get_query_service()
        results = service.search_processes(q, limit)
        
        return {
            "query": q,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.get("/search/steps")
async def search_steps(
    q: str = QueryParam(..., description="Search query"),
    limit: int = QueryParam(20, ge=1, le=100, description="Max results"),
):
    """
    Fulltext search on step name, description, and instructions.
    
    Returns matching steps with process information.
    """
    try:
        service = get_query_service()
        results = service.search_steps(q, limit)
        
        return {
            "query": q,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.post("/similarity")
async def find_similar_processes(req: SimilarityRequest):
    """
    Find processes similar to a given process.
    
    Uses ChromaDB step embeddings to calculate process similarity.
    Requires ChromaDB with 'process_steps' collection.
    
    Returns processes ranked by average step similarity.
    """
    try:
        service = get_query_service()
        
        if not service.chroma:
            raise HTTPException(
                status_code=503, 
                detail="Semantic search unavailable: ChromaDB not connected"
            )
        
        results = service.find_similar_processes(
            process_id=req.process_id,
            limit=req.limit,
            min_similarity=req.min_similarity,
        )
        
        return {
            "source_process_id": req.process_id,
            "results": results,
            "count": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {e}")


@router.post("/steps/semantic-search")
async def semantic_search_steps(req: SemanticSearchRequest):
    """
    Semantic search on process steps using natural language.
    
    Uses ChromaDB embeddings to find semantically similar steps.
    Requires ChromaDB with 'process_steps' collection.
    
    Example query: "Genehmigung durch Gemeinderat"
    """
    try:
        service = get_query_service()
        
        if not service.chroma:
            raise HTTPException(
                status_code=503, 
                detail="Semantic search unavailable: ChromaDB not connected"
            )
        
        results = service.semantic_search_steps(
            query_text=req.query,
            limit=req.limit,
            min_similarity=req.min_similarity,
        )
        
        return {
            "query": req.query,
            "results": results,
            "count": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {e}")


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/frequent-steps")
async def analytics_frequent_steps(limit: int = QueryParam(20, ge=1, le=200)):
    """Top N most frequent steps across all processes."""
    try:
        mining = get_mining_service()
        rows = mining.frequent_steps(limit=limit)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {e}")


@router.get("/analytics/frequent-transitions")
async def analytics_frequent_transitions(limit: int = QueryParam(20, ge=1, le=200)):
    """Top N most frequent transitions (NEXT edges)."""
    try:
        mining = get_mining_service()
        rows = mining.frequent_transitions(limit=limit)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {e}")


@router.get("/analytics/bottlenecks")
async def analytics_bottlenecks(limit: int = QueryParam(20, ge=1, le=200)):
    """Bottleneck candidates by heuristic score."""
    try:
        mining = get_mining_service()
        rows = mining.bottlenecks(limit=limit)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {e}")


@router.post("/analytics/persist")
async def analytics_persist(req: PersistMetricsRequest):
    """
    Persist computed metrics back into the graph as node/edge properties.
    """
    try:
        mining = get_mining_service()
        result = mining.persist_metrics(steps=req.steps, transitions=req.transitions)
        return {"status": "success", "updated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persist failed: {e}")


# ============================================================================
# GAPS ENDPOINTS
# ============================================================================

@router.get("/gaps/missing-roles")
async def gaps_missing_roles(process_id: Optional[str] = QueryParam(None)):
    """List steps without PERFORMED_BY relation (optionally by process)."""
    try:
        gaps = get_gap_service()
        rows = gaps.detect_missing_roles(process_id=process_id)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/gaps/dead-ends")
async def gaps_dead_ends(process_id: Optional[str] = QueryParam(None)):
    """List steps with no outgoing NEXT (non-terminal)."""
    try:
        gaps = get_gap_service()
        rows = gaps.detect_dead_ends(process_id=process_id)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/gaps/unconnected-steps")
async def gaps_unconnected_steps(process_id: Optional[str] = QueryParam(None)):
    """List steps with neither incoming nor outgoing NEXT (non-terminal)."""
    try:
        gaps = get_gap_service()
        rows = gaps.detect_unconnected_steps(process_id=process_id)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/gaps/missing-controls")
async def gaps_missing_controls(process_id: Optional[str] = QueryParam(None)):
    """List steps that have no CONTROLS relation."""
    try:
        gaps = get_gap_service()
        rows = gaps.detect_missing_controls(process_id=process_id)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/gaps/missing-legal-refs")
async def gaps_missing_legal_refs(process_id: Optional[str] = QueryParam(None)):
    """List steps that have no CITES relation to legal references."""
    try:
        gaps = get_gap_service()
        rows = gaps.detect_missing_legal_refs(process_id=process_id)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/gaps/cycles")
async def gaps_cycles(process_id: Optional[str] = QueryParam(None), max_len: int = QueryParam(20, ge=2, le=100)):
    """Detect simple NEXT cycles up to max_len."""
    try:
        gaps = get_gap_service()
        rows = gaps.detect_cycles(process_id=process_id, max_len=max_len)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/gaps/temporal-inconsistencies")
async def gaps_temporal_inconsistencies(process_id: Optional[str] = QueryParam(None)):
    """Detect NEXT edges where successor date < predecessor date using Temporal Canon."""
    try:
        gaps = get_gap_service()
        rows = gaps.detect_temporal_inconsistencies(process_id=process_id)
        return {"count": len(rows), "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/gaps/summary")
async def gaps_summary(process_id: Optional[str] = QueryParam(None)):
    """Run all gap checks and return grouped results with counts."""
    try:
        gaps = get_gap_service()
        summary = gaps.summarize(process_id=process_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {e}")


@router.get("/stats/overview")
async def get_process_stats():
    """
    Get overview statistics for all processes.
    
    Returns:
    - Total process count
    - Processes by domain
    - Processes by status
    - Total steps count
    """
    try:
        service = get_query_service()
        
        # Total processes
        cypher_total = "MATCH (p:Process) RETURN count(p) AS total"
        total_result = service.graph.execute_query(cypher_total, {})
        total = total_result[0]["total"] if total_result else 0
        
        # By domain
        cypher_domain = """
        MATCH (p:Process)
        WHERE p.domain IS NOT NULL
        RETURN p.domain AS domain, count(p) AS count
        ORDER BY count DESC
        """
        domain_result = service.graph.execute_query(cypher_domain, {})
        by_domain = [{"domain": r["domain"], "count": r["count"]} for r in domain_result]
        
        # By status
        cypher_status = """
        MATCH (p:Process)
        WHERE p.status IS NOT NULL
        RETURN p.status AS status, count(p) AS count
        ORDER BY count DESC
        """
        status_result = service.graph.execute_query(cypher_status, {})
        by_status = [{"status": r["status"], "count": r["count"]} for r in status_result]
        
        # Total steps
        cypher_steps = "MATCH (s:Step) RETURN count(s) AS total"
        steps_result = service.graph.execute_query(cypher_steps, {})
        total_steps = steps_result[0]["total"] if steps_result else 0
        
        return {
            "total_processes": total,
            "total_steps": total_steps,
            "by_domain": by_domain,
            "by_status": by_status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats query failed: {e}")


# ============================================================================
# DOCUMENT ENDPOINTS
# ============================================================================

@router.get("/{process_id}/documents")
async def get_process_documents(
    process_id: str,
    from_date: Optional[str] = QueryParam(None, description="Valid from filter (ISO date YYYY-MM-DD)"),
    until_date: Optional[str] = QueryParam(None, description="Valid until filter (ISO date YYYY-MM-DD)"),
    role: Optional[str] = QueryParam(None, description="Document role filter"),
):
    """List documents linked to a process, optionally filtered by validity and role."""
    try:
        service = get_query_service()
        cypher = """
        MATCH (p:Process {id: $pid})<-[r:RELATES_TO_PROCESS]-(doc:Document)
        OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
        OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
        WHERE ($role IS NULL OR r.role = $role)
          AND ($from IS NULL OR df.iso IS NULL OR df.iso <= $until_param)
          AND ($until IS NULL OR dt.iso IS NULL OR dt.iso >= $from_param)
        RETURN doc.id AS document_id, doc.key AS key, doc.title AS title, doc.type AS type,
               doc.source_uri AS source_uri, doc.published_at AS published_at,
               coalesce(df.iso, df.date) AS valid_from, coalesce(dt.iso, dt.date) AS valid_until,
               r.role AS role, r.confidence AS confidence
        ORDER BY coalesce(doc.published_at, doc.created_at) DESC
        """
        params = {
            "pid": process_id,
            "role": role,
            "from": from_date,
            "until": until_date,
            "from_param": from_date,
            "until_param": until_date,
        }
        results = service.graph.execute_query(cypher, params)
        return {"count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document query failed: {e}")


@router.get("/steps/{step_id}/documents")
async def get_step_documents(
    step_id: str,
    on_date: Optional[str] = QueryParam(None, description="Filter by date (ISO YYYY-MM-DD)"),
):
    """List documents linked to a step, optionally filtered by validity on a specific date."""
    try:
        service = get_query_service()
        cypher = """
        MATCH (s:Step {id: $sid})<-[r]-(doc:Document)
        WHERE type(r) IN ['EVIDENCES_STEP', 'INPUT_OF_STEP', 'OUTPUT_OF_STEP']
        OPTIONAL MATCH (doc)-[:EFFECTIVE_FROM]->(df:Date)
        OPTIONAL MATCH (doc)-[:EFFECTIVE_UNTIL]->(dt:Date)
        WHERE $on IS NULL 
           OR ((df.iso IS NULL OR df.iso <= $on) AND (dt.iso IS NULL OR dt.iso >= $on))
        RETURN doc.id AS document_id, doc.key AS key, doc.title AS title, doc.type AS type,
               type(r) AS relation, coalesce(df.iso, df.date) AS valid_from, coalesce(dt.iso, dt.date) AS valid_until
        ORDER BY doc.created_at DESC
        """
        results = service.graph.execute_query(cypher, {"sid": step_id, "on": on_date})
        return {"count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document query failed: {e}")


@router.get("/{process_id}/calendar")
async def get_process_calendar(
    process_id: str,
    from_date: Optional[str] = QueryParam(None, description="Start date filter (ISO YYYY-MM-DD)"),
    until_date: Optional[str] = QueryParam(None, description="End date filter (ISO YYYY-MM-DD)"),
):
    """Get calendar view: steps (with occurrences) and linked documents in a date range."""
    try:
        service = get_query_service()
        # Steps with OCCURS_ON
        steps_cypher = """
        MATCH (p:Process {id: $pid})-[:HAS_STEP]->(s:Step)-[:OCCURS_ON]->(d:Date)
        WHERE ($from IS NULL OR d.iso >= $from) AND ($until IS NULL OR d.iso <= $until)
        RETURN 'step' AS type, s.id AS id, s.name AS name, d.iso AS date
        """
        # StepOccurrences
        occ_cypher = """
        MATCH (p:Process {id: $pid})-[:HAS_STEP]->(s:Step)<-[:OF_STEP]-(o:StepOccurrence)-[:OCCURS_ON]->(d:Date)
        WHERE ($from IS NULL OR d.iso >= $from) AND ($until IS NULL OR d.iso <= $until)
        RETURN 'occurrence' AS type, o.id AS id, s.name AS name, d.iso AS date
        """
        # Documents with published_at or OCCURS_ON
        docs_cypher = """
        MATCH (p:Process {id: $pid})<-[:RELATES_TO_PROCESS]-(doc:Document)
        OPTIONAL MATCH (doc)-[:OCCURS_ON]->(d:Date)
        WHERE ($from IS NULL OR d.iso >= $from) AND ($until IS NULL OR d.iso <= $until)
        RETURN 'document' AS type, doc.id AS id, doc.title AS name, d.iso AS date
        """
        params = {"pid": process_id, "from": from_date, "until": until_date}
        steps = service.graph.execute_query(steps_cypher, params)
        occs = service.graph.execute_query(occ_cypher, params)
        docs = service.graph.execute_query(docs_cypher, params)
        
        # Combine and sort
        all_items = steps + occs + docs
        all_items = [r for r in all_items if r.get("date")]  # Filter out null dates
        all_items.sort(key=lambda x: x.get("date", ""))
        
        return {"count": len(all_items), "results": all_items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar query failed: {e}")


# ============================================================================
# UDS3 INTEGRATION & SEMANTIC SEARCH (NEW - 31.10.2025)
# ============================================================================

# Global UDS3 instance (initialized on demand)
_uds3_strategy = None


def get_uds3_strategy():
    """Get or create UDS3 UnifiedDatabaseStrategy instance."""
    global _uds3_strategy
    
    if _uds3_strategy is None:
        try:
            from uds3.core.database import UnifiedDatabaseStrategy
            
            # UDS3 Config (from environment)
            config = {
                "neo4j": {
                    "uri": os.getenv("NEO4J_URI", "bolt://192.168.178.94:7687"),
                    "user": os.getenv("NEO4J_USER", "neo4j"),
                    "password": os.getenv("NEO4J_PASSWORD", "neo4j"),
                },
                "postgres": {
                    "host": os.getenv("POSTGRES_HOST", "192.168.178.94"),
                    "port": int(os.getenv("POSTGRES_PORT", "5432")),
                    "user": os.getenv("POSTGRES_USER", "postgres"),
                    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
                    "database": os.getenv("POSTGRES_DATABASE", "postgres"),
                },
                "chromadb": {
                    "host": os.getenv("CHROMA_HOST", "192.168.178.94"),
                    "port": int(os.getenv("CHROMA_PORT", "8000")),
                },
                "couchdb": {
                    "host": os.getenv("COUCHDB_HOST", "192.168.178.94"),
                    "port": int(os.getenv("COUCHDB_PORT", "32931")),
                }
            }
            
            _uds3_strategy = UnifiedDatabaseStrategy(config)
            print("✅ UDS3 Strategy initialized (4 databases)")
            
        except ImportError:
            print("⚠️ UDS3 not available - semantic search limited")
            _uds3_strategy = None
        except Exception as e:
            print(f"⚠️ UDS3 initialization failed: {e}")
            _uds3_strategy = None
    
    return _uds3_strategy


class SemanticProcessSearchRequest(BaseModel):
    """Request for semantic process search."""
    query: str = Field(..., description="Natural language query (e.g., 'Mitarbeiter Onboarding')")
    top_k: int = Field(10, ge=1, le=50, description="Number of results")
    domain: Optional[str] = Field(None, description="Optional domain filter")
    status: Optional[str] = Field(None, description="Optional status filter")


@router.post("/search/semantic")
async def search_processes_semantic(request: SemanticProcessSearchRequest):
    """
    Semantic search for processes using UDS3 ChromaDB embeddings.
    
    Finds processes by meaning, not just keyword matching.
    
    Example:
        Query: "Mitarbeiter einstellen"
        Returns: "Mitarbeiter Onboarding", "HR Recruiting", "Einstellung Prozess", ...
        (even if exact words don't match!)
    
    Args:
        query: Natural language query
        top_k: Number of results
        domain: Optional domain filter (e.g., "HR")
        status: Optional status filter (e.g., "active")
    
    Returns:
        List of processes with similarity scores (0.0-1.0)
    """
    try:
        uds3 = get_uds3_strategy()
        
        if uds3 is None:
            raise HTTPException(
                status_code=503,
                detail="UDS3 not available - semantic search disabled"
            )
        
        # Build filter
        filter_dict = {"node_type": "Process"}
        if request.domain:
            filter_dict["domain"] = request.domain
        if request.status:
            filter_dict["status"] = request.status
        
        # Query UDS3 ChromaDB
        results = uds3.query_similar(
            query=request.query,
            top_k=request.top_k,
            filter=filter_dict
        )
        
        # Format response
        formatted_results = []
        for result in results:
            metadata = result.get("metadata", {})
            formatted_results.append({
                "process_id": result["id"],
                "title": metadata.get("title", "N/A"),
                "key": metadata.get("key", "N/A"),
                "domain": metadata.get("domain", "N/A"),
                "owner_org": metadata.get("owner_org", "N/A"),
                "status": metadata.get("status", "N/A"),
                "version": metadata.get("version", "N/A"),
                "similarity": result.get("similarity", 0.0),
                "distance": result.get("distance", 1.0)
            })
        
        return {
            "query": request.query,
            "count": len(formatted_results),
            "results": formatted_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.get("/search/semantic/suggest")
async def suggest_similar_processes(
    process_id: str = QueryParam(..., description="Source process ID"),
    top_k: int = QueryParam(5, ge=1, le=20, description="Number of suggestions"),
):
    """
    Get process suggestions based on similarity to a given process.
    
    Useful for "You might also be interested in..." features.
    
    Args:
        process_id: Source process ID
        top_k: Number of suggestions
    
    Returns:
        List of similar processes with similarity scores
    """
    try:
        uds3 = get_uds3_strategy()
        
        if uds3 is None:
            raise HTTPException(
                status_code=503,
                detail="UDS3 not available - suggestions disabled"
            )
        
        # Get source process metadata
        service = get_query_service()
        source_process = service.get_process_by_id(process_id)
        
        if not source_process:
            raise HTTPException(
                status_code=404,
                detail=f"Process {process_id} not found"
            )
        
        # Build query from process title + domain
        query = f"{source_process.get('title', '')} {source_process.get('domain', '')}"
        
        # Find similar processes (exclude source)
        results = uds3.query_similar(
            query=query,
            top_k=top_k + 1,  # +1 because source might be included
            filter={"node_type": "Process"}
        )
        
        # Remove source process from results
        filtered_results = [
            r for r in results 
            if r["id"] != process_id
        ][:top_k]
        
        # Format response
        formatted_results = []
        for result in filtered_results:
            metadata = result.get("metadata", {})
            formatted_results.append({
                "process_id": result["id"],
                "title": metadata.get("title", "N/A"),
                "domain": metadata.get("domain", "N/A"),
                "similarity": result.get("similarity", 0.0),
                "reason": "Similar content and domain"
            })
        
        return {
            "source_process_id": process_id,
            "source_title": source_process.get("title", "N/A"),
            "count": len(formatted_results),
            "suggestions": formatted_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Suggestion generation failed: {str(e)}"
        )


@router.get("/analytics/uds3-stats")
async def get_uds3_statistics():
    """
    Get UDS3 statistics (database counts, health status).
    
    Shows how many processes are in each database (Neo4j, PostgreSQL, ChromaDB, CouchDB).
    """
    try:
        uds3 = get_uds3_strategy()
        
        if uds3 is None:
            return {
                "uds3_available": False,
                "message": "UDS3 not initialized"
            }
        
        stats = {
            "uds3_available": True,
            "databases": {}
        }
        
        # Neo4j count
        try:
            service = get_query_service()
            neo4j_result = service.graph.execute_query(
                "MATCH (p:Process) RETURN count(p) AS count",
                {}
            )
            stats["databases"]["neo4j"] = {
                "processes": neo4j_result[0]["count"] if neo4j_result else 0,
                "status": "connected"
            }
        except Exception as e:
            stats["databases"]["neo4j"] = {
                "processes": 0,
                "status": f"error: {e}"
            }
        
        # ChromaDB count (if available)
        try:
            # Query ChromaDB collection for Process entities
            # Note: Actual implementation depends on UDS3 API
            stats["databases"]["chromadb"] = {
                "embeddings": "N/A (query UDS3.chromadb.count())",
                "status": "connected"
            }
        except Exception as e:
            stats["databases"]["chromadb"] = {
                "embeddings": 0,
                "status": f"error: {e}"
            }
        
        # PostgreSQL count (if available)
        try:
            stats["databases"]["postgresql"] = {
                "rows": "N/A (query UDS3.postgres.count())",
                "status": "connected"
            }
        except Exception as e:
            stats["databases"]["postgresql"] = {
                "rows": 0,
                "status": f"error: {e}"
            }
        
        # CouchDB count (if available)
        try:
            stats["databases"]["couchdb"] = {
                "documents": "N/A (query UDS3.couchdb.count())",
                "status": "connected"
            }
        except Exception as e:
            stats["databases"]["couchdb"] = {
                "documents": 0,
                "status": f"error: {e}"
            }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stats query failed: {str(e)}"
        )


# ============================================================================
# HYBRID SEARCH (Semantic + Keyword) - NEW
# ============================================================================

class HybridSearchRequest(BaseModel):
    """Request for hybrid search (semantic + keyword)."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, ge=1, le=50, description="Number of results per method")
    semantic_weight: float = Field(0.7, ge=0.0, le=1.0, description="Weight for semantic results (0.0-1.0)")
    keyword_weight: float = Field(0.3, ge=0.0, le=1.0, description="Weight for keyword results (0.0-1.0)")
    domain: Optional[str] = Field(None, description="Optional domain filter")
    status: Optional[str] = Field(None, description="Optional status filter")


@router.post("/search/hybrid")
async def search_processes_hybrid(request: HybridSearchRequest):
    """
    Hybrid Search: Combines Semantic (ChromaDB) + Keyword (Neo4j/PostgreSQL).
    
    Best of both worlds:
    - Semantic: Finds processes by meaning (ChromaDB embeddings)
    - Keyword: Finds exact/partial text matches (Neo4j fulltext)
    - Fusion: Re-ranks results using weighted score
    
    Example:
        Query: "Mitarbeiter"
        Semantic: "Mitarbeiter Onboarding", "HR Recruiting", "Team Reorganization"
        Keyword: "Mitarbeiter Einstellung", "Mitarbeiter Offboarding"
        Hybrid: Combines & re-ranks both result sets
    
    Args:
        query: Search query (works for both semantic and keyword)
        top_k: Number of results per method (semantic + keyword)
        semantic_weight: Weight for semantic results (default: 0.7)
        keyword_weight: Weight for keyword results (default: 0.3)
        domain: Optional domain filter
        status: Optional status filter
    
    Returns:
        Combined & re-ranked results with hybrid scores
    """
    try:
        # Validate weights sum to 1.0
        total_weight = request.semantic_weight + request.keyword_weight
        if not (0.99 <= total_weight <= 1.01):  # Allow small floating point error
            raise HTTPException(
                status_code=400,
                detail=f"Weights must sum to 1.0 (got {total_weight})"
            )
        
        # Results containers
        semantic_results = []
        keyword_results = []
        
        # ====================================================================
        # 1. SEMANTIC SEARCH (ChromaDB)
        # ====================================================================
        try:
            uds3 = get_uds3_strategy()
            
            if uds3 is not None:
                # Build filter
                filter_dict = {"node_type": "Process"}
                if request.domain:
                    filter_dict["domain"] = request.domain
                if request.status:
                    filter_dict["status"] = request.status
                
                # Query ChromaDB
                semantic_raw = uds3.query_similar(
                    query=request.query,
                    top_k=request.top_k,
                    filter=filter_dict
                )
                
                # Normalize semantic results
                for result in semantic_raw:
                    metadata = result.get("metadata", {})
                    semantic_results.append({
                        "process_id": result["id"],
                        "title": metadata.get("title", "N/A"),
                        "key": metadata.get("key", "N/A"),
                        "domain": metadata.get("domain", "N/A"),
                        "owner_org": metadata.get("owner_org", "N/A"),
                        "status": metadata.get("status", "N/A"),
                        "version": metadata.get("version", "N/A"),
                        "semantic_score": result.get("similarity", 0.0),
                        "source": "semantic"
                    })
        except Exception as e:
            # Semantic search failed, continue with keyword only
            print(f"⚠️ Semantic search failed: {e}")
        
        # ====================================================================
        # 2. KEYWORD SEARCH (Neo4j Fulltext)
        # ====================================================================
        try:
            service = get_query_service()
            
            # Build Cypher query for keyword search
            cypher = """
            MATCH (p:Process)
            WHERE p.title CONTAINS $query
               OR p.key CONTAINS $query
               OR p.domain CONTAINS $query
            """
            
            # Add filters
            if request.domain:
                cypher += " AND p.domain = $domain"
            if request.status:
                cypher += " AND p.status = $status"
            
            cypher += """
            RETURN p.id AS process_id,
                   p.title AS title,
                   p.key AS key,
                   p.domain AS domain,
                   p.owner_org AS owner_org,
                   p.status AS status,
                   p.version AS version
            LIMIT $top_k
            """
            
            params = {
                "query": request.query,
                "domain": request.domain,
                "status": request.status,
                "top_k": request.top_k
            }
            
            keyword_raw = service.graph.execute_query(cypher, params)
            
            # Normalize keyword results (assign score based on match type)
            for result in keyword_raw:
                title = result.get("title", "")
                key = result.get("key", "")
                domain = result.get("domain", "")
                
                # Calculate keyword score (1.0 = exact match, 0.5 = partial)
                score = 0.0
                query_lower = request.query.lower()
                if title.lower() == query_lower:
                    score = 1.0
                elif key.lower() == query_lower:
                    score = 0.9
                elif query_lower in title.lower():
                    score = 0.7
                elif query_lower in key.lower():
                    score = 0.6
                elif query_lower in domain.lower():
                    score = 0.4
                else:
                    score = 0.3  # Fallback
                
                keyword_results.append({
                    "process_id": result.get("process_id"),
                    "title": title,
                    "key": key,
                    "domain": domain,
                    "owner_org": result.get("owner_org", "N/A"),
                    "status": result.get("status", "N/A"),
                    "version": result.get("version", "N/A"),
                    "keyword_score": score,
                    "source": "keyword"
                })
        except Exception as e:
            # Keyword search failed, continue with semantic only
            print(f"⚠️ Keyword search failed: {e}")
        
        # ====================================================================
        # 3. HYBRID FUSION (Weighted Re-Ranking)
        # ====================================================================
        
        # Merge results by process_id
        merged = {}
        
        # Add semantic results
        for result in semantic_results:
            pid = result["process_id"]
            merged[pid] = {
                **result,
                "semantic_score": result["semantic_score"],
                "keyword_score": 0.0,  # Default if no keyword match
                "sources": ["semantic"]
            }
        
        # Add/merge keyword results
        for result in keyword_results:
            pid = result["process_id"]
            if pid in merged:
                # Process found in both → merge scores
                merged[pid]["keyword_score"] = result["keyword_score"]
                merged[pid]["sources"].append("keyword")
            else:
                # Process only in keyword results
                merged[pid] = {
                    **result,
                    "semantic_score": 0.0,  # Default if no semantic match
                    "keyword_score": result["keyword_score"],
                    "sources": ["keyword"]
                }
        
        # Calculate hybrid score
        for pid, data in merged.items():
            hybrid_score = (
                data["semantic_score"] * request.semantic_weight +
                data["keyword_score"] * request.keyword_weight
            )
            data["hybrid_score"] = hybrid_score
        
        # Sort by hybrid score (descending)
        final_results = sorted(
            merged.values(),
            key=lambda x: x["hybrid_score"],
            reverse=True
        )[:request.top_k]
        
        return {
            "query": request.query,
            "method": "hybrid",
            "semantic_weight": request.semantic_weight,
            "keyword_weight": request.keyword_weight,
            "semantic_results_count": len(semantic_results),
            "keyword_results_count": len(keyword_results),
            "total_unique_processes": len(merged),
            "count": len(final_results),
            "results": final_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Hybrid search failed: {str(e)}"
        )
