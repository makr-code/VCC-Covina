# WFS Ingestion Worker
**Automated Web Feature Service Ingestion for Covina UDS3**

## 🗺️ Overview

Der **WFS Ingestion Worker** ermöglicht die automatische Ingestion von Geodaten aus OGC Web Feature Services (WFS) in die Covina UDS3 Pipeline.

## Features

✅ **OGC WFS Support**
- WFS 1.0.0, 1.1.0, 2.0.0
- GetCapabilities, DescribeFeatureType, GetFeature
- GML und GeoJSON Output-Formate

✅ **Geometry Handling**
- Coordinate System Transformation (EPSG)
- Shapely/PyProj Integration
- Spatial Metadata Extraction
- Centroid, Bounds, Area Calculation

✅ **Data Processing**
- Automatic Pagination für große Datasets
- Attribute Mapping
- Property Filtering
- Retry Logic & Error Handling

✅ **UDS3 Integration**
- Automatische Konvertierung zu UDS3 Format
- Metadata Enrichment
- Classification als GEO_DATA
- JSON Output für Ingestion Pipeline

## 📦 Installation

### Dependencies
```bash
# Core dependencies (required)
pip install requests

# Geometry support (recommended)
pip install shapely pyproj

# Rich terminal UI (optional)
pip install rich
```

## 🚀 Quick Start

### 1. Create Metadata File

Create `my_wfs_service.json`:
```json
{
  "wfs_service": {
    "url": "https://inspire.brandenburg.de/services/bimschg_wfs",
    "version": "2.0.0",
    "layers": ["bimschg:Anlagen"],
    "output_format": "application/json"
  }
}
```

### 2. Run Ingestion

```bash
python -m ingestion.wfs_ingestion_worker my_wfs_service.json
```

### 3. Check Output

Ingested documents are saved to `data/wfs_ingestion/`:
```
data/wfs_ingestion/
├── bimschg_Anlagen_<feature_id>_<timestamp>.json
├── bimschg_Anlagen_<feature_id>_<timestamp>.json
└── ...
```

## 📋 Metadata Schema

### Complete Example

See `examples/wfs_metadata_brandenburg_bimschg.json`:

```json
{
  "wfs_service": {
    "url": "https://inspire.brandenburg.de/services/bimschg_wfs",
    "version": "2.0.0",
    "layers": ["bimschg:Anlagen"],
    "output_format": "application/json",
    "srs": "EPSG:4326",
    "max_features": 1000,
    "timeout": 30,
    "retry_count": 3
  },
  "ingestion_config": {
    "source_name": "Brandenburg INSPIRE BImSchG WFS",
    "source_type": "wfs",
    "category": "environmental",
    "data_provider": "Land Brandenburg"
  },
  "attribute_mapping": {
    "inspireId": "feature_id",
    "name": "facility_name",
    "type": "facility_type"
  }
}
```

### Schema Documentation

#### wfs_service (required)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | ✅ | - | WFS service base URL |
| `version` | string | ❌ | "2.0.0" | WFS version (1.0.0, 1.1.0, 2.0.0) |
| `layers` | array | ✅ | [] | Layer names to ingest |
| `output_format` | string | ❌ | "application/json" | Output format (GeoJSON, GML) |
| `srs` | string | ❌ | "EPSG:4326" | Coordinate reference system |
| `max_features` | int | ❌ | 1000 | Features per request (pagination) |
| `timeout` | int | ❌ | 30 | Request timeout (seconds) |
| `retry_count` | int | ❌ | 3 | Number of retry attempts |

#### ingestion_config (optional)

Additional metadata added to all ingested documents:
```json
{
  "source_name": "Data Source Name",
  "source_type": "wfs",
  "category": "environmental|administrative|infrastructure|...",
  "data_provider": "Provider Name",
  "license": "License Information",
  "update_frequency": "daily|weekly|monthly"
}
```

#### attribute_mapping (optional)

Map WFS feature attributes to UDS3 metadata fields:
```json
{
  "wfs_attribute_name": "target_metadata_field",
  "inspireId": "feature_id",
  "name": "facility_name"
}
```

#### filters (optional)

Filter features before ingestion:
```json
{
  "bbox": [minx, miny, maxx, maxy],
  "property_filters": {
    "status": "active",
    "type": "industrial"
  }
}
```

#### transformation (optional)

