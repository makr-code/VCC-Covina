from typing import Any
#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_4d_geo_extension"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
)
module_file_key = "76215238e60c121754985fc6e167c445252bf58f14a297f7227d597d74504559"
module_version = "1.0"
module_protection_level = 1
# === END PROTECTION KEYS ===
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""


"""
UDS3 4D-Geodaten Extension (X,Y,Z,T)
===================================

Erweiterte Geodaten-Architektur für das UDS3-System mit vollständiger 
4D-Unterstützung (3D Raum + Zeit) und Multi-CRS-Kompatibilität.

Features:
- 4D-Koordinaten (X,Y,Z,T) mit Transformations-Parametern (U,V,W)
- Multi-Coordinate-Reference-System Support
- 3D-Geometrien (Punkte, Linien, Polygone, Volumina)
- Zeitbasierte Geo-Operationen
- CRS-Transformationen und Umrechnungen
- Qualitäts- und Genauigkeits-Metadaten

Geometrie-Typen:
- 2D: Point, LineString, Polygon
- 3D: Point Z, LineString Z, Polygon Z  
- Volumen: Sphere, Cylinder, Box, Polyhedron
- 4D: Point ZM, LineString ZM, Polygon ZM (Z=Höhe, M=Zeit)

Coordinate Reference Systems:
- Geografisch: WGS84 (2D/3D), ETRS89
- Projektiv: UTM, Gauß-Krüger, Web Mercator
- Lokal: Kartesisch, Gebäude-Koordinaten

Autor: Veritas UDS3 Team
Datum: 22. August 2025  
Version: 2.0 (4D Extension)
"""

import logging
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Union, Tuple, Dict, Any
from datetime import datetime

# Optional dependencies mit Fallbacks
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from shapely.geometry import Point, LineString, Polygon
    from shapely.geometry import MultiPoint, MultiLineString, MultiPolygon
    from shapely import wkt, wkb

    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

try:
    import pyproj
    from pyproj import Proj, transform, Transformer

    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False

logger = logging.getLogger(__name__)


class GeometryType(Enum):
    """Erweiterte 4D-Geometrie-Typen"""

    # 2D Basis-Geometrien
    POINT = "POINT"
    LINESTRING = "LINESTRING"
    POLYGON = "POLYGON"
    MULTIPOINT = "MULTIPOINT"
    MULTILINESTRING = "MULTILINESTRING"
    MULTIPOLYGON = "MULTIPOLYGON"

    # 3D-Geometrien (Z-Koordinate)
    POINT_Z = "POINT Z"
    LINESTRING_Z = "LINESTRING Z"
    POLYGON_Z = "POLYGON Z"
    MULTIPOINT_Z = "MULTIPOINT Z"
    MULTILINESTRING_Z = "MULTILINESTRING Z"
    MULTIPOLYGON_Z = "MULTIPOLYGON Z"

    # Volumetrische 3D-Geometrien
    SPHERE = "SPHERE"  # Kugel (x,y,z,radius)
    CYLINDER = "CYLINDER"  # Zylinder (x,y,z,radius,height)
    BOX = "BOX"  # Quader (x,y,z,width,depth,height)
    POLYHEDRON = "POLYHEDRON"  # Polyeder (Liste von Polygonen)
    CONE = "CONE"  # Kegel (x,y,z,radius,height)
    ELLIPSOID = "ELLIPSOID"  # Ellipsoid (x,y,z,a,b,c)

    # 4D-Geometrien mit Zeit (M = Measure/Time)
    POINT_ZM = "POINT ZM"  # 4D-Punkt (x,y,z,time)
    LINESTRING_ZM = "LINESTRING ZM"  # 4D-Linie
    POLYGON_ZM = "POLYGON ZM"  # 4D-Polygon

    # Erweiterte räumliche Strukturen
    BUILDING = "BUILDING"  # Gebäude-Komplex
    TERRAIN = "TERRAIN"  # Geländemodell (TIN/Grid)
    VOXEL_GRID = "VOXEL_GRID"  # Voxel-basierte Volumen


