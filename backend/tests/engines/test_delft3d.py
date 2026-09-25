import pytest
from app.engines.delft3d.engine import Delft3DEngine
from app.engines.delft3d.executor import HostDelft3DExecutor

def test_delft3d_validation():
    class MockScenario:
        class ScenarioType:
            value = "DAM_BREAK"
        scenario_type = ScenarioType()
        simulation_duration = 1.0
        timestep = 60.0
        parameters = {}

    class MockContext:
        scenario = MockScenario()
        dem = None
        hydrology = None

    engine = Delft3DEngine(MockContext())
    assert engine.validate() == True

def test_delft3d_executor_check():
    executor = HostDelft3DExecutor()
    assert executor.validate_installation() == True