Geometry transformation settings:
```json
{
  "target_crs": "EPSG:4326",
  "geometry_simplification": false,
  "simplification_tolerance": 0.0001
}
```

## 🎯 Use Cases

### 1. INSPIRE WFS Services

Brandenburg BImSchG Anlagen:
```bash
python -m ingestion.wfs_ingestion_worker examples/wfs_metadata_brandenburg_bimschg.json
```

### 2. Custom WFS Services

Create metadata file for your WFS:
```json
{
  "wfs_service": {
    "url": "https://your-server.com/geoserver/wfs",
    "layers": ["workspace:layer_name"]
  }
}
```

### 3. Multiple Layers

Ingest multiple layers from same service:
```json
{
  "wfs_service": {
    "url": "https://server.com/wfs",
    "layers": [
      "namespace:layer1",
      "namespace:layer2",
      "namespace:layer3"
    ]
  }
}
```

### 4. Large Datasets

Automatic pagination for datasets >1000 features:
```json
{
  "wfs_service": {
    "max_features": 500
  }
}
```
The worker automatically fetches all features using pagination.

## 📊 Output Format

### UDS3 Document Structure

Converted documents follow UDS3 format:

```json
{
  "doc_id": "bimschg_Anlagen_123_1759941234",
  "content": "inspireId: DE123...\nname: Facility Name\ntype: industrial",
  "metadata": {
    "source": "wfs",
    "wfs_service": "https://inspire.brandenburg.de/services/bimschg_wfs",
    "layer_name": "bimschg:Anlagen",
    "feature_id": "123",
    "crs": "EPSG:4326",
    "ingestion_timestamp": "2025-10-08T19:00:00",
    "has_geometry": true,
    "geometry_type": "Point",
    "centroid": {"lon": 13.4, "lat": 52.5},
    "area": 0.0,
    "bounds": [13.4, 52.5, 13.4, 52.5],
    "facility_name": "Example Facility",
    "facility_type": "industrial",
    "source_name": "Brandenburg INSPIRE BImSchG WFS",
    "category": "environmental"
  },
  "geometry": {
    "type": "Point",
    "coordinates": [13.4, 52.5]
  },
  "classification": "GEO_DATA",
  "file_path": "wfs://bimschg:Anlagen/123"
}
```

## 🔧 Advanced Configuration

### Custom Coordinate Systems

Transform to specific CRS:
```json
{
  "wfs_service": {
    "srs": "EPSG:25833"
  },
  "transformation": {
    "target_crs": "EPSG:4326"
  }
}
```

### Bounding Box Filter

Limit ingestion to specific area:
```json
{
  "filters": {
    "bbox": [13.0, 52.0, 14.0, 53.0]
  }
}
```

### Geometry Simplification

Simplify complex geometries:
```json
{
  "transformation": {
    "geometry_simplification": true,
    "simplification_tolerance": 0.0001
  }
}
```

### Retry Configuration

Configure retry behavior:
```json
{
  "wfs_service": {
    "retry_count": 5,
    "timeout": 60
  }
}
```

## 📈 Performance

### Pagination

- Default: 1000 features per request
- Automatic continuation until all features fetched
- Progress bar shows current status

### Parallel Processing

Currently sequential, planned enhancements:
- Parallel layer processing
- Concurrent feature conversion
- Batch ingestion to UDS3

### Memory Usage

- Streaming feature processing
- No full dataset in memory
- Suitable for large datasets (>100k features)

## 🐛 Troubleshooting

### "Connection timeout"

Increase timeout:
```json
{
  "wfs_service": {
    "timeout": 60
  }
}
```

### "No features found"

Check layer name in GetCapabilities:
```bash
curl "https://server.com/wfs?request=GetCapabilities&service=WFS"
```

### "Geometry transformation failed"

Install shapely:
```bash
pip install shapely pyproj
```

### "Output format not supported"

Try different format:
```json
{
  "wfs_service": {
    "output_format": "application/json"
  }
}
```
Or use GML:
```json
{
  "wfs_service": {
    "output_format": "text/xml; subtype=gml/3.1.1"
  }
}
```

## 🧪 Testing

### Test with Brandenburg BImSchG

```bash
# Run ingestion
python -m ingestion.wfs_ingestion_worker examples/wfs_metadata_brandenburg_bimschg.json

# Check output
ls -l data/wfs_ingestion/

# Verify documents
cat data/wfs_ingestion/bimschg_*.json | jq .
```

### Test WFS Connectivity