class CoordinateReferenceSystem(Enum):
    """Umfassende CRS-Definitionen für Deutschland/Europa"""

    # Geografische Koordinatensysteme
    WGS84_2D = ("EPSG:4326", "WGS 84", 2)  # Geografisch 2D
    WGS84_3D = ("EPSG:4979", "WGS 84 3D", 3)  # Geografisch 3D
    ETRS89_2D = ("EPSG:4258", "ETRS89", 2)  # Europa 2D
    ETRS89_3D = ("EPSG:4937", "ETRS89 3D", 3)  # Europa 3D

    # Projektive Koordinatensysteme
    WEB_MERCATOR = ("EPSG:3857", "WGS 84 / Pseudo-Mercator", 2)
    UTM32N_ETRS89 = ("EPSG:25832", "ETRS89 / UTM zone 32N", 2)
    UTM33N_ETRS89 = ("EPSG:25833", "ETRS89 / UTM zone 33N", 2)

    # Deutsche Koordinatensysteme
    GAUSS_KRUGER_3 = ("EPSG:31467", "DHDN / 3-degree Gauss-Kruger zone 3", 2)
    GAUSS_KRUGER_4 = ("EPSG:31468", "DHDN / 3-degree Gauss-Kruger zone 4", 2)
    GAUSS_KRUGER_5 = ("EPSG:31469", "DHDN / 3-degree Gauss-Kruger zone 5", 2)

    # ETRS89-basierte deutsche Systeme
    ETRS89_UTM32 = ("EPSG:25832", "ETRS89 / UTM zone 32N", 2)
    ETRS89_UTM33 = ("EPSG:25833", "ETRS89 / UTM zone 33N", 2)
    ETRS89_LCC = ("EPSG:3034", "ETRS89 / Lambert Conformal Conic", 2)

    # Lokale/Spezielle Systeme
    LOCAL_CARTESIAN = ("LOCAL:CART", "Local Cartesian", 3)
    BUILDING_LOCAL = ("LOCAL:BLD", "Building Local Coordinates", 3)
    SURVEY_LOCAL = ("LOCAL:SURVEY", "Survey Local Grid", 2)

    def __init__(self, code: str, name: str, dimensions: int):
        self.code = code
        self.name = name
        self.dimensions = dimensions
        self.authority = code.split(":")[0] if ":" in code else "LOCAL"
        self.id = code.split(":")[1] if ":" in code else code


@dataclass
class TransformationParameters:
    """Transformations-Parameter für CRS-Konvertierungen"""

    # Helmert-Transformation (7-Parameter)
    translation_x: float = 0.0  # Translation X (m)
    translation_y: float = 0.0  # Translation Y (m)
    translation_z: float = 0.0  # Translation Z (m)
    rotation_x: float = 0.0  # Rotation X (arc seconds)
    rotation_y: float = 0.0  # Rotation Y (arc seconds)
    rotation_z: float = 0.0  # Rotation Z (arc seconds)
    scale_factor: float = 0.0  # Skalierungsfaktor (ppm)

    # Projektions-Parameter
    central_meridian: Optional[float] = None
    latitude_of_origin: Optional[float] = None
    standard_parallel_1: Optional[float] = None
    standard_parallel_2: Optional[float] = None
    false_easting: Optional[float] = None
    false_northing: Optional[float] = None

    # Custom Transformations-Matrix (4x4)
    transformation_matrix: Optional[List[List[float]]] = None


