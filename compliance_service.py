"""
Compliance Service for Covina Backend
=====================================

Provides compliance checking functionality including DSGVO/GDPR validation.

Created: 17. Oktober 2025
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Compliance checking service for documents.
    
    Provides:
    - DSGVO/GDPR compliance checks
    - PII (Personally Identifiable Information) detection
    - Regulatory compliance validation
    """
    
    # PII Patterns (German context)
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+49|0)[1-9]\d{1,14}\b',
        'iban': r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b',
        'tax_id': r'\b\d{11}\b',  # Steuer-ID
        'social_security': r'\b\d{12}\b',  # Sozialversicherungsnummer
    }
    
    # DSGVO relevant keywords
    DSGVO_KEYWORDS = [
        'personenbezogen', 'datenschutz', 'einwilligung', 'verarbeitung',
        'betroffene', 'widerruf', 'auskunft', 'löschung', 'sperrung'
    ]
    
    def __init__(self, postgres_backend=None):
        """Initialize Compliance Service"""
        self.postgres_backend = postgres_backend
        logger.info("ComplianceService initialized")
    
    def check_document(
        self, 
        document_id: str, 
        content: Optional[str] = None,
        check_type: str = "dsgvo"
    ) -> Dict[str, Any]:
        """
        Perform compliance check on document.
        
        Args:
            document_id: Document identifier
            content: Document content (optional, will fetch from DB if not provided)
            check_type: Type of check (dsgvo, gdpr, regulatory)
        
        Returns:
            Compliance check result dictionary
        """
        try:
            # If content not provided, try to fetch from database
            if not content and self.postgres_backend:
                content = self._fetch_document_content(document_id)
            
            if not content:
                return {
                    'document_id': document_id,
                    'check_type': check_type,
                    'status': 'error',
                    'message': 'Document content not available',
                    'findings': [],
                    'risk_level': 'unknown'
                }
            
            # Perform checks based on type
            if check_type == 'dsgvo' or check_type == 'gdpr':
                return self._check_dsgvo(document_id, content)
            elif check_type == 'regulatory':
                return self._check_regulatory(document_id, content)
            else:
                return self._check_general(document_id, content)
                
        except Exception as e:
            logger.error(f"Error checking document {document_id}: {e}")
            return {
                'document_id': document_id,
                'check_type': check_type,
                'status': 'error',
                'message': str(e),
                'findings': [],
                'risk_level': 'unknown'
            }
    
    def _check_dsgvo(self, document_id: str, content: str) -> Dict[str, Any]:
        """
        Perform DSGVO/GDPR compliance check.
        
        Checks for:
        - PII (Personally Identifiable Information)
        - DSGVO-relevant keywords
        - Data processing consent indicators
        """
        findings = []
        risk_level = 'low'
        
        # Check for PII
        pii_found = {}
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                pii_found[pii_type] = len(matches)
                findings.append(f"{pii_type.upper()} detected: {len(matches)} occurrences")
        
        # Check for DSGVO keywords
        dsgvo_keywords_found = []
        for keyword in self.DSGVO_KEYWORDS:
            if keyword.lower() in content.lower():
                dsgvo_keywords_found.append(keyword)
        
        if dsgvo_keywords_found:
            findings.append(f"DSGVO keywords found: {', '.join(dsgvo_keywords_found)}")
        
        # Determine risk level
        if pii_found:
            if len(pii_found) > 3 or any(count > 10 for count in pii_found.values()):
                risk_level = 'high'
            elif len(pii_found) > 1:
                risk_level = 'medium'
            else:
                risk_level = 'low'
        
        # Check for consent indicators
        consent_keywords = ['einwilligung', 'zustimmung', 'consent']
        has_consent = any(kw in content.lower() for kw in consent_keywords)
        
        if pii_found and not has_consent:
            findings.append("WARNING: PII found without explicit consent indicator")
            risk_level = 'high' if risk_level != 'critical' else 'critical'
        
        status = 'compliant' if risk_level == 'low' else 'review_required'
        
        return {
            'document_id': document_id,
            'check_type': 'dsgvo',
            'status': status,
            'findings': findings,
            'risk_level': risk_level,
            'pii_detected': pii_found,
            'dsgvo_keywords': dsgvo_keywords_found,
            'has_consent_indicator': has_consent,
            'checked_at': datetime.now().isoformat()
        }
    
    def _check_regulatory(self, document_id: str, content: str) -> Dict[str, Any]:
        """
        Perform regulatory compliance check.
        
        Placeholder for future regulatory checks (GoBD, etc.)
        """
        return {
            'document_id': document_id,
            'check_type': 'regulatory',
            'status': 'not_implemented',
            'findings': ['Regulatory checks not yet implemented'],
            'risk_level': 'unknown',
            'checked_at': datetime.now().isoformat()
        }
    
    def _check_general(self, document_id: str, content: str) -> Dict[str, Any]:
        """
        Perform general compliance check.
        """
        return {
            'document_id': document_id,
            'check_type': 'general',
            'status': 'completed',
            'findings': [],
            'risk_level': 'low',
            'checked_at': datetime.now().isoformat()
        }
    
    def _fetch_document_content(self, document_id: str) -> Optional[str]:
        """
        Fetch document content from database.
        
        Args:
            document_id: Document identifier
        
        Returns:
            Document content or None
        """
        try:
            if not self.postgres_backend:
                return None
            
            self.postgres_backend.connect()
            
            query = "SELECT content FROM documents WHERE document_id = %s"
            self.postgres_backend.cursor.execute(query, (document_id,))
            result = self.postgres_backend.cursor.fetchone()
            
            if result and result[0]:
                return result[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching document {document_id}: {e}")
            return None
    
    def get_dsgvo_status(self, document_id: str) -> Dict[str, Any]:
        """
        Get DSGVO compliance status for a document.
        
        Args:
            document_id: Document identifier
        
        Returns:
            DSGVO status dictionary
        """
        try:
            if not self.postgres_backend:
                return {
                    'document_id': document_id,
                    'dsgvo_compliant': None,
                    'status': 'unavailable',
                    'message': 'Database not available'
                }
            
            # Fetch document and check compliance
            content = self._fetch_document_content(document_id)
            
            if not content:
                return {
                    'document_id': document_id,
                    'dsgvo_compliant': None,
                    'status': 'not_found',
                    'message': 'Document not found or has no content'
                }
            
            # Perform DSGVO check
            check_result = self._check_dsgvo(document_id, content)
            
            # Determine compliance status
            is_compliant = (
                check_result['risk_level'] in ['low', 'medium'] and
                check_result['status'] == 'compliant'
            )
            
            return {
                'document_id': document_id,
                'dsgvo_compliant': is_compliant,
                'status': check_result['status'],
                'risk_level': check_result['risk_level'],
                'pii_detected': check_result.get('pii_detected', {}),
                'has_consent': check_result.get('has_consent_indicator', False),
                'findings': check_result.get('findings', []),
                'checked_at': check_result.get('checked_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting DSGVO status for {document_id}: {e}")
            return {
                'document_id': document_id,
                'dsgvo_compliant': None,
                'status': 'error',
                'message': str(e)
            }
    
    def list_checks(
        self, 
        check_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List compliance checks.
        
        Note: This would typically query from a compliance_checks table.
        For now, returns empty list as placeholder.
        
        Args:
            check_type: Filter by check type
            status: Filter by status
            limit: Maximum results
        
        Returns:
            List of compliance check records
        """
        # TODO: Implement actual database query when compliance_checks table exists
        logger.info(f"list_checks called: type={check_type}, status={status}, limit={limit}")
        return []


# Singleton instance
_compliance_service_instance = None


def get_compliance_service(postgres_backend=None):
    """
    Get or create ComplianceService singleton instance.
    
    Args:
        postgres_backend: PostgreSQL backend instance
    
    Returns:
        ComplianceService instance
    """
    global _compliance_service_instance
    
    if _compliance_service_instance is None:
        _compliance_service_instance = ComplianceService(postgres_backend)
    
    return _compliance_service_instance
