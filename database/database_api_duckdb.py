#!/usr/bin/env python3
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

"""
DuckDB Analytics Database Backend
=================================

Hochperformante OLAP-Datenbank für Analytics und Reporting
- Ultra-schnelle SQL-Queries
- Columnar Storage
- In-Memory + Persistent Storage
- Pandas/Arrow Integration
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from database.database_api_base import RelationalDatabaseBackend

# UDS3 v3.0 Import mit Fallback
try:
    from uds3_core import UnifiedDatabaseStrategy
    get_unified_database_strategy = UnifiedDatabaseStrategy
    UDS3_AVAILABLE = True
except ImportError:
    UDS3_AVAILABLE = False
    get_unified_database_strategy = None

# DuckDB Import mit Fallback
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

logger = logging.getLogger(__name__)


class DuckDBAnalyticsBackend(RelationalDatabaseBackend):
    """DuckDB Backend für Analytics und OLAP-Operationen mit UDS3-Integration"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.connection = None
        self.database_path = config.get('database_path', ':memory:')
        self.read_only = config.get('read_only', False)
        self.threads = config.get('threads', 4)
        self.memory_limit = config.get('memory_limit', '1GB')
        try:
            if callable(get_unified_database_strategy):
                self.strategy = get_unified_database_strategy()
            else:
                self.strategy = None
        except Exception as exc:
            logger.warning(f"UDS3 strategy initialization failed for DuckDB: {exc}")
            self.strategy = None

        strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
        logger.info(f"DuckDB Analytics Backend initialisiert mit Strategie {strategy_version}")
    
    def _backend_connect(self) -> bool:
        """Verbindung zu DuckDB herstellen"""
        if not DUCKDB_AVAILABLE:
            logger.error("DuckDB Python client nicht installiert")
            return False
            
        try:
            # DuckDB-Verbindung mit Konfiguration
            self.connection = duckdb.connect(
                database=self.database_path,
                read_only=self.read_only
            )
            
            # Performance-Konfiguration
            self.connection.execute(f"SET threads TO {self.threads}")
            self.connection.execute(f"SET memory_limit = '{self.memory_limit}'")
            
            # Erweiterte Features aktivieren
            self.connection.execute("INSTALL 'json'")
            self.connection.execute("LOAD 'json'")
            
            # Test-Query
            result = self.connection.execute("SELECT 'DuckDB Connected' as status").fetchone()
            logger.info(f"DuckDB verbunden: {result[0]} ({self.get_backend_type()})")
            return True
            
        except Exception as e:
            logger.error(f"DuckDB Verbindung fehlgeschlagen: {e}")
            return False
    
    def disconnect(self):
        """Verbindung schließen"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def is_available(self) -> bool:
        """Prüft ob Backend verfügbar ist"""
        try:
            if self.connection:
                self.connection.execute("SELECT 1").fetchone()
                return True
        except:
            pass
        return False
    
    def get_backend_type(self) -> str:
        """Backend-Typ für Logging"""
        mode = "In-Memory" if self.database_path == ":memory:" else "Persistent"
        return f"DuckDB Analytics ({mode})"
    
    def create_table(self, table_name: str, schema: Dict[str, str], 
                     indexes: List[str] = None) -> bool:
        """Tabelle erstellen mit DuckDB-optimiertem Schema"""
        try:
            # Schema zu DuckDB SQL konvertieren
            columns = []
            for col_name, col_type in schema.items():
                # DuckDB Typen-Mapping
                duck_type = self._map_to_duckdb_type(col_type)
                columns.append(f"{col_name} {duck_type}")
            
            columns_sql = ", ".join(columns)
            
            # Tabelle erstellen
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})"
            self.connection.execute(create_sql)
            
            # Indizes erstellen (DuckDB hat automatische Optimierung)
            if indexes:
                for index in indexes:
                    try:
                        index_sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{index} ON {table_name} ({index})"
                        self.connection.execute(index_sql)
                    except Exception as e:
                        logger.warning(f"Index {index} für {table_name} nicht erstellt: {e}")
            
            logger.debug(f"DuckDB Tabelle erstellt: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"DuckDB Tabelle erstellen fehlgeschlagen: {e}")
            return False
    
    def _map_to_duckdb_type(self, generic_type: str) -> str:
        """Mappt generische Typen zu DuckDB-Typen"""
        type_mapping = {
            'INTEGER': 'INTEGER',
            'TEXT': 'VARCHAR',
            'REAL': 'DOUBLE',
            'BLOB': 'BLOB',
            'BOOLEAN': 'BOOLEAN',
            'DATETIME': 'TIMESTAMP',
            'JSON': 'JSON',
            'DECIMAL': 'DECIMAL(18,2)',
            'BIGINT': 'BIGINT',
            'UUID': 'UUID'
        }
        return type_mapping.get(generic_type.upper(), 'VARCHAR')
    
    def insert_data(self, table_name: str, data: Union[Dict, List[Dict]]) -> bool:
        """Daten einfügen mit Batch-Optimierung"""
        try:
            if isinstance(data, dict):
                data = [data]
            
            if not data:
                return True
            
            # Spaltennamen aus erstem Datensatz
            columns = list(data[0].keys())
            placeholders = ["?" for _ in columns]
            
            # Batch-Insert für Performance
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            # Daten vorbereiten
            values_list = []
            for row in data:
                values = [self._prepare_value(row.get(col)) for col in columns]
                values_list.append(values)
            
            # Batch-Execute
            self.connection.executemany(insert_sql, values_list)
            
            logger.debug(f"DuckDB Batch-Insert: {len(data)} Zeilen in {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"DuckDB Insert fehlgeschlagen: {e}")
            return False
    
    def _prepare_value(self, value):
        """Wert für DuckDB vorbereiten"""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value
    
    def query_data(self, query: str, params: tuple = None) -> List[Dict]:
        """SQL-Query ausführen"""
        try:
            if params:
                result = self.connection.execute(query, params)
            else:
                result = self.connection.execute(query)
            
            # Spaltennamen abrufen
            columns = [desc[0] for desc in result.description]
            
            # Ergebnisse zu Dict-Liste konvertieren
            rows = []
            for row in result.fetchall():
                row_dict = dict(zip(columns, row))
                rows.append(row_dict)
            
            return rows
            
        except Exception as e:
            logger.error(f"DuckDB Query fehlgeschlagen: {e}")
            return []
    
    def update_data(self, table_name: str, data: Dict, 
                   condition: str, params: tuple = None) -> bool:
        """Daten aktualisieren"""
        try:
            # SET-Klausel aufbauen
            set_parts = []
            values = []
            for key, value in data.items():
                set_parts.append(f"{key} = ?")
                values.append(self._prepare_value(value))
            
            set_clause = ", ".join(set_parts)
            
            # Update-SQL
            update_sql = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
            
            # Parameter kombinieren
            if params:
                values.extend(params)
            
            self.connection.execute(update_sql, values)
            return True
            
        except Exception as e:
            logger.error(f"DuckDB Update fehlgeschlagen: {e}")
            return False
    
    def delete_data(self, table_name: str, condition: str, params: tuple = None) -> bool:
        """Daten löschen"""
        try:
            delete_sql = f"DELETE FROM {table_name} WHERE {condition}"
            self.connection.execute(delete_sql, params or ())
            return True
            
        except Exception as e:
            logger.error(f"DuckDB Delete fehlgeschlagen: {e}")
            return False
    
    def execute_raw_query(self, query: str, params: tuple = None) -> Any:
        """Raw SQL-Query ausführen"""
        try:
            if params:
                return self.connection.execute(query, params)
            else:
                return self.connection.execute(query)
        except Exception as e:
            logger.error(f"DuckDB Raw Query fehlgeschlagen: {e}")
            return None
    
    def get_table_info(self, table_name: str) -> Dict:
        """Tabellen-Informationen abrufen"""
        try:
            # Schema abrufen
            schema_query = f"DESCRIBE {table_name}"
            schema_result = self.connection.execute(schema_query).fetchall()
            
            # Zeilenanzahl
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count_result = self.connection.execute(count_query).fetchone()
            
            return {
                'table_name': table_name,
                'schema': schema_result,
                'row_count': count_result[0] if count_result else 0,
                'backend_type': self.get_backend_type()
            }
            
        except Exception as e:
            logger.error(f"DuckDB Tabellen-Info fehlgeschlagen: {e}")
            return {}
    
    def analytics_query(self, query: str, params: tuple = None) -> Dict:
        """Spezialisierte Analytics-Query mit Performance-Metriken"""
        try:
            import time
            start_time = time.time()
            
            # Query ausführen
            result = self.query_data(query, params)
            
            execution_time = time.time() - start_time
            
            return {
                'data': result,
                'execution_time_ms': round(execution_time * 1000, 2),
                'row_count': len(result),
                'backend': 'DuckDB Analytics'
            }
            
        except Exception as e:
            logger.error(f"DuckDB Analytics Query fehlgeschlagen: {e}")
            return {'data': [], 'error': str(e)}
    
    def export_to_parquet(self, table_name: str, file_path: str) -> bool:
        """Tabelle zu Parquet exportieren"""
        try:
            export_sql = f"COPY {table_name} TO '{file_path}' (FORMAT 'parquet')"
            self.connection.execute(export_sql)
            logger.info(f"DuckDB Export: {table_name} -> {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"DuckDB Parquet Export fehlgeschlagen: {e}")
            return False
    
    def import_from_parquet(self, table_name: str, file_path: str) -> bool:
        """Parquet-Datei importieren"""
        try:
            import_sql = f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{file_path}')"
            self.connection.execute(import_sql)
            logger.info(f"DuckDB Import: {file_path} -> {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"DuckDB Parquet Import fehlgeschlagen: {e}")
            return False


def get_backend_class():
    """Factory-Funktion für DuckDB Backend"""
    return DuckDBAnalyticsBackend if DUCKDB_AVAILABLE else None


"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_duckdb"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
module_file_key = "44ca905beba1e42ff839f7c3239dbeef29f78ce05f86eae278dca895b089df2e"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===