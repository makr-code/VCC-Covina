# Geodaten/Metadaten Integration in UDS3
## Konzept für geografische und Meta-Datenbank-Integration

Stand: 22. August 2025

## 1. Architektur-Übersicht

### 1.1 Bestehende UDS3-Struktur (Analyse)
Das aktuelle UDS3-System implementiert bereits eine Multi-Database-Architektur:

**Datenbankrollen:**
- **Vector DB (ChromaDB/Pinecone):** Semantische Suche über alle Dokumenttypen
- **Graph DB (Neo4j/ArangoDB):** Normenhierarchien, Verwaltungsverfahren, Behördenstrukturen
- **Relational DB (SQLite/PostgreSQL):** Metadaten, Fristen, Verfahrensstatus, Compliance

### 1.2 Geodaten-Integration: Erweiterte Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    UDS3 + GEO Extension                     │
├─────────────────────────────────────────────────────────────┤
│  Vector DB        │  Graph DB         │  Relational DB      │
│  (Semantik)       │  (Beziehungen)    │  (Metadaten)        │
│  ─────────────    │  ─────────────    │  ─────────────      │
│  • ChromaDB       │  • Neo4j          │  • PostgreSQL       │
│  • Embeddings     │  • Verwaltung     │  • Structured Data  │
│  • Similarity     │  • Hierarchien    │  • ACID Garantien   │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   GEO Extension   │
                    └─────────┬─────────┘
┌─────────────────────────────┼─────────────────────────────┐
│            GEODATEN-LAYER (Neu)                          │
├─────────────────────────────┼─────────────────────────────┤
│  PostGIS           │  Neo4j Spatial   │  Vector Geo       │
│  (Geo-Relational) │  (Geo-Graph)      │  (Geo-Semantic)   │
│  ─────────────     │  ─────────────    │  ─────────────    │
│  • Geometrien      │  • Räumliche      │  • Geo-Embeddings │
│  • Topologien      │    Beziehungen    │  • Spatial Search │
│  • Koordinaten     │  • Routing        │  • Location Vec   │
└─────────────────────────────────────────────────────────────┘
```

## 2. Geodaten-Datenmodell

### 2.1 Erweiterte UDS3-Schemas mit Geodaten

**A) Relational DB (PostgreSQL + PostGIS):**

```sql
-- Erweiterte documents-Tabelle
CREATE TABLE documents (
    -- Bestehende UDS3-Felder
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    content_preview TEXT,
    rechtsgebiet VARCHAR(200),
    gericht VARCHAR(200),
    aktenzeichen VARCHAR(200),
    
    -- NEUE GEODATEN-FELDER
    location_point GEOMETRY(POINT, 4326),          -- Punkt-Koordinaten
    location_polygon GEOMETRY(POLYGON, 4326),      -- Flächen (Grundstücke, Bezirke)
    location_linestring GEOMETRY(LINESTRING, 4326), -- Linien (Straßen, Grenzen)
    administrative_level INTEGER,                   -- Verwaltungsebene (Bund=1, Land=2, etc.)
    postal_code VARCHAR(10),                        -- PLZ für schnelle Suche
    municipality VARCHAR(100),                      -- Gemeinde/Stadt
    district VARCHAR(100),                          -- Landkreis/Bezirk
    state VARCHAR(50),                             -- Bundesland
    country VARCHAR(50) DEFAULT 'Deutschland',     -- Land
    
    -- Geo-Metadaten
    coordinate_system VARCHAR(20) DEFAULT 'EPSG:4326', -- Koordinatensystem
    location_accuracy INTEGER,                      -- Genauigkeit in Metern
    location_source VARCHAR(100),                   -- Quelle der Geodaten
    geo_quality_score DECIMAL(3,2)                 -- Qualitätsscore 0.00-1.00
);

-- Spatial Index für Performance
CREATE INDEX idx_documents_location_point ON documents USING GIST (location_point);
CREATE INDEX idx_documents_location_polygon ON documents USING GIST (location_polygon);

