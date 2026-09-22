import os
import pytest
from unittest.mock import patch
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
    config = {
        "scenario_type": "DAM_BREAK",
        "parameters": {
            "initial_water_level": 10.5
        },
        "time_control": {"duration_hours": 12}
    }
    
    builder = Delft3DModelBuilder(
        workspace_root=str(tmp_path),
        simulation_id="test-sim-001",
        config=config
    )
    
    mdu_file = builder.build()
    assert mdu_file == "scenario.mdu"
    
    mdu_path = os.path.join(builder.workspace_path, mdu_file)
    assert os.path.exists(mdu_path)
    
    # Verify MDU contents
    with open(mdu_path, "r") as f:
        content = f.read()
        assert "[physics]" in content
        assert "43200" in content  # TStop (12 * 3600)

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
    
    engine = Delft3DEngine(scenario_config={})
    assert engine.validate() is False
    assert "not enabled" in engine.error_message
