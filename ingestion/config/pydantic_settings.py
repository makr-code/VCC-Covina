"""
Pydantic Settings for Type-Safe Configuration

Provides:
- Type-safe configuration with pydantic BaseSettings
- Environment variable support (.env files)
- Validation and default values

Usage:
    from ingestion.config.pydantic_settings import app_settings
    
    print(app_settings.neo4j_uri)
    print(app_settings.extraction.confidence_threshold)
"""
from __future__ import annotations

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionSettings(BaseSettings):
    """Extraction-specific settings."""
    
    enabled_extractors: List[str] = Field(
        default=["legal_entity_extractor", "norm_extractor"],
        description="List of enabled extractors"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for entity extraction"
    )
    max_entities_per_document: int = Field(
        default=100,
        ge=1,
        description="Maximum entities to extract per document"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="EXTRACTION_",
        case_sensitive=False
    )


class NLPSettings(BaseSettings):
    """NLP-specific settings."""
    
    spacy_model: str = Field(
        default="de_core_news_md",
        description="spaCy model name"
    )
    batch_size: int = Field(
        default=50,
        ge=1,
        description="Batch size for NLP processing"
    )
    max_length: int = Field(
        default=1000000,
        ge=1000,
        description="Maximum document length for spaCy"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="NLP_",
        case_sensitive=False
    )


class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    
    postgres_host: str = Field(default="192.168.178.94")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_database: str = Field(default="postgres")
    
    neo4j_uri: str = Field(default="bolt://192.168.178.94:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")
    
    chromadb_host: str = Field(default="192.168.178.94")
    chromadb_port: int = Field(default=8000)
    
    couchdb_host: str = Field(default="192.168.178.94")
    couchdb_port: int = Field(default=32770)
    couchdb_user: str = Field(default="admin")
    couchdb_password: str = Field(default="admin")
    couchdb_database: str = Field(default="covina")
    
    model_config = SettingsConfigDict(
        case_sensitive=False
    )


class AppSettings(BaseSettings):
    """Global application settings."""
    
    # Nested settings
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    nlp: NLPSettings = Field(default_factory=NLPSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    
    # Top-level settings
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
app_settings = AppSettings()
