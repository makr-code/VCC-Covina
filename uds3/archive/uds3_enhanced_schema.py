"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_enhanced_schema"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...OtT7aQ=="  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "36e2bc3ebd2e157a938ea9a147cbd6bd053a74203cfc4d999f336824a1bba492"
)
module_file_key = "6c354c12dce3cf08303f52bdab3fe5dcbc95b0f78d955817766df86d6a8908a2"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
UDS3 Enhanced Schema Definition
==============================

Erweiterte UDS3-Schemata basierend auf Scraper-Erkenntnissen
und Enhanced Metadata Integration

Diese Datei definiert die angepassten Datenbank-Schemata für die
optimale Verarbeitung rechtsspezifischer Metadaten
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class EnhancedDatabaseRole(Enum):
    """Erweiterte UDS3-Datenbankrollen mit rechtsspezifischen Funktionen"""

    # === CORE UDS3 ROLLEN ===
    VECTOR_DB = "vector_database"  # Semantic Search & RAG
    GRAPH_DB = "graph_database"  # Beziehungen & Vernetzung
    RELATIONAL_DB = "relational_database"  # Strukturierte Metadaten

    # === ENHANCED LEGAL ROLLEN ===
    LEGAL_METADATA_DB = "legal_metadata_database"  # Rechtsspezifische Metadaten
    CITATION_GRAPH_DB = "citation_graph_database"  # Zitationsnetzwerk
    QUALITY_METRICS_DB = "quality_metrics_database"  # Quality & Scoring
    CROSS_REFERENCE_DB = "cross_reference_database"  # Querverweise


@dataclass
class EnhancedVectorSchema:
    """Erweitertes Vector-DB Schema für Rechtstexte"""

    # === STANDARD FELDER ===
    document_id: str
    chunk_index: int
    content_vector: List[float]  # Embeddings
    content_text: str
    content_length: int

    # === RECHTSSPEZIFISCHE FELDER ===
    aktenzeichen: Optional[str] = None
    gericht: Optional[str] = None
    rechtsgebiet: Optional[str] = None
    content_category: Optional[str] = None  # 'rechtsprechung', 'gesetz', 'wissenschaft'
    instanz: Optional[str] = None  # 'bundesgericht', 'landesgericht', 'amtsgericht'

    # === QUALITÄTS-METRIKEN ===
    quality_score: float = 0.0  # 0-100 Content Quality
    extraction_confidence: float = 0.0  # 0-1 Extraction Confidence
    metadata_completeness: float = 0.0  # 0-1 Metadata Completeness

    # === SEMANTIC ENHANCEMENT ===
    legal_concepts: List[str] = None  # Extrahierte Rechtsbegriffe
    referenced_laws: List[str] = None  # Referenzierte Gesetze
    semantic_keywords: List[str] = None  # Semantic Keywords

    # === PROCESSING METADATEN ===
    source_domain: str = ""
    processing_version: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class EnhancedGraphSchema:
    """Erweitertes Graph-DB Schema für Rechtsvernetzung"""

    # === NODE TYPES ===
    class NodeType(Enum):
        DOCUMENT = "document"
        COURT = "court"
        LAW = "law"
        LEGAL_CONCEPT = "legal_concept"
        AUTHORITY = "authority"
        CASE = "case"
        PERSON = "person"
        ORGANIZATION = "organization"

    # === RELATIONSHIP TYPES ===
    class RelationType(Enum):
        CITES = "cites"  # Dokument zitiert anderes Dokument
        REFERENCES_LAW = "references_law"  # Dokument referenziert Gesetz
        DECIDED_BY = "decided_by"  # Fall entschieden von Gericht
        APPEALS_TO = "appeals_to"  # Berufung an höheres Gericht
        BELONGS_TO = "belongs_to"  # Gehört zu Rechtsgebiet
        SIMILAR_TO = "similar_to"  # Ähnlicher Inhalt
        CONTRADICTS = "contradicts"  # Widersprüchliche Entscheidung
        CONFIRMS = "confirms"  # Bestätigende Entscheidung
        ISSUED_BY = "issued_by"  # Erlassen von Behörde
        CONTAINS_CONCEPT = "contains_concept"  # Enthält Rechtsbegriff

    # === DOCUMENT NODE ===
    document_id: str
    node_type: NodeType

    # Rechtsspezifische Eigenschaften
    aktenzeichen: Optional[str] = None
    ecli: Optional[str] = None
    title: Optional[str] = None
    content_hash: Optional[str] = None

    # === COURT NODE ===
    court_name: Optional[str] = None
    court_type: Optional[str] = None  # 'AG', 'LG', 'OLG', 'BGH', etc.
    jurisdiction: Optional[str] = None  # 'bund', 'land', 'international'
    court_level: Optional[int] = None  # 1=AG, 2=LG, 3=OLG, 4=BGH

    # === LAW NODE ===
    law_name: Optional[str] = None
    law_abbreviation: Optional[str] = None  # 'BGB', 'StGB', 'GG', etc.
    paragraph: Optional[str] = None
    version: Optional[str] = None

    # === RELATIONSHIPS ===
    relationships: List[Dict[str, Any]] = None  # Liste von Beziehungen

    # === GRAPH METRIKEN ===
    citation_count: int = 0  # Wie oft zitiert
    reference_count: int = 0  # Wie oft referenziert
    centrality_score: float = 0.0  # Graph-Zentralität
    authority_score: float = 0.0  # Autorität im Netzwerk


