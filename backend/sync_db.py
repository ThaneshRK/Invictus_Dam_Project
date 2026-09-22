import asyncio
from app.db.session import engine
from app.db.base_class import Base
from app.models.project import Project
from app.models.scenario import Scenario, InitialCondition, DamBreakParameters, ControlledReleaseParameters, RiverBlockageParameters
from app.models.government import GovernmentInfrastructureFeature

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_models())
