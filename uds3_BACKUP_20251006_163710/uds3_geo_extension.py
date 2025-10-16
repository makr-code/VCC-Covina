#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
result: Any = None
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_geo_extension"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
)
module_file_key = "e1c351f109759ee4e5f933b15bfd46984b4200cc9ec7750ed978bf720ca7b106"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""


"""
UDS3 Geodaten-Erweiterung - Implementierung
============================================

Erweitert das Unified Database Strategy v3.0 System um umfassende Geodaten-Funktionalität:

- PostGIS Integration für räumliche Datenbank-Operationen
- Neo4j Spatial für geografische Beziehungsmodellierung  
- Automatische Geo-Extraktion aus Dokumenteninhalten
- Verwaltungsgeografie und Zuständigkeitserkennung
- Erweiterte Metadaten-Pipeline

Autor: Veritas UDS3 Team
Datum: 22. August 2025
Version: 1.0
"""

import logging
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import hashlib

# Geo-Libraries
try:
    from shapely.geometry import Point, Polygon, LineString
    from shapely.wkt import loads as wkt_loads
    from geopy.geocoders import Nominatim
    from geopy.distance import geodesic

    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    print(
        "Warning: Geopy/Shapely not available. Install with: pip install geopy shapely"
    )

# Database Backends
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    POSTGIS_AVAILABLE = True
except ImportError:
    POSTGIS_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "PostGIS client libraries not available. Install with: pip install psycopg2-binary"
    )

logger = logging.getLogger(__name__)


class GeoDataType(Enum):
    """Geodaten-Typen"""

    POINT = "point"
    POLYGON = "polygon"
    LINESTRING = "linestring"
    MULTIPOINT = "multipoint"
    MULTIPOLYGON = "multipolygon"


class AdministrativeLevel(Enum):
    """Deutsche Verwaltungsebenen"""

    BUND = 1
    LAND = 2
    REGIERUNGSBEZIRK = 3
    KREIS = 4
    GEMEINDE = 5
    ORTSTEIL = 6


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

    def to_wkt(self) -> str:
        """Konvertiert zu Well-Known Text Format"""
        if self.altitude:
            return f"POINT Z ({self.longitude} {self.latitude} {self.altitude})"
        return f"POINT ({self.longitude} {self.latitude})"

    def distance_to(self, other: "GeoLocation") -> float:
        """Berechnet Entfernung zu anderem Punkt in Kilometern"""
        if not GEOPY_AVAILABLE:
            # Vereinfachte Berechnung
            import math

            dlat = math.radians(other.latitude - self.latitude)
            dlon = math.radians(other.longitude - self.longitude)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(self.latitude))
                * math.cos(math.radians(other.latitude))
                * math.sin(dlon / 2) ** 2
            )
            return 6371.0 * 2 * math.asin(math.sqrt(a))  # Erdradius in km

        return geodesic(
            (self.latitude, self.longitude), (other.latitude, other.longitude)
        ).kilometers


@dataclass
class AdministrativeArea:
    """Deutsches Verwaltungsgebiet"""

    ags: str  # Amtlicher Gemeindeschlüssel
    name: str
    area_type: AdministrativeLevel
    parent_ags: Optional[str] = None
    population: Optional[int] = None
    area_km2: Optional[float] = None
    geometry_wkt: Optional[str] = None

    def get_hierarchy_level(self) -> int:
        """Gibt die Hierarchieebene zurück"""
        return self.area_type.value


@dataclass
class Institution:
    """Gericht/Behörde mit geografischen Daten"""

    id: str
    name: str
    institution_type: str  # 'gericht', 'behoerde', 'ministerium'
    address: Optional[str] = None
    location: Optional[GeoLocation] = None
    jurisdiction_area_wkt: Optional[str] = None
    administrative_area_ags: Optional[str] = None
    contact_info: Optional[Dict] = None