@dataclass
class EnhancedRelationalSchema:
    """Erweitertes Relational-DB Schema für strukturierte Metadaten"""

    # === DOCUMENTS TABLE ===
    document_id: str  # Primary Key

    # === BASIC METADATA ===
    title: Optional[str] = None
    content_length: int = 0
    word_count: int = 0
    language: str = "de"
    encoding: str = "utf-8"

    # === LEGAL METADATA ===
    aktenzeichen: Optional[str] = None
    case_number: Optional[str] = None
    gericht: Optional[str] = None
    court_international: Optional[str] = None
    entscheidungsdatum: Optional[str] = None
    verkuendungsdatum: Optional[str] = None
    rechtsgebiet: Optional[str] = None
    instanz: Optional[str] = None
    ecli: Optional[str] = None

    # === ADMINISTRATIVE METADATA ===
    behoerde: Optional[str] = None
    aktenzeichen_behoerde: Optional[str] = None
    erlass_datum: Optional[str] = None
    gueltigkeitsbereich: Optional[str] = None
    verwaltungsebene: Optional[str] = None

    # === LEGISLATIVE METADATA ===
    gesetz_name: Optional[str] = None
    gesetz_kuerzel: Optional[str] = None
    paragraph: Optional[str] = None
    absatz: Optional[str] = None
    normenkette: Optional[str] = None

    # === CLASSIFICATION ===
    document_type: Optional[str] = None  # 'urteil', 'beschluss', 'gesetz'
    content_category: Optional[str] = None  # 'rechtsprechung', 'verwaltung'
    source_type: str = "unknown"  # 'scraper', 'manual', 'import'
    source_domain: str = ""

    # === QUALITY METRICS ===
    metadaten_vollstaendigkeit: float = 0.0  # 0-1 Score
    content_quality_score: int = 0  # 0-100 Score
    extraction_confidence: float = 0.0  # 0-1 Confidence

    # === PROCESSING METADATA ===
    scraped_at: Optional[str] = None
    processed_at: Optional[str] = None
    last_updated: Optional[str] = None
    processing_version: str = ""

    # === INDEXES FOR PERFORMANCE ===
    # CREATE INDEX idx_aktenzeichen ON documents(aktenzeichen);
    # CREATE INDEX idx_gericht ON documents(gericht);
    # CREATE INDEX idx_rechtsgebiet ON documents(rechtsgebiet);
    # CREATE INDEX idx_entscheidungsdatum ON documents(entscheidungsdatum);
    # CREATE INDEX idx_source_domain ON documents(source_domain);
    # CREATE INDEX idx_document_type ON documents(document_type);


