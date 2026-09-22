import pytest
import geopandas as gpd
from shapely.geometry import Point
from app.services.gis_service import GISService

def test_normalize_crs():
    # Create GeoDataFrame in a different CRS (e.g., Web Mercator)
    gdf = gpd.GeoDataFrame(
        {'id': [1]}, 
        geometry=[Point(0, 0)],
        crs="EPSG:3857"
    )
    
    # Normalize to EPSG:4326
    normalized_gdf = GISService.normalize_crs(gdf)
    assert normalized_gdf.crs.to_string() == "EPSG:4326"

def test_prepare_river_geometry():
    gdf = gpd.GeoDataFrame(
        {'name': ['Test River']}, 
        geometry=[Point(0, 0)],
        crs="EPSG:4326"
    )
    result = GISService.prepare_river_geometry(gdf)
    assert result.crs.to_string() == "EPSG:4326"
