# Legal Domain Knowledge Graph - Design Document

**Version:** 1.0  
**Datum:** 29. Oktober 2025  
**Status:** Design Phase  
**Ziel:** Transformation der generischen Neo4j-Struktur in eine domänenspezifische Legal/Administrative Ontologie

---

## 📊 Executive Summary

### Problem Statement
Die aktuelle Neo4j-Struktur (161.067 Nodes, 19.334 Relationships) ist zu generisch:
- **Rechtsgebiete** nur als String-Properties (`rechtsgebiet: "Baurecht"`)
- **Legal Concepts** (Immissionsschutz, Wasser, Bildung) fehlen als eigenständige Entities
- **Jurisdiktions-Hierarchie** (Bund → Land → Kreis → Kommune) nicht modelliert
- **Behörden-Zuständigkeiten** nicht strukturiert verknüpft

### Solution Architecture
**Best-Practice Legal Knowledge Graph** mit 4 Ebenen:

```
1. Legal Domain Taxonomy (Rechtsgebiets-Hierarchie)
   └─ Öffentliches Recht → Verwaltungsrecht → Baurecht → BImSchG

2. Jurisdictional Hierarchy (Verwaltungsebenen)
   └─ Bund → Land NRW → Kreis Köln → Stadt Köln

3. Authority Network (Behörden + Zuständigkeiten)
   └─ Bauamt Köln [SUPERVISES] → Baugenehmigungen [REQUIRES] → BauGB

4. Legal Concept Graph (Rechtsbegriffe + Normen)
   └─ Immissionsschutz [REGULATED_BY] → BImSchG [ENFORCED_BY] → Umweltamt
```

---

## 🏗️ Best Practice: Legal Knowledge Graph Patterns

### Pattern 1: Legal Domain Taxonomy (Rechtsgebiets-Ontologie)

**Hierarchische Struktur:**
```cypher
// Haupt-Rechtsgebiete (Tier 1)
(:LegalDomain {
    id: "oeffentliches_recht",
    name: "Öffentliches Recht",
    tier: 1,
    description: "Regelt Verhältnis Staat ↔ Bürger"
})

// Sub-Domains (Tier 2)
(:LegalDomain {
    id: "verwaltungsrecht",
    name: "Verwaltungsrecht",
    tier: 2,
    parent: "oeffentliches_recht"
})

// Spezialgebiete (Tier 3)
(:LegalDomain {
    id: "baurecht",
    name: "Baurecht",
    tier: 3,
    parent: "verwaltungsrecht",
    keywords: ["Baugenehmigung", "Bebauungsplan", "Immissionsschutz"]
})

// Relationship: Hierarchie
CREATE (baurecht)-[:SUBDOMAIN_OF]->(verwaltungsrecht)-[:SUBDOMAIN_OF]->(oeffentliches_recht)
```

**Vorteile:**
- ✅ Taxonomie-Queries: "Alle Dokumente im Öffentlichen Recht" (inkl. Subdomains)
- ✅ Automatische Klassifikation durch Keyword-Matching
- ✅ Compliance-Checks: "Ist dieses Dokument im richtigen Rechtsgebiet?"

---

### Pattern 2: Jurisdictional Hierarchy (Verwaltungsebenen)

