"""
UDS3 Knowledge Base Integration
API-Backend für VPB Process Designer mit Ollama LLM Integration

Bietet:
- Semantische Prozessanalyse
- Rechtliche Compliance-Prüfung
- Automatische Element-Kategorisierung
- Prozess-Optimierungsvorschläge
- SQLite-basierte Persistierung

Autor: UDS3 Development Team
Datum: 22. August 2025
"""

import json
import subprocess
import logging
from typing import Dict, List, Optional, Any
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime

# VPB SQLite Integration
try:
    from vpb_sqlite_db import VPBSQLiteDB  # type: ignore
except Exception:  # pragma: no cover - optional local dependency
    from typing import Any

    VPBSQLiteDB = Any  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class UDS3KnowledgeEntry:
    """UDS3 Wissensbasis-Eintrag"""

    entry_id: str
    category: str
    legal_framework: str
    authority: str
    description: str
    keywords: List[str]
    related_processes: List[str]
    compliance_rules: List[str]
    geographic_scope: str = "Deutschland"
    validity_period: Optional[str] = None


@dataclass
class ProcessAnalysisResult:
    """Ergebnis der Prozessanalyse"""

    process_id: str
    complexity_score: float
    compliance_issues: List[str]
    optimization_suggestions: List[str]
    missing_elements: List[str]
    authority_mapping: Dict[str, str]
    estimated_duration_days: int
    risk_assessment: str


