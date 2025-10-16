#!/usr/bin/env python3
"""
PostGIS Database Backend für UDS3 
=================================

PostgreSQL + PostGIS Backend Implementation für geografische Datenoperationen
im Unified Database Strategy v3.0 System.

Features:
- Vollständige PostGIS Integration
- Spatial Queries und Indexing
- Administrative Gebiete Management
- Institution/Jurisdiction Mapping
- Performance-optimierte Geodaten-Operationen

Erbt von database_api_base.RelationalDatabaseBackend für UDS3-Kompatibilität.

Autor: Veritas UDS3 Team
Datum: 22. August 2025
Version: 1.0
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    from psycopg2.sql import SQL, Identifier, Literal
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 not available. Install with: pip install psycopg2-binary")

# UDS3 Base Classes
try:
    from database.database_api_base import RelationalDatabaseBackend
    UDS3_BASE_AVAILABLE = True
except ImportError:
    UDS3_BASE_AVAILABLE = False
    # Fallback Base Class
    class RelationalDatabaseBackend:
        def __init__(self, config):
            self.config = config
            self.logger = logging.getLogger(__name__)

class PostGISBackend(RelationalDatabaseBackend):
    """
    PostgreSQL + PostGIS Backend für UDS3 Geodaten
    
    Implementiert vollständige räumliche Datenbank-Funktionalität
    mit optimierten Spatial Queries und Indexing.
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.connection = None
        self.cursor = None
        self.logger = logging.getLogger(f"{__name__}.PostGISBackend")
        
        # PostGIS spezifische Konfiguration
        self.default_srid = config.get('srid', 4326)  # WGS84
        self.enable_topology = config.get('topology', False)
        self.spatial_ref_sys = config.get('spatial_ref_sys', 'EPSG:4326')
        
    def connect(self) -> bool:
        """Stellt Verbindung zu PostgreSQL + PostGIS her"""
        if not PSYCOPG2_AVAILABLE:
            self.logger.error("psycopg2 not available - cannot connect to PostGIS")
            return False
        
        try:
            connection_params = {
                'host': self.config.get('host', 'localhost'),
                'port': self.config.get('port', 5432),
                'database': self.config.get('database', 'uds3_geo'),
                'user': self.config.get('user', 'postgres'),
                'password': self.config.get('password', ''),
                'cursor_factory': RealDictCursor
            }
            
            self.connection = psycopg2.connect(**connection_params)
            self.connection.autocommit = False
            
            # Extensions aktivieren
            self._enable_postgis_extensions()
            
            # Schema initialisieren falls gewünscht
            if self.config.get('auto_init_schema', True):
                self.initialize_spatial_schema()
            
            self.logger.info(f"PostGIS connection established: {connection_params['host']}:{connection_params['port']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to PostGIS: {e}")
            return False
    
    def _enable_postgis_extensions(self):
        """Aktiviert PostGIS und verwandte Extensions"""
        extensions = ['postgis', 'postgis_topology', 'fuzzystrmatch', 'postgis_tiger_geocoder']
        
        with self.connection.cursor() as cursor:
            for ext in extensions:
                try:
                    cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
                    self.logger.debug(f"Extension {ext} enabled")
                except Exception as e:
                    if ext == 'postgis':  # PostGIS ist kritisch
                        raise e
                    else:
                        self.logger.warning(f"Optional extension {ext} failed: {e}")
            
            self.connection.commit()
    
    def disconnect(self) -> bool:
        """Schließt PostGIS Verbindung"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
            self.logger.info("PostGIS connection closed")
            return True
        except Exception as e:
            self.logger.error(f"Error closing PostGIS connection: {e}")
            return False
    
    def initialize_spatial_schema(self) -> bool:
        """Erstellt das vollständige Geodaten-Schema"""
        try:
            with self.connection.cursor() as cursor:
                # === UDS3 CORE TABLES WITH GEO EXTENSION ===
                
                # Documents with Geo Fields
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS uds3_documents_geo (
                        -- UDS3 Standard Fields
                        id VARCHAR(64) PRIMARY KEY,
                        doc_uuid UUID UNIQUE DEFAULT gen_random_uuid(),
                        title VARCHAR(500) NOT NULL,
                        file_path VARCHAR(1000),
                        content_preview TEXT,
                        mime_type VARCHAR(100),
                        file_size BIGINT,
                        
                        -- Legal/Administrative Metadata
                        rechtsgebiet VARCHAR(200),
                        gericht VARCHAR(200),
                        aktenzeichen VARCHAR(200),
                        entscheidungsdatum DATE,
                        rechtskraft BOOLEAN,
                        
                        -- === GEODATEN FIELDS ===
                        -- Primary Location (Point)
                        location_point GEOMETRY(POINT, {self.default_srid}),
                        
                        -- Area/Polygon (für Grundstücke, Zuständigkeitsbereiche)
                        location_polygon GEOMETRY(MULTIPOLYGON, {self.default_srid}),
                        
                        -- Linear Features (Straßen, Grenzen, Leitungen)
                        location_linestring GEOMETRY(MULTILINESTRING, {self.default_srid}),
                        
                        -- Administrative Geography
                        administrative_level INTEGER CHECK (administrative_level BETWEEN 1 AND 6),
                        postal_code VARCHAR(10),
                        municipality VARCHAR(100),          -- Gemeinde
                        district VARCHAR(100),              -- Landkreis
                        state VARCHAR(50),                  -- Bundesland
                        country VARCHAR(50) DEFAULT 'Deutschland',
                        
                        -- Geo-Metadaten
                        coordinate_system VARCHAR(20) DEFAULT '{self.spatial_ref_sys}',
                        location_accuracy INTEGER,          -- Genauigkeit in Metern
                        location_source VARCHAR(100),       -- Quelle der Koordinaten
                        geo_quality_score DECIMAL(3,2) CHECK (geo_quality_score BETWEEN 0.00 AND 1.00),
                        geo_confidence INTEGER CHECK (geo_confidence BETWEEN 0 AND 100),
                        
                        -- UDS3 Standard Timestamps
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Geo Processing Timestamps
                        geo_processed_at TIMESTAMP WITH TIME ZONE,
                        geo_validated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
                
                # Administrative Areas (German Administrative Hierarchy)
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS administrative_areas (
                        ags VARCHAR(20) PRIMARY KEY,           -- Amtlicher Gemeindeschlüssel
                        name VARCHAR(200) NOT NULL,
                        name_variants TEXT[],                  -- Alternative Namen
                        area_type INTEGER NOT NULL CHECK (area_type BETWEEN 1 AND 6),
                        parent_ags VARCHAR(20),
                        
                        -- Statistics
                        population INTEGER,
                        area_km2 DECIMAL(12,4),
                        population_density DECIMAL(10,2),
                        
                        -- Geometry
                        geometry GEOMETRY(MULTIPOLYGON, {self.default_srid}),
                        centroid GEOMETRY(POINT, {self.default_srid}),
                        bbox GEOMETRY(POLYGON, {self.default_srid}),
                        
                        -- Metadata
                        valid_from DATE,
                        valid_to DATE,
                        source VARCHAR(100),
                        last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (parent_ags) REFERENCES administrative_areas(ags)
                    )
                """)
                
                # Institutions (Courts, Authorities)
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS geo_institutions (
                        id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(200) NOT NULL,
                        name_short VARCHAR(50),
                        institution_type VARCHAR(50) NOT NULL,    -- 'gericht', 'behoerde', 'ministerium'
                        institution_subtype VARCHAR(100),        -- 'amtsgericht', 'landgericht', etc.
                        
                        -- Contact Information
                        address TEXT,
                        postal_code VARCHAR(10),
                        city VARCHAR(100),
                        phone VARCHAR(50),
                        email VARCHAR(100),
                        website VARCHAR(200),
                        
                        -- Geo Information
                        location GEOMETRY(POINT, {self.default_srid}),
                        jurisdiction_area GEOMETRY(MULTIPOLYGON, {self.default_srid}),
                        service_radius_km INTEGER,
                        
                        -- Administrative Assignment
                        administrative_area_ags VARCHAR(20),
                        parent_institution_id VARCHAR(64),
                        
                        -- Additional Metadata
                        contact_info JSONB,
                        opening_hours JSONB,
                        services JSONB,
                        
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (administrative_area_ags) REFERENCES administrative_areas(ags),
                        FOREIGN KEY (parent_institution_id) REFERENCES geo_institutions(id)
                    )
                """)
                
                # Spatial Relationships (Document <-> Location Relationships)
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS spatial_relationships (
                        id SERIAL PRIMARY KEY,
                        document_id VARCHAR(64) NOT NULL,
                        related_document_id VARCHAR(64),
                        institution_id VARCHAR(64),
                        administrative_area_ags VARCHAR(20),
                        
                        relationship_type VARCHAR(50) NOT NULL, -- 'located_in', 'jurisdiction_of', 'nearby', etc.
                        distance_meters DECIMAL(12,2),
                        confidence_score DECIMAL(3,2),
                        
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (document_id) REFERENCES uds3_documents_geo(id) ON DELETE CASCADE,
                        FOREIGN KEY (related_document_id) REFERENCES uds3_documents_geo(id) ON DELETE CASCADE,
                        FOREIGN KEY (institution_id) REFERENCES geo_institutions(id),
                        FOREIGN KEY (administrative_area_ags) REFERENCES administrative_areas(ags)
                    )
                """)
                
                # === SPATIAL INDICES ===
                indices = [
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_point ON uds3_documents_geo USING GIST (location_point)",
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_polygon ON uds3_documents_geo USING GIST (location_polygon)",
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_linestring ON uds3_documents_geo USING GIST (location_linestring)",
                    
                    "CREATE INDEX IF NOT EXISTS idx_admin_areas_geometry ON administrative_areas USING GIST (geometry)",
                    "CREATE INDEX IF NOT EXISTS idx_admin_areas_centroid ON administrative_areas USING GIST (centroid)",
                    
                    "CREATE INDEX IF NOT EXISTS idx_institutions_location ON geo_institutions USING GIST (location)",
                    "CREATE INDEX IF NOT EXISTS idx_institutions_jurisdiction ON geo_institutions USING GIST (jurisdiction_area)",
                    
                    # Standard B-Tree Indices
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_administrative_level ON uds3_documents_geo (administrative_level)",
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_postal_code ON uds3_documents_geo (postal_code)",
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_state ON uds3_documents_geo (state)",
                    "CREATE INDEX IF NOT EXISTS idx_documents_geo_quality ON uds3_documents_geo (geo_quality_score)",
                    
                    "CREATE INDEX IF NOT EXISTS idx_admin_areas_type ON administrative_areas (area_type)",
                    "CREATE INDEX IF NOT EXISTS idx_admin_areas_parent ON administrative_areas (parent_ags)",
                    
                    "CREATE INDEX IF NOT EXISTS idx_institutions_type ON geo_institutions (institution_type)",
                    "CREATE INDEX IF NOT EXISTS idx_institutions_area ON geo_institutions (administrative_area_ags)",
                    
                    "CREATE INDEX IF NOT EXISTS idx_spatial_rel_doc ON spatial_relationships (document_id)",
                    "CREATE INDEX IF NOT EXISTS idx_spatial_rel_type ON spatial_relationships (relationship_type)"
                ]
                
                for index_sql in indices:
                    cursor.execute(index_sql)
                    
                # === FUNCTIONS AND TRIGGERS ===
                
                # Update Trigger für timestamps
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql'
                """)
                
                # Trigger für Documents
                cursor.execute("""
                    DROP TRIGGER IF EXISTS update_documents_geo_updated_at ON uds3_documents_geo;
                    CREATE TRIGGER update_documents_geo_updated_at
                        BEFORE UPDATE ON uds3_documents_geo
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
                """)
                
                # Trigger für Institutions  
                cursor.execute("""
                    DROP TRIGGER IF EXISTS update_institutions_updated_at ON geo_institutions;
                    CREATE TRIGGER update_institutions_updated_at
                        BEFORE UPDATE ON geo_institutions
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
                """)
                
                self.connection.commit()
                self.logger.info("PostGIS spatial schema initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize spatial schema: {e}")
            self.connection.rollback()
            return False
    
    # === SPATIAL OPERATIONS ===
    
    def insert_document_with_geo(self, doc_data: Dict) -> bool:
        """Fügt Dokument mit Geodaten ein"""
        try:
            with self.connection.cursor() as cursor:
                # Geo-WKT aus Koordinaten erstellen
                point_wkt = None
                if doc_data.get('latitude') and doc_data.get('longitude'):
                    point_wkt = f"POINT({doc_data['longitude']} {doc_data['latitude']})"
                
                cursor.execute("""
                    INSERT INTO uds3_documents_geo (
                        id, title, file_path, rechtsgebiet, gericht, aktenzeichen,
                        location_point, postal_code, municipality, district, state,
                        coordinate_system, location_accuracy, location_source, geo_quality_score
                    ) VALUES (
                        %(id)s, %(title)s, %(file_path)s, %(rechtsgebiet)s, %(gericht)s, %(aktenzeichen)s,
                        ST_GeomFromText(%(point_wkt)s, %(srid)s), %(postal_code)s, %(municipality)s, 
                        %(district)s, %(state)s, %(coordinate_system)s, %(location_accuracy)s,
                        %(location_source)s, %(geo_quality_score)s
                    ) ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        location_point = EXCLUDED.location_point,
                        geo_quality_score = EXCLUDED.geo_quality_score,
                        updated_at = CURRENT_TIMESTAMP
                """, {
                    **doc_data,
                    'point_wkt': point_wkt,
                    'srid': self.default_srid
                })
                
                self.connection.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to insert document with geo: {e}")
            self.connection.rollback()
            return False
    
    def spatial_search_documents(self, center_lat: float, center_lng: float, 
                                radius_km: float, filters: Dict = None, 
                                limit: int = 100) -> List[Dict]:
        """Erweiterte räumliche Dokumentensuche"""
        try:
            # Base Query mit Common Table Expression für Performance
            base_query = """
                WITH spatial_search AS (
                    SELECT 
                        d.id, d.title, d.rechtsgebiet, d.gericht, d.aktenzeichen,
                        ST_X(d.location_point) as longitude,
                        ST_Y(d.location_point) as latitude,
                        d.postal_code, d.municipality, d.district, d.state,
                        d.geo_quality_score, d.location_source,
                        ST_Distance_Sphere(
                            d.location_point, 
                            ST_Point(%(center_lng)s, %(center_lat)s)
                        ) as distance_meters,
                        d.created_at, d.updated_at
                    FROM uds3_documents_geo d
                    WHERE d.location_point IS NOT NULL
                      AND ST_DWithin(
                          d.location_point::geography,
                          ST_Point(%(center_lng)s, %(center_lat)s)::geography,
                          %(radius_m)s
                      )
            """
            
            params = {
                'center_lat': center_lat,
                'center_lng': center_lng,
                'radius_m': radius_km * 1000
            }
            
            # Filter hinzufügen
            filter_conditions = []
            if filters:
                if filters.get('rechtsgebiet'):
                    filter_conditions.append("d.rechtsgebiet ILIKE %(rechtsgebiet_filter)s")
                    params['rechtsgebiet_filter'] = f"%{filters['rechtsgebiet']}%"
                
                if filters.get('gericht'):
                    filter_conditions.append("d.gericht ILIKE %(gericht_filter)s")
                    params['gericht_filter'] = f"%{filters['gericht']}%"
                
                if filters.get('state'):
                    filter_conditions.append("d.state = %(state_filter)s")
                    params['state_filter'] = filters['state']
                    
                if filters.get('min_quality'):
                    filter_conditions.append("d.geo_quality_score >= %(min_quality)s")
                    params['min_quality'] = filters['min_quality']
            
            if filter_conditions:
                base_query += " AND " + " AND ".join(filter_conditions)
            
            # Final Query
            final_query = base_query + f"""
                )
                SELECT 
                    *,
                    ROUND((distance_meters / 1000.0)::numeric, 2) as distance_km,
                    CASE 
                        WHEN distance_meters < 1000 THEN 'sehr_nah'
                        WHEN distance_meters < 5000 THEN 'nah' 
                        WHEN distance_meters < 15000 THEN 'mittel'
                        ELSE 'weit'
                    END as distance_category
                FROM spatial_search
                ORDER BY distance_meters ASC
                LIMIT {limit}
            """
            
            with self.connection.cursor() as cursor:
                cursor.execute(final_query, params)
                results = cursor.fetchall()
                
                # Convert to list of dicts for JSON serialization
                return [dict(row) for row in results]
                
        except Exception as e:
            self.logger.error(f"Spatial search failed: {e}")
            return []
    
    def get_administrative_hierarchy(self, lat: float, lng: float) -> List[Dict]:
        """Ermittelt vollständige Verwaltungshierarchie für Koordinaten"""
        try:
            query = """
                WITH RECURSIVE admin_hierarchy AS (
                    -- Startpunkt: Finde die niedrigste Verwaltungsebene (Gemeinde)
                    SELECT 
                        a.ags, a.name, a.area_type, a.parent_ags, 
                        a.population, a.area_km2,
                        ST_AsGeoJSON(a.geometry) as geometry_geojson,
                        ST_AsGeoJSON(a.centroid) as centroid_geojson,
                        1 as hierarchy_level
                    FROM administrative_areas a
                    WHERE ST_Contains(a.geometry, ST_Point(%(lng)s, %(lat)s))
                      AND a.area_type = 5  -- Gemeinde
                    
                    UNION ALL
                    
                    -- Rekursiv: Gehe die Hierarchie nach oben
                    SELECT 
                        p.ags, p.name, p.area_type, p.parent_ags,
                        p.population, p.area_km2,
                        ST_AsGeoJSON(p.geometry) as geometry_geojson,
                        ST_AsGeoJSON(p.centroid) as centroid_geojson,
                        h.hierarchy_level + 1
                    FROM administrative_areas p
                    JOIN admin_hierarchy h ON p.ags = h.parent_ags
                    WHERE h.hierarchy_level < 6  -- Schutz vor Endlos-Rekursion
                )
                SELECT 
                    ags, name, area_type, parent_ags, population, area_km2,
                    geometry_geojson, centroid_geojson, hierarchy_level,
                    CASE area_type
                        WHEN 1 THEN 'Bund'
                        WHEN 2 THEN 'Land' 
                        WHEN 3 THEN 'Regierungsbezirk'
                        WHEN 4 THEN 'Landkreis'
                        WHEN 5 THEN 'Gemeinde'
                        WHEN 6 THEN 'Ortsteil'
                    END as area_type_name
                FROM admin_hierarchy
                ORDER BY area_type ASC  -- Von Bund zu Gemeinde
            """
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, {'lat': lat, 'lng': lng})
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get administrative hierarchy: {e}")
            return []
    
    def find_jurisdictions(self, lat: float, lng: float, 
                          institution_types: List[str] = None) -> List[Dict]:
        """Findet zuständige Institutionen für eine Position"""
        try:
            query = """
                SELECT 
                    i.id, i.name, i.institution_type, i.institution_subtype,
                    i.address, i.postal_code, i.city,
                    ST_X(i.location) as longitude, ST_Y(i.location) as latitude,
                    ST_Distance_Sphere(i.location, ST_Point(%(lng)s, %(lat)s)) as distance_meters,
                    i.contact_info, i.services,
                    CASE 
                        WHEN ST_Contains(i.jurisdiction_area, ST_Point(%(lng)s, %(lat)s)) THEN true
                        ELSE false
                    END as has_jurisdiction
                FROM geo_institutions i
                WHERE i.active = true
                  AND (
                      ST_Contains(i.jurisdiction_area, ST_Point(%(lng)s, %(lat)s))
                      OR ST_DWithin(
                          i.location::geography, 
                          ST_Point(%(lng)s, %(lat)s)::geography, 
                          50000  -- 50km radius
                      )
                  )
            """
            
            params = {'lat': lat, 'lng': lng}
            
            # Institution Type Filter
            if institution_types:
                placeholders = ', '.join(['%s'] * len(institution_types))
                query += f" AND i.institution_type = ANY(ARRAY[{placeholders}])"
                # Note: psycopg2 Parameter können hier als Liste übergeben werden
            
            query += """
                ORDER BY 
                    has_jurisdiction DESC,
                    distance_meters ASC
                LIMIT 20
            """
            
            with self.connection.cursor() as cursor:
                if institution_types:
                    cursor.execute(query, {**params, 'types': institution_types})
                else:
                    cursor.execute(query, params)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to find jurisdictions: {e}")
            return []
    
    def get_geo_statistics(self) -> Dict[str, Any]:
        """Erstellt umfassende Geodaten-Statistiken"""
        stats = {
            'documents': {},
            'spatial_coverage': {},
            'quality_metrics': {},
            'administrative_coverage': {},
            'institutions': {},
            'generated_at': datetime.now().isoformat()
        }
        
        try:
            with self.connection.cursor() as cursor:
                # === DOCUMENT STATISTICS ===
                
                # Gesamtzahl Dokumente mit Geodaten
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_documents,
                        COUNT(location_point) as documents_with_point,
                        COUNT(location_polygon) as documents_with_polygon,
                        COUNT(location_linestring) as documents_with_linestring
                    FROM uds3_documents_geo
                """)
                stats['documents'].update(dict(cursor.fetchone()))
                
                # Geo-Quellen
                cursor.execute("""
                    SELECT location_source, COUNT(*) as count
                    FROM uds3_documents_geo 
                    WHERE location_point IS NOT NULL
                    GROUP BY location_source
                    ORDER BY count DESC
                """)
                stats['documents']['sources'] = dict(cursor.fetchall())
                
                # Qualitätsverteilung
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN geo_quality_score >= 0.9 THEN 'excellent'
                            WHEN geo_quality_score >= 0.7 THEN 'good'
                            WHEN geo_quality_score >= 0.5 THEN 'fair'
                            WHEN geo_quality_score >= 0.3 THEN 'poor'
                            ELSE 'very_poor'
                        END as quality_level,
                        COUNT(*) as count
                    FROM uds3_documents_geo 
                    WHERE geo_quality_score IS NOT NULL
                    GROUP BY quality_level
                    ORDER BY 
                        CASE quality_level
                            WHEN 'excellent' THEN 1
                            WHEN 'good' THEN 2
                            WHEN 'fair' THEN 3
                            WHEN 'poor' THEN 4
                            ELSE 5
                        END
                """)
                stats['quality_metrics']['distribution'] = dict(cursor.fetchall())
                
                # === SPATIAL COVERAGE ===
                
                # Coverage by State
                cursor.execute("""
                    SELECT state, COUNT(*) as count
                    FROM uds3_documents_geo 
                    WHERE state IS NOT NULL
                    GROUP BY state
                    ORDER BY count DESC
                """)
                stats['spatial_coverage']['states'] = dict(cursor.fetchall())
                
                # Administrative Level Distribution
                cursor.execute("""
                    SELECT 
                        administrative_level,
                        CASE administrative_level
                            WHEN 1 THEN 'Bund'
                            WHEN 2 THEN 'Land'
                            WHEN 3 THEN 'Regierungsbezirk'
                            WHEN 4 THEN 'Landkreis'
                            WHEN 5 THEN 'Gemeinde'
                            WHEN 6 THEN 'Ortsteil'
                        END as level_name,
                        COUNT(*) as count
                    FROM uds3_documents_geo 
                    WHERE administrative_level IS NOT NULL
                    GROUP BY administrative_level
                    ORDER BY administrative_level
                """)
                admin_levels = cursor.fetchall()
                stats['administrative_coverage']['levels'] = {
                    row['level_name']: row['count'] for row in admin_levels
                }
                
                # === INSTITUTIONS ===
                cursor.execute("""
                    SELECT 
                        institution_type,
                        COUNT(*) as count,
                        COUNT(jurisdiction_area) as with_jurisdiction_area
                    FROM geo_institutions
                    WHERE active = true
                    GROUP BY institution_type
                    ORDER BY count DESC
                """)
                stats['institutions'] = {
                    row['institution_type']: {
                        'total': row['count'],
                        'with_jurisdiction': row['with_jurisdiction_area']
                    }
                    for row in cursor.fetchall()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to generate geo statistics: {e}")
        
        return stats
    
    # === UDS3 INTERFACE METHODS ===
    
    def store_document(self, doc_id: str, data: Dict) -> bool:
        """UDS3 Interface: Dokument speichern"""
        return self.insert_document_with_geo({
            'id': doc_id,
            **data
        })
    
    def search(self, query: Dict) -> List[Dict]:
        """UDS3 Interface: Suche nach Dokumenten"""
        if 'spatial' in query:
            spatial = query['spatial']
            return self.spatial_search_documents(
                spatial['lat'], spatial['lng'], spatial['radius'],
                query.get('filters'), query.get('limit', 50)
            )
        
        # Fallback auf Standard-Suche
        return []
    
    def health_check(self) -> Dict[str, Any]:
        """UDS3 Interface: Gesundheitsstatus"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT PostGIS_Version()")
                postgis_version = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM uds3_documents_geo")
                document_count = cursor.fetchone()[0]
                
                return {
                    'status': 'healthy',
                    'postgis_version': postgis_version,
                    'document_count': document_count,
                    'connection': 'active'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'connection': 'failed'
            }

# Export
__all__ = ['PostGISBackend']

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_postgis"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...6xzUKfI="  # Gekuerzt fuer Sicherheit
module_organization_key = "41687ae4842c898445e1c71c6e744edeb8a25e8a93549c4138201050d3c84a00"
module_file_key = "8abc01b420a470ed4e017657424cd4f171dcce3086f371573b12d25ad5043738"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