**5-stufige Hierarchie:**
```cypher
// Bund (Tier 0)
(:Jurisdiction {
    id: "bund_de",
    name: "Bundesrepublik Deutschland",
    tier: 0,
    type: "federal",
    ags: "00000000"  // Amtlicher Gemeindeschlüssel
})

// Land (Tier 1)
(:Jurisdiction {
    id: "land_nrw",
    name: "Nordrhein-Westfalen",
    tier: 1,
    type: "state",
    ags: "05000000",
    capital: "Düsseldorf"
})

// Regierungsbezirk (Tier 2)
(:Jurisdiction {
    id: "rb_koeln",
    name: "Regierungsbezirk Köln",
    tier: 2,
    type: "district",
    ags: "05300000"
})

// Kreis (Tier 3)
(:Jurisdiction {
    id: "kreis_koeln",
    name: "Stadt Köln (kreisfreie Stadt)",
    tier: 3,
    type: "municipality_independent",
    ags: "05315000"
})

// Gemeinde (Tier 4)
(:Jurisdiction {
    id: "stadt_koeln",
    name: "Köln",
    tier: 4,
    type: "city",
    ags: "05315000",
    population: 1085664
})

// Relationships: Hierarchie
CREATE (stadt_koeln)-[:PART_OF]->(kreis_koeln)
       -[:PART_OF]->(rb_koeln)
       -[:PART_OF]->(land_nrw)
       -[:PART_OF]->(bund_de)
```

**Queries:**
```cypher
// Alle Dokumente in NRW (inkl. Untergliederungen)
MATCH (doc:Document)-[:APPLIES_TO]->(j:Jurisdiction)
      -[:PART_OF*0..]->(nrw:Jurisdiction {id: "land_nrw"})
RETURN doc, j

// Zuständige Behörden für Köln
MATCH (auth:Authority)-[:JURISDICTION_AREA]->(j:Jurisdiction)
      -[:PART_OF*0..]->(koeln:Jurisdiction {id: "stadt_koeln"})
RETURN auth.name, j.name
```

---

### Pattern 3: Legal Concept Graph (Rechtsbegriffe als Nodes)

**Konzept-Entities:**
```cypher
// Legal Concept: Immissionsschutz
(:LegalConcept {
    id: "immissionsschutz",
    name: "Immissionsschutz",
    category: "environmental_law",
    definition: "Schutz vor schädlichen Umwelteinwirkungen (Lärm, Luftverschmutzung, etc.)",
    keywords: ["Lärm", "Luftqualität", "Emissionen", "Grenzwerte"],
    legal_domains: ["baurecht", "umweltrecht"]
})

// Legal Concept: Baugenehmigung
(:LegalConcept {
    id: "baugenehmigung",
    name: "Baugenehmigung",
    category: "administrative_procedure",
    definition: "Behördliche Erlaubnis zur Errichtung/Änderung baulicher Anlagen",
    keywords: ["Bauantrag", "Bauvoranfrage", "Baugenehmigungsverfahren"],
    legal_domains: ["baurecht"]
})

// Legal Concept: Wasserschutz
(:LegalConcept {
    id: "wasserschutz",
    name: "Wasserschutz",
    category: "environmental_law",
    definition: "Schutz von Oberflächengewässern und Grundwasser",
    keywords: ["Grundwasser", "Gewässerschutz", "Wasserschutzgebiet"],
    legal_domains: ["umweltrecht", "wasserrecht"]
})

// Legal Concept: Bildungsauftrag
(:LegalConcept {
    id: "bildungsauftrag",
    name: "Bildungsauftrag",
    category: "social_law",
    definition: "Staatlicher Auftrag zur Bereitstellung von Bildungseinrichtungen",
    keywords: ["Schule", "Bildung", "Schulpflicht", "Lehrplan"],
    legal_domains: ["bildungsrecht"]
})

// Relationships: Konzept ↔ Rechtsgebiet
MATCH (concept:LegalConcept {id: "immissionsschutz"})
MATCH (domain:LegalDomain {id: "baurecht"})
CREATE (concept)-[:PART_OF_DOMAIN]->(domain)

// Relationships: Konzept ↔ Dokument
MATCH (doc:Document {file_path: "bauantrag_001.pdf"})
MATCH (concept:LegalConcept {id: "baugenehmigung"})
CREATE (doc)-[:MENTIONS_CONCEPT {count: 15, confidence: 0.92}]->(concept)
```

