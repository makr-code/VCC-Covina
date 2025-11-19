# Themis-Integration Roadmap

## Aktueller Stand (Commit 0640caa)

✅ **Vollständiger Polyglot-Ansatz implementiert**:
- 4 Datenbanken: PostgreSQL, ChromaDB, Neo4j, CouchDB
- Complete JSON Export mit Binary File
- Completeness Score (1.0 = 100%)

## Themis-Nähe ohne Polyglot zu verlassen

### Strategie: Hybrid-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     COVINA INGESTION                         │
│                                                               │
│  ┌────────────────┐        ┌────────────────────────────┐   │
│  │  Upload & Parse│        │  Polyglot Aggregator        │   │
│  │  (Legal Text)  │───────>│  - All 4 DBs               │   │
│  └────────────────┘        │  - Binary File             │   │
│                            │  - Complete JSON           │   │
│                            └────────┬───────────────────┘   │
│                                     │                        │
│                            ┌────────▼───────────────────┐   │
│                            │  THEMIS INTERFACE LAYER     │   │
│                            │                             │   │
│                            │  ┌──────────────────────┐  │   │
│                            │  │ Themis Adapter       │  │   │
│                            │  │ - Maps Polyglot→Themis│ │   │
│                            │  │ - Optimized Queries  │  │   │
│                            │  │ - API Compatibility  │  │   │
│                            │  └──────────────────────┘  │   │
│                            └────────┬───────────────────┘   │
│                                     │                        │
└─────────────────────────────────────┼────────────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │      THEMIS DATENBANK              │
                    │  (Kann Polyglot-JSON konsumieren) │
                    └────────────────────────────────────┘
```

### Phase 1: Themis Adapter (2-3 Tage)

**Ziel**: Schnittstelle zwischen Covina UDS3 und Themis

**Komponenten**:

1. **Themis Data Mapper** (`ingestion/themis/themis_mapper.py`):
```python
class ThemisDataMapper:
    """Maps Covina Polyglot JSON to Themis format"""
    
    def map_to_themis(self, polyglot_json: Dict) -> Dict:
        """
        Converts Polyglot JSON to Themis-specific format
        
        Input: Covina Polyglot JSON
        Output: Themis-compatible structure
        """
        return {
            "id": polyglot_json["document_id"],
            "version": polyglot_json["version"],
            
            # Relational → Themis Metadata
            "metadata": self._map_metadata(polyglot_json["relational"]),
            
            # Vector → Themis Embeddings
            "embeddings": self._map_vectors(polyglot_json["vector"]),
            
            # Graph → Themis Relationships
            "relationships": self._map_graph(polyglot_json["graph"]),
            
            # File → Themis Binary Storage
            "binary": {
                "data": polyglot_json["file"]["binary_data"],
                "content_type": polyglot_json["file"]["content_type"],
                "filename": polyglot_json["file"]["filename"]
            },
            
            # Text → Themis Full Text Index
            "full_text": polyglot_json["file"]["text_content"]
        }
```

2. **Themis Query Adapter** (`ingestion/themis/themis_queries.py`):
```python
class ThemisQueryAdapter:
    """Optimizes queries for Themis database"""
    
    def query_by_legal_reference(self, reference: str):
        """
        Query: Find all chunks with legal reference
        
        Themis-optimized:
        - Uses indexed fields
        - Minimiert DB-Calls
        - Cached results
        """
        pass
    
    def query_cross_references(self, doc_id: str):
        """Find cross-referenced documents"""
        pass
```

3. **Themis API Client** (`ingestion/themis/themis_client.py`):
```python
class ThemisAPIClient:
    """Client for Themis database API"""
    
    async def store_document(self, themis_data: Dict):
        """Store in Themis DB"""
        pass
    
    async def retrieve_document(self, doc_id: str):
        """Retrieve from Themis DB"""
        pass
```

### Phase 2: Optimized Storage Strategy (3-5 Tage)

**Dual Storage**: UDS3 Polyglot + Themis

```
Upload → Parse → UDS3 (4 DBs) → Polyglot JSON → Themis Adapter → Themis DB
                     ↓                              ↓
                 Backup/Debug              Production Queries
