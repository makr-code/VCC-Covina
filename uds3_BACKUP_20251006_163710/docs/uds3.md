# UDS3 Systembeschreibung (Unified Database Strategy v3.0)

> Version: Draft 0.1 • Datum: 24.09.2025  
> Scope dieses Dokuments: Technische Gesamtübersicht der im `uds3` Verzeichnis vorhandenen Module, ihre Rollen, Datenflüsse, Interaktionen und Anschlussfähigkeit an den neuen Ingestion-Core.

---
## 1. Mission & Kontext
Die *Unified Database Strategy v3.0 (UDS3)* bildet einen domänenspezifischen Orchestrierungs- und Qualitätsrahmen für Verwaltungs- und Rechtsdokumente. Ziel ist eine konsistente, nachvollziehbare und auditierbare Verarbeitung über drei primäre Datenbank-Perspektiven:

- Vector DB: Semantische Repräsentation (Embeddings, Chunks, Ähnlichkeitssuche)
- Graph DB: Beziehungen, Hierarchien, Prozess- und Rechtsstrukturen
- Relationale DB: Strukturierte Metadaten, Indizes, Statistiken, Qualitätsmetriken

Ergänzt um Security- und Quality-Layer (Integrität, Compliance, Qualitäts-Score) sowie ein Relations-Framework (Neo4j Schema + Almanach) für konsistente Kanten-Typen.

---
## 2. Modulübersicht (High-Level)
| Modul | Rolle | Kernfunktion(en) |
|-------|-------|------------------|
| `uds3_core.py` | Strategische Hauptlogik | Processing-Pläne, CRUD-Pläne, Cross-DB Mapping, Security/Quality Integration |
| `uds3_security.py` | Sicherheits-Framework | Hashing, UUID, Integrity Verification, Secure Deletion, Audit Logging |
| `uds3_quality.py` | Qualitäts-Framework | 7D-Qualitätsmetrik, Scoring, Cross-DB-Validierung, Reports, Trends |
| `uds3_relations_core.py` | Relations / Neo4j Backend | Schema-Erstellung, Indizes, Relationserstellung, Konsistenzprüfung |
| `uds3_process_mining.py` | Prozess-/Workflow-Extraktion | Regex-basierte Prozessschritt-, Rollen-, Entscheidungsanalyse |
| `uds3_api_backend.py` | Wissens- & Prozess-API | LLM-gestützte Prozessanalyse, Knowledge Base, Vorschläge |
| `uds3_validation_worker.py` | (Angedeutet) Validierung | Plausibilitäts-, Struktur- oder Cross-Checks (Erweiterungspunkt) |
| `uds3_document_classifier.py` | Dokumentklassifikation | (Heuristiken / ML Platzhalter) Kategorisierung für Routing |
| `uds3_enhanced_schema.py` | Erweitertes Schema | Aggregierte Schema-/Strukturdefinitionen (Meta-Schicht) |
| `uds3_schemas.py` / `uds3_vpb_schema.py` | Schemata | Strukturierte Definitionen für externe/VPB-Objekte |
| `uds3_core_geo.py` / `uds3_geo_extension.py` / `uds3_4d_geo_extension.py` | Geo-Erweiterungen | Räumliche Kontexte, 4D-Zeit/Geo-Bezüge |
| `uds3_quality_security` (`uds3_security_quality.py`) | Kombi-Layer | Möglicher Brückencode Security ↔ Quality |
| `uds3_process_export_engine.py` | Exportlogik | Prozess-/Analyse-Ergebnisse in Zielsysteme |
| `uds3_follow_up_orchestrator.py` | Folgeprozesse | Trigger für nachgelagerte Operationen |
| `uds3_collection_templates.py` | Sammlungs-Templates | Vorlagen für Collections / Batch-Strukturen |
| `uds3_complete_process_integration.py` | Gesamtintegration | Orchestriert End-2-End Prozess (Meta-Pipeline) |
| `uds3_strategic_insights_analysis.py` | Strategische Analyse | Höhere Auswertungen über Bestände |
| `uds3_admin_types.py` | Typen / Enums | Zentrale Verwaltungstypen (Dokumentklassen etc.) |
| `uds3_epk_process_parser.py` / `uds3_bpmn_process_parser.py` | Parser | Alternative Prozessmodell-Importer |

---
## 3. Kern-Domänenschichten
### 3.1 Security Layer (`uds3_security`)
Zentrale Verantwortlichkeiten:
- Generierung sicherer Document-IDs (UUID + Hash + HMAC + Salt)
- Integritätsverifikation (Hash, Checksum, HMAC)
- Audit Logging (Operationen, Prüfungen, Deletion)
- Konfigurierbare Security Level (PUBLIC → CONFIDENTIAL)
- Secure Deletion Workflow (Audit + Bestätigung)

Integrationstrigger: Wird beim Anlegen neuer Dokumente aus `uds3_core` aufgerufen (`create_secure_document`). Gibt `security_info` zurück für Mapping und spätere Validierungen.

