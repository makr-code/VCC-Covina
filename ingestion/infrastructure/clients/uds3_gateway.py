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
            from uds3.database.database_manager import DatabaseManager
        except Exception as e:  # pragma: no cover - harte Importfehler klar melden
            raise RuntimeError(f"UDS3 nicht verfügbar oder fehlerhaft installiert: {e}")

        # Starte nur Graph-Backend über den UDS3 DatabaseManager
        manager = DatabaseManager({'graph': {'enabled': True}}, autostart=True)
        adapter = getattr(manager, 'graph_backend', None)
        if not adapter:
            raise RuntimeError("Graph-Backend nicht verfügbar (UDS3 DatabaseManager hat kein graph_backend)")

        # Adapter ist bereits verbunden (manager.autostart=True sorgt für Connect)
        self._graph_adapter = adapter
        return self._graph_adapter