@dataclass
class SpatialCoordinate:
    """Erweiterte 4D-Koordinate mit vollständiger CRS-Definition"""

    # Basis-Koordinaten
    x: float  # X/Longitude/Ost
    y: float  # Y/Latitude/Nord
    z: Optional[float] = None  # Z/Elevation/Höhe
    t: Optional[datetime] = None  # Zeitstempel

    # Transformations-Koordinaten (für komplexe Umrechnungen)
    u: Optional[float] = None  # Transformations-Parameter U
    v: Optional[float] = None  # Transformations-Parameter V
    w: Optional[float] = None  # Transformations-Parameter W

    # Coordinate Reference System
    crs: CoordinateReferenceSystem = CoordinateReferenceSystem.WGS84_2D
    crs_custom: Optional[str] = None  # Custom CRS Definition

    # Genauigkeits- und Qualitätsmetriken
    accuracy_xy: Optional[float] = None  # Horizontale Genauigkeit (m)
    accuracy_z: Optional[float] = None  # Vertikale Genauigkeit (m)
    accuracy_t: Optional[float] = None  # Zeitliche Genauigkeit (s)
    quality_score: Optional[float] = None  # Gesamt-Qualitätsscore (0-1)

    # Metadaten
    source: Optional[str] = None  # Datenquelle
    measurement_method: Optional[str] = None  # Messverfahren (GPS, Total Station, etc.)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertierung zu Dictionary für Serialisierung"""
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "t": self.t.isoformat() if self.t else None,
            "u": self.u,
            "v": self.v,
            "w": self.w,
            "crs": self.crs.code,
            "crs_name": self.crs.name,
            "accuracy_xy": self.accuracy_xy,
            "accuracy_z": self.accuracy_z,
            "accuracy_t": self.accuracy_t,
            "quality_score": self.quality_score,
            "source": self.source,
            "measurement_method": self.measurement_method,
            "created_at": self.created_at.isoformat(),
        }

    def distance_3d(self, other: "SpatialCoordinate") -> Optional[float]:
        """3D-Entfernung zwischen zwei Koordinaten (wenn Z vorhanden)"""
        if not (self.z is not None and other.z is not None):
            return None

        # Einfache euklidische Distanz (für gleiche CRS)
        if self.crs == other.crs:
            dx = self.x - other.x
            dy = self.y - other.y
            dz = self.z - other.z
            return math.sqrt(dx * dx + dy * dy + dz * dz)

        # TODO: CRS-Transformation für unterschiedliche Systeme
        logger.warning(
            f"Distance calculation between different CRS not implemented: {self.crs} vs {other.crs}"
        )
        return None


@dataclass
class VolumetricParameters:
    """Parameter für volumetrische 3D-Geometrien"""

    # Basis-Parameter
    radius: Optional[float] = None  # Radius (Sphere, Cylinder)
    height: Optional[float] = None  # Höhe (Cylinder, Cone, Box)
    width: Optional[float] = None  # Breite (Box)
    depth: Optional[float] = None  # Tiefe (Box)

    # Ellipsoid-Parameter
    semi_major_axis: Optional[float] = None  # Große Halbachse
    semi_minor_axis: Optional[float] = None  # Kleine Halbachse
    semi_polar_axis: Optional[float] = None  # Polare Halbachse

    # Orientierung im 3D-Raum
    orientation_x: float = 0.0  # Rotation um X-Achse (deg)
    orientation_y: float = 0.0  # Rotation um Y-Achse (deg)
    orientation_z: float = 0.0  # Rotation um Z-Achse (deg)

    # Voxel-Parameter
    voxel_size: Optional[Tuple[float, float, float]] = None
    voxel_resolution: Optional[Tuple[int, int, int]] = None


