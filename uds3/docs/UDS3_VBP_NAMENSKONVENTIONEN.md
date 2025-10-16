# UDS3/VBP NAMENSKONVENTIONEN DOKUMENTATION
=====================================================

## ÜBERSICHT
Das UDS3-System folgt strikten Namenskonventionen für eine klare Trennung der Komponenten:

- **UDS3**: Unified Document Structure v3 - Kerndokument-Framework
- **VBP**: Verwaltungsverfahren - Administrative Verfahrenscompliance
- **XÖV**: XML-basierte Online-Verwaltung - Government data exchange
- **FZD**: Funktions-Zuordnungs-Diagramm - EPK Satellite mapping
- **BVA**: Bundesverwaltungsamt - Federal administration standards

## DATEINAMEN-STRUKTUR

### UDS3 Core Components
```
uds3_bpmn_process_parser.py          # BPMN 2.0 Parser mit UDS3-Integration
uds3_epk_process_parser.py           # EPK/eEPK Parser mit FZD-Satelliten
uds3_process_export_engine.py        # XML Export Engine für BPMN/EPK
uds3_complete_process_integration.py # Vollständige Prozess-Integration
uds3_system_integration_tester.py    # Vollständiger Systemtest
```

### VBP Compliance Components
```
vbp_compliance_engine.py             # Verwaltungsverfahren Compliance-Engine
```

### Legacy Components (Korrekte Benennung)
```
# Bereits korrekt benannte Dateien:
advanced_cross_reference_engine.py   # Cross-Reference ohne UDS3-Bezug
api_endpoint_fastapi_production.py   # API ohne direkten UDS3-Bezug
conversation_manager.py              # Allgemein, kein UDS3-Bezug
```

## KLASSEN-STRUKTUR

### UDS3 Classes
```python
# uds3_bpmn_process_parser.py
class BPMNProcessParser           # UDS3 BPMN Parser
class BPMN20Validator            # BPMN 2.0 Validation
class UDS3BPMNDocument           # UDS3 BPMN Document Structure

# uds3_epk_process_parser.py  
class EPKProcessParser           # UDS3 EPK Parser
class EPKValidator              # EPK/eEPK Validation
class UDS3EPKDocument           # UDS3 EPK Document Structure

# uds3_process_export_engine.py
class ProcessExportEngine       # UDS3 Export Engine
class UDS3ExportResult         # Export Result Structure

# uds3_complete_process_integration.py
class UDS3UnifiedProcessParser           # Unified Parser
class UDS3ProcessIntegrationCoordinator  # Integration Coordinator
class UDS3ProcessWorker                  # Process Worker
```

### VBP Classes
```python
# vbp_compliance_engine.py
class VBPComplianceEngine       # VBP Compliance Validation
class VBPComplianceReport       # VBP Compliance Reporting
class VBPComplianceResult       # VBP Compliance Result Structure
```

## IMPORT-STRUKTUR

### Korrekte Imports
```python
# UDS3 Core Imports
from uds3_bpmn_process_parser import BPMNProcessParser, BPMN20Validator
from uds3_epk_process_parser import EPKProcessParser, EPKValidator  
from uds3_process_export_engine import ProcessExportEngine
from uds3_complete_process_integration import create_uds3_process_coordinator

# VBP Compliance Imports
from vbp_compliance_engine import VBPComplianceEngine, VBPComplianceReport
```

## FUNKTIONS-NAMENSKONVENTIONEN

### UDS3 Functions
```python
# Create Functions
create_uds3_process_coordinator()    # UDS3 Coordinator Creation
create_uds3_document()              # UDS3 Document Creation

# Parse Functions  
parse_bpmn_to_uds3()                # BPMN zu UDS3 Conversion
parse_epk_to_uds3()                 # EPK zu UDS3 Conversion

# Export Functions
export_uds3_to_xml()                # UDS3 zu XML Export
export_uds3_to_bpmn()               # UDS3 zu BPMN Export

# Validation Functions
validate_uds3_document()            # UDS3 Document Validation
validate_bpmn_process()             # BPMN Process Validation
```

