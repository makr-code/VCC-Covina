#!/usr/bin/env python3
"""
UDS3 Document Classification Integration für Ingestion Pipeline

Erweitert den FileDiscoveryService um intelligente Dokumentklassifikation
für DSGVO-konforme und automatisierte Sensitivitätserkennung.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# UDS3 Document Classifier Import
try:
    import sys
    import os
    # Add UDS3 path for imports
    uds3_path = os.path.join(os.path.dirname(__file__), '..', 'uds3')
    if uds3_path not in sys.path:
        sys.path.insert(0, uds3_path)
    
    from uds3_document_classifier import UDS3DocumentClassifier
    from uds3_admin_types import AdminDocumentType, AdminLevel, AdminDomain
    UDS3_CLASSIFIER_AVAILABLE = True
except ImportError:
    UDS3_CLASSIFIER_AVAILABLE = False
    UDS3DocumentClassifier = None

# DSGVO Core Import für Sensitivity Detection
try:
    from uds3_dsgvo_core import UDS3DSGVOCore, PIIType, DSGVOProcessingBasis
    DSGVO_CORE_AVAILABLE = True
except ImportError:
    DSGVO_CORE_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentSensitivityLevel:
    """DSGVO-basierte Sensitivitätsstufen für Dokumente"""
    PUBLIC = "public"                    # Keine PII, öffentlich verfügbar
    INTERNAL = "internal"                # Betriebsinterne Daten, begrenzt PII
    CONFIDENTIAL = "confidential"        # Personenbezogene Daten vorhanden
    RESTRICTED = "restricted"            # Sensible PII, strenge Kontrollen
    SECRET = "secret"                    # Hochsensible/Verschlusssachen


class UDS3DocumentClassificationService:
    """
    Intelligente Dokumentklassifikation mit DSGVO-Compliance für Ingestion Pipeline.
    
    Features:
    - Automatische Dokumenttyp-Erkennung (UDS3 Admin Types)
    - PII-basierte Sensitivitätsbewertung (DSGVO-konform)
    - Compliance-Metadaten für automatische Policy-Anwendung
    - Integration in File Discovery Pipeline
    """
    
    def __init__(
        self,
        dsgvo_core: Optional['UDS3DSGVOCore'] = None,
        enable_content_analysis: bool = True,
        min_confidence_threshold: float = 0.7
    ):
        self.enable_content_analysis = enable_content_analysis
        self.min_confidence_threshold = min_confidence_threshold
        
        # Initialize UDS3 Document Classifier
        if UDS3_CLASSIFIER_AVAILABLE:
            self.document_classifier = UDS3DocumentClassifier()
            logger.info("[OK] UDS3 Document Classifier initialized")
        else:
            self.document_classifier = None
            logger.warning("[WARN] UDS3 Document Classifier nicht verfügbar")
        
        # Initialize DSGVO Core für PII Detection
        self.dsgvo_core = dsgvo_core
        if dsgvo_core and DSGVO_CORE_AVAILABLE:
            logger.info("[OK] DSGVO Core für Sensitivity Analysis verfügbar")
        else:
            logger.warning("[WARN] DSGVO Core nicht verfügbar - eingeschränkte Sensitivity Analysis")
    
    def classify_file(
        self, 
        file_path: Path, 
        file_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Klassifiziert eine Datei mit UDS3 Standards und DSGVO-Compliance.
        
        Args:
            file_path: Pfad zur zu klassifizierenden Datei
            file_content: Optional bereits gelesener Dateiinhalt
            
        Returns:
            Dict mit Klassifikationsergebnissen und Compliance-Metadaten
        """
        classification_result = {
            'file_path': str(file_path),
            'filename': file_path.name,
            'file_extension': file_path.suffix.lower(),
            'classification_timestamp': None,
            'uds3_classification': None,
            'sensitivity_analysis': None,
            'compliance_metadata': {},
            'processing_recommendations': {}
        }
        
        try:
            # 1. Grundlegende Dateierkennung
            basic_category = self._classify_file_type(file_path)
            classification_result['basic_category'] = basic_category
            
            # 2. Content-basierte UDS3-Klassifikation
            if self.enable_content_analysis and file_content:
                classification_result['uds3_classification'] = self._classify_with_uds3(
                    content=file_content,
                    filename=file_path.name
                )
            else:
                # Fallback: Dateiname-basierte Klassifikation für PDFs ohne Content
                classification_result['uds3_classification'] = self._classify_filename_only(file_path.name)
                
            # 3. DSGVO-Sensitivity Analysis
            classification_result['sensitivity_analysis'] = self._analyze_sensitivity(
                content=file_content or "",
                document_type=classification_result['uds3_classification']
            )
            
            # 4. Compliance-Metadaten generieren
            classification_result['compliance_metadata'] = self._generate_compliance_metadata(
                classification_result
            )
            
            # 5. Processing-Empfehlungen
            classification_result['processing_recommendations'] = self._generate_processing_recommendations(
                classification_result
            )
            
            # Timestamp setzen
            from datetime import datetime
            classification_result['classification_timestamp'] = datetime.now().isoformat()
            
            logger.debug(f"Klassifikation abgeschlossen für {file_path.name}")
            return classification_result
            
        except Exception as e:
            logger.error(f"Fehler bei Dokumentklassifikation für {file_path}: {e}")
            return self._fallback_classification(file_path, str(e))
    
    def _classify_file_type(self, file_path: Path) -> str:
        """Grundlegende Dateityp-Klassifikation basierend auf Extension"""
        extension = file_path.suffix.lower()
        
        if extension in {'.pdf', '.doc', '.docx', '.odt'}:
            return 'document'
        elif extension in {'.txt', '.md', '.rtf'}:
            return 'text'
        elif extension in {'.xls', '.xlsx', '.csv', '.ods'}:
            return 'spreadsheet'
        elif extension in {'.ppt', '.pptx', '.odp'}:
            return 'presentation'
        elif extension in {'.jpg', '.jpeg', '.png', '.tiff', '.pdf'}:
            return 'image_or_scan'
        elif extension in {'.xml', '.json', '.yaml'}:
            return 'structured_data'
        else:
            return 'other'
    
    def _classify_with_uds3(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """UDS3-basierte Dokumentklassifikation"""
        if not self.document_classifier:
            return None
        
        try:
            # UDS3 Klassifikation durchführen
            uds3_result = self.document_classifier.classify_document(
                text_content=content,
                filename=filename
            )
            
            # Confidence Check
            if uds3_result.get('confidence_score', 0) < self.min_confidence_threshold:
                logger.warning(f"Niedrige Confidence für {filename}: {uds3_result.get('confidence_score', 0)}")
            
            # Enum Values zu String konvertieren für JSON-Serialisierung
            result = {
                'document_type': uds3_result['document_type'].value if hasattr(uds3_result['document_type'], 'value') else str(uds3_result['document_type']),
                'admin_level': uds3_result['admin_level'].value if hasattr(uds3_result['admin_level'], 'value') else str(uds3_result['admin_level']),
                'admin_domain': uds3_result['admin_domain'].value if hasattr(uds3_result['admin_domain'], 'value') else str(uds3_result['admin_domain']),
                'procedure_stage': uds3_result['procedure_stage'].value if hasattr(uds3_result['procedure_stage'], 'value') else str(uds3_result['procedure_stage']),
                'confidence_score': uds3_result['confidence_score'],
                'classification_metadata': uds3_result.get('classification_metadata', {}),
                'classification_source': uds3_result.get('classification_source', 'uds3_classifier')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"UDS3 Klassifikation fehlgeschlagen für {filename}: {e}")
            return None
    
    def _classify_filename_only(self, filename: str) -> Dict[str, Any]:
        """Fallback-Klassifikation basierend nur auf Dateiname"""
        filename_lower = filename.lower()
        
        # Pattern-basierte Erkennung deutscher Gesetze
        if any(pattern in filename_lower for pattern in ['gesetz', 'g.pdf', 'gg.pdf']):
            doc_type = 'LAW'
            confidence = 0.8
        elif any(pattern in filename_lower for pattern in ['verordnung', 'vo.pdf', 'v.pdf']):
            doc_type = 'REGULATION'  
            confidence = 0.7
        elif any(pattern in filename_lower for pattern in ['bescheid', 'genehmigung']):
            doc_type = 'PERMIT'
            confidence = 0.6
        else:
            doc_type = 'FILE_NOTE'
            confidence = 0.3
            
        return {
            'document_type': doc_type,
            'admin_level': 'FEDERAL',  # Default für deutsche Gesetze
            'admin_domain': 'GENERAL_ADMIN',
            'procedure_stage': 'FINAL',
            'confidence_score': confidence,
            'classification_metadata': {'method': 'filename_pattern'},
            'classification_source': 'filename_fallback'
        }
    
    def _analyze_sensitivity(
        self, 
        content: str, 
        document_type: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """DSGVO-basierte Sensitivitätsanalyse"""
        sensitivity_result = {
            'sensitivity_level': DocumentSensitivityLevel.PUBLIC,
            'pii_detected': False,
            'pii_elements': [],
            'processing_basis_recommendation': DSGVOProcessingBasis.PUBLIC_TASK.value,
            'retention_recommendation_years': 7,
            'access_control_recommendation': 'public'
        }
        
        if not self.dsgvo_core or not DSGVO_CORE_AVAILABLE:
            # Fallback: Pattern-basierte PII Detection
            return self._fallback_sensitivity_analysis(content, document_type)
        
        try:
            # PII Detection über DSGVO Core
            detected_pii = self.dsgvo_core.detect_pii(content)
            
            if detected_pii:
                sensitivity_result['pii_detected'] = True
                sensitivity_result['pii_elements'] = detected_pii
                
                # Sensitivität basierend auf PII-Typen bestimmen
                pii_types = {pii['type'] for pii in detected_pii}
                
                if any(pii_type in {'health', 'biometric', 'financial'} for pii_type in pii_types):
                    sensitivity_result['sensitivity_level'] = DocumentSensitivityLevel.RESTRICTED
                    sensitivity_result['processing_basis_recommendation'] = DSGVOProcessingBasis.CONSENT.value
                    sensitivity_result['access_control_recommendation'] = 'restricted'
                elif any(pii_type in {'email', 'phone', 'name'} for pii_type in pii_types):
                    sensitivity_result['sensitivity_level'] = DocumentSensitivityLevel.CONFIDENTIAL
                    sensitivity_result['processing_basis_recommendation'] = DSGVOProcessingBasis.LEGAL_OBLIGATION.value
                    sensitivity_result['access_control_recommendation'] = 'confidential'
                else:
                    sensitivity_result['sensitivity_level'] = DocumentSensitivityLevel.INTERNAL
                    sensitivity_result['access_control_recommendation'] = 'internal'
            
            # Dokumenttyp-spezifische Sensitivitätsanpassung
            if document_type:
                doc_type = document_type.get('document_type', '')
                if doc_type in ['court_decision', 'enforcement_order', 'disciplinary_action']:
                    # Gerichtsentscheidungen sind oft öffentlich, aber können PII enthalten
                    if not detected_pii:
                        sensitivity_result['sensitivity_level'] = DocumentSensitivityLevel.PUBLIC
                        sensitivity_result['access_control_recommendation'] = 'public'
                elif doc_type in ['internal_memo', 'draft_decision', 'meeting_minutes']:
                    # Interne Dokumente mindestens internal
                    if sensitivity_result['sensitivity_level'] == DocumentSensitivityLevel.PUBLIC:
                        sensitivity_result['sensitivity_level'] = DocumentSensitivityLevel.INTERNAL
                        sensitivity_result['access_control_recommendation'] = 'internal'
        
        except Exception as e:
            logger.error(f"DSGVO Sensitivity Analysis fehlgeschlagen: {e}")
            return self._fallback_sensitivity_analysis(content, document_type)
        
        return sensitivity_result
    
    def _fallback_sensitivity_analysis(self, content: str, document_type: Optional[Dict]) -> Dict[str, Any]:
        """Fallback Pattern-basierte Sensitivitätsanalyse"""
        import re
        
        # Einfache Pattern für PII-Erkennung
        pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(\+49|0)\s*\d+[\s\-\d]+\b',
            'name': r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'  # Sehr einfach
        }
        
        detected_pii = []
        for pii_type, pattern in pii_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                detected_pii.extend([{'type': pii_type, 'count': len(matches)}])
        
        if detected_pii:
            return {
                'sensitivity_level': DocumentSensitivityLevel.CONFIDENTIAL,
                'pii_detected': True,
                'pii_elements': detected_pii,
                'processing_basis_recommendation': DSGVOProcessingBasis.LEGAL_OBLIGATION.value,
                'access_control_recommendation': 'confidential',
                'note': 'Fallback pattern-based analysis'
            }
        else:
            return {
                'sensitivity_level': DocumentSensitivityLevel.PUBLIC,
                'pii_detected': False,
                'pii_elements': [],
                'processing_basis_recommendation': DSGVOProcessingBasis.PUBLIC_TASK.value,
                'access_control_recommendation': 'public',
                'note': 'Fallback pattern-based analysis'
            }
    
    def _generate_compliance_metadata(self, classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generiert DSGVO-Compliance-Metadaten für automatische Policy-Anwendung"""
        compliance_metadata = {
            'gdpr_relevant': False,
            'requires_consent': False,
            'requires_anonymization': False,
            'retention_policy': '7_years_standard',
            'access_logging_required': False,
            'encryption_required': False
        }
        
        sensitivity = classification_result.get('sensitivity_analysis', {})
        
        if sensitivity.get('pii_detected', False):
            compliance_metadata['gdpr_relevant'] = True
            compliance_metadata['access_logging_required'] = True
            
            sensitivity_level = sensitivity.get('sensitivity_level', DocumentSensitivityLevel.PUBLIC)
            
            if sensitivity_level == DocumentSensitivityLevel.RESTRICTED:
                compliance_metadata['requires_consent'] = True
                compliance_metadata['requires_anonymization'] = True
                compliance_metadata['encryption_required'] = True
                compliance_metadata['retention_policy'] = '3_years_restricted'
            elif sensitivity_level == DocumentSensitivityLevel.CONFIDENTIAL:
                compliance_metadata['requires_anonymization'] = True
                compliance_metadata['encryption_required'] = True
        
        return compliance_metadata
    
    def _generate_processing_recommendations(self, classification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generiert Verarbeitungsempfehlungen für Pipeline"""
        recommendations = {
            'chunking_strategy': 'standard',
            'vectorization_priority': 'normal',
            'graph_extraction': True,
            'anonymize_before_storage': False,
            'skip_llm_enrichment': False,
            'manual_review_required': False
        }
        
        # UDS3-Klassifikation-basierte Empfehlungen
        uds3_class = classification_result.get('uds3_classification')
        if uds3_class:
            doc_type = uds3_class.get('document_type', '')
            confidence = uds3_class.get('confidence_score', 0)
            
            # Niedrige Confidence -> Manual Review
            if confidence < self.min_confidence_threshold:
                recommendations['manual_review_required'] = True
            
            # Dokumenttyp-spezifische Empfehlungen
            if doc_type in ['law', 'regulation', 'directive']:
                recommendations['chunking_strategy'] = 'section_based'
                recommendations['vectorization_priority'] = 'high'
                recommendations['graph_extraction'] = True
            elif doc_type in ['court_decision', 'permit', 'enforcement_order']:
                recommendations['chunking_strategy'] = 'decision_based'
                recommendations['graph_extraction'] = True
            elif doc_type in ['internal_memo', 'meeting_minutes']:
                recommendations['vectorization_priority'] = 'low'
        
        # Sensitivität-basierte Empfehlungen
        sensitivity = classification_result.get('sensitivity_analysis', {})
        if sensitivity.get('pii_detected', False):
            recommendations['anonymize_before_storage'] = True
            
            sensitivity_level = sensitivity.get('sensitivity_level', DocumentSensitivityLevel.PUBLIC)
            if sensitivity_level in [DocumentSensitivityLevel.RESTRICTED, DocumentSensitivityLevel.SECRET]:
                recommendations['skip_llm_enrichment'] = True  # Kein LLM für hochsensible Daten
        
        return recommendations
    
    def _fallback_classification(self, file_path: Path, error: str) -> Dict[str, Any]:
        """Fallback-Klassifikation bei Fehlern"""
        return {
            'file_path': str(file_path),
            'filename': file_path.name,
            'file_extension': file_path.suffix.lower(),
            'classification_timestamp': None,
            'uds3_classification': None,
            'sensitivity_analysis': {
                'sensitivity_level': DocumentSensitivityLevel.INTERNAL,  # Sicher fallback
                'pii_detected': False,
                'note': 'Fallback classification due to error'
            },
            'compliance_metadata': {
                'gdpr_relevant': True,  # Sicher fallback
                'access_logging_required': True
            },
            'processing_recommendations': {
                'manual_review_required': True  # Bei Fehlern -> Manual Review
            },
            'classification_error': error
        }