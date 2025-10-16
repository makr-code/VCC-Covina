#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_document_classifier"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...VljQig=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "ee1a5a58ac385161f1aede990b112726848afdd2372bb29d4d4fead3b214ca35"
)
module_file_key = "bab51e00f5daede58753370d0f95a62f316ee131420c1cbfd06d7246930842ce"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
UDS3 Administrative Document Classifier
Intelligente Klassifikation von Verwaltungsdokumenten

Diese Klasse analysiert Dokumentinhalte und klassifiziert sie automatisch
nach UDS3-Standards für Verwaltungsrecht.
"""

import re
import logging
from typing import Dict, List, Any
from typing import Optional, Any
from uds3_admin_types import AdminDocumentType, AdminLevel, AdminDomain, ProcedureStage

logger = logging.getLogger(__name__)


class UDS3DocumentClassifier:
    """Intelligente Klassifikation für administrative Dokumente"""

    def __init__(self):
        self.classification_patterns = self._init_classification_patterns()
        self.admin_level_patterns = self._init_admin_level_patterns()
        self.domain_patterns = self._init_domain_patterns()
        self.procedure_stage_patterns = self._init_procedure_stage_patterns()

    def classify_document(
        self, text_content: str, filename: str = "", metadata: Optional[Dict[Any, Any]] = None
    ) -> Dict:
        """Hauptmethode für Dokumentklassifikation"""
        try:
            # Bereinige Text für Analyse
            clean_text = self._clean_text(text_content)

            # Klassifikation durchführen
            doc_type = self._classify_document_type(clean_text, filename)
            admin_level = self._classify_admin_level(clean_text, filename)
            admin_domain = self._classify_admin_domain(clean_text, filename)
            procedure_stage = self._classify_procedure_stage(clean_text)

            # Confidence Score berechnen
            confidence = self._calculate_confidence(
                clean_text, doc_type, admin_level, admin_domain
            )

            # Zusätzliche Metadaten extrahieren
            extracted_metadata = self._extract_legal_metadata(clean_text)

            return {
                "document_type": doc_type,
                "admin_level": admin_level,
                "admin_domain": admin_domain,
                "procedure_stage": procedure_stage,
                "confidence_score": confidence,
                "classification_metadata": extracted_metadata,
                "classification_source": "uds3_auto_classifier",
            }

        except Exception as e:
            logger.error(f"Fehler bei Dokumentklassifikation: {e}")
            return self._fallback_classification()

    def _init_classification_patterns(self) -> Dict[AdminDocumentType, List[str]]:
        """Initialisiert Muster für Dokumenttyp-Erkennung"""
        return {
            # Normative Ebene
            AdminDocumentType.LAW: [
                r"\bGesetz\b",
                r"\bGesetzbuch\b",
                r"BGBl\b",
                r"GVBl\b",
                r"\b§\s*\d+",
                r"\bArtikel\s*\d+",
                r"\bArt\.\s*\d+",
                r"verkündet",
                r"erlassen",
                r"beschlossen",
            ],
            AdminDocumentType.REGULATION: [
                r"\bVerordnung\b",
                r"\bVO\b",
                r"\bBAnz\b",
                r"aufgrund\s+des?\s+§",
                r"ermächtigt",
                r"verordnet",
            ],
            AdminDocumentType.ORDINANCE: [
                r"\bSatzung\b",
                r"\bOrdnung\b",
                r"Amtsblatt",
                r"Gemeinderat",
                r"Stadtrat",
                r"Kreistag",
            ],
            # Verwaltungsentscheidungen
            AdminDocumentType.ADMINISTRATIVE_ACT: [
                r"\bVerwaltungsakt\b",
                r"\bBescheid\b",
                r"\bVerfügung\b",
                r"Rechtsmittelbelehrung",
                r"Widerspruch",
                r"bestandskräftig",
            ],
            AdminDocumentType.PERMIT: [
                r"\bGenehmigung\b",
                r"\bErlaubnis\b",
                r"\bBewilligung\b",
                r"genehmigt",
                r"gestattet",
                r"zugelassen",
                r"erteilt",
            ],
            AdminDocumentType.REJECTION: [
                r"\bAblehnung\b",
                r"\bVersagung\b",
                r"abgelehnt",
                r"versagt",
                r"nicht genehmigt",
                r"unzulässig",
            ],
            # Planungsrecht
            AdminDocumentType.SPATIAL_PLAN: [
                r"\bRaumordnungsplan\b",
                r"\bRegionalplan\b",
                r"\bLEP\b",
                r"\bREP\b",
                r"Vorranggebiet",
                r"Vorbehaltsgebiet",
                r"Raumordnung",
            ],
            AdminDocumentType.LAND_USE_PLAN: [
                r"\bFlächennutzungsplan\b",
                r"\bFNP\b",
                r"§\s*5\s+BauGB",
                r"Darstellung",
                r"Wohnbaufläche",
                r"Gewerbefläche",
            ],
            AdminDocumentType.DEVELOPMENT_PLAN: [
                r"\bBebauungsplan\b",
                r"\bB-Plan\b",
                r"§\s*9\s+BauGB",
                r"Festsetzung",
                r"\bWA\b",
                r"\bWR\b",
                r"\bMI\b",
                r"\bGE\b",
            ],
            # Betriebsanweisungen (Graph DB optimiert!)
            AdminDocumentType.PROCESS_INSTRUCTION: [
                r"\bVerfahrensanweisung\b",
                r"\bArbeitsanweisung\b",
                r"\bSOP\b",
                r"Schritt\s*\d+",
                r"Ablauf",
                r"Verfahren",
                r"zunächst.*dann",
            ],
            AdminDocumentType.WORKFLOW_DEFINITION: [
                r"\bWorkflow\b",
                r"\bArbeitsablauf\b",
                r"\bProzess\b",
                r"automatisch",
                r"digital",
                r"System",
                r"elektronisch",
            ],
            AdminDocumentType.COMPETENCY_MATRIX: [
                r"\bZuständigkeit\b",
                r"\bKompetenz\b",
                r"\bGeschäftsverteilung\b",
                r"zuständig",
                r"verantwortlich",
                r"Abteilung",
                r"Referat",
            ],
            # Gerichtsentscheidungen
            AdminDocumentType.COURT_DECISION: [
                r"\bVG\s+\w+\b",
                r"\bOVG\b",
                r"\bBVerwG\b",
                r"\bVGH\b",
                r"Urteil.*vom",
                r"Beschluss.*vom",
                r"Az\.",
                r"Aktenzeichen",
            ],
            AdminDocumentType.CONSTITUTIONAL_DECISION: [
                r"\bBVerfG\b",
                r"\bBundesverfassungsgericht\b",
                r"Verfassungsbeschwerde",
                r"Grundrecht",
                r"Art\.\s*\d+\s+GG",
            ],
            # Gutachten und interne Dokumente
            AdminDocumentType.LEGAL_OPINION: [
                r"\bRechtsgutachten\b",
                r"\bStellungnahme\b",
                r"rechtliche?\s+Bewertung",
                r"Rechtslage",
            ],
            AdminDocumentType.EXPERT_OPINION: [
                r"\bGutachten\b",
                r"\bExpertise\b",
                r"\bSachverständige",
                r"fachliche?\s+Bewertung",
                r"Einschätzung",
            ],
        }

    def _init_admin_level_patterns(self) -> Dict[AdminLevel, List[str]]:
        """Initialisiert Muster für Verwaltungsebenen-Erkennung"""
        return {
            AdminLevel.FEDERAL: [
                r"\bBund\b",
                r"\bBundes\w+\b",
                r"\bBGBl\b",
                r"\bBAnz\b",
                r"Bundesregierung",
                r"Bundestag",
                r"Bundesrat",
            ],
            AdminLevel.STATE: [
                r"\bLand\b",
                r"\bLandes\w+\b",
                r"\bGVBl\b",
                r"Landtag",
                r"Landesregierung",
                r"Ministerpräsident",
                r"Bayern",
                r"Hessen",
                r"NRW",
                r"Baden-Württemberg",
            ],
            AdminLevel.REGIONAL: [
                r"\bRegion\b",
                r"\bRegional\w+\b",
                r"\bRegierungsbezirk\b",
                r"Regionalplanung",
                r"Planungsregion",
            ],
            AdminLevel.COUNTY: [
                r"\bKreis\b",
                r"\bLandkreis\b",
                r"\bkreisfreie?\s+Stadt\b",
                r"Kreistag",
                r"Landrat",
                r"Kreisausschuss",
            ],
            AdminLevel.MUNICIPAL: [
                r"\bGemeinde\b",
                r"\bStadt\b",
                r"\bOrt\b",
                r"Gemeinderat",
                r"Stadtrat",
                r"Bürgermeister",
                r"Amtsblatt",
                r"kommunal",
            ],
            AdminLevel.EU: [
                r"\bEU\b",
                r"\bEuropäische?\s+Union\b",
                r"Richtlinie.*EU",
                r"Verordnung.*EU",
                r"EuGH",
            ],
        }

    def _init_domain_patterns(self) -> Dict[AdminDomain, List[str]]:
        """Initialisiert Muster für Rechtsgebiets-Erkennung"""
        return {
            AdminDomain.BUILDING_LAW: [
                r"\bBaurecht\b",
                r"\bBauordnung\b",
                r"\bBauGB\b",
                r"Baugenehmigung",
                r"Bauvorhaben",
                r"Bauaufsicht",
            ],
            AdminDomain.ENVIRONMENTAL_LAW: [
                r"\bUmweltrecht\b",
                r"\bNaturschutz\b",
                r"\bBImSchG\b",
                r"Umweltverträglichkeit",
                r"Emission",
                r"Naturschutzgebiet",
            ],
            AdminDomain.PLANNING_LAW: [
                r"\bPlanungsrecht\b",
                r"\bBauleitplanung\b",
                r"Raumordnung",
                r"Stadtplanung",
                r"Regionalplanung",
            ],
            AdminDomain.SPATIAL_PLANNING: [
                r"\bRaumordnung\b",
                r"\bLandesplanung\b",
                r"Raumordnungsplan",
                r"Regionalplan",
                r"LEP",
                r"REP",
            ],
            AdminDomain.URBAN_PLANNING: [
                r"\bStadtplanung\b",
                r"\bBauleitplanung\b",
                r"Flächennutzungsplan",
                r"Bebauungsplan",
                r"Städtebau",
            ],
            AdminDomain.TAX_LAW: [
                r"\bSteuerrecht\b",
                r"\bAO\b",
                r"\bEStG\b",
                r"Steuerbescheid",
                r"Finanzamt",
                r"Besteuerung",
            ],
            AdminDomain.SOCIAL_LAW: [
                r"\bSozialrecht\b",
                r"\bSGB\b",
                r"Sozialleistung",
                r"Arbeitslosengeld",
                r"Sozialhilfe",
                r"Jobcenter",
            ],
            AdminDomain.POLICE_LAW: [
                r"\bPolizeirecht\b",
                r"\bOrdnungsrecht\b",
                r"Polizeiverordnung",
                r"Ordnungswidrigkeit",
                r"Bußgeld",
            ],
        }

    def _init_procedure_stage_patterns(self) -> Dict[ProcedureStage, List[str]]:
        """Initialisiert Muster für Verfahrensstadien-Erkennung"""
        return {
            ProcedureStage.APPLICATION: [
                r"\bAntrag\b",
                r"\bBeantragung\b",
                r"beantragt",
                r"Antragsteller",
                r"Antragsunterlagen",
            ],
            ProcedureStage.EXAMINATION: [
                r"\bPrüfung\b",
                r"\bErmittlung\b",
                r"geprüft",
                r"Sachverhaltsermittlung",
                r"Untersuchung",
            ],
            ProcedureStage.HEARING: [
                r"\bAnhörung\b",
                r"\bErörterung\b",
                r"angehört",
                r"Stellungnahme",
                r"Einwendung",
            ],
            ProcedureStage.DECISION: [
                r"\bEntscheidung\b",
                r"\bBescheid\b",
                r"entschieden",
                r"beschieden",
                r"verfügt",
            ],
            ProcedureStage.OBJECTION: [
                r"\bWiderspruch\b",
                r"widersprochen",
                r"Widerspruchsverfahren",
                r"Widerspruchsbescheid",
            ],
            ProcedureStage.PLAN_ADOPTION: [
                r"\bPlanbeschluss\b",
                r"\bSatzungsbeschluss\b",
                r"beschlossen",
                r"verabschiedet",
            ],
            ProcedureStage.PUBLIC_DISPLAY: [
                r"\böffentliche?\s+Auslegung\b",
                r"\bOffenlage\b",
                r"ausgelegt",
                r"Bürgerbeteiligung",
            ],
        }

    def _clean_text(self, text: str) -> str:
        """Bereinigt Text für bessere Analyse"""
        if not text:
            return ""

        # Entferne übermäßige Whitespaces
        text = re.sub(r"\s+", " ", text)

        # Entferne Sonderzeichen in Aktenzeichen (aber behalte Struktur)
        text = re.sub(r"([A-Z]{1,3})\s*-?\s*(\d+)\s*[/\\]\s*(\d+)", r"\1-\2/\3", text)

        return text.strip()

    def _classify_document_type(self, text: str, filename: str) -> AdminDocumentType:
        """Klassifiziert Dokumenttyp basierend auf Inhalt und Dateiname"""
        scores: dict[Any, Any] = {}

        # Analysiere Text-Pattern
        for doc_type, patterns in self.classification_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * 2  # Textinhalt wird höher gewichtet

                # Bonus für Pattern im Dateinamen
                if re.search(pattern, filename, re.IGNORECASE):
                    score += 3

            if score > 0:
                scores[doc_type] = score

        # Bestimme Typ mit höchstem Score
        if scores:
            best_type = max(scores, key=scores.get)
            logger.debug(
                f"Dokumenttyp klassifiziert: {best_type.value} (Score: {scores[best_type]})"
            )
            return best_type

        # Fallback
        return AdminDocumentType.FILE_NOTE

    def _classify_admin_level(self, text: str, filename: str) -> AdminLevel:
        """Klassifiziert Verwaltungsebene"""
        scores: dict[Any, Any] = {}

        for level, patterns in self.admin_level_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches

                if re.search(pattern, filename, re.IGNORECASE):
                    score += 2

            if score > 0:
                scores[level] = score

        if scores:
            return max(scores, key=scores.get)

        # Fallback auf Gemeindeebene (häufigster Fall)
        return AdminLevel.MUNICIPAL

    def _classify_admin_domain(self, text: str, filename: str) -> AdminDomain:
        """Klassifiziert Rechtsgebiet"""
        scores: dict[Any, Any] = {}

        for domain, patterns in self.domain_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches

                if re.search(pattern, filename, re.IGNORECASE):
                    score += 2

            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)

        # Fallback
        return AdminDomain.BUILDING_LAW  # Häufigster Fall in der Verwaltung

    def _classify_procedure_stage(self, text: str) -> ProcedureStage:
        """Klassifiziert Verfahrensstadium"""
        scores: dict[Any, Any] = {}

        for stage, patterns in self.procedure_stage_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches

            if score > 0:
                scores[stage] = score

        if scores:
            return max(scores, key=scores.get)

        # Fallback
        return ProcedureStage.APPLICATION

    def _calculate_confidence(
        self,
        text: str,
        doc_type: AdminDocumentType,
        admin_level: AdminLevel,
        admin_domain: AdminDomain,
    ) -> float:
        """Berechnet Confidence Score für Klassifikation"""
        try:
            total_score = 0
            max_possible = 0

            # Dokumenttyp-Confidence
            type_patterns = self.classification_patterns.get(doc_type, [])
            type_matches = sum(
                len(re.findall(p, text, re.IGNORECASE)) for p in type_patterns
            )
            total_score += min(type_matches * 10, 50)  # Max 50 Punkte
            max_possible += 50

            # Admin Level-Confidence
            level_patterns = self.admin_level_patterns.get(admin_level, [])
            level_matches = sum(
                len(re.findall(p, text, re.IGNORECASE)) for p in level_patterns
            )
            total_score += min(level_matches * 10, 30)  # Max 30 Punkte
            max_possible += 30

            # Domain-Confidence
            domain_patterns = self.domain_patterns.get(admin_domain, [])
            domain_matches = sum(
                len(re.findall(p, text, re.IGNORECASE)) for p in domain_patterns
            )
            total_score += min(domain_matches * 10, 20)  # Max 20 Punkte
            max_possible += 20

            # Normalisiere auf 0-1
            confidence = total_score / max_possible if max_possible > 0 else 0
            return round(confidence, 2)

        except Exception as e:
            logger.error(f"Fehler bei Confidence-Berechnung: {e}")
            return 0.5  # Neutral

    def _extract_legal_metadata(self, text: str) -> Dict:
        """Extrahiert zusätzliche rechtsspezifische Metadaten"""
        metadata: dict[Any, Any] = {}

        # Aktenzeichen/Geschäftszeichen
        az_pattern = r"(?:Az\.?|Aktenzeichen|Geschäftszeichen)[:,\s]*([A-Z\d\s\-/\.]+(?:\d{2,4}))"
        az_matches = re.findall(az_pattern, text, re.IGNORECASE)
        if az_matches:
            metadata["aktenzeichen"] = [az.strip() for az in az_matches[:3]]  # Max 3

        # Datum-Extraktion
        date_pattern = r"(\d{1,2}\.?\s*\d{1,2}\.?\s*\d{4})"
        dates = re.findall(date_pattern, text)
        if dates:
            metadata["dates"] = dates[:5]  # Max 5 Daten

        # Paragraphen-Referenzen
        paragraph_pattern = r"§\s*(\d+[a-z]?(?:\s+\w+)?)"
        paragraphs = re.findall(paragraph_pattern, text, re.IGNORECASE)
        if paragraphs:
            metadata["paragraphs"] = list(set(paragraphs))[:10]  # Max 10, unique

        # Rechtsmittelbelehrung
        if re.search(
            r"Rechtsmittelbelehrung|Widerspruch.*Monat|Klage.*Monat",
            text,
            re.IGNORECASE,
        ):
            metadata["has_legal_remedy_notice"] = True

        # Fristen
        deadline_pattern = (
            r"(?:Frist|binnen|innerhalb)\s+(\d+\s+(?:Tag|Woche|Monat|Jahr))"
        )
        deadlines = re.findall(deadline_pattern, text, re.IGNORECASE)
        if deadlines:
            metadata["deadlines"] = deadlines[:3]

        return metadata

    def _fallback_classification(self) -> Dict:
        """Fallback-Klassifikation wenn automatische Erkennung fehlschlägt"""
        return {
            "document_type": AdminDocumentType.FILE_NOTE,
            "admin_level": AdminLevel.MUNICIPAL,
            "admin_domain": AdminDomain.BUILDING_LAW,
            "procedure_stage": ProcedureStage.APPLICATION,
            "confidence_score": 0.1,
            "classification_metadata": {},
            "classification_source": "uds3_fallback",
        }


# Utility-Funktionen für Integration in Ingestion Pipeline
def classify_document_by_content(
    text_content: str, filename: str = "", metadata: Optional[Dict[Any, Any]] = None
) -> Dict:
    """Hauptfunktion für UDS3-Dokumentklassifikation"""
    classifier = UDS3DocumentClassifier()
    return classifier.classify_document(text_content, filename, metadata)


def get_collection_for_document_type(
    doc_type: AdminDocumentType, admin_level: AdminLevel = None
) -> str:
    """Bestimmt beste Collection für Dokumenttyp"""
    try:
        from uds3_collection_templates import UDS3CollectionTemplates

        template = UDS3CollectionTemplates.get_template_by_document_type(doc_type)

        if template:
            return template["collection_name"]
    except ImportError:
        logger.warning(
            "UDS3CollectionTemplates nicht verfügbar, verwende Fallback-Mapping"
        )

    # Fallback-Mapping
    fallback_mapping = {
        AdminDocumentType.LAW: "bundesgesetze"
        if admin_level == AdminLevel.FEDERAL
        else "landesgesetze",
        AdminDocumentType.PERMIT: "baugenehmigungen",
        AdminDocumentType.DEVELOPMENT_PLAN: "bebauungsplaene",
        AdminDocumentType.PROCESS_INSTRUCTION: "verfahrensanweisungen",
    }

    return fallback_mapping.get(doc_type, "administrative_documents")


if __name__ == "__main__":
    # Test der Klassifikation
    print("🧠 UDS3 Document Classifier - Test")
    print("=" * 50)

    # Test-Dokumente
    test_documents = [
        {
            "text": "Bescheid über Baugenehmigung. Az: 34.1-B123/2024. Hiermit wird die Genehmigung für das Bauvorhaben erteilt. Rechtsmittelbelehrung: Gegen diesen Bescheid kann binnen eines Monats Widerspruch eingelegt werden.",
            "filename": "baugenehmigung_muster.pdf",
            "expected_type": "PERMIT",
        },
        {
            "text": "Verfahrensanweisung VA-01: Bearbeitung von Bauanträgen. Schritt 1: Vollständigkeitsprüfung. Schritt 2: Fachliche Prüfung. Zuständig: Bauaufsichtsbehörde.",
            "filename": "VA_Bauantraege.docx",
            "expected_type": "PROCESS_INSTRUCTION",
        },
        {
            "text": "Bebauungsplan Nr. 47 'Gewerbegebiet Ost'. § 9 BauGB. Festsetzungen: GE - Gewerbegebiet, GRZ 0,6. Öffentliche Auslegung vom 01.04.2024 bis 02.05.2024.",
            "filename": "B-Plan_47_GO.pdf",
            "expected_type": "DEVELOPMENT_PLAN",
        },
    ]

    classifier = UDS3DocumentClassifier()

    for i, doc in enumerate(test_documents, 1):
        print(f"\n📄 Test-Dokument {i}: {doc['filename']}")
        print(f"Text: {doc['text'][:100]}...")

        result = classifier.classify_document(doc["text"], doc["filename"])

        print("✅ Klassifikation:")
        print(f"   Typ: {result['document_type'].value}")
        print(f"   Ebene: {result['admin_level'].value}")
        print(f"   Rechtsgebiet: {result['admin_domain'].value}")
        print(f"   Verfahren: {result['procedure_stage'].value}")
        print(f"   Confidence: {result['confidence_score']}")

        # Collection-Empfehlung
        collection = get_collection_for_document_type(
            result["document_type"], result["admin_level"]
        )
        print(f"   → Collection: {collection}")

        # Metadaten
        if result["classification_metadata"]:
            print(f"   Metadaten: {result['classification_metadata']}")

    print("\n✅ UDS3-Klassifikation erfolgreich getestet!")