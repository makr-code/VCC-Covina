# UDS3 Identity Service – Architekturentwurf

*Stand: 26.09.2025*

Dieses Dokument beschreibt die Zielarchitektur für den neuen Identity-Service, der das duale Identitätskonzept (UUID ↔ Aktenzeichen) und das persistente Cross-DB-Mapping innerhalb der UDS3-Plattform umsetzt.

## 1. Ziele
- **UUID als technische Primär-ID** für alle Vorgänge ab dem ersten Pipeline-Schritt.
- **Aktenzeichen als fachliche ID**, die über den Identity-Service registriert, validiert und an die UUID gebunden wird.
- **Persistentes Mapping** der beteiligten Datenbank-IDs (Vector, Graph, Relational, File) zur UUID.
- **Transaktionssichere Ablage** aller Identitätsdaten in der relationalen Datenbank (ACID, Auditierbarkeit).

## 2. Datenbank-Schema
Alle Tabellen werden in der relationalen DB angelegt und beim Start des Identity-Service automatisch migriert.

### 2.1 `administrative_identities`
| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `uuid` | TEXT PRIMARY KEY | Technische UUID (canonical, in lower-case, ohne Klammern) |
| `aktenzeichen` | TEXT NULLABLE | Fachliches Aktenzeichen (optional bis zur Extraktion, mehrere UUIDs möglich) |
| `status` | TEXT | z. B. `registered`, `pending`, `retired` |
| `source_system` | TEXT | Quelle der UUID (z. B. `ingestion.scanner`) |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Erstellt |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Aktualisiert |

### 2.2 `administrative_identity_mappings`
| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `uuid` | TEXT PRIMARY KEY REFERENCES administrative_identities(uuid) | Referenz auf UUID |
| `aktenzeichen` | TEXT | Duplicate für schnelle JOINs (INDEX) |
| `relational_id` | TEXT | Primär-ID in relationaler DB |
| `graph_id` | TEXT | Key im Graph-Backend |
| `vector_id` | TEXT | Collection/Item-ID im Vector-Backend |
| `file_storage_id` | TEXT | Key im File/Object-Store |
| `metadata` | TEXT | JSON-Blob mit Zusatzinfos |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Aktualisiert |

### 2.3 `administrative_identity_audit`
| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `audit_id` | TEXT PRIMARY KEY | UUID v4 |
| `uuid` | TEXT | Betroffene Identity |
| `action` | TEXT | `create_uuid`, `register_aktenzeichen`, `map_backend_id`, … |
| `actor` | TEXT | Benutzer/Service |
| `details` | TEXT | JSON |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Zeitpunkt |

Zusätzliche Indizes:
- `idx_aktz_lookup` auf `administrative_identities(aktenzeichen)`.
- `idx_mapping_relational`, `idx_mapping_graph`, `idx_mapping_vector`.

## 3. Service-Schnittstellen (Python)
Der Dienst wird als Singleton (`get_identity_service()`) bereitgestellt und verwendet den Relational Backend Adapter über den Database Manager.

```python
class UDS3IdentityService:
    def generate_uuid(self, source_system: str, aktenzeichen: str | None = None) -> IdentityRecord:
        """Erzeugt eine neue UUID, legt sie in `administrative_identities` an und kann optional ein Aktenzeichen vorregistrieren."""

    def register_aktenzeichen(self, uuid: str, aktenzeichen: str, actor: str = "system") -> IdentityRecord:
        """Schreibt das Aktenzeichen in die Identity-Tabelle (Normalisierung, keine Eindeutigkeitsprüfung)."""

    def resolve_by_uuid(self, uuid: str) -> IdentityRecord | None:
        """Lädt vollständige Identitäts- und Mapping-Informationen."""

    def resolve_by_aktenzeichen(self, aktenzeichen: str) -> IdentityRecord | None:
        """Lookup per Aktenzeichen (case insensitive)."""

    def bind_backend_ids(self, uuid: str, *, relational_id=None, graph_id=None, vector_id=None, file_storage_id=None, metadata=None) -> IdentityRecord:
        """Upsert in `administrative_identity_mappings` inkl. Audit-Eintrag."""

    def record_audit(self, uuid: str, action: str, details: dict, actor: str = "system") -> None:
        """Persistentes Audit-Logging."""
```

### DTO / Rückgabestruktur
```python
@dataclass
class IdentityRecord:
    uuid: str
    aktenzeichen: str | None
    status: str
    source_system: str | None
    mappings: dict[str, str | None]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

## 4. Integrationspunkte
1. **Ingestion (Scanner/File Events):** nutzt `generate_uuid()` beim ersten Kontakt. Optional `register_aktenzeichen()` falls extrahiert.
2. **UDS3 Core (`UnifiedDatabaseStrategy`):** ersetzt `_generate_document_id` durch Identity-Service-Aufruf; `create_secure_document` ruft `bind_backend_ids()` nach erfolgreichen DB-Operationen.
3. **Saga-Orchestrator (Folgeschritt):** referenziert Identity-Service für Saga-States.
4. **Relationale Schema-Definition:** `uds3_core._create_relational_schema` referenziert neue Tabellen.

## 5. Fehler- und Konfliktbehandlung
- **Aktenzeichen:** Mehrere Identitäten können dasselbe Aktenzeichen tragen; der Service erzwingt keine Eindeutigkeit.
- **Transaktionen:** Identity-Service arbeitet (wo verfügbar) mit DB-Transaktionen; bei SQLite Nutzung von `BEGIN IMMEDIATE`.
- **Soft Deletes:** Identity kann mit Status `retired` markiert werden, um fachliche Historien abzubilden.

## 6. Offene Punkte / Folgearbeit
- Saga-Integration & Orchestrator Persistenz.
- REST/gRPC-Expose für externe Systeme.
- Batch-Migrationsskript für bestehende Dokumente.

---
*Vorbereitet für die Implementierung durch GitHub Copilot (Assistenz).*