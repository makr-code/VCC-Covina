# -*- coding: utf-8 -*-
"""
VPB Process Mining Engine

Open-Source Process Mining specifically designed for VPB (Visual Process Builder) 
German Administrative Processes. Based on PM4Py framework with VPB-specific 
adaptations for legal compliance and administrative workflows.

This module provides:
- VPB-XML/JSON process analysis
- German administrative process pattern recognition  
- Legal compliance gap detection
- Process efficiency analysis
- Administrative workflow optimization recommendations

Author: Covina Team
License: AGPL-3.0
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

try:
    import pm4py
    from pm4py.objects.log.importer.xes import importer as xes_importer
    from pm4py.objects.conversion.log import converter as log_converter
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
    from pm4py.objects.petri_net.exporter import exporter as pnml_exporter
    from pm4py.visualization.petri_net import visualizer as pn_visualizer
    PM4PY_AVAILABLE = True
except ImportError:
    PM4PY_AVAILABLE = False
    logging.warning("PM4Py not available. Process mining functionality will be limited.")

logger = logging.getLogger(__name__)

class VPBProcessMiner:
    """
    VPB-specific Process Mining Engine
    
    Analyzes VPB process definitions (XML/JSON) to discover:
    - Administrative workflow patterns
    - Legal compliance gaps
    - Process efficiency bottlenecks
    - Missing legal checkpoints
    - Authority jurisdiction issues
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize VPB Process Miner with configuration"""
        self.config = config or {}
        self.processes = []
        self.event_logs = []
        self.process_models = {}
        
        # VPB-specific element types
        self.vpb_element_types = {
            'START_EVENT', 'END_EVENT', 'INTERMEDIATE_EVENT',
            'FUNCTION', 'LEGAL_CHECKPOINT', 'GATEWAY', 
            'GEO_CONTEXT', 'AUTHORITY_HANDOVER', 'COMPLIANCE_CHECK',
            'CITIZEN_INTERACTION', 'DOCUMENT_CHECK', 'DECISION_POINT'
        }
        
        # German administrative process patterns
        self.admin_patterns = {
            'ANTRAGSTELLUNG': ['START_EVENT', 'CITIZEN_INTERACTION', 'DOCUMENT_CHECK'],
            'PRUEFUNG': ['LEGAL_CHECKPOINT', 'COMPLIANCE_CHECK', 'GATEWAY'],
            'ENTSCHEIDUNG': ['DECISION_POINT', 'GATEWAY', 'AUTHORITY_HANDOVER'],
            'BESCHEIDUNG': ['FUNCTION', 'CITIZEN_INTERACTION', 'END_EVENT']
        }
        
        # Legal compliance requirements
        self.compliance_requirements = {
            'VWVFG': ['ANTRAGSTELLUNG', 'PRUEFUNG', 'ANHOERUNG', 'BESCHEIDUNG'],
            'BAUO_NRW': ['BAUANTRAG', 'VOLLSTAENDIGKEITSPRUEFUNG', 'MATERIELLE_PRUEFUNG', 'BAUGENEHMIGUNG'],
            'DSGVO': ['DATENSCHUTZPRUEFUNG', 'EINVERSTAENDNIS', 'DATENMINIMIERUNG']
        }
    
    def load_vpb_process(self, file_path: str) -> Dict[str, Any]:
        """
        Load VPB process from XML or JSON file
        
        Args:
            file_path: Path to VPB process file (.vpb.xml or .vpb.json)
            
        Returns:
            Parsed VPB process data
        """
        try:
            if file_path.endswith('.xml') or file_path.endswith('.vpb.xml'):
                return self._load_vpb_xml(file_path)
            elif file_path.endswith('.json') or file_path.endswith('.vpb.json'):
                return self._load_vpb_json(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
        except Exception as e:
            logger.error(f"Failed to load VPB process {file_path}: {e}")
            raise
    
    def _load_vpb_xml(self, file_path: str) -> Dict[str, Any]:
        """Load VPB process from XML format"""
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract VPB process structure
        process_data = {
            'process_id': root.get('processId', ''),
            'version': root.get('version', '1.0'),
            'metadata': {},
            'elements': [],
            'flows': []
        }
        
        # Extract metadata
        metadata_elem = root.find('.//{urn:uds3:vpb:1.0}ProcessMetadata')
        if metadata_elem is not None:
            process_data['metadata'] = {
                'name': self._get_element_text(metadata_elem, 'Name'),
                'legal_context': self._get_element_text(metadata_elem, 'LegalContext'),
                'legal_basis': self._get_element_text(metadata_elem, 'LegalBasis'),
                'responsible_authority': self._get_element_text(metadata_elem, 'ResponsibleAuthority'),
                'target_processing_days': self._get_element_text(metadata_elem, 'TargetProcessingDays')
            }
        
        # Extract process elements
        elements_container = root.find('.//{urn:uds3:vpb:1.0}ProcessElements')
        if elements_container is not None:
            for element in elements_container:
                element_data = self._parse_vpb_element(element)
                if element_data:
                    process_data['elements'].append(element_data)
        
        # Extract process flows
        flows_container = root.find('.//{urn:uds3:vpb:1.0}ProcessFlows')
        if flows_container is not None:
            for flow in flows_container:
                flow_data = self._parse_vpb_flow(flow)
                if flow_data:
                    process_data['flows'].append(flow_data)
        
        self.processes.append(process_data)
        return process_data
    
    def _load_vpb_json(self, file_path: str) -> Dict[str, Any]:
        """Load VPB process from JSON format"""
        with open(file_path, 'r', encoding='utf-8') as f:
            process_data = json.load(f)
        
        self.processes.append(process_data)
        return process_data
    
    def _get_element_text(self, parent, tag_name):
        """Extract text from XML element with namespace handling"""
        element = parent.find(f'.//{{{parent.nsmap.get("vpb", "urn:uds3:vpb:1.0")}}}{tag_name}')
        return element.text if element is not None else ''
    
    def _parse_vpb_element(self, element) -> Optional[Dict]:
        """Parse VPB process element from XML"""
        element_data = {
            'element_id': element.get('elementId', ''),
            'element_type': element.tag.split('}')[-1].upper(),  # Remove namespace
            'name': '',
            'x': int(element.get('x', 0)),
            'y': int(element.get('y', 0)),
            'properties': {}
        }
        
        # Extract element-specific properties
        for child in element:
            tag_name = child.tag.split('}')[-1]
            if tag_name == 'Name':
                element_data['name'] = child.text or ''
            elif tag_name == 'Description':
                element_data['properties']['description'] = child.text or ''
            elif tag_name == 'LegalBasis':
                element_data['properties']['legal_basis'] = child.text or ''
            elif tag_name == 'ResponsibleAuthority':
                element_data['properties']['responsible_authority'] = child.text or ''
            elif tag_name == 'DeadlineDays':
                element_data['properties']['deadline_days'] = int(child.text or 0)
            elif tag_name == 'GeoRelevance':
                element_data['properties']['geo_relevance'] = child.text.lower() == 'true'
        
        return element_data
    
    def _parse_vpb_flow(self, flow) -> Optional[Dict]:
        """Parse VPB process flow from XML"""
        return {
            'flow_id': flow.get('flowId', ''),
            'source_ref': flow.get('sourceRef', ''),
            'target_ref': flow.get('targetRef', ''),
            'flow_type': flow.get('type', 'SEQUENCE'),
            'description': flow.find('.//Description').text if flow.find('.//Description') is not None else ''
        }
    
    def convert_to_event_log(self, process_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert VPB process to PM4Py-compatible event log format
        
        Args:
            process_data: VPB process data
            
        Returns:
            Event log as pandas DataFrame
        """
        events = []
        case_id = process_data.get('process_id', 'case_1')
        
        # Create synthetic event log from process structure
        for i, element in enumerate(process_data.get('elements', [])):
            event = {
                'case:concept:name': case_id,
                'concept:name': element.get('name', element.get('element_id', f'activity_{i}')),
                'time:timestamp': datetime.now() + timedelta(hours=i),
                'lifecycle:transition': 'complete',
                'element_type': element.get('element_type', 'FUNCTION'),
                'element_id': element.get('element_id', ''),
                'responsible_authority': element.get('properties', {}).get('responsible_authority', ''),
                'legal_basis': element.get('properties', {}).get('legal_basis', ''),
                'deadline_days': element.get('properties', {}).get('deadline_days', 0)
            }
            events.append(event)
        
        event_log = pd.DataFrame(events)
        self.event_logs.append(event_log)
        return event_log
    
    def discover_process_model(self, process_data: Dict[str, Any]) -> Optional[Any]:
        """
        Discover process model using PM4Py Inductive Miner
        
        Args:
            process_data: VPB process data
            
        Returns:
            Discovered process model (Petri net)
        """
        if not PM4PY_AVAILABLE:
            logger.warning("PM4Py not available for process discovery")
            return None
        
        try:
            # Convert to event log
            event_log = self.convert_to_event_log(process_data)
            
            # Convert pandas DataFrame to PM4Py log format
            log = log_converter.apply(event_log, parameters={
                log_converter.Variants.TO_EVENT_LOG.value.Parameters.CASE_ID_KEY: 'case:concept:name'
            })
            
            # Discover process model using Inductive Miner
            net, initial_marking, final_marking = inductive_miner.apply(log)
            
            # Store model
            process_id = process_data.get('process_id', 'unknown')
            self.process_models[process_id] = {
                'net': net,
                'initial_marking': initial_marking,
                'final_marking': final_marking,
                'log': log
            }
            
            return net, initial_marking, final_marking
        
        except Exception as e:
            logger.error(f"Process discovery failed: {e}")
            return None
    
    def analyze_process_gaps(self, process_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze VPB process for administrative and legal compliance gaps
        
        Args:
            process_data: VPB process data
            
        Returns:
            Gap analysis results
        """
        gaps = {
            'missing_legal_checkpoints': [],
            'authority_jurisdiction_issues': [],
            'deadline_compliance_risks': [],
            'missing_administrative_patterns': [],
            'process_efficiency_issues': []
        }
        
        elements = process_data.get('elements', [])
        flows = process_data.get('flows', [])
        
        # Check for missing legal checkpoints
        legal_checkpoints = [e for e in elements if e.get('element_type') == 'LEGAL_CHECKPOINT']
        if not legal_checkpoints:
            gaps['missing_legal_checkpoints'].append({
                'severity': 'high',
                'description': 'Kein LEGAL_CHECKPOINT gefunden - Rechtsprüfung fehlt',
                'recommendation': 'Rechtsprüfung nach §66 VwVfG hinzufügen'
            })
        
        # Check for authority jurisdiction
        authorities = set()
        for element in elements:
            auth = element.get('properties', {}).get('responsible_authority')
            if auth:
                authorities.add(auth)
        
        if len(authorities) > 3:
            gaps['authority_jurisdiction_issues'].append({
                'severity': 'medium',
                'description': f'Zu viele Zuständigkeiten ({len(authorities)}) - Kompetenzkonflikt möglich',
                'authorities': list(authorities),
                'recommendation': 'Zuständigkeiten konsolidieren oder Übergabepunkte definieren'
            })
        
        # Check deadline compliance
        deadline_elements = [e for e in elements 
                           if e.get('properties', {}).get('deadline_days', 0) > 0]
        total_deadline_days = sum(e.get('properties', {}).get('deadline_days', 0) 
                                for e in deadline_elements)
        
        target_days = int(process_data.get('metadata', {}).get('target_processing_days', 0))
        if target_days > 0 and total_deadline_days > target_days:
            gaps['deadline_compliance_risks'].append({
                'severity': 'high',
                'description': f'Gesamtdauer ({total_deadline_days} Tage) überschreitet Ziel ({target_days} Tage)',
                'total_days': total_deadline_days,
                'target_days': target_days,
                'recommendation': 'Parallelisierung oder Fristverkürzung erforderlich'
            })
        
        # Check for administrative patterns
        element_types = [e.get('element_type') for e in elements]
        
        # Check ANTRAGSTELLUNG pattern
        if 'START_EVENT' not in element_types or 'CITIZEN_INTERACTION' not in element_types:
            gaps['missing_administrative_patterns'].append({
                'pattern': 'ANTRAGSTELLUNG',
                'severity': 'medium',
                'description': 'Antragstellung-Pattern unvollständig',
                'missing_elements': ['START_EVENT', 'CITIZEN_INTERACTION'],
                'recommendation': 'Bürgerinteraktion und Antragseingangsereignis hinzufügen'
            })
        
        # Check process efficiency
        if len(flows) < len(elements) - 1:
            gaps['process_efficiency_issues'].append({
                'severity': 'low',
                'description': 'Prozessfluss möglicherweise unvollständig',
                'elements_count': len(elements),
                'flows_count': len(flows),
                'recommendation': 'Alle Prozessschritte durch Sequenzflüsse verbinden'
            })
        
        return gaps
    
    def analyze_legal_compliance(self, process_data: Dict[str, Any], 
                               legal_framework: str = 'VWVFG') -> Dict[str, Any]:
        """
        Analyze legal compliance of VPB process
        
        Args:
            process_data: VPB process data
            legal_framework: Legal framework to check against (VWVFG, BAUO_NRW, etc.)
            
        Returns:
            Compliance analysis results
        """
        compliance = {
            'framework': legal_framework,
            'compliance_score': 0.0,
            'required_elements': [],
            'missing_elements': [],
            'compliance_issues': []
        }
        
        required_patterns = self.compliance_requirements.get(legal_framework, [])
        elements = process_data.get('elements', [])
        element_types = [e.get('element_type') for e in elements]
        
        # Check required elements for framework
        if legal_framework == 'VWVFG':
            required_elements = ['START_EVENT', 'LEGAL_CHECKPOINT', 'CITIZEN_INTERACTION', 'END_EVENT']
            compliance['required_elements'] = required_elements
            
            for req_element in required_elements:
                if req_element not in element_types:
                    compliance['missing_elements'].append(req_element)
        
        elif legal_framework == 'BAUO_NRW':
            # Specific requirements for building permit process
            required_elements = ['BAUANTRAG', 'VOLLSTAENDIGKEITSPRUEFUNG', 'MATERIELLE_PRUEFUNG']
            
            # Check for building-specific elements
            has_building_elements = any('BAU' in e.get('name', '').upper() 
                                      for e in elements)
            if not has_building_elements:
                compliance['compliance_issues'].append({
                    'severity': 'high',
                    'description': 'Bauspezifische Elemente fehlen',
                    'recommendation': 'Bauantrag, Vollständigkeitsprüfung, materielle Prüfung hinzufügen'
                })
        
        # Calculate compliance score
        if compliance['required_elements']:
            missing_count = len(compliance['missing_elements'])
            total_count = len(compliance['required_elements'])
            compliance['compliance_score'] = max(0.0, (total_count - missing_count) / total_count)
        
        return compliance
    
    def generate_process_recommendations(self, process_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate improvement recommendations for VPB process
        
        Args:
            process_data: VPB process data
            
        Returns:
            List of improvement recommendations
        """
        recommendations = []
        
        gaps = self.analyze_process_gaps(process_data)
        
        # Generate recommendations based on gaps
        for gap_type, gap_list in gaps.items():
            for gap in gap_list:
                recommendation = {
                    'type': gap_type,
                    'priority': gap.get('severity', 'low'),
                    'title': gap.get('description', ''),
                    'action': gap.get('recommendation', ''),
                    'estimated_effort': self._estimate_effort(gap_type, gap.get('severity', 'low'))
                }
                recommendations.append(recommendation)
        
        return recommendations
    
    def _estimate_effort(self, gap_type: str, severity: str) -> str:
        """Estimate implementation effort for gap resolution"""
        effort_matrix = {
            'high': {'missing_legal_checkpoints': 'medium', 'deadline_compliance_risks': 'high'},
            'medium': {'authority_jurisdiction_issues': 'medium', 'missing_administrative_patterns': 'low'},
            'low': {'process_efficiency_issues': 'low'}
        }
        
        return effort_matrix.get(severity, {}).get(gap_type, 'medium')
    
    def export_analysis_results(self, output_file: str, 
                               process_data: Dict[str, Any]) -> bool:
        """
        Export process analysis results to JSON file
        
        Args:
            output_file: Output file path
            process_data: VPB process data
            
        Returns:
            Success status
        """
        try:
            gaps = self.analyze_process_gaps(process_data)
            compliance = self.analyze_legal_compliance(process_data)
            recommendations = self.generate_process_recommendations(process_data)
            
            results = {
                'process_id': process_data.get('process_id', ''),
                'analysis_timestamp': datetime.now().isoformat(),
                'gaps': gaps,
                'compliance': compliance,
                'recommendations': recommendations,
                'summary': {
                    'total_gaps': sum(len(gap_list) for gap_list in gaps.values()),
                    'compliance_score': compliance.get('compliance_score', 0.0),
                    'high_priority_issues': len([r for r in recommendations if r['priority'] == 'high'])
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export analysis results: {e}")
            return False

# Utility functions for VPB process mining

def load_multiple_vpb_processes(directory_path: str) -> List[Dict[str, Any]]:
    """Load multiple VPB processes from directory"""
    import os
    
    miner = VPBProcessMiner()
    processes = []
    
    for filename in os.listdir(directory_path):
        if filename.endswith(('.vpb.xml', '.vpb.json')):
            file_path = os.path.join(directory_path, filename)
            try:
                process_data = miner.load_vpb_process(file_path)
                processes.append(process_data)
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")
    
    return processes

def batch_analyze_processes(processes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform batch analysis on multiple VPB processes"""
    miner = VPBProcessMiner()
    
    batch_results = {
        'analyzed_processes': len(processes),
        'total_gaps': 0,
        'average_compliance_score': 0.0,
        'common_issues': {},
        'process_results': []
    }
    
    compliance_scores = []
    gap_counts = []
    
    for process_data in processes:
        gaps = miner.analyze_process_gaps(process_data)
        compliance = miner.analyze_legal_compliance(process_data)
        
        total_gaps = sum(len(gap_list) for gap_list in gaps.values())
        gap_counts.append(total_gaps)
        compliance_scores.append(compliance.get('compliance_score', 0.0))
        
        batch_results['process_results'].append({
            'process_id': process_data.get('process_id', ''),
            'gaps_count': total_gaps,
            'compliance_score': compliance.get('compliance_score', 0.0)
        })
    
    # Calculate batch statistics
    batch_results['total_gaps'] = sum(gap_counts)
    batch_results['average_compliance_score'] = np.mean(compliance_scores) if compliance_scores else 0.0
    
    return batch_results