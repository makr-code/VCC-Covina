"""
Themis Document Backend

Implements CouchDB-like document operations on top of Themis Content API.

Author: VCC Covina Team
Created: 2025-11-07
Version: 0.1.0
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any

from .themis_adapter import ThemisAdapter


class ThemisDocumentBackend:
    """Document Backend for Themis (CouchDB → Themis Content API)

    Provides UDS3-compatible operations:
    - store_document(doc_id, file_path, mime_type, metadata=None, blob_data=None)
    - get_document(doc_id)
    - get_blob(doc_id)
    - get_chunks(doc_id, page=1, page_size=100)
    """

    def __init__(self, adapter: ThemisAdapter):
        self.adapter = adapter
        self.client = adapter  # use adapter's retry-enabled methods
        self.logger = adapter.logger

    async def store_document(
        self,
        doc_id: str,
        file_path: str,
        mime_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        blob_data: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Store document metadata and optional binary content."""
        content_meta = {
            "id": doc_id,
            "mime_type": mime_type,
            "category": self._get_category(mime_type),
            "original_filename": Path(file_path).name,
            "size_bytes": len(blob_data) if blob_data else 0,
            "hash_sha256": hashlib.sha256(blob_data).hexdigest() if blob_data else "",
            "user_metadata": metadata or {},
        }
        payload: Dict[str, Any] = {"content": content_meta}
        if blob_data:
            payload["blob_base64"] = base64.b64encode(blob_data).decode("ascii")

        response = await self.client.post("/content/import", json=payload)
        return response.json()

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        response = await self.client.get(f"/content/{doc_id}")
        if response.status_code == 404:
            return None
        return response.json()

    async def get_blob(self, doc_id: str) -> Optional[bytes]:
        response = await self.client.get(f"/content/{doc_id}/blob")
        if response.status_code == 404:
            return None
        return response.content

    async def get_chunks(self, doc_id: str, page: int = 1, page_size: int = 100) -> List[Dict[str, Any]]:
        response = await self.client.get(f"/content/{doc_id}/chunks", params={"page": page, "page_size": page_size})
        data = response.json()
        return data.get("chunks", [])

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _get_category(self, mime_type: str) -> int:
        if mime_type.startswith("text"):
            return 0  # TEXT
        if mime_type.startswith("image"):
            return 1  # IMAGE
        if mime_type.startswith("audio"):
            return 2  # AUDIO
        if mime_type.startswith("video"):
            return 3  # VIDEO
        if mime_type == "application/pdf":
            return 8  # BINARY
        return 9  # UNKNOWN

__all__ = ["ThemisDocumentBackend"]
