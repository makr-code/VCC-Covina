# UDS3 Dynamic Naming Strategy - Dokumentation

## Überblick

Das **UDS3 Dynamic Naming Strategy System** ermöglicht kontextbasierte, dynamische Namensgebung für Collections, Tabellen, Node-Labels und Buckets basierend auf:

- **Behörden-Kontext**: Bund, Land, Kommune, Amt/Behörde
- **Rechtsgebiet**: Baurecht, Umweltrecht, Planungsrecht, etc.
- **Dokumenttyp**: Genehmigungen, Bescheide, Pläne, Gesetze, etc.
- **Processing-Stage**: Draft, Active, Archive
- **Access-Level**: Public, Internal, Confidential

## Hauptkomponenten

### 1. `uds3_naming_strategy.py`

Kernsystem mit folgenden Klassen:

#### `OrganizationContext`
- **Zweck**: Repräsentiert hierarchischen Behörden-Kontext
- **Attribute**:
  - `level`: AdminLevel (FEDERAL, STATE, MUNICIPAL)
  - `state`: Bundesland (z.B. "nrw", "bayern")
  - `municipality`: Kommune (z.B. "münster", "köln")
  - `authority`: Behörde (z.B. "bauamt", "umweltamt")
  - `department`: Abteilung (optional)
  - `domain`: AdminDomain (BUILDING_LAW, ENVIRONMENTAL_LAW, etc.)
  - `legal_areas`: Liste von Rechtsgebieten

**Beispiel**:
```python
from uds3_naming_strategy import OrganizationContext
from uds3_admin_types import AdminLevel, AdminDomain

org_context = OrganizationContext(
    level=AdminLevel.MUNICIPAL,
    state="nrw",
    municipality="münster",
    authority="bauamt",
    domain=AdminDomain.BUILDING_LAW,
)
```

#### `NamingStrategy`
- **Zweck**: Generiert Namen für verschiedene Datenbank-Typen
- **Methoden**:
  - `generate_vector_collection_name()`: Vector-DB Collections
  - `generate_relational_table_name()`: SQL-Tabellen
  - `generate_graph_node_label()`: Graph-DB Node-Labels
  - `generate_graph_relationship_type()`: Graph-DB Relationships
  - `generate_file_storage_bucket()`: File-Storage Buckets
  - `generate_unified_namespace()`: Cross-DB Namespace

**Beispiel**:
```python
from uds3_naming_strategy import NamingStrategy, create_municipal_strategy
from uds3_admin_types import AdminDocumentType

# Factory-Methode
strategy = create_municipal_strategy(
    municipality="münster",
    authority="bauamt",
    state="nrw"
)

# Namen generieren
vector_collection = strategy.generate_vector_collection_name(
    document_type=AdminDocumentType.PERMIT,
    content_type="chunks"
)
# Result: "uds3_muenster_bauamt_permit_chunks"

relational_table = strategy.generate_relational_table_name(
    entity_type="metadata",
    document_type=AdminDocumentType.PERMIT
)
# Result: "uds3_muenster_bauamt_permit_metadata"

graph_node_label = strategy.generate_graph_node_label(
    node_type="Document",
    document_type=AdminDocumentType.PERMIT
)
# Result: "MuensterBauamtPermit"

file_bucket = strategy.generate_file_storage_bucket(
    document_type=AdminDocumentType.PERMIT,
    access_level="internal"
)
# Result: "uds3_muenster_bauamt_permit_internal"
```

#### Factory Functions
- `create_municipal_strategy(municipality, authority, state, **kwargs)`: Kommune-Ebene
- `create_state_strategy(state, authority, **kwargs)`: Landes-Ebene
- `create_federal_strategy(authority, **kwargs)`: Bundes-Ebene

### 2. `uds3_naming_integration.py`

Integration mit bestehender UDS3-Architektur.

#### `NamingContext`
- **Zweck**: Wrapper für Dokument-Metadata mit Naming-Kontext
- **Methoden**:
  - `from_metadata(document_id, metadata)`: Erstellt aus Dict
  - `to_organization_context()`: Konvertiert zu OrganizationContext

**Beispiel**:
```python
from uds3_naming_integration import NamingContext

metadata = {
    "behoerde": "Bauamt",
    "kommune": "Münster",
    "bundesland": "NRW",
    "rechtsgebiet": "Baurecht",
    "document_type": "PERMIT",
    "admin_level": "municipal",
}

naming_ctx = NamingContext.from_metadata("DOC-001", metadata)
```

