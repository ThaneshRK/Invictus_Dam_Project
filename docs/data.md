# Data Ingestion & Formats

This document outlines the supported data formats and the validation steps performed during ingestion in the Flood Simulation & HADR Framework.

## Supported Formats

### Raster Data
- **GeoTIFF (.tif, .tiff)**: Recommended for all grid-based continuous data (DEM, land cover, probability surfaces).
- **Validation**:
  - File existence and readable by `rasterio`.
  - CRS detection.
  - Bounding box and spatial resolution extraction.

### Vector Data
- **Shapefile (.shp)**: Standard vector format (requires associated .shx, .dbf, .prj files if uploaded together, though currently singular file uploads are prioritized; GeoJSON is preferred for single-file web uploads).
- **GeoJSON (.geojson)**: Lightweight, web-friendly vector format.
- **KML (.kml)**: Supported via `fiona` drivers.
- **Validation**:
  - Readable by `geopandas`.
  - Must contain valid geometries.
  - CRS and bounding box detection.

### Tabular Data
- **CSV (.csv)**: General tabular data. If `latitude` and `longitude` columns are present, spatial bounds can be inferred (EPSG:4326).
- **Validation**:
  - Readable by `pandas`.

## Ingestion Strategy

To support massive datasets (e.g., global DEMs), the ingestion service uses **lazy loading**.
Rasters are never fully loaded into memory during metadata extraction. We utilize `rasterio.open()` which only parses headers. Vectors are parsed using `geopandas` which is efficient for typical bounding box and CRS validation.
