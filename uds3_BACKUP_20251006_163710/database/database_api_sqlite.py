#!/usr/bin/env python3
"""
SQLite Relational Database Backend

Implementiert die abstrakte `RelationalDatabaseBackend`-Schnittstelle für lokale
SQLite-Dateien. Ziel ist ein einfach nutzbarer Adapter, der von Migrationen und
Tests verwendet werden kann.
"""

import logging
import sqlite3
import os
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from database.database_api_base import RelationalDatabaseBackend

# UDS3 v3.0 Import mit Fallback (wie in anderen Adaptern)
try:
	from uds3.uds3_core import UnifiedDatabaseStrategy
	get_unified_database_strategy: Optional[callable] = UnifiedDatabaseStrategy
	UDS3_AVAILABLE = True
except Exception:
	UDS3_AVAILABLE = False
	get_unified_database_strategy = None

logger = logging.getLogger(__name__)


class SQLiteRelationalBackend(RelationalDatabaseBackend):
	"""SQLite-basierter Relational-Adapter.

	Konvention: Tabellen-Primary-Key heißt 'id' (TEXT). Die Implementierung ist
	robust gegen fehlende Pfade und erstellt erforderliche Verzeichnisse.
	"""

	def __init__(self, config: Dict = None):
		super().__init__(config)
		cfg = config or {}
		# Support legacy 'path' and newer 'database_path'
		self.db_path = cfg.get('database_path') or cfg.get('path') or './data/sqlite_relational.db'
		self.connection: Optional[sqlite3.Connection] = None
		# UDS3 strategy optional initialisieren
		try:
			if callable(get_unified_database_strategy):
				self.strategy = get_unified_database_strategy()
			else:
				self.strategy = None
		except Exception as exc:
			logger.warning(f"SQLite UDS3 strategy init failed: {exc}")
			self.strategy = None

		strategy_version = getattr(self.strategy, 'version', 'UDS3') if self.strategy else 'UDS3'
		logger.info(f"SQLite Relational Backend initialisiert mit Strategie {strategy_version}")

	def _backend_connect(self) -> bool:
		"""Low-level connect called by RelationalDatabaseBackend.connect()."""
		try:
			os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
			# sqlite3 connect
			self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
			self.connection.row_factory = sqlite3.Row
			# Enable foreign keys
			try:
				cur = self.connection.cursor()
				cur.execute('PRAGMA foreign_keys = ON')
				cur.close()
			except Exception:
				pass

			# Ensure base saga schema is not created here; migrations run separately.
			logger.info(f"SQLite verbunden: {self.db_path}")
			return True
		except Exception as e:
			logger.error(f"SQLite Verbindung fehlgeschlagen: {e}")
			self.connection = None
			return False

	def disconnect(self):
		if self.connection:
			try:
				self.connection.close()
			except Exception:
				pass
			self.connection = None

	def is_available(self) -> bool:
		try:
			if self.connection:
				cur = self.connection.cursor()
				cur.execute('SELECT 1')
				cur.close()
				return True
		except Exception:
			pass
		return False

	def get_backend_type(self) -> str:
		return 'SQLite'

	# ----------------
	# Required methods
	# ----------------
	def execute_query(self, query: str, params: Tuple = None) -> List[Dict]:
		"""Execute a SQL query and return rows as list of dicts.

		Non-SELECT statements return a dict with affected_rows.
		"""
		if not self.connection:
			logger.error('SQLite: no connection')
			return []
		try:
			cur = self.connection.cursor()
			try:
				if params:
					cur.execute(query, params)
				else:
					cur.execute(query)

				command = query.strip().split()[0].upper() if query else ''
				is_select_like = command in ('SELECT', 'PRAGMA', 'WITH')

				if is_select_like:
					rows = cur.fetchall()
					result = [dict(r) for r in rows]
					return result
				else:
					try:
						self.connection.commit()
					except Exception:
						pass
					return [{'affected_rows': cur.rowcount if hasattr(cur, 'rowcount') else -1}]
			finally:
				try:
					cur.close()
				except Exception:
					pass
		except Exception as e:
			logger.error(f"SQLite Query failed: {e}")
			return []

	def create_table(self, table_name: str, schema: Dict) -> bool:
		"""Create a table given a schema dict mapping column->type."""
		try:
			columns = []
			for name, coltype in schema.items():
				columns.append(f"{name} {coltype}")
			sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
			self.execute_query(sql)
			return True
		except Exception as e:
			logger.error(f"SQLite create_table failed: {e}")
			return False

	def insert_record(self, table_name: str, data: Dict) -> Any:
		"""Insert a record and return its id. Uses TEXT id by default."""
		try:
			if 'id' not in data:
				data['id'] = str(uuid.uuid4())

			keys = list(data.keys())
			placeholders = ','.join(['?'] * len(keys))
			cols = ','.join(keys)
			values = tuple(data[k] for k in keys)
			sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
			res = self.execute_query(sql, values)
			return data.get('id')
		except Exception as e:
			logger.error(f"SQLite insert_record failed: {e}")
			return None

	def update_record(self, table_name: str, record_id: Any, data: Dict) -> bool:
		"""Update a record by 'id' primary key."""
		try:
			if not data:
				return False
			set_parts = []
			params = []
			for k, v in data.items():
				set_parts.append(f"{k} = ?")
				params.append(v)
			params.append(record_id)
			sql = f"UPDATE {table_name} SET {', '.join(set_parts)} WHERE id = ?"
			res = self.execute_query(sql, tuple(params))
			# execute_query returns affected_rows for non-select
			if res and isinstance(res, list) and 'affected_rows' in res[0]:
				return res[0]['affected_rows'] != 0
			return True
		except Exception as e:
			logger.error(f"SQLite update_record failed: {e}")
			return False

	def insert(self, table_name: str, data: Dict) -> Any:
		"""Convenience wrapper used by saga orchestration logic.

		Delegates to :meth:`insert_record` while preventing side effects on the
		caller-provided dictionary.
		"""
		if not isinstance(data, dict):
			logger.error('SQLite insert expects dict payload, got %s', type(data))
			return None
		return self.insert_record(table_name, dict(data))

	# ----------------
	# Helper/Convenience
	# ----------------
	def select(self, table: str, conditions: Dict = None, order_by: str = None, limit: int = None) -> List[Dict]:
		try:
			sql = f"SELECT * FROM {table}"
			params = []
			if conditions:
				where = []
				for k, v in conditions.items():
					where.append(f"{k} = ?")
					params.append(v)
				sql += " WHERE " + " AND ".join(where)
			if order_by:
				sql += f" ORDER BY {order_by}"
			if limit:
				sql += f" LIMIT {int(limit)}"
			return self.execute_query(sql, tuple(params) if params else None)
		except Exception as e:
			logger.error(f"SQLite select failed: {e}")
			return []

	def delete(self, table: str, conditions: Dict) -> bool:
		try:
			where = []
			params = []
			for k, v in conditions.items():
				where.append(f"{k} = ?")
				params.append(v)
			sql = f"DELETE FROM {table} WHERE {' AND '.join(where)}"
			res = self.execute_query(sql, tuple(params))
			return True
		except Exception as e:
			logger.error(f"SQLite delete failed: {e}")
			return False

	def get_table_schema(self, table_name: str) -> Dict:
		try:
			rows = self.execute_query(f"PRAGMA table_info({table_name})")
			schema = {}
			for r in rows:
				schema[r.get('name')] = {
					'type': r.get('type'),
					'nullable': r.get('notnull') == 0,
					'default': r.get('dflt_value')
				}
			return schema
		except Exception as e:
			logger.error(f"SQLite get_table_schema failed: {e}")
			return {}

	def get_tables(self) -> List[str]:
		try:
			rows = self.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
			return [r.get('name') for r in rows]
		except Exception:
			return []