class PostGISBackend:
    """PostgreSQL + PostGIS Backend für geografische Datenhaltung"""

    def __init__(self, config: Dict):
        # Merge zentrale defaults mit übergebenem config-Dict
        def _merge_db_config(local_cfg: dict, key: str) -> dict:
            try:
                from . import config as _config

                base = dict(_config.DATABASES.get(key, {}))
            except Exception:
                base: dict[Any, Any] = {}

            if not isinstance(local_cfg, dict):
                return base

            merged = dict(base)
            merged.update(local_cfg)
            return merged

        self.config = _merge_db_config(config or {}, "postgis")
        self.connection = None
        self.logger = logging.getLogger(f"{__name__}.PostGISBackend")

    def connect(self) -> bool:
        """Stellt Verbindung zu PostGIS her"""
        if not POSTGIS_AVAILABLE:
            self.logger.error("PostGIS dependencies not available")
            return False

        try:
            self.connection = psycopg2.connect(
                host=self.config.get("host"),
                database=self.config.get("database"),
                user=self.config.get("user"),
                password=self.config.get("password"),
                cursor_factory=RealDictCursor,
                connect_timeout=self.config.get("connect_timeout", 10),
            )

            # PostGIS Extensions aktivieren
            with self.connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
                self.connection.commit()

            self.logger.info("PostGIS connection established")
            return True

        except Exception as e:
            self.logger.error(f"PostGIS connection failed: {e}")
            return False

    def initialize_schema(self) -> bool:
        """Erstellt die Geodaten-Tabellen"""
        if not self.connection:
            return False

        try:
            with self.connection.cursor() as cursor:
                # Documents-Tabelle mit Geodaten
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents_geo (
                        id VARCHAR(64) PRIMARY KEY,
                        title VARCHAR(500) NOT NULL,
                        file_path VARCHAR(1000),
                        rechtsgebiet VARCHAR(200),
                        gericht VARCHAR(200),
                        
                        -- Geodaten
                        location_point GEOMETRY(POINT, 4326),
                        location_polygon GEOMETRY(POLYGON, 4326),
                        administrative_level INTEGER,
                        postal_code VARCHAR(10),
                        municipality VARCHAR(100),
                        district VARCHAR(100),
                        state VARCHAR(50),
                        country VARCHAR(50) DEFAULT 'Deutschland',
                        
                        -- Geo-Metadaten
                        coordinate_system VARCHAR(20) DEFAULT 'EPSG:4326',
                        location_accuracy INTEGER,
                        location_source VARCHAR(100),
                        geo_quality_score DECIMAL(3,2),
                        
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Administrative Gebiete
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS administrative_areas (
                        ags VARCHAR(20) PRIMARY KEY,
                        name VARCHAR(200) NOT NULL,
                        area_type INTEGER NOT NULL,
                        parent_ags VARCHAR(20),
                        population INTEGER,
                        area_km2 DECIMAL(10,2),
                        geometry GEOMETRY(MULTIPOLYGON, 4326),
                        
                        FOREIGN KEY (parent_ags) REFERENCES administrative_areas(ags)
                    )
                """)

                # Institutionen (Gerichte/Behörden)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS institutions (
                        id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(200) NOT NULL,
                        institution_type VARCHAR(50),
                        address TEXT,
                        location GEOMETRY(POINT, 4326),
                        jurisdiction_area GEOMETRY(MULTIPOLYGON, 4326),
                        administrative_area_ags VARCHAR(20),
                        contact_info JSONB,
                        
                        FOREIGN KEY (administrative_area_ags) REFERENCES administrative_areas(ags)
                    )
                """)

                # Spatial Indizes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_point ON documents_geo USING GIST (location_point)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_polygon ON documents_geo USING GIST (location_polygon)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_admin_areas_geometry ON administrative_areas USING GIST (geometry)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_institutions_location ON institutions USING GIST (location)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_institutions_jurisdiction ON institutions USING GIST (jurisdiction_area)"
                )

                self.connection.commit()
                self.logger.info("PostGIS schema initialized")
                return True

        except Exception as e:
            self.logger.error(f"Schema initialization failed: {e}")
            return False

    def insert_document_geo(
        self, doc_id: str, title: str, location: GeoLocation, metadata: Optional[Dict[Any, Any]] = None
    ) -> bool:
        """Fügt Dokument mit Geodaten ein"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO documents_geo (
                        id, title, location_point, 
                        coordinate_system, location_accuracy, location_source, geo_quality_score,
                        rechtsgebiet, gericht, postal_code, municipality, district, state
                    ) VALUES (
                        %s, %s, ST_Point(%s, %s),
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        location_point = EXCLUDED.location_point,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    [
                        doc_id,
                        title,
                        location.longitude,
                        location.latitude,
                        location.coordinate_system,
                        location.accuracy_meters,
                        location.source,
                        location.quality_score,
                        metadata.get("rechtsgebiet") if metadata else None,
                        metadata.get("gericht") if metadata else None,
                        metadata.get("postal_code") if metadata else None,
                        metadata.get("municipality") if metadata else None,
                        metadata.get("district") if metadata else None,
                        metadata.get("state") if metadata else None,
                    ],
                )

                self.connection.commit()
                return True

        except Exception as e:
            self.logger.error(f"Failed to insert document geo: {e}")
            return False

    def spatial_search(
        self,
        center: GeoLocation,
        radius_km: float,
        filters: Optional[Dict[Any, Any]] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Räumliche Suche nach Dokumenten"""
        try:
            # Base Query
            query = """
                SELECT 
                    id, title, rechtsgebiet, gericht,
                    ST_X(location_point) as longitude,
                    ST_Y(location_point) as latitude,
                    ST_Distance_Sphere(location_point, ST_Point(%s, %s)) as distance_m
                FROM documents_geo
                WHERE ST_DWithin(
                    location_point::geography,
                    ST_Point(%s, %s)::geography,
                    %s
                )
            """

            params = [
                center.longitude,
                center.latitude,  # Distance calculation
                center.longitude,
                center.latitude,  # ST_DWithin center
                radius_km * 1000,  # Radius in meters
            ]

            # Additional filters
            if filters:
                filter_conditions: list[Any] = []
                for key, value in filters.items():
                    if key in ["rechtsgebiet", "gericht", "state", "municipality"]:
                        filter_conditions.append(f"{key} ILIKE %s")
                        params.append(f"%{value}%")

                if filter_conditions:
                    query += " AND " + " AND ".join(filter_conditions)

            query += f" ORDER BY distance_m LIMIT {limit}"

            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

        except Exception as e:
            self.logger.error(f"Spatial search failed: {e}")
            return []

    def get_administrative_hierarchy(
        self, location: GeoLocation
    ) -> List[AdministrativeArea]:
        """Ermittelt Verwaltungshierarchie für eine Position"""
        try:
            query = """
                WITH RECURSIVE admin_hierarchy AS (
                    -- Find the lowest level (Gemeinde)
                    SELECT ags, name, area_type, parent_ags, population, area_km2,
                           ST_AsText(geometry) as geometry_wkt
                    FROM administrative_areas
                    WHERE ST_Contains(geometry, ST_Point(%s, %s))
                      AND area_type = 5  -- Gemeinde
                    
                    UNION ALL
                    
                    -- Recursively find parents
                    SELECT p.ags, p.name, p.area_type, p.parent_ags, 
                           p.population, p.area_km2, ST_AsText(p.geometry)
                    FROM administrative_areas p
                    JOIN admin_hierarchy h ON p.ags = h.parent_ags
                )
                SELECT * FROM admin_hierarchy
                ORDER BY area_type DESC  -- From Bund to Gemeinde
            """

            with self.connection.cursor() as cursor:
                cursor.execute(query, [location.longitude, location.latitude])
                results = cursor.fetchall()

                return [
                    AdministrativeArea(
                        ags=row["ags"],
                        name=row["name"],
                        area_type=AdministrativeLevel(row["area_type"]),
                        parent_ags=row["parent_ags"],
                        population=row["population"],
                        area_km2=float(row["area_km2"]) if row["area_km2"] else None,
                        geometry_wkt=row["geometry_wkt"],
                    )
                    for row in results
                ]

        except Exception as e:
            self.logger.error(f"Failed to get administrative hierarchy: {e}")
            return []


