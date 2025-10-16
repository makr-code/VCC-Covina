# Generische Verwaltungsarchitektur auf Basis von UDS3

> Version: Draft 0.1 · Stand: 25.09.2025  \
> Zweck: Leitfaden für die Einführung eines adaptiven Verwaltungs-Backends, das auf der Unified Database Strategy (UDS3) aufsetzt und gezielt Erweiterungen/Änderungen in späteren Phasen ermöglicht.

---

## 1. Leitprinzipien

1. **Schichten-Trennung:** Klare Trennung zwischen Orchestrierung, fachlicher Verwaltung und Datenpersistenz (Vector / Graph / Relational / File).
2. **Provider-Neutralität:** Alle Integrationen (z. B. Graph-Adapter) implementieren gemeinsame Interfaces (`database_api_base.py`), sodass Backend-Wechsel ohne Prozessbruch möglich sind.
3. **Change-by-Contract:** Änderungen erfolgen über versionierte Verträge (APIs, Events, Schema-IDs) statt impliziter Kopplung.
4. **Governance-First:** Qualitäts-, Sicherheits- und Audit-Funktionen sind integraler Bestandteil jeder Stufe.
5. **Observability & Feedback:** Jede Operation liefert Telemetrie (Timing, Qualität, Status), die sich in Dashboards und Reports widerspiegelt.
6. **Iterative Verfeinerung:** Architektur erlaubt Teil-Deployments (Phase 3 Graph, Phase 4 Vector, …) ohne Big Bang.

---

## 2. Architekturüberblick