### 3.2 Quality Layer (`uds3_quality`)
- 7 Dimensionen (Completeness, Consistency, Accuracy, Validity, Uniqueness, Timeliness, Semantic Coherence)
- Gewichtetes Gesamtscoring + Issues + Empfehlungen
- Cross-DB Qualitätsvalidierung (ID, Hash, Titel, Konsistenz)
- Reports (Verteilung, häufige Issues, Action Items)
- Trendanalyse (Regressionsabschätzung / Richtung)

Eingebunden nach erfolgreichen CRUD/CREATE Operationen zur Bewertung der Datenlage.

### 3.3 Relations Layer (`uds3_relations_core`)
- Nutzt einen Relations-Almanach (Tabelle definierter Relationstypen mit Eigenschaften)
- Erstellt Neo4j Schema (Constraints, Indizes, Fulltext, Composite)
- Erweitert Relations mit UDS3-spezifischen Metadaten (Priorität, Performance Weight)
- Bietet `create_relation` / inverse Relation Erzeugung
- Konsistenzvalidierung (unbekannte Relationstypen, Dokument ohne Chunks, Orphans)

### 3.4 Core Strategy (`uds3_core`)
- Erzeugt optimierte DB-spezifische Operationpläne (Vector/Graph/Relational)
- CRUD Operation Plans (create/update/delete/read/batch)
- Sicherheits-/Qualitätsintegration (SecurityManager & QualityManager Hooks)
- Synchronisationspläne (Phasen & Sequenzen)
- Konfliktlösung (timestamp-based / authoritative_source)
- Cross-DB Validierung & Mapping (`document_mapping`)

### 3.5 Process & Workflow Mining (`uds3_process_mining`)
- Regex-basierte Extraktion von Prozessschritten, Rollen, Entscheidungen
- Ableitung von Automatisierungspotenzial (HIGH/MEDIUM/LOW)
- Graph-fähige Knoten/Beziehungslisten (z.B. für Neo4j Import)

### 3.6 API Backend & Knowledge (`uds3_api_backend`)
- Enthält verwaltungsrechtlich orientierte Knowledge Base (Domänen: Bau, Gewerbe, Umwelt, Sozial)
- LLM-basierte Prozessanalyse (via Ollama) mit Fallback-Regellogik
- Liefert: Komplexität, Compliance-Issues, Optimierungsvorschläge, Risikoeinschätzung
- Vorschlagsgenerator für fehlende Prozess-Elemente (Legal Checkpoints)

---
## 4. Datenflüsse (vereinfachtes Sequenzmodell)
1. Ingestion (geplant via neuer Core-Pipeline) liefert Datei + Extrakt (Chunks, Metadaten)
2. `uds3_core.create_secure_document`:
   - Security-ID erzeugen → DB Operationen planen (vector/graph/relational)
   - Mock/Real Execution (später austauschbar) → Ergebnisse sammeln
   - Quality Score berechnen → Issues / Empfehlungen
3. Relations-Anreicherung (optional):
   - `create_relation` für PART_OF / CONTAINS_CHUNK / semantische oder rechtliche Verknüpfungen
4. Process Mining (falls Dokument Prozessinstruktion) → Graph-Knoten + Relationen
5. API Backend kann Analyse-/Optimierungslayer für Prozessdaten nutzen
6. Cross-DB / Cross-Layer Validierungen (Consistency + Quality + Security)

### 4.1 Neues File-Storage Backend (Backend #4)
Motivation: Nicht alle Artefakte (Original-PDF, gescannte Bilder, Anlagen, Binärformate) eignen sich für direkte Speicherung in Vector/Graph/Relational-DBs. Das File-Storage Backend ergänzt einen persistenten, referenzierten Speicherort.

Fokus & Prinzipien:
- Single Source of Truth für Originaldatei (Auditing, Re-Prozessierung)
- Versionierung (neue Datei-Versionen bei Updates archivieren statt Überschreiben)
- Integritätsmetadaten (Hash, Größe, optional Signatur) für spätere Verifikation
- Retention & Archiv-Strategien (Regulatorik, Legal Hold)

Implementierung (aktueller Stand Mock in `uds3_core`):
- Rolle ergänzt in `database_roles[DatabaseRole.FILE]`
- Schema via `_create_file_storage_schema()` (Retention, Versioning, Integrity Settings)
- Operationsgenerator `_create_file_storage_operations()` erzeugt:
   - `store_original_file_reference`
   - `store_derivative_manifest` (z.B. Text-Extraktion)
- Execution Helper `_execute_file_storage_create()` + (Update/Delete/Read Platzhalter)

CRUD Auswirkungen:
- CREATE: Sichert Referenz + Derivat-Manifest
- READ: Liefert File Info + Versionsliste
- UPDATE: Plant neue Version (Versionierung statt Überschreiben)
- DELETE: Soft (Archiv) vs. Hard (physische Entfernung) → Rollback möglich

Validierungserweiterung:
- Cross-DB Validation erweitert um File-Check (Operationserfolg + referenzierte ID)
- Quality Layer kann künftig Verfügbarkeit/Lesbarkeit prüfen