class GeoLocationExtractor:
    """Extrahiert geografische Informationen aus Dokumenteninhalten"""

    def __init__(self):
        self.geocoder = (
            Nominatim(user_agent="uds3-geo-extractor") if GEOPY_AVAILABLE else None
        )
        self.logger = logging.getLogger(f"{__name__}.GeoLocationExtractor")

        # Deutsche Postleitzahlen-Pattern
        self.plz_pattern = re.compile(r"\b\d{5}\b")

        # Koordinaten-Pattern
        self.coord_patterns = [
            re.compile(
                r"(\d{1,2}[.,]\d+)°?\s*N,?\s*(\d{1,2}[.,]\d+)°?\s*E", re.IGNORECASE
            ),
            re.compile(
                r"Lat:\s*(\d{1,2}[.,]\d+),?\s*Lon[g]?:\s*(\d{1,2}[.,]\d+)",
                re.IGNORECASE,
            ),
            re.compile(r"(\d{1,2}[.,]\d+),\s*(\d{1,2}[.,]\d+)"),  # Decimal coordinates
        ]

        # Deutsche Städte-Pattern (Top 100)
        self.major_cities = [
            "Berlin",
            "Hamburg",
            "München",
            "Köln",
            "Frankfurt",
            "Stuttgart",
            "Düsseldorf",
            "Dortmund",
            "Essen",
            "Leipzig",
            "Bremen",
            "Dresden",
            "Hannover",
            "Nürnberg",
            "Duisburg",
            "Bochum",
            "Wuppertal",
            "Bielefeld",
            # ... weitere Städte können hinzugefügt werden
        ]

    def extract_from_document(
        self, content: str, title: str, metadata: Optional[Dict[Any, Any]] = None
    ) -> Optional[GeoLocation]:
        """Hauptmethode zur Geo-Extraktion aus Dokumenten"""

        full_text = f"{title} {content}"

        # 1. Direkte Koordinaten
        location = self._extract_coordinates(full_text)
        if location:
            location.source = "coordinates_extracted"
            location.quality_score = 0.95
            return location

        # 2. Postleitzahlen geocodieren
        location = self._geocode_postal_codes(full_text)
        if location:
            location.source = "postal_code_geocoded"
            location.quality_score = 0.80
            return location

        # 3. Städte/Ortsnamen
        location = self._geocode_cities(full_text)
        if location:
            location.source = "city_geocoded"
            location.quality_score = 0.70
            return location

        # 4. Institutionen (Gerichte/Behörden)
        if metadata:
            gericht = metadata.get("gericht")
            if gericht:
                location = self._geocode_institution(gericht)
                if location:
                    location.source = "institution_geocoded"
                    location.quality_score = 0.85
                    return location

        return None

    def _extract_coordinates(self, text: str) -> Optional[GeoLocation]:
        """Extrahiert direkte Koordinaten aus Text"""
        for pattern in self.coord_patterns:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    lat = float(match[0].replace(",", "."))
                    lng = float(match[1].replace(",", "."))

                    # Plausibilitätsprüfung für Deutschland
                    if 47.0 <= lat <= 55.5 and 5.5 <= lng <= 15.5:
                        return GeoLocation(
                            latitude=lat, longitude=lng, accuracy_meters=100
                        )
                except (ValueError, IndexError):
                    continue
        return None

    def _geocode_postal_codes(self, text: str) -> Optional[GeoLocation]:
        """Geocodiert deutsche Postleitzahlen"""
        if not self.geocoder:
            return None

        plz_matches = self.plz_pattern.findall(text)
        for plz in plz_matches:
            try:
                location = self.geocoder.geocode(f"{plz}, Deutschland")
                if location:
                    return GeoLocation(
                        latitude=location.latitude,
                        longitude=location.longitude,
                        accuracy_meters=5000,  # PLZ-Genauigkeit
                    )
            except Exception as e:
                self.logger.debug(f"Geocoding failed for PLZ {plz}: {e}")
                continue
        return None

    def _geocode_cities(self, text: str) -> Optional[GeoLocation]:
        """Geocodiert bekannte deutsche Städte"""
        if not self.geocoder:
            return None

        text_upper = text.upper()
        for city in self.major_cities:
            if city.upper() in text_upper:
                try:
                    location = self.geocoder.geocode(f"{city}, Deutschland")
                    if location:
                        return GeoLocation(
                            latitude=location.latitude,
                            longitude=location.longitude,
                            accuracy_meters=10000,  # Stadt-Genauigkeit
                        )
                except Exception as e:
                    self.logger.debug(f"Geocoding failed for city {city}: {e}")
                    continue
        return None

    def _geocode_institution(self, institution_name: str) -> Optional[GeoLocation]:
        """Geocodiert Gerichte und Behörden"""
        if not self.geocoder:
            return None

        try:
            # Spezielle Behandlung für deutsche Gerichte
            if any(
                term in institution_name.lower()
                for term in [
                    "gericht",
                    "amtsgericht",
                    "landgericht",
                    "oberlandesgericht",
                ]
            ):
                location = self.geocoder.geocode(f"{institution_name}, Deutschland")
                if location:
                    return GeoLocation(
                        latitude=location.latitude,
                        longitude=location.longitude,
                        accuracy_meters=1000,
                    )
        except Exception as e:
            self.logger.debug(
                f"Geocoding failed for institution {institution_name}: {e}"
            )

        return None


