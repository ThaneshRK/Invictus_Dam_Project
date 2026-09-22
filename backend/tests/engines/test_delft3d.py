import pytest
from app.engines.delft3d.engine import Delft3DEngine
from app.engines.delft3d.executor import HostDelft3DExecutor

def test_delft3d_validation():
    config = {
        "scenario_type": "DAM_BREAK",
        "time_control": {"duration_hours": 1.0, "timestep_seconds": 60.0}
    }
    engine = Delft3DEngine(config)
    assert engine.validate() == True

def test_delft3d_executor_check():
    executor = HostDelft3DExecutor()
    assert executor.validate_installation() == True