-- Administrative Gebiete (Master Data)
CREATE TABLE administrative_areas (
    id VARCHAR(20) PRIMARY KEY,              -- AGS (Amtlicher Gemeindeschlüssel)
    name VARCHAR(200) NOT NULL,
    area_type VARCHAR(50),                   -- 'bund', 'land', 'kreis', 'gemeinde'
    parent_id VARCHAR(20),                   -- Hierarchie
    geometry GEOMETRY(MULTIPOLYGON, 4326),  -- Gebietsgrenzen
    population INTEGER,
    area_km2 DECIMAL(10,2),
    FOREIGN KEY (parent_id) REFERENCES administrative_areas(id)
);

-- Geo-Indizierung für Behörden/Gerichte
CREATE TABLE institutions_geo (
    institution_id VARCHAR(64) PRIMARY KEY,
    institution_name VARCHAR(200),
    institution_type VARCHAR(50),           -- 'gericht', 'behoerde', 'ministerium'
    address TEXT,
    location GEOMETRY(POINT, 4326),
    jurisdiction_area GEOMETRY(MULTIPOLYGON, 4326), -- Zuständigkeitsbereich
    administrative_area_id VARCHAR(20),
    FOREIGN KEY (administrative_area_id) REFERENCES administrative_areas(id)
);
```

**B) Graph DB (Neo4j + Spatial):**

```cypher
-- Geo-Knoten und Beziehungen
CREATE (doc:Document {
    id: "doc_12345",
    title: "Baugenehmigung Hauptstraße 1",
    latitude: 52.5200,
    longitude: 13.4050,
    administrative_level: 3
})

CREATE (area:AdministrativeArea {
    ags: "11000000",
    name: "Berlin",
    type: "land",
    geometry: "POLYGON(...)"
})

CREATE (court:Institution {
    name: "VG Berlin",
    type: "gericht",
    latitude: 52.5170,
    longitude: 13.3888
})

-- Räumliche Beziehungen
CREATE (doc)-[:LOCATED_IN]->(area)
CREATE (doc)-[:UNDER_JURISDICTION_OF]->(court)
CREATE (court)-[:COVERS_AREA]->(area)

-- Spatial-Index in Neo4j
CREATE INDEX spatial_documents FOR (n:Document) ON (n.latitude, n.longitude)
```

**C) Vector DB (ChromaDB mit Geo-Embeddings):**

```python
# Erweiterte Metadaten für ChromaDB
geo_metadata = {
    "document_id": "doc_12345",
    "location_lat": 52.5200,
    "location_lng": 13.4050,
    "administrative_areas": ["Berlin", "Mitte", "Deutschland"],
    "geo_tags": ["urban", "hauptstadt", "zentral"],
    "spatial_context": "berlin_city_center",
    "geo_quality": 0.95
}

# Geo-enhanced Embeddings (Text + Geo-Kontext)
text_content = "Baugenehmigung für Wohngebäude in Berlin-Mitte"
geo_context = "Berlin, Deutschland, Hauptstadt, Urban, Zentral"
combined_text = f"{text_content} [GEO: {geo_context}]"
```

### 2.2 Metadatenbank-Erweiterung

**Erweiterte Metadaten-Typen:**

```python
# Neue Metadaten-Kategorien in UDS3
class MetadataType(Enum):
    # Bestehende
    LEGAL = "legal"
    ADMINISTRATIVE = "administrative" 
    TEMPORAL = "temporal"
    
    # NEUE GEODATEN-METADATEN
    GEOGRAPHIC = "geographic"
    SPATIAL_REFERENCE = "spatial_reference"
    ADMINISTRATIVE_GEOGRAPHY = "administrative_geography"
    TOPOLOGICAL = "topological"
    
    # ERWEITERTE METADATENBANKEN
    BIBLIOGRAPHIC = "bibliographic"      # Bibliothekswesen
    SEMANTIC_WEB = "semantic_web"        # RDF/OWL Ontologien
    PROVENANCE = "provenance"            # Datenherkunft
    QUALITY_METRICS = "quality_metrics"  # Datenqualität
    USAGE_ANALYTICS = "usage_analytics"  # Nutzungsstatistiken