```
┌────────────────────────────────────────────────────────────────────┐
│ Nutzer & Fachprozesse (Portale, Behörden, Integrationen)           │
└────────────────────────────────────────────────────────────────────┘
                 │            ▲                             
                 │ Events/API │                             │ Insights
                 ▼            │                             │
┌────────────────────────────────────────────────────────────────────┐
│ Verwaltungs-Service-Layer (dieses Dokument)                        │
│  • Verwaltungs-Kern (Lifecycle-, Policy-, Registry-Service)        │
│  • Governance & Quality (Security, Audit, QA, Compliance)          │
│  • Orchestrierungs-Anschluss (UDS3 Core, Ingestion Pipelines)      │
│  • Erweiterungs-Hubs (Domänen-Module, Prozess-Engines)             │
└────────────────────────────────────────────────────────────────────┘
                 │            ▲
                 │ Commands/  │ Telemetrie
                 │ Plans      │
                 ▼            │
┌────────────────────────────────────────────────────────────────────┐
│ UDS3 Ausführungsschicht                                            │
│  • UnifiedDatabaseStrategy (Plans, Cross-DB Validation)            │
│  • Security-/Quality-/Relations-Layer                              │
│  • Adapter-API (`database_api_*`)                                  │
└────────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│ Datenplattformen                                                   │
│  Vector · Graph · Relational · File · Externe Systeme              │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Komponenten

### 3.1 Verwaltungs-Kern
| Komponente | Aufgabe | Erweiterungspunkt |
|------------|---------|-------------------|
| **Lifecycle Manager** | Verfolgt Status eines Verwaltungsobjekts (z. B. Vorgang, Dokument, Prozess) über alle Phasen. | Neue Lifecycle-States via Konfiguration. |
| **Policy Engine** | Erzwingt Governance-Regeln (Retention, Zugriffsrechte, Qualitäts-Schwellen). | Policies versionieren, Evaluierungs-Hooks bereitstellen. |
| **Registry Service** | Führt Metaregister über Verwaltungsobjekte, verweist auf UDS3-IDs, Versionen, Historie. | Registrierung neuer Objektklassen via Schema-Definition. |
| **Change Orchestrator** | Plant und überwacht Änderungen (z. B. Datenmigration, neue Fachservices). | Change-Playbooks (siehe Abschnitt 5). |

#### Implementierungsstand Verwaltungs-Kern (Stand 2025-09-28)

- **Vorhandene Basis:** `management_core` stellt produktionsnahe Implementierungen für Lifecycle-, Policy- und Registry-Management bereit; Integrationen für Vector-, Graph-, Relational- und Filesystem-Backends sind als eigenständige Services verfügbar und lassen sich über den `ManagementCore` orchestrieren.
- **Erste Kopplungen:** Lifecycle-Übergänge synchronisieren sich bereits mit Registry-Einträgen, optionale Policy-Prüfungen können bei Registrierung und Statuswechsel erzwungen werden, Referenzen zu Backend-IDs werden konsistent abgelegt.
- **Identifizierte Lücken:**
  - AuthZ-Guardrails auf Scope-Basis werden schrittweise ergänzt, um differenzierte Berechtigungen zu ermöglichen.
  - Observability- und Governance-Hooks sind vorbereitet, aber noch nicht mit dem bestehenden Telemetrie-Bus (Saga-/Identity-Metriken) verdrahtet.
  - Konfigurierbare Provisionierung/Dependency Injection für Backend-Services steht aus; derzeit müssen Adapter manuell injiziert werden.
  - Testabdeckung konzentriert sich auf Unit-Niveau der Einzelservices; integrierte Tests und Contract-Prüfungen sind zu etablieren.

**Update 28.09.2025:**
- REST-Zugriff erfolgt jetzt über eine FastAPI-App (`management_core.api.create_app`), abgesichert via Header `X-API-Key`; Endpunkte für Registrierung, Lifecycle-Transition, Objekt-/State-Liste vorhanden.
- Kommandozeilen-Zugriff über `ManagementCoreCLI` ermöglicht Registrieren/Transition/Show/List ohne REST-Hop; Pytests decken beide Pfade ab.

### 3.2 Governance & Observability
- **Security Gateway:** Aggregiert Security Events aus `uds3_security`, ergänzt Verwaltungs-spezifische Logs (z. B. Zuständigkeitsprüfungen).
- **Quality Hub:** Nutzt Scorecards aus `uds3_quality` und verknüpft sie mit Verwaltungskennzahlen (z. B. SLA-Erfüllung).
- **Audit Layer:** Schreibt revisionssichere Journale, unterstützt Export (JSONL) und Reports.
- **Observability Bus:** Standardisiert Metriken (Prometheus/OpenTelemetry), Events und Alerts.

**MC-OBS Planung (Stand 2025-09-28):**
- `management_core.observability` (neu) wird als zentraler Emitter implementiert und über Listener an Lifecycle-, Registry- und Policy-Komponenten angebunden (`LifecycleManager.add_listener`, `RegistryService.add_listener`, `PolicyEngine.add_listener`).
- Ereignisse erzeugen OpenTelemetry-konforme Spans/Metriken mit Namensraum `management_core.*` (z. B. `management_core.lifecycle.transition`, `management_core.policy.result`, `management_core.registry.changed`) und reichen Identitätskontext (`identity_key`, `object_type`) weiter.
- Für Systeme ohne OTEL-Collector stellt das Modul einen austauschbaren Sink bereit (Logger, Event-Bus oder UDS3 Saga Observability), konfigurierbar via ManagementCoreConfig.
- Tests prüfen, dass Hooks bei Transition/Policy-Auswertung/Registry-Änderung ausgelöst werden und Payload-Schema (`event_type`, `object_id`, `metadata`) einhalten.

- **MC-AUDIT Umsetzung (Stand 2025-09-28):**
  - REST-Eingänge erzeugen strukturierte Audit-Events über `ManagementCoreAuditRecorder`. Ereignisse enthalten `action`, `result`, `object_id`, `object_type`, `actor`, `scope`, `request_id` sowie Metadaten zu Fehlern/Transitions und werden kanalisiert (`channel="api"`).
  - Audit-Sink lässt sich via `MANAGEMENT_CORE_AUDIT_SINK` konfigurieren (`logger`, `stdout`, `file`, `sqlite` inkl. `MANAGEMENT_CORE_AUDIT_PATH`); Recorder kann für Governance-Bus/DB erweitert werden.
  - Header `X-Actor` und `X-Request-Id` reichern Audit-Log und Observability um Identitätskontext an; fehlgeschlagene Authentifizierungen werden mit `result="denied"` protokolliert.
  - CLI-Befehle nutzen denselben Recorder (Channel `cli`), generieren Request-IDs on-the-fly und auditieren Erfolg, Fehler sowie Scope-Denials.

**Auth-Scopes (Stand 2025-09-28):**
- API verwendet Default-Scopes (`management:read`, `management:write`, `management:lifecycle:transition`, `management:policies:evaluate`), konfigurierbar über `MANAGEMENT_CORE_DEFAULT_SCOPES`. Fehlende Scopes führen zu HTTP 403 und Audit `result="denied"` (`metadata.reason = "missing_scope"`).
- Token-Validierung bleibt über `X-API-Key`; bei fehlendem/fehlerhaftem Token werden HTTP 401 sowie Audit-Ereignisse `action="auth"`, `result="denied"` geschrieben.
- CLI übernimmt identische Scopes (`MANAGEMENT_CORE_CLI_SCOPES`, `MANAGEMENT_CORE_CLI_ACTOR`) und erlaubt über `MANAGEMENT_CORE_CLI_SCOPE_MAP` oder `MANAGEMENT_CORE_TOKEN_SCOPES` eine benutzerspezifische Scope-Zuweisung (JSON-Mapping). Scope-Fehler erzeugen `PermissionError` und Audit `result="denied"`.
- Token-Registry persistent: `administrative_token_scopes` wird via `TokenScopeRegistry`/`TokenScopeCache` geladen (`MANAGEMENT_CORE_TOKEN_DB_PATH`, Fallback `./var/management_core_tokens.db`), Hot-Reload erfolgt über Dateimtime oder TTL (`MANAGEMENT_CORE_TOKEN_RELOAD_SECONDS`). CLI stellt `tokens list|sync` bereit und kann Actor-Scopes über `actor_hint` aktualisieren.

#### Identitätszentrierte Telemetrie (Neu)
- **Schemaerweiterung:** Relationale Backends erhalten die Tabellen `administrative_identity_metrics` und `administrative_identity_traces` inklusive Indexierung auf `identity_key`, `stage` bzw. `trace_id`.
- **Instrumentierung:** `SagaDatabaseCRUD` erzeugt für jede CRUD-Operation identitätsbezogene Metriken (`*.attempt`, `*.success`, `*.error`, `*.governance_blocked`, `*.duration_ms`, optionale `*.chunk_count`) und Trace-Events (Stage, Status, Payload-Auszug). Governance-Checks markieren blockierte Operationen explizit.
- **Saga-Verankerung:** `UDS3SagaOrchestrator` schreibt Audit-/Metrik-Events mit `saga_name`, `identity_key` und `document_id`, sodass Sagas auf Personen- bzw. Dokumentkontext rückführbar bleiben; Tests (`tests/test_saga_orchestrator.py`) validieren die neuen Spalten.
- **Kontext-Anreicherung:** `UnifiedDatabaseStrategy` füllt Saga-Kontexte vor Ausführung mit `identity_key`, `identity_uuid` und relationalen Referenzen aus Security-/Metadata-Schritten, wodurch Start-Events bereits identitätsgebundene Telemetrie liefern und `document_mapping` Identity-Daten versioniert.
- **Statusmodell:** Der Trace-Status unterscheidet `success`, `error` und `governance_blocked` und erlaubt dadurch Dashboards, Policy-Verletzungen separat auszuwerten.
- **Tracing-Fluss:** Die Telemetrie wird backendagnostisch sammelbar (Vector/Graph/Relational/File), sodass Dashboards Identitäten über mehrere Speicher hinweg verfolgen können.
- **Tests:** `tests/test_saga_crud.py` validiert, dass Observability-Daten bei Relational-Operationen geschrieben werden (Happy Path, Fehlerfall, Governance-Block) und schützt die Schema-Kontrakte.

### 3.3 Erweiterungs-Hubs
- **Domänen-Module:** Spezifische Verwaltungsbereiche (Bauwesen, Gewerbe, Umwelt). Werden über API-Verträge eingebunden.
- **Process Engines:** Binden `uds3_process_mining` und Folgeprozessoren ein (z. B. BPMN/EPK).
- **Analytics & Insights:** Verwendet `uds3_strategic_insights_analysis` und Datenprodukte in Vector/Graph/Relational DBs.

### 3.4 Vector-DB Management (Neu in Draft 0.1)
- **Modul:** `management_core.vector_management.VectorManagementService`
- **Aufgabe:** Abstrakte Verwaltungs- und Governance-Schicht für Vektor-Indizes (z. B. Chroma, Pinecone). Koordiniert Collection-Registrierung, Metadaten-Anreicherung via UDS3-Strategie sowie Lifecycle-Hooks.
- **Konfigurierbarkeit:** `VectorManagementConfig` erlaubt Auto-Provisioning, Dimension-Validierung und Metadaten-Overrides.
- **Erweiterungspunkte:** Hooks `on_before_store`, `on_after_store`, `on_failure` erlauben spätere Policy-/Observability-Einbindung. Collections lassen sich über `VectorCollectionDefinition` versionieren.
- **Nächste Schritte:** Siehe Kapitel 9 (P1–P4) sowie Tests in `tests/test_vector_management_service.py`.

---

## 4. Daten- & Kontrollflüsse

1. **Eingang** (z. B. digitales Dokument, Vorgang aus externem System) gelangt via Ingestion-Pipeline zu UDS3 Core.
2. **UDS3 Core** erzeugt Pläne für Vector/Graph/Relational/File und führt Security- & Quality-Prüfungen durch.
3. **Verwaltungs-Kern** registriert den Vorgang, ordnet ihn einem Lifecycle zu und speichert Referenzen auf UDS3 IDs.
4. **Governance-Ebene** überwacht Policies: Sind Qualitäts-Mindestwerte erfüllt? Bestehen Sicherheitsauflagen?
5. **Domänenerweiterungen** können zusätzliche Metadaten einbringen, automatisierte Prozessschritte auslösen oder externe Systeme informieren.
6. **Feedback Loop:** Telemetrie fließt an Observability Bus → Dashboards, Alerts, Entscheidungsgrundlagen.

---

## 5. Change-by-Contract Mechanismus

| Schritt | Beschreibung | Artefakte |
|---------|--------------|-----------|
| 1. Change Intake | Änderungsidee erfassen, betroffene Domänen/Objekte benennen. | Change Ticket (z. B. `changes/CHG-####.md`). |
| 2. Impact Analyse | Betroffene Verträge (APIs, Schemas, Policies) identifizieren. | Decision Log Update (`docs/PHASE4_DECISIONS.md`). |
| 3. Contract Draft | Neue/angepasste Verträge definieren (Version, Fallback, Deprecation). | API-/Schema-Spezifikation. |
| 4. Pilot Deployment | Feature Flags / Shadow Mode / Canary. | Konfigurationsdateien, Tests. |
| 5. Rollout & Monitoring | Aktivierung gemäß Policy, Telemetrie überwachen. | Dashboard, Alert-Konfiguration. |
| 6. Review & Learnings | Wirksamkeit prüfen, Lessons Learned dokumentieren. | Review-Protokoll. |