**Vorteile:**
- ✅ Semantische Suche: "Alle Dokumente zu Immissionsschutz" (unabhängig von Wording)
- ✅ Multi-Domain Concepts: Immissionsschutz in Bau- UND Umweltrecht
- ✅ Concept Co-Occurrence: "Welche Konzepte treten häufig zusammen auf?"

---

### Pattern 4: Authority Network (Behörden + Zuständigkeiten)

**Behörden-Entities:**
```cypher
// Behörde: Bauamt Köln
(:Authority {
    id: "bauamt_koeln",
    name: "Bauaufsichtsamt Köln",
    type: "bauamt",
    level: "municipality",
    address: "Willy-Brandt-Platz 2, 50679 Köln",
    email: "bauaufsicht@stadt-koeln.de",
    phone: "+49 221 221-0",
    opening_hours: "Mo-Fr 08:00-12:00",
    online_services: ["Bauvoranfrage", "Baugenehmigung", "Bauanzeige"]
})

// Behörde: Umweltamt Köln
(:Authority {
    id: "umweltamt_koeln",
    name: "Amt für Umwelt- und Verbraucherschutz Köln",
    type: "umweltamt",
    level: "municipality",
    competencies: ["Immissionsschutz", "Gewässerschutz", "Bodenschutz"]
})

// Behörde: Schulamt Köln
(:Authority {
    id: "schulamt_koeln",
    name: "Schulamt für die Stadt Köln",
    type: "schulamt",
    level: "municipality",
    competencies: ["Schulpflicht", "Schulaufnahme", "Schulwechsel"]
})

// Relationships: Behörde ↔ Rechtsgebiet
MATCH (auth:Authority {id: "bauamt_koeln"})
MATCH (domain:LegalDomain {id: "baurecht"})
CREATE (auth)-[:SUPERVISES_DOMAIN]->(domain)

// Relationships: Behörde ↔ Jurisdiktion
MATCH (auth:Authority {id: "bauamt_koeln"})
MATCH (jurisdiction:Jurisdiction {id: "stadt_koeln"})
CREATE (auth)-[:JURISDICTION_AREA]->(jurisdiction)

// Relationships: Behörde ↔ Legal Concept
MATCH (auth:Authority {id: "umweltamt_koeln"})
MATCH (concept:LegalConcept {id: "immissionsschutz"})
CREATE (auth)-[:ENFORCES_CONCEPT]->(concept)
```

**Queries:**
```cypher
// Zuständige Behörde für Baugenehmigung in Köln
MATCH (concept:LegalConcept {id: "baugenehmigung"})
      <-[:ENFORCES_CONCEPT]-(auth:Authority)
      -[:JURISDICTION_AREA]->(j:Jurisdiction {id: "stadt_koeln"})
RETURN auth.name, auth.email, auth.online_services

// Alle Behörden im Baurecht (bundesweit)
MATCH (auth:Authority)-[:SUPERVISES_DOMAIN]->(domain:LegalDomain {id: "baurecht"})
RETURN auth.name, auth.level, auth.type
ORDER BY auth.level
```

---

### Pattern 5: Legal Basis Integration (Normen + Gesetze)

