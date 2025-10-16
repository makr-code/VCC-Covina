#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

"""
Generic Database Schema Definitions für Unified Database Strategy v3.0

Definiert standardisierte Schemas für ALLE verwaltungsrechtlichen Dokumente:
- Normative Ebene: Gesetze, Verordnungen, Ausführungsbestimmungen
- Verwaltungsentscheidungen: Bescheide, Verfügungen, Planfeststellungen  
- Gerichtsentscheidungen: VG/OVG/BVerwG-Urteile (Teilbereich)
- Verwaltungsinterne Dokumente: Aktennotizen, Gutachten, Korrespondenz

Unterstützte Datenbanken:
- SQLite/PostgreSQL (Relational DB)
- ChromaDB/Pinecone (Vector DB) 
- Neo4j/ArangoDB (Graph DB)

Inkludiert Security & Quality Felder für alle Schemas.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json


class DatabaseType(Enum):
    """Unterstützte Datenbanktypen"""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    CHROMADB = "chromadb"
    PINECONE = "pinecone"
    NEO4J = "neo4j"
    ARANGODB = "arangodb"


class FieldType(Enum):
    """Datentypen für Schema-Felder"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TEXT = "text"
    JSON = "json"
    VECTOR = "vector"
    HASH = "hash"
    UUID = "uuid"


@dataclass
class SchemaField:
    """Definition eines Datenbankfeldes"""

    name: str
    type: FieldType
    required: bool = False
    indexed: bool = False
    unique: bool = False
    max_length: Optional[int] = None
    default: Optional[Any] = None
    description: str = ""
    security_sensitive: bool = False
    quality_relevant: bool = False


