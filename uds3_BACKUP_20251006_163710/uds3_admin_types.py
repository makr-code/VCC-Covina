#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_admin_types"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...LuOSJQ=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "f0a3e14d4d7bbc03e994eb9cdfe53a9b3db38a42697ebe7a736d14a51162046f"
)
module_file_key = "10618177fa4a28ecd6a7fe21697301a32913f14a596b8db30c3393b000ab888e"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
UDS3 Administrative Document Types
Definiert alle Dokumenttypen des Verwaltungsrechts

Kategorien:
- Normative Ebene (Gesetze, Verordnungen, Richtlinien)
- Verwaltungsentscheidungen (Bescheide, Verfügungen)
- Gerichtsentscheidungen (nur Teilbereich!)
- Verwaltungsinterne Dokumente (Aktennotizen, Gutachten)
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional


class AdminDocumentType(Enum):
    """Hauptkategorien verwaltungsrechtlicher Dokumente"""

    # Normative Ebene
    LAW = "law"  # Gesetze (Bundes-, Landes-, kommunal)
    REGULATION = "regulation"  # Rechtsverordnungen
    ORDINANCE = "ordinance"  # Satzungen, lokale Vorschriften
    DIRECTIVE = "directive"  # Verwaltungsrichtlinien, Rundschreiben
    CIRCULAR = "circular"  # Erlasse, Verwaltungsanweisungen
    IMPLEMENTATION_RULE = "impl_rule"  # Ausführungsbestimmungen

    # Verwaltungsentscheidungen
    ADMINISTRATIVE_ACT = "admin_act"  # Verwaltungsakte allgemein
    PERMIT = "permit"  # Genehmigungen, Erlaubnisse
    REJECTION = "rejection"  # Ablehnungen, Versagungen
    ORDER = "order"  # Verfügungen, Anordnungen
    PROHIBITION = "prohibition"  # Untersagungen, Verbote
    PLANNING_DECISION = "planning"  # Planfeststellungsbeschlüsse
    SUBSIDY_DECISION = "subsidy"  # Förderbescheide, Subventionen

    # Planungsrecht (eigenständiger Bereich!)
    SPATIAL_PLAN = "spatial_plan"  # Raumordnungspläne, Regionalpläne
    LAND_USE_PLAN = "land_use_plan"  # Flächennutzungspläne (FNP)
    DEVELOPMENT_PLAN = "dev_plan"  # Bebauungspläne (B-Plan)
    SECTORAL_PLAN = "sectoral_plan"  # Fachplanungen (Verkehr, Ver-/Entsorgung)
    INFRASTRUCTURE_PLAN = "infra_plan"  # Verkehrswegeplanung, Energieplanung
    ENVIRONMENTAL_PLAN = "env_plan"  # Landschaftspläne, Naturschutzplanung
    URBAN_DEVELOPMENT = "urban_dev"  # Städtebauliche Entwicklungskonzepte
    PLANNING_APPROVAL = "plan_approval"  # Planungsgenehmigungen, -änderungen
    PLANNING_PROCEDURE = "plan_proc"  # Planfeststellungsverfahren

    # Gerichtsentscheidungen (erweitert für Vector DB!)
    COURT_DECISION = "court_decision"  # Allgemeine Gerichtsentscheidungen
    CONSTITUTIONAL_DECISION = "const"  # BVerfG, LVerfG-Entscheidungen
    ADMINISTRATIVE_COURT_ORDER = "admin_court"  # VG/OVG-Beschlüsse
    JUDGMENT = "judgment"  # Urteile aller Instanzen
    EU_COURT_DECISION = "eu_court"  # EuGH, EGMR-Entscheidungen
    FINANCE_COURT = "finance_court"  # Finanzgerichtsentscheidungen
    FEDERAL_COURT_DECISION = "federal_court"  # BGH, BFH, BAG, BSG
    PRECEDENT_DECISION = "precedent"  # Präzedenzfälle, Leitentscheidungen

    # Verwaltungsinterne Dokumente
    FILE_NOTE = "file_note"  # Aktennotizen, interne Vermerke
    LEGAL_OPINION = "legal_opinion"  # Rechtsgutachten
    EXPERT_OPINION = "expert_opinion"  # Fachgutachten, Stellungnahmen
    CORRESPONDENCE = "correspondence"  # Behördenverkehr, Bürgeranfragen
    HEARING_PROTOCOL = "hearing"  # Anhörungen, Erörterungstermine
    INSPECTION_REPORT = "inspection"  # Ortsbesichtigungen, Kontrollen

    # Technische Dokumente & Standards
    TECHNICAL_STANDARD = "tech_standard"  # DIN, DIN EN, ISO-Normen
    TECHNICAL_GUIDELINE = "tech_guideline"  # TA Luft, TA Lärm, TRGS
    TECHNICAL_ASSESSMENT = "tech_assessment"  # Gutachten, Messberichte
    EVALUATION_TEMPLATE = "eval_template"  # Bewertungsvorlagen, Checklisten
    REFERENCE_DOCUMENT = "reference_doc"  # Nachschlagewerke, Handbücher

    # Interne Betriebsanweisungen (HOCH RELEVANT für Graph DB!)
    ORG_MANUAL = "org_manual"  # Organisationshandbuch
    PROCESS_INSTRUCTION = "process_instr"  # Verfahrensanweisungen, SOPs
    COMPLETION_GUIDE = "completion_guide"  # Ausfüllvorschriften, Formularhilfen
    WORKFLOW_DEFINITION = "workflow_def"  # Arbeitsablaufdefinitionen
    COMPETENCY_MATRIX = "competency_matrix"  # Zuständigkeitsregelungen
    ESCALATION_PROCEDURE = "escalation"  # Eskalationsverfahren
    DELEGATION_RULE = "delegation"  # Vertretungsregelungen