@dataclass
class LegalMetadataSchema:
    """Separate Tabelle für erweiterte rechtsspezifische Metadaten"""

    document_id: str  # Foreign Key zu documents

    # === CITATIONS & REFERENCES ===
    zitierte_normen: Optional[str] = None  # JSON Array
    zitierte_entscheidungen: Optional[str] = None  # JSON Array
    fundstellen: Optional[str] = None  # JSON Array
    cross_references: Optional[str] = None  # JSON Array

    # === CONTENT CLASSIFICATION ===
    rechtsgebiet_klassifikation: Optional[str] = None  # JSON Array
    schlagworte: Optional[str] = None  # JSON Array
    legal_concepts: Optional[str] = None  # JSON Array
    semantic_keywords: Optional[str] = None  # JSON Array

    # === INTERNATIONAL METADATA ===
    application_number: Optional[str] = None  # EGMR
    procedure_type: Optional[str] = None  # EuGH
    treaty_article: Optional[str] = None  # Vertragsartikel

    # === SCIENTIFIC METADATA ===
    author: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    issn: Optional[str] = None


@dataclass
class QualityMetricsSchema:
    """Separate Tabelle für Quality & Performance Metriken"""

    document_id: str  # Foreign Key

    # === EXTRACTION QUALITY ===
    extraction_method: str = ""  # 'markdown', 'pdf', 'html'
    extraction_confidence: float = 0.0
    metadata_completeness: float = 0.0
    field_accuracy_score: float = 0.0

    # === CONTENT QUALITY ===
    content_quality_score: int = 0  # 0-100
    text_clarity_score: float = 0.0
    structure_score: float = 0.0
    completeness_score: float = 0.0

    # === PROCESSING PERFORMANCE ===
    processing_time_ms: int = 0
    memory_usage_mb: float = 0.0
    error_count: int = 0
    warning_count: int = 0

    # === VALIDATION STATUS ===
    validated_manually: bool = False
    validation_date: Optional[str] = None
    validator_id: Optional[str] = None
    validation_notes: Optional[str] = None


