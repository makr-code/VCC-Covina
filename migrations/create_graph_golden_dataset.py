#!/usr/bin/env python3
"""
Graph Golden Dataset Migration
===============================

Erstellt Infrastruktur für Graph-basierte Golden Datasets:
1. PostgreSQL Tabelle für Metadata/Beschreibungen
2. Neo4j Graph Patterns für Prozessvalidierung

Use Cases:
- Workflow-Validierung (Prozess-Patterns)
- Dokumenten-Beziehungen (Rechnungen → Lieferungen → Verträge)
- Compliance-Pfade (DSGVO-konforme Datenflüsse)
- Organisationsstrukturen (Abteilungen, Rollen, Hierarchien)

Hybrid Storage:
- PostgreSQL: Metadata (Name, Beschreibung, Tags, Status)
- Neo4j: Graph Pattern (Nodes + Relationships)

Autor: Covina System
Datum: 17. Oktober 2025
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j Import (optional)
NEO4J_AVAILABLE = False
GraphDatabase = None

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except (ImportError, AttributeError) as e:
    # AttributeError: Python 3.13 compatibility issue (socket.EAI_ADDRFAMILY)
    NEO4J_AVAILABLE = False
    if isinstance(e, AttributeError):
        logger.warning(f"⚠️ Neo4j Driver nicht Python 3.13 kompatibel: {e}")
    else:
        logger.warning("⚠️ Neo4j Driver nicht verfügbar - nur PostgreSQL Migration")


def get_postgres_connection():
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


def get_neo4j_driver():
    """Neo4j Driver erstellen"""
    if not NEO4J_AVAILABLE:
        logger.warning("⚠️ Neo4j Driver nicht verfügbar")
        return None
    
    uri = os.getenv('NEO4J_URI', 'bolt://192.168.178.94:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'neo4j')
    
    logger.info(f"📡 Verbinde mit Neo4j: {uri}")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        logger.info("✅ Neo4j Verbindung erfolgreich")
        return driver
    except Exception as e:
        logger.error(f"❌ Neo4j Verbindung fehlgeschlagen: {e}")
        return None


def create_postgres_table(conn):
    """Erstelle PostgreSQL Tabelle für Graph Golden Dataset Metadata"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS graph_golden_dataset (
        id SERIAL PRIMARY KEY,
        pattern_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        
        -- Graph Pattern Definition (als JSON)
        nodes_definition JSONB NOT NULL,
        relationships_definition JSONB NOT NULL,
        
        -- Validation Rules
        validation_rules JSONB DEFAULT '{}',
        
        -- Metadata
        created_by TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        reviewed_by TEXT,
        reviewed_at TIMESTAMP,
        
        -- Status & Tags
        status TEXT DEFAULT 'active' CHECK (status IN ('active', 'draft', 'archived')),
        tags TEXT[],
        
        -- Neo4j Reference (Optional)
        neo4j_pattern_label TEXT,
        
        -- Statistics
        usage_count INTEGER DEFAULT 0,
        last_used_at TIMESTAMP,
        
        metadata JSONB DEFAULT '{}'
    );
    """
    
    # Indizes
    create_indexes_sql = [
        """
        CREATE INDEX IF NOT EXISTS idx_graph_golden_pattern_id 
        ON graph_golden_dataset(pattern_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_golden_category 
        ON graph_golden_dataset(category);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_golden_status 
        ON graph_golden_dataset(status);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_golden_tags 
        ON graph_golden_dataset USING GIN(tags);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_golden_nodes 
        ON graph_golden_dataset USING GIN(nodes_definition);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_graph_golden_relationships 
        ON graph_golden_dataset USING GIN(relationships_definition);
        """
    ]
    
    # Trigger für updated_at
    create_trigger_sql = """
    CREATE OR REPLACE FUNCTION update_graph_golden_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS graph_golden_updated_at_trigger ON graph_golden_dataset;
    CREATE TRIGGER graph_golden_updated_at_trigger
    BEFORE UPDATE ON graph_golden_dataset
    FOR EACH ROW
    EXECUTE FUNCTION update_graph_golden_updated_at();
    """
    
    cursor = conn.cursor()
    
    try:
        # Erstelle Tabelle
        logger.info("📝 Erstelle graph_golden_dataset Tabelle...")
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
            WHERE table_name = 'graph_golden_dataset'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        logger.info("\n📊 Graph Golden Dataset Schema:")
        logger.info("=" * 70)
        for col in columns:
            logger.info(f"  {col[0]:30} {col[1]:20} (nullable={col[2]})")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def create_neo4j_constraints(driver):
    """Erstelle Neo4j Constraints für Graph Patterns"""
    if not driver:
        logger.warning("⚠️ Überspringe Neo4j Constraints (kein Driver)")
        return False
    
    constraints = [
        # Unique Constraint für GoldenPattern Nodes
        "CREATE CONSTRAINT golden_pattern_id IF NOT EXISTS FOR (p:GoldenPattern) REQUIRE p.pattern_id IS UNIQUE",
        
        # Unique Constraint für GoldenNode Nodes
        "CREATE CONSTRAINT golden_node_id IF NOT EXISTS FOR (n:GoldenNode) REQUIRE n.node_id IS UNIQUE",
        
        # Index für schnelles Filtern
        "CREATE INDEX golden_pattern_category IF NOT EXISTS FOR (p:GoldenPattern) ON (p.category)",
        "CREATE INDEX golden_pattern_status IF NOT EXISTS FOR (p:GoldenPattern) ON (p.status)"
    ]
    
    try:
        with driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"✅ Constraint/Index: {constraint[:50]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Constraint/Index bereits vorhanden oder Fehler: {e}")
        
        logger.info("✅ Neo4j Constraints/Indizes erstellt")
        return True
        
    except Exception as e:
        logger.error(f"❌ Neo4j Constraints Fehler: {e}")
        return False


def insert_sample_patterns(pg_conn, neo4j_driver):
    """Füge Beispiel-Graph-Patterns ein"""
    
    # Beispiel 1: Invoice → Delivery → Contract Workflow
    invoice_workflow = {
        'pattern_id': 'invoice_delivery_contract_workflow',
        'name': 'Rechnung → Lieferung → Vertrag Workflow',
        'description': 'Standard-Workflow für Rechnungsverarbeitung mit Liefernachweis und Vertragsreferenz',
        'category': 'invoice_processing',
        'nodes_definition': json.dumps([
            {'id': 'contract', 'label': 'Contract', 'properties': {'type': 'supplier_contract'}},
            {'id': 'delivery', 'label': 'Delivery', 'properties': {'status': 'completed'}},
            {'id': 'invoice', 'label': 'Invoice', 'properties': {'status': 'approved'}}
        ]),
        'relationships_definition': json.dumps([
            {'from': 'contract', 'to': 'delivery', 'type': 'TRIGGERED', 'properties': {}},
            {'from': 'delivery', 'to': 'invoice', 'type': 'BILLED_BY', 'properties': {'verified': True}}
        ]),
        'validation_rules': json.dumps({
            'required_nodes': ['contract', 'delivery', 'invoice'],
            'required_relationships': ['TRIGGERED', 'BILLED_BY'],
            'node_constraints': {
                'invoice': {'status': ['approved', 'paid']},
                'delivery': {'status': ['completed']}
            }
        }),
        'created_by': 'system',
        'status': 'active',
        'tags': ['invoice', 'workflow', 'validation']
    }
    
    # Beispiel 2: DSGVO Consent Flow
    gdpr_consent = {
        'pattern_id': 'gdpr_consent_flow',
        'name': 'DSGVO Einwilligungs-Prozess',
        'description': 'Validierter Consent-Flow für personenbezogene Datenverarbeitung',
        'category': 'compliance',
        'nodes_definition': json.dumps([
            {'id': 'person', 'label': 'Person', 'properties': {'gdpr_relevant': True}},
            {'id': 'consent', 'label': 'Consent', 'properties': {'status': 'granted'}},
            {'id': 'processing', 'label': 'Processing', 'properties': {'lawful_basis': 'consent'}}
        ]),
        'relationships_definition': json.dumps([
            {'from': 'person', 'to': 'consent', 'type': 'GAVE', 'properties': {'timestamp': 'required'}},
            {'from': 'consent', 'to': 'processing', 'type': 'AUTHORIZES', 'properties': {'scope': 'defined'}}
        ]),
        'validation_rules': json.dumps({
            'required_nodes': ['person', 'consent', 'processing'],
            'required_relationships': ['GAVE', 'AUTHORIZES'],
            'temporal_constraints': {
                'GAVE': {'must_precede': 'AUTHORIZES'}
            }
        }),
        'created_by': 'system',
        'status': 'active',
        'tags': ['gdpr', 'compliance', 'consent']
    }
    
    # Beispiel 3: Organization Hierarchy
    org_hierarchy = {
        'pattern_id': 'organization_hierarchy',
        'name': 'Organisations-Hierarchie',
        'description': 'Standard 3-Level Hierarchie: Company → Department → Team',
        'category': 'organization',
        'nodes_definition': json.dumps([
            {'id': 'company', 'label': 'Company', 'properties': {}},
            {'id': 'department', 'label': 'Department', 'properties': {}},
            {'id': 'team', 'label': 'Team', 'properties': {}}
        ]),
        'relationships_definition': json.dumps([
            {'from': 'company', 'to': 'department', 'type': 'HAS_DEPARTMENT', 'properties': {}},
            {'from': 'department', 'to': 'team', 'type': 'HAS_TEAM', 'properties': {}}
        ]),
        'validation_rules': json.dumps({
            'hierarchy_levels': 3,
            'no_circular_refs': True
        }),
        'created_by': 'system',
        'status': 'active',
        'tags': ['organization', 'hierarchy']
    }
    
    patterns = [invoice_workflow, gdpr_consent, org_hierarchy]
    
    # PostgreSQL Insert
    insert_sql = """
    INSERT INTO graph_golden_dataset 
        (pattern_id, name, description, category, nodes_definition, relationships_definition,
         validation_rules, created_by, status, tags)
    VALUES 
        (%(pattern_id)s, %(name)s, %(description)s, %(category)s, %(nodes_definition)s::jsonb,
         %(relationships_definition)s::jsonb, %(validation_rules)s::jsonb, %(created_by)s,
         %(status)s, %(tags)s)
    ON CONFLICT (pattern_id) DO NOTHING;
    """
    
    cursor = pg_conn.cursor()
    
    try:
        logger.info("\n📝 Füge Beispiel-Patterns ein...")
        for pattern in patterns:
            cursor.execute(insert_sql, pattern)
            logger.info(f"  ✅ {pattern['name']}")
        
        pg_conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM graph_golden_dataset;")
        count = cursor.fetchone()[0]
        logger.info(f"\n✅ {count} Graph Golden Dataset Patterns gespeichert")
        
        # Optional: Neo4j Graph Pattern erstellen
        if neo4j_driver:
            create_neo4j_patterns(neo4j_driver, patterns)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        pg_conn.rollback()
        return False
    finally:
        cursor.close()


def create_neo4j_patterns(driver, patterns):
    """Erstelle Graph Patterns in Neo4j"""
    logger.info("\n📝 Erstelle Neo4j Graph Patterns...")
    
    try:
        with driver.session() as session:
            for pattern in patterns:
                # Create GoldenPattern Node
                create_pattern_node = """
                MERGE (p:GoldenPattern {pattern_id: $pattern_id})
                SET p.name = $name,
                    p.description = $description,
                    p.category = $category,
                    p.status = $status,
                    p.created_at = datetime()
                RETURN p
                """
                
                session.run(create_pattern_node, {
                    'pattern_id': pattern['pattern_id'],
                    'name': pattern['name'],
                    'description': pattern['description'],
                    'category': pattern['category'],
                    'status': pattern['status']
                })
                
                logger.info(f"  ✅ Pattern Node: {pattern['name']}")
        
        logger.info("✅ Neo4j Patterns erstellt")
        
    except Exception as e:
        logger.error(f"❌ Neo4j Pattern Creation Fehler: {e}")


def main():
    """Haupt-Migration"""
    logger.info("=" * 80)
    logger.info("🚀 Graph Golden Dataset Migration")
    logger.info("=" * 80)
    
    # PostgreSQL Migration
    try:
        pg_conn = get_postgres_connection()
        logger.info("✅ PostgreSQL verbunden")
        
        if not create_postgres_table(pg_conn):
            logger.error("❌ PostgreSQL Migration fehlgeschlagen")
            return False
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL Fehler: {e}")
        return False
    
    # Neo4j Migration (Optional)
    neo4j_driver = None
    if NEO4J_AVAILABLE:
        try:
            neo4j_driver = get_neo4j_driver()
            if neo4j_driver:
                create_neo4j_constraints(neo4j_driver)
        except Exception as e:
            logger.warning(f"⚠️ Neo4j Migration übersprungen: {e}")
    
    # Sample Data
    insert_sample = input("\n❓ Beispiel-Patterns einfügen? (y/n): ").strip().lower()
    if insert_sample == 'y':
        insert_sample_patterns(pg_conn, neo4j_driver)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Migration erfolgreich abgeschlossen!")
    logger.info("=" * 80)
    
    pg_conn.close()
    if neo4j_driver:
        neo4j_driver.close()
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