```

**Vorteile**:
- ✅ Polyglot bleibt erhalten (Backup, Debugging)
- ✅ Themis für optimierte Queries
- ✅ Beste Performance beider Welten

**Storage Decision Matrix**:

| Data Type | UDS3 Polyglot | Themis | Reasoning |
|-----------|---------------|---------|-----------|
| Original Binary | ✅ CouchDB + JSON | ✅ Themis | Redundanz für Sicherheit |
| Text Content | ✅ CouchDB | ✅ Themis | Full-text search |
| Embeddings | ✅ ChromaDB | ✅ Themis | Vector search optimization |
| Metadata | ✅ PostgreSQL | ✅ Themis | Query performance |
| Graph | ✅ Neo4j | ✅ Themis | Relationship queries |

### Phase 3: Query Router (2-3 Tage)

**Smart Query Routing**: Automatische Auswahl der besten Datenbank

```python
class QueryRouter:
    """Routes queries to optimal database"""
    
    def route_query(self, query_type: str, params: Dict):
        if query_type == "legal_reference":
            # Themis optimized für Legal Queries
            return self.themis_client.query_legal(params)
        
        elif query_type == "semantic_search":
            # ChromaDB für Vektor-Suche
            return self.chroma_client.search(params)
        
        elif query_type == "graph_traversal":
            # Neo4j für Graph-Queries
            return self.neo4j_client.traverse(params)
        
        elif query_type == "full_document":
            # Themis für Complete Document
            return self.themis_client.get_document(params)
```

### Phase 4: Performance Optimierung (5-7 Tage)

**Caching Layer**:
```python
class ThemisCacheLayer:
    """Cache frequently accessed Themis data"""
    
    # Redis für Hot Data
    # PostgreSQL für Metadata
    # Themis für Complete Documents
```

**Batch Processing**:
```python
class ThemisBatchWriter:
    """Batch writes to Themis for performance"""
    
    # Sammelt 100 Dokumente
    # Schreibt in einem Batch
    # Reduziert API Calls um 90%
```

## Implementation Plan

### Week 1: Themis Adapter
- [ ] Create ThemisDataMapper
- [ ] Test with sample documents
- [ ] Validate format compatibility

### Week 2: Integration
- [ ] Integrate into ingestion pipeline
- [ ] Dual-write (UDS3 + Themis)
- [ ] Performance benchmarks

### Week 3: Query Optimization
- [ ] Implement QueryRouter
- [ ] Optimize common queries
- [ ] Cache layer

### Week 4: Production Ready
- [ ] Full test suite
- [ ] Documentation
- [ ] Deployment

## Beispiel: BImSchG Workflow

**1. Upload** → BImSchG.pdf

**2. Parse** → Legal Structure (§, Absatz, Nummer)

**3. UDS3 Storage**:
- PostgreSQL: Metadata ✅
- ChromaDB: 10 Chunks mit Embeddings ✅
- Neo4j: Document Node ✅
- CouchDB: Full Text ✅
- JSON: `data/polyglot/abc123.json` ✅

**4. Themis Mapping**:
```python
themis_data = themis_mapper.map_to_themis(polyglot_json)
# → Optimiert für Themis Queries
```

**5. Themis Storage**:
```python
themis_client.store_document(themis_data)
# → Dual storage: UDS3 + Themis
```

**6. Query**:
```python
# User Query: "Was steht in § 1 Abs. 2?"
result = query_router.route_query("legal_reference", {
    "reference": "§ 1 Abs. 2"
})
# → Themis optimized query
# → Returns: Chunk mit § 1 Abs. 2
```

## Vorteile Hybrid-Ansatz

### 1. Polyglot Preserved
- ✅ Alle 4 Datenbank-Typen bleiben
- ✅ Flexibilität für verschiedene Use Cases
- ✅ Kein Vendor Lock-in

### 2. Themis Optimized
- ✅ Schnellere Queries
- ✅ Optimierte Speicherung
- ✅ Bessere Integration

### 3. Beste Beide Welten
- ✅ UDS3 für Debugging/Backup
- ✅ Themis für Production Queries
- ✅ Automatisches Routing

## Migration Path

**Kein Breaking Change**:
1. Bestehende UDS3 Polyglot bleibt
2. Themis wird zusätzlich aktiviert
3. Queries nutzen automatisch beste DB
4. Schrittweise Migration möglich

## Next Steps

1. **Themis API Spec** erhalten
2. **ThemisDataMapper** implementieren
3. **Dual-Write** testen
4. **Performance** vergleichen
5. **Production** deployment

## Fragen für Themis Team

1. Themis API Spezifikation?
2. Bevorzugtes Daten-Format?
3. Rate Limits / Batch Sizes?
4. Query Optimierungen?
5. Authentifizierung?

## Status

**Current**: ✅ Complete Polyglot JSON Export (Commit 0640caa)  
**Next**: 🔄 Themis Adapter Implementation  
**Goal**: 🎯 Hybrid UDS3 + Themis Architecture