class EnhancedUDS3DatabaseStrategy:
    """
    Enhanced UDS3 Database Strategy mit rechtsspezifischen Optimierungen
    """

    def __init__(self):
        self.schemas = {
            EnhancedDatabaseRole.VECTOR_DB: EnhancedVectorSchema,
            EnhancedDatabaseRole.GRAPH_DB: EnhancedGraphSchema,
            EnhancedDatabaseRole.RELATIONAL_DB: EnhancedRelationalSchema,
            EnhancedDatabaseRole.LEGAL_METADATA_DB: LegalMetadataSchema,
            EnhancedDatabaseRole.QUALITY_METRICS_DB: QualityMetricsSchema,
        }

        # SQL Statements für Tabellenerstellung
        self.create_statements = self._build_create_statements()

        # Index-Strategien für Performance
        self.index_strategies = self._build_index_strategies()

    def _build_create_statements(self) -> Dict[str, str]:
        """Baut CREATE TABLE Statements für alle Schemata"""
        return {
            "documents": """
            CREATE TABLE IF NOT EXISTS documents (
                document_id VARCHAR(255) PRIMARY KEY,
                title TEXT,
                content_length INTEGER DEFAULT 0,
                word_count INTEGER DEFAULT 0,
                language VARCHAR(10) DEFAULT 'de',
                encoding VARCHAR(20) DEFAULT 'utf-8',
                
                -- Legal Metadata
                aktenzeichen VARCHAR(255),
                case_number VARCHAR(255),
                gericht VARCHAR(255),
                court_international VARCHAR(255),
                entscheidungsdatum VARCHAR(20),
                verkuendungsdatum VARCHAR(20),
                rechtsgebiet VARCHAR(255),
                instanz VARCHAR(100),
                ecli VARCHAR(255),
                
                -- Administrative Metadata
                behoerde VARCHAR(255),
                aktenzeichen_behoerde VARCHAR(255),
                erlass_datum VARCHAR(20),
                gueltigkeitsbereich VARCHAR(255),
                verwaltungsebene VARCHAR(100),
                
                -- Legislative Metadata
                gesetz_name VARCHAR(255),
                gesetz_kuerzel VARCHAR(50),
                paragraph VARCHAR(100),
                absatz VARCHAR(50),
                normenkette TEXT,
                
                -- Classification
                document_type VARCHAR(100),
                content_category VARCHAR(100),
                source_type VARCHAR(50) DEFAULT 'unknown',
                source_domain VARCHAR(255),
                
                -- Quality Metrics
                metadaten_vollstaendigkeit DECIMAL(3,2) DEFAULT 0.0,
                content_quality_score INTEGER DEFAULT 0,
                extraction_confidence DECIMAL(3,2) DEFAULT 0.0,
                
                -- Processing Metadata
                scraped_at TIMESTAMP,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                processing_version VARCHAR(50)
            );
            """,
            "legal_metadata": """
            CREATE TABLE IF NOT EXISTS legal_metadata (
                document_id VARCHAR(255) PRIMARY KEY,
                
                -- Citations & References (JSON)
                zitierte_normen JSON,
                zitierte_entscheidungen JSON,
                fundstellen JSON,
                cross_references JSON,
                
                -- Content Classification (JSON)
                rechtsgebiet_klassifikation JSON,
                schlagworte JSON,
                legal_concepts JSON,
                semantic_keywords JSON,
                
                -- International Metadata
                application_number VARCHAR(255),
                procedure_type VARCHAR(100),
                treaty_article VARCHAR(255),
                
                -- Scientific Metadata
                author VARCHAR(255),
                publication_date VARCHAR(20),
                journal VARCHAR(255),
                doi VARCHAR(255),
                issn VARCHAR(20),
                
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            );
            """,
            "quality_metrics": """
            CREATE TABLE IF NOT EXISTS quality_metrics (
                document_id VARCHAR(255) PRIMARY KEY,
                
                -- Extraction Quality
                extraction_method VARCHAR(50),
                extraction_confidence DECIMAL(3,2) DEFAULT 0.0,
                metadata_completeness DECIMAL(3,2) DEFAULT 0.0,
                field_accuracy_score DECIMAL(3,2) DEFAULT 0.0,
                
                -- Content Quality
                content_quality_score INTEGER DEFAULT 0,
                text_clarity_score DECIMAL(3,2) DEFAULT 0.0,
                structure_score DECIMAL(3,2) DEFAULT 0.0,
                completeness_score DECIMAL(3,2) DEFAULT 0.0,
                
                -- Processing Performance
                processing_time_ms INTEGER DEFAULT 0,
                memory_usage_mb DECIMAL(8,2) DEFAULT 0.0,
                error_count INTEGER DEFAULT 0,
                warning_count INTEGER DEFAULT 0,
                
                -- Validation Status
                validated_manually BOOLEAN DEFAULT FALSE,
                validation_date TIMESTAMP,
                validator_id VARCHAR(100),
                validation_notes TEXT,
                
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            );
            """,
        }

    def _build_index_strategies(self) -> Dict[str, List[str]]:
        """Definiert Index-Strategien für Performance-Optimierung"""
        return {
            "documents": [
                "CREATE INDEX idx_aktenzeichen ON documents(aktenzeichen);",
                "CREATE INDEX idx_gericht ON documents(gericht);",
                "CREATE INDEX idx_rechtsgebiet ON documents(rechtsgebiet);",
                "CREATE INDEX idx_entscheidungsdatum ON documents(entscheidungsdatum);",
                "CREATE INDEX idx_source_domain ON documents(source_domain);",
                "CREATE INDEX idx_document_type ON documents(document_type);",
                "CREATE INDEX idx_content_category ON documents(content_category);",
                "CREATE INDEX idx_instanz ON documents(instanz);",
                "CREATE INDEX idx_quality_score ON documents(content_quality_score);",
                "CREATE INDEX idx_processing_version ON documents(processing_version);",
                # Composite Indexes für häufige Queries
                "CREATE INDEX idx_gericht_rechtsgebiet ON documents(gericht, rechtsgebiet);",
                "CREATE INDEX idx_source_quality ON documents(source_domain, content_quality_score);",
                "CREATE INDEX idx_type_category ON documents(document_type, content_category);",
            ],
            "legal_metadata": [
                "CREATE INDEX idx_author ON legal_metadata(author);",
                "CREATE INDEX idx_publication_date ON legal_metadata(publication_date);",
                "CREATE INDEX idx_journal ON legal_metadata(journal);",
                "CREATE INDEX idx_application_number ON legal_metadata(application_number);",
            ],
            "quality_metrics": [
                "CREATE INDEX idx_extraction_confidence ON quality_metrics(extraction_confidence);",
                "CREATE INDEX idx_metadata_completeness ON quality_metrics(metadata_completeness);",
                "CREATE INDEX idx_content_quality ON quality_metrics(content_quality_score);",
                "CREATE INDEX idx_validated ON quality_metrics(validated_manually);",
                "CREATE INDEX idx_processing_time ON quality_metrics(processing_time_ms);",
            ],
        }

    def get_schema_for_role(self, role: EnhancedDatabaseRole):
        """Gibt Schema für spezifische Datenbankrolle zurück"""
        return self.schemas.get(role)

    def get_create_statement(self, table_name: str) -> str:
        """Gibt CREATE TABLE Statement zurück"""
        return self.create_statements.get(table_name, "")

    def get_indexes_for_table(self, table_name: str) -> List[str]:
        """Gibt Index-Definitionen für Tabelle zurück"""
        return self.index_strategies.get(table_name, [])