```

## 3. Implementierung

### 3.1 UDS3 Geo-Extension Module

```python
#!/usr/bin/env python3
"""
uds3_geo_extension.py - Geodaten-Erweiterung für UDS3
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
import json
from shapely.geometry import Point, Polygon, LineString
from geopy.geocoders import Nominatim
import logging

@dataclass
class GeoLocation:
    """Standardisierte Geo-Location für UDS3"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy_meters: Optional[int] = None
    coordinate_system: str = "EPSG:4326"
    source: Optional[str] = None
    quality_score: Optional[float] = None

@dataclass
class AdministrativeArea:
    """Verwaltungsgebiet mit Geodaten"""
    ags: str                    # Amtlicher Gemeindeschlüssel
    name: str
    area_type: str             # bund, land, kreis, gemeinde
    parent_ags: Optional[str]
    population: Optional[int]
    area_km2: Optional[float]
    geometry: Optional[str]    # WKT-Format

class UDS3GeoManager:
    """
    Geodaten-Manager für UDS3 Integration
    """
    
    def __init__(self, uds3_core, postgis_connection=None):
        self.uds3 = uds3_core
        self.postgis = postgis_connection
        self.geocoder = Nominatim(user_agent="uds3-geo-extension")
        self.logger = logging.getLogger(__name__)
    
    def extract_location_from_document(self, document: Dict) -> Optional[GeoLocation]:
        """
        Extrahiert Geo-Informationen aus Dokumententext
        
        Strategien:
        1. Explizite Koordinaten
        2. Adressen (mit Geocoding)
        3. Ortsnamen
        4. Postleitzahlen
        5. Gerichts-/Behördenzuordnung
        """
        
        content = document.get('content', '')
        title = document.get('title', '')
        
        # 1. Koordinaten direkt extrahieren
        location = self._extract_coordinates(content + ' ' + title)
        if location:
            return location
            
        # 2. Adressen geocodieren
        addresses = self._extract_addresses(content + ' ' + title)
        for address in addresses:
            location = self._geocode_address(address)
            if location:
                return location
        
        # 3. Gerichts-/Behördenzuordnung
        institution = document.get('gericht') or document.get('behoerde')
        if institution:
            return self._get_institution_location(institution)
        
        return None
    
    def add_geo_metadata(self, document_id: str, location: GeoLocation, 
                        administrative_areas: List[str] = None) -> bool:
        """Fügt Geodaten zu einem UDS3-Dokument hinzu"""
        
        try:
            # Relational DB: PostGIS Update
            if self.postgis:
                self._update_postgis_location(document_id, location)
            
            # Graph DB: Geo-Beziehungen
            if self.uds3.graph_backend:
                self._create_geo_relationships(document_id, location, administrative_areas)
            
            # Vector DB: Geo-Context in Embeddings
            if self.uds3.vector_backend:
                self._update_geo_embeddings(document_id, location, administrative_areas)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding geo metadata: {e}")
            return False
    
    def spatial_search(self, center: GeoLocation, radius_km: float,
                      document_filters: Dict = None) -> List[Dict]:
        """
        Räumliche Suche nach Dokumenten
        
        Args:
            center: Mittelpunkt der Suche
            radius_km: Suchradius in Kilometern
            document_filters: Zusätzliche Filter (rechtsgebiet, etc.)
        """
        
        if not self.postgis:
            return []
        
        # PostGIS Spatial Query
        query = """
        SELECT d.*, ST_Distance_Sphere(d.location_point, ST_Point(%s, %s)) as distance_m
        FROM documents d
        WHERE ST_DWithin(
            d.location_point::geography, 
            ST_Point(%s, %s)::geography, 
            %s
        )
        ORDER BY distance_m
        """
        
        params = [
            center.longitude, center.latitude,  # ST_Point Parameter
            center.longitude, center.latitude,  # ST_DWithin Parameter  
            radius_km * 1000  # Radius in Metern
        ]
        
        # Zusätzliche Filter
        if document_filters:
            filter_conditions = []
            for key, value in document_filters.items():
                filter_conditions.append(f"d.{key} = %s")
                params.append(value)
            
            if filter_conditions:
                query = query.replace("ORDER BY", f"AND {' AND '.join(filter_conditions)} ORDER BY")
        
        # Execute Query (Implementation abhängig von DB-Driver)
        results = self._execute_postgis_query(query, params)
        return results
    
    def get_administrative_hierarchy(self, document_id: str) -> List[AdministrativeArea]:
        """Ermittelt die vollständige Verwaltungshierarchie eines Dokuments"""
        
        # Von Gemeinde bis Bund
        hierarchy_query = """
        WITH RECURSIVE admin_tree AS (
            -- Start mit dem Dokument
            SELECT aa.* FROM administrative_areas aa
            JOIN documents d ON ST_Within(d.location_point, aa.geometry)
            WHERE d.id = %s AND aa.area_type = 'gemeinde'
            
            UNION ALL
            
            -- Rekursiv nach oben
            SELECT parent.* FROM administrative_areas parent
            JOIN admin_tree child ON parent.id = child.parent_id
        )
        SELECT * FROM admin_tree ORDER BY 
            CASE area_type 
                WHEN 'gemeinde' THEN 4 
                WHEN 'kreis' THEN 3 
                WHEN 'land' THEN 2 
                WHEN 'bund' THEN 1 
            END
        """
        
        return self._execute_postgis_query(hierarchy_query, [document_id])
