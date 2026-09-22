import pytest
import pytest_asyncio
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

@pytest.mark.asyncio
async def test_create_project(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/projects/",
        json={"name": "Test Project", "description": "A test project", "crs": "EPSG:4326"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data

@pytest.mark.asyncio
async def test_get_projects(async_client: AsyncClient):
    response = await async_client.get("/api/v1/projects/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
