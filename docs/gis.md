# GIS Processing

The framework supports extensive preprocessing of both raster and vector formats. 
Operations rely heavily on `rasterio` and `geopandas`.

## Windowed Raster Processing
To support massive regional DEMs without consuming excessive RAM, operations like `handle_nodata` 
use `rasterio`'s `block_windows`. This approach allows chunked reading and writing.

## Terrain Derivatives
We implement modular derivative generation (slope and aspect) using `numpy` gradients. 
This lays the foundation for advanced hydrological simulations (e.g., integrating `richdem` or `pysheds` in the future) while keeping the environment footprint relatively low for Phase 2.

## Geometry Preparation
All ingested geometries (Rivers, Dams, Blockages) are forced into a unified CRS (`EPSG:4326` by default) 
using `GISService.normalize_crs`. This ensures downstream operations do not fail due to spatial reference mismatches.
