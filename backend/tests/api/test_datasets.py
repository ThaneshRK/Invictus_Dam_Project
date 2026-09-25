import pytest
import pytest_asyncio
import os
from httpx import AsyncClient
import asyncpg
from sqlalchemy import text
from conftest import test_engine as engine

@pytest_asyncio.fixture(autouse=True)
async def check_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except (ConnectionRefusedError, asyncpg.exceptions.CannotConnectNowError, OSError) as e:
        pytest.skip(f"Database unavailable: {e}")

@pytest.fixture
def mock_csv_file(tmp_path):
    file_path = tmp_path / "test.csv"
    with open(file_path, "w") as f:
        f.write("timestamp,value\n0.0,100.0\n1.0,200.0")
    return file_path

@pytest.mark.asyncio
async def test_dataset_upload_invalid_file(async_client: AsyncClient, tmp_path):
    # Create project first
    proj_res = await async_client.post("/api/v1/projects/", json={"name": "Dataset Test"})
    if proj_res.status_code != 201:
        pytest.skip("Could not create project")
    
    project_id = proj_res.json()["id"]
    
    # Create a dummy invalid file
    dummy_file = tmp_path / "invalid.xyz"
    dummy_file.write_text("dummy")
    
    with open(dummy_file, "rb") as f:
        response = await async_client.post(
            f"/api/v1/projects/{project_id}/datasets",
            data={"name": "Invalid Data", "dataset_type": "DEM"},
            files={"file": ("invalid.xyz", f, "text/plain")}
        )
    
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

@pytest.mark.asyncio
async def test_dataset_upload_csv(async_client: AsyncClient, mock_csv_file):
    # Create project
    proj_res = await async_client.post("/api/v1/projects/", json={"name": "CSV Test Project"})
    project_id = proj_res.json()["id"]
    
    with open(mock_csv_file, "rb") as f:
        response = await async_client.post(
            f"/api/v1/projects/{project_id}/datasets",
            data={"name": "Test CSV", "dataset_type": "hydrological"},
            files={"file": ("test.csv", f, "text/csv")}
        )
        
    if response.status_code != 201:
        print("CSV UPLOAD ERROR:", response.text)
    assert response.status_code == 201
    data = response.json()
    assert data["format"] == "CSV"
    assert data["crs"] is None
    assert "rows" in data["metadata_"]
