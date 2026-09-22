import pytest
from pydantic import ValidationError
from app.schemas.scenario_parameters import DamBreakParameters, WaterReleaseParameters
from app.schemas.scenario import ScenarioBase
from app.models.scenario import ScenarioType

def test_dam_break_validation_negative_value():
    with pytest.raises(ValidationError) as exc_info:
        DamBreakParameters(
            initial_water_level=10.0,
            reservoir_volume=-500.0, # invalid
            breach_width=50.0,
            breach_height=20.0,
            breach_elevation=100.0,
            breach_formation_time=2.0
        )
    assert "Input should be greater than or equal to 0" in str(exc_info.value)

def test_water_release_peak_validation():
    with pytest.raises(ValidationError) as exc_info:
        WaterReleaseParameters(
            initial_water_level=10.0,
            initial_discharge=100.0,
            peak_discharge=50.0, # invalid, < initial
            release_duration=5.0
        )
    assert "Initial discharge cannot be greater than peak discharge" in str(exc_info.value)

def test_scenario_timestep_duration_validation():
    with pytest.raises(ValidationError) as exc_info:
        ScenarioBase(
            name="Test",
            scenario_type=ScenarioType.DAM_BREAK,
            parameters={},
            simulation_duration=1.0, # 1 hour = 3600 seconds
            timestep=4000.0, # invalid, > duration
            output_interval=4000.0
        )
    assert "Timestep cannot be larger than the simulation duration" in str(exc_info.value)

def test_scenario_output_interval_validation():
    with pytest.raises(ValidationError) as exc_info:
        ScenarioBase(
            name="Test",
            scenario_type=ScenarioType.DAM_BREAK,
            parameters={},
            simulation_duration=10.0,
            timestep=60.0,
            output_interval=30.0 # invalid, < timestep
        )
    assert "Output interval cannot be smaller than timestep" in str(exc_info.value)
