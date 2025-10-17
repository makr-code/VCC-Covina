#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL adapter using psycopg (psycopg3) for relational full-CRUD.
Config keys:
- dsn or {host,port,user,password,database}
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple

import psycopg
from psycopg.rows import dict_row

from database.database_api_base import RelationalDatabaseBackend

logger = logging.getLogger(__name__)


class PostgreSQLRelationalBackend(RelationalDatabaseBackend):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        cfg = config or {}
        self.dsn = cfg.get('dsn') or cfg.get('connection_string')
        self._pool: Optional[psycopg.Connection] = None
        self._is_connected = False
    
    @property
    def conn(self):
        """SAGA Orchestrator compatibility: Expose _pool as conn"""
        return self._pool

    def connect(self) -> bool:
        try:
            # Connection timeout (5 seconds) - prevents long startup hangs
            connect_timeout = self.config.get('connect_timeout', 5)
            
            if self.dsn:
                self._pool = psycopg.connect(
                    self.dsn, 
                    row_factory=dict_row,
                    connect_timeout=connect_timeout
                )
            else:
                self._pool = psycopg.connect(
                    host=self.config.get('host', 'localhost'),
                    port=self.config.get('port', 5432),
                    user=self.config.get('user'),
                    password=self.config.get('password'),
                    dbname=self.config.get('database') or self.config.get('dbname'),
                    row_factory=dict_row,
                    connect_timeout=connect_timeout
                )
            self._is_connected = True
            logger.info('PostgreSQL connected')
            return True
        except Exception as exc:
            logger.error('PostgreSQL connect failed: %s', exc)
            self._pool = None
            self._is_connected = False
            return False

    def disconnect(self):
        try:
            if self._pool:
                self._pool.close()
            self._pool = None
            self._is_connected = False
        except Exception:
            pass

    def is_available(self) -> bool:
        return bool(self._is_connected and self._pool is not None)

    def get_backend_type(self) -> str:
        return 'postgresql'

    def execute_query(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        if not self._pool:
            logger.error('PostgreSQL: no connection')
            return []
        try:
            with self._pool.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                else:
                    # Return affected rows as convenience
                    return [{'affected_rows': cur.rowcount}]
        except Exception as exc:
            logger.exception('PostgreSQL query failed: %s', exc)
            return []

    # Convenience CRUD for simple tables
    def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        cols = []
        for name, ctype in schema.items():
            cols.append(f"{name} {ctype}")
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(cols)})"
        self.execute_query(sql)
        return True

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> Optional[Any]:
        keys = list(data.keys())
        cols = ','.join(keys)
        vals = ','.join([f'%s' for _ in keys])
        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({vals}) RETURNING id"
        params = tuple(data[k] for k in keys)
        rows = self.execute_query(sql, params)
        if rows:
            return rows[0].get('id')
        return None

    def get_record_by_id(self, table_name: str, record_id: Any) -> Optional[Dict[str, Any]]:
        sql = f"SELECT * FROM {table_name} WHERE id = %s"
        rows = self.execute_query(sql, (record_id,))
        return rows[0] if rows else None

    def update_record(self, table_name: str, record_id: Any, data: Dict[str, Any]) -> bool:
        if not data:
            return False
        set_parts = ', '.join([f"{k} = %s" for k in data.keys()])
        params = tuple(data[k] for k in data.keys()) + (record_id,)
        sql = f"UPDATE {table_name} SET {set_parts} WHERE id = %s"
        self.execute_query(sql, params)
        return True

    def delete_record(self, table_name: str, record_id: Any) -> bool:
        sql = f"DELETE FROM {table_name} WHERE id = %s"
        self.execute_query(sql, (record_id,))
        return True


def get_backend_class():
    return PostgreSQLRelationalBackend
