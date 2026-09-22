import asyncio
from app.db.session import engine

async def reset_models():
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

from sqlalchemy import text
asyncio.run(reset_models())
