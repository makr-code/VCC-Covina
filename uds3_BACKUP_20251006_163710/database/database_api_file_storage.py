#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileSystem Storage Backend
--------------------------

Ein einfaches, lokales dateibasiertes Storage-Backend für Binär-Assets.
Ziele:
- Speichert Binärdateien unter einem Root-Pfad deterministisch nach Content-Hash
- Liefert stabile URIs (file:// oder Pfad) zurück
- Keine Rohdaten in DBs; nur Pfad/URI und Metadaten werden anrufseitig persistiert

Hinweis: Dieses Backend implementiert nur die für Asset-Speicherung relevanten Methoden und
erbt von der generischen DatabaseBackend-Basis. Es stellt KEINE Vektor/Graph/SQL-Funktionen bereit.
"""

import logging
import os
import hashlib
import shutil
from datetime import datetime
from typing import Dict, Optional

from database.database_api_base import DatabaseBackend

logger = logging.getLogger(__name__)


class FileSystemStorageBackend(DatabaseBackend):
    """Lokales Dateisystem-Storage für Binär-Assets"""

    def __init__(self, config: Dict):
        super().__init__(config)
        # Konfiguration
        self.root_path = os.path.abspath(config.get('root_path', './data/assets'))
        self.uri_scheme = config.get('uri_scheme', 'file')  # 'file' oder 'path'
        self.preserve_filenames = bool(config.get('preserve_filenames', False))
        self.hash_subdirs = int(config.get('hash_subdirs', 2))  # Anzahl Subdir-Ebenen nach Hash-Präfix
        self._available = False

    # === Required abstract methods from DatabaseBackend ===
    def connect(self) -> bool:
        try:
            os.makedirs(self.root_path, exist_ok=True)
            # Schreibprobe
            test_path = os.path.join(self.root_path, '.fs_backend_write_test')
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write('ok')
            os.remove(test_path)
            self._available = True
            self._is_connected = True
            logger.info(f"✅ FileSystemStorage verbunden: root={self.root_path}")
            return True
        except Exception as e:
            logger.error(f"FileSystemStorage connect fehlgeschlagen: {e}")
            self._available = False
            self._is_connected = False
            return False

    def disconnect(self):
        # Nichts zu tun für das Lokalfilesystem
        self._is_connected = False
        logger.info("FileSystemStorage getrennt")

    def is_available(self) -> bool:
        return bool(self._available and os.path.isdir(self.root_path))

    def get_backend_type(self) -> str:
        return "FileSystem Storage"

    # === Public API ===
    def store_asset(self, *, source_path: Optional[str] = None, data: Optional[bytes] = None,
                    filename: Optional[str] = None, mime: Optional[str] = None,
                    content_hash: Optional[str] = None, subdir: Optional[str] = None,
                    metadata: Optional[Dict] = None) -> Dict:
        """Speichert ein Asset im Dateisystem und liefert Metadaten zurück.

        Priorität: data (Bytes) > source_path. Falls content_hash fehlt, wird er berechnet (SHA-256).
        Der Zielpfad basiert auf dem Hash und optionaler Subdir-Struktur.
        """
        if not self.is_available():
            raise RuntimeError("FileSystemStorage ist nicht verfügbar")

        if data is None and not source_path:
            raise ValueError("store_asset erfordert entweder 'data' oder 'source_path'")

        # Hash berechnen
        if content_hash:
            file_hash = content_hash.lower()
        else:
            file_hash = self._compute_sha256(source_path=source_path, data=data)

        # Dateiendung beibehalten (falls filename oder source_path vorhanden)
        ext = ""
        for candidate in (filename, source_path):
            if candidate:
                _, ext = os.path.splitext(candidate)
                break

        # Zielpfad konstruieren (hash-basierte Subdirs)
        rel_dir = self._hash_to_subdirs(file_hash, subdir=subdir)
        abs_dir = os.path.join(self.root_path, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        # Dateiname: Hash + Originalextension (falls vorhanden) oder Originalname (optional)
        if self.preserve_filenames and filename:
            target_name = filename
        else:
            target_name = f"{file_hash}{ext.lower()}"

        abs_path = os.path.join(abs_dir, target_name)

        # Falls Datei bereits existiert: kein erneutes Schreiben
        if not os.path.exists(abs_path):
            if data is not None:
                with open(abs_path, 'wb') as f:
                    f.write(data)
            else:
                shutil.copy2(source_path, abs_path)

        size_bytes = os.path.getsize(abs_path)
        created_at = datetime.fromtimestamp(os.path.getmtime(abs_path)).isoformat()
        uri = self._to_uri(abs_path)

        info = {
            'asset_id': file_hash,
            'hash': file_hash,
            'uri': uri,
            'path': abs_path,
            'size': size_bytes,
            'mime': mime,
            'created_at': created_at,
        }
        if metadata:
            info['metadata'] = metadata
        return info

    def upsert_derivative(self, *, asset_id: str, derivative_type: str,
                           source_path: Optional[str] = None, data: Optional[bytes] = None,
                           filename: Optional[str] = None, mime: Optional[str] = None,
                           content_hash: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict:
        """Speichert ein Derivat (z. B. Thumbnail) unterhalb des Asset-Ordners."""
        if not self.is_available():
            raise RuntimeError("FileSystemStorage ist nicht verfügbar")

        # Unterordner: <root>/<hash-subdirs>/<asset_id>/derivatives/<type>/
        rel_dir = self._hash_to_subdirs(asset_id)
        rel_dir = os.path.join(rel_dir, asset_id, 'derivatives', derivative_type)
        abs_dir = os.path.join(self.root_path, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        # Hash/Dateiname bestimmen
        if content_hash:
            file_hash = content_hash.lower()
        else:
            file_hash = self._compute_sha256(source_path=source_path, data=data)

        ext = ""
        for candidate in (filename, source_path):
            if candidate:
                _, ext = os.path.splitext(candidate)
                break
        target_name = filename or f"{file_hash}{ext.lower()}"
        abs_path = os.path.join(abs_dir, target_name)

        if not os.path.exists(abs_path):
            if data is not None:
                with open(abs_path, 'wb') as f:
                    f.write(data)
            else:
                shutil.copy2(source_path, abs_path)

        size_bytes = os.path.getsize(abs_path)
        created_at = datetime.fromtimestamp(os.path.getmtime(abs_path)).isoformat()
        uri = self._to_uri(abs_path)
        return {
            'asset_id': asset_id,
            'type': derivative_type,
            'hash': file_hash,
            'uri': uri,
            'path': abs_path,
            'size': size_bytes,
            'mime': mime,
            'created_at': created_at,
            'metadata': metadata or {}
        }

    # === Helpers ===
    def _compute_sha256(self, *, source_path: Optional[str] = None, data: Optional[bytes] = None) -> str:
        h = hashlib.sha256()
        if data is not None:
            h.update(data)
            return h.hexdigest()
        if source_path:
            with open(source_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()
        raise ValueError("_compute_sha256 requires source_path or data")

    def _hash_to_subdirs(self, file_hash: str, *, subdir: Optional[str] = None) -> str:
        # Erzeuge n Ebenen Subdirs aus den ersten 2*n Zeichen des Hashs
        parts = []
        for i in range(self.hash_subdirs):
            start = i * 2
            parts.append(file_hash[start:start+2])
        rel = os.path.join(*parts) if parts else ''
        if subdir:
            rel = os.path.join(rel, subdir)
        return rel

    def _to_uri(self, abs_path: str) -> str:
        if self.uri_scheme == 'file':
            # Windows-sichere file-URI
            p = abs_path.replace('\\', '/')
            if not p.startswith('/'):
                p = '/' + p
            return f"file://{p}"
        return abs_path


def get_backend_class():
    """Factory-Funktion für FileSystem Storage Backend"""
    return FileSystemStorageBackend