class AdminLevel(Enum):
    """Verwaltungsebenen inkl. Planungsebenen"""

    FEDERAL = "federal"  # Bundesebene
    STATE = "state"  # Landesebene
    REGIONAL = "regional"  # Regierungsbezirk/Regionalplanung
    COUNTY = "county"  # Kreis/kreisfreie Stadt
    MUNICIPAL = "municipal"  # Gemeinde/Stadt
    INTERCOMMUNAL = "intercommunal"  # Interkommunal/Zweckverbände
    EU = "eu"  # Europäische Ebene


class AdminDomain(Enum):
    """Verwaltungsbereiche (erweitert für alle Rechtsgebiete)"""

    # Klassisches Verwaltungsrecht
    BUILDING_LAW = "building"  # Baurecht
    ENVIRONMENTAL_LAW = "environment"  # Umweltrecht
    TAX_LAW = "tax"  # Steuerrecht
    SOCIAL_LAW = "social"  # Sozialrecht
    POLICE_LAW = "police"  # Polizei-/Ordnungsrecht
    BUSINESS_LAW = "business"  # Gewerberecht
    EDUCATION_LAW = "education"  # Bildungsrecht
    HEALTH_LAW = "health"  # Gesundheitsrecht
    IMMIGRATION_LAW = "immigration"  # Aufenthalts-/Asylrecht

    # Planungsrecht (eigenständiger Bereich!)
    PLANNING_LAW = "planning"  # Planungsrecht (allgemein)
    SPATIAL_PLANNING = "spatial_plan"  # Raumordnung und Landesplanung
    URBAN_PLANNING = "urban_plan"  # Stadt- und Gemeindeplanung
    SECTORAL_PLANNING = "sectoral_plan"  # Fachplanungen

    # Spezialgebiete
    DATA_PROTECTION = "data_protection"  # Datenschutzrecht
    PROCUREMENT = "procurement"  # Vergaberecht
    TECHNICAL_STANDARDS = "tech_standards"  # Technische Normung

    # NEUE ERWEITERUNG: Weitere Rechtsgebiete für Rechtsprechung
    CONSTITUTIONAL_LAW = "constitutional"  # Verfassungsrecht
    CIVIL_LAW = "civil"  # Zivilrecht
    CRIMINAL_LAW = "criminal"  # Strafrecht
    LABOR_LAW = "labor"  # Arbeitsrecht
    FINANCE_LAW = "finance"  # Finanzrecht
    EU_LAW = "eu_law"  # Europarecht

    # Interne Verwaltung
    GENERAL_ADMIN = "general_admin"  # Allgemeine Verwaltung
    PROCESS_MANAGEMENT = "process_mgmt"  # Prozessmanagement (WICHTIG für Graph DB!)
    ORGANIZATIONAL = "organizational"  # Organisationsrecht


