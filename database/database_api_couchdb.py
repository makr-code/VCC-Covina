#!/usr/bin/env python3
"""
CouchDB adapter for the Database API.

Provides a lightweight HTTP-based adapter implementing a subset of the
expected DatabaseBackend/Relational-like interface used by the project.

Methods implemented: connect(), is_available(), execute_query() (simple
wrapper), create_database(), insert(), select(), update(), delete(),
get_tables(), get_backend_type(). Uses `requests` and falls back to socket
probe when requests is not available.
"""
import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

from database.database_api_base import DatabaseBackend

logger = logging.getLogger(__name__)


class CouchDBBackend(DatabaseBackend):
    """Simple CouchDB adapter using HTTP API.

    Config keys expected (in config dict):
      - host (str)
      - port (int)
      - username (optional)
      - password (optional)
      - protocol (http/https, optional)
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = int(config.get('port', 5984))
        self.username = config.get('username')
        self.password = config.get('password')
        self.protocol = config.get('protocol', 'http')
        self.base_url = f"{self.protocol}://{self.host}:{self.port}/"
        self.session = None

    def _auth(self):
        if self.username:
            return (self.username, self.password or '')
        return None

    def connect(self) -> bool:
        try:
            if REQUESTS_AVAILABLE:
                self.session = requests.Session()
                auth = self._auth()
                if auth:
                    self.session.auth = auth
                # simple heartbeat
                r = self.session.get(self.base_url, timeout=5)
                r.raise_for_status()
                logger.info(f"CouchDB connected: {self.base_url}")
                return True
            else:
                # Fall back to a TCP probe
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect((self.host, self.port))
                s.close()
                logger.info(f"CouchDB reachable via TCP: {self.host}:{self.port}")
                return True
        except Exception as e:
            logger.error(f"CouchDB connection failed: {e}")
            self.session = None
            return False

    def is_available(self) -> bool:
        try:
            if self.session and REQUESTS_AVAILABLE:
                r = self.session.get(self.base_url, timeout=3)
                return r.status_code == 200
            # if no session, try connect probe
            return self.connect()
        except Exception:
            return False

    def get_backend_type(self) -> str:
        return "CouchDB"

    # Minimal compatibility: list of databases as 'tables'
    def get_tables(self) -> List[str]:
        try:
            if not REQUESTS_AVAILABLE:
                return []
            r = self.session.get(urljoin(self.base_url, '_all_dbs'), timeout=5)
            r.raise_for_status()
            return list(r.json())
        except Exception as e:
            logger.debug(f"CouchDB get_tables failed: {e}")
            return []

    def create_database(self, db_name: str) -> bool:
        try:
            if not REQUESTS_AVAILABLE:
                logger.error('requests not available for CouchDB operations')
                return False
            url = urljoin(self.base_url, db_name)
            r = self.session.put(url, timeout=5)
            # 201 Created or 412 if already exists
            if r.status_code in (201, 202):
                return True
            if r.status_code == 412:
                return True
            logger.error(f"CouchDB create_database failed: {r.status_code} {r.text}")
            return False
        except Exception as e:
            logger.error(f"CouchDB create_database exception: {e}")
            return False

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Generic SQL-like execution is not supported; provide a minimal shim.

        The function accepts a few custom commands for convenience:
          - 'LIST_DBS' -> returns list of DBs
        For other inputs it returns empty list.
        """
        try:
            q = query.strip().upper()
            if q == 'LIST_DBS':
                return [{'db': d} for d in self.get_tables()]
            return []
        except Exception as e:
            logger.debug(f"CouchDB execute_query failed: {e}")
            return []

    def insert(self, db_name: str, data: Dict) -> Optional[str]:
        """Insert a document into a CouchDB database (db_name acts like table).

        Returns document id on success.
        """
        try:
            if 'id' in data:
                doc_id = data.get('id')
            else:
                doc_id = str(uuid.uuid4())
                data['id'] = doc_id

            # CouchDB expects JSON doc without 'id' field named _id
            payload = dict(data)
            payload['_id'] = payload.pop('id')

            url = urljoin(self.base_url, f"{db_name}/{payload['_id']}")
            r = self.session.put(url, json=payload, timeout=5)
            if r.status_code in (201, 202):
                return payload['_id']
            # conflict -> already exists
            if r.status_code == 409:
                logger.debug('CouchDB insert conflict - document exists')
                return payload['_id']
            logger.error(f"CouchDB insert failed: {r.status_code} {r.text}")
            return None
        except Exception as e:
            logger.error(f"CouchDB insert exception: {e}")
            return None

    def select(self, db_name: str, conditions: Dict = None, order_by: str = None, limit: int = None) -> List[Dict]:
        """Simple select: fetch all docs or get by id when conditions contains 'id'."""
        try:
            if conditions and 'id' in conditions:
                doc_id = conditions['id']
                url = urljoin(self.base_url, f"{db_name}/{doc_id}")
                r = self.session.get(url, timeout=5)
                if r.status_code == 200:
                    doc = r.json()
                    # Convert _id back to id
                    doc['id'] = doc.get('_id')
                    return [doc]
                return []

            # else: _all_docs with include_docs
            url = urljoin(self.base_url, f"{db_name}/_all_docs?include_docs=true")
            r = self.session.get(url, timeout=10)
            if r.status_code != 200:
                return []
            payload = r.json()
            rows = payload.get('rows', [])
            docs = []
            for row in rows:
                doc = row.get('doc')
                if doc:
                    doc['id'] = doc.get('_id')
                    docs.append(doc)
            if limit:
                return docs[:limit]
            return docs
        except Exception as e:
            logger.error(f"CouchDB select failed: {e}")
            return []

    def update(self, db_name: str, data: Dict, conditions: Dict) -> bool:
        """Update document: requires id in conditions or data."""
        try:
            doc_id = conditions.get('id') if conditions else data.get('id')
            if not doc_id:
                logger.error('CouchDB update requires id')
                return False
            # fetch current _rev
            url = urljoin(self.base_url, f"{db_name}/{doc_id}")
            r = self.session.get(url, timeout=5)
            if r.status_code != 200:
                logger.error(f"CouchDB update fetch failed: {r.status_code}")
                return False
            doc = r.json()
            rev = doc.get('_rev')
            payload = dict(data)
            payload['_id'] = doc.get('_id')
            if rev:
                payload['_rev'] = rev
            # ensure _id/_rev present
            put_url = urljoin(self.base_url, f"{db_name}/{payload['_id']}")
            r2 = self.session.put(put_url, json=payload, timeout=5)
            return r2.status_code in (201, 202)
        except Exception as e:
            logger.error(f"CouchDB update failed: {e}")
            return False

    def delete(self, db_name: str, conditions: Dict) -> bool:
        try:
            doc_id = conditions.get('id')
            if not doc_id:
                logger.error('CouchDB delete requires id')
                return False
            # fetch rev
            url = urljoin(self.base_url, f"{db_name}/{doc_id}")
            r = self.session.get(url, timeout=5)
            if r.status_code != 200:
                logger.error(f"CouchDB delete fetch failed: {r.status_code}")
                return False
            rev = r.json().get('_rev')
            if not rev:
                logger.error('CouchDB delete: could not determine _rev')
                return False
            del_url = urljoin(self.base_url, f"{db_name}/{doc_id}?rev={rev}")
            r2 = self.session.delete(del_url, timeout=5)
            return r2.status_code in (200, 202)
        except Exception as e:
            logger.error(f"CouchDB delete failed: {e}")
            return False

    def disconnect(self):
        """Close HTTP session if open."""
        try:
            if self.session:
                try:
                    self.session.close()
                except Exception:
                    pass
            self.session = None
        except Exception:
            self.session = None
        return True

