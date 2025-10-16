# `config.py`

Kurzbeschreibung
-----------------
Zentrale Konfigurationsschnittstelle für das `database`-Package. Lädt lokale
Konfig-Dateien (z. B. `server_config.json`), stellt `get_database_backend_dict()`
und Fabrikhilfen bereit.

Analyse
-------
`config.py` ist die Einstiegsschnittstelle für Umgebungs- und Datei-basierte
Konfiguration. Es ist sinnvoll, klare Environment-Overrides und Defaults zu
dokumentieren, da Tests und Produktionsläufe unterschiedliche Sets erwarten.

Wichtige Funktionen
-------------------
- `get_database_backend_dict()` — liefert das konfigurierte Backend-Dictionary.
- `create_backend_instances_dynamisch()` — (falls vorhanden) Erzeugt
  instanziierte Backend-Configs für `DatabaseManager`.

Tests
-----
- Usage: `tests/test_all_configured_backends.py` und Manager-Tests nutzen das
  Config-API.

Roadmap
-------
- Dokumentation der erlaubten Keys pro Backend (host, port, username, password,
  database, database_path, path, uds3 flags, usw.).
- CLI/Hilfs-Funktion: `config.validate()` zur Validierung der `server_config.json`.
- Optional: Unterstützung für `yaml` Config Dateien und de-/fallback-Profile.

Beispiel
-------
```python
from database import config
backend_dict = config.get_database_backend_dict()
```