**Legal Basis Entities:**
```cypher
// Gesetz: BauGB
(:LegalBasis {
    id: "baugb",
    name: "Baugesetzbuch",
    abbreviation: "BauGB",
    type: "Bundesgesetz",
    jurisdiction: "bund",
    legal_domain: "baurecht",
    enacted: date("1960-06-23"),
    last_amended: date("2023-12-20"),
    url: "https://www.gesetze-im-internet.de/bbaug/",
    paragraphs_count: 249
})

// Norm: §29 BauGB (Baugenehmigung)
(:LegalNorm {
    id: "baugb_29",
    law: "BauGB",
    paragraph: "§29",
    title: "Baugenehmigung",
    content: "Im Geltungsbereich eines Bebauungsplans...",
    applies_to: ["baugenehmigung", "bauvoranfrage"],
    legal_concepts: ["baugenehmigung", "immissionsschutz"]
})

// Gesetz: BImSchG
(:LegalBasis {
    id: "bimschg",
    name: "Bundes-Immissionsschutzgesetz",
    abbreviation: "BImSchG",
    type: "Bundesgesetz",
    jurisdiction: "bund",
    legal_domain: "umweltrecht",
    enacted: date("1974-05-15"),
    url: "https://www.gesetze-im-internet.de/bimschg/"
})

// Relationships: Norm ↔ Legal Concept
MATCH (norm:LegalNorm {id: "baugb_29"})
MATCH (concept:LegalConcept {id: "baugenehmigung"})
CREATE (norm)-[:REGULATES_CONCEPT]->(concept)

// Relationships: Behörde ↔ Norm (Enforcement)
MATCH (auth:Authority {id: "bauamt_koeln"})
MATCH (norm:LegalNorm {id: "baugb_29"})
CREATE (auth)-[:ENFORCES_NORM]->(norm)

// Relationships: Dokument ↔ Norm (References)
MATCH (doc:Document {file_path: "bauantrag_001.pdf"})
MATCH (norm:LegalNorm {id: "baugb_29"})
CREATE (doc)-[:CITES_NORM {context: "Antrag gemäß §29 BauGB"}]->(norm)
```

---

## 🎯 Implementierungsplan

### Phase 1: Schema Migration (Woche 1)

#### Task 1.1: Legal Domain Taxonomy erstellen
- [ ] **Datei:** `ingestion/graph/legal_domain_taxonomy.py`
- [ ] **Taxonomie-Daten:** CSV/JSON mit Rechtsgebiets-Hierarchie
  ```json
  {
    "domains": [
      {
        "id": "oeffentliches_recht",
        "name": "Öffentliches Recht",
        "tier": 1,
        "children": ["verwaltungsrecht", "strafrecht", "verfassungsrecht"]
      },
      {
        "id": "verwaltungsrecht",
        "name": "Verwaltungsrecht",
        "tier": 2,
        "parent": "oeffentliches_recht",
        "children": ["baurecht", "umweltrecht", "wasserrecht", "bildungsrecht"]
      },
      {
        "id": "baurecht",
        "name": "Baurecht",
        "tier": 3,
        "parent": "verwaltungsrecht",
        "keywords": ["Baugenehmigung", "Bebauungsplan", "Bauvoranfrage", "Immissionsschutz"]
      }
    ]
  }
  ```
- [ ] **Cypher Queries:** Bulk-Insert via Neo4j Python Driver
- [ ] **Tests:** Taxonomie-Traversierung, Keyword-Matching

#### Task 1.2: Jurisdictional Hierarchy erstellen
- [ ] **Datei:** `ingestion/graph/jurisdiction_hierarchy.py`
- [ ] **Datenquelle:** Amtlicher Gemeindeschlüssel (AGS) CSV
  - Quelle: https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/_inhalt.html
- [ ] **Struktur:** 5-stufig (Bund → Land → Regierungsbezirk → Kreis → Gemeinde)
- [ ] **Geo-Integration:** Optionale Lat/Lng für Behörden
- [ ] **Tests:** Hierarchie-Queries, Zuständigkeits-Matching

#### Task 1.3: Legal Concepts extrahieren
- [ ] **Datei:** `ingestion/graph/legal_concept_extractor.py`
- [ ] **Methode:** NLP-basierte Extraktion aus bestehendem Corpus
  ```python
  class LegalConceptExtractor:
      """Extrahiert Legal Concepts aus bestehendem Dokumenten-Corpus"""
      
      def extract_concepts_from_corpus(self) -> List[LegalConcept]:
          # 1. TF-IDF auf allen Dokumenten
          # 2. Top-K Keywords pro Rechtsgebiet
          # 3. Clustering ähnlicher Terms (z.B. "Lärmschutz" + "Immissionsschutz")
          # 4. Manual Review + Curation
          pass
      
      def create_concept_nodes(self, concepts: List[LegalConcept]):
          # Cypher INSERT für jeden Concept
          pass
  ```