class ProcedureStage(Enum):
    """Verfahrensstadien inkl. Planungsverfahren"""

    APPLICATION = "application"  # Antragstellung
    EXAMINATION = "examination"  # Prüfung/Ermittlung
    HEARING = "hearing"  # Anhörung
    DECISION = "decision"  # Entscheidung/Bescheid
    OBJECTION = "objection"  # Widerspruch
    LAWSUIT = "lawsuit"  # Klage vor VG
    APPEAL = "appeal"  # Berufung vor OVG
    REVISION = "revision"  # Revision vor BVerwG
    ENFORCEMENT = "enforcement"  # Vollstreckung

    # Planungsverfahren (besondere Stadien)
    PLAN_INITIATION = "plan_initiation"  # Planungsauftrag/Aufstellungsbeschluss
    EARLY_PARTICIPATION = (
        "early_participation"  # Frühzeitige Öffentlichkeitsbeteiligung
    )
    ENVIRONMENTAL_ASSESSMENT = "env_assessment"  # Umweltprüfung/SUP
    PUBLIC_DISPLAY = "public_display"  # Öffentliche Auslegung
    PLAN_ADOPTION = "plan_adoption"  # Planbeschluss/Satzungsbeschluss
    PLAN_APPROVAL = "plan_approval"  # Planungsgenehmigung
    PLAN_EFFECTIVENESS = "plan_effectiveness"  # Inkrafttreten/Rechtskraft


@dataclass
class AdminDocumentMetadata:
    """Erweiterte Metadaten für Verwaltungsdokumente"""

    document_type: AdminDocumentType
    admin_level: AdminLevel
    admin_domain: AdminDomain
    procedure_stage: Optional[ProcedureStage] = None
    authority: Optional[str] = None  # Zuständige Behörde
    case_number: Optional[str] = None  # Aktenzeichen
    legal_basis: Optional[List[str]] = None  # Rechtsgrundlagen
    deadline: Optional[str] = None  # Fristen
    parties: Optional[List[str]] = None  # Verfahrensbeteiligte
    subject_matter: Optional[str] = None  # Verfahrensgegenstand
    geographical_scope: Optional[str] = None  # Räumlicher Geltungsbereich


