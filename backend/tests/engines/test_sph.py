import pytest
from app.engines.sph.solver import SPHSolver
from app.engines.sph.engine import SPHEngine

def test_sph_solver_init():
    solver = SPHSolver(max_particles=100, h=2.0, max_dt=0.01)
    solver.init_benchmark_dam_break(0, 10, 0, 10, 1.0, [0, 10, 0, 10])
    assert solver.state.num_particles > 0
    assert len(solver.state.pos) >= 100

def test_sph_engine_lifecycle():
    config = {
        "metadata": {"type": "DAM_BREAK"},
        "time_control": {"duration_hours": 0.001, "timestep_seconds": 0.01}, # tiny duration
        "physics_parameters": {"breach_width": 10.0, "initial_water_level": 10.0}
    }
    
    engine = SPHEngine(config)
    assert engine.validate() == True
    
    engine.prepare()
    assert engine.status == "PREPARED"
    
    engine.run()
    assert engine.status == "COMPLETED"
    
    results = engine.load_results()
    assert "max_depth_array" in results
