#!/usr/bin/env python3
"""Lightweight HTTP-only ChromaDB remote adapter.

This implements a minimal VectorDatabaseBackend that talks to a remote ChromaDB
server via its HTTP API (no chromadb python package required). It focuses on
connectivity, listing/creating collections, adding documents (with optional
embeddings) and querying.
"""

import logging
try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    requests = None
    _HAS_REQUESTS = False
    # lightweight requests-like shim using urllib to avoid hard dependency
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
    import json as _json

    class _RequestsShimResponse:
        def __init__(self, code, content, headers=None):
            self.status_code = code
            self.text = content
            self._content = content
            self.headers = headers or {}

        def json(self):
            try:
                return _json.loads(self._content) if self._content else {}
            except Exception:
                return {}

        def raise_for_status(self):
            if 400 <= int(self.status_code):
                raise _urllib_error.HTTPError(None, int(self.status_code), 'HTTP error', None, None)

    class _RequestsShim:
        def __init__(self):
            self.auth = None

        def _do(self, method, url, json=None, timeout=5):
            data = None
            headers = {'Content-Type': 'application/json'} if json is not None else {}
            if json is not None:
                data = _json.dumps(json).encode('utf-8')
            req = _urllib_request.Request(url, data=data, headers=headers, method=method)
            try:
                with _urllib_request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    charset = resp.headers.get_content_charset() or 'utf-8'
                    text = raw.decode(charset) if raw else ''
                    return _RequestsShimResponse(resp.getcode(), text, resp.headers)
            except _urllib_error.HTTPError as e:
                # create response-like object with error code and body
                try:
                    body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
                except Exception:
                    body = ''
                r = _RequestsShimResponse(e.code if hasattr(e, 'code') else 500, body)
                # raise when caller calls raise_for_status
                return r

        def get(self, url, timeout=5):
            return self._do('GET', url, timeout=timeout)

        def post(self, url, json=None, timeout=5):
            return self._do('POST', url, json=json, timeout=timeout)

        def close(self):
            return None
from typing import Dict, List, Optional, Any
from database.database_api_base import VectorDatabaseBackend

logger = logging.getLogger(__name__)


class _RemoteCollection:
    def __init__(self, backend, name: str):
        self._backend = backend
        self.name = name

    def add(self, documents: List[str] = None, metadatas: List[Dict] = None,
            ids: List[str] = None, embeddings: List[List[float]] = None):
        url = f"{self._backend.server_url.rstrip('/')}/collections/{self.name}/add"
        payload: Dict[str, Any] = {}
        if documents is not None:
            payload['documents'] = documents
        if metadatas is not None:
            payload['metadatas'] = metadatas
        if ids is not None:
            payload['ids'] = ids
        if embeddings is not None:
            payload['embeddings'] = embeddings
        resp = requests.post(url, json=payload, timeout=self._backend.timeout)
        resp.raise_for_status()
        return resp.json()

    def query(self, query_texts: List[str] = None, query_embeddings: List[List[float]] = None,
              n_results: int = 5):
        url = f"{self._backend.server_url.rstrip('/')}/collections/{self.name}/query"
        payload: Dict[str, Any] = {'n_results': n_results}
        if query_texts is not None:
            payload['query_texts'] = query_texts
        if query_embeddings is not None:
            payload['query_embeddings'] = query_embeddings
        resp = requests.post(url, json=payload, timeout=self._backend.timeout)
        resp.raise_for_status()
        return resp.json()


