#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CouchDB adapter - lightweight Document DB adapter using `couchdb` package.
Provides full CRUD: create_document, get_document, update_document, delete_document, query.

Config keys:
- url: http://user:pass@host:5984
- db: database name
"""
from __future__ import annotations

import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import couchdb  # pip install CouchDB

from database.database_api_base import DatabaseBackend

logger = logging.getLogger(__name__)


class CouchDBAdapter(DatabaseBackend):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        cfg = config or {}
        
        # Build URL from components if not provided directly
        if 'url' in cfg:
            self.url = cfg['url']
        else:
            # Build from host, port, username, password
            host = cfg.get('host', 'localhost')
            port = cfg.get('port', 5984)
            username = cfg.get('username', '')
            password = cfg.get('password', '')
            protocol = cfg.get('protocol', 'http')
            
            if username and password:
                self.url = f"{protocol}://{username}:{password}@{host}:{port}"
            else:
                self.url = f"{protocol}://{host}:{port}"
        
        self.db_name = cfg.get('db', cfg.get('database'))
        self.server: Optional[couchdb.Server] = None
        self.db: Optional[couchdb.Database] = None
        self._is_connected = False

    def connect(self) -> bool:
        try:
            self.server = couchdb.Server(self.url)
            # Ensure DB exists
            if self.db_name not in self.server:
                self.server.create(self.db_name)
            self.db = self.server[self.db_name]
            self._is_connected = True
            logger.info('CouchDB connected %s/%s', self.url, self.db_name)
            return True
        except Exception as exc:
            logger.exception('CouchDB connect failed: %s', exc)
            self.server = None
            self.db = None
            self._is_connected = False
            return False

    def disconnect(self):
        self.server = None
        self.db = None
        self._is_connected = False

    def is_available(self) -> bool:
        return bool(self._is_connected and self.db is not None)

    def get_backend_type(self) -> str:
        return 'couchdb'

    # CRUD
    def create_document(self, doc: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        if not self.db:
            raise RuntimeError('CouchDB not connected')
        if doc_id:
            self.db[doc_id] = doc
            return doc_id
        else:
            docid, _rev = self.db.save(doc)
            return docid

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if not self.db:
            raise RuntimeError('CouchDB not connected')
        try:
            return dict(self.db[doc_id])
        except Exception:
            return None

    def update_document(self, doc_id: str, changes: Dict[str, Any]) -> bool:
        if not self.db:
            raise RuntimeError('CouchDB not connected')
        try:
            doc = self.db[doc_id]
            for k, v in changes.items():
                doc[k] = v
            self.db.save(doc)
            return True
        except Exception as exc:
            logger.exception('CouchDB update failed: %s', exc)
            return False

    def delete_document(self, doc_id: str) -> bool:
        if not self.db:
            raise RuntimeError('CouchDB not connected')
        try:
            doc = self.db[doc_id]
            self.db.delete(doc)
            return True
        except Exception as exc:
            logger.exception('CouchDB delete failed: %s', exc)
            return False

    def query(self, map_fun: str = None, reduce_fun: str = None, **opts) -> List[Dict[str, Any]]:
        """Run a temporary view query (map/reduce) - simplistic helper."""
        if not self.db:
            raise RuntimeError('CouchDB not connected')
        try:
            # Temporary views are discouraged; expect users to define design docs.
            result = []
            if map_fun:
                for row in self.db.query(map_fun, reduce=bool(reduce_fun), **opts):
                    result.append(dict(row))
            return result
        except Exception as exc:
            logger.exception('CouchDB query failed: %s', exc)
            return []

    # File Storage Interface (for saga_crud compatibility)
    def store_asset(
        self,
        source_path: Optional[str] = None,
        data: Optional[bytes] = None,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a file asset in CouchDB as an attachment.
        Returns dict with asset_id, file_storage_id, and metadata.
        """
        if not self.db:
            raise RuntimeError('CouchDB not connected')
        
        try:
            # Generate unique asset ID
            import uuid
            asset_id = str(uuid.uuid4())
            
            # Read data from source_path if not provided
            if data is None and source_path:
                with open(source_path, 'rb') as f:
                    data = f.read()
            
            if data is None:
                raise ValueError("Either 'data' or 'source_path' must be provided")
            
            # Determine filename
            if not filename:
                if source_path:
                    filename = str(Path(source_path).name)
                else:
                    filename = 'document.bin'
            
            # Create document with metadata
            doc_data = {
                '_id': asset_id,
                'filename': filename,
                'metadata': metadata or {},
                'created_at': str(datetime.datetime.now())
            }
            
            # Save document first
            self.db[asset_id] = doc_data
            
            # Attach file data
            self.db.put_attachment(
                self.db[asset_id],
                data,
                filename=filename,
                content_type='application/octet-stream'
            )
            
            logger.info(f'Stored asset {asset_id} with filename {filename}')
            
            return {
                'success': True,
                'asset_id': asset_id,
                'file_storage_id': asset_id,
                'filename': filename,
                'size': len(data),
                'metadata': metadata
            }
            
        except Exception as exc:
            logger.exception(f'CouchDB store_asset failed: {exc}')
            raise RuntimeError(f'Failed to store asset: {exc}')

    def delete_asset(self, asset_id: str) -> bool:
        """
        Delete a file asset from CouchDB.
        Compatible with saga_crud file_delete().
        """
        return self.delete_document(asset_id)


def get_backend_class():
    return CouchDBAdapter