#### `NamingContextManager`
- **Zweck**: Zentrale Verwaltung von NamingStrategies mit Caching
- **Methoden**:
  - `resolve_vector_collection_name(naming_context, content_type)`: Vector Collection
  - `resolve_relational_table_name(naming_context, entity_type)`: SQL Table
  - `resolve_graph_node_label(naming_context, node_type)`: Graph Node
  - `resolve_graph_relationship_type(naming_context, rel_type)`: Graph Relationship
  - `resolve_file_storage_bucket(naming_context)`: File Bucket
  - `resolve_all_names(naming_context)`: Alle Namen auf einmal

**Beispiel**:
```python
from uds3_naming_integration import NamingContextManager, NamingContext

# Manager erstellen
naming_mgr = NamingContextManager()

# Context aus Metadata
naming_ctx = NamingContext.from_metadata("DOC-001", metadata)

# Namen resolven
collection = naming_mgr.resolve_vector_collection_name(naming_ctx, "chunks")
table = naming_mgr.resolve_relational_table_name(naming_ctx, "metadata")
node_label = naming_mgr.resolve_graph_node_label(naming_ctx, "Document")

# Alle Namen auf einmal
all_names = naming_mgr.resolve_all_names(naming_ctx)
print(all_names)
# {
#   'vector_collection': 'uds3_muenster_bauamt_permit_chunks',
#   'vector_summaries': 'uds3_muenster_bauamt_permit_summaries',
#   'relational_table': 'uds3_muenster_bauamt_permit_metadata',
#   'graph_node_label': 'MuensterBauamtPermit',
#   'file_bucket': 'uds3_muenster_bauamt_permit_internal',
#   'namespace': 'uds3_muenster_bauamt'
# }
```

#### `DynamicNamingSagaCRUD`
- **Zweck**: Wrapper für SagaDatabaseCRUD mit automatischer Namensgebung
- **Verwendung**: Drop-In-Replacement für bestehende SagaDatabaseCRUD

**Beispiel**:
```python
from uds3_naming_integration import create_naming_enabled_saga_crud

# Bestehende CRUD-Instanz
saga_crud = SagaDatabaseCRUD(...)

# Mit Naming erweitern
dynamic_crud = create_naming_enabled_saga_crud(
    saga_crud_instance=saga_crud,
    org_context=org_context  # Optional: Default-Context
)

# Verwendung (collection wird automatisch resolved)
dynamic_crud.vector_create(
    document_id="DOC-001",
    chunks=["chunk1", "chunk2"],
    metadata={
        "behoerde": "Bauamt",
        "kommune": "Münster",
        "document_type": "PERMIT"
    }
    # collection-Parameter wird automatisch generiert!
)
```

## Generierte Namensmuster

### Vector Collections
**Pattern**: `{prefix}_{org}_{doc_type}_{content_type}`

Beispiele:
- `uds3_muenster_bauamt_permit_chunks`
- `uds3_nrw_umweltministerium_adminact_summaries`
- `uds3_bund_justiz_gesetz_embeddings`

### Relational Tables
**Pattern**: `{prefix}_{org}_{doc_type}_{entity_type}_{purpose}`

Beispiele:
- `uds3_muenster_bauamt_permit_metadata`
- `uds3_koeln_planungsamt_documents_active`
- `uds3_nrw_umwelt_permits_archive`

### Graph Node Labels
**Pattern**: `{OrgPascalCase}{DocTypePascalCase}{NodeType}` (PascalCase)

Beispiele:
- `MuensterBauamtPermit`
- `NrwUmweltministeriumDocument`
- `BundJustizLaw`

### Graph Relationships
**Pattern**: `{CONTEXT}_{REL_TYPE}` (UPPER_SNAKE_CASE)

Beispiele:
- `BAUAMT_ISSUED_BY`
- `NRW_REFERENCES`
- `SUPERSEDES` (ohne Kontext)

### File Storage Buckets
**Pattern**: `{prefix}_{org}_{doc_type}_{access_level}`

Beispiele:
- `uds3_muenster_bauamt_permit_internal`
- `uds3_nrw_umwelt_documents_confidential`
- `uds3_bund_gesetze_public`

## Multi-Tenancy Support

Das System ermöglicht automatische Datentrennung zwischen verschiedenen Organisationen:

```python
# Stadt Münster
muenster_strategy = create_municipal_strategy(
    municipality="münster", authority="bauamt", state="nrw"
)
muenster_collection = muenster_strategy.generate_vector_collection_name(
    AdminDocumentType.PERMIT, "chunks"
)
# → "uds3_muenster_bauamt_permit_chunks"

# Stadt Köln
koeln_strategy = create_municipal_strategy(
    municipality="köln", authority="bauamt", state="nrw"
)
koeln_collection = koeln_strategy.generate_vector_collection_name(
    AdminDocumentType.PERMIT, "chunks"
)
# → "uds3_koeln_bauamt_permit_chunks"
```

✅ **Separate Collections** = Keine Datenvermischung!

## Integration in bestehenden Code

### Vor (Statisch):
```python
# saga_crud.py
def vector_create(self, document_id, chunks, metadata, collection="document_chunks"):
    # Alle Dokumente in derselben Collection
    ...
```

### Nach (Dynamisch):
```python
# saga_crud.py (mit NamingContextManager)
def vector_create(self, document_id, chunks, metadata, collection=None):
    if collection is None:
        # Dynamische Namensgebung
        naming_ctx = NamingContext.from_metadata(document_id, metadata)
        collection = self.naming_manager.resolve_vector_collection_name(naming_ctx)
    
    # Rest bleibt gleich
    ...
```

**Vorteile**:
- ✅ Abwärtskompatibel (collection-Parameter bleibt)
- ✅ Opt-In: Wenn `collection=None`, dann dynamisch
- ✅ Minimale Code-Änderungen
- ✅ Kein Breaking Change für Tests

## Use Cases

### 1. Multi-Tenancy (Mehrere Kommunen)
```python
cities = ["münster", "köln", "dortmund", "essen"]

for city in cities:
    strategy = create_municipal_strategy(
        municipality=city, authority="bauamt", state="nrw"
    )
    collection = strategy.generate_vector_collection_name(
        AdminDocumentType.PERMIT, "chunks"
    )
    print(f"{city:10} → {collection}")
```

Output:
```
münster    → uds3_muenster_bauamt_permit_chunks
köln       → uds3_koeln_bauamt_permit_chunks
dortmund   → uds3_dortmund_bauamt_permit_chunks
essen      → uds3_essen_bauamt_permit_chunks
```

### 2. Rechtsgebiete-Trennung
```python
rechtsgebiete = ["Baurecht", "Umweltrecht", "Planungsrecht"]

for rechtsgebiet in rechtsgebiete:
    metadata = {
        "kommune": "Münster",
        "rechtsgebiet": rechtsgebiet,
        "document_type": "PERMIT"
    }
    naming_ctx = NamingContext.from_metadata("DOC", metadata)
    collection = naming_mgr.resolve_vector_collection_name(naming_ctx)
    print(f"{rechtsgebiet:20} → {collection}")
```

### 3. Processing-Stages
```python
stages = ["draft", "active", "archive"]

for stage in stages:
    metadata = {
        "kommune": "Dortmund",
        "document_type": "PERMIT",
        "processing_stage": stage
    }
    naming_ctx = NamingContext.from_metadata("DOC", metadata)
    table = naming_mgr.resolve_relational_table_name(naming_ctx)
    print(f"{stage:10} → {table}")
```

Output:
```
draft      → uds3_dortmund_bauamt_permit_draft
active     → uds3_dortmund_bauamt_permit_active
archive    → uds3_dortmund_bauamt_permit_archive
```

### 4. Access-Level-Trennung
```python
access_levels = ["public", "internal", "confidential"]

for level in access_levels:
    metadata = {
        "kommune": "Essen",
        "document_type": "PERMIT",
        "access_level": level
    }
    naming_ctx = NamingContext.from_metadata("DOC", metadata)
    bucket = naming_mgr.resolve_file_storage_bucket(naming_ctx)
    print(f"{level:15} → {bucket}")
```

Output:
```
public          → uds3_essen_bauamt_permit_public
internal        → uds3_essen_bauamt_permit_internal
confidential    → uds3_essen_bauamt_permit_confidential
```

## Vorteile

### ✅ Vorteile der dynamischen Namensgebung:

1. **Multi-Tenancy**: Verschiedene Behörden/Kommunen isoliert
2. **Semantische Namen**: Aussagekräftig statt generisch
3. **Skalierbarkeit**: Kleinere Indizes pro Organization
4. **Performance**: Gezielte Suche nur in relevanten Collections
5. **Compliance**: Klare Datentrennung für Datenschutz
6. **Wartbarkeit**: Namen zeigen direkt den Kontext
7. **Flexibilität**: Neue Behörden ohne Code-Änderung
8. **Konsistenz**: Einheitliche Namensgebung über alle DB-Typen

### ❌ Alt (Statisch):
```
document_chunks              ← Alle Dokumente gemischt
documents_metadata           ← Keine Trennung
Document                     ← Generisch
```

