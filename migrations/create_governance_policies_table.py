#!/usr/bin/env python3
"""
Governance Policies Table Migration
====================================

Erstellt die governance_policies Tabelle für Unternehmens-Richtlinien und Compliance-Regeln.

Use Cases:
- Dokumenten-Aufbewahrungsfristen (Retention Policies)
- Zugriffskontroll-Richtlinien (Access Control)
- DSGVO-Compliance-Regeln (Data Protection)
- Klassifikations-Regeln (Document Classification)
- Qualitäts-Standards (Quality Thresholds)
- Audit-Anforderungen (Audit Requirements)

Tabelle: governance_policies
Spalten:
- id (SERIAL PRIMARY KEY)
- policy_id (TEXT NOT NULL, UNIQUE)
- name (TEXT NOT NULL)
- description (TEXT)
- policy_type (TEXT NOT NULL) - 'retention', 'access_control', 'classification', 'quality', 'audit', 'custom'
- scope (TEXT) - 'global', 'department', 'project', 'document_type'
- rules (JSONB NOT NULL) - Regelwerk als JSON
- status (TEXT) - 'active', 'draft', 'archived'
- priority (INTEGER) - Priorität bei Regelkonflikten
- effective_from (TIMESTAMP)
- effective_until (TIMESTAMP)
- created_by (TEXT)
- created_at (TIMESTAMP DEFAULT NOW())
- updated_at (TIMESTAMP DEFAULT NOW())
- approved_by (TEXT)
- approved_at (TIMESTAMP)
- metadata (JSONB)

Autor: Covina System
Datum: 17. Oktober 2025
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

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


def create_governance_policies_table(conn):
    """Erstelle governance_policies Tabelle"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS governance_policies (
        id SERIAL PRIMARY KEY,
        policy_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT,
        policy_type TEXT NOT NULL CHECK (policy_type IN (
            'retention', 'access_control', 'classification', 
            'quality', 'audit', 'compliance', 'custom'
        )),
        scope TEXT DEFAULT 'global' CHECK (scope IN (
            'global', 'department', 'project', 'document_type', 'custom'
        )),
        
        -- Regelwerk (JSON)
        rules JSONB NOT NULL,
        
        -- Status
        status TEXT DEFAULT 'active' CHECK (status IN ('active', 'draft', 'archived')),
        priority INTEGER DEFAULT 100,
        
        -- Gültigkeit
        effective_from TIMESTAMP DEFAULT NOW(),
        effective_until TIMESTAMP,
        
        -- Tracking
        created_by TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        approved_by TEXT,
        approved_at TIMESTAMP,
        
        -- Metadata
        metadata JSONB DEFAULT '{}'
    );
    """
    
    # Indizes
    create_indexes_sql = [
        """
        CREATE INDEX IF NOT EXISTS idx_governance_policy_id 
        ON governance_policies(policy_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_governance_policy_type 
        ON governance_policies(policy_type);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_governance_scope 
        ON governance_policies(scope);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_governance_status 
        ON governance_policies(status);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_governance_priority 
        ON governance_policies(priority DESC);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_governance_effective 
        ON governance_policies(effective_from, effective_until);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_governance_rules 
        ON governance_policies USING GIN(rules);
        """
    ]
    
    # Trigger für updated_at
    create_trigger_sql = """
    CREATE OR REPLACE FUNCTION update_governance_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS governance_updated_at_trigger ON governance_policies;
    CREATE TRIGGER governance_updated_at_trigger
    BEFORE UPDATE ON governance_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_governance_updated_at();
    """
    
    cursor = conn.cursor()
    
    try:
        # Erstelle Tabelle
        logger.info("📝 Erstelle governance_policies Tabelle...")
        cursor.execute(create_table_sql)
        conn.commit()
        logger.info("✅ Tabelle erstellt")
        
        # Erstelle Indizes
        logger.info("📝 Erstelle Indizes...")
        for idx_sql in create_indexes_sql:
            cursor.execute(idx_sql)
        conn.commit()
        logger.info(f"✅ {len(create_indexes_sql)} Indizes erstellt")
        
        # Erstelle Trigger
        logger.info("📝 Erstelle Trigger...")
        cursor.execute(create_trigger_sql)
        conn.commit()
        logger.info("✅ Trigger erstellt")
        
        # Verifiziere Schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'governance_policies'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        logger.info("\n📊 Governance Policies Schema:")
        logger.info("=" * 70)
        for col in columns:
            logger.info(f"  {col[0]:25} {col[1]:20} (nullable={col[2]})")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def insert_sample_policies(conn):
    """Füge Beispiel-Policies ein"""
    
    # Policy 1: Retention Policy für Rechnungen
    retention_policy = {
        'policy_id': 'retention_invoices_10y',
        'name': 'Rechnungsaufbewahrung 10 Jahre',
        'description': 'Gesetzliche Aufbewahrungsfrist für Rechnungen gemäß HGB §257',
        'policy_type': 'retention',
        'scope': 'document_type',
        'rules': json.dumps({
            'document_types': ['invoice', 'receipt'],
            'retention_period_days': 3650,  # 10 Jahre
            'auto_archive_after_days': 3650,
            'delete_allowed': False,
            'legal_basis': 'HGB §257 Abs. 1 Nr. 1'
        }),
        'status': 'active',
        'priority': 100,
        'created_by': 'system'
    }
    
    # Policy 2: DSGVO Löschpflicht
    gdpr_deletion = {
        'policy_id': 'gdpr_deletion_personal_data',
        'name': 'DSGVO Löschpflicht personenbezogener Daten',
        'description': 'Automatische Löschung personenbezogener Daten nach Zweckerfüllung',
        'policy_type': 'compliance',
        'scope': 'global',
        'rules': json.dumps({
            'applies_to': 'personal_data',
            'max_retention_days': 365,  # 1 Jahr nach Zweckerfüllung
            'deletion_required': True,
            'exceptions': ['legal_requirement', 'active_contract'],
            'legal_basis': 'DSGVO Art. 17 (Recht auf Löschung)'
        }),
        'status': 'active',
        'priority': 200,  # Höhere Priorität als Retention
        'created_by': 'system'
    }
    
    # Policy 3: Quality Threshold
    quality_policy = {
        'policy_id': 'quality_threshold_classification',
        'name': 'Mindest-Qualität für Klassifikation',
        'description': 'Dokumente mit niedriger Quality Score müssen manuell geprüft werden',
        'policy_type': 'quality',
        'scope': 'global',
        'rules': json.dumps({
            'min_quality_score': 0.8,
            'action_below_threshold': 'manual_review',
            'review_queue_priority': 'high',
            'auto_reject_below': 0.5
        }),
        'status': 'active',
        'priority': 50,
        'created_by': 'system'
    }
    
    # Policy 4: Access Control
    access_control = {
        'policy_id': 'access_control_confidential',
        'name': 'Zugriffskontrolle vertrauliche Dokumente',
        'description': 'Vertrauliche Dokumente nur für autorisierte Benutzer',
        'policy_type': 'access_control',
        'scope': 'document_type',
        'rules': json.dumps({
            'document_classifications': ['confidential', 'secret'],
            'required_roles': ['manager', 'admin'],
            'audit_access': True,
            'encryption_required': True
        }),
        'status': 'active',
        'priority': 150,
        'created_by': 'system'
    }
    
    # Policy 5: Audit Requirements
    audit_policy = {
        'policy_id': 'audit_financial_documents',
        'name': 'Audit-Trail für Finanzdokumente',
        'description': 'Vollständige Protokollierung aller Zugriffe auf Finanzdokumente',
        'policy_type': 'audit',
        'scope': 'document_type',
        'rules': json.dumps({
            'document_types': ['invoice', 'contract', 'financial_report'],
            'log_all_access': True,
            'log_all_modifications': True,
            'retention_audit_log_days': 7300,  # 20 Jahre
            'alert_on_suspicious_access': True
        }),
        'status': 'active',
        'priority': 75,
        'created_by': 'system'
    }
    
    policies = [retention_policy, gdpr_deletion, quality_policy, access_control, audit_policy]
    
    insert_sql = """
    INSERT INTO governance_policies 
        (policy_id, name, description, policy_type, scope, rules, status, priority, created_by)
    VALUES 
        (%(policy_id)s, %(name)s, %(description)s, %(policy_type)s, %(scope)s, 
         %(rules)s::jsonb, %(status)s, %(priority)s, %(created_by)s)
    ON CONFLICT (policy_id) DO NOTHING;
    """
    
    cursor = conn.cursor()
    
    try:
        logger.info("\n📝 Füge Beispiel-Policies ein...")
        for policy in policies:
            cursor.execute(insert_sql, policy)
            logger.info(f"  ✅ {policy['name']}")
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM governance_policies;")
        count = cursor.fetchone()[0]
        logger.info(f"\n✅ {count} Governance Policies gespeichert")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def main():
    """Haupt-Migration"""
    logger.info("=" * 80)
    logger.info("🚀 Governance Policies Migration")
    logger.info("=" * 80)
    
    try:
        conn = get_db_connection()
        logger.info("✅ Verbindung hergestellt")
        
        if not create_governance_policies_table(conn):
            logger.error("❌ Migration fehlgeschlagen")
            return False
        
        # Sample Data
        insert_sample = input("\n❓ Beispiel-Policies einfügen? (y/n): ").strip().lower()
        if insert_sample == 'y':
            insert_sample_policies(conn)
        
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
