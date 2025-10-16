# `saga_compensations.py`

Kurzbeschreibung
-----------------
Registry und Sammlung von Standard-Kompensationen, die von der Saga-
Orchestrator-Logik aufgerufen werden. Kompensationen sind idempotente
Rückgängig-Operationen, die im Fehlerfall in umgekehrter Reihenfolge
ausgeführt werden.

Analyse
-------
`saga_compensations.py` ist bewusst als leichtgewichtige Registry realisiert:
- `register(name, handler)` fügt einen Handler hinzu
- `get(name)` liefert den Handler zurück oder `None`

Die Default-Handler (z. B. `relational_delete`) sind robust implementiert und
achten auf Idempotency (z. B. löschen eines bereits gelöschten Eintrags wird
als Erfolg behandelt).

API / Signaturen
----------------
- `register(name: str, handler: Callable[[DatabaseManager, Dict], bool])`
- `get(name: str) -> Callable | None`
- Default Handler: `relational_delete(manager, payload) -> bool`
  - Erwartet `payload` mit `table` und `record`/`id` Feldern

Testabdeckung
-------------
- `tests/test_saga_compensations.py` prüft Funktionen wie `relational_delete` und
  stellt sicher, dass wiederholte Aufrufe idempotent behandelt werden.

Roadmap
-------
- Handler-Metadaten: beschreiben, ob Handler blockierend sind und welche
  Fehler skalierbar sind.
- Priorisierung und kompensations-spezifische Retry-Strategien
- Möglichkeit, Kompensations-Handler asynchron zu registrieren (z. B. via
  entry_points für Plugins)

Beispiel
-------
```python
from database.saga_compensations import register, get

def my_compensation(manager, payload):
    # payload example: {'table':'documents','record':{'id':'d1'}}
    return True

register('my_comp', my_compensation)
handler = get('my_comp')
```