**Versionierung:** Jede Schnittstelle erhält SemVer + Ablaufdatum. Binding über `Contract Registry` (Teil des Registry Service).

---

## 6. Schnittstellenübersicht

| Schnittstelle | Richtung | Technologie | Beschreibung |
|---------------|----------|-------------|--------------|
| **Ingestion ↔ Verwaltungs-Kern** | Pull (REST/Queue) | JSON/Events | Übergibt neue Dokumente/Vorgänge + Status. |
| **Verwaltungs-Kern ↔ UDS3 Core** | Command + Callback | Python SDK / REST | Startet `create_secure_document`, verarbeitet Resultate & IDs. |
| **Verwaltungs-Kern ↔ Governance** | Events | Event Bus (Kafka/AMQP) | Lifecycle Events, Policy-Verletzungen, Quality Alerts. |
| **Verwaltungs-Kern ↔ Domänen-Module** | REST/gRPC | JSON/Proto | Veröffentlicht Registry-Events, empfängt Fachentscheidungen. |
| **Observability** | Push/Pull | OpenTelemetry, Prometheus | Einheitliche Metriken und Logs. |

---

## 7. Erweiterungs- & Verfeinerungspfade

1. **Neue Domänenmodule:** Registrieren eigenen Handler, Policies und Observability-Kennzahlen.
2. **Backend-Wechsel:** Adapter über `database_api_base.py` austauschen (z. B. Neo4j → ArangoDB) ohne Verwaltungs-Kern anzupassen.
3. **Policy-Erweiterungen:** Neue Regeln per Konfiguration, Policy-Engine wertet sie per DSL/Skript aus.
4. **Lifecycle-Verfeinerung:** Zusätzliche Stati über Registry + Dokumentation definieren, Tasks in Pipelines erweitern.
5. **Qualitätsmetriken:** Scorecards erweitern, `uds3_quality` liefert zusätzliche Dimensionen. Verwaltungs-Kern übernimmt Routing/Thresholds.
6. **Change Automation:** Playbooks in `changes/` ablegen, Orchestrator kann wiederkehrende Tätigkeiten automatisieren.

