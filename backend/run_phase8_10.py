import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.ingestion.relationships import RelationshipDiscovery
from app.services.ingestion.readiness import ReadinessCalculator

async def run():
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("Running Relationships...")
        rel = RelationshipDiscovery(db)
        await rel.run_discovery()
        print("Running Readiness...")
        read = ReadinessCalculator(db)
        await read.update_all_dams()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(run())
