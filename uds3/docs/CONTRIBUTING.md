# Contributing to UDS3

Vielen Dank, dass du zum UDS3-Projekt beitragen möchtest!

Kurze Hinweise:

- Branching: Erstelle Feature-Branches von `main` mit klaren Commit-Messages.
- Tests: Füge für neue Funktionen kurze pytest-Tests hinzu. Lokales Ausführen:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

- Proprietäre Abhängigkeiten: Einige Module sind intern (z. B. `veritas_relations_almanach`, `database.*`). Für lokale Entwicklung können die vorhandenen Any-Fallbacks genutzt werden, oder du legst Stubs unter `third_party_stubs/` an.

Editor / Pylance Hinweise (VSCode)
---------------------------------

Wenn Pylance in VSCode `Import "uds3" konnte nicht aufgelöst werden` anzeigt, stelle sicher, dass der Workspace-Pfad richtig gesetzt ist und die `third_party_stubs/` im PYTHONPATH enthalten sind. Beispiel `settings.json` (Workspace):

```
{
	"python.analysis.extraPaths": [
		"${workspaceFolder}",
		"${workspaceFolder}/third_party_stubs"
	],
	"python.languageServer": "Pylance"
}
```

Alternativ kannst du in einer PowerShell-Session vor dem Start der IDE ein virtuelles Environment aktivieren und das Repo-Root dem PYTHONPATH hinzufügen:

```powershell
# PowerShell
$env:PYTHONPATH = "${PWD}\third_party_stubs;${PWD}"
code .
```

Verwende die `third_party_stubs/` um einfache, leichtgewichtige Stubs für proprietäre Module bereitzustellen. Diese Stubs sollten nur die API-Signaturen enthalten, die du beim Entwickeln erwartest.

Beispiel minimaler Stub (third_party_stubs/collection_manager.py):

```python
class CollectionManager:
		def __init__(self):
				pass

		def register_collection(self, name, schema):
				return True
```

Automatisches Setup für Entwickler
----------------------------------

Es gibt ein kleines PowerShell-Skript `setup_dev.ps1` im Projekt-Root, das ein virtuelles Environment erstellt, dev-Abhängigkeiten installiert und den `PYTHONPATH` für die aktuelle Session setzt:

```powershell
.\\\setup_dev.ps1
```

Nach dem Ausführen dieses Skripts ist VSCode in der Regel in der Lage, `uds3` und die `third_party_stubs/` korrekt aufzulösen.

- Code style: Halte dich an bestehendes Format. Nutze `black`/`ruff` falls im Team eingerichtet.

- Pull Requests: Beschreibe kurz die Änderung, Auswirkungen auf Laufzeit-Abhängigkeiten und ggf. notwendige Migrations-Schritte.
