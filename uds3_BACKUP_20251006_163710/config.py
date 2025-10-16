"""Zentrale Konfigurationsdatei für das UDS3 Projekt.

Diese Datei enthält Standardkonfigurationen für alle Adapter (Datenbanken,
Geo, Identity, Security, Quality, Batch-Optimierungen etc.).

Wichtig: Laut Anforderung werden keine Umgebungsvariablen direkt im Code
verwendet. Overrides können lokal durch das Laden einer separaten
`config_local.py` erfolgen, welche die hier definierten Werte ändern kann.
"""

from typing import Dict, Any

# Default database adapter configurations
DATABASES: Dict[str, Dict[str, Any]] = {
    "postgis": {
        "host": "localhost",
        "port": 5432,
        "database": "uds3_geo",
        "user": "postgres",
        "password": "",
        "connect_timeout": 10,
    },
    "vector": {
        "provider": "chromadb",
        "endpoint": "http://localhost:8000",
        "api_key": "",
    },
    "graph": {
        "provider": "neo4j",
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "",
    },
    "relational": {
        "provider": "postgresql",
    },
}

# Feature flags and adapter switches (explicit, no os.getenv())
FEATURES: Dict[str, Any] = {
    # Expect UDS3 backend (used in api backend to enable dev behaviours)
    "expect_uds3_backend": False,
}

# Optimization and batch sizes
OPTIMIZATION: Dict[str, Any] = {
    "batch_size": 500,
    "vector_batch_size": 100,
}

# Geo specific defaults
GEO_SETTINGS: Dict[str, Any] = {
    "auto_extract": True,
    "quality_threshold": 0.5,
    "default_srid": 4326,
}


def load_local(overrides_module_name: str = "uds3.config_local") -> None:
    """Lädt optionale lokale Überschreibungen aus `config_local.py`.

    Diese Funktion importiert das Modul mit dem gegebenen Namen (falls
    vorhanden) und übernimmt alle Attribute, die in diesem Modul gesetzt
    sind (z.B. DATABASES, FEATURES, OPTIMIZATION).
    """
    try:
        mod = __import__(overrides_module_name, fromlist=["*"])
    except ImportError:
        return

    for name in ("DATABASES", "FEATURES", "OPTIMIZATION"):
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)


# Versuche lokale Overrides automatisch zu laden, falls vorhanden
load_local()