class UDS3APIBackend:
    """UDS3 Knowledge Base API Backend mit Ollama Integration"""

    def __init__(self, ollama_model: str = "llama3.1"):
        self.ollama_model = ollama_model
        self.knowledge_base = self._initialize_knowledge_base()
        self._verify_ollama_available()

    def _verify_ollama_available(self):
        """Überprüft ob Ollama verfügbar ist"""
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Ollama verfügbar. Modelle: {result.stdout[:100]}...")
                return True
            else:
                logger.warning(f"Ollama nicht verfügbar: {result.stderr}")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Ollama-Kommando fehlgeschlagen: {e}")
            return False

    def _initialize_knowledge_base(self) -> Dict[str, UDS3KnowledgeEntry]:
        """Initialisiert UDS3 Knowledge Base mit Verwaltungsrecht-Wissen"""

        kb: dict[Any, Any] = {}

        # Baurecht
        kb["BAURECHT_001"] = UDS3KnowledgeEntry(
            entry_id="BAURECHT_001",
            category="BAURECHT",
            legal_framework="BauO NRW",
            authority="Bauaufsichtsamt",
            description="Baugenehmigungsverfahren für Wohngebäude",
            keywords=[
                "Baugenehmigung",
                "Bauantrag",
                "Wohnbau",
                "Vollständigkeitsprüfung",
            ],
            related_processes=["GEWERBE_BAU", "UMWELT_BAU"],
            compliance_rules=[
                "Formale Vollständigkeitsprüfung binnen 14 Tagen",
                "Materielle Prüfung binnen 8 Wochen",
                "Beteiligung Nachbarn bei erforderlich",
            ],
            geographic_scope="Nordrhein-Westfalen",
        )

        # Gewerberecht
        kb["GEWERBE_001"] = UDS3KnowledgeEntry(
            entry_id="GEWERBE_001",
            category="GEWERBERECHT",
            legal_framework="GewO",
            authority="Gewerbeamt",
            description="Gewerbeanmeldung für Handwerksbetriebe",
            keywords=["Gewerbeanmeldung", "Handwerk", "Meisterpflicht", "WZ-Code"],
            related_processes=["BAURECHT_GEWERBE", "UMWELT_GEWERBE", "BRANDSCHUTZ"],
            compliance_rules=[
                "Anmeldung binnen einer Woche nach Betriebsaufnahme",
                "Meisternachweis bei zulassungspflichtigen Handwerken",
                "Führungszeugnis bei bestimmten Gewerben",
            ],
        )

        # Umweltrecht
        kb["UMWELT_001"] = UDS3KnowledgeEntry(
            entry_id="UMWELT_001",
            category="UMWELTRECHT",
            legal_framework="BImSchG",
            authority="Umweltamt",
            description="Immissionsschutzrechtliche Genehmigung",
            keywords=["Emissionen", "Immissionsschutz", "UVP", "Luftreinhaltung"],
            related_processes=["GEWERBE_INDUSTRIE", "BAURECHT_INDUSTRIE"],
            compliance_rules=[
                "UVP-Pflicht ab bestimmten Schwellenwerten",
                "Öffentlichkeitsbeteiligung bei UVP-pflichtigen Vorhaben",
                "Emissionsgrenzwerte einhalten",
            ],
        )

        # Sozialrecht
        kb["SOZIAL_001"] = UDS3KnowledgeEntry(
            entry_id="SOZIAL_001",
            category="SOZIALRECHT",
            legal_framework="SGB II",
            authority="Jobcenter",
            description="Arbeitslosengeld II Antragsverfahren",
            keywords=["ALG II", "Bürgergeld", "Bedarfsgemeinschaft", "Eingliederung"],
            related_processes=["SOZIAL_WOHNGELD", "SOZIAL_BILDUNG"],
            compliance_rules=[
                "Antrag binnen 3 Monaten rückwirkend möglich",
                "Mitwirkungspflicht des Antragstellers",
                "Eingliederungsvereinbarung erforderlich",
            ],
        )

        logger.info(f"UDS3 Knowledge Base initialisiert mit {len(kb)} Einträgen")
        return kb

    def analyze_process_with_llm(
        self, process_elements: List[Dict], process_connections: List[Dict]
    ) -> ProcessAnalysisResult:
        """Analysiert Verwaltungsprozess mit Ollama LLM"""

        logger.info(f"Starte Prozessanalyse mit {len(process_elements)} Elementen")

        # Prozess-Kontext für LLM zusammenstellen
        process_context = {
            "elements": process_elements,
            "connections": process_connections,
            "element_count": len(process_elements),
            "connection_count": len(process_connections),
            "authorities": list(
                set(
                    [
                        e.get("competent_authority", "")
                        for e in process_elements
                        if e.get("competent_authority")
                    ]
                )
            ),
            "legal_bases": list(
                set(
                    [
                        e.get("legal_basis", "")
                        for e in process_elements
                        if e.get("legal_basis")
                    ]
                )
            ),
        }

        # LLM-Prompt für Prozessanalyse
        analysis_prompt = f"""
        Analysiere den folgenden deutschen Verwaltungsprozess und bewerte:

        Prozess-Daten:
        {json.dumps(process_context, indent=2, ensure_ascii=False)}

        Bewerte bitte:
        1. Komplexität des Prozesses (Skala 1-10)
        2. Compliance-Probleme mit deutschem Verwaltungsrecht
        3. Optimierungsvorschläge für Effizienz
        4. Fehlende Elemente (z.B. Rechtsprüfungen, Fristen)
        5. Zuständigkeits-Mapping der Behörden
        6. Geschätzte Bearbeitungsdauer in Tagen
        7. Risikobewertung (niedrig/mittel/hoch)

        Antworte in strukturiertem JSON-Format.
        """

        try:
            # Ollama LLM aufrufen
            llm_response = self._call_ollama_llm(analysis_prompt)

            # Response parsen
            analysis_data = self._parse_llm_response(llm_response)

            # ProcessAnalysisResult erstellen
            result = ProcessAnalysisResult(
                process_id=f"PROC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                complexity_score=analysis_data.get("complexity_score", 5.0),
                compliance_issues=analysis_data.get("compliance_issues", []),
                optimization_suggestions=analysis_data.get(
                    "optimization_suggestions", []
                ),
                missing_elements=analysis_data.get("missing_elements", []),
                authority_mapping=analysis_data.get("authority_mapping", {}),
                estimated_duration_days=analysis_data.get(
                    "estimated_duration_days", 30
                ),
                risk_assessment=analysis_data.get("risk_assessment", "mittel"),
            )

            logger.info(
                f"Prozessanalyse abgeschlossen. Komplexität: {result.complexity_score}"
            )
            return result

        except Exception as e:
            logger.error(f"LLM-Prozessanalyse fehlgeschlagen: {e}")

            # Fallback: Einfache regelbasierte Analyse
            return self._fallback_analysis(process_elements, process_connections)

    def _call_ollama_llm(self, prompt: str, timeout: int = 30) -> str:
        """Ruft Ollama LLM mit Prompt auf"""

        try:
            # Ollama über Subprocess aufrufen
            cmd = ["ollama", "run", self.ollama_model, prompt]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8"
            )

            if result.returncode == 0:
                logger.debug(f"LLM Response erhalten: {len(result.stdout)} Zeichen")
                return result.stdout.strip()
            else:
                logger.error(f"Ollama-Fehler: {result.stderr}")
                raise Exception(f"Ollama-Aufruf fehlgeschlagen: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error(f"Ollama-Timeout nach {timeout} Sekunden")
            raise Exception("LLM-Aufruf timeout")
        except Exception as e:
            logger.error(f"Ollama-Aufruf fehlgeschlagen: {e}")
            raise

    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parst LLM-Response zu strukturierten Daten"""

        try:
            # Versuche JSON zu extrahieren
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback: Einfache Textanalyse
                return self._parse_text_response(llm_response)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON-Parsing fehlgeschlagen: {e}")
            return self._parse_text_response(llm_response)

    def _parse_text_response(self, text_response: str) -> Dict[str, Any]:
        """Fallback: Parst Textantwort zu strukturierten Daten"""

        result = {
            "complexity_score": 5.0,
            "compliance_issues": [],
            "optimization_suggestions": [],
            "missing_elements": [],
            "authority_mapping": {},
            "estimated_duration_days": 30,
            "risk_assessment": "mittel",
        }

        # Einfache Keyword-basierte Extraktion
        lines = text_response.lower().split("\n")

        for line in lines:
            if "komplexität" in line or "complexity" in line:
                # Versuche Zahl zu extrahieren
                import re

                numbers = re.findall(r"\d+(?:\.\d+)?", line)
                if numbers:
                    result["complexity_score"] = float(numbers[0])

            elif "compliance" in line or "rechtlich" in line:
                result["compliance_issues"].append(line.strip())

            elif "optimierung" in line or "verbesserung" in line:
                result["optimization_suggestions"].append(line.strip())

            elif "fehlt" in line or "missing" in line:
                result["missing_elements"].append(line.strip())

        return result

    def _fallback_analysis(
        self, elements: List[Dict], connections: List[Dict]
    ) -> ProcessAnalysisResult:
        """Fallback-Analyse ohne LLM"""

        logger.info("Verwende Fallback-Analyse (regelbasiert)")

        # Einfache regelbasierte Analyse
        complexity_factors = [
            len(elements) / 10.0,  # Element-Anzahl
            len(connections) / 10.0,  # Verbindungs-Anzahl
            len(set([e.get("competent_authority", "") for e in elements]))
            / 3.0,  # Behörden-Anzahl
        ]

        complexity_score = min(10.0, sum(complexity_factors))

        # Standard-Empfehlungen
        compliance_issues: list[Any] = []
        optimization_suggestions = [
            "Prüfen Sie die Bearbeitungsfristen gemäß VwVfG",
            "Stellen Sie sicher, dass alle Rechtsprüfungen dokumentiert sind",
        ]
        missing_elements: list[Any] = []

        if not any("legal" in str(e.get("element_type", "")).lower() for e in elements):
            missing_elements.append("Legal Checkpoints für Rechtsprüfung")

        return ProcessAnalysisResult(
            process_id=f"FALLBACK_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            complexity_score=complexity_score,
            compliance_issues=compliance_issues,
            optimization_suggestions=optimization_suggestions,
            missing_elements=missing_elements,
            authority_mapping={},
            estimated_duration_days=int(complexity_score * 7),
            risk_assessment="mittel" if complexity_score < 7 else "hoch",
        )

    def get_related_knowledge(
        self, keywords: List[str], category: Optional[str] = None
    ) -> List[UDS3KnowledgeEntry]:
        """Findet verwandte Wissenseinträge basierend auf Keywords"""

        related_entries: list[Any] = []

        for entry in self.knowledge_base.values():
            # Kategorie-Filter
            if category and entry.category.lower() != category.lower():
                continue

            # Keyword-Matching
            entry_keywords_lower = [k.lower() for k in entry.keywords]
            input_keywords_lower = [k.lower() for k in keywords]

            matches = len(set(entry_keywords_lower) & set(input_keywords_lower))

            if matches > 0:
                related_entries.append(entry)

        # Sortiere nach Relevanz (Anzahl Matches)
        related_entries.sort(
            key=lambda e: len(
                set([k.lower() for k in e.keywords])
                & set([k.lower() for k in keywords])
            ),
            reverse=True,
        )

        logger.debug(
            f"Gefunden {len(related_entries)} verwandte Knowledge-Einträge für Keywords: {keywords}"
        )
        return related_entries[:5]  # Top 5

    def suggest_process_elements(
        self, current_elements: List[Dict], process_type: str = "ADMINISTRATIVE"
    ) -> List[Dict]:
        """Schlägt zusätzliche Prozess-Elemente vor basierend auf UDS3 Knowledge Base"""

        suggestions: list[Any] = []

        # Analysiere aktuelle Elemente
        current_authorities = set(
            [e.get("competent_authority", "") for e in current_elements]
        )
        current_legal_bases = set([e.get("legal_basis", "") for e in current_elements])

        # Finde passende Knowledge-Einträge
        for entry in self.knowledge_base.values():
            if entry.authority not in current_authorities:
                continue

            # Prüfe ob Legal Checkpoints fehlen
            for rule in entry.compliance_rules:
                suggestion = {
                    "element_type": "LEGAL_CHECKPOINT",
                    "name": f"Compliance-Prüfung: {rule[:50]}...",
                    "description": rule,
                    "competent_authority": entry.authority,
                    "legal_basis": entry.legal_framework,
                    "source": f"UDS3 Knowledge Base ({entry.entry_id})",
                }
                suggestions.append(suggestion)

        logger.info(f"Erstellt {len(suggestions)} Element-Vorschläge")
        return suggestions[:10]  # Top 10


import threading

try:
    from . import config as _config
except Exception:
    _config = None

# Singleton-Instance + Lock für Thread-Safety
_uds3_backend_instance: Any = None
_uds3_backend_lock = threading.Lock()


def get_uds3_backend(expect_backend: bool | None = None) -> Optional[UDS3APIBackend]:
    """Thread-sicherer Singleton-Zugriff auf das UDS3 Backend.

    Args:
        expect_backend: Optionales Override, ob Backend explizit erwartet wird.
                        Wenn None → liest ENV `EXPECT_UDS3_BACKEND` ("true"/"false").
    Returns:
        UDS3APIBackend Instanz oder None (falls nicht verfügbar / Fehler beim Init)
    """
    global _uds3_backend_instance

    if expect_backend is None:
        # Verwende ausschließlich zentrale Config.FEATURES; entferne direkte ENV-Abfragen
        expect_backend = (
            bool(_config.FEATURES.get("expect_uds3_backend", False))
            if _config is not None
            else False
        )

    if _uds3_backend_instance is not None:
        return _uds3_backend_instance

    # Double-Checked Locking
    with _uds3_backend_lock:
        if _uds3_backend_instance is not None:
            return _uds3_backend_instance
        try:
            _uds3_backend_instance = UDS3APIBackend()
            logger.info("✅ UDS3 Backend API aktiv (Vollmodus)")
        except Exception as e:
            # Erwartet vs. optional unterscheiden
            if expect_backend:
                logger.warning(
                    f"⚠️ UDS3 Backend konnte nicht initialisiert werden (erwartet). Fallback auf Core-only. Grund: {type(e).__name__}: {e}"
                )
            else:
                logger.info(
                    f"ℹ️ UDS3 Backend nicht geladen (optional). Core-only Modus aktiv. Grund: {type(e).__name__}: {e}"
                )
            _uds3_backend_instance = None
        return _uds3_backend_instance
    return uds3_backend


"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_api_backend"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...Z3llo0Q="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "cc831f722afccae8fd8ad10ae90011bbc17b808ac21deafbc64512d7ef13fdf6"
)
module_file_key = "aba789d0cd52411caffd4b88072ca4bbc91974e0062fdc6c836c227c207dbf73"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===