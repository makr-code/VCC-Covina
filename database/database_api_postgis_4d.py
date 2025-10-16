#!/usr/bin/env python3
"""
UDS3 4D-PostGIS Backend (X,Y,Z,T Multi-CRS)
==========================================

Erweiterte PostGIS-Integration für 4D-Geodaten mit Multi-CRS-Support.
Unterstützt räumliche und zeitliche Dimensionen, volumetrische Geometrien
und Koordinatensystem-Transformationen.

Features:
- 4D-Geometrien (POINT ZM, LINESTRING ZM, POLYGON ZM)
- Multi-CRS-Support mit automatischen Transformationen
- Volumetrische 3D-Objekte (Sphere, Cylinder, Box, etc.)
- Zeitbasierte räumliche Abfragen
- Administrative Hierarchie-Integration
- Performance-optimierte räumliche Indizes

PostgreSQL/PostGIS Requirements:
- PostgreSQL 12+ mit PostGIS 3.0+
- Unterstützung für 3D/4D Geometrien
- Temporal-Extensions (optional)

Autor: Veritas UDS3 Team
Datum: 22. August 2025  
Version: 2.0 (4D Extension)
"""

import logging
import json
import struct
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from dataclasses import asdict

# PostGIS/PostgreSQL Verbindung
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    from psycopg2.extensions import AsIs
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# 4D Geo Extensions
try:
    from uds3_4d_geo_extension import (
        Enhanced4DGeoLocation, SpatialGeometry, SpatialCoordinate,
        GeometryType, CoordinateReferenceSystem, VolumetricParameters,
        CRSTransformer, validate_4d_geo_location
    )
    GEO_4D_AVAILABLE = True
except Exception as e:
    # Importing the 4D geo extension can fail due to missing dependency or
    # enum attribute assignment issues on some Python versions/environments.
    # Fall back to disabled mode but keep safe stubs so module import does
    # not crash the whole application.
    GEO_4D_AVAILABLE = False
    class Enhanced4DGeoLocation:  # stub
        pass
    class SpatialGeometry:
        pass
    class SpatialCoordinate:
        pass
    class GeometryType:
        pass
    class CoordinateReferenceSystem:
        pass
    class VolumetricParameters:
        pass
    class CRSTransformer:
        def __init__(self):
            pass
    def validate_4d_geo_location(x):
        return False

logger = logging.getLogger(__name__)

