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
async def test_create_export_job(async_client: AsyncClient):
    # Setup requires a project, scenario, and result.
    # To keep tests fast and decoupled, we verify failure on missing result
    res = await async_client.post(
        "/api/v1/exports",
        json={"result_id": "00000000-0000-0000-0000-000000000000", "format": "SHP"}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]
