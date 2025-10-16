# UDS3 4D-Geodaten Integration - Deployment Plan

## Sofortige Integration (Nächste Schritte)

### 1. Backend-Integration 
```python
# In database_config.py erweitern:
POSTGIS_4D_CONFIG = {
    'enabled': True,
    'primary_crs': 'EPSG:4326',  # WGS84 als Standard
    'supported_crs': ['EPSG:4326', 'EPSG:25832', 'EPSG:31467'],  # WGS84, UTM32N, GK3
    'enable_volumetric': True,
    'enable_temporal': True,
    'quality_threshold': 0.7
}
```

### 2. Scraper-Erweiterung für 4D-Geo-Extraktion
```python
# In scraper_framework.py integrieren:
from uds3_4d_geo_extension import Enhanced4DGeoLocation, GeometryType

def extract_4d_legal_locations(self, content: str, metadata: dict) -> List[Enhanced4DGeoLocation]:
    """Erweiterte 4D-Geo-Extraktion für Rechtsdokumente"""
    
    locations = []
    
    # Standard-Orts-Extraktion
    standard_locations = self.extract_locations(content)
    
    for loc in standard_locations:
        # 4D-Enhancement
        enhanced_4d = Enhanced4DGeoLocation(
            primary_geometry=SpatialGeometry(
                coordinates=SpatialCoordinate(
                    x=loc.longitude, y=loc.latitude,
                    crs=CoordinateReferenceSystem.WGS84_2D
                ),
                geometry_type=GeometryType.POINT
            )
        )
        
        # Zeitbezug aus Rechtsdokument extrahieren
        if 'entscheidungsdatum' in metadata:
            enhanced_4d.primary_geometry.coordinates.t = metadata['entscheidungsdatum']
            
        # Administrative Zuordnung  
        enhanced_4d.administrative_areas = [loc.municipality, loc.district, loc.state]
        
        locations.append(enhanced_4d)
    
    return locations
```

### 3. API-Endpoint-Erweiterung
```python
# Neue 4D-Geo-Endpoints in api_endpoint.py:

@app.route('/api/v1/search/4d-geo', methods=['POST'])
def search_4d_geo():
    """4D-Geodaten-Suche"""
    try:
        data = request.get_json()
        
        center = SpatialCoordinate(
            x=data['longitude'], y=data['latitude'], z=data.get('elevation'),
            crs=CoordinateReferenceSystem[data.get('crs', 'WGS84_2D')]
        )
        
        results = uds3_core.search_by_4d_location(
            center_coord=center,
            radius_m=data.get('radius_m', 1000),
            time_range=data.get('time_range'),
            target_crs=data.get('target_crs')
        )
        
        return jsonify({
            'status': 'success',
            'results': results,
            'query_meta': {
                'center_coordinates': data,
                'total_results': len(results),
                'search_radius_m': data.get('radius_m', 1000)
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/v1/geo/crs-transform', methods=['POST'])
def transform_crs():
    """CRS-Transformation-Service"""
    try:
        data = request.get_json()
        
        source_coord = SpatialCoordinate(
            x=data['x'], y=data['y'], z=data.get('z'),
            crs=CoordinateReferenceSystem[data['source_crs']]
        )
        
        target_crs = CoordinateReferenceSystem[data['target_crs']]
        
        transformer = CRSTransformer()
        transformed = transformer.transform_coordinate(source_coord, target_crs)
        
        return jsonify({
            'status': 'success',
            'transformed_coordinates': {
                'x': transformed.x, 'y': transformed.y, 'z': transformed.z,
                'crs': transformed.crs.value,
                'accuracy_xy': transformed.accuracy_xy
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
```

### 4. COVINA UI Integration
```python
# In covina_ui_sidebar.py erweitern:

def create_4d_geo_search_panel(self):
    """4D-Geodaten-Suchpanel"""
    
    frame = ttk.LabelFrame(self.sidebar_frame, text="4D-Geodaten-Suche", padding=10)
    
    # Koordinaten-Eingabe
    ttk.Label(frame, text="Längengrad:").grid(row=0, column=0, sticky='w')
    self.longitude_var = tk.StringVar()
    ttk.Entry(frame, textvariable=self.longitude_var, width=15).grid(row=0, column=1)
    
    ttk.Label(frame, text="Breitengrad:").grid(row=1, column=0, sticky='w')
    self.latitude_var = tk.StringVar()
    ttk.Entry(frame, textvariable=self.latitude_var, width=15).grid(row=1, column=1)
    
    ttk.Label(frame, text="Höhe (optional):").grid(row=2, column=0, sticky='w')
    self.elevation_var = tk.StringVar()
    ttk.Entry(frame, textvariable=self.elevation_var, width=15).grid(row=2, column=1)
    
    # CRS-Auswahl
    ttk.Label(frame, text="Koordinatensystem:").grid(row=3, column=0, sticky='w')
    self.crs_var = tk.StringVar(value="WGS84_2D")
    crs_combo = ttk.Combobox(frame, textvariable=self.crs_var, width=12,
                            values=["WGS84_2D", "WGS84_3D", "UTM32N_ETRS89", "GAUSS_KRUGER_3"])
    crs_combo.grid(row=3, column=1)
    
    # Suchradius
    ttk.Label(frame, text="Radius (m):").grid(row=4, column=0, sticky='w')
    self.radius_var = tk.StringVar(value="1000")
    ttk.Entry(frame, textvariable=self.radius_var, width=15).grid(row=4, column=1)
    
    # Zeit-Filter
    ttk.Label(frame, text="Von (JJJJ-MM-TT):").grid(row=5, column=0, sticky='w')
    self.time_start_var = tk.StringVar()
    ttk.Entry(frame, textvariable=self.time_start_var, width=15).grid(row=5, column=1)
    
    ttk.Label(frame, text="Bis (JJJJ-MM-TT):").grid(row=6, column=0, sticky='w')  
    self.time_end_var = tk.StringVar()
    ttk.Entry(frame, textvariable=self.time_end_var, width=15).grid(row=6, column=1)
    
    # 4D-Suche starten
    ttk.Button(frame, text="4D-Geo-Suche", 
              command=self.execute_4d_geo_search).grid(row=7, column=0, columnspan=2, pady=10)
    
    return frame
```

## Test-Deployment

### Sofortiger Test mit Demo-System:
```bash
cd y:\veritas
python uds3_4d_geo_demo.py
```

### Integration in Hauptsystem:
1. **Backend**: `database_api_postgis_4d.py` in bestehende Database-APIs integrieren
2. **Core**: `uds3_4d_geo_extension.py` in UDS3-Core importieren  
3. **Scraper**: 4D-Geo-Extraktion in Scraping-Pipeline einbauen
4. **API**: Neue 4D-Endpoints zu `api_endpoint.py` hinzufügen
5. **UI**: 4D-Geo-Panel in COVINA-Interface integrieren

## Performance-Monitoring 
```python
# Monitoring für 4D-System einrichten:
geo_4d_metrics = Geo4DMonitoring()
metrics = geo_4d_metrics.collect_4d_metrics()

print(f"4D-Koordinaten gesamt: {metrics['coordinates']['total_4d_coordinates']}")
print(f"CRS-Verteilung: {metrics['coordinates']['crs_distribution']}")  
print(f"Durchschn. 4D-Abfrage: {metrics['performance']['avg_4d_query_time']}ms")
```

---

**Status:** 4D-System bereit für sofortige Integration! 🚀