- [ ] **Initial Seed:** Top-30 Legal Concepts (manuell kuratiert)
  - Bau: Baugenehmigung, Bauvoranfrage, Immissionsschutz, Bebauungsplan
  - Umwelt: Gewässerschutz, Bodenschutz, Lärmschutz, Luftreinhaltung
  - Bildung: Schulpflicht, Schulaufnahme, Schulwechsel, Bildungsauftrag
  - Wasser: Wasserschutzgebiet, Grundwasserschutz, Abwasser
- [ ] **Tests:** Concept Extraction Accuracy, Relationship Creation

#### Task 1.4: Authority Network aufbauen
- [ ] **Datei:** `ingestion/graph/authority_network.py`
- [ ] **Datenquelle:** Behörden-Datenbank (manuell kuratiert oder Web-Scraping)
  - Start: Top-20 Behörden in Köln/NRW
  - Beispiele: Bauamt, Umweltamt, Schulamt, Ordnungsamt, Jugendamt
- [ ] **Properties:** Name, Typ, Ebene, Kontakt, Zuständigkeiten, Online-Services
- [ ] **Relationships:**
  - `(:Authority)-[:JURISDICTION_AREA]->(:Jurisdiction)`
  - `(:Authority)-[:SUPERVISES_DOMAIN]->(:LegalDomain)`
  - `(:Authority)-[:ENFORCES_CONCEPT]->(:LegalConcept)`
- [ ] **Tests:** Authority Lookup, Competency Queries

#### Task 1.5: Document Re-Linking (Migration)
- [ ] **Datei:** `ingestion/graph/document_migration.py`
- [ ] **Aufgabe:** Bestehende 161k Documents mit neuen Entities verknüpfen
  ```python
  class DocumentMigration:
      """Migriert bestehende Documents zu neuen Legal Graph Entities"""
      
      async def migrate_documents(self):
          # Für jedes Document:
          # 1. Extract Rechtsgebiet (aus Property) → Link zu LegalDomain
          # 2. Extract Legal Concepts (NLP auf content) → Link zu LegalConcept
          # 3. Extract Jurisdiction (aus metadata) → Link zu Jurisdiction
          # 4. Extract Authority (aus metadata) → Link zu Authority
          pass
      
      def link_document_to_domain(self, doc_id: str, domain_id: str):
          cypher = """
          MATCH (doc:Document {document_id: $doc_id})
          MATCH (domain:LegalDomain {id: $domain_id})
          MERGE (doc)-[:CLASSIFIED_IN_DOMAIN]->(domain)
          """
          pass
  ```
- [ ] **Performance:** Batch Processing (1000 Docs/Batch)
- [ ] **Validation:** Stichproben-Checks (100 random docs)

---

### Phase 2: Query Optimizations (Woche 2)

#### Task 2.1: Neo4j Indexes erstellen
```cypher
// Performance-Indizes für neue Node Types
CREATE INDEX legal_domain_id IF NOT EXISTS FOR (d:LegalDomain) ON (d.id);
CREATE INDEX legal_domain_tier IF NOT EXISTS FOR (d:LegalDomain) ON (d.tier);
CREATE INDEX legal_concept_id IF NOT EXISTS FOR (c:LegalConcept) ON (c.id);
CREATE INDEX legal_concept_category IF NOT EXISTS FOR (c:LegalConcept) ON (c.category);
CREATE INDEX jurisdiction_id IF NOT EXISTS FOR (j:Jurisdiction) ON (j.id);
CREATE INDEX jurisdiction_ags IF NOT EXISTS FOR (j:Jurisdiction) ON (j.ags);
CREATE INDEX authority_id IF NOT EXISTS FOR (a:Authority) ON (a.id);
CREATE INDEX authority_type IF NOT EXISTS FOR (a:Authority) ON (a.type);

// Fulltext Search
CREATE FULLTEXT INDEX legal_concept_search IF NOT EXISTS
FOR (c:LegalConcept) ON EACH [c.name, c.definition, c.keywords];
```

