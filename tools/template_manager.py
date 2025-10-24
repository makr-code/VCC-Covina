"""
Covina Template Manager
======================

Template-Manager für dynamische dokumenttypspezifische Kuratierung.
Lädt und verwaltet JSON-basierte Templates mit KI-Prompts und Validierungsregeln.

Autor: Covina System
Datum: 2025-01-27
Basierend auf: default_metadata.json und curation_templates.json
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CurationTemplateManager:
    """
    Verwaltet dokumenttypspezifische Templates für die Kuratierung.
    """
    
    def __init__(self, template_file: str = "curation_templates.json"):
        """
        Initialisiert den Template Manager.
        
        Args:
            template_file: Pfad zur Template-JSON-Datei
        """
        self.template_file = template_file
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.global_fields: Dict[str, Dict[str, Any]] = {}
        self.classification_config: Dict[str, Any] = {}
        self.loaded = False
        
        # Versuche Templates zu laden
        self._load_templates()
    
    def _load_templates(self) -> bool:
        """
        Lädt Templates aus JSON-Datei.
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            # Prüfe verschiedene Pfade
            possible_paths = [
                self.template_file,
                os.path.join(os.path.dirname(__file__), self.template_file),
                os.path.join(os.getcwd(), self.template_file)
            ]
            
            template_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    template_path = path
                    break
            
            if not template_path:
                logger.warning(f"Template-Datei nicht gefunden: {self.template_file}")
                return False
            
            with open(template_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.templates = data.get("templates", {})
            self.global_fields = data.get("global_field_definitions", {})
            self.classification_config = data.get("classification_config", {})
            
            self.loaded = True
            logger.info(f"✅ Templates geladen: {len(self.templates)} Dokumenttypen")
            return True
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Laden der Templates: {e}")
            return False
    
    def get_available_templates(self) -> List[str]:
        """
        Gibt Liste aller verfügbaren Template-Namen zurück.
        
        Returns:
            Liste von Template-IDs
        """
        return list(self.templates.keys())
    
    def get_template(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """
        Gibt Template für Dokumenttyp zurück.
        
        Args:
            doc_type: Dokumenttyp (z.B. 'GESETZ', 'RECHTSPRECHUNG')
        
        Returns:
            Template-Dictionary oder None
        """
        return self.templates.get(doc_type.upper())
    
    def get_template_info(self, doc_type: str) -> Dict[str, str]:
        """
        Gibt Metainformationen über Template zurück.
        
        Args:
            doc_type: Dokumenttyp
        
        Returns:
            Dictionary mit name, description, icon
        """
        template = self.get_template(doc_type)
        if not template:
            return {
                "name": "Unbekannt",
                "description": "Kein Template vorhanden",
                "icon": "❓"
            }
        
        return {
            "name": template.get("name", "Unbekannt"),
            "description": template.get("description", ""),
            "icon": template.get("icon", "📄")
        }
    
    def get_required_fields(self, doc_type: str) -> List[str]:
        """
        Gibt Liste der Pflichtfelder für Dokumenttyp zurück.
        
        Args:
            doc_type: Dokumenttyp
        
        Returns:
            Liste von Feldnamen
        """
        template = self.get_template(doc_type)
        if not template:
            return []
        
        return template.get("required_fields", [])
    
    def get_optional_fields(self, doc_type: str) -> List[str]:
        """
        Gibt Liste der optionalen Felder für Dokumenttyp zurück.
        
        Args:
            doc_type: Dokumenttyp
        
        Returns:
            Liste von Feldnamen
        """
        template = self.get_template(doc_type)
        if not template:
            return []
        
        return template.get("optional_fields", [])
    
    def get_all_visible_fields(self, doc_type: str) -> List[str]:
        """
        Gibt alle sichtbaren Felder (required + optional) zurück.
        
        Args:
            doc_type: Dokumenttyp
        
        Returns:
            Liste von Feldnamen
        """
        required = self.get_required_fields(doc_type)
        optional = self.get_optional_fields(doc_type)
        return required + optional
    
    def get_field_groups(self, doc_type: str) -> List[Dict[str, Any]]:
        """
        Gibt gruppierte Felder für UI-Darstellung zurück.
        
        Args:
            doc_type: Dokumenttyp
        
        Returns:
            Liste von Gruppen mit Feldern
        """
        template = self.get_template(doc_type)
        if not template:
            return []
        
        return template.get("field_groups", [])
    
    def get_ai_prompt(self, doc_type: str, field_name: str) -> Optional[str]:
        """
        Gibt KI-Prompt für spezifisches Feld zurück.
        
        Args:
            doc_type: Dokumenttyp
            field_name: Name des Feldes
        
        Returns:
            Prompt-String oder None
        """
        template = self.get_template(doc_type)
        if not template:
            return None
        
        ai_prompts = template.get("ai_prompts", {})
        return ai_prompts.get(field_name)
    
    def get_all_ai_prompts(self, doc_type: str) -> Dict[str, str]:
        """
        Gibt alle KI-Prompts für Dokumenttyp zurück.
        
        Args:
            doc_type: Dokumenttyp
        
        Returns:
            Dictionary {field_name: prompt}
        """
        template = self.get_template(doc_type)
        if not template:
            return {}
        
        return template.get("ai_prompts", {})
    
    def get_validation_rules(self, doc_type: str, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Gibt Validierungsregeln für Feld zurück.
        
        Args:
            doc_type: Dokumenttyp
            field_name: Name des Feldes
        
        Returns:
            Validation-Dictionary oder None
        """
        template = self.get_template(doc_type)
        if not template:
            return None
        
        validation_rules = template.get("validation_rules", {})
        return validation_rules.get(field_name)
    
    def validate_field(self, doc_type: str, field_name: str, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validiert Feldwert gegen Template-Regeln.
        
        Args:
            doc_type: Dokumenttyp
            field_name: Name des Feldes
            value: Zu validierender Wert
        
        Returns:
            (is_valid, error_message)
        """
        rules = self.get_validation_rules(doc_type, field_name)
        if not rules:
            return (True, None)
        
        # Required-Check
        if rules.get("required", False) and not value:
            return (False, f"Feld '{field_name}' ist ein Pflichtfeld")
        
        # String-Validierung
        if isinstance(value, str):
            # Min/Max Length
            min_len = rules.get("min_length")
            if min_len and len(value) < min_len:
                return (False, f"Mindestlänge: {min_len} Zeichen")
            
            max_len = rules.get("max_length")
            if max_len and len(value) > max_len:
                return (False, f"Maximallänge: {max_len} Zeichen")
            
            # Enum-Check
            enum_values = rules.get("enum")
            if enum_values and value not in enum_values:
                return (False, f"Erlaubte Werte: {', '.join(enum_values)}")
            
            # Pattern-Check
            pattern = rules.get("pattern")
            if pattern:
                import re
                if not re.match(pattern, value):
                    return (False, f"Ungültiges Format")
        
        # Numeric-Validierung
        if isinstance(value, (int, float)):
            min_val = rules.get("min")
            if min_val is not None and value < min_val:
                return (False, f"Minimalwert: {min_val}")
            
            max_val = rules.get("max")
            if max_val is not None and value > max_val:
                return (False, f"Maximalwert: {max_val}")
        
        return (True, None)
    
    def validate_metadata(self, doc_type: str, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validiert gesamtes Metadaten-Dictionary.
        
        Args:
            doc_type: Dokumenttyp
            metadata: Metadaten-Dictionary
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Prüfe Pflichtfelder
        required_fields = self.get_required_fields(doc_type)
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                errors.append(f"Pflichtfeld fehlt: {field}")
        
        # Validiere vorhandene Felder
        for field_name, value in metadata.items():
            is_valid, error = self.validate_field(doc_type, field_name, value)
            if not is_valid:
                errors.append(f"{field_name}: {error}")
        
        return (len(errors) == 0, errors)
    
    def classify_document(self, text: str, title: str = "") -> str:
        """
        Klassifiziert Dokumenttyp basierend auf Keywords.
        
        Args:
            text: Dokumenttext
            title: Titel (optional)
        
        Returns:
            Dokumenttyp (z.B. 'GESETZ', 'RECHTSPRECHUNG')
        """
        if not self.classification_config.get("auto_classification_enabled", True):
            return "SONSTIGES"
        
        text_lower = (title + " " + text).lower()
        keywords = self.classification_config.get("classification_keywords", {})
        
        # Zähle Keywords pro Typ
        scores = {}
        for doc_type, type_keywords in keywords.items():
            score = sum(1 for keyword in type_keywords if keyword in text_lower)
            scores[doc_type] = score
        
        # Wähle Typ mit höchstem Score
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0:
                return best_type
        
        return "SONSTIGES"
    
    def get_field_definition(self, field_name: str) -> Dict[str, Any]:
        """
        Gibt globale Felddefinition zurück.
        
        Args:
            field_name: Name des Feldes
        
        Returns:
            Field-Definition-Dictionary
        """
        return self.global_fields.get(field_name, {})
    
    def generate_metadata_template(self, doc_type: str, include_optional: bool = True) -> Dict[str, Any]:
        """
        Generiert leeres Metadaten-Template für Dokumenttyp.
        
        Args:
            doc_type: Dokumenttyp
            include_optional: Optionale Felder einbeziehen?
        
        Returns:
            Dictionary mit leeren Feldern
        """
        template_data = {}
        
        # Required Fields
        for field in self.get_required_fields(doc_type):
            template_data[field] = ""
        
        # Optional Fields
        if include_optional:
            for field in self.get_optional_fields(doc_type):
                template_data[field] = ""
        
        return template_data
    
    def get_completeness_score(self, doc_type: str, metadata: Dict[str, Any]) -> float:
        """
        Berechnet Vollständigkeitsscore der Metadaten.
        
        Args:
            doc_type: Dokumenttyp
            metadata: Metadaten-Dictionary
        
        Returns:
            Score zwischen 0.0 und 1.0
        """
        required = self.get_required_fields(doc_type)
        optional = self.get_optional_fields(doc_type)
        all_fields = required + optional
        
        if not all_fields:
            return 0.0
        
        # Zähle gefüllte Felder
        filled_count = 0
        for field in all_fields:
            if field in metadata and metadata[field]:
                filled_count += 1
        
        return filled_count / len(all_fields)
    
    def suggest_next_fields(self, doc_type: str, metadata: Dict[str, Any], limit: int = 5) -> List[str]:
        """
        Schlägt nächste zu füllende Felder vor.
        
        Args:
            doc_type: Dokumenttyp
            metadata: Aktuell gefüllte Metadaten
            limit: Maximale Anzahl Vorschläge
        
        Returns:
            Liste von Feldnamen
        """
        # Priorität: Erst Pflichtfelder, dann optionale
        required = self.get_required_fields(doc_type)
        optional = self.get_optional_fields(doc_type)
        
        suggestions = []
        
        # Prüfe fehlende Pflichtfelder
        for field in required:
            if field not in metadata or not metadata[field]:
                suggestions.append(field)
                if len(suggestions) >= limit:
                    return suggestions
        
        # Prüfe fehlende optionale Felder
        for field in optional:
            if field not in metadata or not metadata[field]:
                suggestions.append(field)
                if len(suggestions) >= limit:
                    return suggestions
        
        return suggestions


# Singleton-Instanz
_template_manager_instance: Optional[CurationTemplateManager] = None


def get_template_manager() -> CurationTemplateManager:
    """
    Gibt Singleton-Instanz des Template Managers zurück.
    
    Returns:
        CurationTemplateManager-Instanz
    """
    global _template_manager_instance
    
    if _template_manager_instance is None:
        _template_manager_instance = CurationTemplateManager()
    
    return _template_manager_instance


# Convenience-Funktionen
def load_template(doc_type: str) -> Optional[Dict[str, Any]]:
    """Lädt Template für Dokumenttyp."""
    return get_template_manager().get_template(doc_type)


def get_fields(doc_type: str) -> List[str]:
    """Gibt alle sichtbaren Felder zurück."""
    return get_template_manager().get_all_visible_fields(doc_type)


def get_prompts(doc_type: str) -> Dict[str, str]:
    """Gibt alle KI-Prompts zurück."""
    return get_template_manager().get_all_ai_prompts(doc_type)


def validate_metadata(doc_type: str, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validiert Metadaten."""
    return get_template_manager().validate_metadata(doc_type, metadata)


def classify_document(text: str, title: str = "") -> str:
    """Klassifiziert Dokumenttyp."""
    return get_template_manager().classify_document(text, title)


if __name__ == "__main__":
    # Test des Template Managers
    print("🧪 Teste Template Manager\n")
    
    manager = get_template_manager()
    
    if not manager.loaded:
        print("❌ Templates konnten nicht geladen werden!")
        exit(1)
    
    print(f"✅ Templates geladen: {manager.get_available_templates()}\n")
    
    # Test: Lade GESETZ-Template
    print("📋 GESETZ-Template:")
    gesetz_template = manager.get_template("GESETZ")
    if gesetz_template:
        print(f"  Name: {gesetz_template['name']}")
        print(f"  Icon: {gesetz_template['icon']}")
        print(f"  Pflichtfelder: {manager.get_required_fields('GESETZ')}")
        print(f"  Optionale Felder: {len(manager.get_optional_fields('GESETZ'))} Felder")
    
    # Test: KI-Prompts
    print("\n💡 KI-Prompt für 'titel' (GESETZ):")
    prompt = manager.get_ai_prompt("GESETZ", "titel")
    print(f"  {prompt[:100]}...")
    
    # Test: Dokumentklassifikation
    print("\n🔍 Dokumentklassifikation:")
    test_texts = [
        ("Bundesgesetz zur Regelung von...", "GESETZ"),
        ("Urteil des Bundesverwaltungsgerichts...", "RECHTSPRECHUNG"),
        ("Genehmigung nach § 4 BImSchG...", "VERWALTUNGSAKT"),
        ("Gutachten zur Umweltverträglichkeit...", "GUTACHTEN")
    ]
    
    for text, expected in test_texts:
        classified = manager.classify_document(text)
        status = "✅" if classified == expected else "❌"
        print(f"  {status} '{text[:40]}...' → {classified}")
    
    # Test: Validierung
    print("\n✔️  Metadaten-Validierung (GESETZ):")
    metadata = {
        "titel": "Test",  # Zu kurz
        "summary": "Dies ist eine Zusammenfassung mit ausreichender Länge.",
        "norm_type": "Bundesgesetz",
        "status": "In Kraft"
    }
    
    is_valid, errors = manager.validate_metadata("GESETZ", metadata)
    if is_valid:
        print("  ✅ Metadaten gültig")
    else:
        print(f"  ❌ Validierungsfehler:")
        for error in errors:
            print(f"     - {error}")
    
    # Test: Vollständigkeitsscore
    print("\n📊 Vollständigkeit:")
    score = manager.get_completeness_score("GESETZ", metadata)
    print(f"  Score: {score:.1%}")
    
    # Test: Nächste Felder
    print("\n➡️  Vorgeschlagene nächste Felder:")
    next_fields = manager.suggest_next_fields("GESETZ", metadata, limit=3)
    for field in next_fields:
        print(f"  - {field}")
    
    print("\n✅ Alle Tests abgeschlossen!")