class DocumentTypeManager:
    """Manager für Dokumenttypen und deren Eigenschaften"""

    def __init__(self):
        self.type_hierarchies = self._create_type_hierarchies()
        self.processing_rules = self._create_processing_rules()

    def _create_type_hierarchies(self) -> Dict:
        """Erstellt Hierarchien zwischen Dokumenttypen"""
        return {
            "normative": [
                AdminDocumentType.LAW,
                AdminDocumentType.REGULATION,
                AdminDocumentType.ORDINANCE,
                AdminDocumentType.DIRECTIVE,
                AdminDocumentType.CIRCULAR,
                AdminDocumentType.IMPLEMENTATION_RULE,
            ],
            "administrative_decisions": [
                AdminDocumentType.ADMINISTRATIVE_ACT,
                AdminDocumentType.PERMIT,
                AdminDocumentType.REJECTION,
                AdminDocumentType.ORDER,
                AdminDocumentType.PROHIBITION,
                AdminDocumentType.PLANNING_DECISION,
                AdminDocumentType.SUBSIDY_DECISION,
            ],
            "planning_documents": [  # NEUE KATEGORIE!
                AdminDocumentType.SPATIAL_PLAN,
                AdminDocumentType.LAND_USE_PLAN,
                AdminDocumentType.DEVELOPMENT_PLAN,
                AdminDocumentType.SECTORAL_PLAN,
                AdminDocumentType.INFRASTRUCTURE_PLAN,
                AdminDocumentType.ENVIRONMENTAL_PLAN,
                AdminDocumentType.URBAN_DEVELOPMENT,
                AdminDocumentType.PLANNING_APPROVAL,
                AdminDocumentType.PLANNING_PROCEDURE,
            ],
            "judicial_decisions": [
                AdminDocumentType.COURT_DECISION,
                AdminDocumentType.CONSTITUTIONAL_DECISION,
                AdminDocumentType.EU_COURT_DECISION,
                AdminDocumentType.FINANCE_COURT,
            ],
            "internal_documents": [
                AdminDocumentType.FILE_NOTE,
                AdminDocumentType.LEGAL_OPINION,
                AdminDocumentType.EXPERT_OPINION,
                AdminDocumentType.CORRESPONDENCE,
                AdminDocumentType.HEARING_PROTOCOL,
                AdminDocumentType.INSPECTION_REPORT,
            ],
            "technical_documents": [
                AdminDocumentType.TECHNICAL_STANDARD,
                AdminDocumentType.TECHNICAL_GUIDELINE,
                AdminDocumentType.TECHNICAL_ASSESSMENT,
                AdminDocumentType.EVALUATION_TEMPLATE,
                AdminDocumentType.REFERENCE_DOCUMENT,
            ],
            "process_management": [  # HOCH RELEVANT für Graph DB!
                AdminDocumentType.ORG_MANUAL,
                AdminDocumentType.PROCESS_INSTRUCTION,
                AdminDocumentType.COMPLETION_GUIDE,
                AdminDocumentType.WORKFLOW_DEFINITION,
                AdminDocumentType.COMPETENCY_MATRIX,
                AdminDocumentType.ESCALATION_PROCEDURE,
                AdminDocumentType.DELEGATION_RULE,
            ],
        }

    def _create_processing_rules(self) -> Dict:
        """Definiert spezifische Verarbeitungsregeln pro Dokumenttyp"""
        return {
            AdminDocumentType.LAW: {
                "extract_paragraphs": True,
                "extract_articles": True,
                "create_norm_hierarchy": True,
                "index_legal_references": True,
                "track_amendments": True,
            },
            AdminDocumentType.ADMINISTRATIVE_ACT: {
                "extract_case_number": True,
                "extract_parties": True,
                "extract_deadlines": True,
                "extract_legal_basis": True,
                "track_procedure_stage": True,
                "monitor_legal_remedies": True,
            },
            AdminDocumentType.COURT_DECISION: {
                "extract_court_level": True,
                "extract_case_law_refs": True,
                "extract_legal_principles": True,
                "create_precedent_links": True,
            },
            AdminDocumentType.FILE_NOTE: {
                "extract_internal_refs": True,
                "track_authorship": True,
                "maintain_confidentiality": True,
                "link_to_main_procedure": True,
            },
            AdminDocumentType.TECHNICAL_STANDARD: {
                "extract_standard_number": True,
                "track_version_history": True,
                "create_reference_links": True,
                "map_application_domains": True,
            },
            AdminDocumentType.TECHNICAL_GUIDELINE: {
                "extract_limit_values": True,
                "map_legal_basis": True,
                "track_updates": True,
                "create_compliance_links": True,
            },
            # PROZESSMANAGEMENT - HOCH RELEVANT für Graph DB!
            AdminDocumentType.ORG_MANUAL: {
                "extract_org_structure": True,
                "map_responsibilities": True,
                "create_hierarchy_graph": True,
                "track_reporting_lines": True,
                "enable_workflow_mapping": True,
            },
            AdminDocumentType.PROCESS_INSTRUCTION: {
                "extract_process_steps": True,
                "map_decision_points": True,
                "create_workflow_graph": True,
                "identify_stakeholders": True,
                "track_process_dependencies": True,
                "enable_automation_hints": True,
            },
            AdminDocumentType.COMPLETION_GUIDE: {
                "extract_form_fields": True,
                "map_validation_rules": True,
                "create_guidance_links": True,
                "track_legal_requirements": True,
            },
            AdminDocumentType.WORKFLOW_DEFINITION: {
                "extract_workflow_steps": True,
                "map_actor_roles": True,
                "identify_triggers": True,
                "create_state_transitions": True,
                "enable_process_mining": True,
            },
            AdminDocumentType.COMPETENCY_MATRIX: {
                "extract_role_definitions": True,
                "map_authority_levels": True,
                "create_delegation_chains": True,
                "track_signature_rights": True,
            },
            # PLANUNGSRECHT - Eigene Verarbeitungsregeln
            AdminDocumentType.SPATIAL_PLAN: {
                "extract_planning_objectives": True,
                "map_spatial_boundaries": True,
                "identify_land_use_categories": True,
                "track_plan_hierarchy": True,
                "extract_planning_principles": True,
            },
            AdminDocumentType.LAND_USE_PLAN: {
                "extract_land_use_designations": True,
                "map_zoning_boundaries": True,
                "identify_development_areas": True,
                "track_plan_amendments": True,
                "link_to_development_plans": True,
            },
            AdminDocumentType.DEVELOPMENT_PLAN: {
                "extract_building_regulations": True,
                "map_plot_boundaries": True,
                "identify_building_lines": True,
                "extract_design_requirements": True,
                "track_plan_variants": True,
                "calculate_development_potential": True,
            },
            AdminDocumentType.SECTORAL_PLAN: {
                "extract_infrastructure_networks": True,
                "map_service_areas": True,
                "identify_technical_requirements": True,
                "track_implementation_phases": True,
            },
            AdminDocumentType.PLANNING_PROCEDURE: {
                "extract_procedure_steps": True,
                "map_stakeholder_involvement": True,
                "track_participation_phases": True,
                "identify_approval_requirements": True,
                "monitor_legal_deadlines": True,
            },
        }

    def get_document_category(self, doc_type: AdminDocumentType) -> str:
        """Ermittelt die Hauptkategorie eines Dokumenttyps"""
        for category, types in self.type_hierarchies.items():
            if doc_type in types:
                return category
        return "unknown"

    def get_processing_rules(self, doc_type: AdminDocumentType) -> Dict:
        """Liefert spezifische Verarbeitungsregeln für einen Dokumenttyp"""
        return self.processing_rules.get(doc_type, {})

    def suggest_relationships(self, doc_type: AdminDocumentType) -> List[str]:
        """Schlägt typische Beziehungen für einen Dokumenttyp vor"""
        suggestions = {
            AdminDocumentType.LAW: ["AMENDED_BY", "IMPLEMENTED_BY", "CITED_BY"],
            AdminDocumentType.REGULATION: ["BASED_ON", "IMPLEMENTS", "SUPERSEDES"],
            AdminDocumentType.ADMINISTRATIVE_ACT: [
                "BASED_ON",
                "APPEALS_TO",
                "ENFORCES",
            ],
            AdminDocumentType.COURT_DECISION: ["REVIEWS", "CITES", "OVERRULES"],
            AdminDocumentType.FILE_NOTE: ["RELATES_TO", "DOCUMENTS", "SUPPORTS"],
            # Technische Dokumente
            AdminDocumentType.TECHNICAL_STANDARD: [
                "REFERENCES",
                "SUPERSEDES",
                "APPLIED_IN",
            ],
            AdminDocumentType.TECHNICAL_GUIDELINE: [
                "BASED_ON_STANDARD",
                "IMPLEMENTS",
                "GUIDES",
            ],
            AdminDocumentType.TECHNICAL_ASSESSMENT: [
                "APPLIES_STANDARD",
                "EVALUATES",
                "RECOMMENDS",
            ],
            # Prozessmanagement (SEHR REICH an Beziehungen für Graph DB!)
            AdminDocumentType.ORG_MANUAL: [
                "DEFINES_STRUCTURE",
                "ASSIGNS_ROLES",
                "ESTABLISHES_HIERARCHY",
            ],
            AdminDocumentType.PROCESS_INSTRUCTION: [
                "IMPLEMENTS_WORKFLOW",
                "REQUIRES_ROLE",
                "TRIGGERS_ACTION",
                "DEPENDS_ON",
            ],
            AdminDocumentType.COMPLETION_GUIDE: [
                "SUPPORTS_PROCESS",
                "VALIDATES_INPUT",
                "GUIDES_USER",
            ],
            AdminDocumentType.WORKFLOW_DEFINITION: [
                "DEFINES_FLOW",
                "ASSIGNS_ACTOR",
                "TRIGGERS",
                "TRANSITIONS_TO",
            ],
            AdminDocumentType.COMPETENCY_MATRIX: [
                "AUTHORIZES",
                "DELEGATES_TO",
                "REQUIRES_APPROVAL",
                "ESCALATES_TO",
            ],
            AdminDocumentType.ESCALATION_PROCEDURE: [
                "ESCALATES_FROM",
                "NOTIFIES",
                "TRIGGERS_REVIEW",
            ],
            AdminDocumentType.DELEGATION_RULE: [
                "DELEGATES_AUTHORITY",
                "SUBSTITUTES_FOR",
                "TEMPORARY_ASSIGNMENT",
            ],
            # Planungsrecht (KOMPLEX an Beziehungen!)
            AdminDocumentType.SPATIAL_PLAN: [
                "GUIDES",
                "CONSTRAINS",
                "PROVIDES_FRAMEWORK",
                "SUPERSEDES",
            ],
            AdminDocumentType.LAND_USE_PLAN: [
                "DERIVES_FROM",
                "IMPLEMENTS",
                "CONSTRAINS_DEVELOPMENT",
            ],
            AdminDocumentType.DEVELOPMENT_PLAN: [
                "IMPLEMENTS_LAND_USE",
                "SPECIFIES",
                "ENABLES_DEVELOPMENT",
            ],
            AdminDocumentType.SECTORAL_PLAN: [
                "COORDINATES_WITH",
                "INTEGRATES",
                "SERVES",
            ],
            AdminDocumentType.INFRASTRUCTURE_PLAN: ["SUPPORTS", "CONNECTS", "ENABLES"],
            AdminDocumentType.ENVIRONMENTAL_PLAN: [
                "PROTECTS",
                "COMPENSATES",
                "MITIGATES",
            ],
            AdminDocumentType.PLANNING_PROCEDURE: [
                "ESTABLISHES_PLAN",
                "INVOLVES_STAKEHOLDER",
                "REQUIRES_APPROVAL",
            ],
            AdminDocumentType.PLANNING_APPROVAL: [
                "APPROVES_PLAN",
                "CONDITIONS",
                "ENABLES_IMPLEMENTATION",
            ],
        }
        return suggestions.get(doc_type, ["RELATES_TO"])


