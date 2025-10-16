#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_collection_templates"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...CvVlpw=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "10cebe9fe0a4f60051b0f515dc4d02d37b6c00791f9e4c18de24117e71247aa9"
)
module_file_key = "f4e17de2ed33a3de335c6583cb11f6e05e5de59eba2a3c30bbc335599a3126f4"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
UDS3 Collection Templates - Vordefinierte Collection-Konfigurationen für Verwaltungsrecht

Dieses Modul stellt Templates für verschiedene administrative Dokumenttypen bereit,
die direkt in die bestehende Collection-Manager-Infrastruktur integriert werden können.
"""

from typing import Dict
from uds3_admin_types import AdminDocumentType, AdminLevel, AdminDomain, ProcedureStage


class UDS3CollectionTemplates:
    """Vordefinierte Collection-Templates für verschiedene Verwaltungsrecht-Bereiche"""

    @staticmethod
    def get_all_templates() -> Dict[str, Dict]:
        """Alle verfügbaren Collection-Templates"""
        return {
            # Normative Ebene - Gesetze & Verordnungen
            "bundesgesetze": UDS3CollectionTemplates.federal_laws_template(),
            "landesgesetze": UDS3CollectionTemplates.state_laws_template(),
            "kommunale_satzungen": UDS3CollectionTemplates.municipal_ordinances_template(),
            # NEUE ERGÄNZUNG: Detailliertes Landesrecht
            "brandenburg_recht": UDS3CollectionTemplates.brandenburg_law_template(),
            "verwaltungsvorschriften": UDS3CollectionTemplates.administrative_regulations_template(),
            # NEUE ERGÄNZUNG: Rechtsprechung (Vector DB optimiert für Ähnlichkeitssuche!)
            "bundesrechtsprechung": UDS3CollectionTemplates.federal_court_decisions_template(),
            "verwaltungsrechtsprechung": UDS3CollectionTemplates.administrative_court_decisions_template(),
            "verfassungsrechtsprechung": UDS3CollectionTemplates.constitutional_court_decisions_template(),
            # Verwaltungsentscheidungen
            "verwaltungsakte": UDS3CollectionTemplates.admin_acts_template(),
            "baugenehmigungen": UDS3CollectionTemplates.building_permits_template(),
            # Planungsrecht (eigenständiger Bereich!)
            "raumordnungsplaene": UDS3CollectionTemplates.spatial_plans_template(),
            "flaechennutzungsplaene": UDS3CollectionTemplates.land_use_plans_template(),
            "bebauungsplaene": UDS3CollectionTemplates.development_plans_template(),
            # Betriebsanweisungen (HOCH RELEVANT für Graph DB!)
            "verfahrensanweisungen": UDS3CollectionTemplates.process_instructions_template(),
            "arbeitsablaeufe": UDS3CollectionTemplates.workflow_definitions_template(),
            "zustaendigkeiten": UDS3CollectionTemplates.competency_matrix_template(),
        }

    # Normative Ebene Templates
    @staticmethod
    def federal_laws_template() -> Dict:
        """Template für Bundesgesetze"""
        return {
            "collection_name": "bundesgesetze",
            "display_name": "Bundesgesetze & Bundesverordnungen",
            "collection_type": "administrative",
            "rechtsgebiet": "Verfassungsrecht, Verwaltungsrecht",
            "description": "Gesetze und Verordnungen auf Bundesebene",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.LAW,
                    AdminDocumentType.REGULATION,
                    AdminDocumentType.IMPLEMENTATION_RULE,
                ],
                "admin_level": AdminLevel.FEDERAL,
                "admin_domains": [
                    AdminDomain.BUILDING_LAW,
                    AdminDomain.ENVIRONMENTAL_LAW,
                    AdminDomain.TAX_LAW,
                    AdminDomain.SOCIAL_LAW,
                ],
                "processing_stages": [
                    ProcedureStage.PLAN_EFFECTIVENESS,
                    ProcedureStage.DECISION,
                ],
                "requires_legal_review": True,
                "classification_rules": {
                    "auto_classify": True,
                    "keywords": [
                        "§",
                        "Artikel",
                        "Gesetz",
                        "Verordnung",
                        "BGBl",
                        "BAnz",
                    ],
                    "normative_indicators": ["erlassen", "beschlossen", "verkündet"],
                },
            },
            "metadata_schema": {
                "required_fields": [
                    "title",
                    "publication_date",
                    "bgbl_reference",
                    "legal_basis",
                ],
                "optional_fields": [
                    "amendment_history",
                    "related_laws",
                    "eu_directive",
                ],
            },
        }

    @staticmethod
    def state_laws_template() -> Dict:
        """Template für Landesgesetze"""
        return {
            "collection_name": "landesgesetze",
            "display_name": "Landesgesetze & Landesverordnungen",
            "collection_type": "administrative",
            "rechtsgebiet": "Landesrecht, Bauordnungsrecht",
            "description": "Gesetze und Verordnungen der Bundesländer",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.LAW,
                    AdminDocumentType.REGULATION,
                    AdminDocumentType.ORDINANCE,
                ],
                "admin_level": AdminLevel.STATE,
                "admin_domains": [
                    AdminDomain.BUILDING_LAW,
                    AdminDomain.SPATIAL_PLANNING,
                    AdminDomain.POLICE_LAW,
                    AdminDomain.EDUCATION_LAW,
                ],
                "processing_stages": [
                    ProcedureStage.PLAN_EFFECTIVENESS,
                    ProcedureStage.DECISION,
                ],
                "requires_legal_review": True,
                "state_specific": True,
                "classification_rules": {
                    "keywords": ["LandesBauO", "LPLG", "NatSchG", "GVBl"],
                    "state_indicators": ["Land", "Freistaat", "Hansestadt"],
                },
            },
        }

    @staticmethod
    def municipal_ordinances_template() -> Dict:
        """Template für Kommunale Satzungen"""
        return {
            "collection_name": "kommunale_satzungen",
            "display_name": "Kommunale Satzungen & Ordnungen",
            "collection_type": "administrative",
            "rechtsgebiet": "Kommunalrecht, Ortsrecht",
            "description": "Satzungen, Verordnungen und Ordnungen von Gemeinden und Städten",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.ORDINANCE,
                    AdminDocumentType.CIRCULAR,
                    AdminDocumentType.ORDER,
                ],
                "admin_level": AdminLevel.MUNICIPAL,
                "admin_domains": [
                    AdminDomain.URBAN_PLANNING,
                    AdminDomain.BUILDING_LAW,
                    AdminDomain.BUSINESS_LAW,
                ],
                "municipal_specific": True,
                "classification_rules": {
                    "keywords": [
                        "Satzung",
                        "Ordnung",
                        "Verordnung",
                        "Gemeindeblatt",
                        "Amtsblatt",
                    ],
                    "municipal_indicators": ["Gemeinde", "Stadt", "Kreis", "Landkreis"],
                },
            },
        }

    # === NEUE TEMPLATES: SPEZIFISCHES LANDESRECHT ===

    @staticmethod
    def brandenburg_law_template() -> Dict:
        """Template speziell für Brandenburg-Recht (für BRAVORS-Integration!)"""
        return {
            "collection_name": "brandenburg_recht",
            "display_name": "Brandenburg Recht & BRAVORS",
            "collection_type": "administrative",
            "rechtsgebiet": "Brandenburg Landesrecht",
            "description": "Spezialisiert für Brandenburg: Gesetze, Verordnungen und Verwaltungsvorschriften aus BRAVORS",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.LAW,
                    AdminDocumentType.REGULATION,
                    AdminDocumentType.DIRECTIVE,
                    AdminDocumentType.CIRCULAR,
                ],
                "admin_level": AdminLevel.STATE,
                "admin_domains": [
                    AdminDomain.BUILDING_LAW,
                    AdminDomain.ENVIRONMENTAL_LAW,
                    AdminDomain.SPATIAL_PLANNING,
                    AdminDomain.POLICE_LAW,
                ],
                "processing_stages": [
                    ProcedureStage.PLAN_EFFECTIVENESS,
                    ProcedureStage.DECISION,
                ],
                "requires_legal_review": True,
                "state_specific": "Brandenburg",
                "bravors_integration": True,
                "classification_rules": {
                    "auto_classify": True,
                    "keywords": [
                        "Brandenburg",
                        "BRAVORS",
                        "BbgBO",
                        "BbgNatSchAG",
                        "BbgWG",
                        "GVBl Brandenburg",
                    ],
                    "brandenburg_indicators": [
                        "Landesbauordnung Brandenburg",
                        "Brandenburgisches",
                        "Land Brandenburg",
                    ],
                    "bravors_patterns": [
                        "verwaltungsvorschriften/",
                        "brandenburg.de",
                        "Rundschreiben",
                        "Erlass",
                    ],
                },
            },
            "metadata_schema": {
                "required_fields": [
                    "title",
                    "publication_date",
                    "bravors_url",
                    "legal_basis",
                    "ministry",
                ],
                "optional_fields": [
                    "amendment_history",
                    "related_laws",
                    "implementation_date",
                    "validity_period",
                ],
                "brandenburg_fields": [
                    "issuing_ministry",
                    "administrative_level",
                    "reference_number",
                ],
            },
            "scraping_integration": {
                "bravors_compatible": True,
                "auto_import": True,
                "update_frequency": "weekly",
            },
        }

    @staticmethod
    def administrative_regulations_template() -> Dict:
        """Template für Verwaltungsvorschriften (perfekt für BRAVORS-Dokumente!)"""
        return {
            "collection_name": "verwaltungsvorschriften",
            "display_name": "Verwaltungsvorschriften & Rundschreiben",
            "collection_type": "administrative",
            "rechtsgebiet": "Verwaltungsrecht, Administrative Richtlinien",
            "description": "Verwaltungsvorschriften, Rundschreiben, Erlasse und Dienstanweisungen",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.DIRECTIVE,
                    AdminDocumentType.CIRCULAR,
                    AdminDocumentType.IMPLEMENTATION_RULE,
                ],
                "admin_level": "ANY",  # Bund, Länder, Kommunen
                "admin_domains": [
                    AdminDomain.GENERAL_ADMIN,
                    AdminDomain.TAX_LAW,
                    AdminDomain.SOCIAL_LAW,
                    AdminDomain.BUILDING_LAW,
                ],
                "internal_binding": True,  # Intern bindend für Verwaltung
                "classification_rules": {
                    "keywords": [
                        "Verwaltungsvorschrift",
                        "Rundschreiben",
                        "Erlass",
                        "Dienstanweisung",
                        "Richtlinie",
                    ],
                    "admin_indicators": [
                        "VV",
                        "RdSchr",
                        "Erl.",
                        "Dienstanweisung",
                        "Geschäftsanweisung",
                    ],
                    "ministry_patterns": [
                        "Ministerium",
                        "Senatsverwaltung",
                        "Bezirksregierung",
                    ],
                },
            },
            "special_features": {
                "internal_document": True,
                "binding_only_for_administration": True,
                "frequent_updates": True,
                "ministry_coordination": True,
            },
        }

    # === NEUE TEMPLATES: RECHTSPRECHUNG (VECTOR DB OPTIMIERT!) ===

    @staticmethod
    def federal_court_decisions_template() -> Dict:
        """Template für Bundesrechtsprechung (VECTOR DB OPTIMIERT für Ähnlichkeitssuche!)"""
        return {
            "collection_name": "bundesrechtsprechung",
            "display_name": "Bundesrechtsprechung (BGH, BFH, BAG, BSG, BVerwG)",
            "collection_type": "jurisprudence",
            "rechtsgebiet": "Bundesrechtsprechung, Höchstrichterliche Rechtsprechung",
            "description": "Entscheidungen der obersten Bundesgerichte - optimiert für semantische Ähnlichkeitssuche",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.COURT_DECISION,
                    AdminDocumentType.JUDGMENT,
                    AdminDocumentType.ORDER,
                ],
                "admin_level": AdminLevel.FEDERAL,
                "court_types": ["BGH", "BFH", "BAG", "BSG", "BVerwG", "BVerfG"],
                "vector_optimized": True,  # HOCHRELEVANT für Vector DB!
                "semantic_search_priority": True,
                "precedent_analysis": True,
                "classification_rules": {
                    "keywords": [
                        "BGH",
                        "BFH",
                        "BAG",
                        "BSG",
                        "BVerwG",
                        "BVerfG",
                        "Urteil",
                        "Beschluss",
                    ],
                    "court_indicators": [
                        "Senat",
                        "Az.",
                        "Aktenzeichen",
                        "vom",
                        "Entscheidung",
                    ],
                    "legal_indicators": [
                        "Revision",
                        "Berufung",
                        "Verfassungsbeschwerde",
                        "Rechtssache",
                    ],
                },
            },
            "vector_db_config": {
                "chunk_strategy": "legal_paragraphs",  # Chunking nach Rechtssätzen
                "embedding_focus": "legal_reasoning",  # Fokus auf Rechtsprechung
                "similarity_threshold": 0.75,
                "cross_court_comparison": True,
                "precedent_tracking": True,
            },
            "metadata_schema": {
                "required_fields": [
                    "court",
                    "case_number",
                    "decision_date",
                    "legal_area",
                    "key_legal_issues",
                ],
                "optional_fields": [
                    "previous_instance",
                    "legal_basis",
                    "cited_cases",
                    "dissenting_opinion",
                ],
                "search_fields": [
                    "legal_principles",
                    "fact_pattern",
                    "reasoning",
                    "outcome",
                ],
            },
        }

    @staticmethod
    def administrative_court_decisions_template() -> Dict:
        """Template für Verwaltungsrechtsprechung (perfekt für VG/OVG/BVerwG!)"""
        return {
            "collection_name": "verwaltungsrechtsprechung",
            "display_name": "Verwaltungsrechtsprechung (VG, OVG, BVerwG)",
            "collection_type": "jurisprudence",
            "rechtsgebiet": "Verwaltungsrecht, Verwaltungsprozessrecht",
            "description": "Entscheidungen der Verwaltungsgerichtsbarkeit - optimiert für Verwaltungsrechtspraxis",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.COURT_DECISION,
                    AdminDocumentType.ADMINISTRATIVE_COURT_ORDER,
                ],
                "admin_level": "ALL",  # VG (Länder), OVG (Länder), BVerwG (Bund)
                "court_types": ["VG", "OVG", "BVerwG"],
                "admin_domains": [
                    AdminDomain.BUILDING_LAW,
                    AdminDomain.ENVIRONMENTAL_LAW,
                    AdminDomain.POLICE_LAW,
                    AdminDomain.SPATIAL_PLANNING,
                ],
                "vector_optimized": True,
                "administrative_focus": True,
                "classification_rules": {
                    "keywords": [
                        "VG",
                        "OVG",
                        "BVerwG",
                        "Verwaltungsgericht",
                        "Oberverwaltungsgericht",
                    ],
                    "admin_court_indicators": [
                        "Klage",
                        "Widerspruch",
                        "Verwaltungsakt",
                        "Ermessen",
                    ],
                    "procedure_types": [
                        "Anfechtungsklage",
                        "Verpflichtungsklage",
                        "Feststellungsklage",
                    ],
                },
            },
            "admin_law_focus": {
                "discretionary_review": True,
                "administrative_act_analysis": True,
                "procedure_compliance": True,
                "competency_disputes": True,
            },
        }

    @staticmethod
    def constitutional_court_decisions_template() -> Dict:
        """Template für Verfassungsrechtsprechung (BVerfG - höchste Relevanz!)"""
        return {
            "collection_name": "verfassungsrechtsprechung",
            "display_name": "Verfassungsrechtsprechung (BVerfG)",
            "collection_type": "jurisprudence",
            "rechtsgebiet": "Verfassungsrecht, Grundrechte",
            "description": "Entscheidungen des Bundesverfassungsgerichts - verfassungsrechtliche Grundsatzentscheidungen",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.CONSTITUTIONAL_DECISION,
                    AdminDocumentType.COURT_DECISION,
                ],
                "admin_level": AdminLevel.FEDERAL,
                "court_types": ["BVerfG"],
                "constitutional_priority": True,
                "highest_precedent_value": True,
                "vector_optimized": True,
                "classification_rules": {
                    "keywords": [
                        "BVerfG",
                        "Bundesverfassungsgericht",
                        "Verfassungsbeschwerde",
                        "Grundrecht",
                    ],
                    "constitutional_indicators": [
                        "Art.",
                        "GG",
                        "Verfassung",
                        "verfassungswidrig",
                        "verfassungsgemäß",
                    ],
                    "procedure_types": [
                        "Verfassungsbeschwerde",
                        "abstrakte Normenkontrolle",
                        "konkrete Normenkontrolle",
                    ],
                },
            },
            "constitutional_analysis": {
                "fundamental_rights_review": True,
                "proportionality_analysis": True,
                "separation_of_powers": True,
                "federalism_issues": True,
            },
        }

    # Planungsrecht Templates
    @staticmethod
    def spatial_plans_template() -> Dict:
        """Template für Raumordnungspläne"""
        return {
            "collection_name": "raumordnungsplaene",
            "display_name": "Raumordnung & Regionalpläne",
            "collection_type": "planning",
            "rechtsgebiet": "Raumordnungsrecht, Regionalplanung",
            "description": "Raumordnungspläne, Regionalpläne und raumordnerische Verträge",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.SPATIAL_PLAN,
                    AdminDocumentType.PLANNING_APPROVAL,
                    AdminDocumentType.PLANNING_PROCEDURE,
                ],
                "admin_level": AdminLevel.REGIONAL,
                "admin_domains": [
                    AdminDomain.SPATIAL_PLANNING,
                    AdminDomain.ENVIRONMENTAL_LAW,
                ],
                "planning_specific": True,
                "gis_integration": True,
                "classification_rules": {
                    "keywords": [
                        "Raumordnungsplan",
                        "Regionalplan",
                        "LEP",
                        "REP",
                        "Vorranggebiet",
                        "Vorbehaltsgebiet",
                    ],
                    "spatial_indicators": ["Raumordnung", "Region", "Planungsregion"],
                },
            },
            "metadata_schema": {
                "required_fields": [
                    "plan_type",
                    "planning_authority",
                    "validity_period",
                    "spatial_scope",
                ],
                "optional_fields": [
                    "gis_data",
                    "environmental_assessment",
                    "participation_process",
                ],
                "spatial_fields": [
                    "coordinates",
                    "administrative_boundaries",
                    "planning_zones",
                ],
            },
        }

    @staticmethod
    def land_use_plans_template() -> Dict:
        """Template für Flächennutzungspläne (FNP)"""
        return {
            "collection_name": "flaechennutzungsplaene",
            "display_name": "Flächennutzungspläne (FNP)",
            "collection_type": "planning",
            "rechtsgebiet": "Bauleitplanung, Städtebaurecht",
            "description": "Flächennutzungspläne und deren Änderungen gemäß BauGB",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.LAND_USE_PLAN,
                    AdminDocumentType.PLANNING_APPROVAL,
                    AdminDocumentType.URBAN_DEVELOPMENT,
                ],
                "admin_level": AdminLevel.MUNICIPAL,
                "admin_domains": [AdminDomain.URBAN_PLANNING, AdminDomain.BUILDING_LAW],
                "requires_public_participation": True,
                "gis_integration": True,
                "classification_rules": {
                    "keywords": [
                        "FNP",
                        "Flächennutzungsplan",
                        "Bauleitplan",
                        "§ 5 BauGB",
                        "Darstellung",
                    ],
                    "fnp_indicators": [
                        "Wohnbauflächen",
                        "Gewerbeflächen",
                        "Grünflächen",
                        "Verkehrsflächen",
                    ],
                },
            },
        }

    @staticmethod
    def development_plans_template() -> Dict:
        """Template für Bebauungspläne (B-Plan)"""
        return {
            "collection_name": "bebauungsplaene",
            "display_name": "Bebauungspläne (B-Plan)",
            "collection_type": "planning",
            "rechtsgebiet": "Bauleitplanung, Bauordnungsrecht",
            "description": "Bebauungspläne und Vorhaben- und Erschließungspläne",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.DEVELOPMENT_PLAN,
                    AdminDocumentType.PLANNING_APPROVAL,
                ],
                "admin_level": AdminLevel.MUNICIPAL,
                "admin_domains": [AdminDomain.URBAN_PLANNING, AdminDomain.BUILDING_LAW],
                "requires_public_participation": True,
                "legally_binding": True,
                "gis_integration": True,
                "classification_rules": {
                    "keywords": [
                        "B-Plan",
                        "Bebauungsplan",
                        "§ 9 BauGB",
                        "Festsetzung",
                        "Baugebiet",
                    ],
                    "bplan_indicators": [
                        "WA",
                        "WR",
                        "MI",
                        "MK",
                        "GE",
                        "GI",
                        "SO",
                        "textliche Festsetzungen",
                    ],
                },
            },
        }

    # Process Instructions Templates (HOCH RELEVANT für Graph DB!)
    @staticmethod
    def process_instructions_template() -> Dict:
        """Template für Verfahrensanweisungen (GRAPH DB OPTIMIERT!)"""
        return {
            "collection_name": "verfahrensanweisungen",
            "display_name": "Verfahrens- & Arbeitsanweisungen",
            "collection_type": "process",
            "rechtsgebiet": "Verwaltungsorganisation, QM",
            "description": "Standard Operating Procedures (SOPs) und Verfahrensanweisungen",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.PROCESS_INSTRUCTION,
                    AdminDocumentType.COMPLETION_GUIDE,
                    AdminDocumentType.ORG_MANUAL,
                ],
                "admin_level": AdminLevel.MUNICIPAL,  # kann alle Ebenen sein
                "admin_domains": "ANY",  # prozessübergreifend
                "graph_optimized": True,
                "workflow_extraction": True,
                "process_mining_enabled": True,
                "classification_rules": {
                    "keywords": [
                        "Verfahrensanweisung",
                        "SOP",
                        "Arbeitsanweisung",
                        "Schritt",
                        "Ablauf",
                        "Zuständigkeit",
                    ],
                    "process_indicators": [
                        "wenn",
                        "dann",
                        "falls",
                        "andernfalls",
                        "Prüfung",
                        "Entscheidung",
                    ],
                },
            },
            "graph_schema": {
                "node_types": [
                    "ProcessStep",
                    "Decision",
                    "Document",
                    "Role",
                    "System",
                    "Condition",
                ],
                "edge_types": [
                    "NEXT_STEP",
                    "REQUIRES",
                    "CREATES",
                    "REVIEWS",
                    "APPROVES",
                    "IF_TRUE",
                    "IF_FALSE",
                ],
                "extraction_rules": {
                    "step_patterns": [
                        "Schritt \\d+",
                        "\\d+\\.",
                        "zunächst",
                        "danach",
                        "abschließend",
                    ],
                    "decision_patterns": [
                        "prüfen",
                        "entscheiden",
                        "bewerten",
                        "genehmigen",
                        "ablehnen",
                    ],
                    "role_patterns": [
                        "zuständig:",
                        "verantwortlich:",
                        "Sachbearbeiter",
                        "Amtsleiter",
                    ],
                },
            },
        }

    @staticmethod
    def workflow_definitions_template() -> Dict:
        """Template für Workflow-Definitionen (GRAPH DB OPTIMIERT!)"""
        return {
            "collection_name": "arbeitsablaeufe",
            "display_name": "Arbeitsabläufe & Workflow-Definitionen",
            "collection_type": "workflow",
            "rechtsgebiet": "Prozessmanagement, Digitalisierung",
            "description": "Strukturierte Arbeitsabläufe mit Automatisierungspotential",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.WORKFLOW_DEFINITION,
                    AdminDocumentType.PROCESS_INSTRUCTION,
                ],
                "graph_optimized": True,
                "automation_analysis": True,
                "rpa_potential": True,
                "classification_rules": {
                    "keywords": [
                        "Workflow",
                        "Arbeitsablauf",
                        "Prozess",
                        "automatisiert",
                        "digital",
                    ],
                    "automation_indicators": [
                        "automatisch",
                        "digital",
                        "system",
                        "elektronisch",
                        "ELSTER",
                    ],
                },
            },
            "automation_analysis": {
                "high_potential_keywords": [
                    "Datenübertragung",
                    "Berechnung",
                    "Prüfung",
                    "Versendung",
                    "Archivierung",
                ],
                "medium_potential_keywords": [
                    "Erfassung",
                    "Dokumentation",
                    "Weiterleitung",
                    "Benachrichtigung",
                ],
                "low_potential_keywords": [
                    "Beratung",
                    "Entscheidung",
                    "Verhandlung",
                    "Ortsbesichtigung",
                ],
            },
        }

    @staticmethod
    def competency_matrix_template() -> Dict:
        """Template für Zuständigkeitsmatrix (GRAPH DB OPTIMIERT!)"""
        return {
            "collection_name": "zustaendigkeiten",
            "display_name": "Zuständigkeits- & Kompetenzregelungen",
            "collection_type": "organization",
            "rechtsgebiet": "Verwaltungsorganisation, Zuständigkeitsrecht",
            "description": "Zuständigkeitsordnungen, Geschäftsverteilungen und Kompetenzmatrizen",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.COMPETENCY_MATRIX,
                    AdminDocumentType.DELEGATION_RULE,
                    AdminDocumentType.ORG_MANUAL,
                ],
                "graph_optimized": True,
                "organizational_analysis": True,
                "classification_rules": {
                    "keywords": [
                        "Zuständigkeit",
                        "Kompetenz",
                        "Geschäftsverteilung",
                        "Organigramm",
                        "Vertretung",
                    ],
                    "org_indicators": [
                        "Abteilung",
                        "Referat",
                        "Sachgebiet",
                        "Dezernent",
                        "Amtsleiter",
                    ],
                },
            },
            "graph_schema": {
                "node_types": [
                    "Role",
                    "Department",
                    "Person",
                    "Task",
                    "Authority",
                    "Document_Type",
                ],
                "edge_types": [
                    "REPORTS_TO",
                    "RESPONSIBLE_FOR",
                    "DELEGATES_TO",
                    "AUTHORIZES",
                    "REVIEWS",
                ],
                "analysis_features": [
                    "bottleneck_detection",
                    "delegation_chains",
                    "competency_gaps",
                ],
            },
        }

    # Weitere Template-Methoden für alle anderen Kategorien...
    @staticmethod
    def admin_acts_template() -> Dict:
        """Template für Verwaltungsakte"""
        return {
            "collection_name": "verwaltungsakte",
            "display_name": "Verwaltungsakte & Bescheide",
            "collection_type": "administrative",
            "rechtsgebiet": "Allgemeines Verwaltungsrecht",
            "description": "Verwaltungsakte, Bescheide und Verfügungen aller Art",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.ADMINISTRATIVE_ACT,
                    AdminDocumentType.PERMIT,
                    AdminDocumentType.REJECTION,
                    AdminDocumentType.ORDER,
                ],
                "requires_legal_review": True,
                "deadline_tracking": True,
                "classification_rules": {
                    "keywords": [
                        "Bescheid",
                        "Verwaltungsakt",
                        "genehmigt",
                        "versagt",
                        "Auflage",
                        "Nebenbestimmung",
                    ],
                    "legal_indicators": [
                        "Rechtsmittelbelehrung",
                        "Widerspruch",
                        "Klage",
                    ],
                },
            },
        }

    @staticmethod
    def building_permits_template() -> Dict:
        """Template für Baugenehmigungen"""
        return {
            "collection_name": "baugenehmigungen",
            "display_name": "Baugenehmigungen & Bauordnungsrecht",
            "collection_type": "administrative",
            "rechtsgebiet": "Bauordnungsrecht, Bauplanungsrecht",
            "description": "Baugenehmigungen, Bauvoranfragen und bauordnungsrechtliche Entscheidungen",
            "uds3_config": {
                "document_types": [
                    AdminDocumentType.PERMIT,
                    AdminDocumentType.ADMINISTRATIVE_ACT,
                ],
                "admin_domains": [AdminDomain.BUILDING_LAW, AdminDomain.URBAN_PLANNING],
                "gis_integration": True,
                "deadline_tracking": True,
                "classification_rules": {
                    "keywords": [
                        "Baugenehmigung",
                        "Bauvoranfrage",
                        "Bauordnung",
                        "Bauaufsicht",
                        "Bauabnahme",
                    ],
                    "building_indicators": [
                        "Grundstück",
                        "Bauvorhaben",
                        "Geschossflächenzahl",
                        "Grundflächenzahl",
                    ],
                },
            },
        }

    # Weitere Templates können hier ergänzt werden...

    @staticmethod
    def get_template_by_document_type(doc_type: AdminDocumentType) -> Dict:
        """Hole Template basierend auf Dokumenttyp"""
        type_mapping = {
            AdminDocumentType.LAW: "bundesgesetze",  # oder landesgesetze je nach Level
            AdminDocumentType.REGULATION: "bundesgesetze",
            AdminDocumentType.ORDINANCE: "kommunale_satzungen",
            AdminDocumentType.PERMIT: "baugenehmigungen",
            AdminDocumentType.SPATIAL_PLAN: "raumordnungsplaene",
            AdminDocumentType.LAND_USE_PLAN: "flaechennutzungsplaene",
            AdminDocumentType.DEVELOPMENT_PLAN: "bebauungsplaene",
            AdminDocumentType.PROCESS_INSTRUCTION: "verfahrensanweisungen",
            AdminDocumentType.WORKFLOW_DEFINITION: "arbeitsablaeufe",
            AdminDocumentType.COMPETENCY_MATRIX: "zustaendigkeiten",
            # ... weitere Mappings
        }

        templates = UDS3CollectionTemplates.get_all_templates()
        template_name = type_mapping.get(doc_type)

        if template_name and template_name in templates:
            return templates[template_name]

        # Fallback auf generisches Template
        return UDS3CollectionTemplates.generic_admin_template()

    @staticmethod
    def generic_admin_template() -> Dict:
        """Generisches Template für alle administrativen Dokumente"""
        return {
            "collection_name": "administrative_documents",
            "display_name": "Administrative Dokumente (Allgemein)",
            "collection_type": "administrative",
            "rechtsgebiet": "Verwaltungsrecht (Allgemein)",
            "description": "Allgemeine administrative Dokumente ohne spezifische Kategorisierung",
            "uds3_config": {
                "document_types": "ANY",
                "admin_level": "ANY",
                "admin_domains": "ANY",
                "classification_rules": {
                    "keywords": ["Verwaltung", "Behörde", "Amt", "Dokument"],
                    "admin_indicators": ["Aktenzeichen", "Geschäftszeichen", "Betreff"],
                },
            },
        }


# Utility Funktionen für Integration in Collection Manager
def integrate_uds3_templates_into_collection_manager():
    """Integration der UDS3-Templates in den bestehenden Collection Manager"""
    try:
        from collection_manager import CollectionManager  # type: ignore
    except Exception:
        from typing import Any

        CollectionManager = Any  # type: ignore

    # Alle Templates laden
    templates = UDS3CollectionTemplates.get_all_templates()

    # Collection Manager initialisieren
    cm = CollectionManager()

    # Templates als vordefinierte Collections hinzufügen
    for template_name, template_config in templates.items():
        try:
            cm.register_collection(
                collection_name=template_config["collection_name"],
                display_name=template_config["display_name"],
                collection_type=template_config["collection_type"],
                rechtsgebiet=template_config["rechtsgebiet"],
                description=template_config["description"],
            )
            print(f"✅ Template '{template_name}' erfolgreich integriert")
        except Exception as e:
            print(f"⚠️ Template '{template_name}' bereits vorhanden oder Fehler: {e}")

    print(f"\n🎯 {len(templates)} UDS3-Templates zur Integration bereitgestellt!")
    return templates


if __name__ == "__main__":
    # Test der Template-Integration
    print("🚀 UDS3 Collection Templates - Integration Test")
    print("=" * 60)

    # Alle Templates anzeigen
    templates = UDS3CollectionTemplates.get_all_templates()
    print(f"📋 {len(templates)} Templates verfügbar:")

    for name, template in templates.items():
        doc_types = template["uds3_config"].get("document_types", [])
        if isinstance(doc_types, list) and len(doc_types) > 0:
            print(
                f"  - {name}: {template['display_name']} ({len(doc_types)} Dokumenttypen)"
            )
        else:
            print(f"  - {name}: {template['display_name']} (Universell)")

    print("\n🔧 Integration in Collection Manager...")
    integrate_uds3_templates_into_collection_manager()

    print("\n✅ UDS3-Templates bereit für Production-Einsatz!")

# Alias für veritas_app.py Kompatibilität
CollectionTemplates = UDS3CollectionTemplates