@dataclass
class SpatialGeometry:
    """Erweiterte 4D-Geometrie-Definition"""

    geometry_type: GeometryType
    coordinates: Union[
        SpatialCoordinate,  # Einzelner Punkt
        List[SpatialCoordinate],  # Linie, Multi-Point
        List[List[SpatialCoordinate]],  # Polygon, Multi-Line
        List[List[List[SpatialCoordinate]]],  # Multi-Polygon, 3D-Strukturen
    ]

    # Volumetrische Parameter
    volume_params: Optional[VolumetricParameters] = None

    # Transformations-Parameter
    transformation: Optional[TransformationParameters] = None

    # Zeitliche Eigenschaften
    temporal_validity: Optional[Tuple[datetime, datetime]] = (
        None  # Gültigkeits-Zeitraum
    )
    temporal_resolution: Optional[float] = None  # Zeitliche Auflösung (s)

    # Qualitäts- und Genauigkeitsmetriken
    geometric_accuracy: Optional[float] = None  # Geometrische Genauigkeit (m)
    topological_quality: Optional[float] = None  # Topologische Qualität (0-1)
    completeness_score: Optional[float] = None  # Vollständigkeitsscore (0-1)

    # Metadaten
    source: Optional[str] = None
    acquisition_method: Optional[str] = None  # Erfassungsmethode
    processing_level: Optional[str] = None  # Bearbeitungsgrad
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def get_bounding_box_4d(self) -> Optional[Dict[str, Union[float, datetime]]]:
        """Berechnet die 4D-Bounding-Box (X,Y,Z,T)"""

        if isinstance(self.coordinates, SpatialCoordinate):
            coords = [self.coordinates]
        elif isinstance(self.coordinates[0], SpatialCoordinate):
            coords = self.coordinates
        else:
            # Flatten verschachtelte Listen
            coords: list[Any] = []

            def flatten_coords(coord_list):
                for item in coord_list:
                    if isinstance(item, SpatialCoordinate):
                        coords.append(item)
                    elif isinstance(item, list):
                        flatten_coords(item)

            flatten_coords(self.coordinates)

        if not coords:
            return None

        # X,Y,Z Grenzen
        x_coords = [c.x for c in coords]
        y_coords = [c.y for c in coords]
        z_coords = [c.z for c in coords if c.z is not None]
        t_coords = [c.t for c in coords if c.t is not None]

        bbox = {
            "min_x": min(x_coords),
            "max_x": max(x_coords),
            "min_y": min(y_coords),
            "max_y": max(y_coords),
        }

        if z_coords:
            bbox.update({"min_z": min(z_coords), "max_z": max(z_coords)})

        if t_coords:
            bbox.update({"min_t": min(t_coords), "max_t": max(t_coords)})

        return bbox

    def calculate_volume(self) -> Optional[float]:
        """Berechnet das Volumen für 3D-Geometrien"""

        if not self.volume_params:
            return None

        volume = None
        params = self.volume_params

        if self.geometry_type == GeometryType.SPHERE and params.radius:
            # Kugelvolumen: 4/3 * π * r³
            volume = (4 / 3) * math.pi * (params.radius**3)

        elif (
            self.geometry_type == GeometryType.CYLINDER
            and params.radius
            and params.height
        ):
            # Zylindervolumen: π * r² * h
            volume = math.pi * (params.radius**2) * params.height

        elif self.geometry_type == GeometryType.BOX and all(
            [params.width, params.height, params.depth]
        ):
            # Quadervolumen: w * h * d
            volume = params.width * params.height * params.depth

        elif (
            self.geometry_type == GeometryType.CONE and params.radius and params.height
        ):
            # Kegelvolumen: 1/3 * π * r² * h
            volume = (1 / 3) * math.pi * (params.radius**2) * params.height

        return volume

    def to_wkt(self) -> Optional[str]:
        """Konvertierung zu Well-Known Text (WKT) wenn möglich"""

        if not SHAPELY_AVAILABLE:
            logger.warning("Shapely not available for WKT conversion")
            return None

        try:
            if self.geometry_type == GeometryType.POINT:
                coord = self.coordinates
                if isinstance(coord, SpatialCoordinate):
                    if coord.z is not None:
                        return f"POINT Z ({coord.x} {coord.y} {coord.z})"
                    else:
                        return f"POINT ({coord.x} {coord.y})"

            elif self.geometry_type == GeometryType.LINESTRING:
                coords = self.coordinates
                if isinstance(coords, list) and all(
                    isinstance(c, SpatialCoordinate) for c in coords
                ):
                    if any(c.z is not None for c in coords):
                        coord_strs = [f"{c.x} {c.y} {c.z or 0}" for c in coords]
                        return f"LINESTRING Z ({', '.join(coord_strs)})"
                    else:
                        coord_strs = [f"{c.x} {c.y}" for c in coords]
                        return f"LINESTRING ({', '.join(coord_strs)})"

            # TODO: Weitere Geometrie-Typen implementieren

        except Exception as e:
            logger.error(f"WKT conversion failed: {e}")

        return None


