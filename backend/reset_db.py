import asyncio
from app.db.session import engine
from app.db.base_class import Base

async def reset_models():
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        await conn.run_sync(Base.metadata.create_all)

from sqlalchemy import text
asyncio.run(reset_models())
