import pytest
import os
import geopandas as gpd
from shapely.geometry import Point
from app.services.dataset_service import DatasetService

@pytest.fixture
def valid_geojson(tmp_path):
    path = tmp_path / "valid.geojson"
    gdf = gpd.GeoDataFrame(
        {'id': [1], 'value': ['test']}, 
        geometry=[Point(0, 0)],
        crs="EPSG:4326"
    )
    gdf.to_file(path, driver="GeoJSON")
    return str(path)

@pytest.fixture
def empty_geojson(tmp_path):
    path = tmp_path / "empty.geojson"
    gdf = gpd.GeoDataFrame(columns=['id', 'geometry'], geometry='geometry', crs="EPSG:4326")
    gdf.to_file(path, driver="GeoJSON")
    return str(path)

def test_inspect_vector_valid(valid_geojson):
    metadata = DatasetService._inspect_vector(valid_geojson, ".geojson")
    assert metadata["crs"] == "EPSG:4326"
    assert metadata["metadata_"]["features_count"] == 1
    assert "id" in metadata["metadata_"]["columns"]
    assert "POLYGON" in metadata["bounding_box"]

def test_inspect_vector_empty(empty_geojson):
    with pytest.raises(ValueError, match="Vector file is empty"):
        DatasetService._inspect_vector(empty_geojson, ".geojson")