@dataclass
class Enhanced4DGeoLocation:
    """Erweiterte 4D Geo-Location für UDS3 Integration"""

    # Haupt-Geometrie
    primary_geometry: SpatialGeometry

    # Zusätzliche Geometrien (z.B. Gebäude-Grundriss + 3D-Modell)
    additional_geometries: List[SpatialGeometry] = field(default_factory=list)

    # Administrative und politische Zuordnungen
    administrative_areas: List[str] = field(default_factory=list)
    political_boundaries: List[str] = field(default_factory=list)

    # Legacy-Kompatibilität zu bestehender GeoLocation
    @property
    def latitude(self) -> float:
        """Legacy: Breitengrad für 2D-Kompatibilität"""
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            return self.primary_geometry.coordinates.y
        return 0.0

    @property
    def longitude(self) -> float:
        """Legacy: Längengrad für 2D-Kompatibilität"""
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            return self.primary_geometry.coordinates.x
        return 0.0

    @property
    def elevation(self) -> Optional[float]:
        """Höhenangabe (Z-Koordinate)"""
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            return self.primary_geometry.coordinates.z
        return None

    @property
    def timestamp(self) -> Optional[datetime]:
        """Zeitstempel der Geo-Location"""
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            return self.primary_geometry.coordinates.t
        return self.primary_geometry.created_at

    @property
    def accuracy_meters(self) -> Optional[float]:
        """Legacy: Horizontale Genauigkeit"""
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            return self.primary_geometry.coordinates.accuracy_xy
        return self.primary_geometry.geometric_accuracy

    @property
    def source(self) -> Optional[str]:
        """Datenquelle"""
        return self.primary_geometry.source

    @property
    def quality_score(self) -> Optional[float]:
        """Qualitätsscore"""
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            coord_quality = self.primary_geometry.coordinates.quality_score or 0.0
        else:
            coord_quality = 0.0

        geom_quality = self.primary_geometry.topological_quality or 0.0

        # Kombinierter Qualitätsscore
        return (
            (coord_quality + geom_quality) / 2.0
            if (coord_quality or geom_quality)
            else None
        )

    @property
    def coordinate_system(self) -> str:
        """Legacy: Koordinatensystem-Code"""
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            return self.primary_geometry.coordinates.crs.code
        return "EPSG:4326"

    def get_all_coordinate_systems(self) -> List[str]:
        """Alle verwendeten Koordinatensysteme"""
        crs_codes = set()

        # Primary Geometry
        if isinstance(self.primary_geometry.coordinates, SpatialCoordinate):
            crs_codes.add(self.primary_geometry.coordinates.crs.code)
        elif isinstance(self.primary_geometry.coordinates, list):
            for coord in self.primary_geometry.coordinates:
                if isinstance(coord, SpatialCoordinate):
                    crs_codes.add(coord.crs.code)

        # Additional Geometries
        for geom in self.additional_geometries:
            if isinstance(geom.coordinates, SpatialCoordinate):
                crs_codes.add(geom.coordinates.crs.code)
            elif isinstance(geom.coordinates, list):
                for coord in geom.coordinates:
                    if isinstance(coord, SpatialCoordinate):
                        crs_codes.add(coord.crs.code)

        return list(crs_codes)

    def calculate_4d_bounds(self) -> Optional[Dict]:
        """Berechnet 4D-Bounding-Box über alle Geometrien"""

        all_bounds: list[Any] = []

        # Primary Geometry
        primary_bounds = self.primary_geometry.get_bounding_box_4d()
        if primary_bounds:
            all_bounds.append(primary_bounds)

        # Additional Geometries
        for geom in self.additional_geometries:
            geom_bounds = geom.get_bounding_box_4d()
            if geom_bounds:
                all_bounds.append(geom_bounds)

        if not all_bounds:
            return None

        # Gesamt-Bounds berechnen
        combined_bounds = {
            "min_x": min(b["min_x"] for b in all_bounds),
            "max_x": max(b["max_x"] for b in all_bounds),
            "min_y": min(b["min_y"] for b in all_bounds),
            "max_y": max(b["max_y"] for b in all_bounds),
        }

        # Z-Bounds wenn vorhanden
        z_bounds = [b for b in all_bounds if "min_z" in b and "max_z" in b]
        if z_bounds:
            combined_bounds.update(
                {
                    "min_z": min(b["min_z"] for b in z_bounds),
                    "max_z": max(b["max_z"] for b in z_bounds),
                }
            )

        # T-Bounds wenn vorhanden
        t_bounds = [b for b in all_bounds if "min_t" in b and "max_t" in b]
        if t_bounds:
            combined_bounds.update(
                {
                    "min_t": min(b["min_t"] for b in t_bounds),
                    "max_t": max(b["max_t"] for b in t_bounds),
                }
            )

        return combined_bounds