```python
from ingestion.wfs_ingestion_worker import WFSClient, WFSServiceConfig

# Create client
config = WFSServiceConfig(
    url="https://inspire.brandenburg.de/services/bimschg_wfs",
    version="2.0.0"
)
client = WFSClient(config)

# Test GetCapabilities
capabilities = client.get_capabilities()
print(f"Service: {capabilities['service_title']}")
print(f"Layers: {len(capabilities['feature_types'])}")

# Test GetFeature
features = client.get_feature("bimschg:Anlagen", max_features=10)
print(f"Fetched {len(features)} features")
```

## 📚 Examples

### Example 1: Simple Ingestion

`simple_wfs.json`:
```json
{
  "wfs_service": {
    "url": "https://server.com/wfs",
    "layers": ["namespace:layer"]
  }
}
```

### Example 2: With Attribute Mapping

`mapped_wfs.json`:
```json
{
  "wfs_service": {
    "url": "https://server.com/wfs",
    "layers": ["cities"]
  },
  "attribute_mapping": {
    "NAME": "city_name",
    "POP": "population",
    "AREA": "area_sqkm"
  }
}
```

### Example 3: Filtered Ingestion

`filtered_wfs.json`:
```json
{
  "wfs_service": {
    "url": "https://server.com/wfs",
    "layers": ["facilities"]
  },
  "filters": {
    "bbox": [13.0, 52.0, 14.0, 53.0],
    "property_filters": {
      "status": "active",
      "type": "industrial"
    }
  }
}
```

## 🔗 Integration with UDS3 Pipeline

### Manual Integration

1. **Run WFS Ingestion:**
   ```bash
   python -m ingestion.wfs_ingestion_worker metadata.json
   ```

2. **Process with UDS3:**
   ```bash
   # Documents are in data/wfs_ingestion/
   python backend.py upload data/wfs_ingestion/
   ```

### Automated Integration

Add to ingestion pipeline:
```python
from ingestion.wfs_ingestion_worker import WFSIngestionWorker
from pathlib import Path

# Run WFS ingestion
worker = WFSIngestionWorker(Path("metadata.json"))
results = await worker.run_ingestion()

# Process results
for result in results:
    print(f"Layer {result.layer_name}: {result.features_ingested} features")
```

## 🎯 Roadmap

### Planned Features

- [ ] WFS 3.0 (OGC API Features) support
- [ ] Incremental updates (changed features only)
- [ ] PostGIS direct integration
- [ ] Parallel layer processing
- [ ] Custom CQL filters
- [ ] Geometry validation
- [ ] Topology checking
- [ ] Time-series support (temporal WFS)
- [ ] Web UI for metadata creation
- [ ] Scheduled automatic ingestion

### Performance Improvements

- [ ] Streaming JSON parsing
- [ ] Batch database inserts
- [ ] Connection pooling
- [ ] Async HTTP requests
- [ ] Feature caching

## 📝 Notes

### Supported Services

Tested with:
- ✅ GeoServer WFS
- ✅ INSPIRE WFS Services (Brandenburg, NRW)
- ✅ MapServer WFS
- ⏳ ArcGIS Server WFS (partially)
- ⏳ QGIS Server WFS (partially)

### Limitations

- GML parsing is simplified (use GeoJSON when possible)
- Complex geometries may need simplification
- Large datasets (>1M features) may need optimization
- CQL filters not yet implemented

### Best Practices

1. **Use GeoJSON output format** for better performance
2. **Test with small max_features** first (e.g., 100)
3. **Check GetCapabilities** to verify layer names
4. **Use EPSG:4326** for maximum compatibility
5. **Implement proper error handling** in production
6. **Monitor disk space** for large ingestions

## ✅ Summary

Der **WFS Ingestion Worker** bietet eine vollständige Lösung für die automatische Geodaten-Ingestion aus WFS-Services in die Covina UDS3 Pipeline.

**Key Features:**
- ✅ OGC WFS 1.0/1.1/2.0 Support
- ✅ Automatic Pagination
- ✅ Geometry Transformation
- ✅ Metadata Enrichment
- ✅ Error Handling & Retry
- ✅ Rich Terminal UI
- ✅ UDS3 Integration

**Ready for production use with INSPIRE WFS services!** 🗺️

---

**Author:** Covina Development Team  
**Date:** 8. Oktober 2025  
**Status:** ✅ PRODUCTION READY
