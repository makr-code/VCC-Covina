# UDS3 - Offene To-dos

Diese Datei fasst alle offenen Aufgaben und Punkte zusammen, wie im Repository-Scan identifiziert.

Stand: 01.10.2025

---

## Aktueller ToDo-Status (kurz)
- `Lücken & Risiken identifizieren` — in progress
- `Konkrete ToDos & Verbesserungen vorschlagen` — not started

---

## Aufgaben (Priorisiert)

1) Health-Check: Umgebung & Basistests (Priority: High)
- Status: vorgeschlagen / noch nicht ausgeführt
- Beschreibung: Lokale Python-Umgebung konfigurieren, Dependencies aus `requirements.txt` installieren, `pytest` ausführen, `ruff`-Check.
- Geschätzter Aufwand: 30–90 Minuten (abhängig von Netzwerk/Build)
- Akzeptanzkriterien:
  - `pip install -r requirements.txt` läuft ohne fatalen Fehler
  - `pytest -q` läuft (mindestens ohne Syntax-Fehler); Output mit Liste fehlschlagender Tests wird erzeugt
  - `ruff` meldet style-Warnungen (optional: Fix-Vorschläge)
- Nächster Schritt: Ich kann das jetzt starten (vorausgesetzt Installation in Arbeitsumgebung ist erlaubt)


2) Sensible Schlüssel / Lizenzhärtung (Priority: High)
- Status: open
- Beschreibung: Dateien enthalten `module_licence_key` / `module_file_key` (VERITAS protected markers). Diese dürfen nicht im Klartext verändert oder entfernt werden ohne rechtliche Freigabe.
- Arbeitspunkte:
  - Inventar aller Dateien mit protection keys
  - Rücksprache mit Lizenzhalter (VERITAS) / Legal bevor Änderungen
  - Falls freigegeben: Schlüssel in Konfiguration / Secrets verschieben (z. B. env, Vault)
- Geschätzter Aufwand: 1–4 Stunden inkl. Abstimmung
- Akzeptanzkriterien: Keine Plaintext-Lizenzschlüssel in bearbeiteten Quell-Dateien; dokumentierter Übergang in Secret-Management


3) Tests & CI (Priority: Medium)
- Status: open
- Beschreibung:
  - Erweitern der Unit-Tests (Kern-Helper + Security/Identity basic tests)
  - GitHub Actions workflow (pytest + ruff + optional mypy)
- Arbeitspunkte:
  - Minimaltests für `_generate_document_id`, `_format_document_id`, Security ID generation
  - CI workflow `python: setup -> pip install -r -> ruff -> pytest`
- Geschätzter Aufwand: 1–2 Tage
- Akzeptanzkriterien: CI läuft grün bei Basis-Checks; neue Tests vorhanden


4) Adapter Interfaces & Mocks (Priority: Medium)
- Status: open
- Beschreibung: Definierte Protocols/Interfaces (z. B. SagaCrudProtocol, DatabaseManagerProtocol) und Mock-Implementierungen für Tests erstellen.
- Arbeitspunkte:
  - Minimal-Protokolle in `third_party_stubs` oder `uds3_admin_types.py`
  - Mocks in `tests/fixtures`
- Geschätzter Aufwand: 0.5–1 Tag
- Akzeptanzkriterien: Unit-Tests laufen mit Mocks ohne reale DB


5) Typisierung & Linter (Priority: Medium)
- Status: open
- Beschreibung: `ruff` und ggf. `mypy` einführen, Typhinweise in kritischen Teilen verbessern.
- Arbeitspunkte: `pyproject.toml`/`mypy.ini` minimal, `ruff`-Konfiguration, erste Fixes
- Geschätzter Aufwand: 2–6 Stunden
- Akzeptanzkriterien: `ruff` ohne Fehler (oder dokumentierte Ausnahmen); `mypy` ohne showstopper-Fehler


6) API-Dokumentation & Adapter-Beispiele (Priority: Low)
- Status: open
- Beschreibung: `docs/API_REFERENCE.md` mit Beispielen für Adapter-Implementierung (saga_crud, vector adapter, graph adapter)
- Geschätzter Aufwand: 4–8 Stunden
- Akzeptanzkriterien: Mindestens ein vollständiges Adapter-Beispiel in `docs/`


7) Langfristig: Performance, Observability, Distributed (Roadmap)
- Status: open
- Beschreibung: Profilerstellung, integration of metrics, distributed orchestration, caching strategies.

---

## Vorgehensweise / Workflow Vorschlag
1. Zustimmung hier im Chat: ich starte den Health-Check (Install & pytest).
2. Ergebnisreport (Erfolg/Fehler). Bei Fehlern: gezielte Fix-Tickets (Priorität: High/Medium/Low).
3. Sobald Health-Check grün (oder Mängel priorisiert), gehen wir Punkt für Punkt die Liste ab; ich übernehme die Umsetzung der ersten kleinen Tasks (Tests, CI) und melde jeweils Ergebnisse.

---

## Änderungsvermerk
- Datei automatisch erstellt am 01.10.2025 per Anforderung des Maintainers.