### VBP Functions
```python
# VBP Validation Functions
validate_uds3_process()             # UDS3 Process mit VBP Rules
validate_verwaltungsverfahren()     # Verwaltungsverfahren Validation
generate_compliance_report()        # VBP Compliance Report
```

## KONFIGURATION UND STANDARDS

### UDS3 Standards
- Document Type: `verwaltungsprozess_bpmn` oder `verwaltungsprozess_epk`
- Namespace: `http://www.verwaltung.de/uds3/v1`
- Version: `3.0`
- Encoding: `UTF-8`

### VBP Standards  
- Compliance Level: `exemplarisch`, `gut`, `ausreichend`, `mangelhaft`
- BVA Ready: Boolean flag für Bundesverwaltungsamt compatibility
- FIM Ready: Boolean flag für FIM-Standards compatibility
- DSGVO Compliant: Boolean flag für DSGVO compliance

## VERZEICHNISSTRUKTUR

### Empfohlene Organisation
```
/veritas/
├── uds3_*.py                    # UDS3 Core Components
├── vbp_*.py                     # VBP Compliance Components  
├── api_*.py                     # API Endpoints (allgemein)
├── conversation_*.py            # Conversation Management
├── analyze_*.py                 # Analysis Scripts
└── config.py                    # Configuration
```

## LOGGING UND DEBUGGING

### Logger Names
```python
# UDS3 Loggers
logger = logging.getLogger('uds3_bpmn_process_parser')
logger = logging.getLogger('uds3_epk_process_parser')
logger = logging.getLogger('uds3_process_export_engine')
logger = logging.getLogger('uds3_complete_process_integration')

# VBP Loggers  
logger = logging.getLogger('vbp_compliance_engine')
```

### Log Messages
```python
# UDS3 Log Format
logger.info("UDS3-BPMN-Parser geladen")
logger.info("BPMN-Prozess erfolgreich geparst: {process_name}")
logger.info("UDS3 Process Integration Coordinator mit {workers} Workern initialisiert")

# VBP Log Format
logger.info("VBP Compliance-Validierung erfolgreich")
logger.info("VBP Compliance Level: {level}")
```

## TESTING NAMENSKONVENTIONEN

### Test File Names
```python
uds3_system_integration_tester.py   # Vollständiger UDS3 System Test
test_uds3_bpmn_parser.py            # UDS3 BPMN Parser Tests
test_vbp_compliance_engine.py       # VBP Compliance Tests
```

### Test Class Names
```python
class TestUDS3BPMNParser            # UDS3 BPMN Parser Test Class
class TestVBPComplianceEngine       # VBP Compliance Test Class
class UDS3SystemTester              # UDS3 System Integration Tester
```

## VERSIONIERUNG UND KOMPATIBILITÄT

### Version Tags
- UDS3 Components: v3.x.x
- VBP Components: v1.x.x  
- API Components: v2.x.x

### Kompatibilitäts-Matrix
```
UDS3 v3.0 + VBP v1.0 = ✅ Vollständig kompatibel
UDS3 v3.0 + BPMN 2.0 = ✅ Vollständig kompatibel  
VBP v1.0 + BVA Standards = ✅ Vollständig kompatibel
EPK + FZD Mapping = ✅ Vollständig kompatibel
```

## FAZIT

✅ **ALLE NAMENSKONVENTIONEN IMPLEMENTIERT**
- UDS3-Präfix für alle Kerndokument-Komponenten
- VBP-Präfix für Verwaltungsverfahren-Compliance
- Klare Trennung der Verantwortlichkeiten
- Einheitliche Import- und Funktionsstruktur
- Vollständige Kompatibilität gewährleistet

**System Status: 🟢 PRODUKTIONSBEREIT**
