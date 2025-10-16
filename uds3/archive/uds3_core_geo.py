#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys.
Modification will be detected and may result in license violations.
"""

"""
UDS3 Core mit Geodaten-Integration
================================

Erweiterte UDS3CoreSystem Klasse mit vollständiger Geodaten-Unterstützung.
Integriert PostGIS, räumliche Suche und geografische Metadaten nahtlos 
in das bestehende Unified Database Strategy v3.0 System.

Features:
- Automatische Geo-Extraktion aus Dokumenteninhalten
- Räumliche Suche und Filterung
- Administrative Hierarchie-Erkennung
- Multi-Database Geo-Synchronisation (PostGIS, Neo4j, ChromaDB)
- Erweiterte Metadaten-Pipeline

Usage:
    from uds3_core_geo import UDS3CoreWithGeo
    
    uds3 = UDS3CoreWithGeo('config.json')
    doc_id = uds3.store_document_with_geo(
        content="Baugenehmigung Berlin Mitte...",
        title="Bauvorhaben Hauptstraße",
        metadata={"rechtsgebiet": "Baurecht"}
    )
    
    nearby_docs = uds3.search_by_location(52.5200, 13.4050, 5.0)

Autor: Veritas UDS3 Team  
Datum: 22. August 2025
Version: 1.0
"""

import logging
import json
from typing import Dict, List, Optional, Any
from typing import Optional, Any
from datetime import datetime
from pathlib import Path

# UDS3 Core System
try:
    from uds3_core import UDS3CoreSystem, DatabaseRole

    UDS3_CORE_AVAILABLE = True
except ImportError:
    UDS3_CORE_AVAILABLE = False
    print("Warning: UDS3 Core not available")

# Geo Extensions
try:
    from uds3_geo_extension import (
        UDS3GeoManager,
        GeoLocation,
        AdministrativeArea,
        GeoLocationExtractor,
        validate_geo_location,
    )

    try:
        from database_api_postgis import PostGISBackend  # type: ignore
    except Exception:
        from typing import Any

        PostGISBackend = Any  # type: ignore
    GEO_EXTENSIONS_AVAILABLE = True
except ImportError:
    GEO_EXTENSIONS_AVAILABLE = False
    print("Warning: Geo extensions not available")

logger = logging.getLogger(__name__)


class UDS3CoreWithGeo:
    """
    Erweiterte UDS3 Core-Klasse mit vollständiger Geodaten-Integration

    Kombiniert das bestehende UDS3-System mit räumlichen Funktionalitäten:
    - PostGIS für geografische Datenhaltung
    - Automatische Geo-Extraktion
    - Multi-Database Geo-Synchronisation
    - Erweiterte Such- und Filterfunktionen
    """

    def __init__(self, config_path: Optional[str] = None, enable_geo: bool = True):
        """
        Initialisiert UDS3 mit Geodaten-Erweiterungen

        Args:
            config_path: Pfad zur Konfigurationsdatei
            enable_geo: Geodaten-Funktionen aktivieren
        """
        self.logger = logging.getLogger(f"{__name__}.UDS3CoreWithGeo")

        # Standard UDS3 Core initialisieren
        if UDS3_CORE_AVAILABLE:
            self.uds3_core = UDS3CoreSystem(config_path)
            self.config = self.uds3_core.config
        else:
            # Fallback-Konfiguration
            # Verwende zentrale config defaults als Basis
            try:
                from . import config as _config

                base_conf = {
                    "databases": {
                        "postgis": dict(_config.DATABASES.get("postgis", {}))
                    },
                    "geo_settings": dict(_config.GEO_SETTINGS),
                }
            except Exception:
                base_conf = self._load_config(config_path)

            # Falls ein lokaler config_path angegeben ist, merge diese Werte
            file_conf = self._load_config(config_path)
            # einfacher merge: file_conf Werte überschreiben base_conf
            merged = base_conf
            merged.update(file_conf or {})
            self.config = merged
            self.uds3_core = None

        # Geo-Erweiterungen initialisieren
        self.geo_enabled = enable_geo and GEO_EXTENSIONS_AVAILABLE
        self.geo_manager = None
        self.postgis_backend = None

        if self.geo_enabled:
            self._initialize_geo_components()

        self.logger.info(
            f"UDS3CoreWithGeo initialized (Geo: {'enabled' if self.geo_enabled else 'disabled'})"
        )

    def _load_config(self, config_path: str) -> Dict:
        """Lädt Konfiguration aus Datei oder verwendet Defaults"""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load config from {config_path}: {e}")

        # Default-Konfiguration
        return {
            "databases": {
                "postgis": {
                    "enabled": False,
                    "host": "localhost",
                    "database": "uds3_geo",
                    "user": "postgres",
                    "password": "",
                }
            },
            "geo_settings": {
                "auto_extract": True,
                "quality_threshold": 0.5,
                "default_srid": 4326,
            },
        }

    def _initialize_geo_components(self):
        """Initialisiert alle Geodaten-Komponenten"""
        try:
            # PostGIS Backend
            def _merge_db_config(local_cfg: dict, key: str) -> dict:
                """Merge central DATABASES defaults with a local override dict.

                local_cfg: the local config dict (may be empty or None).
                key: database key in central _config.DATABASES (e.g. 'postgis').
                """
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

            postgis_config = _merge_db_config(
                self.config.get("databases", {}).get("postgis", {}), "postgis"
            )

            if postgis_config.get("enabled", True):
                self.postgis_backend = PostGISBackend(postgis_config)

                if self.postgis_backend.connect():
                    self.logger.info("PostGIS backend connected successfully")
                else:
                    self.logger.warning("PostGIS backend connection failed")
                    self.postgis_backend = None

            # Geo-Manager
            if self.uds3_core:
                self.geo_manager = UDS3GeoManager(self.uds3_core, postgis_config)
            else:
                # Standalone Geo-Manager
                self.geo_manager = UDS3GeoManager(self, postgis_config)

            self.logger.info("Geo components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize geo components: {e}")
            self.geo_enabled = False

    # === DOCUMENT STORAGE WITH GEO ===

    def store_document_with_geo(
        self,
        content: str,
        title: str,
        metadata: Dict,
        location: GeoLocation = None,
        auto_extract_geo: Optional[bool] = None,
    ) -> str:
        """
        Speichert Dokument mit automatischer oder expliziter Geo-Zuordnung

        Args:
            content: Dokumenteninhalt
            title: Dokumententitel
            metadata: Standard UDS3-Metadaten
            location: Optional - explizite Geo-Location
            auto_extract_geo: Geo-Extraktion aktivieren (überschreibt Config)

        Returns:
            Document ID
        """

        # Standard UDS3 Speicherung
        if self.uds3_core:
            doc_id = self.uds3_core.store_document(content, title, metadata)
        else:
            # Fallback: Einfache ID-Generierung
            import uuid

            doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Geodaten-Processing
        if self.geo_enabled and self.geo_manager:
            should_extract = (
                auto_extract_geo
                if auto_extract_geo is not None
                else self.config.get("geo_settings", {}).get("auto_extract", True)
            )

            # Geo-Location extrahieren wenn nicht gegeben
            if not location and should_extract:
                document = {"content": content, "title": title, **metadata}
                location = self.geo_manager.geo_extractor.extract_from_document(
                    content, title, metadata
                )

            # Geodaten hinzufügen
            if location and validate_geo_location(location):
                success = self._add_geo_to_document(doc_id, title, location, metadata)
                if success:
                    self.logger.info(f"Geo metadata added to document {doc_id}")

                    # Geo-Processing Metadaten speichern
                    geo_meta = {
                        "geo_processed": True,
                        "geo_location": {
                            "lat": location.latitude,
                            "lng": location.longitude,
                            "quality": location.quality_score,
                            "source": location.source,
                        },
                        "geo_processed_at": datetime.now().isoformat(),
                    }

                    # Geo-Metadaten zu Standard-Metadaten hinzufügen
                    if hasattr(self.uds3_core, "update_document_metadata"):
                        self.uds3_core.update_document_metadata(doc_id, geo_meta)

            elif should_extract:
                self.logger.debug(f"No valid geo location found for document {doc_id}")

        return doc_id

    def _add_geo_to_document(
        self, doc_id: str, title: str, location: GeoLocation, metadata: Dict
    ) -> bool:
        """Fügt Geodaten zu allen relevanten Datenbanken hinzu"""

        success_count = 0

        # PostGIS - Relationale Geodaten
        if self.postgis_backend:
            try:
                doc_data = {
                    "id": doc_id,
                    "title": title,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "location_accuracy": location.accuracy_meters,
                    "location_source": location.source,
                    "geo_quality_score": location.quality_score,
                    "coordinate_system": location.coordinate_system,
                    **{
                        k: v
                        for k, v in metadata.items()
                        if k
                        in [
                            "rechtsgebiet",
                            "gericht",
                            "aktenzeichen",
                            "postal_code",
                            "municipality",
                            "district",
                            "state",
                        ]
                    },
                }

                if self.postgis_backend.insert_document_with_geo(doc_data):
                    success_count += 1

            except Exception as e:
                self.logger.error(f"Failed to add PostGIS geo data: {e}")

        # Neo4j - Graph-Beziehungen
        if (
            self.uds3_core
            and hasattr(self.uds3_core, "graph_backend")
            and self.uds3_core.graph_backend
        ):
            try:
                # Administrative Hierarchie ermitteln
                admin_areas: list[Any] = []
                if self.postgis_backend:
                    admin_hierarchy = self.postgis_backend.get_administrative_hierarchy(
                        location.latitude, location.longitude
                    )
                    admin_areas = [area["name"] for area in admin_hierarchy]

                # Neo4j Geo-Relationships erstellen
                self._create_neo4j_geo_relationships(doc_id, location, admin_areas)
                success_count += 1

            except Exception as e:
                self.logger.error(f"Failed to add Neo4j geo relationships: {e}")

        # ChromaDB - Geo-Context in Embeddings
        if (
            self.uds3_core
            and hasattr(self.uds3_core, "vector_backend")
            and self.uds3_core.vector_backend
        ):
            try:
                self._update_vector_geo_context(doc_id, location)
                success_count += 1

            except Exception as e:
                self.logger.error(f"Failed to update vector geo context: {e}")

        return success_count > 0

    def _create_neo4j_geo_relationships(
        self, doc_id: str, location: GeoLocation, admin_areas: List[str]
    ):
        """Erstellt Geo-Beziehungen in Neo4j"""

        if not (self.uds3_core and hasattr(self.uds3_core, "graph_backend")):
            return

        try:
            session = self.uds3_core.graph_backend.session

            # Dokument mit Geo-Properties
            cypher = """
                MERGE (doc:Document {id: $doc_id})
                SET doc.latitude = $lat,
                    doc.longitude = $lng,
                    doc.geo_quality = $quality,
                    doc.geo_source = $source,
                    doc.coordinate_system = $coord_sys,
                    doc.geo_updated = datetime()
            """

            session.run(
                cypher,
                {
                    "doc_id": doc_id,
                    "lat": location.latitude,
                    "lng": location.longitude,
                    "quality": location.quality_score or 0.5,
                    "source": location.source or "extracted",
                    "coord_sys": location.coordinate_system,
                },
            )

            # Beziehungen zu Verwaltungsgebieten
            for area_name in admin_areas:
                cypher_area = """
                    MATCH (doc:Document {id: $doc_id})
                    MERGE (area:AdministrativeArea {name: $area_name})
                    ON CREATE SET area.created = datetime()
                    MERGE (doc)-[r:LOCATED_IN]->(area)
                    ON CREATE SET r.created = datetime()
                    SET r.confidence = $confidence
                """

                session.run(
                    cypher_area,
                    {
                        "doc_id": doc_id,
                        "area_name": area_name,
                        "confidence": location.quality_score or 0.7,
                    },
                )

            # Räumliche Nachbarschaft zu anderen Dokumenten (5km Radius)
            if self.postgis_backend:
                nearby_docs = self.postgis_backend.spatial_search_documents(
                    location.latitude, location.longitude, 5.0, limit=10
                )

                for nearby in nearby_docs:
                    if nearby["id"] != doc_id:
                        cypher_nearby = """
                            MATCH (doc1:Document {id: $doc_id})
                            MATCH (doc2:Document {id: $nearby_id})
                            MERGE (doc1)-[r:SPATIALLY_NEAR]->(doc2)
                            SET r.distance_km = $distance_km,
                                r.created = datetime()
                        """

                        session.run(
                            cypher_nearby,
                            {
                                "doc_id": doc_id,
                                "nearby_id": nearby["id"],
                                "distance_km": float(nearby.get("distance_km", 0)),
                            },
                        )

        except Exception as e:
            self.logger.error(f"Failed to create Neo4j geo relationships: {e}")

    def _update_vector_geo_context(self, doc_id: str, location: GeoLocation):
        """Erweitert Vector DB um Geo-Kontext"""

        if not (self.uds3_core and hasattr(self.uds3_core, "vector_backend")):
            return

        try:
            # Administrative Kontexte sammeln
            geo_context_parts = ["Deutschland"]  # Default Land

            if self.postgis_backend:
                admin_hierarchy = self.postgis_backend.get_administrative_hierarchy(
                    location.latitude, location.longitude
                )

                for area in admin_hierarchy:
                    if area.get("name"):
                        geo_context_parts.append(area["name"])

            # Geo-Tags basierend auf Koordinaten
            geo_tags = self._generate_geo_tags(location)
            geo_context_parts.extend(geo_tags)

            # Geo-Metadaten für ChromaDB
            geo_metadata = {
                "geo_latitude": location.latitude,
                "geo_longitude": location.longitude,
                "geo_context": " ".join(geo_context_parts),
                "geo_quality": location.quality_score or 0.5,
                "geo_source": location.source or "extracted",
                "geo_tags": ",".join(geo_tags),
                "coordinate_system": location.coordinate_system,
            }

            # Metadaten-Update (Implementation abhängig vom Vector Backend)
            if hasattr(self.uds3_core.vector_backend, "update_metadata"):
                self.uds3_core.vector_backend.update_metadata(doc_id, geo_metadata)

        except Exception as e:
            self.logger.error(f"Failed to update vector geo context: {e}")

    def _generate_geo_tags(self, location: GeoLocation) -> List[str]:
        """Generiert geografische Tags basierend auf Koordinaten"""

        tags: list[Any] = []

        # Grobe geografische Einordnung für Deutschland
        lat, lng = location.latitude, location.longitude

        # Nord/Süd
        if lat > 53.0:
            tags.append("norddeutschland")
        elif lat > 51.0:
            tags.append("mitteldeutschland")
        else:
            tags.append("süddeutschland")

        # West/Ost (grobe Einordnung)
        if lng < 9.0:
            tags.append("westdeutschland")
        elif lng > 12.0:
            tags.append("ostdeutschland")
        else:
            tags.append("mitteldeutschland")

        # Koordinaten-Genauigkeit
        if location.accuracy_meters:
            if location.accuracy_meters <= 100:
                tags.append("hochpräzise")
            elif location.accuracy_meters <= 1000:
                tags.append("präzise")
            else:
                tags.append("ungefähr")

        return tags

    # === SPATIAL SEARCH OPERATIONS ===

    def search_by_location(
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
            Liste von Dokumenten mit Entfernungsangaben und Geo-Metadaten
        """

        if not self.geo_enabled or not self.postgis_backend:
            self.logger.warning("Geo search not available - PostGIS not configured")
            return []

        try:
            # PostGIS Spatial Search
            results = self.postgis_backend.spatial_search_documents(
                center_lat, center_lng, radius_km, filters, limit
            )

            # Ergebnisse mit zusätzlichen UDS3-Daten anreichern
            enriched_results: list[Any] = []
            for result in results:
                doc_id = result["id"]

                # UDS3 Core-Daten hinzufügen wenn verfügbar
                if self.uds3_core:
                    try:
                        # Vector similarity für Geo-Context
                        if (
                            hasattr(self.uds3_core, "vector_backend")
                            and self.uds3_core.vector_backend
                        ):
                            geo_query = f"Dokumente in der Nähe von {center_lat:.4f}, {center_lng:.4f}"
                            similarity_score = self._calculate_geo_similarity(
                                doc_id, geo_query
                            )
                            result["similarity_score"] = similarity_score

                        # Graph-Beziehungen
                        if (
                            hasattr(self.uds3_core, "graph_backend")
                            and self.uds3_core.graph_backend
                        ):
                            relationships: list[Any] = []
                            result["relationships"] = relationships

                    except Exception as e:
                        self.logger.debug(f"Failed to enrich result for {doc_id}: {e}")

                enriched_results.append(result)

            return enriched_results

        except Exception as e:
            self.logger.error(f"Geo search failed: {e}")
            return []

    def get_document_geography(self, doc_id: str) -> Dict[str, Any]:
        """
        Ermittelt vollständige geografische Informationen eines Dokuments

        Returns:
            Dictionary mit Location, Administrative Hierarchie, Beziehungen, etc.
        """

        if not self.geo_enabled:
            return {"error": "Geo functionality not enabled"}

