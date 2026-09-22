import pytest
from httpx import AsyncClient
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

@pytest.mark.asyncio
async def test_get_location_intelligence(client: AsyncClient, db_session: AsyncSession):
    # This assumes there is an existing project in the DB or we create one here.
    # We will just verify that the endpoint handles 404 properly for non-existent project
    # or we can test an invalid UUID.
    
    response = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000/enrichment")
    assert response.status_code == 200 # It should return an empty response with "NONE" status if project not found
    data = response.json()
    assert data["job_status"] == "NONE"
    
@pytest.mark.asyncio
async def test_create_project_triggers_enrichment(client: AsyncClient, db_session: AsyncSession):
    # Create project
    project_data = {
        "name": "Test Mettur Dam",
        "description": "A test project",
        "latitude": 11.8,
        "longitude": 77.8,
        "crs": "EPSG:4326"
    }
    response = await client.post("/api/v1/projects/", json=project_data)
    assert response.status_code == 201
    
    project_id = response.json()["id"]
    
    # Wait for the background task to run
    import asyncio
    await asyncio.sleep(0.2)
    
    # Check if job was created
    response = await client.get(f"/api/v1/projects/{project_id}/enrichment")
    assert response.status_code == 200
    # Because BackgroundTasks run after the response in FastAPI, in a test environment
    # using TestClient it runs synchronously immediately, but with AsyncClient it depends.
    # It should at least be PENDING or COMPLETED
    data = response.json()
    assert data["job_status"] in ["PENDING", "RUNNING", "COMPLETED", "PARTIAL", "FAILED"]