---

## 8. Dokumentation & Governance

- **Quelle:** Dieses Dokument gilt als Single Source of Truth für die Verwaltungsarchitektur.
- **Versionierung:** Änderungen per Pull Request, mit Decision Log (`docs/PHASE4_DECISIONS.md`) und ToDo-Updates.
- **Verbindung zu bestehenden Dokumenten:**
  - `docs/INGESTION_ARCHITEKTUR.md` → beschreibt Pipeline-/Job-Ebene.
  - `docs/PHASE3_GRAPH_SCHEMA.md` → definiert Graph-Layer.
  - `docs/toDo.md` → Roadmap/Sprintplanung (Phasen 3–6).

---

## 9. Nächste Schritte (Hands-On)

1. Verwaltungs-Kern als Python-Modul entwerfen (`management_core/`), inkl. Lifecycle-, Policy- und Registry-Service.
2. Contract Registry (SemVer/Dokumentation) implementieren und an Change-Prozess anbinden.
3. Observability Bus definieren (Metrics + Logging + Alerts) und in Worker/Handler einbauen.
4. Proof-of-Concept: Einen vollständigen Vorgang durch Ingestion → UDS3 Core → Verwaltungs-Kern → Governance testen.
5. Dokumentation kontinuierlich pflegen (Lessons Learned, neue Module) und mit Release-Zyklus verzahnen.