#### Task 2.2: Graph Queries für Frontend
- [ ] **Datei:** `backend/queries/legal_graph_queries.py`
- [ ] **Endpoints:**
  ```python
  # Query 1: Alle Dokumente in Rechtsgebiet (inkl. Subdomains)
  GET /api/v1/legal-domains/{domain_id}/documents?include_subdomains=true
  
  # Query 2: Zuständige Behörde für Legal Concept + Jurisdiction
  GET /api/v1/authority-lookup?concept=baugenehmigung&jurisdiction=stadt_koeln
  
  # Query 3: Related Legal Concepts (Graph Co-Occurrence)
  GET /api/v1/legal-concepts/{concept_id}/related?limit=10
  
  # Query 4: Document Classification Suggestions
  POST /api/v1/documents/{doc_id}/classify-suggest
  # → Analysiert Content, schlägt Legal Domains + Concepts vor
  ```

---

### Phase 3: NLP Integration (Woche 3)

#### Task 3.1: Legal Concept Detection (NER)
- [ ] **Datei:** `ingestion/nlp/legal_concept_detector.py`
- [ ] **Modell:** Spacy + Custom Training auf Legal Corpus
- [ ] **Entities:** LEGAL_CONCEPT, AUTHORITY, JURISDICTION, LEGAL_NORM
- [ ] **Pipeline:**
  ```python
  class LegalConceptDetector:
      def detect_concepts(self, text: str) -> List[ConceptMention]:
          # 1. Spacy NER
          # 2. Keyword Matching (gegen LegalConcept.keywords)
          # 3. Confidence Scoring
          # 4. Return Top-K Mentions
          pass
  ```

#### Task 3.2: Automated Document Linking
- [ ] **Integration:** In `process_document_with_uds3()`
- [ ] **Workflow:**
  ```
  Document Upload
    → NLP Detection (Legal Concepts, Jurisdictions, Authorities)
    → Cypher Relationship Creation
    → Neo4j Insert
  ```

---

### Phase 4: Validation & Testing (Woche 4)

#### Task 4.1: Graph Quality Metrics
- [ ] **Metriken:**
  - Concept Coverage: % Documents with ≥1 Legal Concept Link
  - Taxonomy Depth: Avg. Hops from Document → Top-Level Domain
  - Authority Linkage: % Concepts with Authority Assignment
  - Orphan Nodes: Nodes ohne Relationships

#### Task 4.2: User Acceptance Testing
- [ ] **Test Queries:**
  - "Alle Dokumente zu Immissionsschutz in Köln"
  - "Zuständige Behörde für Baugenehmigung in Musterstadt"
  - "Rechtsgebiets-Hierarchie für Dokument XYZ"

---

## 📁 Neue Dateien (zu erstellen)

```
ingestion/
├── graph/
│   ├── __init__.py
│   ├── legal_domain_taxonomy.py       # Rechtsgebiets-Hierarchie
│   ├── jurisdiction_hierarchy.py      # Verwaltungsebenen
│   ├── legal_concept_extractor.py     # NLP-basierte Concept Extraction
│   ├── authority_network.py           # Behörden-Netzwerk
│   └── document_migration.py          # Bestehende Docs migrieren
│
├── nlp/
│   ├── __init__.py
│   └── legal_concept_detector.py      # NER für Legal Entities
│
└── data/
    ├── legal_domains.json              # Rechtsgebiets-Taxonomie (Seed Data)
    ├── jurisdictions.csv               # AGS-Daten (Gemeindeschlüssel)
    ├── authorities.json                # Behörden-Verzeichnis (kuratiert)
    └── legal_concepts_seed.json        # Initial 30 Legal Concepts

backend/
└── queries/
    └── legal_graph_queries.py          # API Endpoints für Legal Graph

tests/
└── integration/
    ├── test_legal_domain_taxonomy.py
    ├── test_jurisdiction_hierarchy.py
    ├── test_legal_concept_extraction.py
    └── test_authority_network.py
```