```

### 3.2 Database Backend Erweiterungen

**A) PostGIS Backend (database_api_postgis.py):**

```python
from database_api_base import RelationalDatabaseBackend
import psycopg2
from psycopg2.extras import RealDictCursor

class PostGISBackend(RelationalDatabaseBackend):
    """PostgreSQL + PostGIS Backend für Geodaten"""
    
    def __init__(self, config):
        super().__init__(config)
        self.connection = None
    
    def connect(self):
        """Verbindung mit PostGIS-Extensions"""
        try:
            self.connection = psycopg2.connect(
                host=self.config.get('host', 'localhost'),
                database=self.config.get('database', 'uds3_geo'),
                user=self.config.get('user', 'postgres'),
                password=self.config.get('password', ''),
                cursor_factory=RealDictCursor
            )
            
            # PostGIS Extension aktivieren
            with self.connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
                self.connection.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"PostGIS connection failed: {e}")
            return False
    
    def spatial_query(self, query: str, params: List = None) -> List[Dict]:
        """Führt räumliche Abfragen aus"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or [])
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Spatial query failed: {e}")
            return []
    
    def insert_with_geometry(self, table: str, data: Dict, 
                           geometry_field: str, wkt_geometry: str):
        """Einfügen mit Geometrie-Daten"""
        
        fields = list(data.keys()) + [geometry_field]
        placeholders = ['%s'] * len(data) + [f'ST_GeomFromText(%s, 4326)']
        values = list(data.values()) + [wkt_geometry]
        
        query = f"""
        INSERT INTO {table} ({', '.join(fields)})
        VALUES ({', '.join(placeholders)})
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(query, values)
            self.connection.commit()
```

**B) Neo4j Spatial Backend (Erweiterung):**

```python
# Erweiterung von database_api_neo4j.py
def create_spatial_relationship(self, doc_id: str, location: GeoLocation, 
                              admin_areas: List[str]):
    """Erstellt räumliche Beziehungen in Neo4j"""
    
    # Dokument-Knoten mit Geo-Properties
    cypher = """
    MERGE (doc:Document {id: $doc_id})
    SET doc.latitude = $lat,
        doc.longitude = $lng,
        doc.geo_quality = $quality
    """
    
    self.session.run(cypher, {
        'doc_id': doc_id,
        'lat': location.latitude,
        'lng': location.longitude,
        'quality': location.quality_score or 0.5
    })
    
    # Verbindungen zu Verwaltungsgebieten
    for area_name in admin_areas:
        cypher = """
        MATCH (doc:Document {id: $doc_id})
        MERGE (area:AdministrativeArea {name: $area_name})
        MERGE (doc)-[:LOCATED_IN]->(area)
        """
        self.session.run(cypher, {'doc_id': doc_id, 'area_name': area_name})

