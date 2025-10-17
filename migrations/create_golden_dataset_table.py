#!/usr/bin/env python3
"""
Golden Dataset Table Migration
===============================

Erstellt die golden_dataset Tabelle für manuell kuratierte Beispieldokumente.

Golden Dataset Use Case:
- Manuell überprüfte und als korrekt markierte Dokumente
- Training/Validierung für ML-Modelle
- Benchmarking für Klassifikationsgenauigkeit
- Review Queue Resolved Items

Tabelle: golden_dataset
Spalten:
- id (SERIAL PRIMARY KEY)
- document_id (TEXT NOT NULL, UNIQUE)
- classification (TEXT NOT NULL)
- quality_score (DECIMAL(3,2))
- reviewed_by (TEXT)
- reviewed_at (TIMESTAMP)
- notes (TEXT)
- metadata (JSONB)
- created_at (TIMESTAMP DEFAULT NOW())
- updated_at (TIMESTAMP DEFAULT NOW())

Autor: Covina System
Datum: 17. Oktober 2025
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    """PostgreSQL Verbindung herstellen"""
    config = {
        'host': os.getenv('POSTGRES_HOST', '192.168.178.94'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DATABASE', 'postgres'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    logger.info(f"📡 Verbinde mit PostgreSQL: {config['host']}:{config['port']}/{config['database']}")
    return psycopg2.connect(**config)


def create_golden_dataset_table(conn):
    """Erstelle golden_dataset Tabelle"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS golden_dataset (
        id SERIAL PRIMARY KEY,
        document_id TEXT NOT NULL UNIQUE,
        classification TEXT NOT NULL,
        quality_score DECIMAL(3,2) CHECK (quality_score >= 0 AND quality_score <= 1),
        reviewed_by TEXT,
        reviewed_at TIMESTAMP,
        notes TEXT,
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    # Index für schnelle document_id Lookups
    create_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_golden_dataset_document_id 
    ON golden_dataset(document_id);
    """
    
    # Index für classification Filtering
    create_classification_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_golden_dataset_classification 
    ON golden_dataset(classification);
    """
    
    # Index für reviewed_by Filtering
    create_reviewed_by_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_golden_dataset_reviewed_by 
    ON golden_dataset(reviewed_by);
    """
    
    # Trigger für updated_at Auto-Update
    create_trigger_function_sql = """
    CREATE OR REPLACE FUNCTION update_golden_dataset_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    
    create_trigger_sql = """
    DROP TRIGGER IF EXISTS golden_dataset_updated_at_trigger ON golden_dataset;
    CREATE TRIGGER golden_dataset_updated_at_trigger
    BEFORE UPDATE ON golden_dataset
    FOR EACH ROW
    EXECUTE FUNCTION update_golden_dataset_updated_at();
    """
    
    cursor = conn.cursor()
    
    try:
        # Erstelle Tabelle
        logger.info("📝 Erstelle golden_dataset Tabelle...")
        cursor.execute(create_table_sql)
        conn.commit()
        logger.info("✅ golden_dataset Tabelle erstellt")
        
        # Erstelle Indizes
        logger.info("📝 Erstelle Indizes...")
        cursor.execute(create_index_sql)
        cursor.execute(create_classification_index_sql)
        cursor.execute(create_reviewed_by_index_sql)
        conn.commit()
        logger.info("✅ Indizes erstellt")
        
        # Erstelle Trigger
        logger.info("📝 Erstelle updated_at Trigger...")
        cursor.execute(create_trigger_function_sql)
        cursor.execute(create_trigger_sql)
        conn.commit()
        logger.info("✅ Trigger erstellt")
        
        # Verifiziere Tabelle
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'golden_dataset'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        logger.info("\n📊 Golden Dataset Schema:")
        logger.info("=" * 60)
        for col in columns:
            logger.info(f"  {col[0]:20} {col[1]:15} (nullable={col[2]})")
        logger.info("=" * 60)
        
        # Verifiziere Indizes
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'golden_dataset';
        """)
        indexes = cursor.fetchall()
        
        logger.info("\n🔍 Indizes:")
        logger.info("=" * 60)
        for idx in indexes:
            logger.info(f"  {idx[0]}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fehler beim Erstellen der Tabelle: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def insert_sample_data(conn):
    """Füge Beispiel-Daten ein (optional)"""
    
    sample_data = [
        {
            'document_id': 'sample_invoice_001',
            'classification': 'invoice',
            'quality_score': 0.98,
            'reviewed_by': 'admin',
            'notes': 'Perfekt klassifizierte Rechnung, alle Pflichtfelder vorhanden',
            'metadata': '{"source": "manual_review", "tags": ["high_quality", "benchmark"]}'
        },
        {
            'document_id': 'sample_contract_001',
            'classification': 'contract',
            'quality_score': 0.95,
            'reviewed_by': 'admin',
            'notes': 'Standardvertrag mit allen relevanten Klauseln',
            'metadata': '{"source": "manual_review", "tags": ["contract_template"]}'
        },
        {
            'document_id': 'sample_letter_001',
            'classification': 'letter',
            'quality_score': 0.92,
            'reviewed_by': 'admin',
            'notes': 'Geschäftsbrief mit korrekter Anrede und Abschluss',
            'metadata': '{"source": "manual_review", "tags": ["business_letter"]}'
        }
    ]
    
    insert_sql = """
    INSERT INTO golden_dataset 
        (document_id, classification, quality_score, reviewed_by, reviewed_at, notes, metadata)
    VALUES 
        (%(document_id)s, %(classification)s, %(quality_score)s, %(reviewed_by)s, NOW(), %(notes)s, %(metadata)s::jsonb)
    ON CONFLICT (document_id) DO NOTHING;
    """
    
    cursor = conn.cursor()
    
    try:
        logger.info("\n📝 Füge Beispiel-Daten ein...")
        for data in sample_data:
            cursor.execute(insert_sql, data)
        
        conn.commit()
        
        # Zähle eingefügte Zeilen
        cursor.execute("SELECT COUNT(*) FROM golden_dataset;")
        count = cursor.fetchone()[0]
        
        logger.info(f"✅ {count} Golden Dataset Einträge vorhanden")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fehler beim Einfügen der Daten: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def main():
    """Haupt-Migration"""
    logger.info("=" * 80)
    logger.info("🚀 Golden Dataset Migration")
    logger.info("=" * 80)
    
    try:
        # Verbindung herstellen
        conn = get_db_connection()
        logger.info("✅ Verbindung hergestellt")
        
        # Tabelle erstellen
        if not create_golden_dataset_table(conn):
            logger.error("❌ Migration fehlgeschlagen")
            return False
        
        # Optional: Beispiel-Daten einfügen
        insert_sample = input("\n❓ Beispiel-Daten einfügen? (y/n): ").strip().lower()
        if insert_sample == 'y':
            insert_sample_data(conn)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Migration erfolgreich abgeschlossen!")
        logger.info("=" * 80)
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration Fehler: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
