Neo4j HTTP-Fallback (Adapter-Dokumentation)
==========================================

Überblick
---------
Der `Neo4jGraphBackend` unterstützt zwei Verbindungswege:

- Native Python-Treiber (`neo4j` package, empfohlen) — verwendet Bolt-Protokoll.
- HTTP-Fallback über den transactional endpoint (`/db/<db>/tx/commit`) — nützlich, wenn der native
  Treiber nicht importierbar oder nicht gewünscht ist.

Konfiguration
-------------
Folgende Konfigurationsoptionen werden vom Adapter beachtet (Konfig-Dict):

- `uri`: Bolt-URI (z. B. `bolt://host:7687`) — Standard für native Driver.
- `username`, `password`: Authentifizierungsdaten.
- `database`: Ziel-Datenbank (Default: `neo4j`).
- `use_http_fallback` (bool, Default: True): Wenn True, versucht der Adapter beim Fehlschlag
  des nativen Treibers einen HTTP-Fallback.
- `http_url` (str, optional): Explizite HTTP-URL (z. B. `http://host:7474`). Wird diese nicht
  gesetzt, versucht der Adapter `host`/`port`/`http_scheme` aus der Config herzuleiten.
- `http_scheme` (str, optional): `http` oder `https` (Default: `http`).

Beispiel-Konfig:

```python
{
  'uri': 'bolt://192.168.178.94:7687',
  'username': 'neo4j',
  'password': 'secret',
  'database': 'neo4j',
  'use_http_fallback': True,
  'http_url': 'https://192.168.178.94:7474'
}
```

Limitierungen des HTTP-Fallbacks
--------------------------------
- Funktionalität: Der HTTP-Fallback verwendet das transactional HTTP-API. Nicht alle Fähigkeiten
  des nativen Treibers (z. B. niedrige Latenz, Session/Transaction-Streaming-Optimierungen)
  sind identisch.
- Authentifizierung: Der Fallback nutzt Basic Auth über `requests.Session().auth`.
- Performance: HTTP-Fallback ist in der Regel langsamer als Bolt.

Best Practices
--------------
1. Produktion: Verwende wenn möglich den offiziellen `neo4j`-Treiber auf einer unterstützten
   Python-Installation.
2. Test/CI: Wenn native driver-Import-Probleme auftreten, nutze den Test-Import-Guard (siehe `tests/README.md`)
   oder führe Tests in einem sauberen `venv` mit einem unterstützten Python aus.
3. Sicherheit: Wenn du HTTPS/TLS verwendest, setze `http_url` mit `https://...` und stelle
   sicher, dass Zertifikatsprüfung korrekt konfiguriert ist.

Fehlerdiagnose
--------------
- Importfehler (z. B. `module 'socket' has no attribute 'EAI_ADDRFAMILY'`) deuten oft auf
  eine eingeschränkte Python-Umgebung; ziehe einen anderen Interpreter/venv in Betracht.
- HTTP-Fallback-Fehler: überprüfe Erreichbarkeit und Authentifizierung des HTTP-Endpoints.