class DatabaseSchemaManager:
    """
    Verwaltet generische Datenbankschemas für das Unified Database System

    Stellt standardisierte Schemas für alle unterstützten Datenbanktypen bereit
    mit integrierten Security & Quality Feldern.
    """

    def __init__(self):
        self.schemas = self._initialize_schemas()

    def _initialize_schemas(self) -> Dict[str, Dict]:
        """Initialisiert alle Datenbankschemas"""
        return {
            "relational": self._create_relational_schemas(),
            "vector": self._create_vector_schemas(),
            "graph": self._create_graph_schemas(),
        }

    def _create_relational_schemas(self) -> Dict[str, List[SchemaField]]:
        """Erstellt Relational Database Schemas (SQLite/PostgreSQL)"""

        # === DOCUMENTS TABLE ===
        documents_schema = [
            # Core Document Fields
            SchemaField(
                name="id",
                type=FieldType.STRING,
                required=True,
                unique=True,
                indexed=True,
                max_length=64,
                description="Eindeutige Dokument-ID (doc_uuid)",
                quality_relevant=True,
            ),
            SchemaField(
                name="title",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                max_length=500,
                description="Dokumententitel",
                quality_relevant=True,
            ),
            SchemaField(
                name="file_path",
                type=FieldType.STRING,
                required=True,
                max_length=1000,
                description="Ursprünglicher Dateipfad",
                quality_relevant=True,
            ),
            SchemaField(
                name="content_preview",
                type=FieldType.TEXT,
                required=False,
                max_length=2000,
                description="Kurze Inhaltsvorschau (ersten 2000 Zeichen)",
            ),
            SchemaField(
                name="file_size",
                type=FieldType.INTEGER,
                required=False,
                description="Dateigröße in Bytes",
            ),
            SchemaField(
                name="mime_type",
                type=FieldType.STRING,
                required=False,
                max_length=100,
                description="MIME-Typ der Originaldatei",
            ),
            # Legal Metadata
            SchemaField(
                name="rechtsgebiet",
                type=FieldType.STRING,
                required=False,
                indexed=True,
                max_length=200,
                description="Rechtsgebiet (Arbeitsrecht, Strafrecht, etc.)",
            ),
            SchemaField(
                name="gericht",
                type=FieldType.STRING,
                required=False,
                indexed=True,
                max_length=200,
                description="Gericht/Behörde",
            ),
            SchemaField(
                name="aktenzeichen",
                type=FieldType.STRING,
                required=False,
                indexed=True,
                max_length=100,
                description="Aktenzeichen",
            ),
            SchemaField(
                name="entscheidungsdatum",
                type=FieldType.DATETIME,
                required=False,
                indexed=True,
                description="Datum der Entscheidung/des Urteils",
            ),
            SchemaField(
                name="author",
                type=FieldType.STRING,
                required=False,
                max_length=200,
                description="Autor/Verfasser",
                security_sensitive=True,
            ),
            # Timestamps
            SchemaField(
                name="created_at",
                type=FieldType.DATETIME,
                required=True,
                indexed=True,
                description="Erstellungsdatum",
                quality_relevant=True,
            ),
            SchemaField(
                name="updated_at",
                type=FieldType.DATETIME,
                required=False,
                indexed=True,
                description="Letzte Aktualisierung",
            ),
            SchemaField(
                name="last_accessed",
                type=FieldType.DATETIME,
                required=False,
                description="Letzter Zugriff",
            ),
            # Security Fields
            SchemaField(
                name="document_uuid",
                type=FieldType.UUID,
                required=True,
                unique=True,
                description="UUID v4 für Dokument",
                security_sensitive=True,
            ),
            SchemaField(
                name="content_hash",
                type=FieldType.HASH,
                required=True,
                max_length=128,
                description="SHA-256 Hash des Inhalts",
                security_sensitive=True,
            ),
            SchemaField(
                name="content_hmac",
                type=FieldType.HASH,
                required=False,
                max_length=128,
                description="HMAC für Authentizität",
                security_sensitive=True,
            ),
            SchemaField(
                name="checksum",
                type=FieldType.HASH,
                required=True,
                max_length=32,
                description="MD5 Checksum für schnelle Validation",
                security_sensitive=True,
            ),
            SchemaField(
                name="security_level",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                max_length=20,
                default="internal",
                description="Sicherheitsstufe (public, internal, confidential, restricted)",
                security_sensitive=True,
            ),
            SchemaField(
                name="encryption_status",
                type=FieldType.BOOLEAN,
                required=True,
                default=False,
                description="Verschlüsselungsstatus",
                security_sensitive=True,
            ),
            # Quality Fields
            SchemaField(
                name="quality_score",
                type=FieldType.FLOAT,
                required=False,
                indexed=True,
                description="Gesamtqualitätsscore (0.0 - 1.0)",
                quality_relevant=True,
            ),
            SchemaField(
                name="completeness_score",
                type=FieldType.FLOAT,
                required=False,
                description="Vollständigkeitsscore",
                quality_relevant=True,
            ),
            SchemaField(
                name="consistency_score",
                type=FieldType.FLOAT,
                required=False,
                description="Konsistenzscore",
                quality_relevant=True,
            ),
            SchemaField(
                name="last_quality_check",
                type=FieldType.DATETIME,
                required=False,
                description="Letzte Qualitätsprüfung",
                quality_relevant=True,
            ),
            SchemaField(
                name="quality_issues",
                type=FieldType.JSON,
                required=False,
                description="JSON Array mit Qualitätsproblemen",
                quality_relevant=True,
            ),
        ]

        # === DOCUMENT_CHUNKS TABLE ===
        chunks_schema = [
            SchemaField(
                name="id",
                type=FieldType.STRING,
                required=True,
                unique=True,
                max_length=64,
                description="Eindeutige Chunk-ID",
            ),
            SchemaField(
                name="document_id",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                max_length=64,
                description="Referenz zum Hauptdokument",
                quality_relevant=True,
            ),
            SchemaField(
                name="chunk_index",
                type=FieldType.INTEGER,
                required=True,
                indexed=True,
                description="Position im Dokument (0-basiert)",
            ),
            SchemaField(
                name="content",
                type=FieldType.TEXT,
                required=True,
                description="Text-Inhalt des Chunks",
            ),
            SchemaField(
                name="content_length",
                type=FieldType.INTEGER,
                required=True,
                description="Länge des Chunk-Inhalts in Zeichen",
            ),
            SchemaField(
                name="start_position",
                type=FieldType.INTEGER,
                required=False,
                description="Start-Position im Original-Dokument",
            ),
            SchemaField(
                name="end_position",
                type=FieldType.INTEGER,
                required=False,
                description="End-Position im Original-Dokument",
            ),
            SchemaField(
                name="chunk_type",
                type=FieldType.STRING,
                required=False,
                max_length=50,
                description="Art des Chunks (paragraph, heading, footnote, etc.)",
            ),
            SchemaField(
                name="vector_id",
                type=FieldType.STRING,
                required=False,
                max_length=100,
                description="Referenz zur Vector-DB",
                quality_relevant=True,
            ),
            SchemaField(
                name="created_at",
                type=FieldType.DATETIME,
                required=True,
                description="Erstellungsdatum",
            ),
        ]

        # === KEYWORDS TABLE ===
        keywords_schema = [
            SchemaField(
                name="id",
                type=FieldType.INTEGER,
                required=True,
                unique=True,
                description="Auto-increment ID",
            ),
            SchemaField(
                name="document_id",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                max_length=64,
                description="Referenz zum Dokument",
            ),
            SchemaField(
                name="keyword",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                max_length=200,
                description="Extrahiertes Keyword",
            ),
            SchemaField(
                name="frequency",
                type=FieldType.INTEGER,
                required=True,
                description="Häufigkeit im Dokument",
            ),
            SchemaField(
                name="context_type",
                type=FieldType.STRING,
                required=False,
                max_length=50,
                description="Kontext (title, content, metadata)",
            ),
            SchemaField(
                name="extraction_method",
                type=FieldType.STRING,
                required=False,
                max_length=50,
                description="Extraktionsmethode (frequency, tfidf, nlp)",
            ),
            SchemaField(
                name="confidence",
                type=FieldType.FLOAT,
                required=False,
                description="Confidence-Score (0.0 - 1.0)",
            ),
        ]

        # === AUDIT_LOG TABLE ===
        audit_log_schema = [
            SchemaField(
                name="audit_id",
                type=FieldType.UUID,
                required=True,
                unique=True,
                description="Eindeutige Audit-ID",
            ),
            SchemaField(
                name="timestamp",
                type=FieldType.DATETIME,
                required=True,
                indexed=True,
                description="Zeitpunkt der Operation",
            ),
            SchemaField(
                name="operation",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                max_length=50,
                description="Art der Operation (CREATE, READ, UPDATE, DELETE)",
            ),
            SchemaField(
                name="document_id",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                max_length=64,
                description="Betroffenes Dokument",
            ),
            SchemaField(
                name="user_id",
                type=FieldType.STRING,
                required=False,
                max_length=100,
                description="Benutzer-ID",
            ),
            SchemaField(
                name="details",
                type=FieldType.JSON,
                required=False,
                description="Zusätzliche Details als JSON",
            ),
            SchemaField(
                name="hash",
                type=FieldType.HASH,
                required=True,
                max_length=128,
                description="Hash für Tamper-Detection",
            ),
        ]

        return {
            "documents": documents_schema,
            "document_chunks": chunks_schema,
            "keywords": keywords_schema,
            "audit_log": audit_log_schema,
        }

    def _create_vector_schemas(self) -> Dict[str, List[SchemaField]]:
        """Erstellt Vector Database Schemas (ChromaDB/Pinecone)"""

        # === DOCUMENT_VECTORS COLLECTION ===
        document_vectors_schema = [
            SchemaField(
                name="id",
                type=FieldType.STRING,
                required=True,
                unique=True,
                description="Chunk-ID oder Document-ID",
            ),
            SchemaField(
                name="document_id",
                type=FieldType.STRING,
                required=True,
                indexed=True,
                description="Referenz zum Hauptdokument",
                quality_relevant=True,
            ),
            SchemaField(
                name="content",
                type=FieldType.TEXT,
                required=True,
                description="Text-Inhalt für Embedding",
            ),
            SchemaField(
                name="embedding",
                type=FieldType.VECTOR,
                required=True,
                description="Vector Embedding (1536-dimensional für OpenAI)",
            ),
            SchemaField(
                name="chunk_index",
                type=FieldType.INTEGER,
                required=False,
                description="Position im Dokument (für Chunks)",
            ),
            SchemaField(
                name="embedding_model",
                type=FieldType.STRING,
                required=False,
                max_length=100,
                description="Verwendetes Embedding-Modell",
            ),
            SchemaField(
                name="embedding_version",
                type=FieldType.STRING,
                required=False,
                max_length=20,
                description="Modell-Version",
            ),
            # Metadata für Vector Search
            SchemaField(
                name="title",
                type=FieldType.STRING,
                required=False,
                max_length=500,
                description="Dokument-/Chunk-Titel",
            ),
            SchemaField(
                name="rechtsgebiet",
                type=FieldType.STRING,
                required=False,
                max_length=200,
                description="Rechtsgebiet für Filterung",
            ),
            SchemaField(
                name="gericht",
                type=FieldType.STRING,
                required=False,
                max_length=200,
                description="Gericht für Filterung",
            ),
            SchemaField(
                name="created_at",
                type=FieldType.DATETIME,
                required=True,
                description="Erstellungsdatum",
            ),
            # Security Metadata
            SchemaField(
                name="security_level",
                type=FieldType.STRING,
                required=True,
                max_length=20,
                description="Sicherheitsstufe",
                security_sensitive=True,
            ),
            SchemaField(
                name="content_hash",
                type=FieldType.HASH,
                required=False,
                max_length=128,
                description="Hash für Integrität",
                security_sensitive=True,
            ),
            # Quality Metadata
            SchemaField(
                name="semantic_coherence",
                type=FieldType.FLOAT,
                required=False,
                description="Semantische Kohärenz-Score",
                quality_relevant=True,
            ),
        ]

        return {"document_vectors": document_vectors_schema}

    def _create_graph_schemas(self) -> Dict[str, List[SchemaField]]:
        """Erstellt Graph Database Schemas (Neo4j/ArangoDB)"""

        # === DOCUMENT NODES ===
        document_nodes_schema = [
            SchemaField(
                name="id",
                type=FieldType.STRING,
                required=True,
                unique=True,
                description="Dokument-ID",
            ),
            SchemaField(
                name="title",
                type=FieldType.STRING,
                required=True,
                description="Dokumententitel",
            ),
            SchemaField(
                name="node_type",
                type=FieldType.STRING,
                required=True,
                default="Document",
                description="Node-Typ (Document, Chunk, Author, Court, etc.)",
            ),
            SchemaField(
                name="rechtsgebiet",
                type=FieldType.STRING,
                required=False,
                description="Rechtsgebiet",
            ),
            SchemaField(
                name="gericht",
                type=FieldType.STRING,
                required=False,
                description="Gericht/Behörde",
            ),
            SchemaField(
                name="created_at",
                type=FieldType.DATETIME,
                required=True,
                description="Erstellungsdatum",
            ),
            # Security Fields
            SchemaField(
                name="security_level",
                type=FieldType.STRING,
                required=True,
                description="Sicherheitsstufe",
                security_sensitive=True,
            ),
            # Quality Fields
            SchemaField(
                name="quality_score",
                type=FieldType.FLOAT,
                required=False,
                description="Qualitätsscore",
                quality_relevant=True,
            ),
        ]

        # === CHUNK NODES ===
        chunk_nodes_schema = [
            SchemaField(
                name="id",
                type=FieldType.STRING,
                required=True,
                unique=True,
                description="Chunk-ID",
            ),
            SchemaField(
                name="content_preview",
                type=FieldType.STRING,
                required=False,
                max_length=200,
                description="Kurze Inhaltsvorschau",
            ),
            SchemaField(
                name="node_type",
                type=FieldType.STRING,
                required=True,
                default="Chunk",
                description="Node-Typ",
            ),
            SchemaField(
                name="chunk_index",
                type=FieldType.INTEGER,
                required=True,
                description="Position im Dokument",
            ),
            SchemaField(
                name="created_at",
                type=FieldType.DATETIME,
                required=True,
                description="Erstellungsdatum",
            ),
        ]

        # === RELATIONSHIPS ===
        relationships_schema = [
            SchemaField(
                name="from_node_id",
                type=FieldType.STRING,
                required=True,
                description="Quell-Node ID",
                quality_relevant=True,
            ),
            SchemaField(
                name="to_node_id",
                type=FieldType.STRING,
                required=True,
                description="Ziel-Node ID",
                quality_relevant=True,
            ),
            SchemaField(
                name="relationship_type",
                type=FieldType.STRING,
                required=True,
                max_length=50,
                description="Art der Beziehung (CONTAINS, CITES, AUTHORED_BY, etc.)",
                quality_relevant=True,
            ),
            SchemaField(
                name="weight",
                type=FieldType.FLOAT,
                required=False,
                default=1.0,
                description="Gewichtung der Beziehung",
            ),
            SchemaField(
                name="created_at",
                type=FieldType.DATETIME,
                required=True,
                description="Erstellungsdatum",
            ),
            SchemaField(
                name="properties",
                type=FieldType.JSON,
                required=False,
                description="Zusätzliche Eigenschaften als JSON",
            ),
        ]

        return {
            "document_nodes": document_nodes_schema,
            "chunk_nodes": chunk_nodes_schema,
            "relationships": relationships_schema,
        }

    # === SCHEMA GENERATION METHODS ===

    def generate_sqlite_schema(self, table_name: str) -> str:
        """Generiert SQLite CREATE TABLE Statement"""
        if (
            "relational" not in self.schemas
            or table_name not in self.schemas["relational"]
        ):
            raise ValueError(f"Schema für Tabelle '{table_name}' nicht gefunden")

        fields = self.schemas["relational"][table_name]
        sql_parts: list[Any] = []

        sql_parts.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")

        field_definitions: list[Any] = []
        for field in fields:
            definition = f"  {field.name} {self._sqlite_type_mapping(field.type)}"

            if field.required:
                definition += " NOT NULL"
            if field.unique and field.name != "id":
                definition += " UNIQUE"
            if field.default is not None:
                definition += f" DEFAULT {self._format_default_value(field.default)}"

            field_definitions.append(definition)

        sql_parts.append(",\n".join(field_definitions))

        # Primary Key
        id_field = next((f for f in fields if f.name == "id"), None)
        if id_field:
            if id_field.type == FieldType.INTEGER:
                sql_parts.append(",\n  PRIMARY KEY (id AUTOINCREMENT)")
            else:
                sql_parts.append(",\n  PRIMARY KEY (id)")

        sql_parts.append("\n);")

        # Indexes
        index_statements: list[Any] = []
        for field in fields:
            if field.indexed and field.name != "id":
                index_name = f"idx_{table_name}_{field.name}"
                index_statements.append(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({field.name});"
                )

        schema_sql = "".join(sql_parts)
        if index_statements:
            schema_sql += "\n\n" + "\n".join(index_statements)

        return schema_sql

    def generate_postgresql_schema(self, table_name: str) -> str:
        """Generiert PostgreSQL CREATE TABLE Statement"""
        if (
            "relational" not in self.schemas
            or table_name not in self.schemas["relational"]
        ):
            raise ValueError(f"Schema für Tabelle '{table_name}' nicht gefunden")

        fields = self.schemas["relational"][table_name]
        sql_parts: list[Any] = []

        sql_parts.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")

        field_definitions: list[Any] = []
        for field in fields:
            definition = f"  {field.name} {self._postgresql_type_mapping(field.type)}"

            if field.required:
                definition += " NOT NULL"
            if field.unique and field.name != "id":
                definition += " UNIQUE"
            if field.default is not None:
                definition += f" DEFAULT {self._format_default_value(field.default)}"

            field_definitions.append(definition)

        sql_parts.append(",\n".join(field_definitions))

        # Primary Key
        id_field = next((f for f in fields if f.name == "id"), None)
        if id_field:
            if id_field.type == FieldType.INTEGER:
                sql_parts.append(",\n  PRIMARY KEY (id)")
            else:
                sql_parts.append(",\n  PRIMARY KEY (id)")

        sql_parts.append("\n);")

        # Indexes
        index_statements: list[Any] = []
        for field in fields:
            if field.indexed and field.name != "id":
                index_name = f"idx_{table_name}_{field.name}"
                index_statements.append(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({field.name});"
                )

        schema_sql = "".join(sql_parts)
        if index_statements:
            schema_sql += "\n\n" + "\n".join(index_statements)

        return schema_sql

    def generate_chromadb_schema(self, collection_name: str) -> Dict:
        """Generiert ChromaDB Collection Schema"""
        if (
            "vector" not in self.schemas
            or collection_name not in self.schemas["vector"]
        ):
            raise ValueError(
                f"Schema für Collection '{collection_name}' nicht gefunden"
            )

        fields = self.schemas["vector"][collection_name]

        # ChromaDB Schema Definition
        schema = {
            "collection_name": collection_name,
            "metadata_fields": {},
            "required_fields": [],
            "security_fields": [],
            "quality_fields": [],
        }

        for field in fields:
            if field.type == FieldType.VECTOR:
                continue  # Embeddings werden separat behandelt

            if field.type in [FieldType.STRING, FieldType.TEXT]:
                schema["metadata_fields"][field.name] = "string"
            elif field.type == FieldType.INTEGER:
                schema["metadata_fields"][field.name] = "int"
            elif field.type == FieldType.FLOAT:
                schema["metadata_fields"][field.name] = "float"
            elif field.type == FieldType.BOOLEAN:
                schema["metadata_fields"][field.name] = "bool"
            elif field.type == FieldType.DATETIME:
                schema["metadata_fields"][field.name] = "string"  # ISO format

            if field.required:
                schema["required_fields"].append(field.name)
            if field.security_sensitive:
                schema["security_fields"].append(field.name)
            if field.quality_relevant:
                schema["quality_fields"].append(field.name)

        return schema

    def generate_neo4j_schema(self) -> Dict[str, List[str]]:
        """Generiert Neo4j Constraints und Indexes"""
        graph_schemas = self.schemas.get("graph", {})

        constraints: list[Any] = []
        indexes: list[Any] = []

        # Document Nodes
        if "document_nodes" in graph_schemas:
            constraints.append(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE"
            )
            indexes.append(
                "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.rechtsgebiet)"
            )
            indexes.append("CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.gericht)")
            indexes.append(
                "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.created_at)"
            )

        # Chunk Nodes
        if "chunk_nodes" in graph_schemas:
            constraints.append(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE"
            )
            indexes.append(
                "CREATE INDEX IF NOT EXISTS FOR (c:Chunk) ON (c.chunk_index)"
            )

        return {"constraints": constraints, "indexes": indexes}

    # === TYPE MAPPING METHODS ===

    def _sqlite_type_mapping(self, field_type: FieldType) -> str:
        """Mappt FieldType auf SQLite Datentypen"""
        mapping = {
            FieldType.STRING: "VARCHAR(255)",
            FieldType.INTEGER: "INTEGER",
            FieldType.FLOAT: "REAL",
            FieldType.BOOLEAN: "BOOLEAN",
            FieldType.DATETIME: "DATETIME",
            FieldType.TEXT: "TEXT",
            FieldType.JSON: "TEXT",  # SQLite speichert JSON als TEXT
            FieldType.HASH: "VARCHAR(128)",
            FieldType.UUID: "VARCHAR(36)",
        }
        return mapping.get(field_type, "TEXT")

    def _postgresql_type_mapping(self, field_type: FieldType) -> str:
        """Mappt FieldType auf PostgreSQL Datentypen"""
        mapping = {
            FieldType.STRING: "VARCHAR(255)",
            FieldType.INTEGER: "INTEGER",
            FieldType.FLOAT: "REAL",
            FieldType.BOOLEAN: "BOOLEAN",
            FieldType.DATETIME: "TIMESTAMP",
            FieldType.TEXT: "TEXT",
            FieldType.JSON: "JSONB",
            FieldType.HASH: "VARCHAR(128)",
            FieldType.UUID: "UUID",
        }
        return mapping.get(field_type, "TEXT")

    def _format_default_value(self, value: Any) -> str:
        """Formatiert Default-Werte für SQL"""
        if isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, bool):
            return "1" if value else "0"  # SQLite boolean
        else:
            return str(value)

    # === UTILITY METHODS ===

    def get_schema_fields(self, db_type: str, schema_name: str) -> List[SchemaField]:
        """Gibt Schema-Felder für einen bestimmten Typ zurück"""
        if db_type not in self.schemas:
            raise ValueError(f"Unbekannter Datenbanktyp: {db_type}")

        if schema_name not in self.schemas[db_type]:
            raise ValueError(f"Unbekanntes Schema: {schema_name} für Typ {db_type}")

        return self.schemas[db_type][schema_name]

    def get_security_fields(self, db_type: str, schema_name: str) -> List[str]:
        """Gibt alle sicherheitsrelevanten Felder zurück"""
        fields = self.get_schema_fields(db_type, schema_name)
        return [field.name for field in fields if field.security_sensitive]

    def get_quality_fields(self, db_type: str, schema_name: str) -> List[str]:
        """Gibt alle qualitätsrelevanten Felder zurück"""
        fields = self.get_schema_fields(db_type, schema_name)
        return [field.name for field in fields if field.quality_relevant]

    def validate_document_data(
        self, db_type: str, schema_name: str, data: Dict
    ) -> Dict:
        """Validiert Dokumentdaten gegen Schema"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "invalid_types": [],
        }

        fields = self.get_schema_fields(db_type, schema_name)

        # Required Fields Check
        for field in fields:
            if field.required and field.name not in data:
                validation_result["missing_required"].append(field.name)
                validation_result["valid"] = False

        # Type Validation (vereinfacht)
        for field_name, field_value in data.items():
            field_def = next((f for f in fields if f.name == field_name), None)
            if field_def:
                if not self._validate_field_type(field_value, field_def.type):
                    validation_result["invalid_types"].append(field_name)
                    validation_result["valid"] = False

        return validation_result

    def _validate_field_type(self, value: Any, expected_type: FieldType) -> bool:
        """Vereinfachte Typ-Validierung"""
        if expected_type == FieldType.STRING and isinstance(value, str):
            return True
        elif expected_type == FieldType.INTEGER and isinstance(value, int):
            return True
        elif expected_type == FieldType.FLOAT and isinstance(value, (int, float)):
            return True
        elif expected_type == FieldType.BOOLEAN and isinstance(value, bool):
            return True
        # Weitere Validierungen...
        return True  # Vereinfacht für Demo


# === FACTORY & UTILITY FUNCTIONS ===


def create_database_schemas() -> DatabaseSchemaManager:
    """Factory für DatabaseSchemaManager"""
    return DatabaseSchemaManager()


def generate_all_sqlite_schemas(schema_manager: DatabaseSchemaManager) -> str:
    """Generiert alle SQLite Schemas"""
    schemas: list[Any] = []

    for table_name in ["documents", "document_chunks", "keywords", "audit_log"]:
        try:
            schema_sql = schema_manager.generate_sqlite_schema(table_name)
            schemas.append(f"-- {table_name.upper()} TABLE")
            schemas.append(schema_sql)
            schemas.append("")
        except ValueError as e:
            schemas.append(f"-- ERROR: {e}")

    return "\n".join(schemas)


# === DEMONSTRATION ===
if __name__ == "__main__":
    print("=== DATABASE SCHEMA DEFINITIONS TEST ===")

    # Schema Manager erstellen
    schema_mgr = create_database_schemas()

    print("\n--- SQLITE SCHEMA GENERATION ---")
    try:
        documents_schema = schema_mgr.generate_sqlite_schema("documents")
        print("✅ Documents Schema:")
        print(
            documents_schema[:500] + "..."
            if len(documents_schema) > 500
            else documents_schema
        )

        chunks_schema = schema_mgr.generate_sqlite_schema("document_chunks")
        print("\n✅ Document Chunks Schema:")
        print(
            chunks_schema[:300] + "..." if len(chunks_schema) > 300 else chunks_schema
        )

    except Exception as e:
        print(f"❌ SQLite Schema Generation Error: {e}")

    print("\n--- CHROMADB SCHEMA GENERATION ---")
    try:
        chromadb_schema = schema_mgr.generate_chromadb_schema("document_vectors")
        print("✅ ChromaDB Schema:")
        print(json.dumps(chromadb_schema, indent=2))

    except Exception as e:
        print(f"❌ ChromaDB Schema Generation Error: {e}")

    print("\n--- NEO4J SCHEMA GENERATION ---")
    try:
        neo4j_schema = schema_mgr.generate_neo4j_schema()
        print("✅ Neo4j Constraints & Indexes:")
        print(f"Constraints: {len(neo4j_schema['constraints'])}")
        print(f"Indexes: {len(neo4j_schema['indexes'])}")

        for constraint in neo4j_schema["constraints"][:2]:
            print(f"  - {constraint}")

    except Exception as e:
        print(f"❌ Neo4j Schema Generation Error: {e}")

    print("\n--- SECURITY & QUALITY FIELDS ---")
    try:
        security_fields = schema_mgr.get_security_fields("relational", "documents")
        quality_fields = schema_mgr.get_quality_fields("relational", "documents")

        print(f"✅ Security Fields: {security_fields}")
        print(f"✅ Quality Fields: {quality_fields}")

    except Exception as e:
        print(f"❌ Fields Extraction Error: {e}")

    print("\n--- DATA VALIDATION ---")
    try:
        test_document = {
            "id": "doc_12345",
            "title": "Test Arbeitsrecht Dokument",
            "file_path": "/test/document.pdf",
            "rechtsgebiet": "Arbeitsrecht",
            "created_at": "2025-08-20T15:30:00",
            "document_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "content_hash": "abc123def456...",
            "checksum": "checksum123",
            "security_level": "internal",
        }

        validation = schema_mgr.validate_document_data(
            "relational", "documents", test_document
        )
        print(f"✅ Validation Result: {'VALID' if validation['valid'] else 'INVALID'}")

        if validation["missing_required"]:
            print(f"   Missing Required: {validation['missing_required']}")
        if validation["invalid_types"]:
            print(f"   Invalid Types: {validation['invalid_types']}")

    except Exception as e:
        print(f"❌ Validation Error: {e}")

    print("\n🎉 Database Schema Definitions Test abgeschlossen!")

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_schemas"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
)
module_file_key = "32a0a6c04770fbb9f376a7fe50fe948a17b168d233d6ad4dead96e44cea5fad2"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
