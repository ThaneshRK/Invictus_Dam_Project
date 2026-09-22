import pytest
from sqlalchemy import text
import asyncpg
from conftest import test_engine as engine

@pytest.mark.asyncio
async def test_database_connectivity():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except (ConnectionRefusedError, asyncpg.exceptions.CannotConnectNowError, OSError) as e:
        pytest.skip(f"Database unavailable, skipping connectivity test. Reason: {e}")