class UDS3GeoManager:
    """
    Hauptklasse für Geodaten-Management in UDS3

    Integriert PostGIS, Geo-Extraktion und erweiterte Metadaten
    in das bestehende UDS3-System.
    """

    def __init__(self, uds3_core, postgis_config: Optional[Dict[Any, Any]] = None):
        self.uds3 = uds3_core
        self.logger = logging.getLogger(f"{__name__}.UDS3GeoManager")

        # PostGIS Backend
        self.postgis = None
        if postgis_config and POSTGIS_AVAILABLE:
            self.postgis = PostGISBackend(postgis_config)
            if self.postgis.connect():
                self.postgis.initialize_schema()

        # Geo-Extraktor
        self.geo_extractor = GeoLocationExtractor()

        # Cache für Administrative Gebiete
        self.admin_areas_cache: dict[Any, Any] = {}

    def store_document_with_geo(
        self, content: str, title: str, metadata: Dict, location: GeoLocation = None
    ) -> str:
        """
        Speichert Dokument in UDS3 mit automatischer Geo-Extraktion

        Args:
            content: Dokumenteninhalt
            title: Dokumententitel
            metadata: Standard UDS3-Metadaten
            location: Optional - explizite Geo-Location

        Returns:
            Document ID
        """

        # Standard UDS3 Speicherung
        doc_id = self.uds3.store_document(content, title, metadata)

        # Geo-Location extrahieren wenn nicht gegeben
        if not location:
            location = self.geo_extractor.extract_from_document(
                content, title, metadata
            )

        # Geodaten hinzufügen
        if location:
            success = self._add_geo_metadata(doc_id, title, location, metadata)
            if success:
                self.logger.info(f"Geo metadata added for document {doc_id}")
            else:
                self.logger.warning(f"Failed to add geo metadata for document {doc_id}")
        else:
            self.logger.debug(f"No geo location found for document {doc_id}")

        return doc_id

    def _add_geo_metadata(
        self, doc_id: str, title: str, location: GeoLocation, metadata: Dict
    ) -> bool:
        """Fügt Geodaten zu allen relevanten Datenbanken hinzu"""

        success_count = 0
        total_operations = 0

        # PostGIS - Relational DB
        if self.postgis:
            total_operations += 1
            if self.postgis.insert_document_geo(doc_id, title, location, metadata):
                success_count += 1

        # Neo4j - Graph DB
        if hasattr(self.uds3, "graph_backend") and self.uds3.graph_backend:
            total_operations += 1
            if self._add_neo4j_geo_relationship(doc_id, location):
                success_count += 1

        # ChromaDB - Vector DB (Geo-Context in Embeddings)
        if hasattr(self.uds3, "vector_backend") and self.uds3.vector_backend:
            total_operations += 1
            if self._update_vector_geo_context(doc_id, location):
                success_count += 1

        return (
            success_count > 0 and success_count >= total_operations * 0.5
        )  # Mindestens 50% Erfolg

    def _add_neo4j_geo_relationship(self, doc_id: str, location: GeoLocation) -> bool:
        """Fügt Geo-Beziehungen in Neo4j hinzu"""
        try:
            # Administrative Hierarchie ermitteln
            if self.postgis:
                admin_hierarchy = self.postgis.get_administrative_hierarchy(location)
            else:
                admin_hierarchy: list[Any] = []

            # Neo4j Cypher - Dokument mit Geo-Properties
            cypher = """
                MERGE (doc:Document {id: $doc_id})
                SET doc.latitude = $lat,
                    doc.longitude = $lng,
                    doc.geo_quality = $quality,
                    doc.geo_source = $source
            """

            self.uds3.graph_backend.session.run(
                cypher,
                {
                    "doc_id": doc_id,
                    "lat": location.latitude,
                    "lng": location.longitude,
                    "quality": location.quality_score or 0.5,
                    "source": location.source or "unknown",
                },
            )

            # Beziehungen zu Verwaltungsgebieten
            for area in admin_hierarchy:
                cypher_area = """
                    MATCH (doc:Document {id: $doc_id})
                    MERGE (area:AdministrativeArea {ags: $ags, name: $name, level: $level})
                    MERGE (doc)-[:LOCATED_IN]->(area)
                """

                self.uds3.graph_backend.session.run(
                    cypher_area,
                    {
                        "doc_id": doc_id,
                        "ags": area.ags,
                        "name": area.name,
                        "level": area.get_hierarchy_level(),
                    },
                )

            return True

        except Exception as e:
            self.logger.error(f"Failed to add Neo4j geo relationship: {e}")
            return False

    def _update_vector_geo_context(self, doc_id: str, location: GeoLocation) -> bool:
        """Aktualisiert Vector DB mit Geo-Kontext"""
        try:
            # Geo-Kontext für Embeddings erstellen
            geo_context_parts: list[Any] = []

            # Administrative Hierarchie als Kontext
            if self.postgis:
                admin_hierarchy = self.postgis.get_administrative_hierarchy(location)
                for area in admin_hierarchy:
                    geo_context_parts.append(area.name)

            # Koordinaten-basierte Kontexte
            geo_context_parts.append(
                f"Koordinaten: {location.latitude:.4f}, {location.longitude:.4f}"
            )
            geo_context_parts.append("Deutschland")  # Land-Kontext

            geo_context = " ".join(geo_context_parts)

            # Metadaten für ChromaDB aktualisieren
            if hasattr(self.uds3.vector_backend, "update_metadata"):
                geo_metadata = {
                    "geo_latitude": location.latitude,
                    "geo_longitude": location.longitude,
                    "geo_context": geo_context,
                    "geo_quality": location.quality_score or 0.5,
                    "geo_source": location.source or "extracted",
                }

                return self.uds3.vector_backend.update_metadata(doc_id, geo_metadata)

            return True

        except Exception as e:
            self.logger.error(f"Failed to update vector geo context: {e}")
            return False

    def spatial_search(
        self,
        center_lat: float,
        center_lng: float,
        radius_km: float,
        filters: Optional[Dict[Any, Any]] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Räumliche Suche nach Dokumenten

        Args:
            center_lat, center_lng: Mittelpunkt der Suche
            radius_km: Suchradius in Kilometern
            filters: Zusätzliche Filter (rechtsgebiet, gericht, etc.)
            limit: Maximale Anzahl Ergebnisse

        Returns:
            Liste von Dokumenten mit Entfernungsangaben
        """

        if not self.postgis:
            self.logger.warning("PostGIS not available for spatial search")
            return []

        center = GeoLocation(center_lat, center_lng)
        return self.postgis.spatial_search(center, radius_km, filters, limit)

    def get_document_geography(self, doc_id: str) -> Dict[str, Any]:
        """
        Ermittelt vollständige geografische Informationen eines Dokuments

        Returns:
            Dictionary mit Location, Administrative Hierarchie, etc.
        """

        result: Dict[str, Any] = {
            "document_id": doc_id,
            "location": None,
            "administrative_hierarchy": [],
            "nearby_documents": [],
            "jurisdiction_info": {},
        }

        if not self.postgis:
            return result

        try:
            # Dokument-Location aus PostGIS
            with self.postgis.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ST_X(location_point) as lng, ST_Y(location_point) as lat,
                           coordinate_system, location_accuracy, location_source, geo_quality_score
                    FROM documents_geo WHERE id = %s
                """,
                    [doc_id],
                )

                row = cursor.fetchone()
                if row and row["lat"] and row["lng"]:
                    result["location"] = {
                        "latitude": row["lat"],
                        "longitude": row["lng"],
                        "coordinate_system": row["coordinate_system"],
                        "accuracy_meters": row["location_accuracy"],
                        "source": row["location_source"],
                        "quality_score": float(row["geo_quality_score"])
                        if row["geo_quality_score"]
                        else None,
                    }

                    # Administrative Hierarchie
                    location = GeoLocation(row["lat"], row["lng"])
                    admin_hierarchy = self.postgis.get_administrative_hierarchy(
                        location
                    )
                    result["administrative_hierarchy"] = [
                        asdict(area) for area in admin_hierarchy
                    ]

                    # Nearby Documents (5km Radius)
                    nearby = self.spatial_search(row["lat"], row["lng"], 5.0, limit=10)
                    result["nearby_documents"] = [
                        doc for doc in nearby if doc["id"] != doc_id
                    ]

        except Exception as e:
            self.logger.error(f"Failed to get document geography for {doc_id}: {e}")

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Erstellt Geodaten-Statistiken"""

        stats = {
            "total_documents_with_geo": 0,
            "geo_sources": {},
            "quality_distribution": {},
            "administrative_levels": {},
            "spatial_coverage": {},
            "generated_at": datetime.now().isoformat(),
        }

        if not self.postgis:
            return stats

        try:
            with self.postgis.connection.cursor() as cursor:
                # Gesamtzahl georeferenzierte Dokumente
                cursor.execute(
                    "SELECT COUNT(*) FROM documents_geo WHERE location_point IS NOT NULL"
                )
                stats["total_documents_with_geo"] = cursor.fetchone()["count"]

                # Geo-Quellen
                cursor.execute("""
                    SELECT location_source, COUNT(*) 
                    FROM documents_geo 
                    WHERE location_point IS NOT NULL 
                    GROUP BY location_source
                """)
                stats["geo_sources"] = dict(cursor.fetchall())

                # Qualitätsverteilung
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN geo_quality_score >= 0.8 THEN 'high'
                            WHEN geo_quality_score >= 0.6 THEN 'medium'
                            ELSE 'low'
                        END as quality_level,
                        COUNT(*)
                    FROM documents_geo 
                    WHERE geo_quality_score IS NOT NULL
                    GROUP BY quality_level
                """)
                stats["quality_distribution"] = dict(cursor.fetchall())

                # Räumliche Abdeckung nach Bundesländern
                cursor.execute("""
                    SELECT state, COUNT(*) 
                    FROM documents_geo 
                    WHERE state IS NOT NULL 
                    GROUP BY state 
                    ORDER BY COUNT(*) DESC
                """)
                stats["spatial_coverage"] = dict(cursor.fetchall())

        except Exception as e:
            self.logger.error(f"Failed to generate geo statistics: {e}")

        return stats


# Utility Functions
def validate_geo_location(location: GeoLocation) -> bool:
    """Validiert eine Geo-Location für Deutschland"""
    if not location:
        return False

    # Deutschland Bounding Box
    if not (47.0 <= location.latitude <= 55.5):
        return False
    if not (5.5 <= location.longitude <= 15.5):
        return False

    return True


def create_geo_hash(location: GeoLocation, precision: int = 8) -> str:
    """Erstellt einen Geo-Hash für räumliche Indizierung"""

    coord_string = f"{location.latitude:.6f},{location.longitude:.6f}"
    return hashlib.md5(coord_string.encode()).hexdigest()[:precision]


# Export der wichtigsten Klassen
__all__ = [
    "GeoLocation",
    "AdministrativeArea",
    "Institution",
    "PostGISBackend",
    "GeoLocationExtractor",
    "UDS3GeoManager",
    "validate_geo_location",
    "create_geo_hash",
]