class ChromaHTTPVectorBackend(VectorDatabaseBackend):
    """Remote HTTP ChromaDB adapter using requests."""

    def __init__(self, config: Dict):
        super().__init__(config)
        host = config.get('host', '127.0.0.1')
        port = config.get('port', 8000)
        server_url = config.get('server_url') or f"http://{host}:{port}"
        self.server_url = server_url
        self.timeout = float(config.get('timeout', 5.0))
        # use requests if available, otherwise fallback to shim
        if _HAS_REQUESTS:
            self.session = requests.Session()
        else:
            self.session = _RequestsShim()
        # optional auth (only applied if using requests.Session())
        auth = config.get('auth')
        if auth and _HAS_REQUESTS:
            if isinstance(auth, (list, tuple)) and len(auth) == 2:
                self.session.auth = tuple(auth)
        logger.info(f"ChromaHTTPVectorBackend configured server_url={self.server_url}")

    def _backend_connect(self) -> bool:
        try:
            # GET /health or /collections as heartbeat
            health_url = self.server_url.rstrip('/') + '/health'
            try:
                r = self.session.get(health_url, timeout=self.timeout)
                if r.status_code == 200:
                    return True
            except Exception:
                # fallback to /collections
                r = self.session.get(self.server_url.rstrip('/') + '/collections', timeout=self.timeout)
                if r.status_code == 200:
                    return True
            return False
        except Exception as e:
            logger.error(f"ChromaHTTP connect failed: {e}")
            return False

    # Compatibility shim for base API: connect() is expected by manager
    def connect(self) -> bool:
        """Connects to the remote Chroma HTTP server. Returns True on success."""
        try:
            ok = self._backend_connect()
            return bool(ok)
        except Exception as e:
            logger.error(f"ChromaHTTP connect() failed: {e}")
            return False

    def disconnect(self):
        try:
            self.session.close()
        except Exception:
            pass

    def is_available(self) -> bool:
        try:
            return self._backend_connect()
        except Exception:
            return False

    def get_backend_type(self) -> str:
        return 'ChromaDB (http)'

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return lightweight stats for manager tests."""
        try:
            cols = self.list_collections()
            return {'collection_count': len(cols), 'collections': cols}
        except Exception:
            return {'collection_count': 0, 'collections': []}

    def status(self) -> Dict[str, Any]:
        return {'type': self.get_backend_type(), 'available': self.is_available()}

    def create_collection(self, name: str, metadata: Dict = None) -> bool:
        try:
            url = f"{self.server_url.rstrip('/')}/collections"
            payload = {'name': name}
            if metadata:
                payload['metadata'] = metadata
            r = self.session.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"ChromaHTTP create_collection failed: {e}")
            return False

    def get_collection(self, name: str):
        # return a lightweight collection wrapper
        return _RemoteCollection(self, name)

    def list_collections(self) -> List[str]:
        try:
            url = f"{self.server_url.rstrip('/')}/collections"
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            # data may be a list of collections or structured; try common shapes
            if isinstance(data, list):
                # list of collection names or objects
                if all(isinstance(x, str) for x in data):
                    return data
                names = []
                for entry in data:
                    if isinstance(entry, dict) and 'name' in entry:
                        names.append(entry['name'])
                return names
            elif isinstance(data, dict) and 'collections' in data:
                return [c.get('name') for c in data.get('collections', []) if isinstance(c, dict)]
            return []
        except Exception as e:
            logger.error(f"ChromaHTTP list_collections failed: {e}")
            return []

    def add_documents(self, collection_name: str, documents: List[str], metadatas: List[Dict], ids: List[str]) -> bool:
        try:
            coll = self.get_collection(collection_name)
            coll.add(documents=documents, metadatas=metadatas, ids=ids)
            return True
        except Exception as e:
            logger.error(f"ChromaHTTP add_documents failed: {e}")
            return False

    def add_vector(self, vector_id: str, vector: List[float], metadata: Dict = None, collection_name: str = None) -> bool:
        """Add a single vector entry to a collection."""
        try:
            if collection_name is None:
                logger.error("add_vector requires a collection_name")
                return False
            coll = self.get_collection(collection_name)
            # use embeddings field
            coll.add(documents=None, metadatas=[metadata] if metadata is not None else [None], ids=[vector_id], embeddings=[vector])
            return True
        except Exception as e:
            logger.error(f"ChromaHTTP add_vector failed: {e}")
            return False

    def search_similar(self, collection_name: str, query: str, n_results: int = 5) -> List[Dict]:
        try:
            coll = self.get_collection(collection_name)
            res = coll.query(query_texts=[query], n_results=n_results)
            # Expect result shape similar to chroma: {'ids': [[...]], 'documents': [[...]], 'metadatas': [[...]], 'distances': [[...]]}
            out = []
            ids = res.get('ids', [[]])[0] if isinstance(res.get('ids'), list) else []
            docs = res.get('documents', [[]])[0] if isinstance(res.get('documents'), list) else []
            metadatas = res.get('metadatas', [[]])[0] if isinstance(res.get('metadatas'), list) else []
            distances = res.get('distances', [[]])[0] if isinstance(res.get('distances'), list) else []
            for i, _id in enumerate(ids):
                out.append({
                    'id': _id,
                    'document': docs[i] if i < len(docs) else None,
                    'metadata': metadatas[i] if i < len(metadatas) else None,
                    'distance': distances[i] if i < len(distances) else None
                })
            return out
        except Exception as e:
            logger.error(f"ChromaHTTP search_similar failed: {e}")
            return []

    def search_vectors(self, collection_name: str, query_embeddings: List[List[float]], n_results: int = 5) -> List[Dict]:
        """Search by vector embeddings."""
        try:
            coll = self.get_collection(collection_name)
            res = coll.query(query_embeddings=query_embeddings, n_results=n_results)
            out = []
            ids = res.get('ids', [[]])[0] if isinstance(res.get('ids'), list) else []
            docs = res.get('documents', [[]])[0] if isinstance(res.get('documents'), list) else []
            metadatas = res.get('metadatas', [[]])[0] if isinstance(res.get('metadatas'), list) else []
            distances = res.get('distances', [[]])[0] if isinstance(res.get('distances'), list) else []
            for i, _id in enumerate(ids):
                out.append({
                    'id': _id,
                    'document': docs[i] if i < len(docs) else None,
                    'metadata': metadatas[i] if i < len(metadatas) else None,
                    'distance': distances[i] if i < len(distances) else None
                })
            return out
        except Exception as e:
            logger.error(f"ChromaHTTP search_vectors failed: {e}")
            return []


# Provide the backward-compatible symbol name expected by DatabaseManager
ChromaVectorBackend = ChromaHTTPVectorBackend

def get_backend_class():
    return ChromaVectorBackend
