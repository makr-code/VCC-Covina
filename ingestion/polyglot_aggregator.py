#!/usr/bin/env python3
"""
Polyglot Document Aggregator
=============================

Aggregiert Daten aus allen 4 UDS3-Datenbanken in ein vollständiges
JSON-Objekt, das auch die Original-Binärdatei enthält.

Format:
{
  "document_id": "abc123",
  "metadata": {
    "created_at": "2025-11-19T18:00:00",
    "file_path": "document.pdf",
    "classification": "GESETZ"
  },
  "relational": { /* PostgreSQL Daten */ },
  "vector": [ /* ChromaDB chunks + embeddings */ ],
  "graph": { /* Neo4j nodes/relationships */ },
  "file": { 
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "size": 524288,
    "text_content": "...",
    "binary_data": "<base64>" 
  }
}

Autor: Covina System  
Datum: November 2025
"""

import json
import base64
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class PolyglotDocumentAggregator:
    """
    Aggregiert Dokument-Daten aus allen Polyglot-Datenbanken.
    
    Erstellt ein vollständiges JSON-Objekt mit:
    - Relational (PostgreSQL): Metadaten
    - Vector (ChromaDB): Embeddings + Chunks
    - Graph (Neo4j): Nodes + Relationships
    - File (CouchDB + Binary): Text + Binärdaten
    """
    
    def __init__(self):
        pass
    
    def aggregate_document(
        self,
        document_id: str,
        file_path: str,
        classification: str,
        relational_data: Optional[Dict[str, Any]] = None,
        vector_data: Optional[List[Dict[str, Any]]] = None,
        graph_data: Optional[Dict[str, Any]] = None,
        text_content: Optional[str] = None,
        binary_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregiert alle Daten zu einem vollständigen Polyglot-JSON.
        
        Args:
            document_id: Eindeutige Document-ID
            file_path: Pfad zur Datei
            classification: Dokumentklassifizierung
            relational_data: PostgreSQL Metadaten
            vector_data: ChromaDB Chunks mit Embeddings
            graph_data: Neo4j Graph-Daten
            text_content: Extrahierter Text
            binary_file_path: Pfad zur Original-Binärdatei
            
        Returns:
            Vollständiges Polyglot-JSON-Objekt
        """
        # Base structure
        aggregated = {
            "document_id": document_id,
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "file_path": file_path,
                "classification": classification,
                "filename": Path(file_path).name if file_path else None
            }
        }
        
        # 1. Relational data (PostgreSQL)
        if relational_data:
            aggregated["relational"] = relational_data
        else:
            aggregated["relational"] = {
                "document_id": document_id,
                "file_path": file_path,
                "classification": classification,
                "note": "Full metadata from PostgreSQL"
            }
        
        # 2. Vector data (ChromaDB)
        if vector_data:
            aggregated["vector"] = {
                "total_chunks": len(vector_data),
                "chunks": vector_data
            }
        else:
            aggregated["vector"] = {
                "total_chunks": 0,
                "chunks": [],
                "note": "Embeddings from ChromaDB"
            }
        
        # 3. Graph data (Neo4j)
        if graph_data:
            aggregated["graph"] = graph_data
        else:
            aggregated["graph"] = {
                "node_id": document_id,
                "node_type": "Document",
                "relationships": [],
                "note": "Graph data from Neo4j"
            }
        
        # 4. File data (CouchDB + Binary)
        file_data = {}
        
        # Add text content
        if text_content:
            file_data["text_content"] = text_content
            file_data["text_length"] = len(text_content)
        
        # Add binary file if path provided
        if binary_file_path and Path(binary_file_path).exists():
            try:
                file_path_obj = Path(binary_file_path)
                
                # Read binary file
                with open(file_path_obj, 'rb') as f:
                    binary_data = f.read()
                
                # Encode to base64
                base64_data = base64.b64encode(binary_data).decode('utf-8')
                
                # Detect content type
                content_type = self._detect_content_type(file_path_obj)
                
                file_data.update({
                    "filename": file_path_obj.name,
                    "content_type": content_type,
                    "size": len(binary_data),
                    "binary_data": base64_data,
                    "encoding": "base64"
                })
                
                logger.info(f"Added binary file: {file_path_obj.name} ({len(binary_data)} bytes)")
                
            except Exception as e:
                logger.error(f"Error reading binary file {binary_file_path}: {e}")
                file_data["binary_error"] = str(e)
        
        aggregated["file"] = file_data
        
        # Add statistics
        aggregated["statistics"] = {
            "has_relational": bool(relational_data),
            "has_vector": bool(vector_data and len(vector_data) > 0),
            "has_graph": bool(graph_data),
            "has_text": bool(text_content),
            "has_binary": bool(binary_file_path and Path(binary_file_path).exists()),
            "polyglot_completeness": self._calculate_completeness(aggregated)
        }
        
        return aggregated
    
    def _detect_content_type(self, file_path: Path) -> str:
        """Detect MIME type based on file extension"""
        suffix = file_path.suffix.lower()
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.html': 'text/html',
            '.xml': 'application/xml',
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.rtf': 'application/rtf'
        }
        
        return mime_types.get(suffix, 'application/octet-stream')
    
    def _calculate_completeness(self, aggregated: Dict[str, Any]) -> float:
        """
        Calculate polyglot completeness score (0.0-1.0).
        
        Score based on presence of all 4 database types + binary.
        """
        score = 0.0
        
        # Relational (20%)
        if aggregated.get('relational'):
            score += 0.2
        
        # Vector (20%)
        if aggregated.get('vector', {}).get('total_chunks', 0) > 0:
            score += 0.2
        
        # Graph (20%)
        if aggregated.get('graph', {}).get('node_id'):
            score += 0.2
        
        # File - Text (20%)
        if aggregated.get('file', {}).get('text_content'):
            score += 0.2
        
        # File - Binary (20%)
        if aggregated.get('file', {}).get('binary_data'):
            score += 0.2
        
        return round(score, 2)
    
    def save_to_json(self, aggregated: Dict[str, Any], output_path: str) -> None:
        """Save aggregated data to JSON file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(aggregated, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved polyglot JSON to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving JSON to {output_path}: {e}")
            raise
    
    def load_from_json(self, json_path: str) -> Dict[str, Any]:
        """Load aggregated data from JSON file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded polyglot JSON from: {json_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading JSON from {json_path}: {e}")
            raise
    
    def extract_binary(self, aggregated: Dict[str, Any], output_path: str) -> None:
        """Extract binary file from aggregated JSON"""
        try:
            binary_data_b64 = aggregated.get('file', {}).get('binary_data')
            
            if not binary_data_b64:
                raise ValueError("No binary data found in aggregated JSON")
            
            # Decode base64
            binary_data = base64.b64decode(binary_data_b64)
            
            # Write to file
            with open(output_path, 'wb') as f:
                f.write(binary_data)
            
            logger.info(f"Extracted binary file to: {output_path}")
        except Exception as e:
            logger.error(f"Error extracting binary to {output_path}: {e}")
            raise


# Convenience function
def create_polyglot_document(
    document_id: str,
    file_path: str,
    classification: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to create polyglot document.
    
    Args:
        document_id: Document ID
        file_path: File path
        classification: Document classification
        **kwargs: Additional data (relational_data, vector_data, etc.)
    
    Returns:
        Complete polyglot JSON
    """
    aggregator = PolyglotDocumentAggregator()
    return aggregator.aggregate_document(
        document_id=document_id,
        file_path=file_path,
        classification=classification,
        **kwargs
    )
