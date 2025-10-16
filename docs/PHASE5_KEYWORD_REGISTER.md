# Phase 5 – Keyword-Register (Relationale Datenbank) Planungsdokument

## Überblick
- **Ziel:** Aufbau eines relationalen Keyword-Registers, das Synonyme, Quellenverweise und Governance-Informationen für UDS3 verwaltet und mit Graph-, Vector- und Filesystem-Stores interoperiert.
- **Zeithorizont:** KW 45–49 (Discovery & Architektur), KW 50–2 (Implementierung & Rollout).
- **Owner:** Relational Data Crew (Lead: Data Platform Engineering).
- **Stakeholder:** Search & Retrieval Product, Behörden-Fachbereiche, Compliance/Legal, Vector WG, Graph Crew, DevOps Platform.
- **Erfolgskriterien:**
  1. Abgenommene Datenmodell-Spezifikation inkl. ER-Diagramm und Normalisierung.
  2. API/Service-Spec (REST/CLI) freigegeben, erste Integrationstests mit Vector & Graph Layer erfolgreich.
  3. Migration/Seed-Skripte für initiales Keyword-Set produktionsbereit.

## Scope
- Modellierung von Keywords, Synonym-Gruppen, Quellen, Klassifikationen und Audit-Trail.
- CRUD- und Such-Operationen via REST + CLI (PowerShell & Python Client).
- Synchronisationsstrategie mit Vector Store (für Embedding-Refresh) und Graph Store (Relationen).
- Migrationspfad für Legacy Keyword-Listen (CSV/Excel) und kontinuierliche Pflegeprozesse.

### Nicht im Scope
- Vollständige Search-UI (Phase 7).
- Automatisierte Qualitätssicherung über ML-Modell (wird in Phase 6 vorbereitet).
- Advanced Analytics (Trendanalysen) – optionaler Stretch Goal.

## Deliverables & Meilensteine
| KW | Deliverable | Owner | Akzeptanzkriterium |
|----|-------------|-------|--------------------|
| 45 | Discovery-Workshops (Anforderungen, Stakeholder) | Product + Data Platform | Abnahme Meeting Minutes & Use-Case Consolidation |
| 46 | ERD Draft + Datenklassifikation | Data Platform | ERD freigegeben, Entitätsliste finalisiert |
| 47 | API/Service Blueprint (REST/CLI) | Backend Team | ADR-Eintrag erstellt, Schnittstellen sign-off |
| 48 | Synchronisationskonzept (Vector/Graph) | Integration Team | Sequenzdiagramme + Fehlerpfade dokumentiert |
| 49 | Migration/Seed Strategie + Testdaten | Data Platform + QA | Seed-Skript läuft lokal, Testplan abgestimmt |
| 50 | Implementierung MVP Services | Backend Team | CRUD-Befehle lauffähig, Tests grün |
| 1 | Integrationen Vector/Graph abgeschlossen | Integration Team | End-to-End Demo erfolgreich |
| 2 | Rollout-Plan + Betriebsdoku | DevOps + Compliance | Betriebs-Runbook abgenommen |

## Datenmodell (Draft)
### Entitäten & Tabellen
| Tabelle | Zweck | Primärschlüssel | Wichtige Felder | Beziehungen |
|---------|-------|-----------------|-----------------|-------------|
| `keywords` | Hauptbegriffe | `keyword_id` (UUID) | `term`, `language`, `status`, `created_at`, `updated_at` | 1:n zu `keyword_synonyms`, n:m zu `keyword_sources` via Bridge |
| `keyword_synonyms` | Synonym-Varianten (inkl. Typ) | `synonym_id` (UUID) | `synonym_term`, `synonym_type` (enum: exact, broad, narrow, colloquial), `confidence_score` | n:1 zu `keywords` |
| `keyword_sources` | Quellen/Referenzen (Normen, Gesetze) | `source_id` (UUID) | `source_name`, `source_type`, `effective_date`, `expiry_date` | n:m via `keyword_source_links` |
| `keyword_source_links` | Bridge Keyword ↔ Source | (`keyword_id`, `source_id`) | `relevance`, `notes` | n:1 zu `keywords` & `keyword_sources` |
| `keyword_categories` | Klassifikation (Domain, Behördenprozess) | `category_id` (UUID) | `category_name`, `description`, `parent_category_id` | 1:n selbst-referenzierend |
| `keyword_category_links` | Bridge Keyword ↔ Kategorie | (`keyword_id`, `category_id`) | `primary_flag` | n:1 zu `keywords` & `keyword_categories` |
| `keyword_audit_log` | Change History | `audit_id` (UUID) | `keyword_id`, `change_type`, `changed_by`, `change_payload`, `timestamp` | n:1 zu `keywords` |

### Normalisierung & Policies
- **3NF** für Haupttabellen, Bridge-Tabellen im BCNF.
- Soft-Delete via `status` Enum (`active`, `deprecated`, `candidate`).
- Temporal Validity für Quellen (`effective_date`, `expiry_date`).
- Mandatory Audit-Log für alle Änderungen (Trigger/Service Level).