def spatial_search_neo4j(self, center_lat: float, center_lng: float, 
                        radius_km: float) -> List[Dict]:
    """Neo4j Spatial Search mit Haversine-Distanz"""
    
    cypher = """
    MATCH (doc:Document)
    WHERE doc.latitude IS NOT NULL AND doc.longitude IS NOT NULL
    WITH doc, 
         point({latitude: doc.latitude, longitude: doc.longitude}) AS doc_point,
         point({latitude: $center_lat, longitude: $center_lng}) AS center_point
    WITH doc, distance(doc_point, center_point) AS distance_m
    WHERE distance_m <= $radius_m
    RETURN doc, distance_m
    ORDER BY distance_m
    """
    
    result = self.session.run(cypher, {
        'center_lat': center_lat,
        'center_lng': center_lng,
        'radius_m': radius_km * 1000
    })
    
    return [dict(record) for record in result]
```

### 3.3 UDS3 Core Integration

**Erweiterte UDS3-Core Klasse:**

```python
# Erweiterung in uds3_core.py

from uds3_geo_extension import UDS3GeoManager, GeoLocation

class UDS3CoreWithGeo(UDS3CoreSystem):
    """UDS3 mit Geodaten-Unterstützung"""
    
    def __init__(self, config_path: str = None):
        super().__init__(config_path)
        
        # Geo-Manager initialisieren
        postgis_config = self.config.get('databases', {}).get('postgis', {})
        postgis_backend = None
        
        if postgis_config.get('enabled'):
            from database_api_postgis import PostGISBackend
            postgis_backend = PostGISBackend(postgis_config)
            postgis_backend.connect()
        
        self.geo_manager = UDS3GeoManager(self, postgis_backend)
    
    def store_document_with_geo(self, content: str, title: str, 
                               metadata: Dict, location: GeoLocation = None) -> str:
        """Speichert Dokument mit automatischer Geo-Extraktion"""
        
        # Standard UDS3 Speicherung
        doc_id = self.store_document(content, title, metadata)
        
        # Geo-Location automatisch extrahieren wenn nicht gegeben
        if not location:
            document = {'content': content, 'title': title, **metadata}
            location = self.geo_manager.extract_location_from_document(document)
        
        # Geodaten hinzufügen
        if location:
            admin_areas = self.geo_manager.get_administrative_hierarchy_by_location(location)
            area_names = [area.name for area in admin_areas]
            
            success = self.geo_manager.add_geo_metadata(doc_id, location, area_names)
            if success:
                self.logger.info(f"Geo metadata added for document {doc_id}")
        
        return doc_id
    
    def search_by_location(self, center_lat: float, center_lng: float,
                          radius_km: float, additional_filters: Dict = None) -> List[Dict]:
        """Räumliche Dokumentensuche"""
        
        center = GeoLocation(center_lat, center_lng)
        return self.geo_manager.spatial_search(center, radius_km, additional_filters)
    
    def get_document_geography(self, doc_id: str) -> Dict:
        """Vollständige geografische Informationen eines Dokuments"""
        
        return {
            'location': self.geo_manager.get_document_location(doc_id),
            'administrative_hierarchy': self.geo_manager.get_administrative_hierarchy(doc_id),
            'nearby_institutions': self.geo_manager.get_nearby_institutions(doc_id, 10),
            'related_documents': self.search_by_location_of_document(doc_id, 5)
        }
