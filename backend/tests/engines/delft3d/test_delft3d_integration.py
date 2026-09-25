import os
import pytest
from unittest.mock import patch, MagicMock
from geoalchemy2.shape import from_shape
import shapely.geometry

from app.engines.delft3d.builder import Delft3DModelBuilder
from app.engines.delft3d.executor import HostDelft3DExecutor, DockerDelft3DExecutor
from app.engines.delft3d.parser import Delft3DResultParser
from app.engines.delft3d.engine import Delft3DEngine
from app.core.config import settings

try:
    import xarray as xr
except ImportError:
    xr = None

def test_delft3d_builder_mdu_generation(tmp_path):
    mock_context = MagicMock()
    mock_context.scenario.scenario_type.value = "DAM_BREAK"
    mock_context.scenario.parameters = {"initial_water_level": 10.5, "duration_hours": 12}
    
    # Create real test dem tif
    import rasterio
    import numpy as np
    from rasterio.transform import from_origin
    
    dem_path = str(tmp_path / "test_dem.tif")
    transform = from_origin(76.4, 31.5, 0.001, 0.001)
    with rasterio.open(
        dem_path, 'w', driver='GTiff',
        height=10, width=10, count=1, dtype=np.float32,
        crs='EPSG:4326', transform=transform, nodata=-9999
    ) as dst:
        dst.write(np.zeros((10, 10), dtype=np.float32), 1)

    mock_context.dem.metadata = {"file_path": dem_path}
    mock_context.dam.geometry = from_shape(shapely.geometry.Point(76.45, 31.45), srid=4326)
    mock_context.study_area = {"type": "Polygon", "coordinates": [[[76.4, 31.4], [76.5, 31.4], [76.5, 31.5], [76.4, 31.5], [76.4, 31.4]]]}

    builder = Delft3DModelBuilder(
        workspace_root=str(tmp_path),
        simulation_id="test-sim-001",
        context=mock_context
    )
    
    mdu_file = builder.build()
    assert mdu_file == "scenario.mdu"
    
    mdu_path = os.path.join(builder.workspace_path, mdu_file)
    assert os.path.exists(mdu_path)
    
    with open(mdu_path, "r") as f:
        content = f.read()
        assert "[physics]" in content

def test_delft3d_host_executor(tmp_path):
    executor = HostDelft3DExecutor(workspace_path=str(tmp_path), mdu_filename="scenario.mdu")
    cmd = executor.build_command()
    assert cmd[0] == "bash"
    assert "run_dflowfm.sh" in cmd[1]
    assert "scenario.mdu" in cmd[2]

def test_delft3d_docker_executor(tmp_path):
    executor = DockerDelft3DExecutor(workspace_path=str(tmp_path), mdu_filename="scenario.mdu")
    cmd = executor.build_command()
    assert cmd[0] == "docker"
    assert "run" in cmd
    assert settings.DELFT3D_CONTAINER_IMAGE in cmd
    assert "dflowfm" in cmd

@pytest.mark.skipif(xr is None, reason="xarray not installed")
def test_delft3d_parser_variable_discovery(tmp_path):
    class MockDataset:
        def __init__(self, vars):
            self.variables = {v: None for v in vars}
            
    parser = Delft3DResultParser(workspace_path=str(tmp_path))
    
    ds = MockDataset(["mesh2d_s1", "mesh2d_waterdepth", "mesh2d_ucx", "mesh2d_ucy", "time", "mesh2d_face_x", "mesh2d_face_y"])
    var_map = parser.discover_variables(ds)
    
    assert var_map["water_level"] == "mesh2d_s1"
    assert var_map["water_depth"] == "mesh2d_waterdepth"
    assert var_map["velocity_x"] == "mesh2d_ucx"
    assert var_map["x"] == "mesh2d_face_x"

@patch('app.engines.delft3d.engine.settings')
def test_delft3d_engine_unconfigured(mock_settings, tmp_path):
    mock_settings.DELFT3D_ENABLED = False
    mock_context = MagicMock()
    
    engine = Delft3DEngine(context=mock_context, workspace_dir=str(tmp_path))
    assert engine.validate() is False
    assert "not enabled" in engine.error_message