# === COMPATIBILITY MAPPING ===


def map_scraper_to_uds3(scraper_document: dict) -> dict:
    """
    Mappt Scraper-Dokument auf Enhanced UDS3 Schema
    """
    uds3_document = {
        # Basic Document Info
        "document_id": scraper_document.get("document_id", ""),
        "title": scraper_document.get("title", ""),
        "content_length": scraper_document.get("content_length", 0),
        "word_count": scraper_document.get("word_count", 0),
        # Legal Metadata - Direct Mapping
        "aktenzeichen": scraper_document.get("aktenzeichen"),
        "case_number": scraper_document.get("case_number"),
        "gericht": scraper_document.get("gericht"),
        "entscheidungsdatum": scraper_document.get("entscheidungsdatum"),
        "rechtsgebiet": scraper_document.get("rechtsgebiet"),
        "ecli": scraper_document.get("ecli"),
        # Source Information
        "source_type": "scraper",
        "source_domain": scraper_document.get("source_domain", ""),
        "document_type": scraper_document.get("document_type"),
        "content_category": scraper_document.get("content_category"),
        # Processing Metadata
        "scraped_at": scraper_document.get("scraped_at"),
        "processed_at": scraper_document.get("processed_at"),
        "processing_version": "enhanced_v1.0",
    }

    # Quality Metrics
    if "quality_metrics" in scraper_document:
        metrics = scraper_document["quality_metrics"]
        uds3_document.update(
            {
                "metadaten_vollstaendigkeit": metrics.get("metadata_completeness", 0.0),
                "content_quality_score": metrics.get("content_quality", 0),
                "extraction_confidence": metrics.get("extraction_confidence", 0.0),
            }
        )

    return uds3_document


if __name__ == "__main__":
    # Teste Enhanced UDS3 Schema
    strategy = EnhancedUDS3DatabaseStrategy()

    print("Enhanced UDS3 Database Strategy")
    print("=" * 50)

    for role in EnhancedDatabaseRole:
        schema = strategy.get_schema_for_role(role)
        print(f"\n{role.value}: {schema.__name__ if schema else 'No schema'}")

    print("\nCreate Statements:")
    for table, statement in strategy.create_statements.items():
        print(f"\n{table}:")
        print(statement[:200] + "...")  # Zeige ersten Teil