# Factory Functions
def create_document_type_manager() -> DocumentTypeManager:
    """Factory für DocumentTypeManager"""
    return DocumentTypeManager()


def classify_document_type(
    title: str, content: str, metadata: Dict
) -> AdminDocumentType:
    """Automatische Klassifikation des Dokumenttyps basierend auf Inhalt"""

    title_lower = title.lower()
    content_lower = content.lower()

    # Gesetze
    if any(word in title_lower for word in ["gesetz", "bgb", "stgb", "vwvfg", "baugb"]):
        return AdminDocumentType.LAW

    # Verordnungen
    if any(word in title_lower for word in ["verordnung", "vo", "bauvo", "lbo"]):
        return AdminDocumentType.REGULATION

    # Bescheide
    if any(word in title_lower for word in ["bescheid", "genehmigung", "ablehnung"]):
        if "genehm" in title_lower:
            return AdminDocumentType.PERMIT
        elif "ableh" in title_lower or "versag" in title_lower:
            return AdminDocumentType.REJECTION
        else:
            return AdminDocumentType.ADMINISTRATIVE_ACT

    # Gerichtsentscheidungen
    if any(
        word in title_lower for word in ["urteil", "beschluss", "bverwg", "vg ", "ovg"]
    ):
        return AdminDocumentType.COURT_DECISION

    # Technische Dokumente
    if any(
        word in title_lower
        for word in ["din ", "din en", "iso ", "ta luft", "ta lärm", "trgs"]
    ):
        if any(word in title_lower for word in ["din ", "iso ", "en "]):
            return AdminDocumentType.TECHNICAL_STANDARD
        else:
            return AdminDocumentType.TECHNICAL_GUIDELINE

    # Gutachten und Bewertungen
    if any(
        word in title_lower for word in ["gutachten", "bewertung", "messber", "prüfber"]
    ):
        return AdminDocumentType.TECHNICAL_ASSESSMENT

    # Prozessmanagement (WICHTIG!)
    if any(
        word in title_lower
        for word in ["organisationshandbuch", "geschäftsord", "verfahrensanw"]
    ):
        return AdminDocumentType.ORG_MANUAL

    if any(
        word in title_lower
        for word in ["arbeitsanw", "ausfüllvor", "leitfaden", "handlungsanw"]
    ):
        if "ausfüll" in title_lower:
            return AdminDocumentType.COMPLETION_GUIDE
        else:
            return AdminDocumentType.PROCESS_INSTRUCTION

    if any(word in title_lower for word in ["workflow", "arbeitsablauf", "prozessdef"]):
        return AdminDocumentType.WORKFLOW_DEFINITION

    if any(word in title_lower for word in ["zuständigk", "kompetenz", "befugnis"]):
        return AdminDocumentType.COMPETENCY_MATRIX

    # Vorlagen und Checklisten
    if any(word in title_lower for word in ["vorlage", "checkliste", "formular"]):
        return AdminDocumentType.EVALUATION_TEMPLATE

    # Planungsdokumente (WICHTIGER BEREICH!)
    if any(word in title_lower for word in ["flächennutzungsplan", "fnp", "f-plan"]):
        return AdminDocumentType.LAND_USE_PLAN

    if any(word in title_lower for word in ["bebauungsplan", "b-plan", "bplan"]):
        return AdminDocumentType.DEVELOPMENT_PLAN

    if any(
        word in title_lower
        for word in ["regionalplan", "landesentwicklungsplan", "raumordnung"]
    ):
        return AdminDocumentType.SPATIAL_PLAN

    if any(
        word in title_lower
        for word in ["landschaftsplan", "grünordnungsplan", "umweltplan"]
    ):
        return AdminDocumentType.ENVIRONMENTAL_PLAN

    if any(
        word in title_lower
        for word in ["verkehrsplan", "infrastrukturplan", "erschließungsplan"]
    ):
        return AdminDocumentType.INFRASTRUCTURE_PLAN

    if any(word in title_lower for word in ["fachplanung", "sektoralplanung"]):
        return AdminDocumentType.SECTORAL_PLAN

    if any(
        word in title_lower
        for word in ["städtebaulich", "stadtentwicklung", "ortsentwicklung"]
    ):
        return AdminDocumentType.URBAN_DEVELOPMENT

    if any(
        word in title_lower
        for word in ["planfeststellung", "planfeststellungsverfahren"]
    ):
        return AdminDocumentType.PLANNING_PROCEDURE

    if any(word in title_lower for word in ["planungsgenehmigung", "plangenehmigung"]):
        return AdminDocumentType.PLANNING_APPROVAL

    # Aktennotizen
    if any(word in title_lower for word in ["notiz", "vermerk", "protokoll"]):
        return AdminDocumentType.FILE_NOTE

    # Default
    return AdminDocumentType.FILE_NOTE