---

## 🎯 Success Criteria

### Technical
- [ ] 100+ Legal Concepts als Nodes (Start: Top-30)
- [ ] 5-stufige Jurisdiktions-Hierarchie (16 Bundesländer + Top-100 Städte)
- [ ] 20+ Rechtsgebiete in 3-Tier Taxonomie
- [ ] 50+ Behörden mit Zuständigkeiten
- [ ] 80%+ Documents mit ≥1 Legal Concept Link
- [ ] <100ms P95 Latency für Graph Queries

### Business Value
- [ ] **Präzisere Suche:** "Immissionsschutz in Köln" → Nur relevante Docs
- [ ] **Behörden-Routing:** Automatische Zuständigkeits-Erkennung
- [ ] **Compliance-Checks:** "Ist Dokument im richtigen Rechtsgebiet?"
- [ ] **Knowledge Discovery:** "Welche Konzepte treten zusammen auf?"

---

## 🚀 Quick Start (für Developer)

### 1. Seed Data laden
```bash
# Legal Domains Taxonomie
python ingestion/graph/legal_domain_taxonomy.py --load-seed data/legal_domains.json

# Jurisdictions (AGS-Daten)
python ingestion/graph/jurisdiction_hierarchy.py --load-csv data/jurisdictions.csv

# Legal Concepts (Initial 30)
python ingestion/graph/legal_concept_extractor.py --load-seed data/legal_concepts_seed.json

# Authorities (Top-20)
python ingestion/graph/authority_network.py --load-json data/authorities.json
```

### 2. Bestehende Documents migrieren
```bash
# Batch Migration (1000 Docs/Batch)
python ingestion/graph/document_migration.py --batch-size 1000 --max-docs 10000
```

### 3. Validierung
```bash
# Graph Quality Metrics
python tests/integration/test_legal_graph_quality.py

# Stichproben-Check
python tests/integration/test_document_linking_accuracy.py --sample-size 100
```

### 4. Neo4j Browser testen
```cypher
// Beispiel-Query: Alle Konzepte im Baurecht
MATCH (concept:LegalConcept)-[:PART_OF_DOMAIN]->(domain:LegalDomain)
WHERE domain.id STARTS WITH 'baurecht'
RETURN concept.name, concept.definition
ORDER BY concept.name
```

---

## 📚 Referenzen

### Best Practices Quellen
1. **Legal Knowledge Graphs:**
   - Paper: "Knowledge Graphs for Legal Information Retrieval" (ACM 2023)
   - Projekt: European Case Law Identifier (ECLI) Graph

2. **Administrative Hierarchies:**
   - Destatis: Amtlicher Gemeindeschlüssel (AGS)
   - OpenStreetMap: Admin Boundaries (Nominatim)

3. **Neo4j Patterns:**
   - Neo4j Graph Data Science Library
   - Graph Schema Design Best Practices (Neo4j Docs)

### Existierende Covina-Dateien (als Referenz)
- `uds3/core/schemas.py` (Lines 125-156): LegalEntity Node Definition
- `uds3/archive/uds3_enhanced_schema.py` (Lines 89-128): Enhanced Graph Schema
- `veritas/shared/pipelines/veritas_relations_almanach.py`: Legal Relations Pattern

---

**Version:** 1.0  
**Status:** ✅ Ready for Implementation  
**Nächster Schritt:** Task 1.1 - Legal Domain Taxonomy Seed Data erstellen
