"""
PostgreSQL Relational Backend für UDS3

Implementiert PostgreSQL-Backend analog zu SQLiteRelationalBackend.
Verwendet für Corvina Backend die migrierte PostgreSQL-Datenbank.
"""

import logging
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PostgreSQLRelationalBackend:
    """PostgreSQL Backend für relationale Daten (Dokument-Metadaten)"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialisiert PostgreSQL Backend
        
        Args:
            config: PostgreSQL Konfiguration mit:
                - host: PostgreSQL Host (e.g., '192.168.178.94')
                - port: PostgreSQL Port (default: 5432)
                - user: Database User (e.g., 'postgres')
                - password: Database Password
                - database: Database Name (e.g., 'postgres')
                - schema: Schema Name (default: 'public')
        """
        self.config = config
        self.host = config.get('host', '192.168.178.94')
        self.port = config.get('port', 5432)
        self.user = config.get('user', 'postgres')
        self.password = config.get('password', 'postgres')
        self.database = config.get('database', 'postgres')
        self.schema = config.get('schema', 'public')
        
        self.conn = None
        self.cursor = None
        
        logger.info(f"PostgreSQL Backend initialisiert: {self.host}:{self.port}/{self.database}")
    
    
    def connect(self):
        """Verbindet zu PostgreSQL-Datenbank"""
        if self.conn is not None and not self.conn.closed:
            return  # Bereits verbunden
        
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            logger.info(f"✅ PostgreSQL Verbindung hergestellt: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ PostgreSQL Verbindung fehlgeschlagen: {e}")
            raise
    
    
    def disconnect(self):
        """Schließt PostgreSQL-Verbindung"""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
        except Exception as e:
            logger.warning(f"Warnung beim Schließen des Cursors: {e}")
        
        try:
            if self.conn and not self.conn.closed:
                self.conn.close()
                self.conn = None
            logger.debug("PostgreSQL Verbindung geschlossen")
        except Exception as e:
            logger.warning(f"Warnung beim Schließen der Verbindung: {e}")
    
    
    def create_tables_if_not_exist(self):
        """Erstellt Tabellen falls nicht vorhanden (Migration hat sie bereits erstellt)"""
        self.connect()
        
        # Documents Tabelle (sollte bereits existieren durch Migration)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                classification TEXT NOT NULL,
                content_length BIGINT NOT NULL,
                legal_terms_count BIGINT NOT NULL,
                created_at TEXT NOT NULL,
                quality_score DOUBLE PRECISION,
                processing_status TEXT DEFAULT 'completed'
            )
        """)
        
        # Keywords Tabelle
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_keywords (
                id SERIAL PRIMARY KEY,
                document_id TEXT,
                keyword TEXT,
                frequency INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents (document_id)
            )
        """)
        
        self.conn.commit()
        logger.info("✅ PostgreSQL Tabellen validiert/erstellt")
    
    
    def insert_document(self, document_id: str, file_path: str, classification: str,
                       content_length: int, legal_terms_count: int, 
                       created_at: Optional[str] = None,
                       quality_score: Optional[float] = None,
                       processing_status: str = 'completed') -> Dict[str, Any]:
        """
        Fügt Dokument ein oder aktualisiert es
        
        Returns:
            Dict mit success, operations, total_documents, etc.
        """
        self.connect()
        
        if created_at is None:
            created_at = datetime.now().isoformat()
        
        try:
            # INSERT oder UPDATE (ON CONFLICT)
            self.cursor.execute("""
                INSERT INTO documents 
                (document_id, file_path, classification, content_length, 
                 legal_terms_count, created_at, quality_score, processing_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) 
                DO UPDATE SET
                    file_path = EXCLUDED.file_path,
                    classification = EXCLUDED.classification,
                    content_length = EXCLUDED.content_length,
                    legal_terms_count = EXCLUDED.legal_terms_count,
                    quality_score = EXCLUDED.quality_score,
                    processing_status = EXCLUDED.processing_status
            """, (document_id, file_path, classification, content_length,
                  legal_terms_count, created_at, quality_score, processing_status))
            
            self.conn.commit()
            
            # Statistiken
            total_docs = self.get_document_count()
            class_docs = self.get_document_count_by_classification(classification)
            
            return {
                "success": True,
                "operations": [
                    "metadata_inserted",
                    "classification_updated",
                    "statistics_calculated"
                ],
                "records_affected": 1,
                "total_documents": total_docs,
                "documents_in_class": class_docs,
                "database": f"{self.host}:{self.port}/{self.database}"
            }
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Dokument-Insert fehlgeschlagen: {e}")
            return {
                "success": False,
                "error": f"PostgreSQL operation failed: {str(e)}"
            }
    
    
    def get_document_count(self) -> int:
        """Gibt Gesamtanzahl der Dokumente zurück"""
        self.connect()
        self.cursor.execute("SELECT COUNT(*) as count FROM documents")
        result = self.cursor.fetchone()
        return result['count'] if result else 0
    
    
    def get_document_count_by_classification(self, classification: str) -> int:
        """Gibt Anzahl Dokumente pro Klassifikation zurück"""
        self.connect()
        self.cursor.execute(
            "SELECT COUNT(*) as count FROM documents WHERE classification = %s",
            (classification,)
        )
        result = self.cursor.fetchone()
        return result['count'] if result else 0
    
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Holt Dokument-Metadaten"""
        self.connect()
        self.cursor.execute(
            "SELECT * FROM documents WHERE document_id = %s",
            (document_id,)
        )
        return self.cursor.fetchone()
    
    
    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Löscht Dokument"""
        self.connect()
        
        try:
            # Lösche Keywords
            self.cursor.execute(
                "DELETE FROM document_keywords WHERE document_id = %s",
                (document_id,)
            )
            
            # Lösche Dokument
            self.cursor.execute(
                "DELETE FROM documents WHERE document_id = %s",
                (document_id,)
            )
            
            rows_deleted = self.cursor.rowcount
            self.conn.commit()
            
            return {
                "success": True,
                "rows_deleted": rows_deleted
            }
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Dokument-Delete fehlgeschlagen: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    
    def get_statistics(self) -> Dict[str, Any]:
        """Holt Datenbank-Statistiken"""
        self.connect()
        
        try:
            # Gesamt-Anzahl
            total = self.get_document_count()
            
            # Klassifikationen
            self.cursor.execute("""
                SELECT classification, COUNT(*) as count
                FROM documents
                GROUP BY classification
                ORDER BY count DESC
            """)
            classifications = {row['classification']: row['count'] 
                             for row in self.cursor.fetchall()}
            
            # Processing Status
            self.cursor.execute("""
                SELECT processing_status, COUNT(*) as count
                FROM documents
                GROUP BY processing_status
                ORDER BY count DESC
            """)
            statuses = {row['processing_status']: row['count'] 
                       for row in self.cursor.fetchall()}
            
            # Quality Score Stats
            self.cursor.execute("""
                SELECT 
                    AVG(quality_score) as avg_score,
                    MIN(quality_score) as min_score,
                    MAX(quality_score) as max_score,
                    COUNT(*) FILTER (WHERE quality_score IS NULL) as null_count
                FROM documents
            """)
            quality_stats = self.cursor.fetchone()
            
            return {
                "total_documents": total,
                "classifications": classifications,
                "processing_statuses": statuses,
                "quality_scores": {
                    "average": float(quality_stats['avg_score']) if quality_stats['avg_score'] else None,
                    "min": float(quality_stats['min_score']) if quality_stats['min_score'] else None,
                    "max": float(quality_stats['max_score']) if quality_stats['max_score'] else None,
                    "null_count": quality_stats['null_count']
                },
                "database": f"{self.host}:{self.port}/{self.database}"
            }
            
        except Exception as e:
            logger.error(f"❌ Statistiken-Abfrage fehlgeschlagen: {e}")
            return {
                "error": str(e)
            }
    
    
    def update_company_metadata(self, document_id: str, company_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update company_metadata JSONB column for a document
        
        This method stores extracted company information from the upload pipeline.
        The company_metadata structure contains:
        - companies: List of extracted companies with register info
        - extraction_timestamp: When the extraction occurred
        - gaps: List of detected data quality gaps
        - verification_skipped: Whether Handelsregister validation was skipped
        
        Args:
            document_id: The document ID to update
            company_metadata: Dictionary with company extraction data
        
        Returns:
            Dict with success status and operation details
        
        Example company_metadata structure:
            {
                "companies": [
                    {
                        "firma": "Beispiel GmbH",
                        "register_number": "HRB 12345",
                        "register_type": "HRB",
                        "register_court": "Amtsgericht München",
                        "verified_in_handelsregister": true,
                        "handelsregister_state": "active",
                        "document_urls": ["https://..."]
                    }
                ],
                "extraction_timestamp": "2025-10-10T10:30:00",
                "gaps": [
                    {
                        "type": "missing_register_number",
                        "firma": "Test AG",
                        "severity": "medium",
                        "message": "..."
                    }
                ],
                "verification_skipped": false
            }
        """
        self.connect()
        
        try:
            import json
            
            # Convert dict to JSON string
            metadata_json = json.dumps(company_metadata, ensure_ascii=False)
            
            # Update company_metadata column
            self.cursor.execute("""
                UPDATE documents 
                SET company_metadata = %s::jsonb
                WHERE document_id = %s
            """, (metadata_json, document_id))
            
            rows_updated = self.cursor.rowcount
            self.conn.commit()
            
            if rows_updated == 0:
                logger.warning(f"⚠️ No document found with ID {document_id}")
                return {
                    "success": False,
                    "error": f"Document {document_id} not found",
                    "rows_updated": 0
                }
            
            logger.info(f"✅ Company metadata updated for document {document_id}")
            
            # Extract statistics from metadata
            companies_count = len(company_metadata.get("companies", []))
            gaps_count = len(company_metadata.get("gaps", []))
            verification_skipped = company_metadata.get("verification_skipped", False)
            
            return {
                "success": True,
                "rows_updated": rows_updated,
                "document_id": document_id,
                "companies_stored": companies_count,
                "gaps_detected": gaps_count,
                "verification_skipped": verification_skipped,
                "database": f"{self.host}:{self.port}/{self.database}"
            }
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Company metadata update failed for {document_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
    
    
    def get_company_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve company_metadata for a document
        
        Args:
            document_id: The document ID to query
        
        Returns:
            Dict with company metadata or None if not found/empty
        """
        self.connect()
        
        try:
            self.cursor.execute("""
                SELECT company_metadata 
                FROM documents 
                WHERE document_id = %s
            """, (document_id,))
            
            result = self.cursor.fetchone()
            
            if result and result['company_metadata']:
                return result['company_metadata']
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve company metadata for {document_id}: {e}")
            return None
    
    
    def search_documents_by_company(self, firma: str, exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        Search documents containing a specific company
        
        Uses JSONB operators for efficient querying:
        - @> (contains): Check if company exists in metadata
        - ->> (get text): Extract firma field for pattern matching
        
        Args:
            firma: Company name to search for
            exact_match: If True, require exact match; if False, use ILIKE pattern
        
        Returns:
            List of documents with matching companies
        
        Example:
            # Find all documents mentioning "Beispiel GmbH"
            docs = backend.search_documents_by_company("Beispiel GmbH")
            
            # Pattern matching (case-insensitive)
            docs = backend.search_documents_by_company("Beispiel%", exact_match=False)
        """
        self.connect()
        
        try:
            if exact_match:
                # Exact match using JSONB contains operator
                self.cursor.execute("""
                    SELECT document_id, file_path, classification, company_metadata
                    FROM documents
                    WHERE company_metadata @> %s::jsonb
                """, (f'{{"companies": [{{"firma": "{firma}"}}]}}',))
            else:
                # Pattern matching using JSONB array elements
                self.cursor.execute("""
                    SELECT DISTINCT d.document_id, d.file_path, d.classification, d.company_metadata
                    FROM documents d,
                         jsonb_array_elements(d.company_metadata->'companies') AS company
                    WHERE company->>'firma' ILIKE %s
                """, (f"%{firma}%",))
            
            results = self.cursor.fetchall()
            
            logger.info(f"Found {len(results)} documents with company '{firma}'")
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Company search failed for '{firma}': {e}")
            return []
    
    
    def get_company_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about extracted companies across all documents
        
        Returns:
            Dict with company extraction statistics:
            - total_documents_with_companies: Documents with company_metadata
            - total_companies_extracted: Total number of companies
            - total_gaps_detected: Total number of gaps
            - verification_skip_rate: Percentage of documents with skipped verification
            - top_companies: Most frequently mentioned companies
        """
        self.connect()
        
        try:
            # Documents with company metadata
            self.cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE company_metadata IS NOT NULL) as docs_with_companies,
                    COUNT(*) as total_docs
                FROM documents
            """)
            doc_stats = self.cursor.fetchone()
            
            # Total companies and gaps
            self.cursor.execute("""
                SELECT 
                    SUM(jsonb_array_length(company_metadata->'companies')) as total_companies,
                    SUM(jsonb_array_length(company_metadata->'gaps')) as total_gaps
                FROM documents
                WHERE company_metadata IS NOT NULL
            """)
            company_stats = self.cursor.fetchone()
            
            # Verification skip rate
            self.cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE (company_metadata->>'verification_skipped')::boolean = true) as skipped,
                    COUNT(*) as total
                FROM documents
                WHERE company_metadata IS NOT NULL
            """)
            verification_stats = self.cursor.fetchone()
            
            # Top 10 most mentioned companies
            self.cursor.execute("""
                SELECT 
                    company->>'firma' as firma,
                    COUNT(*) as mention_count
                FROM documents,
                     jsonb_array_elements(company_metadata->'companies') AS company
                WHERE company_metadata IS NOT NULL
                GROUP BY company->>'firma'
                ORDER BY mention_count DESC
                LIMIT 10
            """)
            top_companies = [{"firma": row['firma'], "count": row['mention_count']} 
                           for row in self.cursor.fetchall()]
            
            return {
                "total_documents": doc_stats['total_docs'],
                "documents_with_companies": doc_stats['docs_with_companies'],
                "total_companies_extracted": int(company_stats['total_companies']) if company_stats['total_companies'] else 0,
                "total_gaps_detected": int(company_stats['total_gaps']) if company_stats['total_gaps'] else 0,
                "verification_skipped_count": verification_stats['skipped'],
                "verification_skip_rate": round(verification_stats['skipped'] / verification_stats['total'] * 100, 2) if verification_stats['total'] > 0 else 0,
                "top_companies": top_companies,
                "database": f"{self.host}:{self.port}/{self.database}"
            }
            
        except Exception as e:
            logger.error(f"❌ Company statistics query failed: {e}")
            return {
                "error": str(e)
            }
    
    def __enter__(self):
        """Context Manager Entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit"""
        if exc_type is not None:
            # Rollback bei Fehler
            try:
                if self.conn and not self.conn.closed:
                    self.conn.rollback()
                    logger.debug("PostgreSQL Rollback durchgeführt")
            except Exception as e:
                logger.warning(f"Rollback-Warnung: {e}")
        else:
            # Commit bei Erfolg
            try:
                if self.conn and not self.conn.closed:
                    self.conn.commit()
                    logger.debug("PostgreSQL Commit durchgeführt")
            except Exception as e:
                logger.warning(f"Commit-Warnung: {e}")
        
        self.disconnect()
        return False  # Don't suppress exceptions


# Factory Function (analog zu anderen Backends)
def create_postgresql_backend(config: Dict[str, Any]) -> PostgreSQLRelationalBackend:
    """
    Erstellt PostgreSQL Backend
    
    Args:
        config: PostgreSQL Konfiguration
        
    Returns:
        PostgreSQLRelationalBackend Instance
    """
    return PostgreSQLRelationalBackend(config)