# Export
__all__ = [
    "AdminDocumentType",
    "AdminLevel",
    "AdminDomain",
    "ProcedureStage",
    "AdminDocumentMetadata",
    "DocumentTypeManager",
    "create_document_type_manager",
    "classify_document_type",
]

if __name__ == "__main__":
    print("🏛️ UDS3 Administrative Document Types Demo")
    print("=" * 50)

    # Document Type Manager erstellen
    type_mgr = create_document_type_manager()

    # Test verschiedener Dokumenttypen
    test_cases = [
        ("Baugesetzbuch (BauGB)", "Baugesetzbuch in der Fassung..."),
        (
            "Baugenehmigung Musterstraße 123",
            "Hiermit wird die Baugenehmigung erteilt...",
        ),
        ("Ablehnungsbescheid Gewerbeanmeldung", "Der Antrag wird abgelehnt..."),
        ("VG München Urteil", "Das Verwaltungsgericht München entscheidet..."),
        ("Aktennotiz Besprechung", "Vermerk über die Besprechung vom..."),
        ("DIN EN 1090 Ausführung von Stahltragwerken", "Diese Norm gilt für..."),
        (
            "TA Luft - Technische Anleitung zur Reinhaltung der Luft",
            "Erste Allgemeine Verwaltungsvorschrift...",
        ),
        (
            "Schalltechnisches Gutachten Neubaugebiet",
            "Das vorliegende Gutachten untersucht...",
        ),
        (
            "Organisationshandbuch Bauamt",
            "Organisationsstruktur und Zuständigkeiten...",
        ),
        ("Ausfüllvorschrift Bauantrag", "Hinweise zum Ausfüllen des Bauantrags..."),
        (
            "Arbeitsanweisung Baugenehmigungsverfahren",
            "Schritt-für-Schritt Anleitung...",
        ),
        (
            "Zuständigkeitsregelung Baugenehmigungen",
            "Matrix der Entscheidungsbefugnisse...",
        ),
        # Planungsrecht - Neue Testfälle
        (
            "Flächennutzungsplan Stadt Musterstadt",
            "Der Flächennutzungsplan stellt die beabsichtigte Art der Bodennutzung dar...",
        ),
        (
            "Bebauungsplan Wohngebiet Nord",
            "Bebauungsplan für das geplante Wohngebiet...",
        ),
        ("Regionalplan Südhessen", "Regionalplan für die Planungsregion Südhessen..."),
        (
            "Landschaftsplan Gemeinde Beispielort",
            "Landschaftsplan zur Sicherung der Leistungsfähigkeit des Naturhaushalts...",
        ),
        (
            "Verkehrsplanung Ortsumgehung B123",
            "Planung der Ortsumgehung für die Bundesstraße...",
        ),
        (
            "Planfeststellungsverfahren Windpark",
            "Verfahren zur Planfeststellung für den geplanten Windpark...",
        ),
    ]

    for title, content in test_cases:
        doc_type = classify_document_type(title, content, {})
        category = type_mgr.get_document_category(doc_type)
        rules = type_mgr.get_processing_rules(doc_type)
        relationships = type_mgr.suggest_relationships(doc_type)

        print(f"\n📄 '{title}'")
        print(f"   Typ: {doc_type.value}")
        print(f"   Kategorie: {category}")
        print(f"   Verarbeitungsregeln: {len(rules)} definiert")
        print(f"   Vorgeschlagene Beziehungen: {', '.join(relationships[:3])}")

    print("\n📊 Statistik:")
    print(f"   Dokumenttypen: {len(AdminDocumentType)}")
    print(f"   Verwaltungsebenen: {len(AdminLevel)}")
    print(f"   Verwaltungsbereiche: {len(AdminDomain)}")
    print(f"   Verfahrensstadien: {len(ProcedureStage)}")

    print("\n🎉 Administrative Document Types Demo abgeschlossen!")