geo_info: dict[str, Any] = {}
            "document_id": doc_id,
            "location": None,
            "administrative_hierarchy": [],
            "nearby_documents": [],
            "institution_jurisdictions": [],
            "spatial_relationships": {},
            "geo_quality_metrics": {},
        }

        # PostGIS Geo-Daten
        if self.postgis_backend:
            try:
                # Dokument-Location
                with self.postgis_backend.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT 
                            ST_X(location_point) as longitude,
                            ST_Y(location_point) as latitude,
                            coordinate_system, location_accuracy, location_source, 
                            geo_quality_score, postal_code, municipality, district, state
                        FROM uds3_documents_geo 
                        WHERE id = %s
                    """,
                        [doc_id],
                    )

                    row = cursor.fetchone()
                    if row and row["latitude"]:
                        geo_info["location"] = dict(row)

                        # Administrative Hierarchie
                        admin_hierarchy = (
                            self.postgis_backend.get_administrative_hierarchy(
                                row["latitude"], row["longitude"]
                            )
                        )
                        geo_info["administrative_hierarchy"] = admin_hierarchy

                        # Nearby Documents
                        nearby = self.postgis_backend.spatial_search_documents(
                            row["latitude"], row["longitude"], 5.0, limit=10
                        )
                        geo_info["nearby_documents"] = [
                            doc for doc in nearby if doc["id"] != doc_id
                        ]

                        # Zuständige Institutionen
                        jurisdictions = self.postgis_backend.find_jurisdictions(
                            row["latitude"], row["longitude"]
                        )
                        geo_info["institution_jurisdictions"] = jurisdictions

            except Exception as e:
                self.logger.error(f"Failed to get PostGIS geo info: {e}")

        # Neo4j Spatial Relationships
        if self.uds3_core and hasattr(self.uds3_core, "graph_backend"):
            try:
                relationships: list[Any] = []
                geo_info["spatial_relationships"] = relationships

            except Exception as e:
                self.logger.error(f"Failed to get Neo4j relationships: {e}")

        # Qualitätsmetriken
        geo_info["geo_quality_metrics"] = self._calculate_geo_quality_metrics(geo_info)

        return geo_info

    def _get_document_geo_relationships(self, doc_id: str) -> Dict:
        """Ermittelt geografische Beziehungen aus Neo4j"""

        relationships = {
            "administrative_areas": [],
            "nearby_documents": [],
            "institutions": [],
        }

        if not (self.uds3_core and hasattr(self.uds3_core, "graph_backend")):
            return relationships

        try:
            session = self.uds3_core.graph_backend.session

            # Administrative Gebiete
            cypher = """
                MATCH (doc:Document {id: $doc_id})-[r:LOCATED_IN]->(area:AdministrativeArea)
                RETURN area.name as name, r.confidence as confidence
                ORDER BY r.confidence DESC
            """

            result = session.run(cypher, {"doc_id": doc_id})
            relationships["administrative_areas"] = [
                {"name": record["name"], "confidence": record["confidence"]}
                for record in result
            ]

            # Nearby Documents
            cypher = """
                MATCH (doc:Document {id: $doc_id})-[r:SPATIALLY_NEAR]->(nearby:Document)
                RETURN nearby.id as id, r.distance_km as distance_km
                ORDER BY r.distance_km ASC
                LIMIT 10
            """

            result = session.run(cypher, {"doc_id": doc_id})
            relationships["nearby_documents"] = [
                {"id": record["id"], "distance_km": record["distance_km"]}
                for record in result
            ]

        except Exception as e:
            self.logger.error(f"Failed to get Neo4j geo relationships: {e}")

        return relationships

    def _calculate_geo_similarity(self, doc_id: str, geo_query: str) -> float:
        """Berechnet Geo-Ähnlichkeit für Vector Search"""

        if not (self.uds3_core and hasattr(self.uds3_core, "vector_backend")):
            return 0.0

        try:
            # Vereinfachte Similarity-Berechnung
            # In der Praxis würde hier ein Geo-enhanced Embedding verwendet
            if hasattr(self.uds3_core.vector_backend, "similarity_search"):
                results = self.uds3_core.vector_backend.similarity_search(geo_query, 1)
                for result in results:
                    if result.get("id") == doc_id:
                        return result.get("similarity", 0.0)

        except Exception as e:
            self.logger.debug(f"Failed to calculate geo similarity: {e}")

        return 0.0

    def _calculate_geo_quality_metrics(self, geo_info: Dict) -> Dict:
        """Berechnet Qualitätsmetriken für Geodaten"""

        metrics = {
            "overall_quality": 0.0,
            "location_accuracy": "unknown",
            "data_completeness": 0.0,
            "administrative_coverage": 0.0,
        }

        try:
            location = geo_info.get("location")
            if not location:
                return metrics

            # Overall Quality basierend auf Score
            quality_score = location.get("geo_quality_score", 0.0)
            metrics["overall_quality"] = float(quality_score) if quality_score else 0.0

            # Location Accuracy
            accuracy = location.get("location_accuracy")
            if accuracy:
                if accuracy <= 100:
                    metrics["location_accuracy"] = "high"
                elif accuracy <= 1000:
                    metrics["location_accuracy"] = "medium"
                else:
                    metrics["location_accuracy"] = "low"

            # Data Completeness (0.0 - 1.0)
            completeness_fields = [
                "longitude",
                "latitude",
                "postal_code",
                "municipality",
                "state",
            ]
            complete_fields = sum(
                1 for field in completeness_fields if location.get(field)
            )
            metrics["data_completeness"] = complete_fields / len(completeness_fields)

            # Administrative Coverage
            admin_hierarchy = geo_info.get("administrative_hierarchy", [])
            metrics["administrative_coverage"] = (
                len(admin_hierarchy) / 5.0
            )  # Max 5 Ebenen

        except Exception as e:
            self.logger.error(f"Failed to calculate geo quality metrics: {e}")

        return metrics

    # === STATISTICS AND UTILITIES ===

    def get_geo_statistics(self) -> Dict[str, Any]:
        """Erstellt umfassende Geodaten-Statistiken"""

        if not self.geo_enabled:
            return {"error": "Geo functionality not enabled"}

        stats = {
            "system_info": {
                "geo_enabled": self.geo_enabled,
                "postgis_available": self.postgis_backend is not None,
                "uds3_core_available": self.uds3_core is not None,
            },
            "generated_at": datetime.now().isoformat(),
        }

        # PostGIS Statistics
        if self.postgis_backend:
            try:
                postgis_stats = self.postgis_backend.get_geo_statistics()
                stats["postgis"] = postgis_stats
            except Exception as e:
                stats["postgis"] = {"error": str(e)}

        # UDS3 Integration Statistics
        if self.uds3_core:
            try:
                # Vector DB Geo-Context
                if (
                    hasattr(self.uds3_core, "vector_backend")
                    and self.uds3_core.vector_backend
                ):
                    stats["vector_geo_integration"] = {
                        "status": "active",
                        "geo_enhanced_embeddings": True,
                    }

                # Graph DB Spatial Relationships
                if (
                    hasattr(self.uds3_core, "graph_backend")
                    and self.uds3_core.graph_backend
                ):
                    stats["graph_geo_integration"] = {
                        "status": "active",
                        "spatial_relationships": True,
                    }

            except Exception as e:
                stats["uds3_integration_error"] = str(e)

        return stats

    # === PASSTHROUGH METHODS TO UDS3 CORE ===

    def store_document(self, content: str, title: str, metadata: Dict) -> str:
        """Standard UDS3 Dokumentenspeicherung (ohne Geo)"""
        if self.uds3_core:
            return self.uds3_core.store_document(content, title, metadata)
        else:
            import uuid

            return f"doc_{uuid.uuid4().hex[:12]}"

    def search_documents(
        self, query: str, filters: Optional[Dict[Any, Any]] = None, limit: int = 10
    ) -> List[Dict]:
        """Standard UDS3 Dokumentensuche"""
        if self.uds3_core:
            return self.uds3_core.search_documents(query, filters, limit)
        return []

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Einzelnes Dokument abrufen"""
        if self.uds3_core:
            return self.uds3_core.get_document(doc_id)
        return None

    def health_check(self) -> Dict[str, Any]:
        """System-Gesundheitscheck"""
        health = {
            "geo_system": "healthy" if self.geo_enabled else "disabled",
            "postgis": "disconnected",
            "uds3_core": "unavailable",
        }

        if self.postgis_backend:
            try:
                postgis_health = self.postgis_backend.health_check()
                health["postgis"] = postgis_health.get("status", "unknown")
            except:
                health["postgis"] = "error"

        if self.uds3_core:
            try:
                core_health = self.uds3_core.health_check()
                health["uds3_core"] = core_health.get("status", "unknown")
            except:
                health["uds3_core"] = "error"

        return health


# Export
__all__ = ["UDS3CoreWithGeo"]

"""
VERITAS Protected Module
WARNING: This file contains embedded protection keys. 
Modification will be detected and may result in license violations.
"""

# === VERITAS PROTECTION KEYS (DO NOT MODIFY) ===
module_name = "uds3_core_geo"
module_licenced_organization = "VERITAS_TECH_GMBH"
module_licence_key = "eyJjbGllbnRfaWQi...NzRkYzhl"  # Gekuerzt fuer Sicherheit
module_organization_key = (
    "6f5304c29594443086e1ace0011c094614b612c22aa16af9f1a63f02a0c9bf5c"
)
module_file_key = "da111c26ef57c2bd7b36e7a747c8e98e4dfb2c4fbb746e2715ffab90521640da"
module_version = "1.0"
module_protection_level = 2
# === END PROTECTION KEYS ===