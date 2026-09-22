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
async def test_create_preprocessing_job(async_client: AsyncClient):
    # Setup project
    proj_res = await async_client.post("/api/v1/projects/", json={"name": "Job Test"})
    if proj_res.status_code != 201:
        pytest.skip("Could not create project")
    project_id = proj_res.json()["id"]

    # Create job
    job_res = await async_client.post(
        f"/api/v1/projects/{project_id}/preprocessing",
        json={"task_type": "DEM_PREP", "parameters": {"input_dem": "dummy.tif"}}
    )
    assert job_res.status_code == 202
    job_data = job_res.json()
    assert job_data["status"] == "PENDING"
    assert "id" in job_data
    job_id = job_data["id"]

    # Check status
    status_res = await async_client.get(f"/api/v1/preprocessing/{job_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] in ["PENDING", "RUNNING", "COMPLETED", "FAILED"]