Nächste Ausbaustufen:
- Physische Speicherung (lokal / S3 / Azure Blob) via Adapter Interface
- Integritäts-Rehash Cron (periodic_rehash_days)
- Verschlüsselungsoption (at rest) + Access Control Layer
- Streaming-Extraktion (große Dateien chunk-basiert extrahieren) zur Speicherschonung

---
## 5. Architektur-Schnittstellen zum neuen Ingestion Core
| Ingestion Element | UDS3 Anschluss | Bemerkung |
|------------------|---------------|-----------|
| File-Level Job (core_ingest) | Übergibt Pfad & Basismetadaten | Potenzieller Hook: Security/Hash sofort |
| Transform Job (core_transform) | Liefert normalisierte Struktur | Grundlage für Chunking / Vektorisierung |
| Export Job (core_api_export) | Könnte `uds3_core.create_secure_document` anstoßen | Übergang in UDS3 CRUD Flow |
| Chunk-Level (zukünftig) | `vector` und `graph` Operationserweiterung | PART_OF / CONTAINS_CHUNK Relationen |

Empfohlene Erweiterung: Ein neuer Handler `uds3_secure_create` der nach `core_transform` den Secure-Create Prozess (Security + Vector + Graph + Relational + Quality) initiiert.

---
## 6. Qualitäts- & Sicherheits-Metrik Übersicht
| Dimension | Quelle | Typ | Beispiel / Check |
|-----------|--------|-----|------------------|
| Completeness | QualityManager | Score | Pflichtfelder vorhanden? |
| Consistency | QualityManager / Cross-DB | Score | ID/Hash/Titel überall gleich |
| Accuracy | Regeln (Länge) | Score | Inhalt plausible Länge |
| Validity | Schema / Dateiendung | Score | Endung erlaubt, ID-Format |
| Uniqueness | ID Modell | Bool/Score | Kollisionen? (später DB) |
| Timeliness | Timestamp | Score | Alter < definierter Schwellen |
| Semantic Coherence | Heuristik | Score | Titel-Content Überdeckung |
| Integrity | SecurityManager | Bool | Hash/HMAC vergleichen |
| Auditability | SecurityManager | Logeinträge | Operation protokolliert |

---
## 7. Erweiterungspunkte & Roadmap
### Kurzfristig
- Handler `uds3_secure_create` in neuer Pipeline registrieren
- Tatsächliche DB Adapter-Schichten (statt Mock) abstrahieren (Interface Layer)
- Mapping File → Chunks → Graph-Knoten standardisieren (ID-Strategie harmonisieren)

### Mittelfristig
- Bidirektionale Synchronisation (Change Events → Recompute Embeddings / Graph Aktualisierung)
- Konsolidierter Validation Runner (Security + Quality + Relations in einem Exec-Pfad)
- Capability-basiertes Scheduling (Handler melden `provides` / `consumes` → orchestrierter Graph)

### Langfristig
- Policy Engine (Retention, Redaction, Access Windows)
- Adaptive Qualitätsmodelle (ML-basiert)
- Echtzeit Relation Impact Analysis (Traversalkosten / Relevanz-Degeneration)

---
## 8. Risiken & Technische Schulden
| Bereich | Risiko | Gegenmaßnahme |
|---------|--------|---------------|
| Mock Implementierungen | Diskrepanz zur realen DB | Layer klare Interfaces, Adapters implementieren |
| Hart verdrahtete Pfade | Geringe Portabilität | Konfigurationsobjekt / ENV nutzen |
| Fehlende Tests | Regressionsgefahr | Pytests für Security/Quality/Relations Kernfälle |
| Fehlende Chunk-Persistenz | Verlust semantischer Tiefe | Frühe Persistenzschicht priorisieren |
| LLM Abhängigkeit (Ollama) | Nicht verfügbar / Timeout | Fallback + Caching |

---
## 9. Glossar (Auszug)
| Begriff | Bedeutung |
|---------|-----------|
| UDS3 | Unified Database Strategy Version 3.0 |
| Almanach | Sammlung definierter Relationstypen + Metadaten |
| Chunk | Teilsegment eines Dokuments für semantische Verarbeitung |
| Processing Plan | Abgeleiteter Satz DB-spezifischer Operationen |
| Quality Score | Aggregierter gewichteter Qualitätsindex |
| Secure Document ID | Kombinierte UUID + Hash + HMAC Identifikation |

---
## 10. Nächste konkrete Schritte (Hands-On)
1. Pipeline-Erweiterung: Neue Task `uds3_secure_create` implementieren → ruft `UnifiedDatabaseStrategy.create_secure_document` auf.
2. Ergebnis-Persistenz: Ergebnisse (vector/graph/relational) in standardisierte Output-Struktur schreiben.
3. Relations-Pilot: Nach Secure-Create automatisch `CONTAINS_CHUNK` Relationen anlegen (Mock → Neo4j Adapter austauschbar).
4. Quality Report Batch: Sammlung mehrerer `quality_score` Ergebnisse in wöchentlichem Report.
5. Security Audit Export: Audit-Log serialisieren (JSONL) zur externen Revisionsprüfung.

---
*Ende des Dokuments – Draft 0.1*
