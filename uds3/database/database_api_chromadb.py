#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB adapter using the official `chromadb` client.
Provides vector store operations used by the vector backend API.

Config keys:
- impl: optional 'chromadb' implementation settings
- collection: default collection name
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

import chromadb
from chromadb.config import Settings

from database.database_api_base import VectorDatabaseBackend

logger = logging.getLogger(__name__)


class ChromaVectorBackend(VectorDatabaseBackend):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        cfg = config or {}
        self.impl_settings = cfg.get('impl', {})
        # allow passing Settings via config
        try:
            settings = Settings(**self.impl_settings) if isinstance(self.impl_settings, dict) else Settings()
        except Exception:
            settings = Settings()
        self.client = chromadb.Client(settings)
        self.collection_name = cfg.get('collection', 'default')
        self._collection = None
        self._is_connected = False

    def connect(self) -> bool:
        try:
            # create or get collection
            try:
                self._collection = self.client.get_collection(self.collection_name)
            except Exception:
                self._collection = self.client.create_collection(self.collection_name)
            self._is_connected = True
            logger.info('ChromaDB connected collection=%s', self.collection_name)
            return True
        except Exception as exc:
            logger.exception('ChromaDB connect failed: %s', exc)
            self._is_connected = False
            self._collection = None
            return False

    def disconnect(self):
        try:
            # chromadb client doesn't have explicit close in many implementations
            self.client = None
            self._collection = None
            self._is_connected = False
        except Exception:
            pass

    def is_available(self) -> bool:
        """
        Check if ChromaDB backend is available.
        Backend is available if client is connected, regardless of which collection is open.
        Individual operations will get_or_create_collection as needed.
        """
        return bool(self._is_connected and self.client is not None)

    def get_backend_type(self) -> str:
        return 'chromadb'

    # Existing, higher-level helpers
    def batch_add_documents(self, collection_name: str, documents: List[str], metadatas: List[Dict], ids: List[str]) -> bool:
        try:
            col = self.client.get_or_create_collection(collection_name)
            col.add(documents=documents, metadatas=metadatas, ids=ids)
            return True
        except Exception as exc:
            logger.exception('Chroma batch add failed: %s', exc)
            return False

    def batch_add_vector(self, vector_id: str, vector: List[float], metadata: Dict = None, collection_name: str = None) -> bool:
        try:
            col = self.client.get_or_create_collection(collection_name or self.collection_name)
            col.add(ids=[vector_id], embeddings=[vector], metadatas=[metadata or {}], documents=[metadata.get('text') if metadata else None])
            return True
        except Exception as exc:
            logger.exception('Chroma add vector failed: %s', exc)
            return False

    def query_vectors(self, vector: List[float], top_k: int = 10, collection_name: str = None) -> List[Dict[str, Any]]:
        try:
            col = self.client.get_or_create_collection(collection_name or self.collection_name)
            res = col.query(query_embeddings=[vector], n_results=top_k)
            # Normalize results
            out = []
            ids = res.get('ids') or []
            distances = res.get('distances') or []
            metadatas = res.get('metadatas') or []
            documents = res.get('documents') or []
            for i, id_ in enumerate(ids[0] if ids and isinstance(ids[0], list) else ids):
                out.append({
                    'id': id_,
                    'distance': (distances[0][i] if distances and isinstance(distances[0], list) else None),
                    'metadata': (metadatas[0][i] if metadatas and isinstance(metadatas[0], list) else None),
                    'document': (documents[0][i] if documents and isinstance(documents[0], list) else None),
                })
            return out
        except Exception as exc:
            logger.exception('Chroma query failed: %s', exc)
            return []

    def delete_vectors(self, ids: List[str], collection_name: str = None) -> bool:
        try:
            col = self.client.get_or_create_collection(collection_name or self.collection_name)
            col.delete(ids=ids)
            return True
        except Exception as exc:
            logger.exception('Chroma delete failed: %s', exc)
            return False

    def get_collections(self) -> List[str]:
        try:
            return [c.name for c in self.client.list_collections()]
        except Exception:
            return []

    # ---- Methods required by VectorDatabaseBackend (wrappers/adapters) ----
    def create_collection(self, name: str, metadata: Dict = None) -> bool:
        try:
            try:
                self.client.get_collection(name)
            except Exception:
                self.client.create_collection(name)
            return True
        except Exception as exc:
            logger.exception('Chroma create_collection failed: %s', exc)
            return False

    def get_collection(self, name: str):
        try:
            return self.client.get_collection(name)
        except Exception:
            return None

    def list_collections(self) -> List[str]:
        return self.get_collections()

    def add_documents(self, collection_name: str, documents: List[str], metadatas: List[Dict], ids: List[str]) -> bool:
        return self.batch_add_documents(collection_name, documents, metadatas, ids)

    def add_vector(self, vector_id: str, vector: List[float], metadata: Dict = None, collection_name: str = None) -> bool:
        return self.batch_add_vector(vector_id, vector, metadata=metadata, collection_name=collection_name)

    def search_similar(self, collection_name: str, query: str, n_results: int = 5) -> List[Dict]:
        """Attempt a text-based similarity search. If the client supports `query_texts` use it,
        otherwise return an empty list (the method exists to satisfy the abstract base)."""
        try:
            col = self.client.get_or_create_collection(collection_name or self.collection_name)
            # many chroma versions support `query_texts` for text -> embedding search
            try:
                res = col.query(query_texts=[query], n_results=n_results)
            except Exception:
                # fallback: try plain query with the string as 'query' field (best-effort)
                res = col.query(query=[query], n_results=n_results)
            ids = res.get('ids') or []
            distances = res.get('distances') or []
            metadatas = res.get('metadatas') or []
            documents = res.get('documents') or []
            out = []
            for i, id_ in enumerate(ids[0] if ids and isinstance(ids[0], list) else ids):
                out.append({
                    'id': id_,
                    'distance': (distances[0][i] if distances and isinstance(distances[0], list) else None),
                    'metadata': (metadatas[0][i] if metadatas and isinstance(metadatas[0], list) else None),
                    'document': (documents[0][i] if documents and isinstance(documents[0], list) else None),
                })
            return out
        except Exception as exc:
            logger.exception('Chroma search_similar failed: %s', exc)
            return []

    def search_vectors(self, query_vector: List[float], top_k: int = 10, collection_name: str = None) -> List[Dict]:
        return self.query_vectors(query_vector, top_k, collection_name or self.collection_name)


def get_backend_class():
    return ChromaVectorBackend
