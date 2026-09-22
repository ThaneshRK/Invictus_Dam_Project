import pytest
import uuid
import httpx
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import get_db_session
from app.models.scenario import Scenario
from app.models.project import Project

@pytest.mark.asyncio
async def test_hadr_service(client, db_session):
    # Create project and scenario to satisfy DB dependencies
    project = Project(
        name="Test Project",
        description="Test",
        latitude=11.8,
        longitude=77.8,
        crs="EPSG:4326"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    scenario = Scenario(
        project_id=project.id,
        name="Test Scenario",
        scenario_type="DAM_BREAK",
        simulation_duration=24.0,
        timestep=1.0,
        output_interval=3600.0
    )
    db_session.add(scenario)
    await db_session.commit()
    await db_session.refresh(scenario)

    response = await client.get(f"/api/v1/hadr/{scenario.id}")
    assert response.status_code == 200
    data = response.json()
    assert "impact" in data
    assert "exposed_population" in data["impact"]
    assert "metadata" in data["impact"]
    assert data["impact"]["metadata"].get("population_source") == "Census of India"
