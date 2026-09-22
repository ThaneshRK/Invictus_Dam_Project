import uuid
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.logger import logger

class RelationshipDiscovery:
    """
    Discovers relationships between Dams, Reservoirs, and Rivers using spatial
    proximity (PostGIS) and attribute matching.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_discovery(self):
        """Runs the batch discovery process for all unmatched dams."""
        logger.info("Starting relationship discovery process...")
        
        # 1. Match Dam -> Reservoir
        await self._match_dam_to_reservoir()
        
        # 2. Match Dam -> River
        await self._match_dam_to_river()
        
        logger.info("Relationship discovery completed.")

    async def _match_dam_to_reservoir(self):
        """
        Matches a Dam to a Reservoir.
        Tries ST_DWithin (e.g., dam point within 500 meters of reservoir polygon)
        """
        sql = """
        INSERT INTO dam_relationships (id, dam_id, target_type, target_id, match_method, match_distance, match_confidence, match_status, created_at)
        SELECT 
            gen_random_uuid()::varchar,
            d.id,
            'RESERVOIR',
            r.id,
            'SPATIAL_DWITHIN',
            ST_Distance(d.geometry::geography, r.geometry::geography),
            0.8, -- confidence
            'HIGH_CONFIDENCE',
            NOW()
        FROM government_dams d
        JOIN government_reservoirs r ON ST_DWithin(d.geometry, r.geometry, 0.005)
        WHERE NOT EXISTS (
            SELECT 1 FROM dam_relationships dr 
            WHERE dr.dam_id = d.id AND dr.target_type = 'RESERVOIR'
        )
        -- To avoid multiple matches, we can use DISTINCT ON but this is a simple bulk heuristic.
        -- We will just insert all close matches and they can be reviewed later.
        """
        try:
            await self.db.execute(text(sql))
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error matching dams to reservoirs: {e}")
            await self.db.rollback()

    async def _match_dam_to_river(self):
        """
        Matches a Dam to a River.
        Tries ST_DWithin (e.g., dam point within 500 meters of river linestring).
        """
        sql = """
        INSERT INTO dam_relationships (id, dam_id, target_type, target_id, match_method, match_distance, match_confidence, match_status, created_at)
        SELECT 
            gen_random_uuid()::varchar,
            d.id,
            'RIVER',
            r.id,
            'SPATIAL_DWITHIN',
            ST_Distance(d.geometry::geography, r.geometry::geography),
            0.7, -- confidence
            'HIGH_CONFIDENCE',
            NOW()
        FROM government_dams d
        JOIN government_rivers r ON ST_DWithin(d.geometry, r.geometry, 0.005)
        WHERE NOT EXISTS (
            SELECT 1 FROM dam_relationships dr 
            WHERE dr.dam_id = d.id AND dr.target_type = 'RIVER'
        )
        """
        try:
            await self.db.execute(text(sql))
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error matching dams to rivers: {e}")
            await self.db.rollback()
