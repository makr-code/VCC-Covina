"""
Process Query API - Neo4j & ChromaDB Queries

Provides query interfaces for:
- Process listing & filtering (Neo4j)
- Process details with entities (Neo4j)
- Semantic search on steps (ChromaDB)
- Process similarity (ChromaDB embeddings)
"""
from __future__ import annotations
from typing import Any, Optional
from datetime import datetime


class ProcessQueryService:
    """
    Service for querying processes from Neo4j and ChromaDB.
    
    Uses:
    - Neo4j for graph queries (processes, steps, relations)
    - ChromaDB for semantic search (step embeddings)
    """
    
    def __init__(self, graph_adapter, chroma_client=None):
        """
        Initialize query service.
        
        Args:
            graph_adapter: Neo4j graph adapter (execute_query method)
            chroma_client: Optional ChromaDB client for semantic search
        """
        self.graph = graph_adapter
        self.chroma = chroma_client
    
    # ========================================================================
    # PROCESS LISTING & FILTERING
    # ========================================================================
    
    def list_processes(
        self,
        domain: str | None = None,
        status: str | None = None,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List processes with optional filters.
        
        Args:
            domain: Filter by domain (e.g., "Stadtplanung")
            status: Filter by status (e.g., "active", "draft", "archived")
            owner: Filter by owner (e.g., "Planungsamt")
            limit: Max results (default: 100)
            offset: Skip results (pagination)
            
        Returns:
            Dict with:
            - processes: List of process dicts
            - total: Total count (before pagination)
            - limit: Applied limit
            - offset: Applied offset
        """
        # Build WHERE clause
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        if domain:
            where_conditions.append("p.domain = $domain")
            params["domain"] = domain
        
        if status:
            where_conditions.append("p.status = $status")
            params["status"] = status
        
        if owner:
            where_conditions.append("p.owner = $owner")
            params["owner"] = owner
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        # Count query
        count_query = f"""
        MATCH (p:Process)
        {where_clause}
        RETURN count(p) AS total
        """
        count_result = self.graph.execute_query(count_query, params)
        total = count_result[0]["total"] if count_result else 0
        
        # List query
        list_query = f"""
        MATCH (p:Process)
        {where_clause}
        RETURN p
        ORDER BY p.created_at DESC
        SKIP $offset
        LIMIT $limit
        """
        
        result = self.graph.execute_query(list_query, params)
        
        processes = []
        for record in result:
            p = record["p"]
            processes.append({
                "id": p.get("id"),
                "key": p.get("key"),
                "name": p.get("name"),
                "version": p.get("version"),
                "domain": p.get("domain"),
                "owner": p.get("owner"),
                "status": p.get("status"),
                "description": p.get("description"),
                "created_at": str(p.get("created_at")) if p.get("created_at") else None,
                "updated_at": str(p.get("updated_at")) if p.get("updated_at") else None,
            })
        
        return {
            "processes": processes,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    # ========================================================================
    # PROCESS DETAILS
    # ========================================================================
    
    def get_process_details(self, process_id: str) -> dict[str, Any] | None:
        """
        Get process details with all entities and relations.
        
        Args:
            process_id: Process ID (UUIDv7)
            
        Returns:
            Process dict with:
            - process: Process metadata
            - steps: List of steps with relations
            - legal_refs: Legal references
            - stats: Step counts, role counts, etc.
        """
        # Get process
        query_process = """
        MATCH (p:Process {id: $process_id})
        RETURN p
        """
        result = self.graph.execute_query(query_process, {"process_id": process_id})
        
        if not result:
            return None
        
        p = result[0]["p"]
        
        # Get steps with relations
        query_steps = """
        MATCH (p:Process {id: $process_id})-[:HAS_STEP]->(s:Step)
        OPTIONAL MATCH (s)-[:NEXT]->(next_step:Step)
        OPTIONAL MATCH (s)-[:PERFORMED_BY]->(role:Role)
        OPTIONAL MATCH (s)-[:USES_SYSTEM]->(system:System)
        OPTIONAL MATCH (s)-[:CONTROLS]->(control:Control)
        OPTIONAL MATCH (s)-[:CITES]->(legal_ref:LegalRef)
        RETURN s, 
               collect(DISTINCT next_step.id) AS next_steps,
               collect(DISTINCT {id: role.id, name: role.name, level: role.level}) AS roles,
               collect(DISTINCT {id: system.id, name: system.name, type: system.type}) AS systems,
               collect(DISTINCT {id: control.id, name: control.name, type: control.type, criticality: control.criticality}) AS controls,
               collect(DISTINCT {id: legal_ref.id, source: legal_ref.source, article: legal_ref.article}) AS legal_refs
        ORDER BY s.created_at
        """
        
        steps_result = self.graph.execute_query(query_steps, {"process_id": process_id})
        
        steps = []
        for record in steps_result:
            s = record["s"]
            steps.append({
                "id": s.get("id"),
                "key": s.get("key"),
                "name": s.get("name"),
                "type": s.get("type"),
                "description": s.get("description"),
                "duration_days": s.get("duration_days"),
                "mandatory": s.get("mandatory"),
                "automated": s.get("automated"),
                "next_steps": [nid for nid in record["next_steps"] if nid],
                "roles": [r for r in record["roles"] if r.get("id")],
                "systems": [sys for sys in record["systems"] if sys.get("id")],
                "controls": [c for c in record["controls"] if c.get("id")],
                "legal_refs": [lr for lr in record["legal_refs"] if lr.get("id")],
            })
        
        # Get process-level legal refs
        query_legal = """
        MATCH (p:Process {id: $process_id})-[:CITES]->(l:LegalRef)
        RETURN l
        """
        legal_result = self.graph.execute_query(query_legal, {"process_id": process_id})
        
        legal_refs = []
        for record in legal_result:
            l = record["l"]
            legal_refs.append({
                "id": l.get("id"),
                "source": l.get("source"),
                "article": l.get("article"),
                "paragraph": l.get("paragraph"),
                "description": l.get("description"),
                "url": l.get("url"),
            })
        
        # Stats
        stats = {
            "steps_count": len(steps),
            "roles_count": len(set(r["id"] for step in steps for r in step["roles"] if r.get("id"))),
            "systems_count": len(set(s["id"] for step in steps for s in step["systems"] if s.get("id"))),
            "controls_count": len(set(c["id"] for step in steps for c in step["controls"] if c.get("id"))),
            "legal_refs_count": len(legal_refs),
        }
        
        return {
            "process": {
                "id": p.get("id"),
                "key": p.get("key"),
                "name": p.get("name"),
                "version": p.get("version"),
                "domain": p.get("domain"),
                "owner": p.get("owner"),
                "status": p.get("status"),
                "description": p.get("description"),
                "source": p.get("source"),
                "source_format": p.get("source_format"),
                "created_at": str(p.get("created_at")) if p.get("created_at") else None,
                "updated_at": str(p.get("updated_at")) if p.get("updated_at") else None,
            },
            "steps": steps,
            "legal_refs": legal_refs,
            "stats": stats,
        }
    
    # ========================================================================
    # FULLTEXT SEARCH
    # ========================================================================
    
    def search_processes(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """
        Fulltext search on process name and description.
        
        Args:
            query: Search query string
            limit: Max results
            
        Returns:
            List of matching processes with relevance score
        """
        cypher = """
        CALL db.index.fulltext.queryNodes('process_search', $query)
        YIELD node, score
        RETURN node AS p, score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        result = self.graph.execute_query(cypher, {"query": query, "limit": limit})
        
        processes = []
        for record in result:
            p = record["p"]
            processes.append({
                "id": p.get("id"),
                "key": p.get("key"),
                "name": p.get("name"),
                "version": p.get("version"),
                "domain": p.get("domain"),
                "description": p.get("description"),
                "score": record["score"],
            })
        
        return processes
    
    def search_steps(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """
        Fulltext search on step name, description, and instructions.
        
        Args:
            query: Search query string
            limit: Max results
            
        Returns:
            List of matching steps with process info and relevance score
        """
        cypher = """
        CALL db.index.fulltext.queryNodes('step_search', $query)
        YIELD node, score
        MATCH (p:Process)-[:HAS_STEP]->(node)
        RETURN node AS s, p, score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        result = self.graph.execute_query(cypher, {"query": query, "limit": limit})
        
        steps = []
        for record in result:
            s = record["s"]
            p = record["p"]
            steps.append({
                "step": {
                    "id": s.get("id"),
                    "key": s.get("key"),
                    "name": s.get("name"),
                    "type": s.get("type"),
                    "description": s.get("description"),
                },
                "process": {
                    "id": p.get("id"),
                    "key": p.get("key"),
                    "name": p.get("name"),
                },
                "score": record["score"],
            })
        
        return steps
    
    # ========================================================================
    # SEMANTIC SEARCH (ChromaDB)
    # ========================================================================
    
    def semantic_search_steps(
        self, 
        query_text: str, 
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Semantic search on step embeddings using ChromaDB.
        
        Args:
            query_text: Natural language query
            limit: Max results
            min_similarity: Minimum cosine similarity (0.0 to 1.0)
            
        Returns:
            List of matching steps with similarity scores
        """
        if not self.chroma:
            return []
        
        # Query ChromaDB
        try:
            results = self.chroma.query(
                collection_name="process_steps",
                query_texts=[query_text],
                n_results=limit,
            )
            
            if not results or not results.get("ids"):
                return []
            
            # Get step IDs and distances
            step_ids = results["ids"][0]
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(step_ids)
            
            # Convert distance to similarity (cosine distance → similarity)
            similarities = [1.0 - d for d in distances]
            
            # Filter by min_similarity
            filtered = [(sid, sim) for sid, sim in zip(step_ids, similarities) if sim >= min_similarity]
            
            if not filtered:
                return []
            
            # Get step details from Neo4j
            step_ids_filtered = [sid for sid, _ in filtered]
            
            cypher = """
            MATCH (s:Step)
            WHERE s.id IN $step_ids
            MATCH (p:Process)-[:HAS_STEP]->(s)
            RETURN s, p
            """
            
            neo4j_results = self.graph.execute_query(cypher, {"step_ids": step_ids_filtered})
            
            # Create result dict
            steps_dict = {}
            for record in neo4j_results:
                s = record["s"]
                p = record["p"]
                steps_dict[s["id"]] = {
                    "step": {
                        "id": s.get("id"),
                        "key": s.get("key"),
                        "name": s.get("name"),
                        "type": s.get("type"),
                        "description": s.get("description"),
                    },
                    "process": {
                        "id": p.get("id"),
                        "key": p.get("key"),
                        "name": p.get("name"),
                    },
                }
            
            # Build results in order
            results_ordered = []
            for step_id, similarity in filtered:
                if step_id in steps_dict:
                    result = steps_dict[step_id].copy()
                    result["similarity"] = round(similarity, 4)
                    results_ordered.append(result)
            
            return results_ordered
        
        except Exception as e:
            # Log error but don't crash
            print(f"ChromaDB semantic search error: {e}")
            return []
    
    # ========================================================================
    # PROCESS SIMILARITY
    # ========================================================================
    
    def find_similar_processes(
        self,
        process_id: str,
        limit: int = 5,
        min_similarity: float = 0.6,
    ) -> list[dict[str, Any]]:
        """
        Find similar processes based on step embeddings.
        
        Strategy:
        1. Get all steps for source process
        2. Query ChromaDB for similar steps
        3. Group by process and aggregate similarity scores
        4. Rank by average similarity
        
        Args:
            process_id: Source process ID
            limit: Max similar processes
            min_similarity: Minimum average similarity
            
        Returns:
            List of similar processes with similarity scores
        """
        if not self.chroma:
            return []
        
        # Get steps for source process
        cypher = """
        MATCH (p:Process {id: $process_id})-[:HAS_STEP]->(s:Step)
        RETURN s.id AS step_id, s.name AS step_name, s.description AS step_description
        """
        
        steps_result = self.graph.execute_query(cypher, {"process_id": process_id})
        
        if not steps_result:
            return []
        
        # Aggregate similarities by process
        process_similarities = {}  # {process_id: [similarity_scores]}
        
        for step in steps_result:
            step_text = f"{step['step_name']} {step.get('step_description', '')}"
            
            # Query similar steps
            try:
                results = self.chroma.query(
                    collection_name="process_steps",
                    query_texts=[step_text],
                    n_results=20,  # Get more to find diverse processes
                )
                
                if results and results.get("ids"):
                    step_ids = results["ids"][0]
                    distances = results["distances"][0] if results.get("distances") else [0.0] * len(step_ids)
                    
                    # Get process IDs for similar steps
                    cypher_proc = """
                    MATCH (p:Process)-[:HAS_STEP]->(s:Step)
                    WHERE s.id IN $step_ids AND p.id <> $source_process_id
                    RETURN s.id AS step_id, p.id AS process_id
                    """
                    
                    proc_results = self.graph.execute_query(
                        cypher_proc, 
                        {"step_ids": step_ids, "source_process_id": process_id}
                    )
                    
                    # Map step_id → process_id
                    step_to_proc = {r["step_id"]: r["process_id"] for r in proc_results}
                    
                    # Aggregate similarities
                    for sid, dist in zip(step_ids, distances):
                        if sid in step_to_proc:
                            proc_id = step_to_proc[sid]
                            similarity = 1.0 - dist
                            process_similarities.setdefault(proc_id, []).append(similarity)
            
            except Exception as e:
                print(f"Error querying similar steps: {e}")
                continue
        
        # Calculate average similarity per process
        process_scores = []
        for proc_id, sims in process_similarities.items():
            avg_sim = sum(sims) / len(sims)
            if avg_sim >= min_similarity:
                process_scores.append((proc_id, avg_sim, len(sims)))
        
        # Sort by average similarity
        process_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get process details for top matches
        top_process_ids = [pid for pid, _, _ in process_scores[:limit]]
        
        if not top_process_ids:
            return []
        
        cypher_details = """
        MATCH (p:Process)
        WHERE p.id IN $process_ids
        RETURN p
        """
        
        details_result = self.graph.execute_query(cypher_details, {"process_ids": top_process_ids})
        
        # Create result dict
        process_dict = {}
        for record in details_result:
            p = record["p"]
            process_dict[p["id"]] = {
                "id": p.get("id"),
                "key": p.get("key"),
                "name": p.get("name"),
                "version": p.get("version"),
                "domain": p.get("domain"),
                "description": p.get("description"),
            }
        
        # Build final results
        results = []
        for proc_id, avg_sim, match_count in process_scores[:limit]:
            if proc_id in process_dict:
                result = process_dict[proc_id].copy()
                result["similarity"] = round(avg_sim, 4)
                result["matching_steps"] = match_count
                results.append(result)
        
        return results
