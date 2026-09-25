import pytest
from app.engines.sph.solver import SPH2DSolver
from app.engines.sph.engine import SPHEngine

def test_sph_solver_init():
    solver = SPH2DSolver(max_particles=100, h=2.0)
    solver.integrator.max_dt = 0.01
    solver.init_benchmark_dam_break(0, 10, 0, 10, 1.0, [0, 10, 0, 10], None)
    assert solver.state.num_particles > 0
    assert len(solver.state.pos) >= 100

def test_sph_engine_lifecycle():
    class MockScenario:
        class ScenarioType:
            value = "DAM_BREAK"
        scenario_type = ScenarioType()
        simulation_duration = 0.001
        parameters = {"breach_width": 10.0, "initial_water_level": 10.0}

    class MockContext:
        scenario = MockScenario()
        dem = None
        hydrology = None
        
    engine = SPHEngine(MockContext())
    engine.is_benchmark = True  # force benchmark mode to bypass geom validation
    assert engine.validate() == True
    
    engine.prepare()
    assert engine.status == "PREPARED"
    
    engine.run()
    assert engine.status == "COMPLETED"
    
    results = engine.load_results()
    assert "max_depth_array" in results
