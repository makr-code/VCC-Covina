# UDS3 - Konkrete Umsetzungsschritte

Datum: 01.10.2025

Diese Datei enthält konkrete, umsetzbare Schritte für die priorisierten Aufgaben aus `todo.md`.

## 1) Health-Check (abgeschlossen)
- Status: Done (mit Python 3.13 kompatibler Anforderungen via `requirements-py313.txt`).
- Ergebnis: `pytest` zeigte 1 passed (siehe Terminal-Output).

## 2) Sofortige Quickwins (Kurzfristig)

A) Test-Hilfsfunktionen: Add Unit Tests (0.5–1h)
- Dateien & Ziele:
  - `tests/test_helpers.py`:
    - test `_generate_document_id`: deterministic given file_path and preview => assert prefix `doc_` and length
    - test `_format_document_id` and `_infer_uuid_from_document_id`
  - `tests/test_security.py`:
    - test `DataSecurityManager.generate_secure_document_id` returns keys `document_id`, `document_uuid`, `content_hash`.
- Akzeptanz: `pytest` zeigt neue Tests grün.

B) Create minimal CI pipeline (1–2h)
- Ziel: GitHub Actions workflow `.github/workflows/ci.yml` mit:
  - setup python 3.13
  - pip install -r requirements-py313.txt
  - pytest -q
  - ruff optional (wenn verfügbar)
- Akzeptanz: Pipeline template in repo; lokal ausführbar.

C) Add `requirements-py313.txt` (done)
- Hinweis: dokumentieren, dass dies dev-spezifisch ist

## 3) Security: Lizenz-Keys Audit (Kurzfristig, 1–2h + Abstimmung)
- Schritte:
  - Skript `tools/find_protection_keys.py` implementieren: listet Dateien mit `module_licence_key`/`module_file_key`.
  - Ergebnis in `security/key_inventory.md`
  - Abstimmung mit Rechts/Lizenzhaltenden Team bevor Entfernen/Änderung.
- Akzeptanz: Inventory erstellt.

## 4) Tests & Adapter-Mocks (Mittelfristig, 1–2d)
- Schritte:
  - Definiere Protokolle in `third_party_stubs` (falls nicht vorhanden), z. B. `SagaCrudProtocol`, `DatabaseManagerProtocol`.
  - Schreibe Mocks in `tests/fixtures/mocks.py`.
  - Erweitere Tests für CRUD-Operationen mit Mocks (create/update/delete happy path + one failure).
- Akzeptanz: Tests laufen komplett mit Mocks, keine externe DB benötigt.

## 5) Typisierung & Linter (Mittelfristig, 4–8h)
- Schritte:
  - `pyproject.toml` oder `mypy.ini` mit Basiskonfiguration hinzufügen.
  - Führe `ruff` (falls verfügbar) und `mypy` lokal; behebe kritische Warnungen.
- Akzeptanz: `ruff` sauber (oder dokumentierte ignore), `mypy` ohne kritische Fehler.

## 6) Documentation (Low/Medium)
- Erstelle `docs/API_REFERENCE.md` mit:
  - Contracts: Saga CRUD expected methods and return payload shape
  - Example: minimal `saga_crud` mock implementation example
- Akzeptanz: Doc existiert und referenziert in `README`.

## 7) Langfristige Verbesserungen (Roadmap)
- Observability: add metrics, Prometheus exporter
- Performance tests: create benchmark scripts for vector ingestion
- Distributed orchestration: research and design multi-node saga orchestration

---

## Nächster konkreter Schritt (ich kann jetzt tun)
- Implementiere `tests/test_helpers.py` und `tests/test_security.py` (Quickwin A) und führe `pytest`. -> Soll ich das jetzt anlegen und ausführen? (Antwort: "ja"/"nein")

