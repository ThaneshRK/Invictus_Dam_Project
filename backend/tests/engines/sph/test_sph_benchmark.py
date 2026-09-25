import pytest
import numpy as np
from app.engines.sph.engine import SPHEngine

def test_sph_level_2_benchmark():
    class MockContext:
        class MockScenario:
            class ScenarioType:
                value = "DAM_BREAK"
            scenario_type = ScenarioType()
            simulation_duration = 0.0005
            parameters = {
                "particle_spacing": 2.0,
                "smoothing_length": 4.0,
                "breach_width": 20.0,
                "initial_water_level": 10.0,
                "failure_time": 0.0,
                "formation_time": 0.1
            }
        scenario = MockScenario()
        dem = None
        hydrology = None
        
    engine = SPHEngine(MockContext())
    engine.is_benchmark = True
    assert engine.validate()
    engine.prepare()
    assert engine.status == "PREPARED"
    
    # Should have ~ 50 particles for this tiny block
    assert engine.solver.state.num_particles > 10
    
    engine.run()
    
    assert engine.status == "COMPLETED", f"Engine failed: {engine.error_message}"
    
    # Check diagnostics
    diags = engine.diagnostics
    assert "relative_volume_error" in diags
    assert abs(diags["relative_volume_error"]) < 0.05
    
    # Check that particles have moved and velocities are reasonable
    max_vel = diags["max_velocity"]
    assert max_vel > 0.1 # Should have moved due to gravity
    assert max_vel < 50.0 # Shouldn't explode
    
    results = engine.load_results()
    assert "max_depth_array" in results
    assert "inundation_polygon" in results
