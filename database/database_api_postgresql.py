#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""



"""
PostgreSQL Relational Database Backend
"""

import logging
import uuid
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.database_api_base import RelationalDatabaseBackend

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

_POSTGRES_IMPL = None
try:
    import psycopg2
    import psycopg2.extras
    _POSTGRES_IMPL = 'psycopg2'
    POSTGRESQL_AVAILABLE = True
except Exception:
    try:
        import pg8000
        _POSTGRES_IMPL = 'pg8000'
        POSTGRESQL_AVAILABLE = True
    except Exception:
        POSTGRESQL_AVAILABLE = False

logger = logging.getLogger(__name__)


class PostgreSQLRelationalBackend(RelationalDatabaseBackend):
    """PostgreSQL relationale Datenbank"""
    
    def __init__(self, config: Dict):
        if not POSTGRESQL_AVAILABLE:
            logger.warning("PostgreSQL drivers not available at import time; connect() will fail if used")
        
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config.get('database', 'postgres')
        self.username = config.get('username', 'postgres')
        self.password = config.get('password', '')
        self.connection = None
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for Postgres: {exc}")
            self.strategy = None
        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"PostgreSQL Backend initialisiert mit Strategie {strategy_version}")
        
    def connect(self) -> bool:
        try:
            if _POSTGRES_IMPL == 'psycopg2':
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password
                )
                try:
                    self.connection.autocommit = True
                except Exception:
                    pass
                # Test connection
                with self.connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
            elif _POSTGRES_IMPL == 'pg8000':
                import pg8000
                # pg8000.connect returns a DB-API compatible connection
                self.connection = pg8000.connect(host=self.host, port=self.port,
                                                 database=self.database, user=self.username,
                                                 password=self.password)
                cur = self.connection.cursor()
                cur.execute('SELECT 1')
                cur.close()
            else:
                logging.error('No Postgres driver available')
                return False
            
            # Basis-Schema erstellen
            self._create_schema()
            logging.info(f"PostgreSQL verbunden: {self.host}:{self.port}/{self.database}")
            return True
            
        except Exception as e:
            logging.error(f"PostgreSQL Verbindung fehlgeschlagen: {e}")
            return False
    
    def _create_schema(self):
        """Erstelle Standard-Schema für relationale Datenbank"""
        try:
            with self.connection.cursor() as cursor:
                # Documents Tabelle
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        title TEXT,
                        content TEXT,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Authors Tabelle
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS authors (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name TEXT UNIQUE NOT NULL,
                        email TEXT,
                        bio TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Document-Author Mapping
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS document_authors (
                        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                        author_id UUID REFERENCES authors(id) ON DELETE CASCADE,
                        role TEXT DEFAULT 'author',
                        PRIMARY KEY (document_id, author_id)
                    )
                ''')
                
                # Tags Tabelle
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tags (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Document-Tag Mapping
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS document_tags (
                        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                        tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
                        PRIMARY KEY (document_id, tag_id)
                    )
                ''')
                
                # Indices für Performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)')
                
        except Exception as e:
            logging.error(f"PostgreSQL Schema erstellen fehlgeschlagen: {e}")
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def is_available(self) -> bool:
        try:
            if self.connection and not self.connection.closed:
                with self.connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        return "PostgreSQL"
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        try:
            if _POSTGRES_IMPL == 'psycopg2':
                cur = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                try:
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)
                    if query.strip().upper().startswith('SELECT'):
                        rows = cur.fetchall()
                        return [dict(row) for row in rows]
                    else:
                        return [{'affected_rows': cur.rowcount}]
                finally:
                    try:
                        cur.close()
                    except Exception:
                        pass
            elif _POSTGRES_IMPL == 'pg8000':
                cur = self.connection.cursor()
                try:
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)
                    if query.strip().upper().startswith('SELECT'):
                        cols = [d[0] for d in cur.description] if cur.description else []
                        rows = cur.fetchall()
                        result = []
                        for r in rows:
                            result.append({cols[i]: r[i] for i in range(len(cols))})
                        return result
                    else:
                        try:
                            self.connection.commit()
                        except Exception:
                            pass
                        return [{'affected_rows': getattr(cur, 'rowcount', 0)}]
                finally:
                    try:
                        cur.close()
                    except Exception:
                        pass
            else:
                return []
                    
        except Exception as e:
            logging.error(f"PostgreSQL Query ausführen fehlgeschlagen: {e}")
            if self.connection:
                self.connection.rollback()
            return []
    
    def insert(self, table: str, data: Dict) -> str:
        try:
            # ID generieren falls nicht vorhanden
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            # JSON Serialisierung für komplexe Datentypen
            processed_data = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    processed_data[key] = json.dumps(value)
                else:
                    processed_data[key] = value
            
            columns = ', '.join(processed_data.keys())
            placeholders = ', '.join(['%s' for _ in processed_data])
            values = tuple(processed_data.values())
            
            query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id'
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, values)
                result = cursor.fetchone()
                
                if result:
                    return str(result[0])
                return data['id']
                
        except Exception as e:
            logging.error(f"PostgreSQL Insert fehlgeschlagen: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def select(self, table: str, conditions: Dict = None, 
              order_by: str = None, limit: int = None) -> List[Dict]:
        try:
            query = f'SELECT * FROM {table}'
            params = []
            
            if conditions:
                where_clauses = []
                for key, value in conditions.items():
                    if isinstance(value, (dict, list)):
                        # JSONB Queries für komplexe Datentypen
                        where_clauses.append(f'{key} @> %s')
                        params.append(json.dumps(value))
                    else:
                        where_clauses.append(f'{key} = %s')
                        params.append(value)
                
                query += f' WHERE {" AND ".join(where_clauses)}'
            
            if order_by:
                query += f' ORDER BY {order_by}'
            
            if limit:
                query += f' LIMIT {limit}'
            
            return self.execute_query(query, tuple(params))
            
        except Exception as e:
            logging.error(f"PostgreSQL Select fehlgeschlagen: {e}")
            return []
    
    def update(self, table: str, data: Dict, conditions: Dict) -> bool:
        try:
            # updated_at hinzufügen
            data['updated_at'] = datetime.now()
            
            # JSON Serialisierung für komplexe Datentypen
            processed_data = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    processed_data[key] = json.dumps(value)
                else:
                    processed_data[key] = value
            
            set_clauses = []
            params = []
            
            for key, value in processed_data.items():
                set_clauses.append(f'{key} = %s')
                params.append(value)
            
            where_clauses = []
            for key, value in conditions.items():
                where_clauses.append(f'{key} = %s')
                params.append(value)
            
            query = f'UPDATE {table} SET {", ".join(set_clauses)} WHERE {" AND ".join(where_clauses)}'
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount > 0
                
        except Exception as e:
            logging.error(f"PostgreSQL Update fehlgeschlagen: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def delete(self, table: str, conditions: Dict) -> bool:
        try:
            where_clauses = []
            params = []
            
            for key, value in conditions.items():
                where_clauses.append(f'{key} = %s')
                params.append(value)
            
            query = f'DELETE FROM {table} WHERE {" AND ".join(where_clauses)}'
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount > 0
                
        except Exception as e:
            logging.error(f"PostgreSQL Delete fehlgeschlagen: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def create_table(self, table_name: str, schema: Dict) -> bool:
        try:
            columns = []
            for column_name, column_type in schema.items():
                columns.append(f'{column_name} {column_type}')
            
            query = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(columns)})'
            
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                return True
                
        except Exception as e:
            logging.error(f"PostgreSQL Create Table fehlgeschlagen: {e}")
            return False

    # Compatibility wrappers for abstract base class expectations
    def insert_record(self, table_name: str, data: Dict) -> Any:
        """Wrapper for RelationalDatabaseBackend.insert_record"""
        return self.insert(table_name, data)

    def update_record(self, table_name: str, record_id: Any, data: Dict) -> bool:
        """Wrapper for RelationalDatabaseBackend.update_record

        Assumes primary key column is named 'id'.
        """
        try:
            conditions = {'id': record_id}
            return self.update(table_name, data, conditions)
        except Exception as e:
            logging.error(f"PostgreSQL update_record failed: {e}")
            return False
    
    def get_table_schema(self, table_name: str) -> Dict:
        try:
            query = '''
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            '''
            
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (table_name,))
                columns = cursor.fetchall()
                
                schema = {}
                for column in columns:
                    schema[column['column_name']] = {
                        'type': column['data_type'],
                        'nullable': column['is_nullable'] == 'YES',
                        'default': column['column_default']
                    }
                
                return schema
                
        except Exception as e:
            logging.error(f"PostgreSQL Get Schema fehlgeschlagen: {e}")
            return {}
    
    def get_tables(self) -> List[str]:
        try:
            query = '''
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            '''
            
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                tables = cursor.fetchall()
                return [table[0] for table in tables]
                
        except Exception as e:
            logging.error(f"PostgreSQL Get Tables fehlgeschlagen: {e}")
            return []
    
    def create_index(self, table: str, columns: List[str], index_name: str = None) -> bool:
        """Erstelle Index auf Tabelle"""
        try:
            if not index_name:
                index_name = f"idx_{table}_{'_'.join(columns)}"
            
            columns_str = ', '.join(columns)
            query = f'CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({columns_str})'
            
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                return True
                
        except Exception as e:
            logging.error(f"PostgreSQL Create Index fehlgeschlagen: {e}")
            return False
    
    def full_text_search(self, table: str, search_column: str, search_term: str) -> List[Dict]:
        """Full-Text Search mit PostgreSQL"""
        try:
            query = f'''
                SELECT *, ts_rank(to_tsvector('german', {search_column}), query) AS rank
                FROM {table}, to_tsquery('german', %s) query
                WHERE to_tsvector('german', {search_column}) @@ query
                ORDER BY rank DESC
            '''
            
            return self.execute_query(query, (search_term,))
            
        except Exception as e:
            logging.error(f"PostgreSQL Full-Text Search fehlgeschlagen: {e}")
            return []


def get_backend_class():
    """Factory-Funktion für PostgreSQL Backend"""
    return PostgreSQLRelationalBackend

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_postgresql"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "e6d542d9764ebafb4f5eca8fe1f07ad3d40982dc55b76a6fcc2397b8e318bf4d"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