```

## 4. Anwendungsfälle und Nutzen

### 4.1 Legal Tech Anwendungen

**A) Räumliche Rechtsprechungsanalyse:**
```python
# Beispiel: Alle Baugenehmigungen im 5km Umkreis um ein Projekt
project_location = GeoLocation(52.5200, 13.4050)  # Berlin
building_permits = uds3.search_by_location(
    52.5200, 13.4050, 5.0,
    {'rechtsgebiet': 'Baurecht', 'dokumenttyp': 'Genehmigung'}
)
```

**B) Zuständigkeitsermittlung:**
```python
# Welches Gericht ist für diese Koordinaten zuständig?
jurisdiction = uds3.geo_manager.get_jurisdiction(
    GeoLocation(51.3397, 12.3731)  # Leipzig
)
```

**C) Verwaltungsgeografie:**
```python
# Vollständige Verwaltungshierarchie eines Falls
hierarchy = uds3.get_document_geography("case_12345")
# Ergebnis: [Bund -> Sachsen -> Leipzig -> Mitte]
```

### 4.2 Datenqualität und Metadatenbanken

**Erweiterte Metadaten-Pipeline:**

```python
class EnhancedMetadataManager:
    """Erweiterte Metadaten-Verwaltung für UDS3"""
    
    def __init__(self):
        self.metadata_schemas = {
            'dublin_core': DublinCoreSchema(),
            'legal_metadata': LegalMetadataSchema(),
            'geo_metadata': GeoMetadataSchema(),
            'provenance': ProvenanceSchema(),
            'quality_metrics': QualityMetricsSchema()
        }
    
    def enrich_document_metadata(self, doc_id: str) -> Dict:
        """Reichert Dokument mit allen verfügbaren Metadatentypen an"""
        
        enriched = {}
        
        # Bibliografische Metadaten
        enriched['bibliographic'] = self.extract_bibliographic_metadata(doc_id)
        
        # Provenance (Datenherkunft)
        enriched['provenance'] = self.track_document_provenance(doc_id)
        
        # Qualitätsmetriken
        enriched['quality'] = self.calculate_quality_metrics(doc_id)
        
        # Semantic Web (RDF/OWL)
        enriched['semantic'] = self.generate_rdf_triples(doc_id)
        
        # Nutzungsstatistiken
        enriched['usage'] = self.get_usage_analytics(doc_id)
        
        return enriched
```

### 4.3 Performance und Skalierung

**Spatial Indexing Strategy:**

```sql
-- Multi-Level Spatial Indexing
CREATE INDEX CONCURRENTLY idx_documents_geo_country 
    ON documents USING GIST (location_point) 
    WHERE country = 'Deutschland';

CREATE INDEX CONCURRENTLY idx_documents_geo_state 
    ON documents USING GIST (location_point, state);

CREATE INDEX CONCURRENTLY idx_documents_geo_admin_level 
    ON documents (administrative_level, postal_code) 
    WHERE location_point IS NOT NULL;

-- Partitionierung nach Bundesländern
CREATE TABLE documents_by_state (LIKE documents INCLUDING ALL)
PARTITION BY LIST (state);

CREATE TABLE documents_nrw PARTITION OF documents_by_state 
    FOR VALUES IN ('Nordrhein-Westfalen');
```

## 5. Implementierungsroadmap

### Phase 1: Grundlagen (Wochen 1-2)
- ✅ PostGIS Backend implementieren
- ✅ Geo-Extension Modul erstellen
- ✅ Basic Spatial Queries

### Phase 2: Integration (Wochen 3-4)  
- ✅ UDS3 Core Erweiterung
- ✅ Neo4j Spatial Support
- ✅ ChromaDB Geo-Embeddings

### Phase 3: Features (Wochen 5-6)
- ✅ Automatische Geo-Extraktion
- ✅ Verwaltungshierarchie-Mapping
- ✅ Spatial Search API

### Phase 4: Optimierung (Wochen 7-8)
- ✅ Performance Tuning
- ✅ Erweiterte Metadaten-Pipelines
- ✅ Qualitätskontrolle

## 6. Technische Anforderungen

### Software-Dependencies:
```bash
pip install psycopg2-binary postgis shapely geopy folium geopandas
```

### Database-Setup:
```bash
# PostgreSQL + PostGIS
sudo apt install postgresql postgresql-contrib postgis

# Neo4j Spatial Plugin
# Automatisch verfügbar in Neo4j 4.0+
```

### Configuration (server_config.json):
```json
{
  "databases": {
    "postgis": {
      "enabled": true,
      "host": "localhost", 
      "database": "uds3_geo",
      "user": "postgres",
      "password": "secure_password"
    },
    "neo4j": {
      "enabled": true,
      "uri": "bolt://localhost:7687",
      "spatial_enabled": true
    }
  },
  "geo_settings": {
    "default_srid": 4326,
    "geocoding_service": "nominatim",
    "auto_extract_location": true,
    "quality_threshold": 0.7
  }
}
```

---

**Dieses Konzept erweitert UDS3 um eine vollständige Geodaten-Dimension und macht es zur führenden Lösung für geografisch-bewusste Rechtsdokument-Verwaltung in Deutschland.**