### ✅ Neu (Dynamisch):
```
uds3_muenster_bauamt_permit_chunks     ← Klar identifiziert
uds3_muenster_bauamt_permit_metadata   ← Spezifisch
MuensterBauamtPermit                   ← Semantisch
```

## Nächste Schritte

### 1. Integration in `database/saga_crud.py`
Ändern Sie die CRUD-Methoden um `NamingContextManager` zu nutzen:

```python
# Vor
def vector_create(self, document_id, chunks, metadata, collection="document_chunks"):
    ...

# Nach
def vector_create(self, document_id, chunks, metadata, collection=None):
    if collection is None and self.naming_manager:
        naming_ctx = NamingContext.from_metadata(document_id, metadata)
        collection = self.naming_manager.resolve_vector_collection_name(naming_ctx)
    elif collection is None:
        collection = "document_chunks"  # Fallback
    ...
```

### 2. Erweitern Sie `uds3_core.py`
Fügen Sie NamingContextManager zu UnifiedDatabaseStrategy hinzu:

```python
class UnifiedDatabaseStrategy:
    def __init__(self, ..., naming_config=None):
        ...
        self.naming_manager = NamingContextManager(**(naming_config or {}))
        
        # Übergebe Manager an SagaCRUD
        self.saga_crud = create_naming_enabled_saga_crud(
            saga_crud_instance=self.saga_crud,
            naming_manager=self.naming_manager
        )
```

### 3. Tests schreiben
Erstellen Sie `test_naming_strategy.py`:
- Test verschiedene Organisationsebenen
- Test Multi-Tenancy-Szenarien
- Test Namens-Caching
- Test Rückwärtskompatibilität

### 4. Migration planen
- Mapping bestehender "document_chunks" → neue Namen
- Migrations-Script für bestehende Daten
- Parallelbetrieb alter/neuer Namen während Migration

### 5. Dokumentation aktualisieren
- README mit Naming-Beispielen
- API-Dokumentation erweitern
- Migrations-Guide erstellen

## Konfiguration

### Global Prefix
```python
naming_mgr = NamingContextManager(
    global_prefix="uds3"  # Standard
)
```

### Namenskonvention
```python
from uds3_naming_strategy import NamingConvention

naming_mgr = NamingContextManager(
    naming_convention=NamingConvention.SNAKE_CASE  # Standard
    # Alternativen: KEBAB_CASE, CAMEL_CASE, PASCAL_CASE
)
```

### Default Organization Context
```python
from uds3_naming_strategy import OrganizationContext
from uds3_admin_types import AdminLevel

default_org = OrganizationContext(
    level=AdminLevel.MUNICIPAL,
    municipality="default",
    authority="verwaltung"
)

naming_mgr = NamingContextManager(
    default_org_context=default_org
)
```

### Caching
```python
naming_mgr = NamingContextManager(
    enable_caching=True  # Standard
)

# Cache löschen (z.B. für Tests)
naming_mgr.clear_cache()
```

## FAQ

**Q: Was passiert mit bestehenden Daten in "document_chunks"?**  
A: Migration-Script erstellen, das Daten in neue Collections kopiert. Parallelbetrieb möglich.

**Q: Kann ich die dynamische Namensgebung deaktivieren?**  
A: Ja, indem Sie explizit `collection="document_chunks"` übergeben.

**Q: Was wenn Metadata keine Behörden-Info enthält?**  
A: Default Organization Context wird verwendet.

**Q: Sind die Namen zu lang für manche Datenbanken?**  
A: Automatische Kürzung + Hash-Suffix wenn max_length überschritten.

**Q: Wie teste ich das?**  
A: Siehe `test_naming_quick.py` für Beispiele.

## Zusammenfassung

Das **UDS3 Dynamic Naming Strategy System** bietet:

✅ **Kontextbasierte Namensgebung** für alle DB-Typen  
✅ **Multi-Tenancy Support** ohne Datenvermischung  
✅ **Semantisch aussagekräftige Namen**  
✅ **Abwärtskompatibel** mit bestehendem Code  
✅ **Einfache Integration** via NamingContextManager  
✅ **Performance-Optimierung** durch kleinere Indizes  
✅ **Compliance-konform** durch klare Datentrennung  

Perfekt geeignet für behördliche Verwaltungssysteme mit:
- Mehreren Behörden/Kommunen
- Verschiedenen Rechtsgebieten
- Unterschiedlichen Access-Levels
- Komplexen Organisations-Hierarchien
