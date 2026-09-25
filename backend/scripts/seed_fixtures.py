import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import async_session_factory
from app.api.endpoints.government import seed_government_fixtures

async def main():
    print("Seeding 5 static government dam systems into database...")
    async with async_session_factory() as db:
        res = await seed_government_fixtures(db)
        print("Seed result:", res)

if __name__ == "__main__":
    asyncio.run(main())
