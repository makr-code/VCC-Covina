"""
Polyglot Data Transformer

Transforms generic entity data into database-specific formats for optimal
polyglot persistence across PostgreSQL, Neo4j, ChromaDB, and CouchDB.

Each database receives data tailored to its strengths:
- PostgreSQL: Structured relational data
- Neo4j: Graph nodes + relationships
- ChromaDB: Semantic embeddings + minimal metadata
- CouchDB: Full document content

Author: GitHub Copilot
Date: 17. Januar 2025
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Lazy-loaded embedding model (singleton)
_embedding_model = None


def get_embedding_model():
    """
    Lazy-load SentenceTransformer model.
    
    Returns:
        SentenceTransformer instance for semantic embeddings
    """
    global _embedding_model
    
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("✅ SentenceTransformer model loaded (all-MiniLM-L6-v2, 384-dim)")
        except Exception as e:
            logger.error(f"❌ Failed to load SentenceTransformer: {e}")
            _embedding_model = None
    
    return _embedding_model


class PolyglotDataTransformer:
    """
    Transforms generic entity data into database-specific formats.
    
    Usage:
        transformer = PolyglotDataTransformer()
        polyglot_data = transformer.transform_for_golden_dataset(entry)
        
        # Pass to UDS3 SAGA
        result = uds3.saga_crud(data=polyglot_data, ...)
    """
    
    @staticmethod
    def transform_for_golden_dataset(entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform GoldenDataset entry for polyglot persistence.
        
        Args:
            entry: GoldenDataset entry with:
                - document_id (str): Unique document ID
                - classification (str): Document type
                - quality_score (float): Quality score (0.0-1.0)
                - reviewed_by (str): Reviewer username
                - notes (str): Review notes
                - metadata (dict): Additional metadata
        
        Returns:
            Database-specific data for PostgreSQL, Neo4j, ChromaDB
        """
        document_id = entry.get("document_id")
        classification = entry.get("classification")
        quality_score = entry.get("quality_score", 0.0)
        reviewed_by = entry.get("reviewed_by", "system")
        notes = entry.get("notes", "")
        metadata = entry.get("metadata", {})
        
        # Generate timestamp
        reviewed_at = datetime.now().isoformat()
        
        return {
            # 1. PostgreSQL (Relational Master)
            "relational": {
                "document_id": document_id,
                "classification": classification,
                "quality_score": quality_score,
                "reviewed_by": reviewed_by,
                "reviewed_at": reviewed_at,
                "notes": notes,
                "metadata": json.dumps(metadata) if metadata else "{}"
            },
            
            # 2. Neo4j (Graph Relations)
            "graph": {
                "node": {
                    "id": document_id,
                    "type": "GoldenDataset",
                    "classification": classification,
                    "quality_score": quality_score,
                    "reviewed_by": reviewed_by,
                    "reviewed_at": reviewed_at
                },
                "relationships": [
                    {
                        "type": "HAS_CLASSIFICATION",
                        "target": classification,
                        "properties": {
                            "confidence": 1.0,
                            "source": "manual_review"
                        }
                    },
                    {
                        "type": "REVIEWED_BY",
                        "target": reviewed_by,
                        "properties": {
                            "reviewed_at": reviewed_at,
                            "quality_score": quality_score
                        }
                    },
                    {
                        "type": "BELONGS_TO",
                        "target": "GOLDEN_DATASET_COLLECTION",
                        "properties": {
                            "added_at": reviewed_at,
                            "quality_threshold": 0.8
                        }
                    }
                ]
            },
            
            # 3. ChromaDB (Vector Embeddings)
            "vector": {
                "embeddings": PolyglotDataTransformer._generate_embeddings_for_golden_dataset(entry),
                "metadata": {
                    "document_id": document_id,
                    "classification": classification,
                    "quality_score": quality_score,
                    "reviewed_by": reviewed_by,
                    "is_golden_dataset": True,  # Important for filtering!
                    "entity_type": "GoldenDataset"
                },
                "text": f"Classification: {classification}. Quality: {quality_score:.2f}. Notes: {notes or 'None'}"
            }
        }
    
    @staticmethod
    def transform_for_graph_pattern(pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform GraphPattern for polyglot persistence.
        
        Args:
            pattern: Graph pattern with:
                - pattern_id (str): Unique pattern ID
                - name (str): Pattern name
                - category (str): Pattern category
                - nodes_definition (str): Nodes JSON
                - relationships_definition (str): Relationships JSON
                - metadata (dict): Additional metadata
        
        Returns:
            Database-specific data for PostgreSQL, Neo4j
        """
        pattern_id = pattern.get("pattern_id")
        name = pattern.get("name")
        category = pattern.get("category", "general")
        nodes_def = pattern.get("nodes_definition", "[]")
        rels_def = pattern.get("relationships_definition", "[]")
        metadata = pattern.get("metadata", {})
        
        created_at = datetime.now().isoformat()
        
        return {
            # 1. PostgreSQL (Relational Master)
            "relational": {
                "pattern_id": pattern_id,
                "name": name,
                "category": category,
                "nodes_definition": nodes_def,
                "relationships_definition": rels_def,
                "status": pattern.get("status", "active"),
                "created_at": created_at,
                "metadata": json.dumps(metadata) if metadata else "{}"
            },
            
            # 2. Neo4j (Graph Pattern as Template)
            "graph": {
                "node": {
                    "id": pattern_id,
                    "type": "GraphPattern",
                    "name": name,
                    "category": category,
                    "status": pattern.get("status", "active"),
                    "created_at": created_at
                },
                "relationships": [
                    {
                        "type": "BELONGS_TO_CATEGORY",
                        "target": category,
                        "properties": {"pattern_type": "golden"}
                    },
                    {
                        "type": "DEFINES_NODES",
                        "target": "PATTERN_NODES",
                        "properties": {"nodes_count": len(json.loads(nodes_def) if nodes_def != "[]" else [])}
                    },
                    {
                        "type": "DEFINES_RELATIONSHIPS",
                        "target": "PATTERN_RELATIONSHIPS",
                        "properties": {"rels_count": len(json.loads(rels_def) if rels_def != "[]" else [])}
                    }
                ],
                # Store pattern structure as graph template
                "pattern_template": {
                    "nodes": json.loads(nodes_def) if nodes_def != "[]" else [],
                    "relationships": json.loads(rels_def) if rels_def != "[]" else []
                }
            }
        }
    
    @staticmethod
    def transform_for_governance_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform GovernancePolicy for polyglot persistence.
        
        Args:
            policy: Governance policy with:
                - policy_id (str): Unique policy ID
                - name (str): Policy name
                - policy_type (str): Policy type
                - scope (str): Policy scope
                - rules (dict): Policy rules
                - priority (int): Priority
        
        Returns:
            Database-specific data for PostgreSQL, Neo4j
        """
        policy_id = policy.get("policy_id")
        name = policy.get("name")
        policy_type = policy.get("policy_type")
        scope = policy.get("scope", "global")
        rules = policy.get("rules", {})
        priority = policy.get("priority", 100)
        
        return {
            # 1. PostgreSQL (Relational Master)
            "relational": {
                "policy_id": policy_id,
                "name": name,
                "description": policy.get("description", ""),
                "policy_type": policy_type,
                "scope": scope,
                "rules": json.dumps(rules),
                "status": policy.get("status", "active"),
                "priority": priority,
                "effective_from": policy.get("effective_from"),
                "effective_until": policy.get("effective_until"),
                "created_by": policy.get("created_by", "system"),
                "approved_by": policy.get("approved_by"),
                "approved_at": policy.get("approved_at"),
                "metadata": json.dumps(policy.get("metadata", {}))
            },
            
            # 2. Neo4j (Policy Hierarchy + Enforcement)
            "graph": {
                "node": {
                    "id": policy_id,
                    "type": "GovernancePolicy",
                    "name": name,
                    "policy_type": policy_type,
                    "scope": scope,
                    "priority": priority,
                    "status": policy.get("status", "active")
                },
                "relationships": [
                    {
                        "type": "HAS_TYPE",
                        "target": policy_type,
                        "properties": {"priority": priority}
                    },
                    {
                        "type": "APPLIES_TO_SCOPE",
                        "target": scope,
                        "properties": {"enforcement_level": "mandatory"}
                    },
                    {
                        "type": "ENFORCES_RULES",
                        "target": "POLICY_RULES",
                        "properties": {"rules_count": len(rules)}
                    }
                ]
            }
        }
    
    @staticmethod
    def transform_for_review_queue_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform ReviewQueueItem for polyglot persistence.
        
        Args:
            item: Review queue item with:
                - document_id (str): Document to review
                - review_type (str): Type of review
                - priority (str): Priority level
                - status (str): Review status
                - assigned_to (str): Assigned reviewer
        
        Returns:
            Database-specific data for PostgreSQL, Neo4j, ChromaDB
        """
        document_id = item.get("document_id")
        review_type = item.get("review_type")
        priority = item.get("priority", "medium")
        status = item.get("status", "pending")
        assigned_to = item.get("assigned_to")
        
        created_at = datetime.now().isoformat()
        
        return {
            # 1. PostgreSQL (Relational Master)
            "relational": {
                "document_id": document_id,
                "review_type": review_type,
                "priority": priority,
                "status": status,
                "assigned_to": assigned_to,
                "created_at": created_at,
                "metadata": json.dumps(item.get("metadata", {}))
            },
            
            # 2. Neo4j (Review Workflow)
            "graph": {
                "node": {
                    "id": f"review_{document_id}_{created_at}",
                    "type": "ReviewTask",
                    "review_type": review_type,
                    "priority": priority,
                    "status": status,
                    "created_at": created_at
                },
                "relationships": [
                    {
                        "type": "REVIEWS_DOCUMENT",
                        "target": document_id,
                        "properties": {"review_type": review_type}
                    },
                    {
                        "type": "ASSIGNED_TO",
                        "target": assigned_to,
                        "properties": {"assigned_at": created_at}
                    },
                    {
                        "type": "HAS_PRIORITY",
                        "target": priority.upper(),
                        "properties": {"priority_level": ["low", "medium", "high", "critical"].index(priority) + 1}
                    }
                ]
            },
            
            # 3. ChromaDB (Review History Embeddings)
            "vector": {
                "embeddings": PolyglotDataTransformer._generate_embeddings_for_review(item),
                "metadata": {
                    "document_id": document_id,
                    "review_type": review_type,
                    "priority": priority,
                    "status": status,
                    "assigned_to": assigned_to,
                    "entity_type": "ReviewQueueItem"
                },
                "text": f"Review: {review_type}. Priority: {priority}. Status: {status}. Assigned to: {assigned_to}"
            }
        }
    
    @staticmethod
    def transform_for_knowledge_gap(gap: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform KnowledgeGap for polyglot persistence.
        
        Args:
            gap: Knowledge gap with:
                - gap_type (str): Gap type
                - description (str): Gap description
                - severity (str): Severity level
                - status (str): Gap status
                - source (str): Gap source
        
        Returns:
            Database-specific data for PostgreSQL, Neo4j, ChromaDB
        """
        gap_type = gap.get("gap_type")
        description = gap.get("description")
        severity = gap.get("severity", "medium")
        status = gap.get("status", "open")
        source = gap.get("source", "system")
        
        created_at = datetime.now().isoformat()
        gap_id = gap.get("gap_id") or f"gap_{hashlib.md5(f'{gap_type}_{description}_{created_at}'.encode()).hexdigest()[:16]}"
        
        return {
            # 1. PostgreSQL (Relational Master)
            "relational": {
                "gap_id": gap_id,
                "gap_type": gap_type,
                "description": description,
                "severity": severity,
                "status": status,
                "source": source,
                "context": gap.get("context", ""),
                "tags": json.dumps(gap.get("tags", [])),
                "created_at": created_at,
                "metadata": json.dumps(gap.get("metadata", {}))
            },
            
            # 2. Neo4j (Gap Dependencies)
            "graph": {
                "node": {
                    "id": gap_id,
                    "type": "KnowledgeGap",
                    "gap_type": gap_type,
                    "severity": severity,
                    "status": status,
                    "created_at": created_at
                },
                "relationships": [
                    {
                        "type": "HAS_TYPE",
                        "target": gap_type,
                        "properties": {"severity": severity}
                    },
                    {
                        "type": "DETECTED_BY",
                        "target": source,
                        "properties": {"detected_at": created_at}
                    },
                    {
                        "type": "REQUIRES_ACTION",
                        "target": "GAP_RESOLUTION",
                        "properties": {"priority": ["low", "medium", "high", "critical"].index(severity) + 1}
                    }
                ]
            },
            
            # 3. ChromaDB (Gap Similarity Search)
            "vector": {
                "embeddings": PolyglotDataTransformer._generate_embeddings_for_gap(gap),
                "metadata": {
                    "gap_id": gap_id,
                    "gap_type": gap_type,
                    "severity": severity,
                    "status": status,
                    "source": source,
                    "entity_type": "KnowledgeGap"
                },
                "text": f"Gap Type: {gap_type}. Severity: {severity}. Description: {description}"
            }
        }
    
    # ========================================================================
    # EMBEDDING GENERATION METHODS
    # ========================================================================
    
    @staticmethod
    def _generate_embeddings_for_golden_dataset(entry: Dict[str, Any]) -> List[float]:
        """
        Generate semantic embeddings for GoldenDataset entry.
        
        Combines:
        - Classification (primary factor)
        - Notes (context)
        - Quality Score (weighting)
        
        Returns:
            384-dim embedding vector or None if model unavailable
        """
        model = get_embedding_model()
        if not model:
            logger.warning("⚠️ Embedding model unavailable - returning None")
            return None
        
        # Combine text for embedding
        text = f"Classification: {entry.get('classification', 'unknown')}"
        if entry.get("notes"):
            text += f" Notes: {entry['notes']}"
        if entry.get("quality_score"):
            text += f" Quality: {entry['quality_score']:.2f}"
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return None
    
    @staticmethod
    def _generate_embeddings_for_review(item: Dict[str, Any]) -> List[float]:
        """Generate embeddings for ReviewQueueItem"""
        model = get_embedding_model()
        if not model:
            return None
        
        text = f"Review Type: {item.get('review_type', 'unknown')}"
        text += f" Priority: {item.get('priority', 'medium')}"
        text += f" Status: {item.get('status', 'pending')}"
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return None
    
    @staticmethod
    def _generate_embeddings_for_gap(gap: Dict[str, Any]) -> List[float]:
        """Generate embeddings for KnowledgeGap"""
        model = get_embedding_model()
        if not model:
            return None
        
        text = f"Gap Type: {gap.get('gap_type', 'unknown')}"
        text += f" Severity: {gap.get('severity', 'medium')}"
        if gap.get("description"):
            text += f" Description: {gap['description']}"
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return None
    
    # ========================================================================
    # BATCH OPERATIONS - Polyglot Transformations
    # ========================================================================
    
    @staticmethod
    def transform_for_batch_update(updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform batch update operations for polyglot persistence.
        
        Args:
            updates: List of update operations, each with:
                - document_id (str): Document to update
                - fields (dict): Fields to update
        
        Returns:
            Database-specific batch update data
        """
        relational_updates = []
        graph_updates = []
        vector_updates = []
        
        for update in updates:
            document_id = update.get("document_id")
            fields = update.get("fields", {})
            
            # 1. PostgreSQL: Update structured fields
            relational_updates.append({
                "document_id": document_id,
                "fields": fields,
                "updated_at": datetime.now().isoformat()
            })
            
            # 2. Neo4j: Update node properties (no full content)
            # Extract only metadata fields (not full content)
            graph_fields = {k: v for k, v in fields.items() 
                           if k in ["status", "priority", "category", "classification"]}
            
            if graph_fields:
                graph_updates.append({
                    "document_id": document_id,
                    "properties": graph_fields,
                    "updated_at": datetime.now().isoformat()
                })
            
            # 3. ChromaDB: Regenerate embeddings if content changed
            # Only if fields contain content that affects semantics
            content_fields = ["title", "content", "description", "notes"]
            has_content_update = any(k in fields for k in content_fields)
            
            if has_content_update:
                # Generate new text for embedding
                text_parts = []
                for field in content_fields:
                    if field in fields:
                        text_parts.append(f"{field}: {fields[field]}")
                
                text = " ".join(text_parts)
                
                # Generate embedding
                model = get_embedding_model()
                if model:
                    try:
                        embedding = model.encode(text, convert_to_numpy=True)
                        vector_updates.append({
                            "document_id": document_id,
                            "embeddings": embedding.tolist(),
                            "metadata": {
                                "document_id": document_id,
                                "updated_at": datetime.now().isoformat(),
                                **{k: v for k, v in fields.items() 
                                   if k in ["status", "classification", "category"]}
                            },
                            "text": text
                        })
                    except Exception as e:
                        logger.error(f"❌ Embedding generation failed for {document_id}: {e}")
        
        return {
            "relational": {"updates": relational_updates} if relational_updates else None,
            "graph": {"updates": graph_updates} if graph_updates else None,
            "vector": {"updates": vector_updates} if vector_updates else None
        }
    
    @staticmethod
    def transform_for_batch_delete(document_ids: List[str], delete_mode: str = "soft", 
                                   cascade: bool = False) -> Dict[str, Any]:
        """
        Transform batch delete operations for polyglot persistence.
        
        Args:
            document_ids: List of document IDs to delete
            delete_mode: "soft" (mark as deleted) or "hard" (permanent delete)
            cascade: For Neo4j, also delete relationships
        
        Returns:
            Database-specific batch delete data
        """
        timestamp = datetime.now().isoformat()
        
        return {
            # 1. PostgreSQL: UPDATE deleted=true OR DELETE
            "relational": {
                "document_ids": document_ids,
                "delete_mode": delete_mode,
                "deleted_at": timestamp if delete_mode == "soft" else None
            },
            
            # 2. Neo4j: DETACH DELETE (removes relationships) or DELETE
            "graph": {
                "document_ids": document_ids,
                "delete_mode": delete_mode,
                "cascade": cascade,  # DETACH DELETE if True
                "deleted_at": timestamp if delete_mode == "soft" else None
            },
            
            # 3. ChromaDB: DELETE vectors (always hard delete)
            "vector": {
                "document_ids": document_ids,
                "delete_mode": "hard"  # ChromaDB doesn't support soft delete
            }
        }
    
    @staticmethod
    def transform_for_batch_upsert(documents: List[Dict[str, Any]], 
                                   conflict_resolution: str = "update") -> Dict[str, Any]:
        """
        Transform batch upsert operations for polyglot persistence.
        
        Args:
            documents: List of documents to upsert, each with:
                - document_id (str): Unique ID
                - fields (dict): Document fields
            conflict_resolution: "update" or "skip"
        
        Returns:
            Database-specific batch upsert data
        """
        relational_docs = []
        graph_docs = []
        vector_docs = []
        
        for doc in documents:
            document_id = doc.get("document_id")
            fields = doc.get("fields", {})
            
            # 1. PostgreSQL: INSERT ON CONFLICT UPDATE/DO NOTHING
            relational_docs.append({
                "document_id": document_id,
                "fields": fields,
                "conflict_resolution": conflict_resolution,
                "created_at": datetime.now().isoformat()
            })
            
            # 2. Neo4j: MERGE (always upsert)
            # Extract only metadata fields
            graph_fields = {k: v for k, v in fields.items() 
                           if k in ["status", "priority", "category", "classification", "title"]}
            
            if graph_fields:
                graph_docs.append({
                    "document_id": document_id,
                    "properties": graph_fields,
                    "created_at": datetime.now().isoformat()
                })
            
            # 3. ChromaDB: Add/Update embeddings
            # Generate embeddings from content fields
            content_fields = ["title", "content", "description", "notes"]
            text_parts = []
            for field in content_fields:
                if field in fields:
                    text_parts.append(f"{field}: {fields[field]}")
            
            if text_parts:
                text = " ".join(text_parts)
                
                # Generate embedding
                model = get_embedding_model()
                if model:
                    try:
                        embedding = model.encode(text, convert_to_numpy=True)
                        vector_docs.append({
                            "document_id": document_id,
                            "embeddings": embedding.tolist(),
                            "metadata": {
                                "document_id": document_id,
                                "created_at": datetime.now().isoformat(),
                                **{k: v for k, v in fields.items() 
                                   if k in ["status", "classification", "category"]}
                            },
                            "text": text
                        })
                    except Exception as e:
                        logger.error(f"❌ Embedding generation failed for {document_id}: {e}")
        
        return {
            "relational": {"documents": relational_docs} if relational_docs else None,
            "graph": {"documents": graph_docs} if graph_docs else None,
            "vector": {"documents": vector_docs} if vector_docs else None
        }

