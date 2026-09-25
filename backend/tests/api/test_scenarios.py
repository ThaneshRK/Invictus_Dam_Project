import pytest
import pytest_asyncio
import asyncpg
from httpx import AsyncClient
from sqlalchemy import text
from conftest import test_engine as engine

@pytest_asyncio.fixture(autouse=True)
async def check_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except (ConnectionRefusedError, asyncpg.exceptions.CannotConnectNowError, OSError) as e:
        pytest.skip(f"Database unavailable: {e}")

@pytest.mark.asyncio
async def test_create_scenario(async_client: AsyncClient):
    proj_res = await async_client.post("/api/v1/projects/", json={"name": "Scenario Test"})
    if proj_res.status_code != 201:
        pytest.skip("Could not create project")
    project_id = proj_res.json()["id"]

    valid_dam_break_params = {
        "initial_water_level": 100.0,
        "reservoir_volume": 1000000.0,
        "breach_width": 50.0,
        "breach_height": 20.0,
        "breach_elevation": 80.0,
        "breach_formation_time": 2.0,
        "initial_downstream_condition": 0.5
    }

    scenario_res = await async_client.post(
        f"/api/v1/projects/{project_id}/scenarios",
        json={
            "name": "Catastrophic Failure",
            "scenario_type": "DAM_BREAK",
            "parameters": valid_dam_break_params,
            "simulation_duration": 24.0,
            "timestep": 1.0,
            "output_interval": 60.0
        }
    )
    
    assert scenario_res.status_code == 201
    data = scenario_res.json()
    assert data["name"] == "Catastrophic Failure"
    assert data["scenario_type"] == "DAM_BREAK"
    assert "id" in data

@pytest.mark.asyncio
async def test_validate_scenario_missing_datasets(async_client: AsyncClient):
    proj_res = await async_client.post("/api/v1/projects/", json={"name": "Scenario Validation Test"})
    if proj_res.status_code != 201:
        pytest.skip("Could not create project")
    project_id = proj_res.json()["id"]

    scenario_res = await async_client.post(
        f"/api/v1/projects/{project_id}/scenarios",
        json={
            "name": "Validation Test",
            "scenario_type": "WATER_RELEASE",
            "parameters": {
                "initial_water_level": 100.0,
                "initial_discharge": 0.0,
                "peak_discharge": 500.0,
                "release_duration": 10.0
            },
            "simulation_duration": 12.0,
            "timestep": 1.0,
            "output_interval": 3600.0
        }
    )
    assert scenario_res.status_code == 201
    scenario_id = scenario_res.json()["id"]

    val_res = await async_client.post(f"/api/v1/scenarios/{scenario_id}/validate")
    # Should fail because source_datasets is missing/empty
    assert val_res.status_code == 400
    assert "Project missing selected dam" in val_res.json()["detail"]