class PostGIS4DBackend:
    """Erweiterte PostGIS-Backend-Klasse für 4D-Geodaten"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger(f"{__name__}.PostGIS4DBackend")
        self.crs_transformer = CRSTransformer() if GEO_4D_AVAILABLE else None
        
        # Unterstützte SRID-Mappings
        self.srid_mapping = {
            'EPSG:4326': 4326,    # WGS84 2D
            'EPSG:4979': 4979,    # WGS84 3D  
            'EPSG:4258': 4258,    # ETRS89 2D
            'EPSG:4937': 4937,    # ETRS89 3D
            'EPSG:3857': 3857,    # Web Mercator
            'EPSG:25832': 25832,  # UTM 32N
            'EPSG:25833': 25833,  # UTM 33N
            'EPSG:31467': 31467,  # Gauß-Krüger Zone 3
            'EPSG:31468': 31468,  # Gauß-Krüger Zone 4
            'EPSG:31469': 31469,  # Gauß-Krüger Zone 5
        }
    
    def connect(self) -> bool:
        """Stellt PostGIS-Verbindung her"""
        
        if not PSYCOPG2_AVAILABLE:
            self.logger.error("psycopg2 not available")
            return False
        
        try:
            self.connection = psycopg2.connect(
                host=self.config.get('host', 'localhost'),
                database=self.config.get('database', 'uds3_geo'),
                user=self.config.get('user', 'postgres'),
                password=self.config.get('password', ''),
                port=self.config.get('port', 5432),
                cursor_factory=RealDictCursor
            )
            self.connection.autocommit = True
            
            # PostGIS-Verfügbarkeit prüfen
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT PostGIS_Version();")
                version = cursor.fetchone()[0]
                self.logger.info(f"Connected to PostGIS version: {version}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"PostGIS connection failed: {e}")
            return False
    
    def initialize_4d_spatial_schema(self) -> bool:
        """Initialisiert das erweiterte 4D-Schema"""
        
        if not self.connection:
            self.logger.error("No database connection")
            return False
        
        try:
            with self.connection.cursor() as cursor:
                
                # Haupttabelle für 4D-Dokumente
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS uds3_documents_4d_geo (
                        -- Basis-Identifikation
                        id VARCHAR(64) PRIMARY KEY,
                        title VARCHAR(500) NOT NULL,
                        content_preview TEXT,
                        
                        -- Standard UDS3-Metadaten
                        rechtsgebiet VARCHAR(200),
                        gericht VARCHAR(200),
                        aktenzeichen VARCHAR(200),
                        entscheidungsdatum DATE,
                        
                        -- 4D-Geometrien (Multi-CRS Support)
                        primary_geometry GEOMETRY,              -- Haupt-Geometrie (beliebiges CRS)
                        primary_geometry_srid INTEGER,          -- SRID der Haupt-Geometrie
                        primary_geometry_type VARCHAR(50),      -- Geometrie-Typ
                        
                        -- Legacy 2D-Koordinaten (immer WGS84 für Kompatibilität)
                        location_point GEOMETRY(POINT, 4326),   -- 2D-Punkt WGS84
                        
                        -- 3D/4D-Koordinaten  
                        location_3d GEOMETRY(POINTZ, 4326),     -- 3D-Punkt WGS84
                        location_4d GEOMETRY(POINTZM, 4326),    -- 4D-Punkt WGS84 (Z=Höhe, M=Zeit)
                        
                        -- Zusätzliche Geometrien
                        additional_geometries GEOMETRY[],        -- Array von Geometrien
                        additional_geometries_meta JSONB,       -- Metadaten für zusätzliche Geometrien
                        
                        -- Volumetrische Parameter
                        volume_type VARCHAR(50),                 -- SPHERE, CYLINDER, BOX, etc.
                        volume_parameters JSONB,                 -- Volumen-spezifische Parameter
                        calculated_volume NUMERIC(12,3),        -- Berechnetes Volumen (m³)
                        
                        -- Zeitliche Eigenschaften
                        temporal_validity_start TIMESTAMP,      -- Gültig von
                        temporal_validity_end TIMESTAMP,        -- Gültig bis  
                        temporal_resolution NUMERIC(10,2),      -- Zeitliche Auflösung (Sekunden)
                        observation_time TIMESTAMP,             -- Beobachtungszeit
                        
                        -- Koordinaten-Referenz-Systeme
                        native_crs VARCHAR(20),                  -- Ursprüngliches CRS
                        supported_crs VARCHAR[],                 -- Unterstützte CRS
                        transformation_parameters JSONB,        -- CRS-Transformations-Parameter
                        
                        -- Qualitäts- und Genauigkeitsmetriken
                        geometric_accuracy_xy NUMERIC(8,2),     -- Horizontale Genauigkeit (m)
                        geometric_accuracy_z NUMERIC(8,2),      -- Vertikale Genauigkeit (m)
                        geometric_accuracy_t NUMERIC(6,2),      -- Zeitliche Genauigkeit (s)
                        topological_quality NUMERIC(4,3),       -- Topologische Qualität (0-1)
                        completeness_score NUMERIC(4,3),        -- Vollständigkeitsscore (0-1)
                        overall_quality_score NUMERIC(4,3),     -- Gesamt-Qualitätsscore (0-1)
                        
                        -- Metadaten und Provenance
                        data_source VARCHAR(200),               -- Datenquelle
                        acquisition_method VARCHAR(100),        -- Erfassungsmethode
                        processing_level VARCHAR(50),           -- Bearbeitungsgrad
                        
                        -- Administrative Zuordnung
                        administrative_areas TEXT[],            -- Administrative Gebiete
                        political_boundaries TEXT[],           -- Politische Grenzen
                        postal_code VARCHAR(10),
                        municipality VARCHAR(100),
                        district VARCHAR(100), 
                        state VARCHAR(50),
                        country VARCHAR(50) DEFAULT 'Deutschland',
                        
                        -- Audit-Felder
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        geo_processed_at TIMESTAMP,
                        
                        -- Erweiterte Suchfelder
                        search_vector tsvector,                 -- Volltext-Suche
                        tags TEXT[]                            -- Freie Tags
                    );
                """)
                
                # Erweiterte CRS-Definitionen Tabelle
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS uds3_coordinate_systems (
                        crs_code VARCHAR(20) PRIMARY KEY,
                        crs_name VARCHAR(200) NOT NULL,
                        crs_authority VARCHAR(20) NOT NULL,
                        crs_id INTEGER,
                        dimensions INTEGER DEFAULT 2,
                        unit_name VARCHAR(50),
                        unit_factor NUMERIC(15,8),
                        area_of_use TEXT,
                        transformation_wkt TEXT,
                        custom_definition JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # 4D-Geometrie-Metadaten Tabelle
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS uds3_geometry_metadata (
                        geometry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        document_id VARCHAR(64) REFERENCES uds3_documents_4d_geo(id) ON DELETE CASCADE,
                        geometry_role VARCHAR(50) NOT NULL,     -- 'primary', 'additional', 'derived'
                        geometry_type VARCHAR(50) NOT NULL,
                        geometry_crs VARCHAR(20),
                        geometry_srid INTEGER,
                        geometry_wkt TEXT,
                        geometry_wkb BYTEA,
                        bounding_box_4d JSONB,                  -- {min_x, max_x, min_y, max_y, min_z, max_z, min_t, max_t}
                        
                        -- Volumetrische Parameter
                        is_volumetric BOOLEAN DEFAULT FALSE,
                        volume_type VARCHAR(50),
                        volume_parameters JSONB,
                        calculated_volume NUMERIC(12,3),
                        surface_area NUMERIC(12,3),
                        
                        -- Qualitätsmetriken
                        vertex_count INTEGER,
                        is_valid BOOLEAN,
                        validation_errors TEXT[],
                        simplification_tolerance NUMERIC(10,6),
                        
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Erweiterte räumliche Indizes
                self.logger.info("Creating spatial indices...")
                
                # Haupt-Geometrie-Index (Multi-SRID)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_primary_geometry 
                    ON uds3_documents_4d_geo USING GIST(primary_geometry);
                """)
                
                # 2D-Legacy-Index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_location_point 
                    ON uds3_documents_4d_geo USING GIST(location_point);
                """)
                
                # 3D-Index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_location_3d 
                    ON uds3_documents_4d_geo USING GIST(location_3d);
                """)
                
                # 4D-Index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_location_4d 
                    ON uds3_documents_4d_geo USING GIST(location_4d);
                """)
                
                # Zeitliche Indizes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_temporal_validity 
                    ON uds3_documents_4d_geo(temporal_validity_start, temporal_validity_end);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_observation_time 
                    ON uds3_documents_4d_geo(observation_time);
                """)
                
                # Administrative Indizes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_municipality 
                    ON uds3_documents_4d_geo(municipality);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_district 
                    ON uds3_documents_4d_geo(district);
                """)
                
                # CRS-Index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_native_crs 
                    ON uds3_documents_4d_geo(native_crs);
                """)
                
                # Qualitäts-Index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_quality_score 
                    ON uds3_documents_4d_geo(overall_quality_score);
                """)
                
                # Volltext-Index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uds3_4d_search_vector 
                    ON uds3_documents_4d_geo USING GIN(search_vector);
                """)
                
                # Standard CRS-Definitionen einfügen
                self._populate_standard_crs_definitions(cursor)
                
                self.logger.info("4D spatial schema initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Schema initialization failed: {e}")
            return False
    
    def _populate_standard_crs_definitions(self, cursor):
        """Fügt Standard-CRS-Definitionen hinzu"""
        
        standard_crs = [
            ('EPSG:4326', 'WGS 84', 'EPSG', 4326, 2, 'degree', 1.0, 'World'),
            ('EPSG:4979', 'WGS 84 3D', 'EPSG', 4979, 3, 'degree', 1.0, 'World'),
            ('EPSG:4258', 'ETRS89', 'EPSG', 4258, 2, 'degree', 1.0, 'Europe'),
            ('EPSG:4937', 'ETRS89 3D', 'EPSG', 4937, 3, 'degree', 1.0, 'Europe'),
            ('EPSG:3857', 'WGS 84 / Pseudo-Mercator', 'EPSG', 3857, 2, 'metre', 1.0, 'World'),
            ('EPSG:25832', 'ETRS89 / UTM zone 32N', 'EPSG', 25832, 2, 'metre', 1.0, 'Europe - 6°E to 12°E'),
            ('EPSG:25833', 'ETRS89 / UTM zone 33N', 'EPSG', 25833, 2, 'metre', 1.0, 'Europe - 12°E to 18°E'),
            ('EPSG:31467', 'DHDN / 3-degree Gauss-Kruger zone 3', 'EPSG', 31467, 2, 'metre', 1.0, 'Germany - West'),
        ]
        
        try:
            for crs_data in standard_crs:
                cursor.execute("""
                    INSERT INTO uds3_coordinate_systems 
                    (crs_code, crs_name, crs_authority, crs_id, dimensions, unit_name, unit_factor, area_of_use)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (crs_code) DO NOTHING
                """, crs_data)
            
            self.logger.info("Standard CRS definitions populated")
            
        except Exception as e:
            self.logger.error(f"Failed to populate CRS definitions: {e}")
    
    def insert_4d_document(self, doc_data: Dict) -> bool:
        """Speichert ein Dokument mit 4D-Geodaten"""
        
        if not self.connection:
            self.logger.error("No database connection")
            return False
        
        if not GEO_4D_AVAILABLE:
            self.logger.error("4D Geo extensions not available")
            return False
        
        try:
            with self.connection.cursor() as cursor:
                
                # Enhanced4DGeoLocation aus doc_data extrahieren
                geo_location = doc_data.get('geo_location')
                if isinstance(geo_location, Enhanced4DGeoLocation):
                    
                    # Primary Geometry verarbeiten
                    primary_geom = geo_location.primary_geometry
                    primary_wkt = None
                    primary_srid = 4326  # Default
                    
                    if isinstance(primary_geom.coordinates, SpatialCoordinate):
                        coord = primary_geom.coordinates
                        primary_srid = self.srid_mapping.get(coord.crs.code, 4326)
                        
                        if coord.z is not None and coord.t is not None:
                            # 4D-Punkt (POINTZM)
                            # M-Wert aus Zeitstempel berechnen (Unix-Timestamp)
                            m_value = coord.t.timestamp() if coord.t else 0
                            primary_wkt = f"POINTZM({coord.x} {coord.y} {coord.z} {m_value})"
                        elif coord.z is not None:
                            # 3D-Punkt (POINTZ) 
                            primary_wkt = f"POINTZ({coord.x} {coord.y} {coord.z})"
                        else:
                            # 2D-Punkt
                            primary_wkt = f"POINT({coord.x} {coord.y})"
                    
                    # Legacy 2D-Punkt für Kompatibilität (immer WGS84)
                    location_2d_wkt = f"POINT({geo_location.longitude} {geo_location.latitude})"
                    
                    # 3D-Punkt wenn verfügbar
                    location_3d_wkt = None
                    if geo_location.elevation is not None:
                        location_3d_wkt = f"POINTZ({geo_location.longitude} {geo_location.latitude} {geo_location.elevation})"
                    
                    # 4D-Punkt wenn Zeit verfügbar
                    location_4d_wkt = None
                    if geo_location.elevation is not None and geo_location.timestamp:
                        m_value = geo_location.timestamp.timestamp()
                        location_4d_wkt = f"POINTZM({geo_location.longitude} {geo_location.latitude} {geo_location.elevation} {m_value})"
                    
                    # Volumetrische Parameter
                    volume_type = None
                    volume_params_json = None
                    calculated_volume = None
                    
                    if primary_geom.volume_params:
                        volume_type = primary_geom.geometry_type.value
                        volume_params_json = Json(asdict(primary_geom.volume_params))
                        calculated_volume = primary_geom.calculate_volume()
                    
                    # Zusätzliche Geometrien
                    additional_geometries_wkb = []
                    additional_geometries_meta = []
                    
                    for geom in geo_location.additional_geometries:
                        geom_wkt = geom.to_wkt()
                        if geom_wkt:
                            # WKT zu WKB konvertieren (vereinfacht)
                            additional_geometries_wkb.append(geom_wkt)
                            additional_geometries_meta.append({
                                'type': geom.geometry_type.value,
                                'crs': geom.coordinates.crs.code if isinstance(geom.coordinates, SpatialCoordinate) else None,
                                'quality': geom.topological_quality,
                                'source': geom.source
                            })
                    
                    # 4D Bounding Box berechnen
                    bounds_4d = geo_location.calculate_4d_bounds()
                    
                    # Administrative Gebiete
                    admin_areas = geo_location.administrative_areas or []
                    
                    # CRS-Informationen
                    all_crs = geo_location.get_all_coordinate_systems()
                    native_crs = all_crs[0] if all_crs else 'EPSG:4326'
                    
                    # Zeitliche Eigenschaften
                    temporal_start = None
                    temporal_end = None
                    if primary_geom.temporal_validity:
                        temporal_start, temporal_end = primary_geom.temporal_validity
                    
                    # Document einfügen
                    cursor.execute("""
                        INSERT INTO uds3_documents_4d_geo (
                            id, title, content_preview,
                            rechtsgebiet, gericht, aktenzeichen, entscheidungsdatum,
                            
                            primary_geometry, primary_geometry_srid, primary_geometry_type,
                            location_point, location_3d, location_4d,
                            
                            volume_type, volume_parameters, calculated_volume,
                            
                            temporal_validity_start, temporal_validity_end,
                            temporal_resolution, observation_time,
                            
                            native_crs, supported_crs,
                            
                            geometric_accuracy_xy, geometric_accuracy_z, geometric_accuracy_t,
                            topological_quality, completeness_score, overall_quality_score,
                            
                            data_source, acquisition_method, processing_level,
                            
                            administrative_areas, postal_code, municipality, district, state,
                            
                            geo_processed_at
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            
                            ST_GeomFromText(%s, %s), %s, %s,
                            ST_GeomFromText(%s, 4326), 
                            CASE WHEN %s IS NOT NULL THEN ST_GeomFromText(%s, 4326) ELSE NULL END,
                            CASE WHEN %s IS NOT NULL THEN ST_GeomFromText(%s, 4326) ELSE NULL END,
                            
                            %s, %s, %s,
                            
                            %s, %s, %s, %s,
                            
                            %s, %s,
                            
                            %s, %s, %s,
                            %s, %s, %s,
                            
                            %s, %s, %s,
                            
                            %s, %s, %s, %s, %s,
                            
                            CURRENT_TIMESTAMP
                        )
                    """, (
                        doc_data['id'], doc_data.get('title', ''), doc_data.get('content_preview', ''),
                        doc_data.get('rechtsgebiet'), doc_data.get('gericht'), 
                        doc_data.get('aktenzeichen'), doc_data.get('entscheidungsdatum'),
                        
                        primary_wkt, primary_srid, primary_geom.geometry_type.value,
                        location_2d_wkt,
                        location_3d_wkt, location_3d_wkt,
                        location_4d_wkt, location_4d_wkt,
                        
                        volume_type, volume_params_json, calculated_volume,
                        
                        temporal_start, temporal_end, 
                        primary_geom.temporal_resolution, geo_location.timestamp,
                        
                        native_crs, all_crs,
                        
                        geo_location.accuracy_meters, 
                        geo_location.primary_geometry.coordinates.accuracy_z if isinstance(geo_location.primary_geometry.coordinates, SpatialCoordinate) else None,
                        geo_location.primary_geometry.coordinates.accuracy_t if isinstance(geo_location.primary_geometry.coordinates, SpatialCoordinate) else None,
                        primary_geom.topological_quality, primary_geom.completeness_score, geo_location.quality_score,
                        
                        geo_location.source, primary_geom.acquisition_method, primary_geom.processing_level,
                        
                        admin_areas, doc_data.get('postal_code'), doc_data.get('municipality'),
                        doc_data.get('district'), doc_data.get('state')
                    ))
                    
                    # Zusätzliche Geometrien in Metadaten-Tabelle einfügen
                    if additional_geometries_wkb:
                        for i, (geom_wkt, meta) in enumerate(zip(additional_geometries_wkb, additional_geometries_meta)):
                            cursor.execute("""
                                INSERT INTO uds3_geometry_metadata (
                                    document_id, geometry_role, geometry_type,
                                    geometry_wkt, bounding_box_4d
                                ) VALUES (%s, %s, %s, %s, %s)
                            """, (
                                doc_data['id'], 'additional', meta['type'],
                                geom_wkt, Json(bounds_4d) if bounds_4d else None
                            ))
                    
                    self.logger.debug(f"4D document inserted successfully: {doc_data['id']}")
                    return True
                
                else:
                    self.logger.error(f"Invalid geo_location type: {type(geo_location)}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to insert 4D document: {e}")
            return False
    
    def spatial_search_4d(self, center_coord: SpatialCoordinate, radius_m: float, 
                         time_range: Optional[Tuple[datetime, datetime]] = None,
                         target_crs: Optional[CoordinateReferenceSystem] = None,
                         filters: Dict = None, limit: int = 50) -> List[Dict]:
        """Erweiterte 4D-räumliche Suche mit Zeit- und CRS-Unterstützung"""
        
        if not self.connection or not GEO_4D_AVAILABLE:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                
                # Target CRS bestimmen
                if target_crs is None:
                    target_crs = center_coord.crs
                
                # Suchkoordinaten in PostGIS-kompatibles CRS konvertieren
                search_srid = self.srid_mapping.get(target_crs.code, 4326)
                
                # CRS-Transformation wenn nötig
                if center_coord.crs != target_crs and self.crs_transformer:
                    transformed_coord = self.crs_transformer.transform_coordinate(center_coord, target_crs)
                    if transformed_coord:
                        search_coord = transformed_coord
                    else:
                        search_coord = center_coord
                        search_srid = self.srid_mapping.get(center_coord.crs.code, 4326)
                else:
                    search_coord = center_coord
                
                # Basis-SQL für räumliche Suche
                base_query = """
                    SELECT 
                        id, title, rechtsgebiet, gericht, aktenzeichen,
                        ST_X(location_point) as longitude,
                        ST_Y(location_point) as latitude,
                        ST_Z(location_3d) as elevation,
                        
                        -- 4D-Koordinaten
                        ST_X(location_4d) as x_4d,
                        ST_Y(location_4d) as y_4d, 
                        ST_Z(location_4d) as z_4d,
                        ST_M(location_4d) as m_4d,
                        
                        -- Distanz-Berechnung (in Metern)
                        ST_Distance(
                            ST_Transform(location_point, %s),
                            ST_Transform(ST_GeomFromText(%s, %s), %s)
                        ) as distance_m,
                        
                        -- 3D-Distanz wenn verfügbar
                        CASE WHEN location_3d IS NOT NULL THEN
                            ST_3DDistance(
                                ST_Transform(location_3d, %s),
                                ST_Transform(ST_GeomFromText(%s, %s), %s)
                            )
                        ELSE NULL END as distance_3d_m,
                        
                        -- CRS-Informationen
                        native_crs, supported_crs,
                        
                        -- Qualitäts-Metriken
                        geometric_accuracy_xy, geometric_accuracy_z,
                        overall_quality_score,
                        
                        -- Zeitliche Informationen
                        observation_time, temporal_validity_start, temporal_validity_end,
                        
                        -- Administrative Zuordnung
                        municipality, district, state, administrative_areas,
                        
                        -- Volumen-Informationen
                        volume_type, calculated_volume,
                        
                        created_at, updated_at
                        
                    FROM uds3_documents_4d_geo
                    WHERE ST_DWithin(
                        ST_Transform(location_point, %s),
                        ST_Transform(ST_GeomFromText(%s, %s), %s),
                        %s
                    )
                """
                
                # Parameter für Basis-Query
                if search_coord.z is not None:
                    search_wkt = f"POINTZ({search_coord.x} {search_coord.y} {search_coord.z})"
                else:
                    search_wkt = f"POINT({search_coord.x} {search_coord.y})"
                
                # UTM für genaue Distanz-Messung verwenden
                utm_srid = 25832 if 6 <= search_coord.x <= 12 else 25833  # UTM 32N oder 33N für Deutschland
                
                query_params = [
                    # Erste ST_Distance Parameter
                    utm_srid, search_wkt, search_srid, utm_srid,
                    # 3D-Distance Parameter  
                    utm_srid, search_wkt, search_srid, utm_srid,
                    # ST_DWithin Parameter
                    utm_srid, search_wkt, search_srid, utm_srid, radius_m
                ]
                
                # Zeitliche Filter hinzufügen
                if time_range:
                    start_time, end_time = time_range
                    base_query += """
                        AND (
                            (observation_time BETWEEN %s AND %s) OR
                            (temporal_validity_start <= %s AND temporal_validity_end >= %s) OR
                            (temporal_validity_start IS NULL AND temporal_validity_end IS NULL)
                        )
                    """
                    query_params.extend([start_time, end_time, end_time, start_time])
                
                # Zusätzliche Filter
                if filters:
                    if filters.get('rechtsgebiet'):
                        base_query += " AND rechtsgebiet = %s"
                        query_params.append(filters['rechtsgebiet'])
                    
                    if filters.get('gericht'):
                        base_query += " AND gericht = %s"
                        query_params.append(filters['gericht'])
                    
                    if filters.get('municipality'):
                        base_query += " AND municipality = %s"
                        query_params.append(filters['municipality'])
                    
                    if filters.get('state'):
                        base_query += " AND state = %s"
                        query_params.append(filters['state'])
                    
                    if filters.get('min_quality'):
                        base_query += " AND overall_quality_score >= %s"
                        query_params.append(filters['min_quality'])
                    
                    if filters.get('volume_type'):
                        base_query += " AND volume_type = %s"
                        query_params.append(filters['volume_type'])
                    
                    if filters.get('has_3d'):
                        base_query += " AND location_3d IS NOT NULL"
                    
                    if filters.get('has_4d'):
                        base_query += " AND location_4d IS NOT NULL"
                
                # Sortierung und Limit
                base_query += " ORDER BY distance_m ASC LIMIT %s"
                query_params.append(limit)
                
                # Query ausführen
                cursor.execute(base_query, query_params)
                results = cursor.fetchall()
                
                # Ergebnisse aufbereiten
                formatted_results = []
                for row in results:
                    result = dict(row)
                    
                    # Distanz in Kilometern
                    result['distance_km'] = result['distance_m'] / 1000.0 if result['distance_m'] else None
                    result['distance_3d_km'] = result['distance_3d_m'] / 1000.0 if result['distance_3d_m'] else None
                    
                    # 4D-Zeitstempel dekodieren
                    if result['m_4d']:
                        try:
                            result['timestamp_4d'] = datetime.fromtimestamp(result['m_4d'])
                        except:
                            result['timestamp_4d'] = None
                    
                    # CRS-Informationen aufbereiten
                    if isinstance(result['supported_crs'], list):
                        result['available_crs'] = result['supported_crs']
                    
                    formatted_results.append(result)
                
                self.logger.debug(f"4D spatial search returned {len(formatted_results)} results")
                return formatted_results
                
        except Exception as e:
            self.logger.error(f"4D spatial search failed: {e}")
            return []
    
    def get_4d_statistics(self) -> Dict[str, Any]:
        """Erweiterte Statistiken für 4D-Geodaten"""
        
        if not self.connection:
            return {'error': 'No database connection'}
        
        stats = {
            'generated_at': datetime.now().isoformat(),
            'database_info': {},
            'document_counts': {},
            'geometry_statistics': {},
            'crs_usage': {},
            'quality_metrics': {},
            'temporal_coverage': {},
            'volumetric_data': {}
        }
        
        try:
            with self.connection.cursor() as cursor:
                
                # Basis-Dokumentenzahlen
                cursor.execute("SELECT COUNT(*) FROM uds3_documents_4d_geo")
                stats['document_counts']['total_documents'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM uds3_documents_4d_geo WHERE location_point IS NOT NULL")
                stats['document_counts']['documents_with_2d'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM uds3_documents_4d_geo WHERE location_3d IS NOT NULL")
                stats['document_counts']['documents_with_3d'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM uds3_documents_4d_geo WHERE location_4d IS NOT NULL")
                stats['document_counts']['documents_with_4d'] = cursor.fetchone()[0]
                
                # Geometrie-Typen
                cursor.execute("""
                    SELECT primary_geometry_type, COUNT(*) 
                    FROM uds3_documents_4d_geo 
                    WHERE primary_geometry_type IS NOT NULL
                    GROUP BY primary_geometry_type 
                    ORDER BY COUNT(*) DESC
                """)
                geometry_types = dict(cursor.fetchall())
                stats['geometry_statistics']['primary_geometry_types'] = geometry_types
                
                # CRS-Nutzung
                cursor.execute("""
                    SELECT native_crs, COUNT(*) 
                    FROM uds3_documents_4d_geo 
                    WHERE native_crs IS NOT NULL
                    GROUP BY native_crs 
                    ORDER BY COUNT(*) DESC
                """)
                crs_usage = dict(cursor.fetchall())
                stats['crs_usage']['native_crs_distribution'] = crs_usage
                
                # Qualitäts-Verteilung
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN overall_quality_score >= 0.8 THEN 'high'
                            WHEN overall_quality_score >= 0.6 THEN 'medium' 
                            WHEN overall_quality_score >= 0.4 THEN 'low'
                            ELSE 'very_low'
                        END as quality_category,
                        COUNT(*)
                    FROM uds3_documents_4d_geo 
                    WHERE overall_quality_score IS NOT NULL
                    GROUP BY quality_category
                """)
                quality_dist = dict(cursor.fetchall())
                stats['quality_metrics']['quality_distribution'] = quality_dist
                
                # Genauigkeits-Statistiken
                cursor.execute("""
                    SELECT 
                        AVG(geometric_accuracy_xy) as avg_xy_accuracy,
                        AVG(geometric_accuracy_z) as avg_z_accuracy,
                        AVG(geometric_accuracy_t) as avg_t_accuracy,
                        AVG(overall_quality_score) as avg_quality_score
                    FROM uds3_documents_4d_geo
                """)
                accuracy_stats = dict(cursor.fetchone())
                stats['quality_metrics']['accuracy_statistics'] = accuracy_stats
                
                # Zeitliche Abdeckung
                cursor.execute("""
                    SELECT 
                        MIN(observation_time) as earliest_observation,
                        MAX(observation_time) as latest_observation,
                        COUNT(DISTINCT DATE(observation_time)) as observation_days
                    FROM uds3_documents_4d_geo 
                    WHERE observation_time IS NOT NULL
                """)
                temporal_coverage = dict(cursor.fetchone())
                if temporal_coverage['earliest_observation']:
                    temporal_coverage['earliest_observation'] = temporal_coverage['earliest_observation'].isoformat()
                if temporal_coverage['latest_observation']:
                    temporal_coverage['latest_observation'] = temporal_coverage['latest_observation'].isoformat()
                stats['temporal_coverage'] = temporal_coverage
                
                # Volumetrische Daten
                cursor.execute("""
                    SELECT volume_type, COUNT(*), AVG(calculated_volume), SUM(calculated_volume)
                    FROM uds3_documents_4d_geo 
                    WHERE volume_type IS NOT NULL AND calculated_volume IS NOT NULL
                    GROUP BY volume_type
                """)
                volume_stats = {}
                for row in cursor.fetchall():
                    volume_type, count, avg_vol, total_vol = row
                    volume_stats[volume_type] = {
                        'count': count,
                        'average_volume_m3': float(avg_vol) if avg_vol else 0,
                        'total_volume_m3': float(total_vol) if total_vol else 0
                    }
                stats['volumetric_data'] = volume_stats
                
                # Administrative Verteilung
                cursor.execute("""
                    SELECT state, COUNT(*) 
                    FROM uds3_documents_4d_geo 
                    WHERE state IS NOT NULL
                    GROUP BY state 
                    ORDER BY COUNT(*) DESC
                """)
                state_dist = dict(cursor.fetchall())
                stats['administrative_distribution'] = {'states': state_dist}
                
        except Exception as e:
            self.logger.error(f"Failed to generate 4D statistics: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Erweiterte Gesundheitsprüfung für 4D-System"""
        
        health = {
            'status': 'unknown',
            'connection': False,
            'postgis_version': None,
            '4d_support': False,
            'spatial_indices': False,
            'crs_definitions': 0,
            'sample_queries': {},
            'performance_metrics': {}
        }
        
        if not self.connection:
            health['status'] = 'no_connection'
            return health
        
        try:
            with self.connection.cursor() as cursor:
                
                # Basis-Verbindung
                cursor.execute("SELECT 1")
                health['connection'] = True
                
                # PostGIS-Version
                cursor.execute("SELECT PostGIS_Version()")
                health['postgis_version'] = cursor.fetchone()[0]
                
                # 4D-Unterstützung prüfen
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'uds3_documents_4d_geo'
                """)
                health['4d_support'] = cursor.fetchone()[0] > 0
                
                if health['4d_support']:
                    # Spatial-Indizes prüfen
                    cursor.execute("""
                        SELECT COUNT(*) FROM pg_indexes 
                        WHERE tablename = 'uds3_documents_4d_geo' 
                        AND indexname LIKE 'idx_uds3_4d_%'
                    """)
                    health['spatial_indices'] = cursor.fetchone()[0] > 0
                    
                    # CRS-Definitionen
                    cursor.execute("SELECT COUNT(*) FROM uds3_coordinate_systems")
                    health['crs_definitions'] = cursor.fetchone()[0]
                    
                    # Sample Queries für Performance
                    import time
                    
                    # 2D-Query Performance
                    start_time = time.time()
                    cursor.execute("""
                        SELECT COUNT(*) FROM uds3_documents_4d_geo 
                        WHERE ST_DWithin(
                            location_point, 
                            ST_GeomFromText('POINT(13.4050 52.5200)', 4326),
                            10000
                        )
                    """)
                    health['sample_queries']['2d_spatial_query_ms'] = (time.time() - start_time) * 1000
                    
                    # 3D-Query Performance
                    start_time = time.time()
                    cursor.execute("""
                        SELECT COUNT(*) FROM uds3_documents_4d_geo 
                        WHERE location_3d IS NOT NULL
                    """)
                    health['sample_queries']['3d_count_query_ms'] = (time.time() - start_time) * 1000
                    
                    # 4D-Query Performance
                    start_time = time.time()
                    cursor.execute("""
                        SELECT COUNT(*) FROM uds3_documents_4d_geo 
                        WHERE location_4d IS NOT NULL
                    """)
                    health['sample_queries']['4d_count_query_ms'] = (time.time() - start_time) * 1000
                
                health['status'] = 'healthy'
                
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        return health

# Export
__all__ = ['PostGIS4DBackend']

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "database_api_postgis_4d"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...hh7ASaQ="  # Gekuerzt fuer Sicherheit
module_organization_key = "cda413e93af2a09c969d11bf369a2e93b5bab201e7ec1b160be2ffef451ce531"
module_file_key = "77c51414ecd2e8e3aaccb88de3ce780b69f610afb53003ff410ab4a9bb942e44"
module_version = "1.0"
module_protection_level = 3
# === END PROTECTION KEYS ===