### 9.1 Umsetzungskalender (KW 39–46 · Q4/2025)

| KW | Fokus | Kern-Deliverables | Verantwortlich | Definition of Done |
|-----|-------|-------------------|----------------|--------------------|
| 39 | Kick-off & Scope-Freeze | Kick-off-Agenda, Teilnehmerliste, beschlossene Vision & Scope Statement | Programmleitung + Product | Kick-off-Notiz im Projekt-Repo (`docs/PHASE4_DECISIONS.md`), Jira-Epics erstellt |
| 40 | Management-Kern MVP | `management_core/` Module (Lifecycle, Policy, Registry) refaktoriert, Basistests grün | Core Platform Team | Tests (`pytest management_core`) grün, API-Signaturen dokumentiert |
| 41 | API & Auth-Design | OpenAPI-Spezifikation, AuthN/AuthZ-Konzept, Reverse-Proxy Draft | Platform + Security | OpenAPI YAML im Repo, Security Review-Protokoll abgelegt |
| 42 | Contract Registry Alpha | SemVer-Registry Modul, CLI `mc-contracts`, ADR-Automation-Skript | Architecture Guild | CLI-Demo, mindestens 3 Contracts registriert, HowTo im `docs/management_core/` |
| 43 | Observability Bus Foundations | OTEL Collector Config, Metrics-Schema, Dashboard-Wireframes | SRE + DataOps | Collector im Dev-Cluster lauffähig, Dashboard-Mockups im Design-Repo |
| 44 | Observability Integration | Handler/Worker senden Events, Alerts in Test-Workspace, Runbooks | SRE + Core | Smoke-Test `tests/test_observability_bus.py` grün, Runbook in `docs/management_core/` |
| 45 | End-to-End PoC Build | End-to-End-Flow orchestriert, Synthetic Dataset, Governance-Demo | Cross Squad | PoC Demo-Skript (`poC_end_to_end.py`), Abnahmeprotokoll |
| 46 | Lessons Learned & Rollout Plan | Retro-Dokument, Release-Checklist, Rollout-Kommunikation | Programmleitung | Retro-Notiz veröffentlicht, Rollout-Plan im README |