### Offene Entscheidungen
- ID-Format: Native UUID vs. Snowflake – Präferenz: UUIDv7 für Zeit-Sortierbarkeit.
- Multi-Language Handling: Separate Einträge je Sprache oder JSON Column (`translations`). Discovery klärt Präferenz der Behörden.

## API- und Service-Spezifikation
### REST-Endpunkte (Draft)
| Methode | Pfad | Beschreibung | Besondere Parameter |
|---------|------|--------------|---------------------|
| GET | `/keywords` | Query/Search mit Paging & Filter | `term`, `language`, `status`, `category`, `source`, `page`, `size` |
| POST | `/keywords` | Keyword + Synonyme + Kategorien anlegen | Payload Validierung, Idempotency-Key |
| GET | `/keywords/{id}` | Keyword inkl. Relationen abrufen | Expand-Parameter: `synonyms`, `sources`, `categories`, `audit` |
| PUT | `/keywords/{id}` | Vollständiges Update | Concurrency via ETag oder `if-match` |
| PATCH | `/keywords/{id}` | Teilupdate (Status, Metadaten) | JSON Patch Support |
| DELETE | `/keywords/{id}` | Soft Delete | Archiviert Eintrag + Audit Log |
| POST | `/keywords/bulk-import` | Batch Import (CSV/JSON) | Async Job, Fortschritt ID |
| GET | `/keywords/search/suggest` | Autocomplete | Response ≤ 20 Vorschläge |

### CLI (PowerShell & Python)
- `kw-sync import --file keywords.csv --format csv --dry-run`
- `kw-sync diff --env staging --limit 50`
- `kw-cli search --term "Gewerbesteuer" --include-synonyms`
- `kw-cli update-status --keyword-id <id> --status deprecated`

### Sicherheitsanforderungen
- OAuth2 Client Credentials, Scope `keywords.admin` für Mutationen, `keywords.read` für GET.
- Request Logging + Audit Trail.
- Ratenbegrenzung (100 req/min) pro Client-ID.

## Synchronisationsstrategie
- **Vector Store:** Trigger Delta-Sync wenn Keyword/Synonym geändert → Refresh der relevanten Embeddings mittels `VectorRefreshHandler` (Webhook/Event Bus).
- **Graph Store:** Maintainer Job synchronisiert Keyword ↔ Graph Entities (z. B. `TERM_MATCHES` Kanten). Batch nächtlich + Event-basierte Sofort-Updates für kritische Änderungen.
- **Filesystem/Docs:** Optionales Export-Skript generiert CSV/Excel für manuelle Review.

## Migration & Seed
1. Bestandsdaten sammeln (Produkt + Behörden) → Konsolidierte CSV.
2. `seed_keywords.py` Script erstellt Staging-Tabellen (`keywords_raw`).
3. Datenbereinigung (Duplikate, Inkonsistenzen) via SQL/Notebook (QA sign-off).
4. Transformationsskripte in Alembic-Migration integrieren (Versionierte Seeds).
5. Dry-Run in Staging Umgebung (Rollback-Test).

## QA & Monitoring
- **Tests:**
  - Unit-Tests für Repository/Service Layer.
  - Integrationstests (API ↔ DB) mit lokalem Postgres.
  - Contract Tests mit Vector/Graph Services (Mock + Real).
- **Metriken:** CRUD Latenzen, Anzahl aktiver Keywords, Sync-Lag zu Vector/Graph, Import-Fehlerquote.
- **Alerting:** Slack/Webhook bei Sync-Fehlschlägen, DB-Locks, Migration Errors.

## Risiken & Gegenmaßnahmen
| Risiko | Auswirkung | Mitigation |
|--------|------------|------------|
| Uneinheitliche Legacy-Listen | Verzögerte Migration | Frühzeitige Datenprofiling-Workshops, dedizierte Data Steward |
| Komplexe Synonym-Logik (Mehrsprachigkeit) | Modell-Overhead | MVP auf DE/EN begrenzen, Option für Übersetzungs-Tabelle |
| Performance bei Bulk Imports | API Timeout | Async Jobs + Chunking, DB Index-Strategie |
| Abhängigkeit zu Vector Refresh | Doppelarbeit/Inkonsistenz | Event Bus Standardisieren, Retry + Dead Letter Queue |

## Offene Aktionen & Nächste Schritte
| Aufgabe | Owner | Deadline | Status |
|---------|-------|----------|--------|
| Discovery-Workshop terminieren (KW 45, Tag 2) | Product Owner | 01.10.2025 | Offen |
| ERD Draft vorbereiten (`drawio` + `docs/PHASE5_KEYWORD_ERD.png`) | Data Platform | 15.10.2025 | Offen |
| API Blueprint ADR (`docs/PHASE5_KEYWORD_DECISION_ADR.md`) anlegen | Backend Lead | 20.10.2025 | Offen |
| Migration-Skript POC (Staging) | Data Platform | 05.11.2025 | Offen |
| Monitoring Dashboard Requirements definieren | QA Lead | 12.11.2025 | Offen |

## Referenzen
- `docs/PHASE3_GRAPH_SCHEMA.md`
- `docs/PHASE4_VECTOR_NOTES.md`
- `docs/UDS3_VERWALTUNGSARCHITEKTUR.md`
- ADR Templates unter `docs/adr/`
