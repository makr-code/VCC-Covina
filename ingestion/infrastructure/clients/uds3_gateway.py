from __future__ import annotations
from typing import Optional, Any


class UDS3Gateway:
    """Adapter für den Zugriff auf UDS3-verwaltete Backends (kein Direktzugriff auf DBs).

    - Lädt die Verbindungsdaten über UDS3 DatabaseManager
    - Erstellt den passenden Backend-Adapter (z. B. Neo4jGraphBackend)
    - Hält optionale Caches für wiederholte Nutzung
    """

    def __init__(self) -> None:
        self._graph_adapter: Optional[Any] = None

    def get_graph_adapter(self) -> Any:
        """Gibt den UDS3 Graph-Backend-Adapter zurück (verbunden, wenn möglich)."""
        if self._graph_adapter is not None:
            return self._graph_adapter

        # Import hier, um harte Abhängigkeit beim Importieren zu vermeiden
        try:
            from uds3.database.config import DatabaseManager, DatabaseType
            from uds3.database.database_api_neo4j import Neo4jGraphBackend
        except Exception as e:  # pragma: no cover - harte Importfehler klar melden
            raise RuntimeError(f"UDS3 nicht verfügbar oder fehlerhaft installiert: {e}")

        manager = DatabaseManager()
        # Suche Graph-DB Konfiguration
        graph_cfg = None
        for db in manager.databases:
            if db.db_type.name.lower() == DatabaseType.GRAPH.value:
                graph_cfg = db
                break
        if graph_cfg is None:
            raise RuntimeError("Keine Graph-Datenbank in UDS3-Konfiguration gefunden")

        # Neo4j-Backend mit UDS3-Config initialisieren
        backend_cfg = {
            'host': graph_cfg.host,
            'port': graph_cfg.port,
            'user': graph_cfg.username,
            'password': graph_cfg.password,
            'database': graph_cfg.database,
            'uri': graph_cfg.get_connection_string().replace('bolt://', 'neo4j://'),
            'settings': graph_cfg.settings or {},
        }

        adapter = Neo4jGraphBackend(backend_cfg)
        adapter.connect()  # Soft-connect: Adapter handhabt Fallbacks/Retry

        self._graph_adapter = adapter
        return self._graph_adapter