### 9.2 Arbeitspaket-Backlog (priorisiert)

1. **MC-CORE-01** – Lifecycle- & Policy-Service Hardening  
  *Tasks:* Monitoring Hooks, Retry-Strategie, Config-Validation.  
  *Abhängigkeiten:* Kick-off (KW39).  
  *DoD:* Alle kritischen Pfade mit Integrationstests (`tests/management_core/test_lifecycle.py`).
2. **MC-CORE-02** – Registry REST API + Auth  
  *Tasks:* Token-basierte AuthZ, Scope-Mapping, Audit Log.  
  *Abhängigkeiten:* MC-CORE-01.  
  *DoD:* OpenAPI publiziert, Security Sign-Off dokumentiert.
3. **MC-CONTRACT-01** – Contract Registry CLI & SemVer Lifecycle  
  *Tasks:* `mc-contracts init|publish|deprecate`, Git Hooks.  
  *Abhängigkeiten:* API-Design (KW41).  
  *DoD:* CLI mit Unit- & Smoke-Tests, Beispiel-Contract im Repo.
4. **MC-OBS-01** – Observability Schema & Collector  
  *Tasks:* OTEL-Resource Schema, Exporter Config, Logging-Konventionen.  
  *Abhängigkeiten:* MC-CORE-02.  
  *DoD:* Collector akzeptiert Events, Grafana-Dashboard zeigt Kernmetriken.
5. **MC-POC-01** – Verwaltungs-PoC Flow  
  *Tasks:* Szenario-Skripte, Synthetic Data, Governance Checkpoints.  
  *Abhängigkeiten:* MC-OBS-01, MC-CONTRACT-01.  
  *DoD:* Demo-Script + Screencast, Feedback von Stakeholdern protokolliert.

### 9.3 Risiko- & Mitigationsübersicht

| Risiko | Auswirkung | Eintrittswahrscheinlichkeit | Mitigation |
|--------|-------------|----------------------------|------------|
| Ressourcenüberlastung in KW 41 (Security Review) | Verzögerung des Contract Registry Alpha | Mittel | Review frühzeitig anfragen, Security-Vertreter im Kick-off fest einplanen |
| OTEL Collector Performance | Verfälschte Metriken im PoC | Niedrig | Lasttests in KW43, Fallback auf lokales Logging vorbereitet |
| PoC-Datensätze unvollständig | Demo verliert Aussagekraft | Mittel | Dedicated DataOps-Verantwortliche ab KW42, eskalieren in Weekly |
| Tooling für ADR-Automation instabil | Verzögerter Contract Release | Mittel | Pilot auf Sample-Repo (KW42), Rollback-Skript bereitstellen |

### 9.4 Reporting & Artefakte

- Weekly Status (Slack + `docs/PHASE4_DECISIONS.md` Update) jeden Donnerstag 14:00.
- Diese Artefakte sind verpflichtend zu pflegen:
  - **Kick-off Notes:** `docs/PHASE4_DECISIONS.md` Kapitel "Management Layer".
  - **Contract Registry Cookbook:** `docs/management_core/contract_registry.md` (neu anzulegen in KW42).
  - **Observability Runbook:** `docs/management_core/observability_runbook.md` (Entwurf KW43, final KW44).
  - **PoC Demo Script & Dataset:** `examples/management_core/poc/` inkl. README.
- Fortschritt spiegelt sich in `docs/toDo.md` (Checkbox-Status) und im CHANGELOG wider.

---
*Ende Draft 0.1*