class CRSTransformer:
    """Coordinate Reference System Transformations"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.CRSTransformer")
        self.transformers_cache: dict[Any, Any] = {}

    def transform_coordinate(
        self, coord: SpatialCoordinate, target_crs: CoordinateReferenceSystem
    ) -> Optional[SpatialCoordinate]:
        """Transformiert eine Koordinate in ein anderes CRS"""

        if not PYPROJ_AVAILABLE:
            self.logger.warning("PyProj not available for CRS transformation")
            return None

        if coord.crs == target_crs:
            return coord  # Keine Transformation notwendig

        try:
            # Transformer aus Cache oder neu erstellen
            cache_key = f"{coord.crs.code}->{target_crs.code}"
            if cache_key not in self.transformers_cache:
                transformer = Transformer.from_crs(
                    coord.crs.code, target_crs.code, always_xy=True
                )
                self.transformers_cache[cache_key] = transformer
            else:
                transformer = self.transformers_cache[cache_key]

            # Transformation durchführen
            if coord.z is not None:
                # 3D-Transformation
                x_new, y_new, z_new = transformer.transform(coord.x, coord.y, coord.z)
                z_transformed = z_new
            else:
                # 2D-Transformation
                x_new, y_new = transformer.transform(coord.x, coord.y)
                z_transformed = None

            # Neue transformierte Koordinate erstellen
            transformed_coord = SpatialCoordinate(
                x=x_new,
                y=y_new,
                z=z_transformed,
                t=coord.t,  # Zeit bleibt gleich
                u=coord.u,  # Transformations-Parameter übernehmen
                v=coord.v,
                w=coord.w,
                crs=target_crs,
                accuracy_xy=coord.accuracy_xy,  # Genauigkeit übernehmen
                accuracy_z=coord.accuracy_z,
                accuracy_t=coord.accuracy_t,
                quality_score=coord.quality_score,
                source=f"transformed_from_{coord.crs.code}",
                measurement_method=coord.measurement_method,
                created_at=datetime.now(),
            )

            return transformed_coord

        except Exception as e:
            self.logger.error(
                f"CRS transformation failed from {coord.crs.code} to {target_crs.code}: {e}"
            )
            return None

    def transform_geometry(
        self, geometry: SpatialGeometry, target_crs: CoordinateReferenceSystem
    ) -> Optional[SpatialGeometry]:
        """Transformiert eine komplette Geometrie in ein anderes CRS"""

        try:
            # Koordinaten transformieren
            if isinstance(geometry.coordinates, SpatialCoordinate):
                # Einzelne Koordinate
                transformed_coord = self.transform_coordinate(
                    geometry.coordinates, target_crs
                )
                if not transformed_coord:
                    return None
                new_coordinates = transformed_coord

            elif isinstance(geometry.coordinates, list):
                # Liste von Koordinaten
                new_coordinates: list[Any] = []
                for coord in geometry.coordinates:
                    if isinstance(coord, SpatialCoordinate):
                        transformed = self.transform_coordinate(coord, target_crs)
                        if transformed:
                            new_coordinates.append(transformed)
                        else:
                            return None  # Fehler bei Transformation
                    elif isinstance(coord, list):
                        # Verschachtelte Liste (Polygon)
                        nested_coords: list[Any] = []
                        for nested_coord in coord:
                            if isinstance(nested_coord, SpatialCoordinate):
                                transformed = self.transform_coordinate(
                                    nested_coord, target_crs
                                )
                                if transformed:
                                    nested_coords.append(transformed)
                                else:
                                    return None
                        new_coordinates.append(nested_coords)
            else:
                self.logger.error(
                    f"Unsupported coordinate structure: {type(geometry.coordinates)}"
                )
                return None

            # Neue Geometrie mit transformierten Koordinaten erstellen
            transformed_geometry = SpatialGeometry(
                geometry_type=geometry.geometry_type,
                coordinates=new_coordinates,
                volume_params=geometry.volume_params,
                transformation=geometry.transformation,
                temporal_validity=geometry.temporal_validity,
                temporal_resolution=geometry.temporal_resolution,
                geometric_accuracy=geometry.geometric_accuracy,
                topological_quality=geometry.topological_quality,
                completeness_score=geometry.completeness_score,
                source=f"crs_transformed_{geometry.source}"
                if geometry.source
                else "crs_transformed",
                acquisition_method=geometry.acquisition_method,
                processing_level=geometry.processing_level,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            return transformed_geometry

        except Exception as e:
            self.logger.error(f"Geometry transformation failed: {e}")
            return None


def create_4d_point(
    x: float,
    y: float,
    z: Optional[float] = None,
    t: Optional[datetime] = None,
    crs: CoordinateReferenceSystem = CoordinateReferenceSystem.WGS84_3D,
) -> Enhanced4DGeoLocation:
    """Hilfsfunktion: Erstellt einen 4D-Punkt"""

    coord = SpatialCoordinate(x=x, y=y, z=z, t=t, crs=crs)
    geometry = SpatialGeometry(
        geometry_type=GeometryType.POINT_ZM
        if (z is not None and t is not None)
        else GeometryType.POINT_Z
        if z is not None
        else GeometryType.POINT,
        coordinates=coord,
    )

    return Enhanced4DGeoLocation(primary_geometry=geometry)


def create_building_geometry(
    base_coords: List[SpatialCoordinate], height: float
) -> Enhanced4DGeoLocation:
    """Hilfsfunktion: Erstellt eine Gebäude-Geometrie aus Grundriss + Höhe"""

    # Basis-Polygon (Grundriss)
    base_polygon = SpatialGeometry(
        geometry_type=GeometryType.POLYGON,
        coordinates=[base_coords],  # Polygon als Liste von Listen
    )

    # 3D-Box für Gebäude-Volumen
    if base_coords and len(base_coords) >= 3:
        # Bounding Box des Grundrisses berechnen
        min_x = min(c.x for c in base_coords)
        max_x = max(c.x for c in base_coords)
        min_y = min(c.y for c in base_coords)
        max_y = max(c.y for c in base_coords)

        # Zentrum als Referenzpunkt
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (base_coords[0].z or 0) + height / 2

        center_coord = SpatialCoordinate(
            x=center_x, y=center_y, z=center_z, crs=base_coords[0].crs
        )

        building_volume = SpatialGeometry(
            geometry_type=GeometryType.BOX,
            coordinates=center_coord,
            volume_params=VolumetricParameters(
                width=max_x - min_x, depth=max_y - min_y, height=height
            ),
        )

        return Enhanced4DGeoLocation(
            primary_geometry=base_polygon, additional_geometries=[building_volume]
        )

    return Enhanced4DGeoLocation(primary_geometry=base_polygon)


def validate_4d_geo_location(location: Enhanced4DGeoLocation) -> bool:
    """Validiert eine 4D Geo-Location"""

    if not location or not location.primary_geometry:
        return False

    # Basis-Validierung der primären Geometrie
    geom = location.primary_geometry

    if not geom.coordinates:
        return False

    # Koordinaten-Validierung
    if isinstance(geom.coordinates, SpatialCoordinate):
        return _validate_spatial_coordinate(geom.coordinates)
    elif isinstance(geom.coordinates, list):
        return all(
            _validate_spatial_coordinate(coord)
            if isinstance(coord, SpatialCoordinate)
            else _validate_coordinate_list(coord)
            for coord in geom.coordinates
        )

    return False


def _validate_spatial_coordinate(coord: SpatialCoordinate) -> bool:
    """Validiert eine einzelne Spatial-Koordinate"""

    # Basis-Validierung
    if coord.x is None or coord.y is None:
        return False

    # CRS-spezifische Validierung
    if coord.crs in [
        CoordinateReferenceSystem.WGS84_2D,
        CoordinateReferenceSystem.WGS84_3D,
    ]:
        # Geografische Koordinaten: Latitude [-90, 90], Longitude [-180, 180]
        if not (-180 <= coord.x <= 180 and -90 <= coord.y <= 90):
            return False

    # Z-Validierung (grobe Plausibilitätsprüfung)
    if coord.z is not None:
        if not (-1000 <= coord.z <= 10000):  # -1000m bis 10000m über NN
            logger.warning(f"Unusual elevation value: {coord.z}m")

    # Genauigkeits-Validierung
    if coord.accuracy_xy is not None and coord.accuracy_xy < 0:
        return False

    if coord.quality_score is not None and not (0 <= coord.quality_score <= 1):
        return False

    return True


def _validate_coordinate_list(coord_list) -> bool:
    """Validiert eine verschachtelte Koordinaten-Liste"""

    if isinstance(coord_list, list):
        return all(
            _validate_spatial_coordinate(coord)
            if isinstance(coord, SpatialCoordinate)
            else _validate_coordinate_list(coord)
            for coord in coord_list
        )
    return False


# Export der wichtigsten Klassen
__all__ = [
    "Enhanced4DGeoLocation",
    "SpatialGeometry",
    "SpatialCoordinate",
    "GeometryType",
    "CoordinateReferenceSystem",
    "VolumetricParameters",
    "TransformationParameters",
    "CRSTransformer",
    "create_4d_point",
    "create_building_geometry",
    "validate_4d_geo_location",
]
