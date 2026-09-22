from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.logger import logger

class ReadinessCalculator:
    """
    Calculates spatial data readiness for dams based on the existence of required relationships.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_all_dams(self):
        """Updates readiness status for all dams."""
        # A dam is SPATIAL_READY if it has BOTH a reservoir AND a river linked to it.
        # Otherwise MISSING.
        sql = """
        UPDATE government_dams
        SET spatial_data_readiness = CASE
            WHEN (
                EXISTS(SELECT 1 FROM dam_relationships WHERE dam_id = government_dams.id AND target_type = 'RESERVOIR')
                AND
                EXISTS(SELECT 1 FROM dam_relationships WHERE dam_id = government_dams.id AND target_type = 'RIVER')
            ) THEN 'AVAILABLE'
            ELSE 'MISSING'
        END;
        """
        try:
            await self.db.execute(text(sql))
            await self.db.commit()
            logger.info("Readiness calculation updated for all dams.")
        except Exception as e:
            logger.error(f"Error updating readiness: {e}")
            await self.db.rollback()
