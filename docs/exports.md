# GIS Export System

The export system translates raw numeric outputs into standards-compliant formats (SHP, KML, GeoJSON, GeoTIFF, CSV) required by urban planners and disaster management authorities.

## Formats Supported
- **GeoTIFF**: Direct raster exports preserving high-fidelity float arrays (e.g. depth mapping).
- **GeoJSON**: Web-friendly polygon geometries outlining flood extents.
- **SHP**: Standard Esri Shapefiles for legacy GIS mapping.
- **KML**: Formatted specifically for Google Earth Pro imports.
- **CSV**: Gridded centroid aggregations for tabular analytics.

## Memory Strategy
Exports are initiated via `POST /api/v1/exports` as **Background Tasks**. They do NOT block the main HTTP thread, meaning clients can request massive dataset conversions safely.
Rasters are handled via `rasterio` windowing, and geometries are streamed where applicable.

## Download Protocol
Clients can poll `GET /api/v1/exports/{id}` for progress. Once `status == COMPLETED`, the file can be retrieved securely using `GET /api/v1/exports/{id}/download`.
